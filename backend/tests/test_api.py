import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes import payments as payments_route
from app.api.routes import webhooks as webhooks_route
from app.api.routes.reading_sessions import get_llm_provider
from app.config import get_settings
from app.main import create_app
from app.schemas.saju import (
    AccountMeResponse,
    AccountOrderResponse,
    AccountReadingResponse,
    CheckoutResponse,
    ConcernCategory,
    FinalReadingResponse,
    InitialProfile,
    ReadingSessionCreateRequest,
    ReadingSessionResponse,
    ReadingSessionStatus,
    ReadingStyle,
)
from app.services.llm.base import LLMResponse, LLMTimeoutError
from app.services.portone import PortOnePayment
from app.services.reading_repository import OrderRecord, ProductRecord, ReadingRepository, get_reading_repository
from app.services.supabase_auth import CurrentUser, get_current_user

USER_ID = "11111111-1111-1111-1111-111111111111"
OTHER_USER_ID = "22222222-2222-2222-2222-222222222222"
LONG_DETAIL_SUFFIX = " 이 문장은 검증 기준을 채우기 위해 충분한 길이의 설명을 덧붙이며, 사용자가 실제 선택 기준을 차분히 확인하도록 돕는 맥락을 유지합니다."

CUSTOM_QUESTION_PAYLOAD = {
    "questions": [
        {
            "id": "q5",
            "type": "single_choice",
            "text": "지금 선택에서 가장 먼저 확인하고 싶은 기준은 무엇인가요?",
            "options": [
                {"id": "A", "label": "성장 가능성"},
                {"id": "B", "label": "안정적인 보상"},
                {"id": "C", "label": "관계의 편안함"},
                {"id": "D", "label": "회복 가능한 리듬"},
            ],
            "intent_signal": "우선순위",
        },
        {
            "id": "q6",
            "type": "single_choice",
            "text": "걱정이 줄어들려면 어떤 변화가 먼저 보여야 할까요?",
            "options": [
                {"id": "A", "label": "선택지가 늘어남"},
                {"id": "B", "label": "일상이 가벼워짐"},
                {"id": "C", "label": "인정받는 느낌"},
                {"id": "D", "label": "몸의 피로 감소"},
            ],
            "intent_signal": "불안 완화",
        },
        {
            "id": "q7",
            "type": "single_choice",
            "text": "이번 결정에서 포기하기 어려운 조건은 무엇인가요?",
            "options": [
                {"id": "A", "label": "돈"},
                {"id": "B", "label": "성장"},
                {"id": "C", "label": "시간"},
                {"id": "D", "label": "사람"},
            ],
            "intent_signal": "핵심 조건",
        },
    ]
}

