# 실제 운영 배포 점검리스트

이 문서는 `frontend` Next.js, `backend` FastAPI, 외부 LLM provider(Gemini/Groq) 조합을 실제 사용자 트래픽에 노출하기 전 확인할 항목이다. 목표는 "절대 장애 없음"이 아니라, 장애를 줄이고 빠르게 감지하며, 과부하 때 서비스가 무너지지 않게 제한하고 복구하는 것이다.

기준이 된 주요 구현:

- [backend/app/services/rate_limiter.py](backend/app/services/rate_limiter.py): 현재 LLM endpoint rate limit
- [backend/app/services/supabase_auth.py](backend/app/services/supabase_auth.py): Supabase access token 검증
- [backend/app/services/reading_repository.py](backend/app/services/reading_repository.py): Supabase Postgres order/session/credit 원장
- [backend/app/services/payment_reconciliation.py](backend/app/services/payment_reconciliation.py): PortOne 결제 조회 검증과 credit 지급
- [backend/app/config.py](backend/app/config.py): CORS, timeout, token, provider 환경변수
- [backend/app/api/routes/saju.py](backend/app/api/routes/saju.py): LLM 호출, 오류 변환, schema 검증
- [frontend/lib/api.ts](frontend/lib/api.ts): frontend API base URL과 fetch 오류 처리

## 0. 현재 구조에서 먼저 알아야 할 운영 리스크

| 영역 | 예상 문제 | 현재 상태 | 운영 전 조치 |
| --- | --- | --- | --- |
| LLM 호출 | `/api/reading-sessions/{id}/generate-custom-questions`, `/api/reading-sessions/{id}/final-reading`가 긴 외부 API 호출에 의존한다. provider 지연, 429, 503, JSON 오류가 사용자 오류로 이어진다. | timeout, schema 검증, 결제 credit gate가 있음 | provider quota 산정, canary 테스트, 429/503 대응 문구와 알림 필요 |
| 동시 사용자 제한 | 현재 rate limiter는 `InMemoryRateLimiter`라 프로세스 메모리 기준이다. 재시작 시 초기화되고, 여러 worker/instance에서는 전역 한도를 보장하지 못한다. | Gemini 3.1 Flash-Lite 유료 기준 기본값은 `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE=200`, `LLM_RATE_LIMIT_PER_IP_PER_HOUR=40` | 트래픽을 보며 `300`, `400-500`으로 올리고, 다중 인스턴스 운영 전 Redis/Upstash 기반 분산 rate limit으로 이전 |
| 백엔드 인스턴스 | 수면 상태가 있는 저가/테스트용 인스턴스는 cold start가 있고 LLM 요청이 길면 첫 사용자가 오래 기다린다. | `DEPLOYMENT.md`는 Gemini paid 운영 기준으로 갱신됨 | 공개 운영 전 Render paid instance 또는 대체 backend로 전환 |
| 인증/결제 원장 | 로그인, 결제, credit 상태가 DB와 외부 provider에 의존한다. | Supabase Auth/Postgres와 PortOne V2로 전환됨 | redirect URL, RLS, webhook, amount/currency 검증을 staging에서 확인 |
| 관리자 설정 저장 | 기존 admin prompt/model 설정은 운영 비활성화됐다. | `ENABLE_ADMIN_PROMPTS=false`, admin UI 제거 | 재활성화 전 Supabase-authenticated admin_members와 감사 로그를 구현 |
| CORS | 기본 regex는 로컬 개발망을 허용한다. 운영에서 그대로 두면 원치 않는 origin을 허용할 수 있다. | `CORS_ORIGIN_REGEX` 기본값 있음 | Production에서는 `CORS_ORIGIN_REGEX=`로 비우고 `CORS_ORIGINS`만 정확히 설정 |
| 관리자 보안 | shared password 방식은 제거 대상이다. | 프론트 admin page 제거, backend admin router는 `ENABLE_ADMIN_PROMPTS=false` | 후속 구현 전까지 운영에서 켜지 않는다 |
| 관측성 | `/health`는 있으나 request id, endpoint별 latency/error/provider quota dashboard가 없다. | LLM debug header 옵션 있음 | 운영 로그, 알림, provider 사용량 모니터링 구성 |

