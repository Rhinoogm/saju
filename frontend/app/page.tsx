"use client";

import { useState } from "react";
import { LockKeyhole, Settings, X } from "lucide-react";
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
  generateQuestions,
  requestFinalReading,
  requestSajuOnly,
} from "@/lib/api";

type Step = "initial" | "questions" | "result" | "saju";

const ADMIN_STORAGE_KEY = "saju_admin_api_key";

const defaultProfile: InitialProfile = {
  name: "",
  gender: "female",
  initial_concern: "",
  birth: {
    calendar_type: "solar",
    year: 1995,
    month: 1,
    day: 1,
    hour: 9,
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

function apiBaseUrl() {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    (typeof window === "undefined" ? "http://localhost:8000" : `${window.location.protocol}//${window.location.hostname}:8000`);

  return baseUrl.replace(/\/+$/, "");
}

export default function Home() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("initial");
  const [profile, setProfile] = useState<InitialProfile>(defaultProfile);
  const [questionResult, setQuestionResult] = useState<GenerateQuestionsResponse | null>(null);
  const [answers, setAnswers] = useState<QuestionAnswer[]>([]);
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
      setAnswers(emptyAnswers(response.questions));
      setStep("questions");
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
    setAnswers([]);

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

  async function handleFinalReading() {
    setLoading(true);
    setError("");

    try {
      const response = await requestFinalReading({ ...profile, answers });
      setFinalResult(response);
      setStep("result");
    } catch (error) {
      setError(requestErrorMessage(error, "최종 풀이 생성 중 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  }

  function restart() {
    setStep("initial");
    setQuestionResult(null);
    setAnswers([]);
    setFinalResult(null);
    setSajuOnlyResult(null);
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
        <div className="mb-5 grid grid-cols-3 gap-2">
          {[
            ["initial", "입력"],
            ["questions", "진단"],
            ["result", "결과"],
          ].map(([key, label], index) => {
            const active = step === key;
            const completed = ["questions", "result"].includes(step) && index === 0;
            const resultCompleted = step === "result" && index === 1;
            return (
              <div
                key={key}
                className={`h-2 rounded-full transition ${active || completed || resultCompleted ? "bg-honey" : "bg-white/80"}`}
                aria-label={`${label} 단계`}
              />
            );
          })}
        </div>

        {error && <div className="mb-4 rounded-lg border border-coral/20 bg-white px-4 py-3 text-sm font-bold leading-6 text-coral shadow-soft">{error}</div>}
        {loading && (
          <div className="mb-4 rounded-lg border border-mint/20 bg-white px-4 py-3 text-sm font-bold leading-6 text-mint shadow-soft">
            요청 처리 중입니다. 무료 서버를 깨우는 중이면 1분 정도 걸릴 수 있어요.
          </div>
        )}

        {step === "initial" && (
          <InitialForm profile={profile} loading={loading} onChange={setProfile} onSubmit={handleGenerateQuestions} onSajuOnly={handleSajuOnly} />
        )}

        {step === "questions" && questionResult && (
          <QuestionsForm
            questions={questionResult.questions}
            answers={answers}
            loading={loading}
            onBack={() => setStep("initial")}
            onAnswerChange={setAnswers}
            onSubmit={handleFinalReading}
          />
        )}

        {step === "result" && finalResult && (
          <ReadingResult result={finalResult} onBack={() => setStep("questions")} onRestart={restart} />
        )}

        {step === "saju" && sajuOnlyResult && (
          <SajuOnlyResult saju={sajuOnlyResult.saju} onBack={() => setStep("initial")} onRestart={restart} />
        )}
      </div>
    </main>
  );
}
