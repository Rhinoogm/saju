"use client";

import type { User } from "@supabase/supabase-js";
import { ClipboardCheck, DoorOpen, HeartHandshake, Landmark, LoaderCircle, type LucideIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { InitialForm } from "@/components/InitialForm";
import { PaymentButton } from "@/components/PaymentButton";
import { QuestionsForm } from "@/components/QuestionsForm";
import { ReadingResult } from "@/components/ReadingResult";
import { UserMenu } from "@/components/UserMenu";
import {
  ApiError,
  DiagnosticQuestion,
  FinalReadingResponse,
  GenerateCustomQuestionsResponse,
  GenerateQuestionsResponse,
  InitialProfile,
  QuestionAnswer,
  ReadingStyle,
  createReadingSession,
  generateCustomQuestions,
  generateQuestions,
  requestFinalReading,
  saveCustomAnswers,
  saveFixedAnswers,
} from "@/lib/api";
import { getLocalDemoSessionUser, isLocalDemoMode } from "@/lib/localDemo";
import { createClient } from "@/lib/supabase/client";

type Step = "hall" | "initial" | "payment" | "fixed" | "custom" | "result";

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
    nickname: "틀린 말은 안 해서 더 열받는 개발자 출신 명리학자",
    description: "위로보다 리스크와 행동 기준을 직설적으로 짚는 현실 분석형 풀이입니다.",
    icon: ClipboardCheck,
    accentClass: "bg-mint text-white",
  },
];

