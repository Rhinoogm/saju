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
  GenerateQuestionsResponse,
  InitialProfile,
  QuestionAnswer,
  ReadingStyle,
  generateNextQuestion,
  generateQuestions,
  requestFinalReading,
  requestSajuOnly,
} from "@/lib/api";

type Step = "hall" | "initial" | "counseling" | "result" | "saju";

const ADMIN_STORAGE_KEY = "saju_admin_api_key";
const TOTAL_COUNSELING_STEPS = 5;

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
    accentClass: "bg-[#2f312d] text-white dark:bg-[#f6f1ea] dark:text-[#1e1e1e]",
  },
  {
    style: "empathetic",
    nickname: "극F 나보다 내 사주 과몰입 사주 잘보는 언니",
    description: "감정을 먼저 안아주는 공감형 해석으로 위로와 지지를 중심에 둡니다.",
    icon: HeartHandshake,
    accentClass: "bg-terracotta text-white",
  },
  {
    style: "direct",
    nickname: "틀린 말은 안 해서 더 열받는 개발자 출신 명리학자",
    description: "위로보다 리스크와 행동 기준을 직설적으로 짚는 현실 분석형 풀이입니다.",
    icon: ClipboardCheck,
    accentClass: "bg-sage text-white",
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
    use_solar_time: false,
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

function emptyAnswer(question: DiagnosticQuestion): QuestionAnswer {
  return {
    question_id: question.id,
    question: question.text,
    answer: "",
    selected_option_ids: [],
  };
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
  const [questions, setQuestions] = useState<DiagnosticQuestion[]>([]);
  const [answers, setAnswers] = useState<QuestionAnswer[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [finalResult, setFinalResult] = useState<FinalReadingResponse | null>(null);
  const [sajuOnlyResult, setSajuOnlyResult] = useState<import("@/lib/api").SajuOnlyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [adminGateOpen, setAdminGateOpen] = useState(false);
  const [adminPassword, setAdminPassword] = useState("");
  const [adminGateLoading, setAdminGateLoading] = useState(false);
  const [adminGateError, setAdminGateError] = useState("");
  const currentQuestion = questions[currentQuestionIndex];
  const currentAnswer = answers[currentQuestionIndex];

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
      setQuestions([response.question]);
      setAnswers([emptyAnswer(response.question)]);
      setCurrentQuestionIndex(0);
      setStep("counseling");
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
    setQuestions([]);
    setAnswers([]);
    setCurrentQuestionIndex(0);

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

  async function handleCounselingSubmit() {
    if (!questionResult || !currentQuestion || !currentAnswer) return;

    const completedAnswers = answers.slice(0, currentQuestionIndex + 1).map((answer) => ({
      ...answer,
      answer: answer.answer.trim(),
    }));
    setLoading(true);
    setError("");

    try {
      if (completedAnswers.length >= TOTAL_COUNSELING_STEPS) {
        const response = await requestFinalReading({
          ...profile,
          reading_style: readingStyle,
          answers: completedAnswers,
        });
        setFinalResult(response);
        setStep("result");
        return;
      }

      const response = await generateNextQuestion({
        ...profile,
        answers: completedAnswers,
      });
      setQuestions((current) => [...current.slice(0, currentQuestionIndex + 1), response.question]);
      setAnswers((current) => [...current.slice(0, currentQuestionIndex + 1), emptyAnswer(response.question)]);
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } catch (error) {
      setError(requestErrorMessage(error, completedAnswers.length >= TOTAL_COUNSELING_STEPS ? "최종 풀이 생성 중 오류가 발생했어요." : "다음 질문 생성 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  function handleQuestionBack() {
    setError("");
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex((current) => current - 1);
      return;
    }
    setStep("initial");
  }

  function handleCurrentAnswerChange(nextAnswer: QuestionAnswer) {
    setAnswers((current) => {
      const next = current.slice(0, currentQuestionIndex + 1);
      next[currentQuestionIndex] = nextAnswer;
      return next;
    });
    setQuestions((current) => current.slice(0, currentQuestionIndex + 1));
  }

  function restart() {
    setStep("hall");
    setReadingStyle("traditional");
    setQuestionResult(null);
    setQuestions([]);
    setAnswers([]);
    setCurrentQuestionIndex(0);
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
      const response = await fetch(`${apiBaseUrl()}/api/admin/prompts/counseling_question_system_prompt`, {
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
    <main className="min-h-screen px-4 py-5 text-foreground sm:px-6 lg:px-8">
      <button
        type="button"
        onClick={() => {
          setAdminGateOpen(true);
          setAdminGateError("");
        }}
        className="fixed right-4 top-4 z-30 grid h-11 w-11 place-items-center rounded-full border border-border bg-surface text-foreground shadow-ritual transition hover:border-sage hover:text-sage focus:outline-none focus:ring-4 focus:ring-sage/15 dark:shadow-ritual-dark"
        aria-label="관리자 설정 열기"
        title="관리자 설정"
      >
        <Settings size={20} strokeWidth={2.4} aria-hidden="true" />
      </button>

      {adminGateOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-[#1e1e1e]/55 px-4 py-6" role="dialog" aria-modal="true" aria-labelledby="admin-gate-title">
          <div className="w-full max-w-sm rounded-lg border border-border bg-surface p-5 shadow-ritual dark:shadow-ritual-dark">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-lg bg-sage/10 text-sage dark:bg-sage/20">
                  <LockKeyhole size={19} strokeWidth={2.5} aria-hidden="true" />
                </div>
                <div>
                  <h2 id="admin-gate-title" className="text-lg font-black text-foreground">
                    관리자 설정
                  </h2>
                  <p className="mt-1 text-xs font-bold text-stone-500 dark:text-stone-400">모델과 프롬프트를 관리합니다.</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAdminGateOpen(false)}
                className="grid h-9 w-9 place-items-center rounded-lg text-stone-500 transition hover:bg-surface-muted hover:text-foreground"
                aria-label="닫기"
              >
                <X size={18} strokeWidth={2.4} aria-hidden="true" />
              </button>
            </div>

            <label className="mt-5 block">
              <span className="mb-2 block text-sm font-black text-stone-700 dark:text-stone-200">관리 비밀번호</span>
              <input
                type="password"
                value={adminPassword}
                onChange={(event) => setAdminPassword(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void handleAdminLogin();
                }}
                autoComplete="current-password"
                className="w-full rounded-lg border border-border bg-surface-muted px-4 py-3 text-base text-foreground outline-none transition focus:border-sage focus:ring-4 focus:ring-sage/15"
              />
            </label>

            {adminGateError && <div className="mt-4 rounded-lg border border-terracotta/20 bg-terracotta/10 px-4 py-3 text-sm font-bold leading-6 text-terracotta">{adminGateError}</div>}

            <button
              type="button"
              disabled={adminGateLoading}
              onClick={handleAdminLogin}
              className="mt-4 h-12 w-full rounded-lg bg-sage px-5 text-sm font-black text-white shadow-ritual transition hover:bg-[#4c5d50] disabled:cursor-not-allowed disabled:opacity-70"
            >
              {adminGateLoading ? "확인 중" : "관리자 페이지 열기"}
            </button>
          </div>
        </div>
      )}

      <div className="mx-auto max-w-6xl">
        {step !== "hall" && step !== "saju" && (
          <div className="mb-5 grid grid-cols-3 gap-2">
            {[
              ["initial", "입력"],
              ["counseling", "상담"],
              ["result", "결과"],
            ].map(([key, label], index, steps) => {
              const active = step === key;
              const currentIndex = steps.findIndex(([stepKey]) => stepKey === step);
              const completed = currentIndex > index;
              return (
                <div
                key={key}
                  className={`h-2 rounded-full transition ${active || completed ? "bg-terracotta" : "bg-surface/80 dark:bg-surface-muted"}`}
                  aria-label={`${label} 단계`}
                />
              );
            })}
          </div>
        )}

        {error && <div className="mb-4 rounded-lg border border-terracotta/20 bg-surface px-4 py-3 text-sm font-bold leading-6 text-terracotta shadow-ritual">{error}</div>}
        {loading && (
          <div className="mb-4 rounded-lg border border-sage/20 bg-surface px-4 py-3 text-sm font-bold leading-6 text-sage shadow-ritual">
            잠시 기다려주세요. 선생님이 고객님의 고민을 같이 고민하는 중이에요.
          </div>
        )}

        {step === "hall" && (
          <section className="overflow-hidden rounded-lg border border-border bg-surface shadow-ritual dark:shadow-ritual-dark">
            <div className="grid gap-8 p-5 sm:p-8 lg:grid-cols-[0.9fr_1.1fr] lg:p-10">
              <div className="flex min-h-[360px] flex-col justify-between">
                <div>
                  <p className="mb-4 inline-flex items-center gap-2 rounded-lg bg-surface-muted px-3 py-1.5 text-xs font-black text-sage dark:text-[#c9d4bd]">
                <DoorOpen size={14} aria-hidden /> 사주 철학관
              </p>
                  <h1 className="max-w-md break-keep font-serif text-4xl font-black leading-tight tracking-normal text-foreground sm:text-5xl">
                    원하는 철학관을 선택해주세요.
                  </h1>
                  <p className="mt-5 max-w-md break-keep text-base font-bold leading-7 text-stone-600 dark:text-stone-300">
                    같은 사주라도 어떤 목소리로 듣느냐에 따라 마음에 남는 기준이 달라집니다.
                  </p>
                </div>
                <div className="mt-8 grid grid-cols-5 gap-2" aria-hidden>
                  {["목", "화", "토", "금", "수"].map((element) => (
                    <span key={element} className="grid aspect-square place-items-center rounded-lg border border-border bg-surface-muted font-serif text-xl font-black text-sage">
                      {element}
                    </span>
                  ))}
                </div>
              </div>

              <div className="grid gap-4">
              {readingStyleOptions.map(({ style, nickname, description, icon: Icon, accentClass }) => (
                <button
                  key={style}
                  type="button"
                  onClick={() => enterReadingStyle(style)}
                    className="group flex flex-col gap-5 rounded-lg border border-border bg-background/70 p-5 text-left shadow-[0_14px_36px_rgba(83,64,42,0.06)] transition hover:-translate-y-0.5 hover:border-terracotta hover:bg-surface focus:outline-none focus:ring-4 focus:ring-terracotta/15 sm:flex-row sm:items-center dark:bg-[#242321] dark:hover:bg-surface"
                >
                  <span className={`grid h-16 w-full shrink-0 place-items-center rounded-lg sm:h-24 sm:w-32 ${accentClass}`}>
                    <Icon size={30} strokeWidth={2.4} aria-hidden />
                  </span>
                  <span className="block flex-1">
                    <span className="block break-keep font-serif text-2xl font-black leading-8 text-foreground">{nickname}</span>
                    <span className="mt-3 block break-keep text-base font-bold leading-7 text-stone-600 dark:text-stone-300">{description}</span>
                  </span>
                  <span className="inline-flex h-11 shrink-0 items-center justify-center rounded-lg bg-surface-muted px-4 text-sm font-black text-stone-700 transition group-hover:bg-terracotta group-hover:text-white dark:text-stone-200">
                    입장하기
                  </span>
                </button>
              ))}
              </div>
            </div>
          </section>
        )}

        {step === "initial" && (
          <>
            <div className="mb-4 flex flex-col gap-3 rounded-lg border border-border bg-surface px-4 py-3 shadow-ritual sm:flex-row sm:items-center sm:justify-between dark:shadow-ritual-dark">
              <div>
                <p className="text-xs font-black text-stone-500 dark:text-stone-400">선택한 철학관</p>
                <p className="mt-1 break-keep text-base font-black text-foreground">{readingStyleOptions.find((option) => option.style === readingStyle)?.nickname}</p>
              </div>
              <button
                type="button"
                onClick={() => setStep("hall")}
                className="inline-flex h-10 items-center justify-center rounded-lg border border-border px-4 text-sm font-black text-stone-600 transition hover:border-terracotta hover:text-terracotta dark:text-stone-300"
              >
                다시 고르기
              </button>
            </div>
            <InitialForm profile={profile} loading={loading} onChange={setProfile} onSubmit={handleGenerateQuestions} onSajuOnly={handleSajuOnly} />
          </>
        )}

        {step === "counseling" && currentQuestion && currentAnswer && (
          <QuestionsForm
            key={currentQuestion.id}
            question={currentQuestion}
            answer={currentAnswer}
            loading={loading}
            stepIndex={currentQuestionIndex + 1}
            eyebrow="5단계 상담"
            title="마음의 방향을 하나씩 좁혀볼게요"
            description="초기 고민과 이전 답변을 바탕으로 만든 질문입니다. 가장 가까운 답을 골라주세요."
            onBack={handleQuestionBack}
            onAnswerChange={handleCurrentAnswerChange}
            onSubmit={handleCounselingSubmit}
            submitLabel={currentQuestionIndex + 1 >= TOTAL_COUNSELING_STEPS ? "최종 풀이 보기" : "다음"}
            loadingLabel={currentQuestionIndex + 1 >= TOTAL_COUNSELING_STEPS ? "최종 풀이 생성 중" : "다음 질문 생성 중"}
          />
        )}

        {step === "result" && finalResult && (
          <ReadingResult
            result={finalResult}
            profileName={profile.name}
            initialConcern={profile.initial_concern}
            readingStyle={readingStyle}
            onBack={() => {
              setStep("counseling");
              setCurrentQuestionIndex(Math.max(0, answers.length - 1));
            }}
            onRestart={restart}
          />
        )}

        {step === "saju" && sajuOnlyResult && (
          <SajuOnlyResult saju={sajuOnlyResult.saju} onBack={() => setStep("initial")} onRestart={restart} />
        )}
      </div>
    </main>
  );
}
