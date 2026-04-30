# Saju MVP 배포 가이드

이 프로젝트는 프론트엔드와 백엔드를 분리해서 배포한다.

- Frontend: Vercel, root directory `frontend/`
- Backend: Render Web Service, root directory `backend/`
- LLM: Gemini 3.1 Flash-Lite 유료 결제, `LLM_PROVIDER=gemini`

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

## 3. Render Backend

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

ENABLE_ADMIN_PROMPTS=true
ADMIN_API_KEY=<admin-password>
PROMPTS_DB_PATH=./prompts.sqlite3
CORS_ORIGINS=https://saju-frontend.vercel.app
CORS_ORIGIN_REGEX=

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

## 4. Vercel Frontend

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
```

Production과 Preview 환경에 같은 값으로 시작한다.

배포 후 메인 화면 오른쪽 위 설정 버튼을 누르고 Render의 `ADMIN_API_KEY` 값으로 로그인하면 `/admin/prompts`에서 프롬프트를 수정할 수 있다.

`No Output Directory named "public" found after the Build completed` 오류가 나면 Vercel Project Settings의 Output Directory가 `public`으로 덮어써진 상태다. `Settings > Build & Development Settings`에서 Framework Preset을 `Next.js`로 바꾸고 Output Directory override를 끄거나 빈 값으로 저장한 뒤 다시 배포한다.

## 5. CORS 최종 고정

Vercel 배포 URL이 확정되면 Render의 `CORS_ORIGINS`를 실제 프론트엔드 origin으로 수정하고 redeploy한다.

```env
CORS_ORIGINS=https://saju-frontend.vercel.app
```

커스텀 도메인을 붙이면 comma-separated로 추가한다.

```env
CORS_ORIGINS=https://saju-frontend.vercel.app,https://yourdomain.com
```

## 6. 운영 확인

- Vercel 페이지가 열린다.
- `만세력 보러가기`가 정상 응답한다.
- `심리 리딩 질문 받기`가 고정 질문 q1-q3과 선택 q4를 표시하고, 이어서 맞춤 질문 q5-q7과 선택 q8을 생성한다.
- `최종 풀이 보기`가 JSON 파싱 오류 없이 결과 화면을 표시한다.
- 오른쪽 위 설정 버튼에서 관리자 비밀번호를 입력하면 `/admin/prompts`로 이동한다.
- `/admin/prompts`는 백엔드 `ENABLE_ADMIN_PROMPTS=true`와 `ADMIN_API_KEY`가 설정되어 있어야 불러오기/저장이 가능하다.
- Gemini, Groq, 자체 제한 한도 초과 시 429 안내 메시지가 표시된다.
- backend cold start, scale-up, provider 지연 상황에서도 프론트 로딩 상태가 유지된다.

다수 사용자가 동시에 접근하는 실제 운영 공개 전에는 [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)의 용량, 보안, rate limit, 모니터링 항목까지 확인한다.

## 7. 장애 대응

- `429 Too Many Requests`: 자체 rate limit 또는 LLM provider quota 초과다. 잠시 뒤 재시도하거나 앱 한도와 Gemini quota를 확인한다.
- `413 Request Entity Too Large`: provider의 tokens-per-minute 한도보다 요청이 크다. prompt 길이, output token, provider TPM 한도를 확인한다.
- `502 Bad Gateway`: LLM 응답 실패 또는 JSON schema 검증 실패다. Render logs에서 provider error body를 확인한다.
- `504 Gateway Timeout`: LLM 응답 시간이 초과됐다. 필요하면 `GEMINI_TIMEOUT_SECONDS=90` 또는 `GROQ_TIMEOUT_SECONDS=90`으로 올린다.
- 첫 요청이 느림: backend cold start, scale-up, provider 지연을 확인한다.
- 관리자 프롬프트 수정 불가: Render의 `ENABLE_ADMIN_PROMPTS=true`, `ADMIN_API_KEY`, `CORS_ORIGINS` 설정을 확인한다.

## 8. 확장 기준

사용자가 꾸준히 들어오면 다음 순서로 확장을 검토한다.

1. Render backend instance size를 올리거나 worker/instance 확장 방식을 정한다.
2. Gemini quota 사용률을 보고 `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE`를 `300`, `400-500` 순서로 올린다.
3. 관리자 프롬프트 편집을 운영에서 계속 사용할 경우 SQLite 대신 Neon 또는 Supabase Postgres로 이전한다.
