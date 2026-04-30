# Saju MVP 배포 가이드

이 프로젝트는 프론트엔드와 백엔드를 분리해서 배포한다.

- Frontend: Vercel, root directory `frontend/`
- Backend: Render Web Service, root directory `backend/`
- LLM: Gemini 3.1 Flash-Lite 유료 결제, `LLM_PROVIDER=gemini`
- Auth/DB: Supabase Auth + Supabase Postgres
- Payment: PortOne V2

다수 사용자가 동시에 쓰는 공개 운영은 Render paid instance와 Gemini paid quota 기준으로 잡는다. 수면 상태가 있는 저가/테스트용 인스턴스는 첫 요청 지연이 생길 수 있으므로 운영 트래픽에는 사용하지 않는다.

## 1. 배포 전 확인

로컬에서 먼저 테스트와 빌드를 통과시킨다.

```bash
cd backend
pytest

cd ../frontend
npm install
npm run build
```

GitHub에 repo를 push한 뒤 Render와 Vercel에서 같은 repo를 연결한다.

## 2. LLM API Key

Gemini AI Studio에서 API key를 만든다. 운영 추천 모델은 `gemini-3.1-flash-lite-preview`다. 현재 백엔드의 Gemini provider는 Google AI Studio Gemini API의 JSON Schema structured output을 사용한다.

Groq를 계속 사용할 수도 있다. Groq 추천 모델은 `openai/gpt-oss-20b`이며, Groq provider는 이 모델에서 JSON Schema response format을 사용한다.

Gemini active limit은 project와 모델 기준으로 적용된다. 이 문서는 AI Studio에서 `4,000 RPM`, `4,000,000 TPM`, `150,000 RPD`가 표시되는 Gemini 3.1 Flash-Lite 유료 설정을 기준으로 한다. 최신 한도는 각 provider 콘솔의 rate limit 문서를 확인한다.

## 3. Supabase

Supabase에서 먼저 프로젝트를 만들고 [backend/migrations/001_supabase_auth_portone_paid_readings.sql](backend/migrations/001_supabase_auth_portone_paid_readings.sql)을 적용한다.

확인 항목:

- Authentication providers에서 Google을 먼저 활성화하고 Kakao는 staging에서 별도 확인한다.
- Site URL과 Redirect URL에 `http://localhost:3000/auth/callback`, production `/auth/callback`, 필요한 Vercel preview pattern을 등록한다.
- RLS가 migration으로 켜졌는지 확인한다.
- `service_role` key는 backend 환경변수에만 넣고 frontend에는 절대 넣지 않는다.

## 4. PortOne

PortOne V2 콘솔에서 Store ID, Channel Key, V2 API Secret, Webhook Secret을 준비한다.

확인 항목:

- 테스트 결제 채널로 checkout/complete/webhook을 먼저 검증한다.
- webhook URL은 `https://<backend-domain>/api/webhooks/portone`으로 등록한다.
- webhook은 raw body signature 검증 후 PortOne 결제 조회로 최종 반영된다.

## 5. Render Backend

Render Dashboard에서 `New > Web Service`를 선택하고 GitHub repo를 연결한다.

설정값:

- Name: `saju-backend`
- Root Directory: `backend`
- Runtime: `Python 3`
- Instance Type: paid instance
- Build Command: `python -m pip install -e .`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

환경변수:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-gemini-api-key>
GEMINI_MODEL=gemini-3.1-flash-lite-preview
GEMINI_RESPONSE_SCHEMA_MODE=json_schema
GEMINI_MAX_OUTPUT_TOKENS=5000
GEMINI_TIMEOUT_SECONDS=60

GROQ_API_KEY=<your-groq-api-key>
GROQ_MODEL=openai/gpt-oss-20b
GROQ_RESPONSE_FORMAT_MODE=auto
GROQ_JSON_SCHEMA_STRICT=true
GROQ_MAX_COMPLETION_TOKENS=5000
GROQ_MAX_REQUEST_TOKENS=6000
GROQ_TIMEOUT_SECONDS=60

ENABLE_ADMIN_PROMPTS=false
CORS_ORIGINS=https://saju-frontend.vercel.app
CORS_ORIGIN_REGEX=

SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<supabase-service-role-key>
SUPABASE_JWT_AUDIENCE=authenticated
DATABASE_URL=<supabase-pooler-postgres-url>

PORTONE_API_SECRET=<portone-v2-api-secret>
PORTONE_WEBHOOK_SECRET=<portone-webhook-secret>
PORTONE_STORE_ID=<portone-store-id>
PORTONE_CHANNEL_KEY=<portone-channel-key>
PORTONE_WEBHOOK_URL=https://<render-service>.onrender.com/api/webhooks/portone

RATE_LIMIT_ENABLED=true
LLM_RATE_LIMIT_PER_IP_PER_HOUR=40
LLM_RATE_LIMIT_GLOBAL_PER_MINUTE=200
```

Gemini 3.1 Flash-Lite 유료 active limit이 약 `4,000 RPM`, `4,000,000 TPM`, `150,000 RPD`라면 `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE=200`부터 시작한다. 전체 리딩 1회가 LLM 2회를 사용하므로 분당 약 100명 완료 수준이다. 로그와 Gemini dashboard가 안정적이면 `300`, 이후 `400-500` 순서로 올린다.

첫 배포가 끝나면 Render URL을 확인한다.

```bash
curl https://<render-service>.onrender.com/health