## 1. 출시 전 의사결정 기준

아래 항목 중 하나라도 해당하면 단순 테스트 배포 수준으로는 부족하고, "많은 사용자가 동시에 사용하는 운영 서비스" 기준으로 준비해야 한다.

- [ ] 하루 수십 명 이상이 동시에 접속할 가능성이 있다.
- [ ] 유료 광고, SNS 공개, 인플루언서 공유 등 트래픽 급증 가능성이 있다.
- [ ] 관리자 페이지에서 프롬프트/모델을 자주 바꿔야 한다. 현재 버전에서는 별도 후속 구현이 필요하다.
- [ ] 사용자 문의를 받을 수 있는 운영 채널이 열려 있다.
- [ ] 장애가 나면 신뢰도나 비용 손실이 발생한다.

하나라도 체크되면 공개 전 최소 조치:

- [ ] backend를 sleep 없는 paid instance로 전환한다.
- [ ] LLM provider quota를 확인하고 예상 동시 사용자보다 30-50% 이상 여유를 둔다.
- [ ] rate limiter를 Redis/Upstash 같은 외부 저장소 기반으로 바꾼다.
- [ ] prompt/model 설정을 운영에서 다시 켤 경우 Supabase Postgres 저장소와 감사 로그를 먼저 구현한다.
- [ ] 로그, 알림, rollback 절차를 준비한다.

## 2. 용량 산정 체크

현재 전체 심리 리딩 1회는 보통 LLM endpoint 2회를 사용한다.

1. `/api/reading-sessions/{id}/generate-questions`: LLM 없음, 사주 계산 및 고정 질문. 로그인과 결제 필요
2. `/api/reading-sessions/{id}/generate-custom-questions`: LLM 1회. 로그인과 결제 필요
3. `/api/reading-sessions/{id}/final-reading`: LLM 1회. 성공 후 credit 소비

따라서 운영 기본값 `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE=200`에서는 이론상 전체 리딩 완료량이 분당 최대 약 100회다. 이것은 Gemini 한도가 아니라 앱이 자체적으로 걸어둔 보호 한도다.

Gemini 3.1 Flash-Lite 유료 active limit 기준:

| 항목 | active limit | 리딩 기준 의미 |
| --- | ---: | --- |
| RPM | 약 4,000 requests/min | RPM만 보면 전체 리딩 약 2,000회/min까지 가능하지만, 실제로는 TPM과 backend가 먼저 병목이 된다. |
| TPM | 약 4,000,000 tokens/min | 리딩 1회가 10k tokens면 약 400회/min, 15k tokens면 약 266회/min, 20k tokens면 약 200회/min이 이론 한계다. |
| RPD | 약 150,000 requests/day | 전체 리딩 기준 하루 최대 약 75,000회다. |

권장 production 시작값:

```env
GEMINI_MODEL=gemini-3.1-flash-lite-preview
RATE_LIMIT_ENABLED=true
LLM_RATE_LIMIT_GLOBAL_PER_MINUTE=200
LLM_RATE_LIMIT_PER_IP_PER_HOUR=40
LLM_CUSTOM_QUESTIONS_MAX_OUTPUT_TOKENS=1200
LLM_FINAL_READING_MAX_OUTPUT_TOKENS=5000
```

이 설정은 앱 기준으로 LLM 호출을 분당 200회까지 허용한다. 전체 리딩은 LLM 2회를 쓰므로 분당 약 100명까지 완료 가능하다. 같은 IP에서는 시간당 LLM 40회, 즉 전체 리딩 약 20회까지 허용한다.

증설 기준:

- [ ] launch 후 30-60분 동안 5xx 비율이 1% 이하이면 `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE=300`으로 올릴 수 있다.
- [ ] Gemini dashboard에서 TPM 사용률이 피크에도 70% 이하이고 backend p95가 안정적이면 `400-500`까지 올릴 수 있다.
- [ ] `500`은 전체 리딩 약 250회/min이다. 리딩 1회 평균이 15k tokens를 넘으면 TPM 4,000,000에 가까워질 수 있으므로 token metric 확인 전에는 넘기지 않는다.
- [ ] 24시간 내내 최대 트래픽이 유지되면 RPD 150,000을 소진할 수 있다. 일일 사용량 알림을 반드시 둔다.

