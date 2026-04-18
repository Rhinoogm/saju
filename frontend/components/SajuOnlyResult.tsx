"use client";

import { ArrowLeft, RefreshCcw } from "lucide-react";

import type { SajuData, PillarDetail } from "@/lib/api";
import { SajuPillarsTable } from "@/components/SajuPillarsTable";

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

interface SajuOnlyResultProps {
  saju: SajuData;
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

export function SajuOnlyResult({ saju, onBack, onRestart }: SajuOnlyResultProps) {
  return (
    <article className="space-y-4 rounded-2xl border border-stone-200 bg-white p-4 shadow-soft sm:p-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cream text-xl font-black text-ink shadow-sm">
            {saju.day_master}
          </div>
          <div>
            <p className="text-sm font-black text-mint">사주만</p>
            <h2 className="mt-1 text-2xl font-black text-ink">명식 확인</h2>
            <p className="mt-2 text-sm leading-6 text-stone-500">
              {saju.solar_date} · {saju.birth_time}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onBack}
            className="flex h-10 items-center justify-center gap-2 rounded-xl border border-stone-200 px-3 text-sm font-bold text-stone-600 hover:bg-cloud"
          >
            <ArrowLeft size={16} aria-hidden />
            입력으로
          </button>
          <button
            type="button"
            onClick={onRestart}
            className="flex h-10 items-center justify-center gap-2 rounded-xl bg-ink px-3 text-sm font-bold text-white hover:bg-berry"
          >
            <RefreshCcw size={16} aria-hidden />
            처음
          </button>
        </div>
      </header>

      <SajuPillarsTable saju={saju} />

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-stone-200 bg-white p-4">
          <h3 className="mb-3 text-sm font-black text-stone-700">일간</h3>
          <div className="text-base font-black text-ink">
            {saju.day_master} ({elementLabels[saju.day_master_element]})
          </div>
        </section>

        <section className="rounded-2xl border border-stone-200 bg-white p-4">
          <h3 className="mb-3 text-sm font-black text-stone-700">오행 분포</h3>
          <div className="grid grid-cols-5 gap-2 text-center text-sm font-black text-stone-700">
            {(["wood", "fire", "earth", "metal", "water"] as const).map((key) => (
              <div key={key} className="rounded-xl bg-cloud px-2 py-3">
                <div className="text-xs text-stone-500">{elementLabels[key]}</div>
                <div className="text-lg text-ink">{saju.elements_count[key] ?? 0}</div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-stone-200 bg-cloud p-4 text-sm font-bold leading-6 text-stone-700">
        {saju.calculation_note}
      </section>
    </article>
  );
}

