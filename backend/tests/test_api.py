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
    "compass_summary": {
        "headline": "성장을 여는 목(木)의 기운이 이직 고민을 비교 가능한 선택으로 바꿔 줍니다.",
        "basis": "갑목(甲木, 곧게 자라려는 나의 중심)에 올해 병오(丙午, 드러내고 움직이는 흐름) 세운이 닿으면서, 지금의 이동 고민은 자연스럽게 커진 성장 신호입니다.",
        "solution": "용신인 목(木, 새 방향을 틔우는 기운)을 살리려면 오늘은 감정보다 작은 탐색이 필요합니다. 지원할 공고 세 개를 고르고, 포기할 조건 하나를 먼저 적어보세요.",
        "strength_animal": "숲길을 먼저 살피는 사슴처럼, 신중함으로 새 길을 고르는 힘",
    },
    "manse_summary": {
        "headline": "기운은 성장 욕구와 현실 점검이 함께 강합니다.",
        "energy_overview": "오행 분포에서는 목과 수가 눈에 띄고, 주무기 십성은 비견으로 잡힙니다. 스스로 기준을 세우려는 힘이 올해 세운과 만나 선택 압박으로 드러납니다.",
        "key_traits": ["일간 甲의 성장성", "주무기 비견의 자기 기준", "세운 丙午의 표현 압력"],
    },
    "dual_reading": {
        "weapon": {
            "title": "나의 무기",
            "headline": "비견의 자기 기준은 흔들리는 선택을 붙잡는 힘입니다.",
            "body": "홍길동님에게 강하게 잡히는 비견은 남의 말에 쉽게 휘둘리기보다 자기 기준을 세우는 힘입니다. 지금 상황이 복잡해 보여도, 이 힘은 조건을 비교하고 버틸 수 있는 중심이 됩니다. 이직 고민에서는 감정적 도피보다 내가 납득할 수 있는 기준표를 만드는 능력으로 쓰일 때 가장 강합니다.",
        },
        "growth_hint": {
            "title": "성장의 힌트",
            "headline": "기준이 강해질수록 혼자 버티려는 부담도 커질 수 있습니다.",
            "body": "다만 비견의 장점이 과해지면 모든 판단을 혼자 책임지려는 무게가 커질 수 있습니다. 기신으로 잡히는 금의 서늘한 압박이 강해질 때는 스스로를 몰아붙이는 방식으로 고민이 깊어집니다. 이럴 때는 희신인 수의 유연함을 빌려, 결론을 당장 내리기보다 정보를 천천히 흘려보내며 선택지를 넓히는 쪽이 좋습니다.",
        },
    },
    "healing_card": {
        "metaphor_sentence": "새벽 공기를 밀고 올라오는 곧은 나무의 첫 숨",
        "affirmation": "내 선택은 천천히 자라도 충분히 힘이 있습니다.",
        "lucky_element": "목",
        "color": "그린/블루",
        "direction": "동쪽",
        "ritual": "아침 5분 동안 창가에서 낯선 음악 한 곡을 들으며 오늘 열어볼 선택지 하나를 떠올려보세요.",
        "interpretation": "이 카드는 홍길동님에게 필요한 목의 기운을 담았습니다. 그린과 블루는 굳은 마음에 새 방향을 열어주고, 동쪽을 향하는 작은 루틴은 멈춘 생각을 다시 자라게 하는 상징으로 작동합니다.",
    },
    "secret_door": {
        "unexplored_area": "관계와 협업의 다음 문",
        "next_month_signal": "다가오는 6월 월운에서는 비견과 식신의 흐름이 함께 보입니다.",
        "teaser": "이번 리포트에서는 이직 고민을 중심으로 보았지만, 다음 달에는 사람들과 함께 움직일 때 열리는 기회가 더 선명해질 수 있습니다. 지금의 고민을 정리한 뒤, 관계와 협업의 흐름을 따로 보면 선택의 폭이 더 넓어집니다.",
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
        return LLMResponse(content='{"reading_title":"끊긴 응답","compass_summary":{"headline":"중간에서', model="test-model", provider="mock")


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
        payload = {**FINAL_PAYLOAD}
        payload.pop("compass_summary")
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
    assert "두려워하는 선택 기준" not in FINAL_USER_PROMPT_TEMPLATE
    assert "field_source_mapping" in FINAL_USER_PROMPT_TEMPLATE
    assert "고객이 진짜 듣고 싶었던 말" in FINAL_USER_PROMPT_TEMPLATE
    assert "5단계 답변으로 듣고 싶은 말 추론" in FINAL_USER_PROMPT_TEMPLATE
    assert "긍정적인 작용" in FINAL_USER_PROMPT_TEMPLATE
    assert "한글(한자)" in FINAL_USER_PROMPT_TEMPLATE
    assert "쉬운 설명" in FINAL_USER_PROMPT_TEMPLATE
    assert "첫 카드 섹션 헤드라인" in FINAL_USER_PROMPT_TEMPLATE
    assert "원국" in FINAL_USER_PROMPT_TEMPLATE
    assert "용신" in FINAL_USER_PROMPT_TEMPLATE
    assert "희신" in FINAL_USER_PROMPT_TEMPLATE
    assert "기신" in FINAL_USER_PROMPT_TEMPLATE
    assert "오행 균형" in FINAL_USER_PROMPT_TEMPLATE
    assert "compass_summary" in FINAL_USER_PROMPT_TEMPLATE
    assert "manse_summary" in FINAL_USER_PROMPT_TEMPLATE
    assert "dual_reading" in FINAL_USER_PROMPT_TEMPLATE
    assert "healing_card" in FINAL_USER_PROMPT_TEMPLATE
    assert "secret_door" in FINAL_USER_PROMPT_TEMPLATE
    assert "final_yongshin[0]" in FINAL_USER_PROMPT_TEMPLATE
    assert "업무 체크리스트" in FINAL_USER_PROMPT_TEMPLATE
    assert "current_luck" in FINAL_USER_PROMPT_TEMPLATE
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
    assert body["reading"]["compass_summary"]["headline"].startswith("성장을 여는 목")
    assert body["reading"]["compass_summary"]["strength_animal"].startswith("숲길을 먼저 살피는 사슴")
    assert body["reading"]["reading_title"] == "전환 앞에 선 마음의 나침반"
    assert "갑목(甲木" in body["reading"]["compass_summary"]["basis"]
    assert body["reading"]["dual_reading"]["weapon"]["title"] == "나의 무기"
    assert body["reading"]["dual_reading"]["growth_hint"]["title"] == "성장의 힌트"
    assert "situation_mirror" not in body["reading"]
    assert "saju_vibe" not in body["reading"]
    assert "answer_signals" not in body["reading"]
    assert "answer_signal_summary" not in body["reading"]
    assert "timing_points" not in body["reading"]
    assert "luck_recipe" not in body["reading"]
    assert "re_engagement_hook" not in body["reading"]
    assert "saju_basis" not in body["reading"]
    assert "period_guidance" not in body["reading"]
    assert body["reading"]["healing_card"]["metaphor_sentence"] == "새벽 공기를 밀고 올라오는 곧은 나무의 첫 숨"
    assert body["reading"]["healing_card"]["direction"] == "동쪽"
    assert body["reading"]["secret_door"]["unexplored_area"] == "관계와 협업의 다음 문"
    assert body["saju"]["yonghuishin"]["yongshin"]["final_yongshin"][0]["element"]
    assert body["saju"]["current_luck"]["annual"]["pillar"]
    assert body["saju"]["dominant_ten_god"]["name"]
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
    assert "compass_summary" in response.json()["detail"]


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