배포 전 확인:

- [ ] 예상 피크 동시 사용자 수를 정한다. 예: 10명, 50명, 100명.
- [ ] 사용자가 한 번 리딩을 완료할 때 평균 LLM 호출 수를 2회로 계산한다.
- [ ] Gemini 3.1 Flash-Lite active limit이 RPM 약 4,000, TPM 약 4,000,000, RPD 약 150,000으로 표시되는지 확인한다.
- [ ] `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE=200`으로 시작하고, 로그를 보며 `300`, `400-500` 순서로 올린다.
- [ ] `LLM_RATE_LIMIT_PER_IP_PER_HOUR=40`은 사용자 1명당 전체 리딩 약 20회/hour를 의미한다. 공유 Wi-Fi 사용자가 많으면 `60`까지 올릴 수 있다.
- [ ] 다중 worker/instance를 켤 예정이면 현재 in-memory limiter를 먼저 교체한다. 그렇지 않으면 worker 수만큼 실제 한도가 증가한다.
- [ ] Gemini/Groq 각각의 fallback 운영 방식을 정한다. 예: 환경변수 배포 변경으로 Gemini 장애 시 Groq로 전환.
- [ ] 모델 전환 시 JSON schema 출력 성공률을 staging에서 먼저 확인한다.

## 3. 환경변수 체크

Backend production:

- [ ] `LLM_PROVIDER=gemini` 또는 운영 provider로 고정한다.
- [ ] `GEMINI_API_KEY` 또는 `GROQ_API_KEY`가 배포 환경에만 있고 git에는 없다.
- [ ] `GEMINI_MODEL=gemini-3.1-flash-lite-preview` 또는 AI Studio에서 확인한 실제 모델 id다.
- [ ] `GEMINI_TIMEOUT_SECONDS`/`GROQ_TIMEOUT_SECONDS`는 provider p95 응답 시간보다 길고 platform timeout보다 짧다.
- [ ] `LLM_CUSTOM_QUESTIONS_MAX_OUTPUT_TOKENS=1200`로 맞춤 질문 응답이 안정적으로 나온다.
- [ ] `LLM_FINAL_READING_MAX_OUTPUT_TOKENS=5000`로 최종 리딩이 잘리지 않는다.
- [ ] `RATE_LIMIT_ENABLED=true`다.
- [ ] `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE=200`으로 시작한다. 충분히 안정적이면 `300-500`까지 단계적으로 올린다.
- [ ] `CORS_ORIGINS=https://<production-frontend-domain>`만 포함한다.
- [ ] `CORS_ORIGIN_REGEX=`로 비워 운영에서 개발 origin 허용을 끈다.
- [ ] `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`이 backend에만 정확히 설정되어 있다.
- [ ] `PORTONE_API_SECRET`, `PORTONE_WEBHOOK_SECRET`, `PORTONE_STORE_ID`, `PORTONE_CHANNEL_KEY`, `PORTONE_WEBHOOK_URL`이 backend에 설정되어 있다.
- [ ] admin 기능은 이번 버전에서 `ENABLE_ADMIN_PROMPTS=false`다.

Frontend production:

- [ ] `NEXT_PUBLIC_API_BASE_URL=https://<production-backend-domain>`이다.
- [ ] `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_PORTONE_STORE_ID`, `NEXT_PUBLIC_PORTONE_CHANNEL_KEY`가 설정되어 있다.
- [ ] `SUPABASE_SERVICE_ROLE_KEY`, `PORTONE_API_SECRET`, `PORTONE_WEBHOOK_SECRET`은 frontend 환경변수에 없다.
- [ ] Preview와 Production 환경변수를 구분한다.
- [ ] Vercel Output Directory override가 비어 있고 Framework Preset이 Next.js다.
- [ ] 브라우저에 admin page가 노출되지 않는지 확인한다.

Secrets:

- [ ] `backend/.env`는 untracked 상태이며 커밋하지 않는다.
- [ ] provider key는 최소 권한 계정으로 발급한다.
- [ ] key 노출 시 즉시 폐기/재발급 절차가 있다.
- [ ] 운영자 퇴사 또는 외부 공유 후 key rotation 절차가 있다.

