export type CalendarType = "solar" | "lunar";
export type Gender = "male" | "female" | "other";
export type QuestionType = "single_choice" | "short_text";

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
  selected_option_id: string | null;
}

export interface ResponseMeta {
  provider: string;
  model: string;
  raw_metadata: Record<string, unknown>;
}

export interface GenerateQuestionsResponse {
  saju: SajuData;
  questions: DiagnosticQuestion[];
  meta: ResponseMeta;
}

export interface ReadingInsightCard {
  title: string;
  headline: string;
  body: string;
}

export interface ReadingSection {
  title: string;
  body: string;
}

export interface FinalReading {
  reading_title: string;
  desired_conclusion: string;
  core_message: string;
  final_text: string;
  summary_cards: ReadingInsightCard[];
  deep_sections: ReadingSection[];
  answer_signals: string[];
  saju_basis: string[];
  timing_points: string[];
  action_steps: string[];
  watchouts: string[];
  caution: string;
}

export interface FinalReadingResponse {
  saju: SajuData;
  reading: FinalReading;
  meta: ResponseMeta;
}

export interface SajuOnlyRequest {
  name: string;
  gender: Gender;
  birth: BirthInfo;
}

export interface SajuOnlyResponse {
  saju: SajuData;
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

async function postJson<TResponse>(path: string, payload: unknown): Promise<TResponse> {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message =
      response.status === 429
        ? "무료 공개 데모의 요청 한도에 도달했어요. 잠시 뒤 다시 시도해주세요."
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

export function generateQuestions(payload: InitialProfile): Promise<GenerateQuestionsResponse> {
  return postJson<GenerateQuestionsResponse>("/api/generate-questions", payload);
}

export function requestFinalReading(payload: InitialProfile & { answers: QuestionAnswer[] }): Promise<FinalReadingResponse> {
  return postJson<FinalReadingResponse>("/api/final-reading", payload);
}

export function requestSajuOnly(payload: SajuOnlyRequest): Promise<SajuOnlyResponse> {
  return postJson<SajuOnlyResponse>("/api/saju-only", payload);
}
