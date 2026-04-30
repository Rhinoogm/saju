from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.schemas.saju import (
    AccountMeResponse,
    AccountOrderResponse,
    AccountReadingResponse,
    CheckoutResponse,
    ConcernCategory,
    CustomAnswersRequest,
    DiagnosticQuestion,
    FinalReadingResponse,
    FixedAnswersRequest,
    GenerateCustomQuestionsResponse,
    GenerateQuestionsResponse,
    InitialProfile,
    ReadingSessionCreateRequest,
    ReadingSessionResponse,
    ReadingSessionStatus,
    ReadingStyle,
    SajuData,
)
from app.services.db import get_db_pool
from app.services.portone import PortOnePayment


@dataclass(frozen=True)
class OrderRecord:
    id: str
    user_id: str
    session_id: str | None
    product_code: str
    payment_id: str
    order_name: str
    amount_krw: int
    currency: str
    status: str


@dataclass(frozen=True)
class ProductRecord:
    code: str
    name: str
    amount_krw: int
    currency: str
    active: bool


class ReadingRepository:
    async def create_session(self, user_id: str, payload: ReadingSessionCreateRequest) -> ReadingSessionResponse:
        raise NotImplementedError

    async def get_session(self, user_id: str, session_id: UUID | str) -> ReadingSessionResponse | None:
        raise NotImplementedError

    async def get_session_for_update(self, user_id: str, session_id: UUID | str) -> dict[str, Any] | None:
        raise NotImplementedError

    async def create_checkout(
        self,
        *,
        user_id: str,
        session_id: UUID | str,
        product_code: str,
        payment_id: str,
        store_id: str,
        channel_key: str,
        order_name: str,
        amount_krw: int,
        webhook_url: str,
    ) -> CheckoutResponse:
        raise NotImplementedError

    async def get_order_by_payment_id(self, payment_id: str) -> OrderRecord | None:
        raise NotImplementedError

    async def get_product(self, product_code: str) -> ProductRecord | None:
        raise NotImplementedError

    async def mark_payment_verified(
        self,
        *,
        order: OrderRecord,
        payment: PortOnePayment,
        webhook_id: str | None = None,
        event_type: str | None = None,
        raw_event: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    async def mark_payment_verification_failed(
        self,
        *,
        order: OrderRecord,
        reason: str,
        payment: PortOnePayment | None = None,
        webhook_id: str | None = None,
        event_type: str | None = None,
        raw_event: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    async def record_webhook_event_once(
        self,
        *,
        webhook_id: str,
        payment_id: str,
        event_type: str,
        raw_event: dict[str, Any],
    ) -> bool:
        raise NotImplementedError

    async def has_available_credit(self, user_id: str, session_id: UUID | str) -> bool:
        raise NotImplementedError

    async def save_fixed_questions(self, user_id: str, session_id: UUID | str, result: GenerateQuestionsResponse) -> None:
        raise NotImplementedError

    async def save_fixed_answers(self, user_id: str, session_id: UUID | str, payload: FixedAnswersRequest) -> None:
        raise NotImplementedError

    async def save_custom_questions(
        self,
        user_id: str,
        session_id: UUID | str,
        result: GenerateCustomQuestionsResponse,
    ) -> None:
        raise NotImplementedError

    async def save_custom_answers(self, user_id: str, session_id: UUID | str, payload: CustomAnswersRequest) -> None:
        raise NotImplementedError

    async def save_final_result_and_consume_credit(
        self,
        user_id: str,
        session_id: UUID | str,
        result: FinalReadingResponse,
    ) -> FinalReadingResponse:
        raise NotImplementedError

    async def get_profile(self, user_id: str) -> AccountMeResponse:
        raise NotImplementedError

    async def list_orders(self, user_id: str) -> list[AccountOrderResponse]:
        raise NotImplementedError

    async def list_readings(self, user_id: str) -> list[AccountReadingResponse]:
        raise NotImplementedError


class InMemoryDemoReadingRepository(ReadingRepository):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = asyncio.Lock()
        self._sessions: dict[str, ReadingSessionResponse] = {}
        self._orders_by_id: dict[str, dict[str, Any]] = {}
        self._orders_by_payment_id: dict[str, dict[str, Any]] = {}
        self._credits_by_order_id: dict[str, str] = {}
        self._webhook_ids: set[str] = set()
        self._products = {
            "SAJU_FULL_READING": ProductRecord(
                code="SAJU_FULL_READING",
                name=settings.saju_full_reading_order_name,
                amount_krw=settings.saju_full_reading_amount_krw,
                currency="KRW",
                active=True,
            )
        }

    async def create_session(self, user_id: str, payload: ReadingSessionCreateRequest) -> ReadingSessionResponse:
        now = _now_iso()
        session = ReadingSessionResponse(
            id=uuid4(),
            user_id=UUID(user_id),
            status=ReadingSessionStatus.payment_required,
            reading_style=payload.reading_style,
            initial_profile=InitialProfile.model_validate(payload.model_dump()),
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._sessions[str(session.id)] = session
        return session

    async def get_session(self, user_id: str, session_id: UUID | str) -> ReadingSessionResponse | None:
        async with self._lock:
            return self._session_for_user(user_id, session_id)

    async def get_session_for_update(self, user_id: str, session_id: UUID | str) -> dict[str, Any] | None:
        async with self._lock:
            session = self._session_for_user(user_id, session_id)
            return session.model_dump(mode="json") if session else None

    async def create_checkout(
        self,
        *,
        user_id: str,
        session_id: UUID | str,
        product_code: str,
        payment_id: str,
        store_id: str,
        channel_key: str,
        order_name: str,
        amount_krw: int,
        webhook_url: str,
    ) -> CheckoutResponse:
        async with self._lock:
            session = self._session_for_user(user_id, session_id)
            if session is None:
                raise LookupError("Reading session not found")

            if session.order_id:
                order = self._orders_by_id.get(str(session.order_id))
                if order and order["status"] in {"ready", "payment_requested"}:
                    return _checkout_response(order, store_id, channel_key, webhook_url)
                if order and order["status"] == "paid":
                    raise RuntimeError("Reading session already has a paid order")

            now = _now_iso()
            order = {
                "id": str(uuid4()),
                "user_id": user_id,
                "session_id": str(session.id),
                "product_code": product_code,
                "payment_id": payment_id,
                "order_name": order_name,
                "amount_krw": amount_krw,
                "currency": "KRW",
                "status": "payment_requested",
                "paid_at": None,
                "created_at": now,
                "updated_at": now,
            }
            self._orders_by_id[order["id"]] = order
            self._orders_by_payment_id[payment_id] = order
            session.order_id = UUID(order["id"])
            session.status = ReadingSessionStatus.payment_required
            session.updated_at = now
            return _checkout_response(order, store_id, channel_key, webhook_url)

    async def get_order_by_payment_id(self, payment_id: str) -> OrderRecord | None:
        async with self._lock:
            order = self._orders_by_payment_id.get(payment_id)
            return _order_record(order) if order else None

    async def get_product(self, product_code: str) -> ProductRecord | None:
        return self._products.get(product_code)

    async def mark_payment_verified(
        self,
        *,
        order: OrderRecord,
        payment: PortOnePayment,
        webhook_id: str | None = None,
        event_type: str | None = None,
        raw_event: dict[str, Any] | None = None,
    ) -> None:
        async with self._lock:
            stored_order = self._orders_by_id.get(order.id)
            if stored_order is None:
                return
            now = _now_iso()
            stored_order["status"] = "paid"
            stored_order["paid_at"] = payment.paid_at or now
            stored_order["updated_at"] = now
            stored_order["raw_payment"] = payment.as_raw()
            if webhook_id:
                self._webhook_ids.add(webhook_id)
            self._credits_by_order_id[order.id] = "available"
            if order.session_id and order.session_id in self._sessions:
                session = self._sessions[order.session_id]
                session.status = ReadingSessionStatus.paid
                session.updated_at = now

    async def mark_payment_verification_failed(
        self,
        *,
        order: OrderRecord,
        reason: str,
        payment: PortOnePayment | None = None,
        webhook_id: str | None = None,
        event_type: str | None = None,
        raw_event: dict[str, Any] | None = None,
    ) -> None:
        async with self._lock:
            stored_order = self._orders_by_id.get(order.id)
            if stored_order is None:
                return
            stored_order["status"] = "verification_failed"
            stored_order["failure_reason"] = reason
            stored_order["raw_payment"] = payment.as_raw() if payment else None
            stored_order["updated_at"] = _now_iso()
            if webhook_id:
                self._webhook_ids.add(webhook_id)

    async def record_webhook_event_once(
        self,
        *,
        webhook_id: str,
        payment_id: str,
        event_type: str,
        raw_event: dict[str, Any],
    ) -> bool:
        async with self._lock:
            if webhook_id in self._webhook_ids:
                return False
            self._webhook_ids.add(webhook_id)
            return True

    async def has_available_credit(self, user_id: str, session_id: UUID | str) -> bool:
        async with self._lock:
            session = self._session_for_user(user_id, session_id)
            if session is None or session.order_id is None:
                return False
            return self._credits_by_order_id.get(str(session.order_id)) == "available"

    async def save_fixed_questions(self, user_id: str, session_id: UUID | str, result: GenerateQuestionsResponse) -> None:
        async with self._lock:
            session = self._session_for_user(user_id, session_id)
            if session is None:
                return
            session.saju = result.saju
            session.category = result.category
            session.category_label = result.category_label
            session.fixed_questions = result.questions
            session.status = ReadingSessionStatus.fixed_questions_ready
            session.updated_at = _now_iso()

    async def save_fixed_answers(self, user_id: str, session_id: UUID | str, payload: FixedAnswersRequest) -> None:
        async with self._lock:
            session = self._session_for_user(user_id, session_id)
            if session is None:
                return
            session.fixed_answers = payload.fixed_answers
            session.updated_at = _now_iso()

    async def save_custom_questions(
        self,
        user_id: str,
        session_id: UUID | str,
        result: GenerateCustomQuestionsResponse,
    ) -> None:
        async with self._lock:
            session = self._session_for_user(user_id, session_id)
            if session is None:
                return
            session.custom_questions = result.questions
            session.status = ReadingSessionStatus.custom_questions_ready
            session.updated_at = _now_iso()

    async def save_custom_answers(self, user_id: str, session_id: UUID | str, payload: CustomAnswersRequest) -> None:
        async with self._lock:
            session = self._session_for_user(user_id, session_id)
            if session is None:
                return
            session.custom_answers = payload.custom_answers
            session.updated_at = _now_iso()

    async def save_final_result_and_consume_credit(
        self,
        user_id: str,
        session_id: UUID | str,
        result: FinalReadingResponse,
    ) -> FinalReadingResponse:
        async with self._lock:
            session = self._session_for_user(user_id, session_id)
            if session is None:
                raise LookupError("Reading session not found")
            if session.final_result is not None:
                return session.final_result
            if session.order_id is None or self._credits_by_order_id.get(str(session.order_id)) != "available":
                raise RuntimeError("No available reading credit")
            self._credits_by_order_id[str(session.order_id)] = "consumed"
            session.final_result = result
            session.status = ReadingSessionStatus.final_ready
            session.updated_at = _now_iso()
            return result

    async def get_profile(self, user_id: str) -> AccountMeResponse:
        return AccountMeResponse(
            id=user_id,
            email=self._settings.local_demo_email,
            display_name="로컬 데모",
            provider="local-demo",
        )

    async def list_orders(self, user_id: str) -> list[AccountOrderResponse]:
        async with self._lock:
            orders = [order for order in self._orders_by_id.values() if order["user_id"] == user_id]
            orders.sort(key=lambda order: order["created_at"], reverse=True)
            return [
                AccountOrderResponse(
                    id=order["id"],
                    payment_id=order["payment_id"],
                    product_code=order["product_code"],
                    order_name=order["order_name"],
                    amount_krw=order["amount_krw"],
                    currency=order["currency"],
                    status=order["status"],
                    paid_at=order["paid_at"],
                    created_at=order["created_at"],
                )
                for order in orders
            ]

    async def list_readings(self, user_id: str) -> list[AccountReadingResponse]:
        async with self._lock:
            sessions = [session for session in self._sessions.values() if str(session.user_id) == user_id]
            sessions.sort(key=lambda session: session.created_at or "", reverse=True)
            return [
                AccountReadingResponse(
                    id=session.id,
                    status=session.status,
                    reading_style=session.reading_style,
                    order_id=session.order_id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    has_final_result=session.final_result is not None,
                )
                for session in sessions
            ]

    def _session_for_user(self, user_id: str, session_id: UUID | str) -> ReadingSessionResponse | None:
        session = self._sessions.get(str(session_id))
        if session is None or str(session.user_id) != user_id:
            return None
        return session


class PostgresReadingRepository(ReadingRepository):
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def create_session(self, user_id: str, payload: ReadingSessionCreateRequest) -> ReadingSessionResponse:
        initial_profile = InitialProfile.model_validate(payload.model_dump()).model_dump(mode="json")
        row = await self._fetchrow(
            """
            insert into public.reading_sessions(user_id, status, reading_style, initial_profile)
            values($1::uuid, 'payment_required', $2, $3::jsonb)
            returning *
            """,
            user_id,
            payload.reading_style.value,
            initial_profile,
        )
        return _session_response(row)

    async def get_session(self, user_id: str, session_id: UUID | str) -> ReadingSessionResponse | None:
        row = await self._fetchrow(
            "select * from public.reading_sessions where id = $1::uuid and user_id = $2::uuid",
            str(session_id),
            user_id,
        )
        return _session_response(row) if row else None

    async def get_session_for_update(self, user_id: str, session_id: UUID | str) -> dict[str, Any] | None:
        return await self._fetchrow(
            "select * from public.reading_sessions where id = $1::uuid and user_id = $2::uuid",
            str(session_id),
            user_id,
        )

    async def create_checkout(
        self,
        *,
        user_id: str,
        session_id: UUID | str,
        product_code: str,
        payment_id: str,
        store_id: str,
        channel_key: str,
        order_name: str,
        amount_krw: int,
        webhook_url: str,
    ) -> CheckoutResponse:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                session = await conn.fetchrow(
                    "select id, order_id from public.reading_sessions where id = $1::uuid and user_id = $2::uuid for update",
                    str(session_id),
                    user_id,
                )
                if session is None:
                    return _not_found_checkout()
                if session["order_id"]:
                    order = await conn.fetchrow(
                        "select * from public.orders where id = $1::uuid and user_id = $2::uuid",
                        str(session["order_id"]),
                        user_id,
                    )
                    if order:
                        if order["status"] in {"ready", "payment_requested"}:
                            return _checkout_response(order, store_id, channel_key, webhook_url)
                        if order["status"] == "paid":
                            raise RuntimeError("Reading session already has a paid order")

                order = await conn.fetchrow(
                    """
                    insert into public.orders(
                      user_id, product_code, payment_id, order_name, amount_krw, currency, status
                    )
                    values($1::uuid, $2, $3, $4, $5, 'KRW', 'payment_requested')
                    returning *
                    """,
                    user_id,
                    product_code,
                    payment_id,
                    order_name,
                    amount_krw,
                )
                await conn.execute(
                    """
                    update public.reading_sessions
                    set order_id = $1::uuid, status = 'payment_required', updated_at = now()
                    where id = $2::uuid and user_id = $3::uuid
                    """,
                    str(order["id"]),
                    str(session_id),
                    user_id,
                )
        return _checkout_response(order, store_id, channel_key, webhook_url)

    async def get_order_by_payment_id(self, payment_id: str) -> OrderRecord | None:
        row = await self._fetchrow(
            """
            select o.*, rs.id as session_id
            from public.orders o
            left join public.reading_sessions rs on rs.order_id = o.id
            where o.payment_id = $1
            """,
            payment_id,
        )
        return _order_record(row) if row else None

    async def get_product(self, product_code: str) -> ProductRecord | None:
        row = await self._fetchrow("select * from public.products where code = $1", product_code)
        if row is None:
            return None
        return ProductRecord(
            code=row["code"],
            name=row["name"],
            amount_krw=row["amount_krw"],
            currency=row["currency"],
            active=row["active"],
        )

    async def mark_payment_verified(
        self,
        *,
        order: OrderRecord,
        payment: PortOnePayment,
        webhook_id: str | None = None,
        event_type: str | None = None,
        raw_event: dict[str, Any] | None = None,
    ) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await _insert_payment_event(conn, webhook_id, order.payment_id, event_type, raw_event)
                await conn.execute(
                    """
                    update public.orders
                    set status = 'paid',
                        portone_tx_id = coalesce($2, portone_tx_id),
                        raw_payment = $3::jsonb,
                        paid_at = coalesce(paid_at, now()),
                        updated_at = now()
                    where id = $1::uuid
                    """,
                    order.id,
                    payment.transaction_id,
                    payment.as_raw(),
                )
                await conn.execute(
                    """
                    insert into public.reading_credits(user_id, order_id, status)
                    values($1::uuid, $2::uuid, 'available')
                    on conflict(order_id) do nothing
                    """,
                    order.user_id,
                    order.id,
                )
                await conn.execute(
                    """
                    update public.reading_sessions
                    set status = 'paid', updated_at = now()
                    where order_id = $1::uuid and user_id = $2::uuid and status in ('payment_required', 'failed')
                    """,
                    order.id,
                    order.user_id,
                )

    async def mark_payment_verification_failed(
        self,
        *,
        order: OrderRecord,
        reason: str,
        payment: PortOnePayment | None = None,
        webhook_id: str | None = None,
        event_type: str | None = None,
        raw_event: dict[str, Any] | None = None,
    ) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await _insert_payment_event(conn, webhook_id, order.payment_id, event_type, raw_event)
                await conn.execute(
                    """
                    update public.orders
                    set status = 'verification_failed',
                        failure_reason = $2,
                        raw_payment = coalesce($3::jsonb, raw_payment),
                        updated_at = now()
                    where id = $1::uuid and status <> 'paid'
                    """,
                    order.id,
                    reason,
                    payment.as_raw() if payment else None,
                )

    async def record_webhook_event_once(
        self,
        *,
        webhook_id: str,
        payment_id: str,
        event_type: str,
        raw_event: dict[str, Any],
    ) -> bool:
        row = await self._fetchrow(
            """
            insert into public.payment_events(webhook_id, payment_id, event_type, raw_event)
            values($1, $2, $3, $4::jsonb)
            on conflict(webhook_id) do nothing
            returning id
            """,
            webhook_id,
            payment_id,
            event_type,
            raw_event,
        )
        return row is not None

    async def has_available_credit(self, user_id: str, session_id: UUID | str) -> bool:
        value = await self._fetchval(
            """
            select exists(
              select 1
              from public.reading_sessions rs
              join public.reading_credits rc on rc.order_id = rs.order_id
              where rs.id = $1::uuid and rs.user_id = $2::uuid and rc.status = 'available'
            )
            """,
            str(session_id),
            user_id,
        )
        return bool(value)

    async def save_fixed_questions(self, user_id: str, session_id: UUID | str, result: GenerateQuestionsResponse) -> None:
        payload = result.model_dump(mode="json")
        await self._execute(
            """
            update public.reading_sessions
            set fixed_questions = $3::jsonb,
                status = 'fixed_questions_ready',
                updated_at = now()
            where id = $1::uuid and user_id = $2::uuid
            """,
            str(session_id),
            user_id,
            payload,
        )

    async def save_fixed_answers(self, user_id: str, session_id: UUID | str, payload: FixedAnswersRequest) -> None:
        await self._execute(
            """
            update public.reading_sessions
            set fixed_answers = $3::jsonb, updated_at = now()
            where id = $1::uuid and user_id = $2::uuid
            """,
            str(session_id),
            user_id,
            [answer.model_dump(mode="json") for answer in payload.fixed_answers],
        )

    async def save_custom_questions(
        self,
        user_id: str,
        session_id: UUID | str,
        result: GenerateCustomQuestionsResponse,
    ) -> None:
        await self._execute(
            """
            update public.reading_sessions
            set custom_questions = $3::jsonb,
                status = 'custom_questions_ready',
                updated_at = now()
            where id = $1::uuid and user_id = $2::uuid
            """,
            str(session_id),
            user_id,
            result.model_dump(mode="json"),
        )

    async def save_custom_answers(self, user_id: str, session_id: UUID | str, payload: CustomAnswersRequest) -> None:
        await self._execute(
            """
            update public.reading_sessions
            set custom_answers = $3::jsonb, updated_at = now()
            where id = $1::uuid and user_id = $2::uuid
            """,
            str(session_id),
            user_id,
            [answer.model_dump(mode="json") for answer in payload.custom_answers],
        )

    async def save_final_result_and_consume_credit(
        self,
        user_id: str,
        session_id: UUID | str,
        result: FinalReadingResponse,
    ) -> FinalReadingResponse:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                session = await conn.fetchrow(
                    """
                    select * from public.reading_sessions
                    where id = $1::uuid and user_id = $2::uuid
                    for update
                    """,
                    str(session_id),
                    user_id,
                )
                if session is None:
                    raise LookupError("Reading session not found")
                if session["final_result"]:
                    return _final_result_response(session["final_result"])
                credit = await conn.fetchrow(
                    """
                    update public.reading_credits
                    set status = 'consumed',
                        consumed_by_session_id = $1::uuid,
                        consumed_at = now()
                    where user_id = $2::uuid
                      and order_id = $3::uuid
                      and status = 'available'
                    returning id
                    """,
                    str(session_id),
                    user_id,
                    str(session["order_id"]),
                )
                if credit is None:
                    raise RuntimeError("No available reading credit")
                await conn.execute(
                    """
                    update public.reading_sessions
                    set final_result = $3::jsonb,
                        status = 'final_ready',
                        updated_at = now()
                    where id = $1::uuid and user_id = $2::uuid
                    """,
                    str(session_id),
                    user_id,
                    result.model_dump(mode="json"),
                )
        return result

    async def get_profile(self, user_id: str) -> AccountMeResponse:
        row = await self._fetchrow("select * from public.profiles where id = $1::uuid", user_id)
        if row is None:
            return AccountMeResponse(id=user_id)
        return AccountMeResponse(
            id=row["id"],
            email=row["email"],
            display_name=row["display_name"],
            avatar_url=row["avatar_url"],
            provider=row["provider"],
        )

    async def list_orders(self, user_id: str) -> list[AccountOrderResponse]:
        rows = await self._fetch(
            """
            select * from public.orders
            where user_id = $1::uuid
            order by created_at desc
            """,
            user_id,
        )
        return [
            AccountOrderResponse(
                id=row["id"],
                payment_id=row["payment_id"],
                product_code=row["product_code"],
                order_name=row["order_name"],
                amount_krw=row["amount_krw"],
                currency=row["currency"],
                status=row["status"],
                paid_at=_iso(row["paid_at"]),
                created_at=_iso(row["created_at"]),
            )
            for row in rows
        ]

    async def list_readings(self, user_id: str) -> list[AccountReadingResponse]:
        rows = await self._fetch(
            """
            select id, status, reading_style, order_id, final_result, created_at, updated_at
            from public.reading_sessions
            where user_id = $1::uuid
            order by created_at desc
            """,
            user_id,
        )
        return [
            AccountReadingResponse(
                id=row["id"],
                status=row["status"],
                reading_style=row["reading_style"],
                order_id=row["order_id"],
                created_at=_iso(row["created_at"]),
                updated_at=_iso(row["updated_at"]),
                has_final_result=row["final_result"] is not None,
            )
            for row in rows
        ]

    async def _fetchrow(self, query: str, *args: Any) -> Any:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def _fetch(self, query: str, *args: Any) -> list[Any]:
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def _fetchval(self, query: str, *args: Any) -> Any:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def _execute(self, query: str, *args: Any) -> str:
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)


def get_reading_repository(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ReadingRepository:
    if settings.local_demo_enabled:
        repo = getattr(request.app.state, "demo_reading_repository", None)
        if repo is None:
            repo = InMemoryDemoReadingRepository(settings)
            request.app.state.demo_reading_repository = repo
        return repo
    return PostgresReadingRepository(get_db_pool(request))


def _session_response(row: Any) -> ReadingSessionResponse:
    fixed_questions = _json(row["fixed_questions"])
    custom_questions = _json(row["custom_questions"])
    final_result = _json(row["final_result"])
    initial_profile = InitialProfile.model_validate(_json(row["initial_profile"]))
    return ReadingSessionResponse(
        id=row["id"],
        user_id=row["user_id"],
        order_id=row["order_id"],
        status=row["status"],
        reading_style=ReadingStyle(row["reading_style"]),
        initial_profile=initial_profile,
        saju=SajuData.model_validate(fixed_questions["saju"]) if isinstance(fixed_questions, dict) and fixed_questions.get("saju") else None,
        category=ConcernCategory(fixed_questions["category"]) if isinstance(fixed_questions, dict) and fixed_questions.get("category") else None,
        category_label=fixed_questions.get("category_label") if isinstance(fixed_questions, dict) else None,
        fixed_questions=[
            DiagnosticQuestion.model_validate(question)
            for question in fixed_questions.get("questions", [])
        ]
        if isinstance(fixed_questions, dict)
        else None,
        fixed_answers=_question_answers(row["fixed_answers"]),
        custom_questions=[
            DiagnosticQuestion.model_validate(question)
            for question in custom_questions.get("questions", [])
        ]
        if isinstance(custom_questions, dict)
        else None,
        custom_answers=_question_answers(row["custom_answers"]),
        final_result=_final_result_response(final_result) if final_result else None,
        created_at=_iso(row["created_at"]),
        updated_at=_iso(row["updated_at"]),
    )


def _question_answers(value: Any) -> Any:
    from app.schemas.saju import QuestionAnswer

    raw = _json(value)
    if raw is None:
        return None
    return [QuestionAnswer.model_validate(item) for item in raw]


def _final_result_response(value: Any) -> FinalReadingResponse:
    return FinalReadingResponse.model_validate(_json(value))


def _order_record(row: Any) -> OrderRecord:
    return OrderRecord(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        session_id=str(row["session_id"]) if row["session_id"] else None,
        product_code=row["product_code"],
        payment_id=row["payment_id"],
        order_name=row["order_name"],
        amount_krw=row["amount_krw"],
        currency=row["currency"],
        status=row["status"],
    )


def _checkout_response(row: Any, store_id: str, channel_key: str, webhook_url: str) -> CheckoutResponse:
    return CheckoutResponse(
        order_id=row["id"],
        payment_id=row["payment_id"],
        store_id=store_id,
        channel_key=channel_key,
        order_name=row["order_name"],
        total_amount=row["amount_krw"],
        currency=row["currency"],
        notice_urls=[webhook_url] if webhook_url else [],
    )


def _not_found_checkout() -> CheckoutResponse:
    raise LookupError("Reading session not found")


async def _insert_payment_event(conn: Any, webhook_id: str | None, payment_id: str, event_type: str | None, raw_event: dict[str, Any] | None) -> None:
    if not webhook_id:
        return
    await conn.execute(
        """
        insert into public.payment_events(webhook_id, payment_id, event_type, raw_event)
        values($1, $2, $3, $4::jsonb)
        on conflict(webhook_id) do nothing
        """,
        webhook_id,
        payment_id,
        event_type or "unknown",
        raw_event or {},
    )


def _json(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