FINAL_PAYLOAD = {
    "reading_title": "전환 앞에 선 마음의 나침반",
    "core_message": "서두르지 말고 조건이 맞을 때 움직이는 편이 좋습니다.",
    "situation_mirror": {
        "title": "지금 마음",
        "headline": "성장 욕구와 안정 확인이 함께 켜져 있습니다.",
        "summary": "지금의 고민은 단순한 도피보다 조건을 확인하려는 마음에 가깝습니다.",
        "detail": "새로운 일을 살피는 마음에는 가능성을 현실로 확인하려는 태도가 있습니다. 안정적인 보상과 회복 가능한 리듬을 함께 보는 흐름은 성장과 안전을 동시에 원한다는 신호입니다. 그래서 지금은 떠날지 말지를 급하게 정하기보다 어떤 환경에서 능력이 살아나는지 분리해 보는 일이 중요합니다. 이 기준이 정리되면 실제 제안 앞에서도 덜 흔들릴 수 있습니다." + LONG_DETAIL_SUFFIX,
    },
    "saju_insight": {
        "title": "명식 흐름",
        "headline": "자라려는 힘과 현실을 재는 힘이 동시에 움직입니다.",
        "summary": "명식에는 변화 욕구와 안정 기준을 함께 확인하려는 흐름이 보입니다.",
        "detail": "명식의 흐름은 더 넓은 역할을 탐색하려는 마음과 감당할 조건을 확인하려는 마음이 같이 움직입니다. 이 고민은 변덕이라기보다 성장할 자리와 버틸 조건을 재는 과정입니다. 준비된 이동에는 힘이 실리지만 감정만 앞선 선택에는 부담이 남을 수 있습니다. 변화 자체보다 환경과 조건을 나누어 보는 편이 판단을 돕습니다." + LONG_DETAIL_SUFFIX,
    },
    "clear_solution": {
        "title": "선택 기준",
        "headline": "지원은 시작하되 퇴사는 조건표가 나온 뒤가 좋습니다.",
        "summary": "지금은 선택지를 꺼내고 조건표로 움직일 기준을 세울 때입니다.",
        "detail": "지금 해야 할 일은 회사를 바로 떠나는 것이 아니라 선택지를 실제로 꺼내 놓는 것입니다. 성장 가능성, 보상, 회복 리듬을 표로 나누고 두 가지 이상 맞는 곳만 진지하게 보세요. 제안이 오기 전까지 현재 자리를 협상 카드로 남겨두면 판단의 폭이 넓어집니다. 이번 선택은 용기보다 기준을 확인하는 일에 가깝습니다." + LONG_DETAIL_SUFFIX,
    },
    "saju_vibe": {
        "title": "타고난 결",
        "headline": "방향을 정하면 꾸준히 뿌리내리는 힘이 있습니다.",
        "summary": "당신의 매력은 빠른 변화보다 오래 가는 기준에 있습니다.",
        "detail": "당신은 빠르게 피어나는 화려함보다 방향을 정하면 꾸준히 뿌리내리는 힘이 강합니다. 처음에는 조심스러워 보여도 기준이 잡히면 쉽게 흔들리지 않습니다. 납득되는 기준을 찾을 때 말과 행동의 결이 선명해집니다. 그래서 계속 속도를 재촉하는 곳보다 준비한 만큼 결과를 쌓을 수 있는 환경이 잘 맞습니다." + LONG_DETAIL_SUFFIX,
    },
    "secret_talent": {
        "title": "숨은 강점",
        "headline": "망설임은 리스크를 먼저 보는 기획력입니다.",
        "summary": "지금의 망설임은 우유부단함보다 점검 능력에 가깝습니다.",
        "detail": "스스로는 우유부단하다고 느낄 수 있지만 중요한 선택을 대충 넘기지 않는 감각이 있습니다. 남들이 보기에는 결정을 미루는 것처럼 보여도 실제로는 손해 볼 지점과 오래 버티기 어려운 조건을 먼저 감지합니다. 이 힘을 걱정으로만 두면 불안이 커지지만 조건표와 일정으로 바꾸면 설득력 있는 판단 기준이 됩니다." + LONG_DETAIL_SUFFIX,
    },
    "answer_signals": ["조건 개선 욕구", "인정 욕구", "안전 확인 욕구"],
    "answer_signal_summary": "조건 개선 욕구와 인정 욕구, 안전 확인 욕구가 함께 보여 기준 확인이 필요합니다.",
    "saju_basis": ["월주 흐름에서 변화 압박이 보입니다.", "오행 균형상 표현 욕구가 중요합니다.", "대운 흐름은 준비된 이동에 유리합니다."],
    "timing_points": ["2주는 조건표를 만드세요.", "한 달 안에는 지원 기준을 나누세요.", "1-3개월 사이에는 실제 제안을 비교하세요."],
    "luck_recipe": [
        {"category": "컬러", "item": "딥 민트", "reason": "차분한 색이 판단의 속도를 낮추는 데 도움이 됩니다."},
        {"category": "음식", "item": "보리차", "reason": "따뜻한 차가 긴장을 낮추고 기준을 다시 보게 돕습니다."},
        {"category": "습관", "item": "조건표 쓰기", "reason": "걱정을 눈에 보이는 선택 기준으로 바꾸는 일이 필요합니다."},
        {"category": "아이템", "item": "체크 노트", "reason": "현실 조건을 밖으로 꺼낼수록 판단이 쉬워집니다."},
    ],
    "re_engagement_hook": {"title": "다음 질문", "body": "다음에는 재물 흐름과 협상 기준을 함께 보면 선택이 더 선명해질 수 있습니다. 지금 정리한 조건표는 다음 결정을 더 구체적으로 만드는 단서가 됩니다."},
    "caution": "이 리딩은 확정 예언이 아니라 자기 이해와 선택을 돕는 참고 자료입니다.",
}


