"use client";

import {
  ArrowLeft,
  BadgeCheck,
  CalendarClock,
  CircleAlert,
  Compass,
  RefreshCcw,
  Sparkles,
} from "lucide-react";

import { SajuPillarsTable } from "@/components/SajuPillarsTable";
import type { DaewoonPeriod, FinalReadingResponse } from "@/lib/api";

const elementLabels: Record<string, string> = {
  wood: "목",
  fire: "화",
  earth: "토",
  metal: "금",
  water: "수",
};

const elementOrder = ["wood", "fire", "earth", "metal", "water"] as const;

const elementColors: Record<(typeof elementOrder)[number], string> = {
  wood: "#2f9d8c",
  fire: "#dd6654",
  earth: "#f1be4d",
  metal: "#8a8178",
  water: "#4f77a8",
};

interface ReadingResultProps {
  result: FinalReadingResponse;
  onBack: () => void;
  onRestart: () => void;
}

function ReportList({ title, items, tone = "light" }: { title: string; items: string[]; tone?: "light" | "warm" }) {
  return (
    <section className={`rounded-lg border p-4 ${tone === "warm" ? "border-[#f0dfc4] bg-[#fff8e8]" : "border-stone-200 bg-white"}`}>
      <h3 className="mb-3 text-sm font-black text-stone-700">{title}</h3>
      <ul className="space-y-2 text-sm font-bold leading-6 text-stone-700">
        {items.map((item, index) => (
          <li key={`${title}-${index}`} className="rounded-lg bg-[#f7f8f5] px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ElementBars({ result }: { result: FinalReadingResponse }) {
  const counts = result.saju.elements_count;
  const maxCount = Math.max(1, ...elementOrder.map((key) => counts[key] ?? 0));

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-black text-stone-700">오행 분포</h3>
          <p className="mt-1 text-xs font-bold leading-5 text-stone-500">강한 기운과 비어 있는 기운을 함께 봅니다.</p>
        </div>
        <div className="rounded-lg bg-[#f7f8f5] px-3 py-2 text-xs font-black text-stone-600">
          일간 {result.saju.day_master} · {elementLabels[result.saju.day_master_element] ?? result.saju.day_master_element}
        </div>
      </div>

      <div className="space-y-3">
        {elementOrder.map((key) => {
          const count = counts[key] ?? 0;
          return (
            <div key={key} className="grid grid-cols-[42px_1fr_28px] items-center gap-3 text-sm font-bold text-stone-700">
              <span>{elementLabels[key]}</span>
              <div className="h-3 overflow-hidden rounded-full bg-stone-100">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${Math.max(8, (count / maxCount) * 100)}%`, backgroundColor: elementColors[key] }}
                  aria-hidden
                />
              </div>
              <span className="text-right text-ink">{count}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function DaewoonTimeline({ periods }: { periods: DaewoonPeriod[] }) {
  const visiblePeriods = periods.slice(0, 3);

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-black text-stone-700">대운 흐름</h3>
      <div className="grid gap-2">
        {visiblePeriods.map((period) => (
          <div key={`${period.order}-${period.pillar}`} className="rounded-lg bg-[#f7f8f5] px-3 py-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-black text-ink">{period.pillar}</span>
              <span className="text-xs font-black text-stone-500">
                {period.age_start}-{period.age_end}세
              </span>
            </div>
            <p className="mt-1 text-xs font-bold leading-5 text-stone-500">
              {period.start_year}년 시작 · {period.stem_ten_god} · {elementLabels[period.main_element] ?? period.main_element}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ReadingResult({ result, onBack, onRestart }: ReadingResultProps) {
  const { reading, saju, meta } = result;

  return (
    <article className="space-y-5">
      <header className="flex flex-col gap-3 rounded-lg border border-[#eadfce] bg-[#fffdf8] p-4 shadow-soft sm:flex-row sm:items-start sm:justify-between sm:p-5">
        <div>
          <p className="text-sm font-black text-mint">최종 리포트</p>
          <h2 className="mt-1 text-2xl font-black leading-tight text-ink">{reading.reading_title}</h2>
          <p className="mt-2 text-sm font-bold leading-6 text-stone-500">
            {saju.solar_date} · {saju.birth_time}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onBack}
            className="flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 bg-white px-3 text-sm font-bold text-stone-600 hover:bg-cloud"
          >
            <ArrowLeft size={16} aria-hidden />
            답변 수정
          </button>
          <button type="button" onClick={onRestart} className="flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-3 text-sm font-bold text-white hover:bg-berry">
            <RefreshCcw size={16} aria-hidden />
            처음
          </button>
        </div>
      </header>

      <section className="rounded-lg bg-ink p-5 text-white shadow-soft sm:p-6">
        <div className="mb-4 flex items-center gap-2 text-sm font-black text-honey">
          <Sparkles size={18} aria-hidden /> 결론
        </div>
        <p className="max-w-3xl text-xl font-black leading-8 sm:text-2xl sm:leading-9">{reading.core_message}</p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {reading.summary_cards.map((card, index) => (
          <div key={`${card.title}-${index}`} className="rounded-lg border border-[#eadfce] bg-white p-4 shadow-[0_12px_30px_rgba(83,64,42,0.07)]">
            <p className="text-xs font-black text-mint">{card.title}</p>
            <h3 className="mt-2 text-base font-black leading-6 text-ink">{card.headline}</h3>
            <p className="mt-2 text-sm font-bold leading-6 text-stone-600">{card.body}</p>
          </div>
        ))}
      </section>

      <div className="grid gap-5 lg:grid-cols-[1.35fr_0.9fr]">
        <div className="space-y-4">
          <section className="rounded-lg border border-stone-200 bg-white p-4 sm:p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-black text-stone-700">
              <Compass size={18} aria-hidden /> 전문가 해설
            </div>
            <div className="space-y-4">
              {reading.deep_sections.map((section, index) => (
                <section key={`${section.title}-${index}`} className="border-t border-stone-100 pt-4 first:border-t-0 first:pt-0">
                  <h3 className="text-lg font-black leading-7 text-ink">{section.title}</h3>
                  <p className="mt-2 whitespace-pre-line text-base font-medium leading-8 text-stone-700">{section.body}</p>
                </section>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 sm:p-5">
            <h3 className="mb-3 text-sm font-black text-stone-700">풀이 전문</h3>
            <div className="whitespace-pre-line text-base font-medium leading-8 text-stone-800">{reading.final_text}</div>
          </section>
        </div>

        <aside className="space-y-4">
          <SajuPillarsTable saju={saju} />
          <ElementBars result={result} />
          <DaewoonTimeline periods={saju.daewoon} />
          <ReportList title="명식 근거" items={reading.saju_basis} />
          <ReportList title="마음에서 읽힌 신호" items={reading.answer_signals} tone="warm" />
        </aside>
      </div>

      <section className="grid gap-4 lg:grid-cols-3">
        <ReportList title="시기 흐름" items={reading.timing_points} />
        <ReportList title="실행 기준" items={reading.action_steps} tone="warm" />
        <ReportList title="주의할 점" items={reading.watchouts} />
      </section>

      <section className="rounded-lg border border-[#f0dfc4] bg-[#fff8e8] p-4">
        <div className="flex items-start gap-3">
          <CircleAlert className="mt-0.5 shrink-0 text-coral" size={18} aria-hidden />
          <p className="text-sm font-bold leading-6 text-stone-700">{reading.caution}</p>
        </div>
      </section>

      <footer className="flex flex-col gap-2 text-xs font-bold text-stone-400 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <BadgeCheck size={14} aria-hidden />
          <span>명식 계산과 LLM 리포트 생성 완료</span>
        </div>
        <div className="flex items-center gap-2">
          <CalendarClock size={14} aria-hidden />
          <span>
            {meta.provider} · {meta.model}
          </span>
        </div>
      </footer>
    </article>
  );
}
