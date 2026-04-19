"use client";

import { ArrowLeft, CheckCircle2, LoaderCircle, PencilLine, Send } from "lucide-react";
import { FormEvent, useState } from "react";

import type { DiagnosticQuestion, QuestionAnswer } from "@/lib/api";

interface QuestionsFormProps {
  questions: DiagnosticQuestion[];
  answers: QuestionAnswer[];
  loading: boolean;
  onBack: () => void;
  onAnswerChange: (answers: QuestionAnswer[]) => void;
  onSubmit: () => void;
}

export function QuestionsForm({ questions, answers, loading, onBack, onAnswerChange, onSubmit }: QuestionsFormProps) {
  const [customQuestionIds, setCustomQuestionIds] = useState<Set<string>>(() => new Set());
  const isComplete = answers.length === 5 && answers.every((answer) => answer.answer.trim().length > 0);

  function updateAnswer(question: DiagnosticQuestion, value: string, selectedOptionIds: string[]) {
    onAnswerChange(
      answers.map((answer) =>
        answer.question_id === question.id
          ? {
              ...answer,
              answer: value,
              selected_option_ids: selectedOptionIds,
            }
          : answer,
      ),
    );
  }

  function selectOption(question: DiagnosticQuestion, selectedOptionId: string) {
    setCustomQuestionIds((current) => {
      const next = new Set(current);
      next.delete(question.id);
      return next;
    });

    const answer = answers.find((item) => item.question_id === question.id);
    const currentSelected = answer?.selected_option_ids ?? [];
    const nextSelected = currentSelected.includes(selectedOptionId)
      ? currentSelected.filter((optionId) => optionId !== selectedOptionId)
      : [...currentSelected, selectedOptionId];
    const selectedLabels = question.options.filter((option) => nextSelected.includes(option.id)).map((option) => option.label);

    updateAnswer(question, selectedLabels.join(", "), nextSelected);
  }

  function selectCustomAnswer(question: DiagnosticQuestion, value = "") {
    setCustomQuestionIds((current) => new Set(current).add(question.id));
    updateAnswer(question, value, []);
  }

  function updateCustomAnswer(question: DiagnosticQuestion, value: string) {
    setCustomQuestionIds((current) => new Set(current).add(question.id));
    updateAnswer(question, value, []);
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
          <p className="text-sm font-black text-mint">2단계</p>
          <h2 className="mt-1 text-2xl font-black text-ink">마음의 방향 확인</h2>
          <p className="mt-2 text-sm leading-6 text-stone-500">답변은 최종 풀이에서 사용자가 실제로 듣고 싶어 하는 결론을 잡는 데 쓰입니다.</p>
        </div>
        <button type="button" onClick={onBack} className="flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 px-3 text-sm font-bold text-stone-600 hover:bg-cloud">
          <ArrowLeft size={16} aria-hidden />
          이전
        </button>
      </div>

      <div className="space-y-4">
        {questions.map((question, index) => {
          const answer = answers.find((item) => item.question_id === question.id);
          const customSelected =
            question.type === "single_choice" &&
            (customQuestionIds.has(question.id) || ((answer?.selected_option_ids.length ?? 0) === 0 && (answer?.answer.trim().length ?? 0) > 0));
          return (
            <section key={question.id} className="rounded-lg border border-stone-200 bg-cloud p-4">
              <div className="mb-3 flex items-start gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-mint text-sm font-black text-white">{index + 1}</span>
                <div>
                  <h3 className="text-base font-black leading-7 text-ink">{question.text}</h3>
                  <p className="mt-1 text-xs font-bold text-stone-500">{question.type === "single_choice" ? "복수 선택하거나 직접 입력" : "짧게 입력"}</p>
                </div>
              </div>

              {question.type === "single_choice" ? (
                <div className="grid gap-2">
                  {question.options.map((option) => {
                    const selected = answer?.selected_option_ids.includes(option.id) ?? false;
                    return (
                      <button
                        key={option.id}
                        type="button"
                        onClick={() => selectOption(question, option.id)}
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
                    onClick={() => selectCustomAnswer(question, (answer?.selected_option_ids.length ?? 0) === 0 ? answer?.answer ?? "" : "")}
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
                      value={(answer?.selected_option_ids.length ?? 0) === 0 ? answer?.answer ?? "" : ""}
                      onChange={(event) => updateCustomAnswer(question, event.target.value)}
                      placeholder="보기 중 맞는 답이 없다면 직접 적어주세요."
                      required
                    />
                  )}
                </div>
              ) : (
                <textarea
                  className="min-h-28 w-full resize-y rounded-lg border border-stone-200 bg-white px-4 py-3 text-base leading-7 text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15"
                  value={answer?.answer ?? ""}
                  onChange={(event) => updateAnswer(question, event.target.value, [])}
                  placeholder="떠오르는 답을 짧게 적어주세요."
                  required
                />
              )}
            </section>
          );
        })}
      </div>

      <button
        type="submit"
        disabled={loading || !isComplete}
        className="mt-5 flex h-[54px] w-full items-center justify-center gap-2 rounded-lg bg-coral px-5 text-base font-black text-white shadow-soft transition hover:bg-berry disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? <LoaderCircle className="animate-spin" size={20} aria-hidden /> : <Send size={19} aria-hidden />}
        {loading ? "무료 모델 응답 대기 중" : "최종 풀이 보기"}
      </button>
    </form>
  );
}
