import json

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.api.routes.saju import get_llm_provider
from app.main import app, create_app
from app.services.llm.base import LLMRateLimitError, LLMResponse
from app.services.prompt_builder import (
    FINAL_SYSTEM_PROMPT_DIRECT,
    FINAL_SYSTEM_PROMPT_EMPATHETIC,
    FINAL_SYSTEM_PROMPT_TRADITIONAL,
    FINAL_USER_PROMPT_TEMPLATE,
)
from app.services.prompt_store import PromptStore
from app.services.rate_limiter import InMemoryRateLimiter
from app.services.runtime_settings import resolve_runtime_llm_settings


QUESTION_PAYLOADS = {
    "q1": {
        "id": "q1",
        "type": "single_choice",
        "text": "이직 고민을 떠올릴 때 지금 마음을 가장 크게 차지하는 감정은 무엇인가요?",
        "options": [
            {"id": "A", "label": "잘못 선택할까 봐 커지는 불안과 초조함"},
            {"id": "B", "label": "혼자 해결하기 어렵다는 막막함과 무기력"},
            {"id": "C", "label": "꼭 더 나은 자리로 가고 싶은 간절함과 기대"},
            {"id": "D", "label": "결정을 혼자 감당해야 한다는 외로움과 부담감"},
        ],
        "intent_signal": "감정 명료화",
    },
    "q2": {
        "id": "q2",
        "type": "single_choice",
        "text": "이 고민의 결과를 바꾸는 데 가장 크게 작용할 요인은 무엇에 가깝나요?",
        "options": [
            {"id": "A", "label": "내가 세울 기준과 앞으로 쌓을 준비"},
            {"id": "B", "label": "회사와 주변 사람이 보이는 반응과 도움"},
            {"id": "C", "label": "채용 시장과 시기처럼 내가 통제하기 어려운 흐름"},
            {"id": "D", "label": "아직은 무엇이 바꿀지 잘 모르겠는 상태"},
        ],
        "intent_signal": "통제 소재",
    },
    "q3": {
        "id": "q3",
        "type": "single_choice",
        "text": "이 이직 고민 앞에서 누군가 딱 한마디를 해준다면 어떤 말이 가장 위로가 될까요?",
        "options": [
            {"id": "A", "label": "큰 문제 없이 안정적으로 지나갈 거예요."},
            {"id": "B", "label": "당신은 더 나은 조건을 선택할 자격과 능력이 있어요."},
            {"id": "C", "label": "지금 흔들리는 마음을 이해해요. 혼자가 아니에요."},
            {"id": "D", "label": "당신의 판단이 맞아요. 기준을 믿고 밀고 가세요."},
        ],
        "intent_signal": "핵심 욕구",
    },
    "q4": {
        "id": "q4",
        "type": "single_choice",
        "text": "지금 이 고민을 풀기 위해 본인에게 가장 필요한 도움은 무엇인가요?",
        "options": [
            {"id": "A", "label": "현실적으로 비교할 수 있는 방법과 계획"},
            {"id": "B", "label": "내 방향이 틀리지 않았다는 확인과 지지"},
            {"id": "C", "label": "결국 괜찮아질 거라는 희망과 긍정"},
            {"id": "D", "label": "복잡한 마음을 정리할 객관적인 시각"},
        ],
        "intent_signal": "변화 준비도",
    },
    "q5": {
        "id": "q5",
        "type": "single_choice",
        "text": "내일 아침 이 이직 고민이 사라져 있다면, 무엇이 가장 큰 이유였을까요?",
        "options": [
            {"id": "A", "label": "내가 용기를 내어 직접 움직이고 상황을 바꿨기 때문에"},
            {"id": "B", "label": "회사나 주변 사람의 반응이 달라졌기 때문에"},
            {"id": "C", "label": "시간이 지나며 걱정보다 자연스럽게 풀렸기 때문에"},
            {"id": "D", "label": "예상 밖의 기회나 도와줄 사람이 나타났기 때문에"},
        ],
        "intent_signal": "희망 해결상",
    },
}


def question_generation_payload(question_id: str) -> dict:
    return {"question": QUESTION_PAYLOADS[question_id]}


