import { createClient } from "@/lib/supabase/client";
import { LOCAL_DEMO_BEARER_TOKEN, hasLocalDemoSession, isLocalDemoMode } from "@/lib/localDemo";

export type CalendarType = "solar" | "lunar";
export type Gender = "male" | "female" | "other";
export type QuestionType = "single_choice" | "short_text";
export type ConcernCategory = "romance" | "career" | "finance" | "health" | "academics" | "others";
export type ReadingStyle = "traditional" | "empathetic" | "direct";
export type ReadingSessionStatus = "payment_required" | "paid" | "fixed_questions_ready" | "custom_questions_ready" | "final_ready" | "failed";

export interface BirthInfo {
  calendar_type: CalendarType;
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  is_leap_month: boolean;
  city: string;
  longitude: number | null;
  use_solar_time: boolean;
}

export interface InitialProfile {
  name: string;
  gender: Gender;
  birth: BirthInfo;
  initial_concern: string;
}

export interface PillarDetail {
  pillar: string;
  stem: string;
  branch: string;
  stem_element: string;
  branch_element: string;
  stem_yin_yang: "yang" | "yin";
  branch_yin_yang: "yang" | "yin";
  stem_ten_god: string | null;
  branch_ten_god: string | null;
}

export interface DaewoonPeriod {
  order: number;
  age_start: number;
  age_end: number;
  start_year: number;
  pillar: string;
  stem: string;
  branch: string;
  stem_ten_god: string;
  main_element: string;
}

export interface SajuData {
  solar_date: string;
  lunar_date: Record<string, unknown>;
  birth_time: string;
  pillars: Record<"year" | "month" | "day" | "hour", PillarDetail>;
  day_master: string;
  day_master_element: string;
  elements_count: Record<string, number>;
  ten_gods: Record<string, string>;
  daewoon: DaewoonPeriod[];
  calculation_note: string;
  raw: Record<string, unknown>;
}

export interface QuestionOption {
  id: string;
  label: string;
}

export interface DiagnosticQuestion {
  id: string;
  type: QuestionType;
  text: string;
  options: QuestionOption[];
  intent_signal: string;
}

export interface QuestionAnswer {
  question_id: string;
  question: string;
  answer: string;
  selected_option_ids: string[];
}

export interface ResponseMeta {
  provider: string;
  model: string;
  raw_metadata: Record<string, unknown>;
}

export interface GenerateQuestionsResponse {
  saju: SajuData;
  category: ConcernCategory;
  category_label: string;
  questions: DiagnosticQuestion[];
  meta: ResponseMeta;
}

export interface GenerateCustomQuestionsResponse {
  questions: DiagnosticQuestion[];
  meta: ResponseMeta;
}

export interface ReadingCareSection {
  title: string;
  headline: string;
  summary: string;
  detail: string;
}

export interface LuckRecipeItem {
  category: string;
  item: string;
  reason: string;
}

export interface FinalReading {
  reading_title: string;
  core_message: string;
  situation_mirror: ReadingCareSection;
  saju_insight: ReadingCareSection;
  clear_solution: ReadingCareSection;
  saju_vibe: ReadingCareSection;
  secret_talent: ReadingCareSection;
  answer_signals: string[];
  answer_signal_summary: string;
  saju_basis: string[];
  timing_points: string[];
  luck_recipe: LuckRecipeItem[];
  re_engagement_hook: {
    title: string;
    body: string;
  };
  caution: string;
}

export interface FinalReadingResponse {
  saju: SajuData;
  reading: FinalReading;
  meta: ResponseMeta;
}

