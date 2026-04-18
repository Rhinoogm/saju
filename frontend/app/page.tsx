"use client";

import { useState } from "react";

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
    selected_option_id: null,
  }));
}

export default function Home() {
  const [step, setStep] = useState<Step>("initial");
  const [profile, setProfile] = useState<InitialProfile>(defaultProfile);
  const [questionResult, setQuestionResult] = useState<GenerateQuestionsResponse | null>(null);
  const [answers, setAnswers] = useState<QuestionAnswer[]>([]);
  const [finalResult, setFinalResult] = useState<FinalReadingResponse | null>(null);
  const [sajuOnlyResult, setSajuOnlyResult] = useState<import("@/lib/api").SajuOnlyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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

  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 lg:px-8">
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