## 4. 배포 전 로컬 검증

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

수동 확인:

- [ ] `/health`가 `{"status":"ok"}`를 반환한다.
- [ ] 비로그인 상태에서 시작하면 `/login`으로 이동한다.
- [ ] Google OAuth 로그인 후 `/auth/callback`에서 세션이 만들어진다.
- [ ] 결제 전 protected API가 `402`를 반환한다.
- [ ] PortOne 테스트 결제 후 order `paid`, credit `available`이 된다.
- [ ] 초기 고민 입력 후 결제 완료 상태에서 고정 질문 q1-q3, 선택 q4가 표시된다.
- [ ] 맞춤 질문 q5-q7, 선택 q8이 표시된다.
- [ ] 최종 리딩이 JSON 파싱 오류 없이 표시된다.
- [ ] 429 응답 시 사용자에게 재시도 안내가 나온다.
- [ ] LLM provider key가 없을 때 502로 실패하고 서버 로그에서 원인이 보인다.
- [ ] `/admin/prompts` frontend page가 노출되지 않는다.
- [ ] backend admin router는 `ENABLE_ADMIN_PROMPTS=false` 상태에서 `/api/admin/prompts`를 노출하지 않는다.
- [ ] admin UI 파일이 frontend bundle에 포함되지 않는다.

## 5. 부하 테스트 체크

LLM endpoint는 비용과 quota를 소모하므로 무작정 대량 부하를 걸지 않는다. 단계적으로 확인한다.

무해한 endpoint:

- [ ] `/health`를 1분간 높은 동시성으로 호출해 backend 자체 응답성과 platform 안정성을 본다.
- [ ] 테스트 계정과 테스트 결제 상태에서 `/api/reading-sessions/{id}/generate-questions`를 낮은 동시성으로 호출해 LLM 없는 계산 경로를 본다.

LLM endpoint:

- [ ] production provider가 아닌 staging key나 낮은 트래픽 시간에만 테스트한다.
- [ ] 동시 2명, 5명, 10명 순서로 올린다.
- [ ] `/api/reading-sessions/{id}/generate-custom-questions`와 `/api/reading-sessions/{id}/final-reading` 각각 p50, p95, 실패율을 기록한다.
- [ ] 429가 예상한 시점에 발생하고, 서버가 5xx 폭증 없이 버티는지 확인한다.
- [ ] provider dashboard에서 RPM/TPM/비용 증가가 예상 범위인지 확인한다.
- [ ] 같은 IP에서 반복 호출 시 `LLM_RATE_LIMIT_PER_IP_PER_HOUR`가 동작하는지 확인한다.

권장 통과 기준:

- [ ] `/health` p95가 300ms 이하.
- [ ] LLM 없는 endpoint p95가 1초 이하.
- [ ] LLM endpoint p95가 `GEMINI_TIMEOUT_SECONDS` 또는 `GROQ_TIMEOUT_SECONDS`의 80% 이하.
- [ ] 5xx 비율이 1% 이하. provider 일시 오류는 별도 집계한다.
- [ ] 429 비율이 운영 정책상 허용한 범위 안이다.
- [ ] backend memory가 지속 증가하지 않는다.

## 6. 동시 사용자 안정화 체크

현재 상태에서 다수 동시 사용자 운영 시 필수 보강:

- [ ] `InMemoryRateLimiter`를 Redis/Upstash 기반으로 교체한다.
- [ ] IP 기준 rate limit은 `x-forwarded-for` 신뢰 체계를 명확히 한다. platform proxy가 외부 조작 헤더를 정리하는지 확인한다.
- [ ] provider 429와 자체 429를 로그에서 구분한다.
- [ ] LLM 요청에 request id를 붙여 frontend 오류, backend 로그, provider 오류를 연결한다.
- [ ] 중복 클릭/새로고침으로 같은 LLM 요청이 반복되지 않도록 client button disabled 상태를 확인한다.
- [ ] 필요하면 동일 입력에 대한 짧은 TTL cache를 추가한다. 단, 생년월일/고민/답변은 민감정보이므로 해시 키와 보관 기간을 명확히 한다.
- [ ] 트래픽 급증 시 즉시 `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE`를 낮출 수 있는 운영 절차가 있다.
- [ ] provider 장애 시 환경변수로 다른 provider/model로 전환하는 절차가 있다.
- [ ] 장기적으로는 LLM 호출을 queue/job 방식으로 분리할지 검토한다. 현재 구조는 요청이 끝날 때까지 브라우저가 기다린다.

