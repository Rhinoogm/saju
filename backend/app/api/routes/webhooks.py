from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from portone_server_sdk.webhook import WebhookVerificationError

from app.config import Settings, get_settings
from app.services.payment_reconciliation import reconcile_payment
from app.services.portone import PortOnePaymentClient, verify_webhook, webhook_event_type, webhook_payment_id
from app.services.reading_repository import ReadingRepository, get_reading_repository

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/portone", response_model=None)
async def portone_webhook(
    request: Request,
    repo: ReadingRepository = Depends(get_reading_repository),
    settings: Settings = Depends(get_settings),
) -> Any:
    if not settings.portone_webhook_secret:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": "Webhook secret is missing"})

    raw_body = await request.body()
    payload = raw_body.decode("utf-8")
    headers = dict(request.headers)
    try:
        event = verify_webhook(settings.portone_webhook_secret, payload, headers)
    except WebhookVerificationError as exc:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": exc.message or "Invalid webhook signature"})

    payment_id = webhook_payment_id(event)
    event_type = webhook_event_type(event)
    webhook_id = headers.get("webhook-id") or headers.get("x-portone-webhook-id")
    raw_event = _parse_raw_event(payload)
    if not payment_id:
        return {"status": "ignored"}

    if webhook_id:
        inserted = await repo.record_webhook_event_once(
            webhook_id=webhook_id,
            payment_id=payment_id,
            event_type=event_type,
            raw_event=raw_event,
        )
        if not inserted:
            return {"status": "duplicate"}

    order = await repo.get_order_by_payment_id(payment_id)
    if order is None:
        return {"status": "unknown_order"}

    if not settings.portone_api_secret:
        return {"status": "missing_api_secret"}

    try:
        payment = await PortOnePaymentClient(
            api_secret=settings.portone_api_secret,
            store_id=settings.portone_store_id,
        ).get_payment(payment_id)
    except Exception:
        return {"status": "payment_lookup_failed"}

    await reconcile_payment(
        repo=repo,
        order=order,
        payment=payment,
        webhook_id=webhook_id,
        event_type=event_type,
        raw_event=raw_event,
    )
    return {"status": "ok"}


def _parse_raw_event(payload: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return {"raw": payload}
    return value if isinstance(value, dict) else {"raw": value}