export interface ReadingSessionResponse {
  id: string;
  user_id: string;
  order_id: string | null;
  status: ReadingSessionStatus;
  reading_style: ReadingStyle;
  initial_profile: InitialProfile;
  saju: SajuData | null;
  category: ConcernCategory | null;
  category_label: string | null;
  fixed_questions: DiagnosticQuestion[] | null;
  fixed_answers: QuestionAnswer[] | null;
  custom_questions: DiagnosticQuestion[] | null;
  custom_answers: QuestionAnswer[] | null;
  final_result: FinalReadingResponse | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CheckoutResponse {
  order_id: string;
  payment_id: string;
  store_id: string;
  channel_key: string;
  order_name: string;
  total_amount: number;
  currency: "KRW";
  notice_urls: string[];
}

export interface PaymentCompleteResponse {
  order_id: string;
  session_id: string | null;
  payment_id: string;
  status: string;
  credit_status: string | null;
}

export interface AccountMeResponse {
  id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  provider: string | null;
}

export interface AccountOrderResponse {
  id: string;
  payment_id: string;
  product_code: string;
  order_name: string;
  amount_krw: number;
  currency: string;
  status: string;
  paid_at: string | null;
  created_at: string | null;
}

export interface AccountReadingResponse {
  id: string;
  status: ReadingSessionStatus;
  reading_style: ReadingStyle;
  order_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  has_final_result: boolean;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function apiBaseUrl() {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    (typeof window === "undefined" ? "http://localhost:8000" : `${window.location.protocol}//${window.location.hostname}:8000`);

  return baseUrl.replace(/\/+$/, "");
}

function apiUrl(path: string) {
  return `${apiBaseUrl()}/${path.replace(/^\/+/, "")}`;
}

async function authHeaders() {
  if (isLocalDemoMode()) {
    if (!hasLocalDemoSession()) {
      throw new ApiError("로그인이 필요합니다.", 401);
    }
    return {
      Authorization: `Bearer ${LOCAL_DEMO_BEARER_TOKEN}`,
    };
  }

  let supabase: ReturnType<typeof createClient>;
  try {
    supabase = createClient();
  } catch (err) {
    throw new ApiError(err instanceof Error ? err.message : "로그인 설정을 확인해주세요.", 503);
  }
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new ApiError("로그인이 필요합니다.", 401);
  }
  return {
    Authorization: `Bearer ${session.access_token}`,
  };
}

async function readResponse<TResponse>(response: Response): Promise<TResponse> {
  if (!response.ok) {
    let message =
      response.status === 401
        ? "로그인이 필요합니다."
        : response.status === 402
          ? "결제가 필요합니다."
          : response.status === 429
            ? "요청 한도에 도달했어요. 잠시 뒤 다시 시도해주세요."
            : `요청이 실패했어요. (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(" / ") || message;
      }
    } catch {
      // Keep the generic message.
    }
    throw new ApiError(message, response.status);
  }
  return response.json();
}

async function requestJson<TResponse>(method: "GET" | "POST" | "PUT", path: string, payload?: unknown): Promise<TResponse> {
  const headers: Record<string, string> = {
    ...(await authHeaders()),
  };
  if (payload !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(apiUrl(path), {
    method,
    headers,
    body: payload === undefined ? undefined : JSON.stringify(payload),
    cache: "no-store",
  });
  return readResponse<TResponse>(response);
}

export function createReadingSession(payload: InitialProfile & { reading_style: ReadingStyle }): Promise<ReadingSessionResponse> {
  return requestJson<ReadingSessionResponse>("POST", "/api/reading-sessions", payload);
}

export function getReadingSession(sessionId: string): Promise<ReadingSessionResponse> {
  return requestJson<ReadingSessionResponse>("GET", `/api/reading-sessions/${sessionId}`);
}

export function createCheckout(sessionId: string, productCode = "SAJU_FULL_READING"): Promise<CheckoutResponse> {
  return requestJson<CheckoutResponse>("POST", "/api/payments/checkout", {
    session_id: sessionId,
    product_code: productCode,
  });
}

export function completePayment(paymentId: string): Promise<PaymentCompleteResponse> {
  return requestJson<PaymentCompleteResponse>("POST", "/api/payments/complete", {
    payment_id: paymentId,
  });
}

export function generateQuestions(sessionId: string): Promise<GenerateQuestionsResponse> {
  return requestJson<GenerateQuestionsResponse>("POST", `/api/reading-sessions/${sessionId}/generate-questions`);
}

export function saveFixedAnswers(sessionId: string, fixedAnswers: QuestionAnswer[]): Promise<ReadingSessionResponse> {
  return requestJson<ReadingSessionResponse>("PUT", `/api/reading-sessions/${sessionId}/fixed-answers`, {
    fixed_answers: fixedAnswers,
  });
}

export function generateCustomQuestions(sessionId: string): Promise<GenerateCustomQuestionsResponse> {
  return requestJson<GenerateCustomQuestionsResponse>("POST", `/api/reading-sessions/${sessionId}/generate-custom-questions`);
}

export function saveCustomAnswers(sessionId: string, customAnswers: QuestionAnswer[]): Promise<ReadingSessionResponse> {
  return requestJson<ReadingSessionResponse>("PUT", `/api/reading-sessions/${sessionId}/custom-answers`, {
    custom_answers: customAnswers,
  });
}

export function requestFinalReading(sessionId: string): Promise<FinalReadingResponse> {
  return requestJson<FinalReadingResponse>("POST", `/api/reading-sessions/${sessionId}/final-reading`);
}

export function getAccountMe(): Promise<AccountMeResponse> {
  return requestJson<AccountMeResponse>("GET", "/api/account/me");
}

export function getAccountOrders(): Promise<AccountOrderResponse[]> {
  return requestJson<AccountOrderResponse[]>("GET", "/api/account/orders");
}

export function getAccountReadings(): Promise<AccountReadingResponse[]> {
  return requestJson<AccountReadingResponse[]>("GET", "/api/account/readings");
}
