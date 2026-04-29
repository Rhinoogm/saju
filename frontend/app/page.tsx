"use client";

import { useState } from "react";
import { ClipboardCheck, DoorOpen, HeartHandshake, Landmark, LockKeyhole, Settings, X, type LucideIcon } from "lucide-react";
import { useRouter } from "next/navigation";

import { InitialForm } from "@/components/InitialForm";
import { QuestionsForm } from "@/components/QuestionsForm";
import { ReadingResult } from "@/components/ReadingResult";
import { SajuOnlyResult } from "@/components/SajuOnlyResult";
import {
  ApiError,
  DiagnosticQuestion,
  FinalReadingResponse,
  GenerateCustomQuestionsResponse,
  GenerateQuestionsResponse,
  InitialProfile,
  QuestionAnswer,
  ReadingStyle,
  generateCustomQuestions,
  generateQuestions,
  requestFinalReading,
  requestSajuOnly,
} from "@/lib/api";

type Step = "hall" | "initial" | "fixed" | "custom" | "result" | "saju";

const ADMIN_STORAGE_KEY = "saju_admin_api_key";

const readingStyleOptions: {
  style: ReadingStyle;
  nickname: string;
  description: string;
  icon: LucideIcon;
  accentClass: string;
}[] = [
  {
    style: "traditional",
    nickname: "어제 계룡산에서 123년 만에 내려온 스님",
    description: "정통 명리학의 깊이와 신뢰감을 담아 정중하고 명확하게 풀이합니다.",
    icon: Landmark,
    accentClass: "bg-ink text-white",
  },
  {
    style: "empathetic",
    nickname: "극F 나보다 내 사주 과몰입 사주 잘보는 언니",
    description: "감정을 먼저 안아주는 공감형 해석으로 위로와 지지를 중심에 둡니다.",
    icon: HeartHandshake,
    accentClass: "bg-coral text-white",
  },
  {
    style: "direct",
    nickname: "틀린 말은 아니라서 더 열받는 개발자 출신 명리학자",
    description: "위로보다 리스크와 행동 기준을 직설적으로 짚는 현실 분석형 풀이입니다.",
    icon: ClipboardCheck,
    accentClass: "bg-mint text-white",
  },
];

const defaultProfile: InitialProfile = {
  name: "김경민",
  gender: "male",
  initial_concern: "",
  birth: {
    calendar_type: "solar",
    year: 1994,
    month: 1,
    day: 16,
    hour: 12,
    minute: 20,
    is_leap_month: false,
    city: "Seoul",
    longitude: null,
    use_solar_time: true,
  },
};

function requestErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof TypeError) {
    return "백엔드 서버에 연결하지 못했어요. 잠시 뒤 다시 시도해주세요.";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

function emptyAnswers(questions: DiagnosticQuestion[]): QuestionAnswer[] {
  return questions.map((question) => ({
    question_id: question.id,
    question: question.text,
    answer: "",
    selected_option_ids: [],
  }));
}

function apiBaseUrl() {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    (typeof window === "undefined" ? "http://localhost:8000" : `${window.location.protocol}//${window.location.hostname}:8000`);

  return baseUrl.replace(/\/+$/, "");
}

export default function Home() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("hall");
  const [readingStyle, setReadingStyle] = useState<ReadingStyle>("traditional");
  const [profile, setProfile] = useState<InitialProfile>(defaultProfile);
  const [questionResult, setQuestionResult] = useState<GenerateQuestionsResponse | null>(null);
  const [fixedAnswers, setFixedAnswers] = useState<QuestionAnswer[]>([]);
  const [customQuestionResult, setCustomQuestionResult] = useState<GenerateCustomQuestionsResponse | null>(null);
  const [customAnswers, setCustomAnswers] = useState<QuestionAnswer[]>([]);
  const [finalResult, setFinalResult] = useState<FinalReadingResponse | null>(null);
  const [sajuOnlyResult, setSajuOnlyResult] = useState<import("@/lib/api").SajuOnlyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [adminGateOpen, setAdminGateOpen] = useState(false);
  const [adminPassword, setAdminPassword] = useState("");
  const [adminGateLoading, setAdminGateLoading] = useState(false);
  const [adminGateError, setAdminGateError] = useState("");

  async function handleGenerateQuestions() {
    if (profile.initial_concern.trim().length === 0) {
      setError("초기 고민을 적어주세요. (사주만 보려면 ‘사주만 보기’를 눌러도 돼요.)");
      return;
    }
    setLoading(true);
    setError("");
    setFinalResult(null);
    setSajuOnlyResult(null);

    try {
      const response = await generateQuestions(profile);
      setQuestionResult(response);
      setFixedAnswers(emptyAnswers(response.questions));
      setCustomQuestionResult(null);
      setCustomAnswers([]);
      setStep("fixed");
    } catch (error) {
      setError(requestErrorMessage(error, "질문 생성 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  async function handleSajuOnly() {
    setLoading(true);
    setError("");
    setFinalResult(null);
    setQuestionResult(null);
    setFixedAnswers([]);
    setCustomQuestionResult(null);
    setCustomAnswers([]);

    try {
      const response = await requestSajuOnly({
        name: profile.name,
        gender: profile.gender,
        birth: profile.birth,
      });
      setSajuOnlyResult(response);
      setStep("saju");
    } catch (error) {
      setError(requestErrorMessage(error, "사주 계산 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateCustomQuestions() {
    if (!questionResult) return;

    const completedFixedAnswers = fixedAnswers.filter((answer) => answer.answer.trim().length > 0);
    setLoading(true);
    setError("");
    setFinalResult(null);

    try {
      const response = await generateCustomQuestions({
        ...profile,
        category: questionResult.category,
        fixed_answers: completedFixedAnswers,
      });
      setCustomQuestionResult(response);
      setCustomAnswers(emptyAnswers(response.questions));
      setStep("custom");
    } catch (error) {
      setError(requestErrorMessage(error, "맞춤 질문 생성 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  async function handleFinalReading() {
    if (!questionResult) return;

    const completedFixedAnswers = fixedAnswers.filter((answer) => answer.answer.trim().length > 0);
    const completedCustomAnswers = customAnswers.filter((answer) => answer.answer.trim().length > 0);
    setLoading(true);
    setError("");

    try {
      const response = await requestFinalReading({
        ...profile,
        category: questionResult.category,
        reading_style: readingStyle,
        answers: [...completedFixedAnswers, ...completedCustomAnswers],
      });
      setFinalResult(response);
      setStep("result");
    } catch (error) {
      setError(requestErrorMessage(error, "최종 풀이 생성 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  function restart() {
    setStep("hall");
    setReadingStyle("traditional");
    setQuestionResult(null);
    setFixedAnswers([]);
    setCustomQuestionResult(null);
    setCustomAnswers([]);
    setFinalResult(null);
    setSajuOnlyResult(null);
    setError("");
  }

  function enterReadingStyle(style: ReadingStyle) {
    setReadingStyle(style);
    setStep("initial");
    setError("");
  }

  async function handleAdminLogin() {
    const password = adminPassword.trim();
    setAdminGateError("");

    if (!password) {
      setAdminGateError("관리 비밀번호를 입력해주세요.");
      return;
    }

    setAdminGateLoading(true);
    try {
      const response = await fetch(`${apiBaseUrl()}/api/admin/prompts/question_system_prompt`, {
        headers: {
          "X-Admin-Key": password,
        },
        cache: "no-store",
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === "string" ? body.detail : "관리 비밀번호를 확인해주세요.");
      }

      window.localStorage.setItem(ADMIN_STORAGE_KEY, password);
      router.push("/admin/prompts");
    } catch (error) {
      setAdminGateError(error instanceof Error ? error.message : "관리자 페이지에 연결하지 못했어요.");
    } finally {
      setAdminGateLoading(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 lg:px-8">
      <button
        type="button"
        onClick={() => {
          setAdminGateOpen(true);
          setAdminGateError("");
        }}
        className="fixed right-4 top-4 z-30 grid h-11 w-11 place-items-center rounded-full border border-stone-200 bg-white text-ink shadow-soft transition hover:border-mint hover:text-mint focus:outline-none focus:ring-4 focus:ring-mint/15"
        aria-label="관리자 설정 열기"
        title="관리자 설정"
      >
        <Settings size={20} strokeWidth={2.4} aria-hidden="true" />
      </button>

      {adminGateOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/35 px-4 py-6" role="dialog" aria-modal="true" aria-labelledby="admin-gate-title">
          <div className="w-full max-w-sm rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-full bg-mint/10 text-mint">
                  <LockKeyhole size={19} strokeWidth={2.5} aria-hidden="true" />
                </div>
                <div>
                  <h2 id="admin-gate-title" className="text-lg font-black text-ink">
                    관리자 설정
                  </h2>
                  <p className="mt-1 text-xs font-bold text-stone-500">모델과 프롬프트를 관리합니다.</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAdminGateOpen(false)}
                className="grid h-9 w-9 place-items-center rounded-full text-stone-500 transition hover:bg-stone-100 hover:text-ink"
                aria-label="닫기"
              >
                <X size={18} strokeWidth={2.4} aria-hidden="true" />
              </button>
            </div>

            <label className="mt-5 block">
              <span className="mb-2 block text-sm font-black text-stone-700">관리 비밀번호</span>
              <input
                type="password"
                value={adminPassword}
                onChange={(event) => setAdminPassword(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void handleAdminLogin();
                }}
                autoComplete="current-password"
                className="w-full rounded-lg border border-stone-200 bg-cloud px-4 py-3 text-base text-ink outline-none transition focus:border-mint focus:ring-4 focus:ring-mint/15"
              />
            </label>

            {adminGateError && <div className="mt-4 rounded-lg border border-coral/20 bg-coral/10 px-4 py-3 text-sm font-bold leading-6 text-coral">{adminGateError}</div>}

            <button
              type="button"
              disabled={adminGateLoading}
              onClick={handleAdminLogin}
              className="mt-4 h-12 w-full rounded-lg bg-mint px-5 text-sm font-black text-white shadow-soft transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {adminGateLoading ? "확인 중" : "관리자 페이지 열기"}
            </button>
          </div>
        </div>
      )}

      <div className="mx-auto max-w-5xl">
        {step !== "hall" && (
          <div className="mb-5 grid grid-cols-4 gap-2">
            {[
              ["initial", "입력"],
              ["fixed", "기본"],
              ["custom", "심층"],
              ["result", "결과"],
            ].map(([key, label], index, steps) => {
              const active = step === key;
              const currentIndex = steps.findIndex(([stepKey]) => stepKey === step);
              const completed = currentIndex > index;
              return (
                <div
                  key={key}
                  className={`h-2 rounded-full transition ${active || completed ? "bg-honey" : "bg-white/80"}`}
                  aria-label={`${label} 단계`}
                />
              );
            })}
          </div>
        )}

        {error && <div className="mb-4 rounded-lg border border-coral/20 bg-white px-4 py-3 text-sm font-bold leading-6 text-coral shadow-soft">{error}</div>}
        {loading && (
          <div className="mb-4 rounded-lg border border-mint/20 bg-white px-4 py-3 text-sm font-bold leading-6 text-mint shadow-soft">
            잠시 기다려주세요. 선생님이 고객님의 고민을 같이 고민하는 중이에요.
          </div>
        )}

        {step === "hall" && (
          <section className="rounded-lg border border-[#eadfce] bg-[#fffdf8] p-5 shadow-soft sm:p-8">
            <div className="mb-8 max-w-2xl">
              <p className="mb-3 inline-flex items-center gap-2 rounded-full bg-[#fff0b9] px-3 py-1.5 text-xs font-black text-[#6e5428]">
                <DoorOpen size={14} aria-hidden /> 사주 철학관
              </p>
              <h1 className="whitespace-nowrap text-2xl font-black leading-tight tracking-normal text-ink sm:text-4xl">원하는 철학관을 선택해주세요.</h1>
            </div>

            <div className="grid gap-4">
              {readingStyleOptions.map(({ style, nickname, description, icon: Icon, accentClass }) => (
                <button
                  key={style}
                  type="button"
                  onClick={() => enterReadingStyle(style)}
                  className="group flex flex-col gap-5 rounded-lg border border-[#eadfce] bg-white p-5 text-left shadow-[0_14px_36px_rgba(83,64,42,0.08)] transition hover:-translate-y-0.5 hover:border-coral hover:shadow-soft focus:outline-none focus:ring-4 focus:ring-coral/15 sm:flex-row sm:items-center"
                >
                  <span className={`grid h-16 w-full shrink-0 place-items-center rounded-lg sm:h-24 sm:w-32 ${accentClass}`}>
                    <Icon size={30} strokeWidth={2.4} aria-hidden />
                  </span>
                  <span className="block flex-1">
                    <span className="block text-2xl font-black leading-8 text-ink">{nickname}</span>
                    <span className="mt-3 block text-base font-bold leading-7 text-stone-500">{description}</span>
                  </span>
                  <span className="inline-flex h-11 shrink-0 items-center justify-center rounded-full bg-cloud px-4 text-sm font-black text-stone-700 transition group-hover:bg-honey group-hover:text-[#4d3b21]">
                    입장하기
                  </span>
                </button>
              ))}
            </div>
          </section>
        )}

        {step === "initial" && (
          <>
            <div className="mb-4 flex flex-col gap-3 rounded-lg border border-stone-200 bg-white px-4 py-3 shadow-soft sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-black text-stone-500">선택한 철학관</p>
                <p className="mt-1 text-base font-black text-ink">{readingStyleOptions.find((option) => option.style === readingStyle)?.nickname}</p>
              </div>
              <button
                type="button"
                onClick={() => setStep("hall")}
                className="inline-flex h-10 items-center justify-center rounded-lg border border-stone-200 px-4 text-sm font-black text-stone-600 transition hover:border-coral hover:text-coral"
              >
                다시 고르기
              </button>
            </div>
            <InitialForm profile={profile} loading={loading} onChange={setProfile} onSubmit={handleGenerateQuestions} onSajuOnly={handleSajuOnly} />
          </>
        )}

        {step === "fixed" && questionResult && (
          <QuestionsForm
            questions={questionResult.questions}
            answers={fixedAnswers}
            loading={loading}
            eyebrow={`${questionResult.category_label} · 기본 질문`}
            title="기본 상담지"
            description="초기 고민을 기준으로 고른 카테고리의 기본 질문입니다. 마지막 문항은 비워두어도 됩니다."
            onBack={() => setStep("initial")}
            onAnswerChange={setFixedAnswers}
            onSubmit={handleGenerateCustomQuestions}
            submitLabel="맞춤 질문 받기"
            loadingLabel="맞춤 질문 생성 중"
            optionalQuestionIds={["q4"]}
          />
        )}

        {step === "custom" && customQuestionResult && (
          <QuestionsForm
            questions={customQuestionResult.questions}
            answers={customAnswers}
            loading={loading}
            eyebrow="맞춤 심층 질문"
            title="마음의 방향을 좁혀볼게요"
            description="기본 답변을 바탕으로 만든 질문입니다. 떠오르는 만큼 편하게 적어주세요."
            onBack={() => setStep("fixed")}
            onAnswerChange={setCustomAnswers}
            onSubmit={handleFinalReading}
            submitLabel="최종 풀이 보기"
            loadingLabel="최종 풀이 생성 중"
            optionalQuestionIds={["q8"]}
          />
        )}

        {step === "result" && finalResult && (
          <ReadingResult result={finalResult} profileName={profile.name} onBack={() => setStep("custom")} onRestart={restart} />
        )}

        {step === "saju" && sajuOnlyResult && (
          <SajuOnlyResult saju={sajuOnlyResult.saju} onBack={() => setStep("initial")} onRestart={restart} />
        )}
      </div>
    </main>
  );
}
