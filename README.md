# 사주 심리 리딩 MVP

Supabase Auth로 로그인한 사용자가 PortOne V2 결제를 완료한 뒤, 사주 정보와 고민 답변을 바탕으로 개인화 리딩을 받는 유료 LLM 웹 앱입니다.

## 구조

```text
backend/   FastAPI, Supabase Postgres, PortOne V2 검증, sajupy 만세력 계산, Gemini/Groq/Ollama LLM provider
frontend/  Next.js App Router, Supabase SSR Auth, PortOne browser SDK, Tailwind CSS
```

## 핵심 흐름

1. 사용자가 Supabase Auth로 로그인합니다.
2. `POST /api/reading-sessions`가 사용자 소유 리딩 세션을 만듭니다.
3. `POST /api/payments/checkout`가 서버에서 PortOne `paymentId`와 주문 원장을 생성합니다.
4. 브라우저는 PortOne 결제창을 열고, backend는 `/api/payments/complete` 또는 `/api/webhooks/portone`에서 PortOne 서버 조회로 결제를 검증합니다.
5. 결제 검증 후 `reading_credits`가 생성되고, 고정 질문, 맞춤 질문, 최종 리딩 API가 열립니다.
6. 최종 리딩 LLM 호출과 JSON schema 검증이 성공한 뒤에만 리딩권이 소비됩니다.

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

Auth/Payment/DB 설정:

```bash
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
PORTONE_API_SECRET=portone-v2-api-secret
PORTONE_WEBHOOK_SECRET=portone-webhook-secret
PORTONE_STORE_ID=store-xxxxxxxx
PORTONE_CHANNEL_KEY=channel-key-xxxxxxxx
PORTONE_WEBHOOK_URL=https://api.yourdomain.com/api/webhooks/portone
```

DB schema는 [backend/migrations/001_supabase_auth_portone_paid_readings.sql](backend/migrations/001_supabase_auth_portone_paid_readings.sql)을 Supabase SQL editor 또는 migration tool로 적용합니다.

## 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`을 엽니다. 프론트는 기본적으로 현재 호스트의 `:8000` 백엔드로 요청합니다. 배포 환경에서는 아래 값을 지정하세요.

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
NEXT_PUBLIC_PORTONE_STORE_ID=store-xxxxxxxx
NEXT_PUBLIC_PORTONE_CHANNEL_KEY=channel-key-xxxxxxxx
```

## API

주요 API는 모두 `Authorization: Bearer <supabase_access_token>`을 요구합니다.

- `POST /api/reading-sessions`
- `POST /api/payments/checkout`
- `POST /api/payments/complete`
- `POST /api/webhooks/portone`
- `POST /api/reading-sessions/{id}/generate-questions`
- `PUT /api/reading-sessions/{id}/fixed-answers`
- `POST /api/reading-sessions/{id}/generate-custom-questions`
- `PUT /api/reading-sessions/{id}/custom-answers`
- `POST /api/reading-sessions/{id}/final-reading`
- `GET /api/account/me`, `/api/account/orders`, `/api/account/readings`

결제 전에는 사주 계산과 LLM API가 모두 `402 Payment Required`로 막힙니다.

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
