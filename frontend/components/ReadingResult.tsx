"use client";

import { toPng } from "html-to-image";
import { useRef, useState, type ReactNode, type RefObject } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  BarChart3,
  CalendarClock,
  CircleAlert,
  Compass,
  Copy,
  Download,
  Flame,
  Gem,
  MapPinned,
  MoonStar,
  RefreshCcw,
  Share2,
  Sparkles,
  Sprout,
  Star,
  Target,
  type LucideIcon,
} from "lucide-react";

import { SajuPillarsTable } from "@/components/SajuPillarsTable";
import type { FinalReadingResponse, ReadingStyle, TenGodScore, TimeLuckPillar, YonghuishinCandidate } from "@/lib/api";

const elementLabels: Record<string, string> = {
  wood: "목",
  fire: "화",
  earth: "토",
  metal: "금",
  water: "수",
};

const elementOrder = ["wood", "fire", "earth", "metal", "water"] as const;
type ElementKey = (typeof elementOrder)[number];

const elementColors: Record<ElementKey, string> = {
  wood: "#4f8f6b",
  fire: "#d45c3f",
  earth: "#c6a14a",
  metal: "#9aa0a6",
  water: "#4f6fa5",
};

const cardThemes: Record<ElementKey, { bg: string; accent: string; soft: string; text: string }> = {
  wood: { bg: "#173f32", accent: "#7ad0a1", soft: "rgba(122, 208, 161, 0.18)", text: "#f3fff8" },
  fire: { bg: "#4b1e24", accent: "#ff8a58", soft: "rgba(255, 138, 88, 0.18)", text: "#fff7ef" },
  earth: { bg: "#40351f", accent: "#f0c95d", soft: "rgba(240, 201, 93, 0.18)", text: "#fff9e8" },
  metal: { bg: "#24272b", accent: "#dfe4e8", soft: "rgba(223, 228, 232, 0.16)", text: "#f8fbfd" },
  water: { bg: "#111b31", accent: "#7fa7e6", soft: "rgba(127, 167, 230, 0.18)", text: "#f2f7ff" },
};

const stemProfiles: Record<string, { term: string; plain: string }> = {
  甲: { term: "갑목(甲木)", plain: "큰 나무처럼 방향을 세우고 길게 성장하려는 성향" },
  乙: { term: "을목(乙木)", plain: "풀과 덩굴처럼 유연하게 적응하며 기회를 만드는 성향" },
  丙: { term: "병화(丙火)", plain: "태양처럼 드러내고 설명하며 분위기를 밝히는 성향" },
  丁: { term: "정화(丁火)", plain: "촛불처럼 필요한 곳에 집중력과 온기를 주는 성향" },
  戊: { term: "무토(戊土)", plain: "산처럼 중심을 잡고 사람과 일을 안정시키는 성향" },
  己: { term: "기토(己土)", plain: "밭처럼 현실을 다지고 쓸모 있게 길러내는 성향" },
  庚: { term: "경금(庚金)", plain: "큰 쇠처럼 기준을 세우고 불필요한 것을 덜어내는 성향" },
  辛: { term: "신금(辛金)", plain: "보석처럼 섬세하게 완성도와 품질을 높이는 성향" },
  壬: { term: "임수(壬水)", plain: "큰 물처럼 흐름을 읽고 넓게 연결하며 유연하게 움직이는 성향" },
  癸: { term: "계수(癸水)", plain: "비와 이슬처럼 조용히 관찰하고 깊이 흡수하는 성향" },
};

const personaLabels: Record<ReadingStyle, string> = {
  traditional: "계룡산 정통 철학관",
  empathetic: "극F 과몰입 언니 철학관",
  direct: "개발자 명리학자 철학관",
};

interface ReadingResultProps {
  result: FinalReadingResponse;
  profileName: string;
  initialConcern: string;
  readingStyle: ReadingStyle;
  onBack: () => void;
  onRestart: () => void;
}

function elementName(key: string) {
  return elementLabels[key] ?? key;
}

function formatElementLabel(element: string) {
  return elementName(element);
}

function normalizeElement(key: string): ElementKey {
  return elementOrder.includes(key as ElementKey) ? (key as ElementKey) : "wood";
}

function primaryElementColor(key: string) {
  return elementColors[normalizeElement(key)];
}

function downloadDataUrl(dataUrl: string, fileName: string) {
  const link = document.createElement("a");
  link.download = fileName;
  link.href = dataUrl;
  link.click();
}

function getPrimaryYongshin(result: FinalReadingResponse) {
  return result.saju.yonghuishin.yongshin.final_yongshin[0] ?? { element: result.saju.day_master_element, score: null, reason: "일간의 기본 기운을 중심으로 봅니다." };
}