def target_question_id_from_prompt(prompt: str) -> str:
    for question_id in reversed(QUESTION_PAYLOADS):
        if f'"id":"{question_id}"' in prompt:
            return question_id
    return "q1"


FINAL_PAYLOAD = {
    "reading_title": "전환 앞에 선 마음의 나침반",
    "core_message": "이직은 서두르지 말고, 성장 조건이 맞을 때 움직이는 쪽이 맞습니다.",
    "desired_answer": "당신이 확인받고 싶었던 답은 움직여도 된다는 허락입니다. 다만 명식의 성장 욕구와 안정 기준을 함께 써야 좋은 자리로 이어집니다.",
    "saju_insight": {
        "title": "이 고민이 찾아온 이유",
        "headline": "자라려는 힘과 현실을 재는 힘이 동시에 움직입니다.",
        "summary": "명식에는 성장할 자리와 감당할 조건을 동시에 재려는 움직임이 함께 보입니다.",
        "detail": "명식에는 더 넓은 역할을 탐색하려는 흐름과 안정된 기준을 확인하려는 흐름이 함께 보입니다. 그래서 지금의 고민은 변덕이 아니라, 성장할 자리와 감당할 조건을 동시에 재는 과정입니다. 대운의 흐름도 준비된 이동에는 힘을 실어주지만, 감정만 앞선 선택에는 부담을 남깁니다. 지금 중요한 것은 변화 자체가 좋은지 나쁜지를 빨리 결론내는 일이 아니라, 어떤 환경에서 능력이 살아나고 어떤 조건에서 지치는지를 분리해서 보는 일입니다. 이 구분이 생기면 막연한 불안은 줄고, 실제 제안이 왔을 때 흔들리지 않는 판단 기준이 됩니다.",
    },
    "clear_solution": {
        "title": "지금 필요한 선택",
        "headline": "지원은 시작하되, 퇴사는 제안서와 조건표가 나온 뒤입니다.",
        "summary": "지금은 퇴사 결정보다 선택지를 꺼내 놓고, 조건표로 움직일 기준을 세울 때입니다.",
        "detail": "지금 해야 할 일은 회사를 박차고 나가는 게 아니라 선택지를 실제로 꺼내 놓는 것입니다. 성장 가능성, 보상, 회복 리듬을 표로 나누고 세 조건 중 두 개 이상 맞는 곳만 진지하게 보세요. 지원을 시작하는 것은 좋지만, 면접 과정에서 들뜬 감정만으로 현재 자리를 끊어내면 판단의 폭이 좁아집니다. 제안이 오기 전까지는 현재 자리를 협상 카드로 남겨두는 쪽이 훨씬 유리합니다. 이번 선택은 용기의 문제가 아니라 조건을 숫자와 일정으로 확인하는 문제이니, 이번 주에는 공고 5개를 비교하고 포기할 조건 3개부터 적는 것이 가장 현실적인 첫 행동입니다.",
    },
    "secret_talent": {
        "title": "강점으로 바뀌는 지점",
        "headline": "망설임은 사실 리스크를 먼저 보는 기획력입니다.",
        "summary": "지금의 망설임은 우유부단함보다 리스크를 먼저 보는 기획력에 가깝습니다.",
        "detail": "스스로는 우유부단하다고 느낄 수 있지만, 지금의 망설임은 중요한 선택을 대충 넘기지 않는 감각입니다. 남들이 보기에는 결정을 미루는 것처럼 보여도, 실제로는 손해 볼 지점과 오래 버티기 어려운 조건을 먼저 감지하고 있습니다. 이 힘을 머릿속 걱정으로만 두면 불안이 커지지만, 조건표와 일정으로 바꾸면 다음 선택을 설득력 있게 만드는 무기가 됩니다. 특히 이직처럼 돈, 성장, 체력, 관계가 한꺼번에 걸린 문제에서는 이런 점검 능력이 큰 장점입니다. 단, 검토만 반복하면 기회가 흐려지니 마감일을 정해 판단을 행동으로 옮기는 장치가 필요합니다.",
    },
    "saju_basis": ["월주 흐름에서 환경 변화 압박이 보입니다.", "오행 균형상 표현 욕구가 막히면 답답함이 커집니다.", "대운 흐름은 준비된 이동에 유리합니다."],
    "period_guidance": [
        {
            "label": "기준을 세우는 흐름",
            "saju_feature": "월주 흐름의 현실 감각이 먼저 살아나는 구간입니다.",
            "good": "조건을 숫자와 역할로 나누면 막연한 불안이 줄고 선택지가 선명해집니다.",
            "caution": "감정만 앞세워 현재 자리를 끊어내면 비교할 기준을 잃기 쉽습니다.",
        },
        {
            "label": "기회가 넓어지는 흐름",
            "saju_feature": "표현 욕구와 성장 기운이 밖으로 드러나기 쉬운 구간입니다.",
            "good": "준비한 이력과 강점을 보여주면 새로운 제안이나 역할 탐색이 자연스럽게 열립니다.",
            "caution": "좋아 보이는 말에만 반응하지 말고 보상과 회복 리듬을 반드시 확인해야 합니다.",
        },
        {
            "label": "선택을 굳히는 흐름",
            "saju_feature": "대운의 이동성이 준비된 결정을 밀어주는 구간입니다.",
            "good": "현재 자리와 새 제안을 같은 기준으로 비교하면 납득되는 결론에 가까워집니다.",
            "caution": "완벽한 확신만 기다리면 기회가 흐려지니 포기 조건을 먼저 정해야 합니다.",
        },
    ],
    "share_card": {
        "core_saju_feature": "성장 욕구와 현실 기준을 함께 쓰는 명식 흐름",
        "balancing_need": "급한 결정보다 기준을 밖으로 꺼내는 금의 기운",
        "daily_element": "작은 체크 노트",
        "daily_reason": "생각을 적어 조건으로 바꾸면 흔들리는 마음이 실제 선택 기준으로 정리됩니다.",
        "strengths": ["기준 정리", "성장 감각", "현실 판단"],
    },
    "caution": "이 리딩은 확정 예언이 아니라 자기 이해와 선택을 돕는 참고 자료입니다.",
}


class MockProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        schema_name: str,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        assert system.strip()
        assert prompt.strip()
        assert schema_name in {"QuestionGenerationOutput", "FinalReadingOutput"}
        assert schema["type"] == "object"
        self.calls.append({"system": system, "prompt": prompt, "schema_name": schema_name, "max_output_tokens": max_output_tokens})
        content = question_generation_payload(target_question_id_from_prompt(prompt)) if schema_name == "QuestionGenerationOutput" else FINAL_PAYLOAD
        return LLMResponse(
            content=json.dumps(content, ensure_ascii=False),
            model="test-model",
            provider="mock",
            raw_metadata={
                "done": True,
                "usage": {"prompt_tokens": 111, "completion_tokens": 222, "total_tokens": 333},
                "choices": [{"finish_reason": "stop"}],
                "provider_internal": {"large": True},
            },
        )


class GroqMetadataProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        schema_name: str,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        self.calls.append({"system": system, "prompt": prompt, "schema_name": schema_name, "max_output_tokens": max_output_tokens})
        content = question_generation_payload(target_question_id_from_prompt(prompt)) if schema_name == "QuestionGenerationOutput" else FINAL_PAYLOAD
        return LLMResponse(
            content=json.dumps(content, ensure_ascii=False),
            model="groq-test-model",
            provider="groq",
            raw_metadata={
                "id": "chatcmpl-test",
                "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
                "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                "system_fingerprint": "provider-internal",
            },
        )


class InvalidJsonProvider:
    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        schema_name: str,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        return LLMResponse(content="not json", model="test-model", provider="mock")


class RateLimitedProvider:
    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        schema_name: str,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        raise LLMRateLimitError("Groq API limit reached: token rate limit exceeded (type=rate_limit_error)")


class AlwaysInvalidFinalReadingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        schema_name: str,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        self.calls += 1
        return LLMResponse(content='{"reading_title":"끊긴 응답","desired_answer":"중간에서', model="test-model", provider="mock")


