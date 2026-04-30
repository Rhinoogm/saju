from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.portone import PortOnePayment
from app.services.reading_repository import OrderRecord, ReadingRepository


@dataclass(frozen=True)
class ReconciliationResult:
    ok: bool
    status: str
    reason: str | None = None


async def reconcile_payment(
    *,
    repo: ReadingRepository,
    order: OrderRecord,
    payment: PortOnePayment,
    webhook_id: str | None = None,
    event_type: str | None = None,
    raw_event: dict[str, Any] | None = None,
) -> ReconciliationResult:
    failure_reason = _payment_failure_reason(order, payment)
    if failure_reason is not None:
        await repo.mark_payment_verification_failed(
            order=order,
            reason=failure_reason,
            payment=payment,
            webhook_id=webhook_id,
            event_type=event_type,
            raw_event=raw_event,
        )
        return ReconciliationResult(ok=False, status="verification_failed", reason=failure_reason)

    await repo.mark_payment_verified(
        order=order,
        payment=payment,
        webhook_id=webhook_id,
        event_type=event_type,
        raw_event=raw_event,
    )
    return ReconciliationResult(ok=True, status="paid")


def _payment_failure_reason(order: OrderRecord, payment: PortOnePayment) -> str | None:
    if payment.payment_id != order.payment_id:
        return "payment_id mismatch"
    if payment.status != "PAID":
        return f"payment is not paid: {payment.status}"
    if payment.currency != order.currency:
        return f"currency mismatch: expected {order.currency}, got {payment.currency}"
    if payment.amount_total != order.amount_krw:
        return f"amount mismatch: expected {order.amount_krw}, got {payment.amount_total}"
    if payment.amount_paid not in (0, order.amount_krw):
        return f"paid amount mismatch: expected {order.amount_krw}, got {payment.amount_paid}"
    return None