class MockProvider:
    def __init__(self, *, fail_final: bool = False) -> None:
        self.fail_final = fail_final
        self.calls: list[str] = []

    async def generate(self, *, system: str, prompt: str, schema: dict, schema_name: str, max_output_tokens: int | None = None) -> LLMResponse:
        self.calls.append(schema_name)
        if self.fail_final and schema_name == "FinalReadingOutput":
            raise LLMTimeoutError("timeout")
        payload = CUSTOM_QUESTION_PAYLOAD if schema_name == "QuestionGenerationOutput" else FINAL_PAYLOAD
        return LLMResponse(content=json.dumps(payload, ensure_ascii=False), model="test-model", provider="mock")


class FakeRepository(ReadingRepository):
    def __init__(self) -> None:
        self.products = {
            "SAJU_FULL_READING": ProductRecord("SAJU_FULL_READING", "사주 심화 리딩 1회권", 9900, "KRW", True)
        }
        self.sessions: dict[str, ReadingSessionResponse] = {}
        self.orders: dict[str, dict] = {}
        self.credits: dict[str, str] = {}
        self.webhook_ids: set[str] = set()

    async def create_session(self, user_id: str, payload: ReadingSessionCreateRequest) -> ReadingSessionResponse:
        session = ReadingSessionResponse(
            id=uuid4(),
            user_id=UUID(user_id),
            status=ReadingSessionStatus.payment_required,
            reading_style=payload.reading_style,
            initial_profile=InitialProfile.model_validate(payload.model_dump()),
        )
        self.sessions[str(session.id)] = session
        return session

    async def get_session(self, user_id: str, session_id) -> ReadingSessionResponse | None:
        session = self.sessions.get(str(session_id))
        if session is None or str(session.user_id) != user_id:
            return None
        return session

    async def get_session_for_update(self, user_id: str, session_id):
        return None

    async def get_product(self, product_code: str) -> ProductRecord | None:
        return self.products.get(product_code)

    async def create_checkout(self, *, user_id: str, session_id, product_code: str, payment_id: str, store_id: str, channel_key: str, order_name: str, amount_krw: int, webhook_url: str) -> CheckoutResponse:
        session = await self.get_session(user_id, session_id)
        if session is None:
            raise LookupError("not found")
        if session.order_id:
            for order in self.orders.values():
                if order["id"] == str(session.order_id) and order["status"] in {"ready", "payment_requested"}:
                    return CheckoutResponse(order_id=order["id"], payment_id=order["payment_id"], store_id=store_id, channel_key=channel_key, order_name=order["order_name"], total_amount=order["amount_krw"], currency=order["currency"], notice_urls=[webhook_url])
                if order["id"] == str(session.order_id) and order["status"] == "paid":
                    raise RuntimeError("Reading session already has a paid order")
        order_id = str(uuid4())
        self.orders[payment_id] = {
            "id": order_id,
            "user_id": user_id,
            "session_id": str(session.id),
            "product_code": product_code,
            "payment_id": payment_id,
            "order_name": order_name,
            "amount_krw": amount_krw,
            "currency": "KRW",
            "status": "payment_requested",
        }
        session.order_id = UUID(order_id)
        return CheckoutResponse(order_id=order_id, payment_id=payment_id, store_id=store_id, channel_key=channel_key, order_name=order_name, total_amount=amount_krw, currency="KRW", notice_urls=[webhook_url])

    async def get_order_by_payment_id(self, payment_id: str) -> OrderRecord | None:
        order = self.orders.get(payment_id)
        if not order:
            return None
        return OrderRecord(**order)

    async def mark_payment_verified(self, *, order: OrderRecord, payment: PortOnePayment, webhook_id: str | None = None, event_type: str | None = None, raw_event: dict | None = None) -> None:
        self.orders[order.payment_id]["status"] = "paid"
        self.credits[order.id] = "available"
        if order.session_id:
            self.sessions[order.session_id].status = ReadingSessionStatus.paid

    async def mark_payment_verification_failed(self, *, order: OrderRecord, reason: str, payment: PortOnePayment | None = None, webhook_id: str | None = None, event_type: str | None = None, raw_event: dict | None = None) -> None:
        self.orders[order.payment_id]["status"] = "verification_failed"
        self.orders[order.payment_id]["failure_reason"] = reason

    async def record_webhook_event_once(self, *, webhook_id: str, payment_id: str, event_type: str, raw_event: dict) -> bool:
        if webhook_id in self.webhook_ids:
            return False
        self.webhook_ids.add(webhook_id)
        return True

    async def has_available_credit(self, user_id: str, session_id) -> bool:
        session = await self.get_session(user_id, session_id)
        return bool(session and session.order_id and self.credits.get(str(session.order_id)) == "available")

    async def save_fixed_questions(self, user_id: str, session_id, result) -> None:
        session = self.sessions[str(session_id)]
        session.saju = result.saju
        session.category = result.category
        session.category_label = result.category_label
        session.fixed_questions = result.questions
        session.status = ReadingSessionStatus.fixed_questions_ready

    async def save_fixed_answers(self, user_id: str, session_id, payload) -> None:
        self.sessions[str(session_id)].fixed_answers = payload.fixed_answers

    async def save_custom_questions(self, user_id: str, session_id, result) -> None:
        session = self.sessions[str(session_id)]
        session.custom_questions = result.questions
        session.status = ReadingSessionStatus.custom_questions_ready

    async def save_custom_answers(self, user_id: str, session_id, payload) -> None:
        self.sessions[str(session_id)].custom_answers = payload.custom_answers

    async def save_final_result_and_consume_credit(self, user_id: str, session_id, result: FinalReadingResponse) -> FinalReadingResponse:
        session = self.sessions[str(session_id)]
        if session.final_result:
            return session.final_result
        if not session.order_id or self.credits.get(str(session.order_id)) != "available":
            raise RuntimeError("No available reading credit")
        self.credits[str(session.order_id)] = "consumed"
        session.final_result = result
        session.status = ReadingSessionStatus.final_ready
        return result

    async def get_profile(self, user_id: str):
        return AccountMeResponse(id=user_id, email="user@example.com")

    async def list_orders(self, user_id: str):
        return [AccountOrderResponse(id=o["id"], payment_id=o["payment_id"], product_code=o["product_code"], order_name=o["order_name"], amount_krw=o["amount_krw"], currency=o["currency"], status=o["status"]) for o in self.orders.values() if o["user_id"] == user_id]

    async def list_readings(self, user_id: str):
        return [AccountReadingResponse(id=s.id, status=s.status, reading_style=s.reading_style, order_id=s.order_id, has_final_result=s.final_result is not None) for s in self.sessions.values() if str(s.user_id) == user_id]


