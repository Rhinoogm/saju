"use client";

import { useId, useState } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  CalendarClock,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  Clock3,
  Copy,
  Gem,
  HeartHandshake,
  Leaf,
  Palette,
  RefreshCcw,
  ShieldCheck,
  Sparkles,
  Star,
  type LucideIcon,
} from "lucide-react";

import { SajuPillarsTable } from "@/components/SajuPillarsTable";
import type { DaewoonPeriod, FinalReadingResponse, LuckRecipeItem, ReadingCareSection } from "@/lib/api";

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

const timingLabels = ["2주", "한 달", "1-3개월"];

interface ReadingResultProps {
  result: FinalReadingResponse;
  profileName: string;
  onBack: () => void;
  onRestart: () => void;
}

function ReportList({ title, items, tone = "light" }: { title: string; items: string[]; tone?: "light" | "warm" }) {
  return (
    <section className={`rounded-lg border p-4 ${tone === "warm" ? "border-[#f0d5dc] bg-[#fff7f8]" : "border-stone-200 bg-white"}`}>
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
                  style={{ width: `${count === 0 ? 0 : Math.max(8, (count / maxCount) * 100)}%`, backgroundColor: elementColors[key] }}
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

function CareSection({
  section,
  icon: Icon,
  tone,
}: {
  section: ReadingCareSection;
  icon: LucideIcon;
  tone: "rose" | "mint" | "honey";
}) {
  const [expanded, setExpanded] = useState(false);
  const detailId = useId();
  const toneClass = {
    rose: "border-[#f0d5dc] bg-[#fff7f8] text-[#7d3f5f]",
    mint: "border-[#cce8e2] bg-[#f4fbf8] text-mint",
    honey: "border-[#f0dfc4] bg-[#fff8e8] text-[#8a6115]",
  }[tone];

  return (
    <section className={`rounded-lg border p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6 ${toneClass}`}>
      <div className="mb-4 flex items-center gap-2 text-sm font-black">
        <Icon size={18} aria-hidden />
        {section.title}
      </div>
      <h3 className="text-xl font-black leading-8 text-ink sm:text-2xl">{section.headline}</h3>
      <p className="mt-3 whitespace-pre-line break-keep text-base font-semibold leading-8 text-stone-700">{section.summary}</p>
      <div id={detailId} hidden={!expanded} className="mt-4 rounded-lg border border-white/70 bg-white/70 px-4 py-4">
        <p className="whitespace-pre-line break-keep text-base font-semibold leading-8 text-stone-700">{section.detail}</p>
      </div>
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={detailId}
        onClick={() => setExpanded((current) => !current)}
        className="mt-4 inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-current/20 bg-white/70 px-3 text-sm font-black transition hover:bg-white"
      >
        {expanded ? <ChevronUp size={16} aria-hidden /> : <ChevronDown size={16} aria-hidden />}
        {expanded ? "접기" : "상세 보기"}
      </button>
    </section>
  );
}

function RecipeIcon({ item }: { item: LuckRecipeItem }) {
  if (item.category === "컬러") return <Palette size={20} aria-hidden />;
  if (item.category === "음식") return <Sparkles size={20} aria-hidden />;
  if (item.category === "작은 습관") return <Leaf size={20} aria-hidden />;
  return <Gem size={20} aria-hidden />;
}

export function ReadingResult({ result, profileName, onBack, onRestart }: ReadingResultProps) {
  const { reading, saju, meta } = result;
  const [copied, setCopied] = useState(false);
  const trimmedName = profileName.trim() || "고객";
  const answerSignalSummary =
    reading.answer_signal_summary ||
    `${reading.answer_signals.join(", ")}의 신호가 함께 보입니다. 겉으로는 차분히 판단하려 해도, 속으로는 더 납득되는 기준과 확신을 찾고 있는 흐름입니다.`;

  async function copyShareText() {
    const shareText = [reading.reading_title, reading.core_message].join("\n");

    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <article className="space-y-5">
      <header className="rounded-lg border border-[#f0d5dc] bg-[#fffaf7] p-5 shadow-soft sm:p-7">
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="inline-flex items-center gap-2 rounded-lg bg-[#fff0f3] px-3 py-1.5 text-xs font-black text-berry">
              <Sparkles size={14} aria-hidden /> 맞춤 사주 리딩
            </p>
            <p className="mt-3 text-sm font-bold leading-6 text-stone-500">
              {saju.solar_date} · {saju.birth_time}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onBack}
              className="flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 bg-white px-3 text-sm font-bold text-stone-600 transition hover:border-mint hover:text-mint"
            >
              <ArrowLeft size={16} aria-hidden />
              답변 수정
            </button>
            <button
              type="button"
              onClick={copyShareText}
              className="flex h-10 items-center justify-center gap-2 rounded-lg border border-[#f0d5dc] bg-white px-3 text-sm font-bold text-berry transition hover:bg-[#fff0f3]"
            >
              <Copy size={16} aria-hidden />
              {copied ? "복사 완료" : "요약 복사"}
            </button>
            <button
              type="button"
              onClick={onRestart}
              className="flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-3 text-sm font-bold text-white transition hover:bg-berry"
            >
              <RefreshCcw size={16} aria-hidden />
              처음
            </button>
          </div>
        </div>

        <h2 className="max-w-3xl break-keep text-3xl font-black leading-tight text-ink sm:text-5xl">{reading.reading_title}</h2>
        <p className="mt-4 max-w-3xl break-keep text-xl font-black leading-9 text-berry sm:text-2xl">{reading.core_message}</p>
      </header>

      <CareSection section={reading.situation_mirror} icon={HeartHandshake} tone="rose" />

      <section className="rounded-lg border border-[#eadfce] bg-white p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
        <div className="mb-4 flex flex-wrap items-center gap-2 text-sm font-black text-stone-700">
          <Star size={17} aria-hidden /> 답변에서 읽힌 신호
        </div>
        <div className="rounded-lg bg-[#f7f8f5] px-4 py-4 text-base font-black leading-7 text-ink sm:px-5">{answerSignalSummary}</div>
        <div className="mt-3 flex flex-wrap gap-2">
          {reading.answer_signals.map((signal) => (
            <span key={signal} className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs font-black text-stone-600">
              {signal}
            </span>
          ))}
        </div>
      </section>

      <CareSection section={reading.saju_insight} icon={Star} tone="mint" />
      <CareSection section={reading.clear_solution} icon={ShieldCheck} tone="honey" />
      <CareSection section={reading.saju_vibe} icon={Leaf} tone="mint" />
      <CareSection section={reading.secret_talent} icon={ShieldCheck} tone="honey" />

      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
        <div className="mb-4 flex items-center gap-2 text-sm font-black text-stone-700">
          <Clock3 size={18} aria-hidden /> 운의 타이밍
        </div>
        <div className="grid gap-3">
          {reading.timing_points.map((point, index) => (
            <div
              key={`${timingLabels[index] ?? "시기"}-${index}`}
              className="grid gap-2 rounded-lg border border-[#e8ece8] bg-[#fbfcf8] p-4 sm:grid-cols-[72px_1fr] sm:items-start"
            >
              <p className="text-xs font-black leading-7 text-mint">{timingLabels[index] ?? "리듬"}</p>
              <p className="text-base font-black leading-7 text-ink">{point}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-[#f0dfc4] bg-[#fffaf0] p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
        <div className="mb-4 flex items-center gap-2 text-sm font-black text-[#8a6115]">
          <Sparkles size={18} aria-hidden /> 행운의 레시피
        </div>
        <div className="grid grid-flow-col auto-cols-[minmax(230px,1fr)] gap-3 overflow-x-auto pb-1 lg:grid-flow-row lg:grid-cols-4 lg:overflow-visible lg:pb-0">
          {reading.luck_recipe.map((item) => (
            <div key={`${item.category}-${item.item}`} className="rounded-lg border border-[#f0dfc4] bg-white p-4">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-[#fff3c9] text-[#8a6115]">
                <RecipeIcon item={item} />
              </div>
              <p className="text-xs font-black text-stone-500">{item.category}</p>
              <h3 className="mt-1 break-keep text-lg font-black leading-7 text-ink">{item.item}</h3>
              <p className="mt-2 break-keep text-sm font-semibold leading-6 text-stone-600">{item.reason}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-[#cce8e2] bg-[#f4fbf8] p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
        <div className="mb-3 flex items-center gap-2 text-sm font-black text-mint">
          <Gem size={18} aria-hidden /> {reading.re_engagement_hook.title}
        </div>
        <p className="text-base font-bold leading-8 text-stone-700">{reading.re_engagement_hook.body}</p>
        <button
          type="button"
          onClick={onRestart}
          className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-black text-white transition hover:bg-mint"
        >
          <RefreshCcw size={16} aria-hidden />
          다른 주제로 다시 보기
        </button>
      </section>

      <section className="rounded-lg border border-stone-200 bg-white shadow-[0_14px_36px_rgba(83,64,42,0.06)]">
        <div className="px-5 py-4">
          <div className="flex items-center gap-2 text-sm font-black text-stone-700">
            <ShieldCheck size={18} aria-hidden /> 전문가 차트
          </div>
          <p className="mt-1 text-xs font-bold leading-5 text-stone-500">명식, 오행, 대운 근거</p>
        </div>
        <div className="grid gap-4 border-t border-stone-100 p-4 lg:grid-cols-2">
          <SajuPillarsTable saju={saju} />
          <ElementBars result={result} />
          <DaewoonTimeline periods={saju.daewoon} />
          <ReportList title="명식 근거" items={reading.saju_basis} />
        </div>
        <div className="border-t border-stone-100 px-5 py-4">
          <div className="flex items-start gap-3 rounded-lg border border-[#f0dfc4] bg-[#fff8e8] p-4">
            <CircleAlert className="mt-0.5 shrink-0 text-coral" size={18} aria-hidden />
            <p className="break-keep text-sm font-bold leading-6 text-stone-700">{reading.caution}</p>
          </div>
        </div>
        <div className="border-t border-stone-100 px-5 py-4">
          <p className="break-keep text-xs font-bold leading-5 text-stone-500">
            이 결과는 {trimmedName}님의 입력 정보와 답변을 바탕으로 생성된 참고용 리딩입니다.
          </p>
        </div>
      </section>

      <footer className="flex flex-col gap-2 text-xs font-bold text-stone-400 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <BadgeCheck size={14} aria-hidden />
          <span>명식 계산과 멘탈 케어 결과 생성 완료</span>
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
