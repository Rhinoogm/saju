# Saju MVP 무료 배포 가이드

이 프로젝트는 무료 공개 데모 기준으로 프론트엔드와 백엔드를 분리해서 배포한다.

- Frontend: Vercel Hobby, root directory `frontend/`
- Backend: Render Free Web Service, root directory `backend/`
- LLM: Groq Free API, `LLM_PROVIDER=groq`

무료 플랜 제약을 전제로 한다. Render Free는 15분 유휴 후 수면 상태가 될 수 있고, Groq Free는 모델별 요청/토큰 한도가 있다. Vercel Hobby는 개인/비상업 용도 기준으로 사용한다.

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

## 2. Groq API Key

Groq Console에서 API key를 만든다. 추천 모델은 `openai/gpt-oss-20b`다. 현재 백엔드의 Groq provider는 이 모델에서 JSON Schema response format을 사용한다.

Groq 무료 한도는 계정과 조직 기준으로 적용된다. 최신 한도는 Groq Console의 rate limit 문서를 확인한다.

## 3. Render Backend

Render Dashboard에서 `New > Web Service`를 선택하고 GitHub repo를 연결한다.

설정값:

- Name: `saju-backend`
- Root Directory: `backend`
- Runtime: `Python 3`
- Instance Type: `Free`
- Build Command: `python -m pip install -e .`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

환경변수:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=<your-groq-api-key>
GROQ_MODEL=openai/gpt-oss-20b
GROQ_RESPONSE_FORMAT_MODE=auto
GROQ_JSON_SCHEMA_STRICT=true
GROQ_TIMEOUT_SECONDS=60

ENABLE_ADMIN_PROMPTS=false
CORS_ORIGINS=https://saju-frontend.vercel.app
CORS_ORIGIN_REGEX=

RATE_LIMIT_ENABLED=true
LLM_RATE_LIMIT_PER_IP_PER_HOUR=6
LLM_RATE_LIMIT_GLOBAL_PER_MINUTE=25
```

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
ENABLE_ADMIN_PROMPTS=false
```

Production과 Preview 환경에 같은 값으로 시작한다.

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
- `심리 리딩 질문 받기`가 질문 5개를 생성한다.
- `최종 풀이 보기`가 JSON 파싱 오류 없이 결과 화면을 표시한다.
- `/admin/prompts`는 `ENABLE_ADMIN_PROMPTS=true`가 아니면 404를 반환한다.
- Groq나 자체 제한 한도 초과 시 429 안내 메시지가 표시된다.
- Render가 잠든 뒤 첫 요청에서 지연이 있어도 프론트 로딩 상태가 유지된다.

## 7. 장애 대응

- `429 Too Many Requests`: 자체 rate limit 또는 Groq Free 한도 초과다. 잠시 뒤 재시도한다.
- `502 Bad Gateway`: Groq 응답 실패 또는 JSON schema 검증 실패다. Render logs에서 Groq error body를 확인한다.
- `504 Gateway Timeout`: LLM 응답 시간이 초과됐다. 필요하면 `GROQ_TIMEOUT_SECONDS=90`으로 올린다.
- 첫 요청이 느림: Render Free 콜드 스타트로 볼 수 있다.
- 관리자 프롬프트 수정 불가: 공개 배포에서는 의도적으로 비활성화한 상태다.

## 8. 유료 전환 기준

사용자가 꾸준히 들어오면 다음 순서로 유료 전환을 검토한다.

1. Render backend를 paid instance로 전환해 콜드 스타트를 제거한다.
2. Groq Developer plan으로 rate limit을 늘린다.
3. 관리자 프롬프트 편집을 다시 켤 경우 SQLite 대신 Neon 또는 Supabase Postgres로 이전한다.