curl https://saju-backend-d90s.onrender.com/health
```

기대 응답:

```json
{"status":"ok"}
```

## 6. Vercel Frontend

Vercel Dashboard에서 `Add New > Project`를 선택하고 같은 GitHub repo를 import한다.

설정값:

- Framework Preset: `Next.js`
- Root Directory: `frontend`
- Install Command: `npm install`
- Build Command: `npm run build`
- Output Directory: 비워둔다. Next.js는 Vercel이 자동으로 처리하므로 `public`을 입력하지 않는다.

환경변수:

```env
NEXT_PUBLIC_API_BASE_URL=https://saju-backend-d90s.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<supabase-anon-key>
NEXT_PUBLIC_PORTONE_STORE_ID=<portone-store-id>
NEXT_PUBLIC_PORTONE_CHANNEL_KEY=<portone-channel-key>
```

Production과 Preview 환경에 같은 값으로 시작한다.

배포 후 `/login`에서 Supabase OAuth 로그인이 되는지 먼저 확인한다. 관리자 프롬프트 UI와 `X-Admin-Key` 방식은 운영 비활성화 상태다.

`No Output Directory named "public" found after the Build completed` 오류가 나면 Vercel Project Settings의 Output Directory가 `public`으로 덮어써진 상태다. `Settings > Build & Development Settings`에서 Framework Preset을 `Next.js`로 바꾸고 Output Directory override를 끄거나 빈 값으로 저장한 뒤 다시 배포한다.

## 7. CORS 최종 고정

Vercel 배포 URL이 확정되면 Render의 `CORS_ORIGINS`를 실제 프론트엔드 origin으로 수정하고 redeploy한다.

```env
CORS_ORIGINS=https://saju-frontend.vercel.app
```

커스텀 도메인을 붙이면 comma-separated로 추가한다.

```env
CORS_ORIGINS=https://saju-frontend.vercel.app,https://yourdomain.com
```

## 8. 운영 확인

- Vercel 페이지가 열린다.
- 로그인하지 않은 상태에서 시작하면 `/login`으로 이동한다.
- 결제 전에는 사주 계산과 질문 생성 API가 `402`로 막힌다.
- PortOne 결제 성공 후 `/api/payments/complete`가 PortOne 서버 조회로 `paid`와 `reading_credit`을 반영한다.
- 브라우저를 닫아도 PortOne webhook만으로 결제 상태가 반영된다.
- 결제 후 고정 질문 q1-q3과 선택 q4를 표시하고, 이어서 맞춤 질문 q5-q7과 선택 q8을 생성한다.
- `최종 풀이 보기`가 JSON 파싱 오류 없이 결과 화면을 표시한다.
- 최종 리딩 성공 후 `reading_credit`이 consumed가 된다.
- Gemini, Groq, 자체 제한 한도 초과 시 429 안내 메시지가 표시된다.
- backend cold start, scale-up, provider 지연 상황에서도 프론트 로딩 상태가 유지된다.

다수 사용자가 동시에 접근하는 실제 운영 공개 전에는 [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)의 용량, 보안, rate limit, 모니터링 항목까지 확인한다.

## 9. 장애 대응

- `429 Too Many Requests`: 자체 rate limit 또는 LLM provider quota 초과다. 잠시 뒤 재시도하거나 앱 한도와 Gemini quota를 확인한다.
- `413 Request Entity Too Large`: provider의 tokens-per-minute 한도보다 요청이 크다. prompt 길이, output token, provider TPM 한도를 확인한다.
- `502 Bad Gateway`: LLM 응답 실패 또는 JSON schema 검증 실패다. Render logs에서 provider error body를 확인한다.
- `504 Gateway Timeout`: LLM 응답 시간이 초과됐다. 필요하면 `GEMINI_TIMEOUT_SECONDS=90` 또는 `GROQ_TIMEOUT_SECONDS=90`으로 올린다.
- 첫 요청이 느림: backend cold start, scale-up, provider 지연을 확인한다.
- 로그인 후 세션 없음: Supabase Site URL과 Redirect URL을 확인한다.
- 결제 후 권한 없음: PortOne API Secret, webhook URL, `/api/payments/complete` 로그, amount/currency mismatch 여부를 확인한다.

## 10. 확장 기준

사용자가 꾸준히 들어오면 다음 순서로 확장을 검토한다.

1. Render backend instance size를 올리거나 worker/instance 확장 방식을 정한다.
2. Gemini quota 사용률을 보고 `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE`를 `300`, `400-500` 순서로 올린다.
3. 관리자 프롬프트 편집을 운영에서 다시 켤 경우 Supabase Auth 기반 admin 권한과 Supabase Postgres 저장소, 감사 로그를 먼저 구현한다.