class FakePortOneClient:
    payment: PortOnePayment

    def __init__(self, *, api_secret: str, store_id: str) -> None:
        pass

    async def get_payment(self, payment_id: str) -> PortOnePayment:
        return self.payment


@pytest.fixture
def repo(monkeypatch) -> FakeRepository:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("PORTONE_STORE_ID", "store-test")
    monkeypatch.setenv("PORTONE_CHANNEL_KEY", "channel-test")
    monkeypatch.setenv("PORTONE_API_SECRET", "secret")
    monkeypatch.setenv("PORTONE_WEBHOOK_SECRET", "whsec")
    monkeypatch.setenv("PORTONE_WEBHOOK_URL", "https://api.example.com/api/webhooks/portone")
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    return FakeRepository()


@pytest.fixture
def client(repo: FakeRepository):
    app = create_app()
    app.state.llm_rate_limiter = None
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=USER_ID, email="user@example.com")
    app.dependency_overrides[get_reading_repository] = lambda: repo
    app.dependency_overrides[get_llm_provider] = lambda: MockProvider()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def initial_payload() -> dict:
    return {
        "name": "홍길동",
        "gender": "male",
        "initial_concern": "올해 이직을 해도 될까요?",
        "reading_style": "traditional",
        "birth": {
            "calendar_type": "solar",
            "year": 1990,
            "month": 10,
            "day": 10,
            "hour": 14,
            "minute": 30,
            "city": "Seoul",
        },
    }


