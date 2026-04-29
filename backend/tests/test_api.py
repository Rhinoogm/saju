import json

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.api.routes.saju import get_llm_provider
from app.main import app, create_app
from app.services.llm.base import LLMRateLimitError, LLMResponse
from app.services.prompt_builder import (
    FINAL_USER_PROMPT_TEMPLATE,
    LEGACY_FINAL_USER_PROMPT_TEMPLATE,
    PREVIOUS_FINAL_USER_PROMPT_TEMPLATE,
    STORED_FINAL_USER_PROMPT_TEMPLATE_V1,
)
from app.services.prompt_store import PromptStore
from app.services.rate_limiter import InMemoryRateLimiter
from app.services.runtime_settings import resolve_runtime_llm_settings


CUSTOM_QUESTION_PAYLOAD = {
    "questions": [
        {
            "id": "q5",
            "type": "single_choice",
            "text": "새로운 일을 떠올릴 때 기대감이 살아나는 느낌이 있어 보여요. 그 기대감 뒤에서 가장 소중하게 지키고 싶은 가치는 무엇에 가까울까요?",
            "options": [
                {"id": "A", "label": "내 능력을 더 넓게 펼칠 수 있는 성장감"},
                {"id": "B", "label": "일과 삶의 균형을 되찾는 안정감"},
                {"id": "C", "label": "노력한 만큼 인정받고 보상받는 공정함"},
                {"id": "D", "label": "새로운 사람들과 환경에서 얻는 활력"},
            ],
            "intent_signal": "반영적 질문, 핵심 가치",
        },
        {
            "id": "q6",
            "type": "single_choice",
            "text": "이미 이력서를 다듬고 공고를 살피는 작은 준비를 시작하셨네요. 이 노력이 쌓인다면 가장 먼저 어떤 긍정적인 변화가 보일까요?",
            "options": [
                {"id": "A", "label": "내가 갈 수 있는 선택지가 실제로 보이기 시작하는 것"},
                {"id": "B", "label": "하루를 버티는 느낌보다 준비한다는 감각이 커지는 것"},
                {"id": "C", "label": "주변 사람들과 커리어 이야기를 더 편하게 나누는 것"},
                {"id": "D", "label": "현재 자리에서도 덜 흔들리고 차분히 일할 수 있는 것"},
            ],
            "intent_signal": "소크라테스식 문답, 가능성 확장",
        },
        {
            "id": "q7",
            "type": "single_choice",
            "text": "여러 조건이 모두 중요하겠지만, 지금 딱 하나만 먼저 채워진다면 어떤 기준이 가장 마음을 놓이게 해줄까요?",
            "options": [
                {"id": "A", "label": "생활이 흔들리지 않을 만큼 안정적인 보상"},
                {"id": "B", "label": "내가 잘할 수 있고 배우는 재미가 있는 역할"},
                {"id": "C", "label": "무리하지 않고 회복할 수 있는 업무 리듬"},
                {"id": "D", "label": "나를 존중해 주는 사람들과 건강하게 일하는 환경"},
            ],
            "intent_signal": "니즈 좁히기, 최우선 조건",
        },
    ]
}


