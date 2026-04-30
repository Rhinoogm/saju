from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from portone_server_sdk import PortOneClient
from portone_server_sdk import webhook as portone_webhook
from portone_server_sdk.webhook import WebhookVerificationError


@dataclass(frozen=True)
class PortOnePayment:
    payment_id: str
    status: str
    amount_total: int
    amount_paid: int
    currency: str
    order_name: str
    transaction_id: str | None = None
    paid_at: str | None = None
    raw: dict[str, Any] | None = None

    def as_raw(self) -> dict[str, Any]:
        if self.raw is not None:
            return self.raw
        return asdict(self)


class PortOnePaymentClient:
    def __init__(self, *, api_secret: str, store_id: str) -> None:
        self._client = PortOneClient(secret=api_secret, store_id=store_id or None)

    async def get_payment(self, payment_id: str) -> PortOnePayment:
        payment = await self._client.payment.get_payment_async(payment_id=payment_id)
        return normalize_portone_payment(payment)


def normalize_portone_payment(payment: Any) -> PortOnePayment:
    raw = _to_dict(payment)
    payment_id = _read(payment, raw, "id") or _read(payment, raw, "payment_id")
    amount = _read(payment, raw, "amount") or {}
    amount_raw = _to_dict(amount)
    amount_total = _read(amount, amount_raw, "total")
    amount_paid = _read(amount, amount_raw, "paid")
    status = _status_from_payment(payment, raw)

    if not isinstance(payment_id, str):
        raise ValueError("PortOne payment has no payment id")
    if not isinstance(amount_total, int):
        raise ValueError("PortOne payment has no total amount")
    if not isinstance(amount_paid, int):
        amount_paid = amount_total if status == "PAID" else 0

    currency = _read(payment, raw, "currency")
    order_name = _read(payment, raw, "order_name")
    transaction_id = _read(payment, raw, "transaction_id")
    paid_at = _read(payment, raw, "paid_at")
    return PortOnePayment(
        payment_id=payment_id,
        status=status,
        amount_total=amount_total,
        amount_paid=amount_paid,
        currency=currency if isinstance(currency, str) else "",
        order_name=order_name if isinstance(order_name, str) else "",
        transaction_id=transaction_id if isinstance(transaction_id, str) else None,
        paid_at=paid_at if isinstance(paid_at, str) else None,
        raw=raw,
    )


def verify_webhook(secret: str, payload: str, headers: Mapping[str, str]) -> Any:
    try:
        return portone_webhook.verify(secret, payload, headers)
    except WebhookVerificationError:
        raise


def webhook_payment_id(event: Any) -> str | None:
    raw = _to_dict(event)
    data = _read(event, raw, "data")
    data_raw = _to_dict(data)
    payment_id = _read(data, data_raw, "payment_id")
    return payment_id if isinstance(payment_id, str) else None


def webhook_transaction_id(event: Any) -> str | None:
    raw = _to_dict(event)
    data = _read(event, raw, "data")
    data_raw = _to_dict(data)
    transaction_id = _read(data, data_raw, "transaction_id")
    return transaction_id if isinstance(transaction_id, str) else None


def webhook_event_type(event: Any) -> str:
    raw = _to_dict(event)
    if isinstance(raw.get("type"), str):
        return raw["type"]
    return event.__class__.__name__


def _status_from_payment(payment: Any, raw: dict[str, Any]) -> str:
    raw_status = _read(payment, raw, "status")
    if isinstance(raw_status, str) and raw_status:
        return raw_status.upper()
    class_name = payment.__class__.__name__
    if class_name == "PaidPayment":
        return "PAID"
    if class_name in {"CancelledPayment", "PartialCancelledPayment"}:
        return "CANCELLED"
    if class_name == "FailedPayment":
        return "FAILED"
    if class_name == "VirtualAccountIssuedPayment":
        return "VIRTUAL_ACCOUNT_ISSUED"
    if class_name == "PayPendingPayment":
        return "PAY_PENDING"
    return "READY"


def _read(source: Any, raw: dict[str, Any], key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    if hasattr(source, key):
        return getattr(source, key)
    return raw.get(key)


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if isinstance(dumped, dict):
            return {key: _jsonable(item) for key, item in dumped.items()}
    if hasattr(value, "__dict__"):
        return {key: _jsonable(item) for key, item in vars(value).items() if not key.startswith("_")}
    return {}


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if hasattr(value, "__dict__"):
        return _to_dict(value)
    return str(value)
