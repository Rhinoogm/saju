# 사주 심리 리딩 MVP

사용자의 사주 정보와 초기 고민을 받아 고정 심리 질문과 맞춤 심층 질문을 생성하고, 그 답변을 사주 명식과 결합해 최종 풀이를 제공하는 LLM 웹 앱입니다.

## 구조

```text
backend/   FastAPI, sajupy 만세력 계산, Gemini/Groq/Ollama LLM provider, structured prompt
frontend/  Next.js, Tailwind CSS, 3단계 화면 전환 UI
```

## 핵심 흐름

1. 사용자가 이름, 성별, 생년월일시, 초기 고민을 입력합니다.
2. `POST /api/generate-questions`가 사주 명식을 계산하고 고정 질문 q1-q3과 선택 서술형 q4를 반환합니다.
3. `POST /api/generate-custom-questions`가 LLM structured output으로 맞춤 질문 q5-q7을 생성하고 선택 서술형 q8을 붙입니다.
4. 프론트엔드가 필수 답변 q1, q2, q3, q5, q6, q7과 선택 답변 q4, q8을 수집합니다.
5. `POST /api/final-reading`이 사주 명식, 초기 고민, 질문 답변을 LLM에 전달해 최종 풀이 JSON을 생성합니다.

## 백엔드 실행

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Ollama 사용:

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
GROQ_MAX_COMPLETION_TOKENS=5000
GROQ_MAX_REQUEST_TOKENS=6000
LLM_CUSTOM_QUESTIONS_MAX_OUTPUT_TOKENS=1200
LLM_FINAL_READING_MAX_OUTPUT_TOKENS=5000
LLM_DEBUG_METRICS_ENABLED=false
```

`auto`는 Groq에서 strict JSON Schema를 지원하는 모델(`openai/gpt-oss-20b`, `openai/gpt-oss-120b`)에는 `json_schema`를 사용하고, 그 외 모델에는 `json_object`를 사용합니다. strict schema를 직접 쓰려면 지원 모델로 `GROQ_MODEL`을 바꾸거나 `GROQ_RESPONSE_FORMAT_MODE=json_schema`를 지정하세요.

Gemini AI Studio API 사용:

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.1-flash-lite-preview
GEMINI_RESPONSE_SCHEMA_MODE=json_schema
GEMINI_MAX_OUTPUT_TOKENS=5000
LLM_CUSTOM_QUESTIONS_MAX_OUTPUT_TOKENS=1200
LLM_FINAL_READING_MAX_OUTPUT_TOKENS=5000
LLM_DEBUG_METRICS_ENABLED=false
```

Gemini provider는 Google AI Studio의 Gemini API `generateContent` REST endpoint를 호출하며, 기본값으로 `responseMimeType=application/json`과 `responseJsonSchema`를 사용합니다.
`LLM_DEBUG_METRICS_ENABLED=true`를 켜면 LLM 응답에 `X-LLM-Duration-Ms`, `X-LLM-Prompt-Tokens`, `X-LLM-Completion-Tokens`, `X-LLM-Provider-Cache`, `Server-Timing` 같은 디버그 헤더가 붙어 Network 탭과 서버 로그에서 토큰/속도 변화를 확인할 수 있습니다.

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

응답은 `saju`, `questions`, `meta`를 반환합니다. `questions`는 고정 질문 q1-q3과 선택 서술형 q4입니다.

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
      "answer": "돈과 조건, 인정받지 못하는 느낌",
      "selected_option_ids": ["A", "B"]
    }
  ]
}
```

실제 요청에서는 필수 답변 q1, q2, q3, q5, q6, q7이 필요하며 q4와 q8은 선택입니다.

## Structured Output

질문 생성 프롬프트와 JSON Schema는 [backend/app/services/prompt_builder.py](/Users/rhino/Documents/gitRepo/saju/backend/app/services/prompt_builder.py)에 있습니다. FastAPI는 `QuestionGenerationOutput` Pydantic 스키마를 LLM provider에 전달하고, 응답을 다시 같은 모델로 검증합니다.

## 테스트

```bash
cd backend
pytest
```

## 배포

운영 배포는 Vercel 프론트엔드, Render FastAPI 백엔드, Gemini 유료 API 구성을 기준으로 합니다. 상세 절차와 환경변수는 [DEPLOYMENT.md](DEPLOYMENT.md)를 참고하세요.

다수 동시 사용자와 실제 운영 장애 대응까지 점검하려면 [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)를 함께 확인하세요.
