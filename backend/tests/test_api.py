import json

from fastapi.testclient import TestClient

from app.api.routes.saju import get_llm_provider
from app.main import app
from app.services.llm.base import LLMResponse


QUESTION_PAYLOAD = {
    "questions": [
        {
            "id": "q1",
            "type": "single_choice",
            "text": "지금 고민에서 가장 크게 걸리는 것은 무엇인가요?",
            "options": [
                {"id": "A", "label": "돈과 조건"},
                {"id": "B", "label": "인정받지 못하는 느낌"},
            ],
            "intent_signal": "보상 욕구",
        },
        {
            "id": "q2",
            "type": "single_choice",
            "text": "결정 후 가장 먼저 얻고 싶은 감정은 무엇인가요?",
            "options": [
                {"id": "A", "label": "안도감"},
                {"id": "B", "label": "해방감"},
            ],
            "intent_signal": "안전 또는 도피",
        },
        {
            "id": "q3",
            "type": "single_choice",
            "text": "누가 등을 밀어주면 바로 움직일 것 같나요?",
            "options": [
                {"id": "A", "label": "가족"},
                {"id": "B", "label": "동료나 상사"},
            ],
            "intent_signal": "외부 인정",
        },
        {
            "id": "q4",
            "type": "single_choice",
            "text": "현재 상황을 유지한다면 가장 두려운 것은 무엇인가요?",
            "options": [
                {"id": "A", "label": "기회를 놓치는 것"},
                {"id": "B", "label": "체력이 버티지 못하는 것"},
            ],
            "intent_signal": "상실 회피",
        },
        {
            "id": "q5",
            "type": "short_text",
            "text": "사실 누군가에게 가장 듣고 싶은 한마디는 무엇인가요?",
            "options": [],
            "intent_signal": "최종 확인 욕구",
        },
    ]
}


FINAL_PAYLOAD = {
    "desired_conclusion": "이직 준비를 시작해도 된다는 확신을 원하고 있습니다.",
    "core_message": "지금은 버티는 운보다 방향을 바꾸는 운을 준비할 때입니다.",
    "final_text": "결론부터 말하면, 지금 마음은 이미 움직이는 쪽으로 기울어 있습니다. 다만 무작정 뛰쳐나가고 싶은 마음이 아니라 조건을 갖춘 뒤 인정받을 수 있는 자리로 옮기고 싶은 욕구가 큽니다.\n\n명식에서는 변화 욕구와 현실 안정 욕구가 함께 보입니다. 그래서 답은 당장 퇴사가 아니라 이직 준비를 공식 일정으로 올리는 것입니다.",
    "answer_signals": ["조건 개선 욕구", "인정 욕구", "안전 확인 욕구"],
    "saju_basis": ["월주 흐름에서 환경 변화 압박이 보입니다.", "오행 균형상 표현 욕구가 막히면 답답함이 커집니다.", "대운 흐름은 준비된 이동에 유리합니다."],
    "action_steps": ["2주 안에 이직 조건표를 만드세요.", "현재 회사에서 버틸 마감일을 정하세요."],
    "caution": "사주는 결정의 참고 자료이며, 실제 조건 확인을 함께 해야 합니다.",
}


class MockProvider:
    async def generate(self, *, system: str, prompt: str, schema: dict, schema_name: str) -> LLMResponse:
        assert "Structured Output" in system
        assert schema_name in {"QuestionGenerationOutput", "FinalReadingOutput"}
        assert schema["type"] == "object"
        content = QUESTION_PAYLOAD if schema_name == "QuestionGenerationOutput" else FINAL_PAYLOAD
        return LLMResponse(
            content=json.dumps(content, ensure_ascii=False),
            model="test-model",
            provider="mock",
            raw_metadata={"done": True},
        )


class InvalidJsonProvider:
    async def generate(self, *, system: str, prompt: str, schema: dict, schema_name: str) -> LLMResponse:
        return LLMResponse(content="not json", model="test-model", provider="mock")


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
            "question_id": item["id"],
            "question": item["text"],
            "answer": item["options"][0]["label"] if item["options"] else "이제 움직여도 된다는 말",
            "selected_option_id": item["options"][0]["id"] if item["options"] else None,
        }
        for item in QUESTION_PAYLOAD["questions"]
    ]


def test_generate_questions_happy_path() -> None:
    app.dependency_overrides[get_llm_provider] = lambda: MockProvider()
    client = TestClient(app)

    response = client.post("/api/generate-questions", json=initial_payload())

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert len(body["questions"]) == 5
    assert body["questions"][0]["id"] == "q1"
    assert body["saju"]["pillars"]["year"]["pillar"]
    assert body["meta"]["provider"] == "mock"


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


def test_final_reading_happy_path() -> None:
    app.dependency_overrides[get_llm_provider] = lambda: MockProvider()
    client = TestClient(app)

    response = client.post("/api/final-reading", json={**initial_payload(), "answers": answer_payload()})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["reading"]["core_message"].startswith("지금은")
    assert len(body["reading"]["saju_basis"]) == 3


def test_generate_questions_rejects_invalid_llm_json() -> None:
    app.dependency_overrides[get_llm_provider] = lambda: InvalidJsonProvider()
    client = TestClient(app)

    response = client.post("/api/generate-questions", json=initial_payload())

    app.dependency_overrides.clear()
    assert response.status_code == 502
    assert "invalid question JSON" in response.json()["detail"]