FINAL_PAYLOAD = {
    "reading_title": "전환 앞에 선 마음의 나침반",
    "core_message": "이직은 서두르지 말고, 성장 조건이 맞을 때 움직이는 쪽이 맞습니다.",
    "hashtags": ["#성장갈림길", "#조건확인", "#준비된전환", "#나를위한선택"],
    "situation_mirror": {
        "title": "당신의 현재 주파수",
        "headline": "성장 욕구와 안정 확인이 동시에 켜져 있습니다.",
        "body": "새로운 일을 찾아보고 싶다는 답은 지금의 자리를 단순히 벗어나고 싶은 마음만은 아닙니다. 이력서를 다듬고 공고를 살피는 선택에는 가능성을 현실로 확인하려는 태도가 담겨 있습니다. 결국 당신은 무작정 뛰는 사람이 아니라, 내 능력이 온전히 쓰일 조건을 찾고 있습니다.",
    },
    "saju_insight": {
        "title": "이 고민이 찾아온 이유",
        "headline": "자라려는 힘과 현실을 재는 힘이 동시에 움직입니다.",
        "body": "명식에는 더 넓은 역할을 탐색하려는 흐름과 안정된 기준을 확인하려는 흐름이 함께 보입니다. 그래서 지금의 고민은 변덕이 아니라, 성장할 자리와 감당할 조건을 동시에 재는 과정입니다. 대운의 흐름도 준비된 이동에는 힘을 실어주지만, 감정만 앞선 선택에는 부담을 남깁니다.",
    },
    "clear_solution": {
        "title": "명쾌한 처방전",
        "headline": "지원은 시작하되, 퇴사는 제안서와 조건표가 나온 뒤입니다.",
        "body": "지금 해야 할 일은 회사를 박차고 나가는 게 아니라 선택지를 실제로 꺼내 놓는 것입니다. 성장 가능성, 보상, 회복 리듬을 표로 나누고 세 조건 중 두 개 이상 맞는 곳만 진지하게 보세요. 제안이 오기 전까지는 현재 자리를 협상 카드로 남겨두는 쪽이 훨씬 유리합니다.",
    },
    "saju_vibe": {
        "title": "나만의 고유한 바이브",
        "headline": "차가운 흙 위에서 방향을 고르는 단단한 새싹 같은 사람",
        "body": "당신의 매력은 급하게 피어나는 화려함보다, 방향을 정하면 꾸준히 뿌리내리는 힘에 있습니다. 납득되는 기준을 찾을 때 표정과 말의 결이 가장 선명해집니다.",
    },
    "secret_talent": {
        "title": "숨겨진 무기",
        "headline": "망설임은 사실 리스크를 먼저 보는 기획력입니다.",
        "body": "스스로는 우유부단하다고 느낄 수 있지만, 지금의 망설임은 중요한 선택을 대충 넘기지 않는 감각입니다. 이 힘을 조건표와 일정으로 바꾸면 다음 선택을 설득력 있게 만드는 무기가 됩니다.",
    },
    "answer_signals": ["조건 개선 욕구", "인정 욕구", "안전 확인 욕구"],
    "saju_basis": ["월주 흐름에서 환경 변화 압박이 보입니다.", "오행 균형상 표현 욕구가 막히면 답답함이 커집니다.", "대운 흐름은 준비된 이동에 유리합니다."],
    "timing_points": ["앞으로 2주는 마음을 다그치기보다 이직 조건표를 만드는 데 쓰세요.", "한 달 안에는 지원할 역할과 포기할 조건을 분리해 기준을 좁히세요.", "1-3개월 사이에는 실제 제안과 현재 자리의 회복 가능성을 나란히 비교하세요."],
    "luck_recipe": [
        {"category": "컬러", "item": "딥 민트", "reason": "과열된 책임감을 식히고 차분히 기준을 세우는 감각을 돕습니다."},
        {"category": "음식", "item": "따뜻한 보리차", "reason": "속도를 낮추고 몸의 긴장을 풀어 결정 피로를 덜어줍니다."},
        {"category": "작은 습관", "item": "퇴근 후 10분 조건표 쓰기", "reason": "흩어진 걱정을 눈에 보이는 선택 기준으로 바꿔줍니다."},
        {"category": "아이템", "item": "작은 체크 노트", "reason": "머릿속 계산을 밖으로 꺼내 현실적인 확신을 쌓게 합니다."},
    ],
    "re_engagement_hook": {
        "title": "다음엔 이런 것도 궁금해질 거예요",
        "body": "명식을 보면 일에서 인정받는 방식만큼 재물 흐름을 관리하는 방식도 꽤 흥미롭습니다. 다음에는 연봉 협상이나 금전운을 열어보면 선택 기준이 더 또렷해질 수 있습니다.",
    },
    "caution": "이 리딩은 확정 예언이 아니라 자기 이해와 선택을 돕는 참고 자료입니다.",
}


class MockProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def generate(self, *, system: str, prompt: str, schema: dict, schema_name: str) -> LLMResponse:
        assert system.strip()
        assert prompt.strip()
        assert schema_name in {"QuestionGenerationOutput", "FinalReadingOutput"}
        assert schema["type"] == "object"
        self.calls.append({"system": system, "prompt": prompt, "schema_name": schema_name})
        content = CUSTOM_QUESTION_PAYLOAD if schema_name == "QuestionGenerationOutput" else FINAL_PAYLOAD
        return LLMResponse(
            content=json.dumps(content, ensure_ascii=False),
            model="test-model",
            provider="mock",
            raw_metadata={"done": True},
        )


class InvalidJsonProvider:
    async def generate(self, *, system: str, prompt: str, schema: dict, schema_name: str) -> LLMResponse:
        return LLMResponse(content="not json", model="test-model", provider="mock")


class RateLimitedProvider:
    async def generate(self, *, system: str, prompt: str, schema: dict, schema_name: str) -> LLMResponse:
        raise LLMRateLimitError("Groq API limit reached: token rate limit exceeded (type=rate_limit_error)")


class AlwaysInvalidFinalReadingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, *, system: str, prompt: str, schema: dict, schema_name: str) -> LLMResponse:
        self.calls += 1
        return LLMResponse(content='{"reading_title":"끊긴 응답","final_text":"중간에서', model="test-model", provider="mock")


class SchemaInvalidFinalReadingProvider:
    async def generate(self, *, system: str, prompt: str, schema: dict, schema_name: str) -> LLMResponse:
        payload = {**FINAL_PAYLOAD, "luck_recipe": FINAL_PAYLOAD["luck_recipe"][:2]}
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
            "question_id": "q1",
            "question": "요즘 커리어나 직장 생활에서 가장 집중하고 있거나, 새롭게 원하는 방향은 어떤 것인가요?",
            "answer": "지금보다 더 성장할 수 있고 가슴 뛰는 새로운 일을 찾아보고 싶어요",
            "selected_option_ids": ["D"],
        },
        {
            "question_id": "q2",
            "question": "이 목표를 향해 나아가기 위해 요즘 일상에서 어떤 준비를 하고 계신가요?",
            "answer": "새로운 도전을 위해 이력서를 다듬거나 채용 공고를 눈여겨보고 있어요",
            "selected_option_ids": ["A"],
        },
        {
            "question_id": "q3",
            "question": "커리어에서 원하는 바를 이루었을 때, 일상에서 가장 크게 달라지길 기대하는 부분은 무엇인가요?",
            "answer": "내 능력을 온전히 발휘하고 있다는 깊은 성취감",
            "selected_option_ids": ["C"],
        }
    ] + [
        {
            "question_id": item["id"],
            "question": item["text"],
            "answer": item["options"][0]["label"],
            "selected_option_ids": [item["options"][0]["id"]],
        }
        for item in CUSTOM_QUESTION_PAYLOAD["questions"]
    ]


def fixed_answer_payload() -> list[dict]:
    return answer_payload()[:3]


