"use client";

import { ArrowLeft, CheckCircle2, LoaderCircle, PencilLine, Send } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import type { DiagnosticQuestion, QuestionAnswer } from "@/lib/api";

interface QuestionsFormProps {
  question: DiagnosticQuestion;
  answer: QuestionAnswer;
  loading: boolean;
  stepIndex: number;
  totalSteps?: number;
  eyebrow?: string;
  title?: string;
  description?: string;
  submitLabel?: string;
  loadingLabel?: string;
  onBack: () => void;
  onAnswerChange: (answer: QuestionAnswer) => void;
  onSubmit: () => void;
}

export function QuestionsForm({
  question,
  answer,
  loading,
  stepIndex,
  totalSteps = 5,
  eyebrow = "상담 질문",
  title = "마음의 방향을 하나씩 좁혀볼게요",
  description = "보기 중 가장 가까운 답을 고르거나, 맞는 답이 없으면 직접 입력해주세요.",
  submitLabel = "다음",
  loadingLabel = "다음 질문 생성 중",
  onBack,
  onAnswerChange,
  onSubmit,
}: QuestionsFormProps) {
  const [customSelected, setCustomSelected] = useState(answer.selected_option_ids.length === 0 && answer.answer.trim().length > 0);
  const isComplete = answer.answer.trim().length > 0;

  useEffect(() => {
    setCustomSelected(answer.selected_option_ids.length === 0 && answer.answer.trim().length > 0);
  }, [answer.answer, answer.selected_option_ids.length, question.id]);

  function updateAnswer(value: string, selectedOptionIds: string[]) {
    onAnswerChange({
      ...answer,
      question_id: question.id,
      question: question.text,
      answer: value,
      selected_option_ids: selectedOptionIds,
    });
  }

  function selectOption(optionId: string, label: string) {
    setCustomSelected(false);
    updateAnswer(label, [optionId]);
  }

  function selectCustomAnswer() {
    setCustomSelected(true);
    updateAnswer(answer.selected_option_ids.length === 0 ? answer.answer : "", []);
  }

  function updateCustomAnswer(value: string) {
    setCustomSelected(true);
    updateAnswer(value, []);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isComplete) {
      onSubmit();
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-stone-200 bg-white p-4 shadow-soft sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-black text-mint">
            {eyebrow} · {stepIndex}/{totalSteps}
          </p>
          <h2 className="mt-1 text-2xl font-black text-ink">{title}</h2>
          <p className="mt-2 text-sm leading-6 text-stone-500">{description}</p>
        </div>
        <button type="button" onClick={onBack} className="flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 px-3 text-sm font-bold text-stone-600 hover:bg-cloud">
          <ArrowLeft size={16} aria-hidden />
          이전
        </button>
      </div>

      <section className="rounded-lg border border-stone-200 bg-cloud p-4">
        <div className="mb-3 flex items-start gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-mint text-sm font-black text-white">{stepIndex}</span>
          <div>
            <h3 className="text-base font-black leading-7 text-ink">{question.text}</h3>
            <p className="mt-1 text-xs font-bold text-stone-500">선택하거나 직접 입력</p>
          </div>
        </div>

        <div className="grid gap-2">
          {question.options.map((option) => {
            const selected = answer.selected_option_ids.includes(option.id);
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => selectOption(option.id, option.label)}
                className={`flex min-h-[48px] items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm font-bold leading-6 transition ${
                  selected ? "border-coral bg-white text-coral shadow-sm" : "border-stone-200 bg-white text-stone-700 hover:border-mint"
                }`}
              >
                <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-xs font-black ${selected ? "bg-coral text-white" : "bg-cloud text-stone-500"}`}>
                  {option.id}
                </span>
                <span>{option.label}</span>
                {selected && <CheckCircle2 className="ml-auto shrink-0 text-coral" size={18} aria-hidden />}
              </button>
            );
          })}

          <button
            type="button"
            onClick={selectCustomAnswer}
            className={`flex min-h-[48px] items-center gap-3 rounded-lg border px-3 py-2 text-left text-sm font-bold leading-6 transition ${
              customSelected ? "border-coral bg-white text-coral shadow-sm" : "border-stone-200 bg-white text-stone-700 hover:border-mint"
            }`}
          >
            <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${customSelected ? "bg-coral text-white" : "bg-cloud text-stone-500"}`}>
              <PencilLine size={15} aria-hidden />
            </span>
            <span>직접 입력</span>
            {customSelected && <CheckCircle2 className="ml-auto shrink-0 text-coral" size={18} aria-hidden />}
          </button>

          {customSelected && (
            <textarea
              className="min-h-24 w-full resize-y rounded-lg border border-stone-200 bg-white px-4 py-3 text-base leading-7 text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15"
              value={answer.selected_option_ids.length === 0 ? answer.answer : ""}
              onChange={(event) => updateCustomAnswer(event.target.value)}
              placeholder="보기 중 맞는 답이 없다면 직접 적어주세요."
              required
            />
          )}
        </div>
      </section>

      <button
        type="submit"
        disabled={loading || !isComplete}
        className="mt-5 flex h-[54px] w-full items-center justify-center gap-2 rounded-lg bg-coral px-5 text-base font-black text-white shadow-soft transition hover:bg-berry disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? <LoaderCircle className="animate-spin" size={20} aria-hidden /> : <Send size={19} aria-hidden />}
        {loading ? loadingLabel : submitLabel}
      </button>
    </form>
  );
}