def fixed_answers() -> list[dict]:
    return [
        {"question_id": "q1", "question": "q1 text", "answer": "성장", "selected_option_ids": ["A"]},
        {"question_id": "q2", "question": "q2 text", "answer": "준비", "selected_option_ids": ["B"]},
        {"question_id": "q3", "question": "q3 text", "answer": "안정", "selected_option_ids": ["C"]},
    ]


def custom_answers() -> list[dict]:
    return [
        {"question_id": "q5", "question": "q5 text", "answer": "성장", "selected_option_ids": ["A"]},
        {"question_id": "q6", "question": "q6 text", "answer": "선택지", "selected_option_ids": ["A"]},
        {"question_id": "q7", "question": "q7 text", "answer": "돈", "selected_option_ids": ["A"]},
    ]


def create_paid_session(client: TestClient, repo: FakeRepository) -> tuple[str, str]:
    session_id = client.post("/api/reading-sessions", json=initial_payload()).json()["id"]
    checkout = client.post("/api/payments/checkout", json={"session_id": session_id, "product_code": "SAJU_FULL_READING"}).json()
    payment_id = checkout["payment_id"]
    FakePortOneClient.payment = PortOnePayment(payment_id=payment_id, status="PAID", amount_total=9900, amount_paid=9900, currency="KRW", order_name="사주 심화 리딩 1회권", transaction_id="tx_test")
    return session_id, payment_id


def test_auth_required_returns_401(repo: FakeRepository) -> None:
    app = create_app()
    app.dependency_overrides[get_reading_repository] = lambda: repo
    with TestClient(app) as client:
        response = client.post("/api/reading-sessions", json=initial_payload())
    assert response.status_code == 401


