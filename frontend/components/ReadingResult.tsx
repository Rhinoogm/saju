"use client";

import { ArrowLeft, RefreshCcw, Sparkles } from "lucide-react";

import type { FinalReadingResponse, PillarDetail } from "@/lib/api";

const pillarLabels: Record<string, string> = {
  year: "연주",
  month: "월주",
  day: "일주",
  hour: "시주",
};

const elementLabels: Record<string, string> = {
  wood: "목",
  fire: "화",
  earth: "토",
  metal: "금",
  water: "수",
};

interface ReadingResultProps {
  result: FinalReadingResponse;
  onBack: () => void;
  onRestart: () => void;
}

function PillarTile({ name, detail }: { name: string; detail: PillarDetail }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-3">
      <div className="mb-2 text-xs font-black text-stone-500">{pillarLabels[name]}</div>
      <div className="text-2xl font-black text-ink">{detail.pillar}</div>
      <div className="mt-2 text-xs leading-5 text-stone-500">
        {elementLabels[detail.stem_element]} / {elementLabels[detail.branch_element]} · {detail.stem_ten_god}
      </div>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-black text-stone-700">{title}</h3>
      <ul className="space-y-2 text-sm leading-6 text-stone-700">
        {items.map((item, index) => (
          <li key={`${title}-${index}`} className="rounded-lg bg-cloud px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ReadingResult({ result, onBack, onRestart }: ReadingResultProps) {
  const { reading, saju, meta } = result;

  return (
    <article className="space-y-4 rounded-lg border border-stone-200 bg-white p-4 shadow-soft sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-black text-mint">3단계</p>
          <h2 className="mt-1 text-2xl font-black text-ink">최종 사주풀이</h2>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={onBack} className="flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 px-3 text-sm font-bold text-stone-600 hover:bg-cloud">
            <ArrowLeft size={16} aria-hidden />
            답변 수정
          </button>
          <button type="button" onClick={onRestart} className="flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-3 text-sm font-bold text-white hover:bg-berry">
            <RefreshCcw size={16} aria-hidden />
            처음
          </button>
        </div>
      </div>

      <section className="rounded-lg bg-berry p-5 text-white">
        <div className="mb-3 flex items-center gap-2 text-sm font-black text-white/85">
          <Sparkles size={18} aria-hidden /> 결론
        </div>
        <p className="text-xl font-black leading-8">{reading.core_message}</p>
        <p className="mt-3 rounded-lg bg-white/10 px-3 py-2 text-sm font-bold leading-6 text-white/90">{reading.desired_conclusion}</p>
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-black text-stone-700">풀이 전문</h3>
        <div className="whitespace-pre-line text-base leading-8 text-stone-800">{reading.final_text}</div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <ListBlock title="답변에서 읽은 신호" items={reading.answer_signals} />
        <ListBlock title="사주 근거" items={reading.saju_basis} />
        <ListBlock title="실행 기준" items={reading.action_steps} />
        <section className="rounded-lg border border-stone-200 bg-white p-4">
          <h3 className="mb-3 text-sm font-black text-stone-700">명식 요약</h3>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(saju.pillars).map(([name, detail]) => (
              <PillarTile key={name} name={name} detail={detail} />
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-lg border border-stone-200 bg-cloud p-4 text-sm font-bold leading-6 text-stone-700">
        {reading.caution}
      </section>

      <div className="text-right text-xs text-stone-400">
        {meta.provider} · {meta.model}
      </div>
    </article>
  );
}
