"use client";

import type { PillarDetail, SajuData } from "@/lib/api";

const pillarLabels: Record<string, string> = {
  hour: "생시",
  day: "생일",
  month: "생월",
  year: "생년",
};

const elementLabels: Record<string, string> = {
  wood: "목",
  fire: "화",
  earth: "토",
  metal: "금",
  water: "수",
};

const yinYangLabel: Record<PillarDetail["stem_yin_yang"], string> = {
  yang: "+",
  yin: "-",
};

function PillarCell({ detail }: { detail: PillarDetail }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-lg bg-surface px-3 py-3 shadow-sm dark:shadow-none">
      <div className="font-serif text-3xl font-black tracking-normal text-foreground">{detail.stem}</div>
      <div className="text-xs font-bold text-stone-500 dark:text-stone-400">
        {yinYangLabel[detail.stem_yin_yang]}
        {elementLabels[detail.stem_element] ?? detail.stem_element}
      </div>
      <div className="mt-1 font-serif text-3xl font-black tracking-normal text-foreground">{detail.branch}</div>
      <div className="text-xs font-bold text-stone-500 dark:text-stone-400">
        {yinYangLabel[detail.branch_yin_yang]}
        {elementLabels[detail.branch_element] ?? detail.branch_element}
      </div>
    </div>
  );
}

export function SajuPillarsTable({ saju }: { saju: SajuData }) {
  const columns = (["hour", "day", "month", "year"] as const).map((key) => [key, saju.pillars[key]] as const);

  return (
    <section className="rounded-lg border border-border bg-surface-muted p-4 sm:p-5">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h3 className="text-sm font-black text-stone-700 dark:text-stone-200">명식</h3>
          <p className="mt-1 text-xs font-bold text-stone-500 dark:text-stone-400">천간/지지를 표 형태로 확인합니다.</p>
        </div>
        <div className="rounded-lg bg-surface px-3 py-1 text-xs font-black text-stone-600 shadow-sm dark:text-stone-300 dark:shadow-none">
          일간 {saju.day_master} · {elementLabels[saju.day_master_element] ?? saju.day_master_element}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2 sm:gap-3">
        {columns.map(([key, detail]) => (
          <div key={key} className="space-y-2">
            <div className="text-center text-xs font-black text-stone-500 dark:text-stone-400">{pillarLabels[key]}</div>
            <PillarCell detail={detail} />
            <div className="grid gap-1">
              <div className="rounded-lg bg-surface px-3 py-2 text-center text-xs font-bold text-stone-600 shadow-sm dark:text-stone-300 dark:shadow-none">
                {detail.stem_ten_god ?? "—"}
              </div>
              <div className="rounded-lg bg-surface px-3 py-2 text-center text-xs font-bold text-stone-600 shadow-sm dark:text-stone-300 dark:shadow-none">
                {detail.branch_ten_god ?? "—"}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs font-bold text-stone-600 sm:grid-cols-4">
        {columns.map(([key, detail]) => (
          <div key={`${key}-pillar`} className="rounded-lg bg-surface px-3 py-2 text-center shadow-sm dark:text-stone-300 dark:shadow-none">
            {detail.pillar}
          </div>
        ))}
      </div>
    </section>
  );
}