## 7. 데이터와 개인정보 체크

이 앱은 이름, 생년월일시, 고민, 답변처럼 민감할 수 있는 정보를 외부 LLM provider로 전송한다.

- [ ] 개인정보 처리방침에 전송 대상, 보관 여부, 목적을 명시한다.
- [ ] 사용자 리딩 세션, 답변, 최종 결과가 Supabase Postgres에 저장된다는 점을 개인정보 처리방침에 반영한다.
- [ ] 로그에 `initial_concern`, `answers`, 생년월일 전체를 남기지 않는다.
- [ ] LLM provider의 데이터 보관/학습 정책을 확인하고 사용자 안내에 반영한다.
- [ ] Supabase 백업, 암호화, 삭제 요청 처리 기준을 정한다.
- [ ] 서비스 문구에 의료, 법률, 투자 결정이 아닌 참고용이라는 안내를 둔다.

## 8. 관리자 기능 보안 체크

- [ ] 운영 기본값은 `ENABLE_ADMIN_PROMPTS=false`다.
- [ ] frontend `/admin/prompts`는 제거된 상태다.
- [ ] shared password, `X-Admin-Key`, browser `localStorage` 관리자 인증을 다시 도입하지 않는다.
- [ ] admin 재활성화 전 Supabase Auth `admin_members`, 감사 로그, 별도 rate limit을 구현한다.
- [ ] prompt/model 변경 후 staging 또는 preview에서 한 번 전체 리딩을 검증하는 절차를 둔다.

## 9. 관측성과 알림 체크

배포 전 최소 로그:

- [ ] method, path, status code, duration_ms
- [ ] request id
- [ ] client IP 또는 익명화된 식별자
- [ ] LLM provider, model, schema name
- [ ] provider status code/error type
- [ ] prompt/completion/total token 수. 원문 prompt는 기록하지 않는다.
- [ ] 자체 rate limit reject count
- [ ] provider rate limit reject count
- [ ] JSON parse/schema validation failure count

알림 기준:

- [ ] 5분 동안 5xx 비율 3% 초과.
- [ ] 5분 동안 429 비율이 평소의 2배 이상.
- [ ] LLM endpoint p95가 timeout의 80% 초과.
- [ ] `/health` 실패가 2회 이상 연속.
- [ ] provider 503/overloaded가 5분 동안 5회 이상.
- [ ] 인증 endpoint 401이 짧은 시간에 반복된다.
- [ ] provider 비용/사용량이 일일 예산의 70%, 90%, 100%에 도달한다.

운영 중 임시 디버그:

- [ ] 문제 분석 때만 `LLM_DEBUG_METRICS_ENABLED=true`를 켠다.
- [ ] 디버그 헤더가 사용자 개인정보를 포함하지 않는지 확인한다.
- [ ] 분석 후 다시 false로 돌린다.

## 10. 배포 절차 체크

배포 전:

- [ ] `main` 또는 배포 브랜치가 최신이다.
- [ ] backend tests가 통과한다.
- [ ] frontend build가 통과한다.
- [ ] env var 변경 내역을 기록했다.
- [ ] rollback할 이전 backend/frontend deployment URL을 알고 있다.
- [ ] provider dashboard와 platform logs를 열어둔다.

배포 중:

- [ ] backend 먼저 배포한다.
- [ ] `/health` 확인 후 frontend를 배포한다.
- [ ] frontend `NEXT_PUBLIC_API_BASE_URL`이 새 backend를 가리키는지 확인한다.
- [ ] CORS error가 없는지 브라우저 console/network에서 확인한다.

배포 직후 smoke test:

- [ ] production frontend 첫 화면 로딩.
- [ ] `/health` 200.
- [ ] `사주만 보기` 성공.
- [ ] 전체 리딩 1회 성공.
- [ ] `/admin/prompts`가 404인지 확인.
- [ ] `/api/admin/prompts`가 404인지 확인.
- [ ] rate limit 설정이 의도대로 표시/동작.

