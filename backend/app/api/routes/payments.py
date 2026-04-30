from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.schemas.saju import CheckoutRequest, CheckoutResponse, PaymentCompleteRequest, PaymentCompleteResponse
from app.services.payment_reconciliation import reconcile_payment
from app.services.portone import PortOnePayment, PortOnePaymentClient
from app.services.reading_repository import ReadingRepository, get_reading_repository
from app.services.supabase_auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
    settings: Settings = Depends(get_settings),
) -> CheckoutResponse:
    if not settings.local_demo_enabled:
        _require_portone_public_config(settings)
    product = await repo.get_product(payload.product_code)
    if product is None or not product.active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Product is not available")
    if product.currency != "KRW":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported product currency")
    payment_id = f"saju_{uuid4().hex}"
    try:
        return await repo.create_checkout(
            user_id=current_user.id,
            session_id=payload.session_id,
            product_code=product.code,
            payment_id=payment_id,
            store_id=settings.portone_store_id or "store-local-demo",
            channel_key=settings.portone_channel_key or "channel-local-demo",
            order_name=product.name,
            amount_krw=product.amount_krw,
            webhook_url=settings.portone_webhook_url,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/complete", response_model=PaymentCompleteResponse)
async def complete_payment(
    payload: PaymentCompleteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
    settings: Settings = Depends(get_settings),
) -> PaymentCompleteResponse:
    if not settings.local_demo_enabled:
        _require_portone_secret_config(settings)
    order = await repo.get_order_by_payment_id(payload.payment_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if settings.local_demo_enabled:
        payment = PortOnePayment(
            payment_id=order.payment_id,
            status="PAID",
            amount_total=order.amount_krw,
            amount_paid=order.amount_krw,
            currency=order.currency,
            order_name=order.order_name,
            transaction_id=f"demo_{order.payment_id}",
            raw={"mode": "local_demo", "payment_id": order.payment_id},
        )
    else:
        payment_client = PortOnePaymentClient(api_secret=settings.portone_api_secret, store_id=settings.portone_store_id)
        try:
            payment = await payment_client.get_payment(payload.payment_id)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not verify payment") from exc

    result = await reconcile_payment(repo=repo, order=order, payment=payment)
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.reason or "Payment verification failed")
    return PaymentCompleteResponse(
        order_id=order.id,
        session_id=order.session_id,
        payment_id=order.payment_id,
        status=result.status,
        credit_status="available",
    )


def _require_portone_public_config(settings: Settings) -> None:
    if not settings.portone_store_id or not settings.portone_channel_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="PortOne public config is missing")


def _require_portone_secret_config(settings: Settings) -> None:
    _require_portone_public_config(settings)
    if not settings.portone_api_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="PortOne API secret is missing")