class SchemaInvalidFinalReadingProvider:
    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        schema_name: str,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        payload = {**FINAL_PAYLOAD, "period_guidance": FINAL_PAYLOAD["period_guidance"][:2]}
        return LLMResponse(content=json.dumps(payload, ensure_ascii=False), model="test-model", provider="mock")


def initial_payload() -> dict:
    return {
        "name": "홍길동",
        "gender": "male",
        "initial_concern": "올해 이직을 해도 될까요?",
        "birth": {
            "calendar_type": "solar",
            "year": 1990,
            "month": 10,
            "day": 10,
            "hour": 14,
            "minute": 30,
        },
    }


def answer_payload() -> list[dict]:
    return [
        {
            "question_id": question["id"],
            "question": question["text"],
            "answer": question["options"][0]["label"],
            "selected_option_ids": [question["options"][0]["id"]],
        }
        for question in QUESTION_PAYLOADS.values()
    ]


def previous_answer_payload(count: int) -> list[dict]:
    return answer_payload()[:count]


def test_generate_questions_happy_path() -> None:
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    response = client.post("/api/generate-questions", json=initial_payload())

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["question"]["id"] == "q1"
    assert body["question"]["type"] == "single_choice"
    assert [option["id"] for option in body["question"]["options"]] == ["A", "B", "C", "D"]
    assert body["saju"]["pillars"]["year"]["pillar"]
    assert body["meta"]["provider"] == "mock"
    assert provider.calls[-1]["max_output_tokens"] == 1200


