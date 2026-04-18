"use client";

import { useState } from "react";

import { InitialForm } from "@/components/InitialForm";
import { QuestionsForm } from "@/components/QuestionsForm";
import { ReadingResult } from "@/components/ReadingResult";
import {
  DiagnosticQuestion,
  FinalReadingResponse,
  GenerateQuestionsResponse,
  InitialProfile,
  QuestionAnswer,
  generateQuestions,
  requestFinalReading,
} from "@/lib/api";

type Step = "initial" | "questions" | "result";

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGenerateQuestions() {
    setLoading(true);
    setError("");
    setFinalResult(null);

    try {
      const response = await generateQuestions(profile);
      setQuestionResult(response);
      setAnswers(emptyAnswers(response.questions));
      setStep("questions");
    } catch (error) {
      setError(error instanceof Error ? error.message : "질문 생성 중 오류가 발생했어요.");
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
      setError(error instanceof Error ? error.message : "최종 풀이 생성 중 오류가 발생했어요.");
    } finally {
      setLoading(false);
    }
  }

  function restart() {
    setStep("initial");
    setQuestionResult(null);
    setAnswers([]);
    setFinalResult(null);
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
                className={`h-2 rounded-full transition ${active || completed || resultCompleted ? "bg-coral" : "bg-stone-200"}`}
                aria-label={`${label} 단계`}
              />
            );
          })}
        </div>

        {error && <div className="mb-4 rounded-lg border border-coral/20 bg-coral/10 px-4 py-3 text-sm font-bold leading-6 text-coral">{error}</div>}

        {step === "initial" && (
          <InitialForm profile={profile} loading={loading} onChange={setProfile} onSubmit={handleGenerateQuestions} />
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
      </div>
    </main>
  );
}