function scoreToPercent(score: number | null, maxScore: number) {
  if (score === null || maxScore <= 0) return 0;
  return Math.max(0, Math.min(100, (score / maxScore) * 100));
}

function confidencePercent(value: number) {
  const normalized = value > 1 ? value : value * 100;
  return Math.max(0, Math.min(100, Math.round(normalized)));
}

function formatCandidate(candidate: YonghuishinCandidate) {
  const score = candidate.score === null ? "점수 없음" : candidate.score.toFixed(3);
  return `${formatElementLabel(candidate.element)} · ${score}`;
}

function SectionHeading({
  index,
  icon: Icon,
  label,
  title,
  description,
}: {
  index: string;
  icon: LucideIcon;
  label: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="mb-4 flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <p className="inline-flex max-w-full items-center gap-2 rounded-lg bg-surface-muted px-3 py-1.5 text-xs font-black text-sage dark:text-[#c9d4bd]">
          <Icon size={15} strokeWidth={2.5} aria-hidden />
          <span className="min-w-0 break-keep">
            {index} · {label}
          </span>
        </p>
        <h3 className="mt-3 break-keep font-serif text-2xl font-black leading-tight text-foreground sm:text-3xl">{title}</h3>
      </div>
      {description && <p className="min-w-0 max-w-md break-keep text-sm font-bold leading-6 text-stone-600 dark:text-stone-300">{description}</p>}
    </div>
  );
}

function AnalysisStatCard({
  icon: Icon,
  label,
  title,
  metric,
  body,
  tone = "sage",
  children,
}: {
  icon: LucideIcon;
  label: string;
  title: string;
  metric: string;
  body: string;
  tone?: "sage" | "terracotta" | "neutral";
  children?: ReactNode;
}) {
  const toneClass =
    tone === "terracotta"
      ? "bg-terracotta/10 text-terracotta dark:text-[#d58c6d]"
      : tone === "neutral"
        ? "bg-surface-muted text-stone-600 dark:text-stone-300"
        : "bg-sage/10 text-sage dark:text-[#c9d4bd]";

  return (
    <article className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <p className={`inline-flex min-w-0 items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-black ${toneClass}`}>
          <Icon size={14} aria-hidden />
          <span className="min-w-0 break-keep">{label}</span>
        </p>
        <span className="shrink-0 rounded-lg bg-surface-muted px-3 py-1.5 text-xs font-black text-stone-600 dark:text-stone-300">{metric}</span>
      </div>
      <h4 className="mt-4 break-keep font-serif text-2xl font-black leading-tight text-foreground [overflow-wrap:anywhere]">{title}</h4>
      <p className="mt-3 break-keep text-sm font-bold leading-6 text-stone-600 dark:text-stone-300">{body}</p>
      {children && <div className="mt-4 min-w-0">{children}</div>}
    </article>
  );
}

function ElementPowerBars({ result }: { result: FinalReadingResponse }) {
  const power = result.saju.yonghuishin.element_power;
  const maxPower = Math.max(0.001, ...elementOrder.map((key) => power[key] ?? 0));

  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <div className="mb-4 flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="text-sm font-black text-foreground">오행 세력</h4>
          <p className="mt-1 break-keep text-xs font-bold leading-5 text-stone-500 dark:text-stone-400">지장간·월령·통근·투출 보정값입니다.</p>
        </div>
        <span className="shrink-0 rounded-lg bg-surface-muted px-3 py-2 text-xs font-black text-stone-600 dark:text-stone-300">계산값</span>
      </div>

      <div className="space-y-3">
        {elementOrder.map((key) => {
          const value = power[key] ?? 0;
          return (
            <div key={key} className="grid min-w-0 grid-cols-[34px_minmax(0,1fr)_48px] items-center gap-3 text-sm font-bold text-stone-700 dark:text-stone-300">
              <span>{formatElementLabel(key)}</span>
              <div className="h-3 min-w-0 overflow-hidden rounded-full bg-surface-muted">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${scoreToPercent(value, maxPower)}%`, backgroundColor: elementColors[key] }}
                  aria-hidden
                />
              </div>
              <span className="text-right text-foreground">{value.toFixed(2)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CandidateGroup({ label, candidates, tone }: { label: string; candidates: YonghuishinCandidate[]; tone: "sage" | "terracotta" | "neutral" }) {
  const toneClass =
    tone === "terracotta"
      ? "bg-terracotta/10 text-terracotta dark:text-[#d58c6d]"
      : tone === "neutral"
        ? "bg-surface-muted text-stone-600 dark:text-stone-300"
        : "bg-sage/10 text-sage dark:text-[#c9d4bd]";
  const maxScore = Math.max(0.001, ...candidates.map((candidate) => Math.abs(candidate.score ?? 0)));

  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <p className={`inline-flex rounded-lg px-3 py-1.5 text-xs font-black ${toneClass}`}>{label}</p>
      <div className="mt-4 space-y-3">
        {candidates.map((candidate, index) => {
          const color = primaryElementColor(candidate.element);
          const score = Math.abs(candidate.score ?? 0);
          return (
            <div key={`${label}-${candidate.element}-${index}`} className="min-w-0 rounded-lg bg-surface-muted p-3">
              <div className="flex min-w-0 items-center justify-between gap-3">
                <p className="min-w-0 break-keep text-sm font-black text-foreground">{formatCandidate(candidate)}</p>
                <span className="h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: color }} aria-hidden />
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface">
                <div className="h-full rounded-full" style={{ width: `${scoreToPercent(score, maxScore)}%`, backgroundColor: color }} aria-hidden />
              </div>
              <p className="mt-3 break-keep text-xs font-bold leading-5 text-stone-500 dark:text-stone-400">{candidate.reason}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DeterministicAnalysisPanel({ result }: { result: FinalReadingResponse }) {
  const { saju } = result;
  const analysis = saju.yonghuishin;
  const { strength, geokguk, yongshin, interpretation } = analysis;
  const finalYongshin = yongshin.final_yongshin[0];
  const monthSource = geokguk.selected_from_month;
  const pillarSummary = (["year", "month", "day", "hour"] as const).map((key) => saju.pillars[key].pillar).join(" · ");
  const dominantTenGod = `${saju.dominant_ten_god.name} ${saju.dominant_ten_god.score.toFixed(1)}`;
  const finalYongshinLabel = yongshin.final_yongshin.map((candidate) => formatElementLabel(candidate.element)).join(" · ");

  return (
    <section className="mt-5 min-w-0 rounded-lg border border-border bg-background/60 p-4 dark:bg-[#242321]">
      <div className="mb-4 flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="inline-flex max-w-full items-center gap-2 rounded-lg bg-surface px-3 py-1.5 text-xs font-black text-sage dark:text-[#c9d4bd]">
            <BarChart3 size={14} aria-hidden />
            <span className="min-w-0 break-keep">계산 기반 분석</span>
          </p>
          <h4 className="mt-3 break-keep font-serif text-xl font-black leading-8 text-foreground">원국과 용희신 판정값</h4>
        </div>
        <div className="grid min-w-0 gap-2 text-xs font-black text-stone-600 sm:grid-cols-3 dark:text-stone-300">
          <span className="min-w-0 rounded-lg bg-surface px-3 py-2 text-center [overflow-wrap:anywhere]">일간 {saju.day_master} · {formatElementLabel(saju.day_master_element)}</span>
          <span className="min-w-0 rounded-lg bg-surface px-3 py-2 text-center [overflow-wrap:anywhere]">월령 {saju.pillars.month.branch}</span>
          <span className="min-w-0 rounded-lg bg-surface px-3 py-2 text-center [overflow-wrap:anywhere]">주요 십성 {dominantTenGod}</span>
        </div>
      </div>

      <div className="mb-4 rounded-lg border border-border bg-surface p-4">
        <p className="text-xs font-black text-stone-500 dark:text-stone-400">원국 요약</p>
        <p className="mt-2 break-keep text-base font-black leading-7 text-foreground [overflow-wrap:anywhere]">{pillarSummary}</p>
        <p className="mt-2 break-keep text-sm font-bold leading-6 text-stone-600 dark:text-stone-300">{interpretation.summary}</p>
      </div>

      <div className="grid min-w-0 gap-4 lg:grid-cols-3">
        <AnalysisStatCard
          icon={Target}
          label="일간 강약"
          title={strength.label}
          metric={`${confidencePercent(strength.strength_index)}%`}
          body={interpretation.strength_reading}
        >
          <div className="grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            <div className="rounded-lg bg-surface-muted px-3 py-2 text-xs font-black text-stone-600 dark:text-stone-300">생조 {strength.support_score.toFixed(2)}</div>
            <div className="rounded-lg bg-surface-muted px-3 py-2 text-xs font-black text-stone-600 dark:text-stone-300">소모·제어 {strength.drain_score.toFixed(2)}</div>
          </div>
        </AnalysisStatCard>

        <AnalysisStatCard
          icon={Star}
          label="격국"
          title={geokguk.name}
          metric={`${confidencePercent(geokguk.confidence)}%`}
          body={interpretation.geokguk_reading}
          tone="neutral"
        >
          <div className="grid min-w-0 gap-2 text-xs font-black text-stone-600 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3 dark:text-stone-300">
            <span className="rounded-lg bg-surface-muted px-3 py-2 text-center">월지 {monthSource.month_branch}</span>
            <span className="rounded-lg bg-surface-muted px-3 py-2 text-center">{monthSource.selected_hidden_stem} · {monthSource.ten_god}</span>
            <span className="rounded-lg bg-surface-muted px-3 py-2 text-center">{monthSource.transmitted ? "투출" : "본기"}</span>
          </div>
        </AnalysisStatCard>

        <AnalysisStatCard
          icon={Compass}
          label="최종 용신"
          title={finalYongshinLabel}
          metric={finalYongshin?.score === null || finalYongshin?.score === undefined ? "점수 없음" : finalYongshin.score.toFixed(3)}
          body={interpretation.yongshin_reading}
          tone="terracotta"
        />
      </div>

      <div className="mt-4 grid min-w-0 gap-4 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <div className="grid min-w-0 gap-4">
          <ElementPowerBars result={result} />
          <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
            <p className="text-sm font-black text-foreground">판정 근거</p>
            <div className="mt-3 grid min-w-0 gap-2">
              {[...strength.evidence, ...geokguk.damage].map((item, index) => (
                <p key={`${item}-${index}`} className="min-w-0 rounded-lg bg-surface-muted px-3 py-2 text-xs font-bold leading-5 text-stone-600 dark:text-stone-300">
                  {item}
                </p>
              ))}
            </div>
          </div>
        </div>

        <div className="grid min-w-0 gap-4">
          <CandidateGroup label="용신" candidates={yongshin.final_yongshin} tone="terracotta" />
          <div className="grid min-w-0 gap-4 sm:grid-cols-2">
            <CandidateGroup label="희신" candidates={yongshin.huishin} tone="sage" />
            <CandidateGroup label="기신" candidates={yongshin.gishin} tone="neutral" />
          </div>
        </div>
      </div>
    </section>
  );
}

function ElementBars({ result }: { result: FinalReadingResponse }) {
  const counts = result.saju.elements_count;
  const maxCount = Math.max(1, ...elementOrder.map((key) => counts[key] ?? 0));

  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <div className="mb-4 flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="text-sm font-black text-foreground">오행 분포</h4>
          <p className="mt-1 break-keep text-xs font-bold leading-5 text-stone-500 dark:text-stone-400">강한 기운과 비어 있는 기운을 함께 봅니다.</p>
        </div>
        <div className="shrink-0 rounded-lg bg-surface-muted px-3 py-2 text-xs font-black text-stone-600 dark:text-stone-300">
          일간 {result.saju.day_master}
        </div>
      </div>

      <div className="space-y-3">
        {elementOrder.map((key) => {
          const count = counts[key] ?? 0;
          return (
            <div key={key} className="grid min-w-0 grid-cols-[34px_minmax(0,1fr)_24px] items-center gap-3 text-sm font-bold text-stone-700 dark:text-stone-300">
              <span>{elementLabels[key]}</span>
              <div className="h-3 min-w-0 overflow-hidden rounded-full bg-surface-muted">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${count === 0 ? 0 : Math.max(8, (count / maxCount) * 100)}%`, backgroundColor: elementColors[key] }}
                  aria-hidden
                />
              </div>
              <span className="text-right text-foreground">{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LuckChip({ luck, icon: Icon }: { luck: TimeLuckPillar; icon: LucideIcon }) {
  const color = primaryElementColor(luck.stem_element);

  return (
    <article className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <p className="inline-flex min-w-0 items-center gap-2 text-xs font-black text-stone-500 dark:text-stone-400">
          <Icon size={15} aria-hidden />
          <span className="min-w-0 break-keep">{luck.label}</span>
        </p>
        <span className="shrink-0 rounded-lg px-2 py-1 text-xs font-black text-white" style={{ backgroundColor: color }}>
          {elementName(luck.stem_element)}
        </span>
      </div>
      <div className="mt-3 flex min-w-0 items-end gap-3">
        <span className="font-serif text-4xl font-black leading-none text-foreground">{luck.pillar}</span>
        <span className="pb-1 text-xs font-bold text-stone-500 dark:text-stone-400">{luck.representative_date}</span>
      </div>
      <p className="mt-3 break-keep text-sm font-bold leading-6 text-stone-700 dark:text-stone-300">
        천간 {luck.stem_ten_god} · 지지 {luck.branch_ten_god}
      </p>
    </article>
  );
}

function TenGodScores({ scores, dominant }: { scores: TenGodScore[]; dominant: TenGodScore }) {
  const topScores = scores.length > 0 ? scores.slice(0, 4) : [dominant];
  const maxScore = Math.max(1, ...topScores.map((score) => score.score));

  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <div className="mb-4 flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="text-sm font-black text-foreground">주무기 십성</h4>
          <p className="mt-1 break-keep text-xs font-bold leading-5 text-stone-500 dark:text-stone-400">원국 안에서 가장 도드라진 작동 방식입니다.</p>
        </div>
        <span className="shrink-0 rounded-lg bg-terracotta px-3 py-2 text-xs font-black text-white">{dominant.name}</span>
      </div>

      <div className="space-y-3">
        {topScores.map((score) => (
          <div key={score.name} className="grid min-w-0 grid-cols-[48px_minmax(0,1fr)_38px] items-center gap-3 text-sm font-bold text-stone-700 dark:text-stone-300">
            <span className="break-keep">{score.name}</span>
            <div className="h-3 min-w-0 overflow-hidden rounded-full bg-surface-muted">
              <div className="h-full rounded-full bg-terracotta" style={{ width: `${Math.max(8, (score.score / maxScore) * 100)}%` }} aria-hidden />
            </div>
            <span className="text-right text-foreground">{score.score.toFixed(1)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CompassSection({ result, concernText, name }: { result: FinalReadingResponse; concernText: string; name: string }) {
  const { reading } = result;
  const yongshin = getPrimaryYongshin(result);

  return (
    <section className="relative overflow-hidden rounded-lg border border-border bg-surface p-4 shadow-ritual sm:p-6 lg:p-7 dark:shadow-ritual-dark">
      <div className="pointer-events-none absolute -right-16 top-8 h-56 w-56 rounded-full border opacity-25" style={{ borderColor: primaryElementColor(yongshin.element) }} aria-hidden />
      <div className="relative z-10 min-w-0">
        <div className="mb-5 flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="inline-flex max-w-full items-center gap-2 rounded-lg bg-terracotta/10 px-3 py-1.5 text-xs font-black text-terracotta dark:text-[#d58c6d]">
              <Compass size={14} aria-hidden />
              <span className="min-w-0 break-keep">핵심 결론</span>
            </p>
          </div>
          <div className="w-fit rounded-lg bg-surface-muted px-3 py-2 text-xs font-black text-stone-600 dark:text-stone-300">
            필요한 기운 · {elementName(yongshin.element)}
          </div>
        </div>

        <div className="min-w-0 max-w-4xl">
          <div className="min-w-0 rounded-lg bg-surface-muted px-4 py-3">
            <p className="text-xs font-black text-stone-500 dark:text-stone-400">{name}님이 입력한 고민</p>
            <p className="mt-2 break-keep text-base font-black leading-7 text-foreground [overflow-wrap:anywhere]">{concernText}</p>
          </div>
          <p className="mt-5 text-xs font-black text-sage dark:text-[#c9d4bd]">핵심 결론</p>
          <h2 className="mt-2 break-keep font-serif text-2xl font-black leading-tight text-foreground [overflow-wrap:anywhere] sm:text-4xl">{reading.compass_summary.strength_animal}</h2>
          <p className="mt-4 break-keep text-base font-bold leading-8 text-stone-700 dark:text-stone-300">{reading.compass_summary.basis}</p>
          <p className="mt-3 break-keep text-base font-black leading-8 text-sage dark:text-[#c9d4bd]">{reading.compass_summary.solution}</p>
        </div>
      </div>
    </section>
  );
}

function HealingCardVisual({ refNode, result, name }: { refNode: RefObject<HTMLDivElement | null>; result: FinalReadingResponse; name: string }) {
  const card = result.reading.healing_card;
  const yongshin = normalizeElement(getPrimaryYongshin(result).element);
  const theme = cardThemes[yongshin];

  return (
    <div
      ref={refNode}
      className="relative min-h-[30rem] w-full overflow-hidden rounded-lg border border-black/20 p-5 shadow-ritual sm:min-h-[34rem] sm:p-7"
      style={{ backgroundColor: theme.bg, color: theme.text }}
    >
      <div className="pointer-events-none absolute right-[-4rem] top-[-4rem] h-64 w-64 rounded-full blur-2xl" style={{ backgroundColor: theme.soft }} aria-hidden />
      <div className="pointer-events-none absolute bottom-[-5rem] left-[-3rem] h-72 w-72 rounded-full blur-2xl" style={{ backgroundColor: theme.soft }} aria-hidden />

      <div className="relative z-10 flex min-h-[27rem] min-w-0 flex-col justify-between gap-8 sm:min-h-[29rem]">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <p className="inline-flex max-w-full items-center gap-2 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-black backdrop-blur">
            <MoonStar size={14} aria-hidden />
            <span className="min-w-0 break-keep">나만의 힐링 오브제</span>
          </p>
          <p className="shrink-0 rounded-lg border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-black backdrop-blur">
            {elementName(yongshin)} · {card.direction}
          </p>
        </div>

        <div className="min-w-0 max-w-[40rem]">
          <p className="text-xs font-black opacity-75">{name}님의 모바일 카드</p>
          <h4 className="mt-3 max-w-[34rem] break-keep font-serif text-[2rem] font-black leading-tight tracking-normal [overflow-wrap:anywhere] sm:text-5xl">
            {card.metaphor_sentence}
          </h4>
          <p className="mt-5 max-w-[34rem] break-keep text-lg font-black leading-8 [overflow-wrap:anywhere] sm:text-2xl" style={{ color: theme.accent }}>
            {card.affirmation}
          </p>
        </div>

        <div className="grid min-w-0 gap-2 text-xs font-black sm:grid-cols-3">
          <div className="min-w-0 rounded-lg border border-white/10 bg-white/[0.08] px-3 py-3 backdrop-blur">
            <span className="block opacity-65">행운 색상</span>
            <span className="mt-1 block break-keep [overflow-wrap:anywhere]">{card.color}</span>
          </div>
          <div className="min-w-0 rounded-lg border border-white/10 bg-white/[0.08] px-3 py-3 backdrop-blur">
            <span className="block opacity-65">방향</span>
            <span className="mt-1 block break-keep [overflow-wrap:anywhere]">{card.direction}</span>
          </div>
          <div className="min-w-0 rounded-lg border border-white/10 bg-white/[0.08] px-3 py-3 backdrop-blur">
            <span className="block opacity-65">작은 루틴</span>
            <span className="mt-1 block break-keep [overflow-wrap:anywhere]">{card.ritual}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ReadingResult({ result, profileName, initialConcern, readingStyle, onBack, onRestart }: ReadingResultProps) {
  const { reading, saju, meta } = result;
  const summaryCardRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [exportStatus, setExportStatus] = useState("");
  const trimmedName = profileName.trim() || "고객";
  const concernText = initialConcern.trim() || "지금 가장 신경 쓰이는 고민";
  const primaryYongshin = getPrimaryYongshin(result);
  const dayMasterProfile = stemProfiles[saju.day_master];

  async function copyShareText() {
    const shareText = [
      reading.reading_title,
      reading.compass_summary.strength_animal,
      reading.compass_summary.basis,
      reading.compass_summary.solution,
      `요약: ${reading.compass_summary.headline}`,
      `힐링 카드: ${reading.healing_card.metaphor_sentence}`,
      `오늘의 문장: ${reading.healing_card.affirmation}`,
      `행운 요소: ${reading.healing_card.color} · ${reading.healing_card.direction}`,
      `다음 흐름: ${reading.secret_door.teaser}`,
    ].join("\n");

    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  async function exportSummaryCard({ share }: { share: boolean }) {
    if (!summaryCardRef.current) return;

    setExportStatus(share ? "공유 이미지를 준비 중입니다." : "PNG를 준비 중입니다.");
    try {
      const dataUrl = await toPng(summaryCardRef.current, {
        cacheBust: true,
        pixelRatio: 2,
        backgroundColor: cardThemes[normalizeElement(primaryYongshin.element)].bg,
      });

      if (share) {
        const blob = await (await fetch(dataUrl)).blob();
        const file = new File([blob], "saju-healing-card.png", { type: "image/png" });
        if (typeof navigator.share === "function" && (!navigator.canShare || navigator.canShare({ files: [file] }))) {
          await navigator.share({
            files: [file],
            title: reading.reading_title,
            text: reading.compass_summary.headline,
          });
          setExportStatus("공유 창을 열었습니다.");
          return;
        }
      }

      downloadDataUrl(dataUrl, "saju-healing-card.png");
      setExportStatus(share ? "이 브라우저에서는 공유 대신 PNG로 저장했습니다." : "PNG 저장을 시작했습니다.");
    } catch (error) {
      setExportStatus(error instanceof Error ? error.message : "요약 카드 생성에 실패했습니다.");
    }
  }

  return (
    <article className="w-full max-w-full space-y-4 overflow-hidden">
      <section className="rounded-lg border border-border bg-surface p-4 shadow-ritual sm:p-5 dark:shadow-ritual-dark">
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="inline-flex max-w-full items-center gap-2 rounded-lg bg-surface-muted px-3 py-1.5 text-xs font-black text-sage dark:text-[#c9d4bd]">
              <Sparkles size={14} aria-hidden />
              <span className="min-w-0 break-keep">{personaLabels[readingStyle]}</span>
            </p>
            <p className="mt-3 break-keep text-sm font-bold leading-6 text-stone-500 dark:text-stone-400">
              기준일 {saju.current_luck.reference_date} · 일간 {saju.day_master}({elementName(saju.day_master_element)})
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onBack}
              className="flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3 text-sm font-bold text-stone-600 transition hover:border-sage hover:text-sage dark:text-stone-300"
            >
              <ArrowLeft size={16} aria-hidden />
              답변 수정
            </button>
            <button
              type="button"
              onClick={copyShareText}
              className="flex h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3 text-sm font-bold text-stone-600 transition hover:border-terracotta hover:text-terracotta dark:text-stone-300"
            >
              <Copy size={16} aria-hidden />
              {copied ? "복사 완료" : "요약 복사"}
            </button>
            <button
              type="button"
              onClick={onRestart}
              className="flex h-10 items-center justify-center gap-2 rounded-lg bg-sage px-3 text-sm font-bold text-white transition hover:bg-[#4c5d50]"
            >
              <RefreshCcw size={16} aria-hidden />
              처음
            </button>
          </div>
        </div>
      </section>

      <CompassSection result={result} concernText={concernText} name={trimmedName} />

      <section className="min-w-0 rounded-lg border border-border bg-surface p-4 shadow-ritual sm:p-5 dark:shadow-ritual-dark">
        <SectionHeading index="02" icon={Star} label="만세력 요약" title={reading.manse_summary.headline} description="기운의 분포와 주요한 작동 방식을 한눈에 봅니다." />
        <p className="mb-4 break-keep text-base font-bold leading-8 text-stone-700 dark:text-stone-300">{reading.manse_summary.energy_overview}</p>
        <div className="mb-4 grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {reading.manse_summary.key_traits.map((trait, index) => (
            <div key={`${trait}-${index}`} className="min-w-0 rounded-lg bg-surface-muted px-4 py-3 text-sm font-black leading-6 text-stone-700 dark:text-stone-300">
              {trait}
            </div>
          ))}
        </div>
        <DeterministicAnalysisPanel result={result} />
        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="grid min-w-0 gap-4">
            <ElementBars result={result} />
            <TenGodScores scores={saju.ten_god_scores} dominant={saju.dominant_ten_god} />
            <div className="grid min-w-0 gap-3 sm:grid-cols-2">
              <LuckChip luck={saju.current_luck.annual} icon={Flame} />
              <LuckChip luck={saju.current_luck.next_month} icon={CalendarClock} />
            </div>
          </div>
          <div className="min-w-0">
            <SajuPillarsTable saju={saju} />
          </div>
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-border bg-background/70 p-4 shadow-ritual sm:p-5 dark:bg-[#242321] dark:shadow-ritual-dark">
        <SectionHeading index="03" icon={Sprout} label="사주 풀이" title="운명의 양면성" description="무속적 예언보다 기질의 장점과 보완점을 객관적으로 정리합니다." />
        <div className="grid min-w-0 gap-4 lg:grid-cols-2">
          <article className="min-w-0 rounded-lg border border-border bg-surface p-4">
            <p className="text-xs font-black text-sage dark:text-[#c9d4bd]">{reading.dual_reading.weapon.title}</p>
            <h4 className="mt-3 break-keep font-serif text-2xl font-black leading-tight text-foreground">{reading.dual_reading.weapon.headline}</h4>
            <p className="mt-4 whitespace-pre-line break-keep text-base font-semibold leading-8 text-stone-600 dark:text-stone-300">{reading.dual_reading.weapon.body}</p>
          </article>
          <article className="min-w-0 rounded-lg border border-border bg-surface p-4">
            <p className="text-xs font-black text-terracotta dark:text-[#d58c6d]">{reading.dual_reading.growth_hint.title}</p>
            <h4 className="mt-3 break-keep font-serif text-2xl font-black leading-tight text-foreground">{reading.dual_reading.growth_hint.headline}</h4>
            <p className="mt-4 whitespace-pre-line break-keep text-base font-semibold leading-8 text-stone-600 dark:text-stone-300">{reading.dual_reading.growth_hint.body}</p>
          </article>
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-border bg-surface p-4 shadow-ritual sm:p-5 dark:shadow-ritual-dark">
        <SectionHeading index="04" icon={Gem} label="모바일 공유용 카드" title="나만의 힐링 오브제" description="용신 오행을 색상, 방향, 짧은 루틴으로 번역한 저장용 카드입니다." />
        <div className="min-w-0 space-y-4">
          <HealingCardVisual refNode={summaryCardRef} result={result} name={trimmedName} />
          <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
            <div className="min-w-0 rounded-lg border border-border bg-surface-muted p-4">
              <p className="text-xs font-black text-sage dark:text-[#c9d4bd]">카드 해석</p>
              <p className="mt-3 break-keep text-base font-bold leading-8 text-stone-700 dark:text-stone-300">{reading.healing_card.interpretation}</p>
            </div>
            <div className="grid min-w-0 gap-3 sm:grid-cols-3">
              <div className="min-w-0 rounded-lg border border-border bg-background/70 p-4 dark:bg-[#242321]">
                <p className="text-xs font-black text-stone-500 dark:text-stone-400">용신</p>
                <p className="mt-2 break-keep text-lg font-black text-foreground">{reading.healing_card.lucky_element}</p>
              </div>
              <div className="min-w-0 rounded-lg border border-border bg-background/70 p-4 dark:bg-[#242321]">
                <p className="text-xs font-black text-stone-500 dark:text-stone-400">색상</p>
                <p className="mt-2 break-keep text-lg font-black text-foreground">{reading.healing_card.color}</p>
              </div>
              <div className="min-w-0 rounded-lg border border-border bg-background/70 p-4 dark:bg-[#242321]">
                <p className="text-xs font-black text-stone-500 dark:text-stone-400">방향</p>
                <p className="mt-2 break-keep text-lg font-black text-foreground">{reading.healing_card.direction}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={() => exportSummaryCard({ share: false })}
              className="flex h-12 flex-1 items-center justify-center gap-2 rounded-lg bg-sage px-4 text-sm font-black text-white transition hover:bg-[#4c5d50]"
            >
              <Download size={17} aria-hidden />
              카드 PNG 저장
            </button>
            <button
              type="button"
              onClick={() => exportSummaryCard({ share: true })}
              className="flex h-12 flex-1 items-center justify-center gap-2 rounded-lg bg-terracotta px-4 text-sm font-black text-white transition hover:bg-[#b46d4d]"
            >
              <Share2 size={17} aria-hidden />
              카드 공유
            </button>
          </div>
          {exportStatus && <p className="break-keep text-sm font-bold leading-6 text-stone-600 dark:text-stone-300">{exportStatus}</p>}
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-border bg-background/70 p-4 shadow-ritual sm:p-5 dark:bg-[#242321] dark:shadow-ritual-dark">
        <SectionHeading index="05" icon={MapPinned} label="비밀의 문" title={reading.secret_door.unexplored_area} description="이번 리포트에서 깊게 다루지 않은 다음 흐름입니다." />
        <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
          <p className="inline-flex max-w-full items-center gap-2 rounded-lg bg-surface-muted px-3 py-1.5 text-xs font-black text-sage dark:text-[#c9d4bd]">
            <CalendarClock size={14} aria-hidden />
            <span className="min-w-0 break-keep">{reading.secret_door.next_month_signal}</span>
          </p>
          <p className="mt-4 break-keep font-serif text-xl font-black leading-8 text-foreground">{reading.secret_door.teaser}</p>
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-border bg-surface p-4 shadow-ritual dark:shadow-ritual-dark">
        <div className="flex min-w-0 items-start gap-3 rounded-lg border border-terracotta/30 bg-terracotta/10 p-4">
          <CircleAlert className="mt-0.5 shrink-0 text-terracotta" size={18} aria-hidden />
          <p className="min-w-0 break-keep text-sm font-bold leading-6 text-stone-700 dark:text-stone-300">{reading.caution}</p>
        </div>
        <p className="mt-4 break-keep text-xs font-bold leading-5 text-stone-500 dark:text-stone-400">
          이 결과는 {trimmedName}님의 입력 정보와 답변을 바탕으로 생성된 참고용 리딩입니다. {dayMasterProfile?.plain}
        </p>
      </section>

      <footer className="flex min-w-0 flex-col gap-2 text-xs font-bold text-stone-500 dark:text-stone-400 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-2">
          <BadgeCheck size={14} aria-hidden />
          <span className="min-w-0 break-keep">명식 계산과 최종 리딩 생성 완료</span>
        </div>
        <div className="flex min-w-0 items-center gap-2">
          <CalendarClock size={14} aria-hidden />
          <span className="min-w-0 break-all">
            {meta.provider} · {meta.model}
          </span>
        </div>
      </footer>
    </article>
  );
}