def test_generate_next_question_happy_path() -> None:
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    response = client.post(
        "/api/generate-next-question",
        json={**initial_payload(), "answers": previous_answer_payload(1)},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["question"]["id"] == "q2"
    assert body["question"]["type"] == "single_choice"
    assert [option["id"] for option in body["question"]["options"]] == ["A", "B", "C", "D"]
    assert body["meta"]["provider"] == "mock"
    assert provider.calls[-1]["max_output_tokens"] == 1200


def test_generate_next_question_after_q4_returns_q5() -> None:
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    response = client.post(
        "/api/generate-next-question",
        json={**initial_payload(), "answers": previous_answer_payload(4)},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["question"]["id"] == "q5"


def test_generate_next_question_rejects_out_of_order_answers() -> None:
    client = TestClient(app)
    payload = {**initial_payload(), "answers": [answer_payload()[0], answer_payload()[2]]}

    response = client.post("/api/generate-next-question", json=payload)

    assert response.status_code == 422


def test_response_meta_slims_provider_raw_metadata() -> None:
    original_limiter = app.state.llm_rate_limiter
    app.state.llm_rate_limiter = None
    provider = GroqMetadataProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    try:
        response = client.post(
            "/api/generate-next-question",
            json={**initial_payload(), "answers": previous_answer_payload(1)},
        )
    finally:
        app.dependency_overrides.clear()
        app.state.llm_rate_limiter = original_limiter

    assert response.status_code == 200
    raw_metadata = response.json()["meta"]["raw_metadata"]
    assert raw_metadata == {
        "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
        "finish_reason": "stop",
    }
    assert "choices" not in raw_metadata
    assert "system_fingerprint" not in raw_metadata


def test_llm_debug_metrics_headers_when_enabled(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_DEBUG_METRICS_ENABLED", "true")
    monkeypatch.setenv("ENABLE_ADMIN_PROMPTS", "false")
    monkeypatch.setenv("PROMPTS_DB_PATH", str(tmp_path / "prompts.sqlite3"))
    get_settings.cache_clear()

    try:
        enabled_app = create_app()
        enabled_app.state.llm_rate_limiter = None
        provider = GroqMetadataProvider()
        enabled_app.dependency_overrides[get_llm_provider] = lambda: provider
        with TestClient(enabled_app) as client:
            response = client.post(
                "/api/generate-next-question",
                json={**initial_payload(), "answers": previous_answer_payload(1)},
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.headers["X-LLM-Prompt-Tokens"] == "11"
    assert response.headers["X-LLM-Completion-Tokens"] == "22"
    assert response.headers["X-LLM-Total-Tokens"] == "33"
    assert response.headers["X-LLM-Max-Output-Tokens"] == "1200"
    assert response.headers["X-LLM-Provider-Cache"] == "unknown"
    assert response.headers["Server-Timing"].startswith("llm;dur=")
    assert int(response.headers["X-LLM-Prompt-Chars"]) > 0
    assert int(response.headers["X-LLM-Estimated-Prompt-Tokens"]) > 0


def test_llm_debug_metrics_headers_disabled_by_default(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_DEBUG_METRICS_ENABLED", "false")
    monkeypatch.setenv("ENABLE_ADMIN_PROMPTS", "false")
    monkeypatch.setenv("PROMPTS_DB_PATH", str(tmp_path / "prompts.sqlite3"))
    get_settings.cache_clear()
    provider = GroqMetadataProvider()

    try:
        disabled_app = create_app()
        disabled_app.state.llm_rate_limiter = None
        disabled_app.dependency_overrides[get_llm_provider] = lambda: provider
        with TestClient(disabled_app) as client:
            response = client.post(
                "/api/generate-next-question",
                json={**initial_payload(), "answers": previous_answer_payload(1)},
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert "X-LLM-Duration-Ms" not in response.headers
    assert "Server-Timing" not in response.headers


def test_generate_questions_rate_limit() -> None:
    original_limiter = app.state.llm_rate_limiter
    app.state.llm_rate_limiter = InMemoryRateLimiter(per_ip_per_hour=1, global_per_minute=100)
    app.dependency_overrides[get_llm_provider] = lambda: MockProvider()
    client = TestClient(app)

    try:
        payload = {**initial_payload(), "answers": previous_answer_payload(1)}
        first_response = client.post("/api/generate-next-question", json=payload)
        second_response = client.post("/api/generate-next-question", json=payload)
    finally:
        app.dependency_overrides.clear()
        app.state.llm_rate_limiter = original_limiter

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert "요청 한도" in second_response.json()["detail"]


def test_generate_questions_preserves_provider_rate_limit_detail() -> None:
    original_limiter = app.state.llm_rate_limiter
    app.state.llm_rate_limiter = None
    app.dependency_overrides[get_llm_provider] = lambda: RateLimitedProvider()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/generate-next-question",
            json={**initial_payload(), "answers": previous_answer_payload(1)},
        )
    finally:
        app.dependency_overrides.clear()
        app.state.llm_rate_limiter = original_limiter

    assert response.status_code == 429
    assert response.json()["detail"] == "Groq API limit reached: token rate limit exceeded (type=rate_limit_error)"


def test_admin_prompts_router_disabled_when_configured_off(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_ADMIN_PROMPTS", "false")
    get_settings.cache_clear()

    try:
        disabled_app = create_app()
        client = TestClient(disabled_app)

        response = client.get("/api/admin/prompts")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 404


def test_admin_prompts_include_reading_style_system_prompts(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ENABLE_ADMIN_PROMPTS", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("PROMPTS_DB_PATH", str(tmp_path / "prompts.sqlite3"))
    get_settings.cache_clear()

    try:
        enabled_app = create_app()
        client = TestClient(enabled_app)

        response = client.get("/api/admin/prompts", headers={"X-Admin-Key": "secret"})
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    prompt_names = [prompt["name"] for prompt in response.json()]
    assert "counseling_question_system_prompt" in prompt_names
    assert "counseling_question_user_prompt" in prompt_names
    assert "final_system_prompt_traditional" in prompt_names
    assert "final_system_prompt_empathetic" in prompt_names
    assert "final_system_prompt_direct" in prompt_names
    assert "question_system_prompt" not in prompt_names
    assert "question_user_prompt" not in prompt_names
    assert "final_system_prompt" not in prompt_names


def test_admin_prompt_keeps_custom_final_user_prompt(monkeypatch, tmp_path) -> None:
    custom_prompt = "사용자가 직접 작성한 최종 프롬프트"
    db_path = tmp_path / "prompts.sqlite3"
    store = PromptStore(str(db_path))
    store.init()
    store.set_prompt("final_user_prompt", custom_prompt)
    monkeypatch.setenv("ENABLE_ADMIN_PROMPTS", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("PROMPTS_DB_PATH", str(db_path))
    get_settings.cache_clear()

    try:
        enabled_app = create_app()
        client = TestClient(enabled_app)

        response = client.get("/api/admin/prompts/final_user_prompt", headers={"X-Admin-Key": "secret"})
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json()["content"] == custom_prompt


def test_default_final_prompt_keeps_personas_and_removes_redundant_internal_goals() -> None:
    assert "프리미엄 명리 심리 상담가" in FINAL_SYSTEM_PROMPT_TRADITIONAL
    assert "극F 성향의 사주 과몰입 찐 언니" in FINAL_SYSTEM_PROMPT_EMPATHETIC
    assert "싸가지 없는 천재 명리학자" in FINAL_SYSTEM_PROMPT_DIRECT
    assert "고객 리텐션" not in FINAL_USER_PROMPT_TEMPLATE
    assert "field_source_mapping" in FINAL_USER_PROMPT_TEMPLATE
    assert "고객이 진짜 듣고 싶었던 말" in FINAL_USER_PROMPT_TEMPLATE
    assert "desired_answer" in FINAL_USER_PROMPT_TEMPLATE
    assert "period_guidance" in FINAL_USER_PROMPT_TEMPLATE
    assert "share_card" in FINAL_USER_PROMPT_TEMPLATE
    assert "strengths" in FINAL_USER_PROMPT_TEMPLATE
    assert "작은 체크 노트" in FINAL_USER_PROMPT_TEMPLATE
    assert "luck_recipe" not in FINAL_USER_PROMPT_TEMPLATE
    assert FINAL_USER_PROMPT_TEMPLATE.count("JSON Schema") == 1


def test_admin_llm_settings_round_trip(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ENABLE_ADMIN_PROMPTS", "true")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("PROMPTS_DB_PATH", str(tmp_path / "prompts.sqlite3"))
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    get_settings.cache_clear()

    try:
        enabled_app = create_app()
        client = TestClient(enabled_app)
        headers = {"X-Admin-Key": "secret"}

        initial = client.get("/api/admin/settings/llm", headers=headers)
        saved = client.put(
            "/api/admin/settings/llm",
            headers=headers,
            json={
                "llm_provider": "groq",
                "groq_model": "openai/gpt-oss-120b",
                "ollama_model": "qwen3:8b",
                "gemini_model": "gemini-2.5-pro",
            },
        )
        loaded = client.get("/api/admin/settings/llm", headers=headers)
    finally:
        get_settings.cache_clear()

    assert initial.status_code == 200
    assert initial.json()["llm_provider"] == "ollama"
    assert initial.json()["groq_model"] == "openai/gpt-oss-20b"
    assert initial.json()["gemini_model"] == "gemini-2.5-flash"
    assert saved.status_code == 200
    assert saved.json()["llm_provider"] == "groq"
    assert saved.json()["groq_model"] == "openai/gpt-oss-120b"
    assert saved.json()["gemini_model"] == "gemini-2.5-pro"
    assert loaded.json()["ollama_model"] == "qwen3:8b"


def test_runtime_llm_settings_prefer_saved_values(tmp_path) -> None:
    store = PromptStore(str(tmp_path / "prompts.sqlite3"))
    store.init()
    store.set_setting("llm_provider", "groq")
    store.set_setting("groq_model", "openai/gpt-oss-120b")
    store.set_setting("ollama_model", "qwen3:8b")
    store.set_setting("gemini_model", "gemini-2.5-pro")

    resolved = resolve_runtime_llm_settings(
        Settings(
            llm_provider="ollama",
            groq_model="openai/gpt-oss-20b",
            ollama_model="qwen3:4b",
            gemini_model="gemini-2.5-flash",
        ),
        store,
    )

    assert resolved.llm_provider == "groq"
    assert resolved.groq_model == "openai/gpt-oss-120b"
    assert resolved.ollama_model == "qwen3:8b"
    assert resolved.gemini_model == "gemini-2.5-pro"


def test_saju_only_happy_path() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/saju-only",
        json={
            "name": "홍길동",
            "gender": "male",
            "birth": {
                "calendar_type": "solar",
                "year": 1990,
                "month": 10,
                "day": 10,
                "hour": 14,
                "minute": 30,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["saju"]["pillars"]["year"]["pillar"]


def test_root_probe_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_final_reading_happy_path() -> None:
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    response = client.post("/api/final-reading", json={**initial_payload(), "answers": answer_payload()})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["reading"]["core_message"].startswith("이직은")
    assert body["reading"]["reading_title"] == "전환 앞에 선 마음의 나침반"
    assert "움직여도 된다는 허락" in body["reading"]["desired_answer"]
    assert body["reading"]["saju_insight"]["title"] == "이 고민이 찾아온 이유"
    assert body["reading"]["clear_solution"]["title"] == "지금 필요한 선택"
    assert body["reading"]["secret_talent"]["title"] == "강점으로 바뀌는 지점"
    assert "situation_mirror" not in body["reading"]
    assert "saju_vibe" not in body["reading"]
    assert "answer_signals" not in body["reading"]
    assert "answer_signal_summary" not in body["reading"]
    assert "timing_points" not in body["reading"]
    assert "luck_recipe" not in body["reading"]
    assert "re_engagement_hook" not in body["reading"]
    assert len(body["reading"]["saju_basis"]) == 3
    assert len(body["reading"]["period_guidance"]) == 3
    assert body["reading"]["share_card"]["daily_element"] == "작은 체크 노트"
    assert len(body["reading"]["share_card"]["strengths"]) == 3
    assert provider.calls[-1]["max_output_tokens"] == 5000


def test_final_reading_rejects_old_q6_q7_flow() -> None:
    client = TestClient(app)
    old_answers = answer_payload()[:3] + [
        {
            "question_id": "q6",
            "question": "이전 맞춤 질문",
            "answer": "이전 답변",
            "selected_option_ids": ["A"],
        },
        {
            "question_id": "q7",
            "question": "이전 맞춤 질문",
            "answer": "이전 답변",
            "selected_option_ids": ["A"],
        },
    ]

    response = client.post("/api/final-reading", json={**initial_payload(), "answers": old_answers})

    assert response.status_code == 422


def test_final_reading_defaults_to_traditional_reading_style() -> None:
    original_limiter = app.state.llm_rate_limiter
    app.state.llm_rate_limiter = None
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    try:
        response = client.post("/api/final-reading", json={**initial_payload(), "answers": answer_payload()})
    finally:
        app.dependency_overrides.clear()
        app.state.llm_rate_limiter = original_limiter

    assert response.status_code == 200
    assert "프리미엄 명리 심리 상담가" in provider.calls[-1]["system"]


def test_final_reading_routes_reading_style_system_prompt() -> None:
    original_limiter = app.state.llm_rate_limiter
    app.state.llm_rate_limiter = None
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    try:
        for style in ["traditional", "empathetic", "direct"]:
            response = client.post("/api/final-reading", json={**initial_payload(), "reading_style": style, "answers": answer_payload()})
            assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.state.llm_rate_limiter = original_limiter

    systems = [call["system"] for call in provider.calls]
    assert "프리미엄 명리 심리 상담가" in systems[0]
    assert "극F 성향의 사주 과몰입 찐 언니" in systems[1]
    assert "싸가지 없는 천재 명리학자" in systems[2]


def test_final_reading_reports_schema_validation_details() -> None:
    provider = SchemaInvalidFinalReadingProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    response = client.post("/api/final-reading", json={**initial_payload(), "answers": answer_payload()})

    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert "period_guidance" in response.json()["detail"]


def test_final_reading_reports_json_syntax_error() -> None:
    provider = AlwaysInvalidFinalReadingProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    response = client.post("/api/final-reading", json={**initial_payload(), "answers": answer_payload()})

    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert provider.calls == 1
    assert "JSON syntax error" in response.json()["detail"]


def test_generate_next_question_rejects_invalid_llm_json() -> None:
    app.dependency_overrides[get_llm_provider] = lambda: InvalidJsonProvider()
    client = TestClient(app)

    response = client.post(
        "/api/generate-next-question",
        json={**initial_payload(), "answers": previous_answer_payload(1)},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert "invalid question JSON" in response.json()["detail"]