const defaultProfile: InitialProfile = {
  name: "",
  gender: "other",
  initial_concern: "",
  birth: {
    calendar_type: "solar",
    year: 1994,
    month: 1,
    day: 1,
    hour: 12,
    minute: 0,
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

function emptyAnswers(questions: DiagnosticQuestion[]): QuestionAnswer[] {
  return questions.map((question) => ({
    question_id: question.id,
    question: question.text,
    answer: "",
    selected_option_ids: [],
  }));
}

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [userLoading, setUserLoading] = useState(true);
  const [step, setStep] = useState<Step>("hall");
  const [readingStyle, setReadingStyle] = useState<ReadingStyle>("traditional");
  const [profile, setProfile] = useState<InitialProfile>(defaultProfile);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questionResult, setQuestionResult] = useState<GenerateQuestionsResponse | null>(null);
  const [fixedAnswers, setFixedAnswers] = useState<QuestionAnswer[]>([]);
  const [customQuestionResult, setCustomQuestionResult] = useState<GenerateCustomQuestionsResponse | null>(null);
  const [customAnswers, setCustomAnswers] = useState<QuestionAnswer[]>([]);
  const [finalResult, setFinalResult] = useState<FinalReadingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isLocalDemoMode()) {
      setUser(getLocalDemoSessionUser());
      setUserLoading(false);
      const syncDemoSession = () => setUser(getLocalDemoSessionUser());
      window.addEventListener("storage", syncDemoSession);
      return () => window.removeEventListener("storage", syncDemoSession);
    }

    let supabase: ReturnType<typeof createClient>;
    try {
      supabase = createClient();
    } catch {
      setUser(null);
      setUserLoading(false);
      return;
    }
    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user);
      setUserLoading(false);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  function handleAuthError(error: unknown, fallback: string) {
    if (error instanceof ApiError) {
      if (error.status === 401) {
        router.push("/login");
        return "로그인이 필요합니다.";
      }
      if (error.status === 402) {
        setStep("payment");
        return "결제가 필요합니다.";
      }
    }
    return requestErrorMessage(error, fallback);
  }

  async function handleCreateSession() {
    if (!user) {
      router.push("/login");
      return;
    }
    if (!profile.name.trim()) {
      setError("이름을 입력해주세요.");
      return;
    }
    if (profile.initial_concern.trim().length === 0) {
      setError("초기 고민을 적어주세요.");
      return;
    }
    setLoading(true);
    setError("");
    setFinalResult(null);

    try {
      const session = await createReadingSession({ ...profile, reading_style: readingStyle });
      setSessionId(session.id);
      setQuestionResult(null);
      setFixedAnswers([]);
      setCustomQuestionResult(null);
      setCustomAnswers([]);
      setStep("payment");
    } catch (error) {
      setError(handleAuthError(error, "리딩 세션 생성 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  async function handlePaid() {
    if (!sessionId) return;
    setLoading(true);
    setError("");
    try {
      const response = await generateQuestions(sessionId);
      setQuestionResult(response);
      setFixedAnswers(emptyAnswers(response.questions));
      setStep("fixed");
    } catch (error) {
      setError(handleAuthError(error, "기본 질문 생성 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateCustomQuestions() {
    if (!sessionId || !questionResult) return;
    const completedFixedAnswers = fixedAnswers.filter((answer) => answer.answer.trim().length > 0);
    setLoading(true);
    setError("");
    setFinalResult(null);

    try {
      await saveFixedAnswers(sessionId, completedFixedAnswers);
      const response = await generateCustomQuestions(sessionId);
      setCustomQuestionResult(response);
      setCustomAnswers(emptyAnswers(response.questions));
      setStep("custom");
    } catch (error) {
      setError(handleAuthError(error, "맞춤 질문 생성 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  async function handleFinalReading() {
    if (!sessionId) return;
    const completedCustomAnswers = customAnswers.filter((answer) => answer.answer.trim().length > 0);
    setLoading(true);
    setError("");

    try {
      await saveCustomAnswers(sessionId, completedCustomAnswers);
      const response = await requestFinalReading(sessionId);
      setFinalResult(response);
      setStep("result");
    } catch (error) {
      setError(handleAuthError(error, "최종 풀이 생성 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  function restart() {
    setStep("hall");
    setReadingStyle("traditional");
    setSessionId(null);
    setQuestionResult(null);
    setFixedAnswers([]);
    setCustomQuestionResult(null);
    setCustomAnswers([]);
    setFinalResult(null);
    setError("");
  }

  function enterReadingStyle(style: ReadingStyle) {
    if (!user) {
      router.push("/login");
      return;
    }
    setReadingStyle(style);
    setStep("initial");
    setError("");
  }

  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 lg:px-8">
      <div className="fixed right-4 top-4 z-30">
        <UserMenu user={user} />
      </div>

      <div className="mx-auto max-w-5xl">
        {step !== "hall" && (
          <div className="mb-5 grid grid-cols-5 gap-2">
            {[
              ["initial", "입력"],
              ["payment", "결제"],
              ["fixed", "기본"],
              ["custom", "심층"],
              ["result", "결과"],
            ].map(([key, label], index, steps) => {
              const active = step === key;
              const currentIndex = steps.findIndex(([stepKey]) => stepKey === step);
              const completed = currentIndex > index;
              return <div key={key} className={`h-2 rounded-full transition ${active || completed ? "bg-honey" : "bg-white/80"}`} aria-label={`${label} 단계`} />;
            })}
          </div>
        )}

        {error && <div className="mb-4 rounded-lg border border-coral/20 bg-white px-4 py-3 text-sm font-bold leading-6 text-coral shadow-soft">{error}</div>}
        {(loading || userLoading) && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-mint/20 bg-white px-4 py-3 text-sm font-bold leading-6 text-mint shadow-soft">
            <LoaderCircle className="animate-spin" size={17} aria-hidden />
            잠시 기다려주세요.
          </div>
        )}

        {step === "hall" && (
          <section className="rounded-lg border border-[#eadfce] bg-[#fffdf8] p-5 shadow-soft sm:p-8">
            <div className="mb-8 max-w-2xl">
              <p className="mb-3 inline-flex items-center gap-2 rounded-full bg-[#fff0b9] px-3 py-1.5 text-xs font-black text-[#6e5428]">
                <DoorOpen size={14} aria-hidden /> 사주 철학관
              </p>
              <h1 className="text-2xl font-black leading-tight tracking-normal text-ink sm:text-4xl">원하는 철학관을 선택해주세요.</h1>
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
            <InitialForm profile={profile} loading={loading} onChange={setProfile} onSubmit={handleCreateSession} />
          </>
        )}

        {step === "payment" && sessionId && user && (
          <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft sm:p-6">
            <p className="text-sm font-black text-mint">결제</p>
            <h2 className="mt-1 text-2xl font-black text-ink">사주 심화 리딩 1회권</h2>
            <p className="mt-3 text-sm font-bold leading-6 text-stone-500">결제 검증이 완료되면 기본 질문 생성부터 진행합니다.</p>
            {isLocalDemoMode() && (
              <p className="mt-4 rounded-lg border border-honey/40 bg-[#fff8df] px-4 py-3 text-sm font-black leading-6 text-[#6e5428]">
                로컬 데모 결제 페이지입니다. 실제 결제창을 호출하지 않고 결제 완료 상태로 넘어갑니다.
              </p>
            )}
            <div className="mt-6 max-w-md">
              <PaymentButton sessionId={sessionId} user={user} onPaid={handlePaid} onError={setError} />
            </div>
          </section>
        )}

        {step === "fixed" && questionResult && (
          <QuestionsForm
            questions={questionResult.questions}
            answers={fixedAnswers}
            loading={loading}
            eyebrow={`${questionResult.category_label} · 기본 질문`}
            title="기본 상담지"
            description="초기 고민을 기준으로 고른 카테고리의 기본 질문입니다. 마지막 문항은 비워두어도 됩니다."
            onBack={() => setStep("payment")}
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

        {step === "result" && finalResult && <ReadingResult result={finalResult} profileName={profile.name} onBack={() => setStep("custom")} onRestart={restart} />}
      </div>
    </main>
  );
}
