export type CalendarType = "solar" | "lunar";
export type Gender = "male" | "female" | "other";
export type QuestionType = "single_choice";
export type ReadingStyle = "traditional" | "empathetic" | "direct";

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

export interface TimeLuckPillar {
  label: string;
  year: number;
  month: number | null;
  representative_date: string;
  pillar: string;
  stem: string;
  branch: string;
  stem_element: string;
  branch_element: string;
  stem_yin_yang: "yang" | "yin";
  branch_yin_yang: "yang" | "yin";
  stem_ten_god: string;
  branch_ten_god: string;
}

export interface CurrentLuck {
  reference_date: string;
  annual: TimeLuckPillar;
  next_month: TimeLuckPillar;
}

export interface TenGodScore {
  name: string;
  score: number;
  count: number;
  positions: string[];
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
  ten_god_scores: TenGodScore[];
  dominant_ten_god: TenGodScore;
  daewoon: DaewoonPeriod[];
  current_luck: CurrentLuck;
  yonghuishin: YonghuishinAnalysis;
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
  question: DiagnosticQuestion;
  meta: ResponseMeta;
}

export interface GenerateNextQuestionRequest extends InitialProfile {
  answers: QuestionAnswer[];
}

export interface GenerateNextQuestionResponse {
  question: DiagnosticQuestion;
  meta: ResponseMeta;
}

export interface CompassSummary {
  headline: string;
  basis: string;
  solution: string;
  strength_animal: string;
}

export interface ManseSummary {
  headline: string;
  energy_overview: string;
  key_traits: string[];
}

export interface YonghuishinCandidate {
  element: string;
  score: number | null;
  reason: string;
}

export interface GeokgukYongshinCandidate extends YonghuishinCandidate {
  ten_god: string | null;
  stem: string | null;
}

export interface DayMasterStrength {
  support_score: number;
  drain_score: number;
  strength_index: number;
  label: string;
  evidence: string[];
}

export interface GeokgukMonthSource {
  month_branch: string;
  selected_hidden_stem: string;
  ten_god: string;
  transmitted: boolean;
}

export interface GeokgukAnalysis {
  name: string;
  selected_from_month: GeokgukMonthSource;
  confidence: number;
  damage: string[];
}

export interface SpecialGeokCandidate {
  name: string;
  confidence: number;
  reason: string;
}

export interface YongshinAnalysis {
  eokbu_yongshin: YonghuishinCandidate[];
  geokguk_yongshin: GeokgukYongshinCandidate[];
  johwu_yongshin: YonghuishinCandidate[];
  final_yongshin: YonghuishinCandidate[];
  huishin: YonghuishinCandidate[];
  gishin: YonghuishinCandidate[];
}

export interface YonghuishinInterpretation {
  summary: string;
  strength_reading: string;
  geokguk_reading: string;
  yongshin_reading: string;
}

export interface YonghuishinAnalysis {
  element_power: Record<string, number>;
  strength: DayMasterStrength;
  geokguk: GeokgukAnalysis;
  special_geok_candidates: SpecialGeokCandidate[];
  yongshin: YongshinAnalysis;
  interpretation: YonghuishinInterpretation;
}

export interface DualReadingSection {
  title: string;
  headline: string;
  body: string;
}

export interface DualReading {
  weapon: DualReadingSection;
  growth_hint: DualReadingSection;
}

export interface HealingCard {
  metaphor_sentence: string;
  affirmation: string;
  lucky_element: string;
  color: string;
  direction: string;
  ritual: string;
  interpretation: string;
}

export interface SecretDoor {
  unexplored_area: string;
  next_month_signal: string;
  teaser: string;
}

export interface FinalReading {
  reading_title: string;
  compass_summary: CompassSummary;
  manse_summary: ManseSummary;
  dual_reading: DualReading;
  healing_card: HealingCard;
  secret_door: SecretDoor;
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

export function generateNextQuestion(payload: GenerateNextQuestionRequest): Promise<GenerateNextQuestionResponse> {
  return postJson<GenerateNextQuestionResponse>("/api/generate-next-question", payload);
}

export function requestFinalReading(payload: InitialProfile & { reading_style?: ReadingStyle; answers: QuestionAnswer[] }): Promise<FinalReadingResponse> {
  return postJson<FinalReadingResponse>("/api/final-reading", payload);
}

export function requestSajuOnly(payload: SajuOnlyRequest): Promise<SajuOnlyResponse> {
  return postJson<SajuOnlyResponse>("/api/saju-only", payload);
}