def test_local_demo_bypasses_auth_payment_and_database(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_DEMO_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    app = create_app()
    headers = {"Authorization": "Bearer local-demo-token"}
    with TestClient(app) as client:
        session = client.post("/api/reading-sessions", json=initial_payload(), headers=headers).json()
        checkout = client.post("/api/payments/checkout", json={"session_id": session["id"]}, headers=headers).json()
        payment = client.post("/api/payments/complete", json={"payment_id": checkout["payment_id"]}, headers=headers)
        questions = client.post(f"/api/reading-sessions/{session['id']}/generate-questions", headers=headers)

    assert payment.status_code == 200
    assert payment.json()["status"] == "paid"
    assert questions.status_code == 200
    get_settings.cache_clear()


def test_unpaid_session_is_payment_required(client: TestClient) -> None:
    session_id = client.post("/api/reading-sessions", json=initial_payload()).json()["id"]
    response = client.post(f"/api/reading-sessions/{session_id}/generate-questions")
    assert response.status_code == 402


def test_checkout_is_idempotent_for_double_click(client: TestClient) -> None:
    session_id = client.post("/api/reading-sessions", json=initial_payload()).json()["id"]
    first = client.post("/api/payments/checkout", json={"session_id": session_id}).json()
    second = client.post("/api/payments/checkout", json={"session_id": session_id}).json()
    assert first["payment_id"] == second["payment_id"]


def test_complete_verifies_portone_payment_and_grants_credit(client: TestClient, monkeypatch, repo: FakeRepository) -> None:
    monkeypatch.setattr(payments_route, "PortOnePaymentClient", FakePortOneClient)
    session_id, payment_id = create_paid_session(client, repo)
    response = client.post("/api/payments/complete", json={"payment_id": payment_id})
    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    assert repo.credits[str(repo.sessions[session_id].order_id)] == "available"


def test_checkout_after_paid_order_is_conflict(client: TestClient, monkeypatch, repo: FakeRepository) -> None:
    monkeypatch.setattr(payments_route, "PortOnePaymentClient", FakePortOneClient)
    session_id, payment_id = create_paid_session(client, repo)
    assert client.post("/api/payments/complete", json={"payment_id": payment_id}).status_code == 200

    response = client.post("/api/payments/checkout", json={"session_id": session_id})

    assert response.status_code == 409


def test_amount_mismatch_does_not_grant_credit(client: TestClient, monkeypatch, repo: FakeRepository) -> None:
    monkeypatch.setattr(payments_route, "PortOnePaymentClient", FakePortOneClient)
    session_id = client.post("/api/reading-sessions", json=initial_payload()).json()["id"]
    payment_id = client.post("/api/payments/checkout", json={"session_id": session_id}).json()["payment_id"]
    FakePortOneClient.payment = PortOnePayment(payment_id=payment_id, status="PAID", amount_total=100, amount_paid=100, currency="KRW", order_name="bad")
    response = client.post("/api/payments/complete", json={"payment_id": payment_id})
    assert response.status_code == 409
    assert not repo.credits
    assert repo.orders[payment_id]["status"] == "verification_failed"


def test_user_session_ownership_is_forbidden(client: TestClient, repo: FakeRepository) -> None:
    other = ReadingSessionResponse(
        id=uuid4(),
        user_id=UUID(OTHER_USER_ID),
        status=ReadingSessionStatus.payment_required,
        reading_style=ReadingStyle.traditional,
        initial_profile=InitialProfile.model_validate(initial_payload()),
    )
    repo.sessions[str(other.id)] = other
    response = client.get(f"/api/reading-sessions/{other.id}")
    assert response.status_code == 403


def test_webhook_idempotency(client: TestClient, monkeypatch, repo: FakeRepository) -> None:
    monkeypatch.setattr(webhooks_route, "verify_webhook", lambda secret, payload, headers: type("Event", (), {"data": type("Data", (), {"payment_id": "p", "transaction_id": "tx"})()})())
    first = client.post("/api/webhooks/portone", content=b'{"type":"paid"}', headers={"webhook-id": "evt_1"})
    second = client.post("/api/webhooks/portone", content=b'{"type":"paid"}', headers={"webhook-id": "evt_1"})
    assert first.status_code == 200
    assert second.json()["status"] == "duplicate"


def test_final_reading_consumes_credit_after_success(client: TestClient, monkeypatch, repo: FakeRepository) -> None:
    monkeypatch.setattr(payments_route, "PortOnePaymentClient", FakePortOneClient)
    session_id, payment_id = create_paid_session(client, repo)
    assert client.post("/api/payments/complete", json={"payment_id": payment_id}).status_code == 200
    assert client.post(f"/api/reading-sessions/{session_id}/generate-questions").status_code == 200
    assert client.put(f"/api/reading-sessions/{session_id}/fixed-answers", json={"fixed_answers": fixed_answers()}).status_code == 200
    assert client.post(f"/api/reading-sessions/{session_id}/generate-custom-questions").status_code == 200
    assert client.put(f"/api/reading-sessions/{session_id}/custom-answers", json={"custom_answers": custom_answers()}).status_code == 200
    response = client.post(f"/api/reading-sessions/{session_id}/final-reading")
    assert response.status_code == 200
    assert repo.credits[str(repo.sessions[session_id].order_id)] == "consumed"


def test_llm_failure_does_not_consume_credit(client: TestClient, monkeypatch, repo: FakeRepository) -> None:
    monkeypatch.setattr(payments_route, "PortOnePaymentClient", FakePortOneClient)
    session_id, payment_id = create_paid_session(client, repo)
    assert client.post("/api/payments/complete", json={"payment_id": payment_id}).status_code == 200
    assert client.post(f"/api/reading-sessions/{session_id}/generate-questions").status_code == 200
    assert client.put(f"/api/reading-sessions/{session_id}/fixed-answers", json={"fixed_answers": fixed_answers()}).status_code == 200
    assert client.post(f"/api/reading-sessions/{session_id}/generate-custom-questions").status_code == 200
    assert client.put(f"/api/reading-sessions/{session_id}/custom-answers", json={"custom_answers": custom_answers()}).status_code == 200
    client.app.dependency_overrides[get_llm_provider] = lambda: MockProvider(fail_final=True)
    response = client.post(f"/api/reading-sessions/{session_id}/final-reading")
    assert response.status_code == 504
    assert repo.credits[str(repo.sessions[session_id].order_id)] == "available"