def test_generate_questions_happy_path() -> None:
    client = TestClient(app)

    response = client.post("/api/generate-questions", json=initial_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "career"
    assert body["category_label"] == "직업"
    assert len(body["questions"]) == 4
    assert body["questions"][0]["id"] == "q1"
    assert body["questions"][3]["id"] == "q4"
    assert body["questions"][3]["type"] == "short_text"
    assert body["saju"]["pillars"]["year"]["pillar"]
    assert body["meta"]["provider"] == "system"


def test_generate_custom_questions_happy_path() -> None:
    provider = MockProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    response = client.post(
        "/api/generate-custom-questions",
        json={**initial_payload(), "category": "career", "fixed_answers": fixed_answer_payload()},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert len(body["questions"]) == 4
    assert body["questions"][0]["id"] == "q5"
    assert body["questions"][0]["type"] == "single_choice"
    assert [option["id"] for option in body["questions"][0]["options"]] == ["A", "B", "C", "D"]
    assert body["questions"][3]["id"] == "q8"
    assert body["questions"][3]["type"] == "short_text"
    assert body["meta"]["provider"] == "mock"


def test_generate_questions_rate_limit() -> None:
    original_limiter = app.state.llm_rate_limiter
    app.state.llm_rate_limiter = InMemoryRateLimiter(per_ip_per_hour=1, global_per_minute=100)
    app.dependency_overrides[get_llm_provider] = lambda: MockProvider()
    client = TestClient(app)

    try:
        payload = {**initial_payload(), "category": "career", "fixed_answers": fixed_answer_payload()}
        first_response = client.post("/api/generate-custom-questions", json=payload)
        second_response = client.post("/api/generate-custom-questions", json=payload)
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
            "/api/generate-custom-questions",
            json={**initial_payload(), "category": "career", "fixed_answers": fixed_answer_payload()},
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
    assert "final_system_prompt_traditional" in prompt_names
    assert "final_system_prompt_empathetic" in prompt_names
    assert "final_system_prompt_direct" in prompt_names
    assert "final_system_prompt" not in prompt_names


def test_admin_prompt_migration_replaces_legacy_final_user_prompt(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "prompts.sqlite3"
    store = PromptStore(str(db_path))
    store.init()
    store.set_prompt("final_user_prompt", LEGACY_FINAL_USER_PROMPT_TEMPLATE.strip())
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
    assert response.json()["content"] == FINAL_USER_PROMPT_TEMPLATE


def test_admin_prompt_migration_replaces_previous_default_final_user_prompts(monkeypatch, tmp_path) -> None:
    for index, previous_prompt in enumerate([PREVIOUS_FINAL_USER_PROMPT_TEMPLATE, STORED_FINAL_USER_PROMPT_TEMPLATE_V1]):
        db_path = tmp_path / f"prompts-{index}.sqlite3"
        store = PromptStore(str(db_path))
        store.init()
        store.set_prompt("final_user_prompt", previous_prompt.strip())
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
        assert response.json()["content"] == FINAL_USER_PROMPT_TEMPLATE


def test_admin_prompt_migration_keeps_custom_final_user_prompt(monkeypatch, tmp_path) -> None:
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
    assert body["reading"]["situation_mirror"]["title"] == "당신의 현재 주파수"
    assert body["reading"]["saju_insight"]["title"] == "이 고민이 찾아온 이유"
    assert body["reading"]["clear_solution"]["title"] == "명쾌한 처방전"
    assert body["reading"]["re_engagement_hook"]["title"] == "다음엔 이런 것도 궁금해질 거예요"
    assert len(body["reading"]["hashtags"]) == 4
    assert len(body["reading"]["luck_recipe"]) == 4
    assert len(body["reading"]["saju_basis"]) == 3
    assert len(body["reading"]["timing_points"]) == 3


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
    assert "오지랖 넓은 푼수이자 영혼의 단짝" in systems[1]
    assert "시니컬한 전략 분석가" in systems[2]


def test_final_reading_reports_schema_validation_details() -> None:
    provider = SchemaInvalidFinalReadingProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    response = client.post("/api/final-reading", json={**initial_payload(), "answers": answer_payload()})

    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert "luck_recipe" in response.json()["detail"]


def test_final_reading_reports_json_syntax_error() -> None:
    provider = AlwaysInvalidFinalReadingProvider()
    app.dependency_overrides[get_llm_provider] = lambda: provider
    client = TestClient(app)

    response = client.post("/api/final-reading", json={**initial_payload(), "answers": answer_payload()})

    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert provider.calls == 1
    assert "JSON syntax error" in response.json()["detail"]


def test_generate_custom_questions_rejects_invalid_llm_json() -> None:
    app.dependency_overrides[get_llm_provider] = lambda: InvalidJsonProvider()
    client = TestClient(app)

    response = client.post(
        "/api/generate-custom-questions",
        json={**initial_payload(), "category": "career", "fixed_answers": fixed_answer_payload()},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert "invalid question JSON" in response.json()["detail"]
