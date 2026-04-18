# 사주 심리 리딩 MVP

사용자의 사주 정보와 초기 고민을 받아 5개의 심리 진단 질문을 생성하고, 그 답변을 사주 명식과 결합해 최종 풀이를 제공하는 2-step LLM 웹 앱입니다.

## 구조

```text
backend/   FastAPI, sajupy 만세력 계산, Groq/Ollama LLM provider, structured prompt
frontend/  Next.js, Tailwind CSS, 3단계 화면 전환 UI
```

## 핵심 흐름

1. 사용자가 이름, 성별, 생년월일시, 초기 고민을 입력합니다.
2. `POST /api/generate-questions`가 사주 명식을 계산하고 LLM에 structured output으로 질문 5개를 요청합니다.
3. 프론트엔드가 질문 5개를 표시하고 답변을 수집합니다.
4. `POST /api/final-reading`이 사주 명식, 초기 고민, 질문 답변을 LLM에 전달해 최종 풀이 JSON을 생성합니다.

## 백엔드 실행

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

로컬 Ollama 기본값:

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
OLLAMA_FORMAT_MODE=auto
```

Groq 사용:

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant
GROQ_RESPONSE_FORMAT_MODE=auto
```

`auto`는 Groq에서 strict JSON Schema를 지원하는 모델(`openai/gpt-oss-20b`, `openai/gpt-oss-120b`)에는 `json_schema`를 사용하고, 그 외 모델에는 `json_object`를 사용합니다. strict schema를 직접 쓰려면 지원 모델로 `GROQ_MODEL`을 바꾸거나 `GROQ_RESPONSE_FORMAT_MODE=json_schema`를 지정하세요.

## 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`을 엽니다. 프론트는 기본적으로 현재 호스트의 `:8000` 백엔드로 요청합니다. 배포 환경에서는 `NEXT_PUBLIC_API_BASE_URL`에 FastAPI 백엔드 주소를 지정하세요.

## API

### `POST /api/generate-questions`

요청:

```json
{
  "name": "홍길동",
  "gender": "female",
  "initial_concern": "이직을 해야 할지 버텨야 할지 모르겠어요.",
  "birth": {
    "calendar_type": "solar",
    "year": 1995,
    "month": 1,
    "day": 1,
    "hour": 9,
    "minute": 0,
    "is_leap_month": false,
    "city": "Seoul",
    "longitude": null,
    "use_solar_time": false
  }
}
```

응답은 `saju`, `questions`, `meta`를 반환합니다. `questions`는 항상 5개입니다.

### `POST /api/final-reading`

`/api/generate-questions` 요청 본문에 `answers`를 추가해 전송합니다.

```json
{
  "name": "홍길동",
  "gender": "female",
  "initial_concern": "이직을 해야 할지 버텨야 할지 모르겠어요.",
  "birth": {
    "calendar_type": "solar",
    "year": 1995,
    "month": 1,
    "day": 1,
    "hour": 9,
    "minute": 0,
    "is_leap_month": false,
    "city": "Seoul",
    "longitude": null,
    "use_solar_time": false
  },
  "answers": [
    {
      "question_id": "q1",
      "question": "지금 고민에서 가장 크게 걸리는 것은 무엇인가요?",
      "answer": "돈과 조건",
      "selected_option_id": "A"
    }
  ]
}
```

실제 요청에서는 `q1`부터 `q5`까지 5개 답변이 필요합니다.

## Structured Output

질문 생성 프롬프트와 JSON Schema는 [backend/app/services/prompt_builder.py](/Users/rhino/Documents/gitRepo/saju/backend/app/services/prompt_builder.py)에 있습니다. FastAPI는 `QuestionGenerationOutput` Pydantic 스키마를 LLM provider에 전달하고, 응답을 다시 같은 모델로 검증합니다.

## 테스트

```bash
cd backend
pytest
```