트래픽 ramp:

- [ ] 처음 10-20명에게만 공개한다.
- [ ] 30분 동안 p95 latency, 429, 5xx, provider quota를 본다.
- [ ] 문제가 없으면 공개 범위를 늘린다.
- [ ] SNS/광고 공개 전 `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE`와 provider quota를 다시 확인한다.

## 11. 장애별 대응 Runbook

### 사용자가 "너무 오래 걸린다"고 말함

- [ ] Render sleep/cold start인지 확인한다.
- [ ] backend log에서 endpoint duration을 본다.
- [ ] provider dashboard에서 latency/overload를 본다.
- [ ] paid instance 전환 또는 min instance를 검토한다.
- [ ] `GEMINI_TIMEOUT_SECONDS`/`GROQ_TIMEOUT_SECONDS`를 올리기 전에 prompt 길이와 output token을 줄일 수 있는지 확인한다.

### 429가 많이 발생함

- [ ] 자체 429인지 provider 429인지 구분한다.
- [ ] 자체 429면 `LLM_RATE_LIMIT_GLOBAL_PER_MINUTE`가 너무 낮은지, abuse인지 확인한다.
- [ ] provider 429면 provider plan/quota/RPM/TPM을 확인한다.
- [ ] 일시적으로 frontend 안내 문구를 노출하거나 공개 유입을 멈춘다.
- [ ] 고트래픽이면 유료 plan 또는 provider fallback을 적용한다.

### 502가 발생함

- [ ] provider error인지 JSON/schema validation 실패인지 로그에서 본다.
- [ ] 최근 provider/model 환경변수 변경을 되돌린다.
- [ ] Gemini/Groq schema mode와 모델 호환성을 확인한다.
- [ ] 최종 리딩이 길어서 잘렸다면 output token과 prompt 길이를 조정한다.

### 504 timeout이 발생함

- [ ] provider가 느린지 backend platform timeout인지 확인한다.
- [ ] provider status page/dashboard를 본다.
- [ ] 더 빠른 모델로 전환하거나 output token을 줄인다.
- [ ] timeout을 올릴 때 frontend 사용자가 기다릴 수 있는 UX인지 같이 확인한다.

### CORS 오류

- [ ] backend `CORS_ORIGINS`에 정확한 frontend origin이 있는지 확인한다.
- [ ] origin에 trailing slash가 들어가지 않았는지 확인한다.
- [ ] production에서는 `CORS_ORIGIN_REGEX=`가 비어 있는지 확인한다.
- [ ] Vercel preview URL을 테스트하려면 preview origin을 별도로 추가한다.

### 결제 후 권한 없음

- [ ] `/api/payments/complete`가 PortOne payment를 조회했는지 확인한다.
- [ ] PortOne webhook URL과 webhook secret이 production backend와 일치하는지 확인한다.
- [ ] `orders.failure_reason`에 amount/currency/status mismatch가 기록됐는지 확인한다.
- [ ] `reading_credits.order_id` unique 제약으로 중복 지급이 막혔는지 확인한다.

## 12. 운영 전 개선 권장사항

우선순위 높음:

- [ ] Redis/Upstash 기반 rate limiter.
- [ ] request id middleware와 structured logging.
- [ ] admin 재활성화 시 Supabase Auth 기반 admin_members, rate limit, 변경 감사 로그.
- [ ] provider/model/prompt 변경 후 자동 smoke test.
- [ ] GitHub Actions로 backend pytest와 frontend build 자동화.

우선순위 중간:

- [ ] LLM provider fallback 정책.
- [ ] 사용자 입력 해시 기반 짧은 TTL cache.
- [ ] frontend fetch timeout/abort와 재시도 안내.
- [ ] provider token/cost dashboard.
- [ ] status page 또는 장애 공지 위치.

우선순위 낮음:

- [ ] queue/job 기반 비동기 리딩 생성.
- [ ] 사용자별 리딩 내역 저장. 단, 개인정보/삭제 정책을 먼저 설계한다.
- [ ] A/B prompt 실험. 단, 비용/품질 지표가 준비된 뒤 진행한다.
