"use client";

import { toPng } from "html-to-image";
import { useRef, useState, type RefObject } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  BookOpen,
  CalendarClock,
  CircleAlert,
  ClipboardCheck,
  Copy,
  Download,
  Gem,
  RefreshCcw,
  Share2,
  ShieldCheck,
  Sparkles,
  Star,
  type LucideIcon,
} from "lucide-react";

import { SajuPillarsTable } from "@/components/SajuPillarsTable";
import type { DaewoonPeriod, FinalReadingResponse, PeriodGuidanceItem, ReadingStyle } from "@/lib/api";

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
  wood: "#5A6B5D",
  fire: "#C57B57",
  earth: "#B79B5A",
  metal: "#8A8178",
  water: "#5B7187",
};

const elementProfiles: Record<ElementKey, { term: string; plain: string; daily: string }> = {
  wood: {
    term: "목(木)",
    plain: "성장, 기획, 배움, 관계를 넓히는 힘",
    daily: "작게 시작해 꾸준히 키우는 루틴으로 살아납니다.",
  },
  fire: {
    term: "화(火)",
    plain: "표현, 열정, 주목도, 감정의 온도를 올리는 힘",
    daily: "생각을 밖으로 말하고 보여주는 행동으로 살아납니다.",
  },
  earth: {
    term: "토(土)",
    plain: "현실감, 안정, 책임, 계획을 뿌리내리는 힘",
    daily: "정리, 일정표, 예산처럼 생활의 바닥을 단단히 만들 때 살아납니다.",
  },
  metal: {
    term: "금(金)",
    plain: "판단, 기준, 정리, 결단과 완성도를 세우는 힘",
    daily: "우선순위를 줄이고 기준을 문장으로 꺼낼 때 살아납니다.",
  },
  water: {
    term: "수(水)",
    plain: "정보, 사고, 유연성, 흐름을 읽고 바꾸는 힘",
    daily: "충분히 살피되 결론을 적어 실행으로 옮길 때 살아납니다.",
  },
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

const animalProfiles: Record<string, { title: string; animal: string; line: string; reason: string }> = {
  甲: { title: "개척형 호랑이", animal: "호랑이", line: "새 길을 여는 기운을 가진 호랑이", reason: "갑목은 큰 나무처럼 방향을 세우고 밀고 나가는 힘이라, 먼저 길을 터는 호랑이로 비유합니다." },
  乙: { title: "적응형 사슴", animal: "사슴", line: "유연하게 길을 찾는 기운을 가진 사슴", reason: "을목은 풀과 덩굴처럼 환경을 읽고 적응하는 힘이라, 민감하게 길을 고르는 사슴으로 비유합니다." },
  丙: { title: "확산형 사자", animal: "사자", line: "밝게 드러내고 확산하는 기운을 가진 사자", reason: "병화는 태양처럼 존재감을 드러내고 분위기를 밝히는 힘이라, 무대 위에서 힘이 커지는 사자로 비유합니다." },
  丁: { title: "집중형 여우", animal: "여우", line: "필요한 곳에 집중하는 기운을 가진 여우", reason: "정화는 촛불처럼 한 지점을 오래 밝히는 힘이라, 섬세하게 판단하고 집중하는 여우로 비유합니다." },
  戊: { title: "중심형 코끼리", animal: "코끼리", line: "흔들리는 판의 중심을 잡는 기운을 가진 코끼리", reason: "무토는 산처럼 큰 중심을 잡는 힘이라, 주변을 안정시키며 버티는 코끼리로 비유합니다." },
  己: { title: "양육형 토끼", animal: "토끼", line: "현실을 돌보고 길러내는 기운을 가진 토끼", reason: "기토는 밭처럼 현실을 다지고 키우는 힘이라, 작은 변화를 살피며 돌보는 토끼로 비유합니다." },
  庚: { title: "결단형 늑대", animal: "늑대", line: "기준을 세워 결단하는 기운을 가진 늑대", reason: "경금은 큰 쇠처럼 기준을 세우고 잘라내는 힘이라, 무리 속에서도 결정을 내리는 늑대로 비유합니다." },
  辛: { title: "정교형 백조", animal: "백조", line: "섬세하게 완성도를 높이는 기운을 가진 백조", reason: "신금은 보석처럼 세부를 다듬고 품질을 높이는 힘이라, 정교한 균형감이 있는 백조로 비유합니다." },
  壬: { title: "흐름형 고래", animal: "고래", line: "큰 흐름을 읽고 연결하는 기운을 가진 고래", reason: "임수는 큰 물처럼 넓게 흐름을 보고 연결하는 힘이라, 깊고 넓게 움직이는 고래로 비유합니다." },
  癸: { title: "통찰형 올빼미", animal: "올빼미", line: "조용히 살피고 깊이 꿰뚫는 기운을 가진 올빼미", reason: "계수는 비와 이슬처럼 조용히 스며들어 이해하는 힘이라, 보이지 않는 맥락을 읽는 올빼미로 비유합니다." },
};

const tenGodProfiles: Record<string, { term: string; plain: string }> = {
  비견: { term: "비견(比肩)", plain: "나와 같은 기운입니다. 자기 기준, 독립성, 주체성을 뜻합니다." },
  겁재: { term: "겁재(劫財)", plain: "사람 속에서 판을 키우는 기운입니다. 경쟁심, 확장력, 관계의 경계를 뜻합니다." },
  식신: { term: "식신(食神)", plain: "내 능력을 안정적으로 꺼내는 기운입니다. 꾸준함, 생산성, 결과물을 뜻합니다." },
  상관: { term: "상관(傷官)", plain: "기존 틀을 바꾸는 표현의 기운입니다. 개성, 변화, 말과 감각을 뜻합니다." },
  편재: { term: "편재(偏財)", plain: "기회를 빠르게 보는 현실 감각입니다. 활동성, 영업력, 움직이는 재물을 뜻합니다." },
  정재: { term: "정재(正財)", plain: "계획적으로 쌓고 관리하는 기운입니다. 안정성, 성실함, 재정 관리를 뜻합니다." },
  편관: { term: "편관(偏官)", plain: "압박을 견디며 돌파하는 기운입니다. 책임, 긴장, 승부수를 뜻합니다." },
  정관: { term: "정관(正官)", plain: "질서와 신뢰를 세우는 기운입니다. 규칙, 책임, 절제력을 뜻합니다." },
  편인: { term: "편인(偏印)", plain: "남들이 놓치는 맥락을 읽는 기운입니다. 직감, 탐구, 독특한 관점을 뜻합니다." },
  정인: { term: "정인(正印)", plain: "배우고 흡수하는 보호의 기운입니다. 학습, 문서, 안정적인 도움을 뜻합니다." },
};

const elementTextPatterns: Record<ElementKey, string[]> = {
  wood: ["목(木)", "목의 기운", "목 기운", "나무의 기운"],
  fire: ["화(火)", "화의 기운", "화 기운", "불의 기운"],
  earth: ["토(土)", "토의 기운", "토 기운", "흙의 기운"],
  metal: ["금(金)", "금의 기운", "금 기운", "쇠의 기운"],
  water: ["수(水)", "수의 기운", "수 기운", "물의 기운"],
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

function isElementKey(key: string): key is ElementKey {
  return elementOrder.includes(key as ElementKey);
}

function primaryElementColor(key: string) {
  return elementColors[key as ElementKey] ?? "#5A6B5D";
}

function getAnimalProfile(dayMaster: string) {
  return (
    animalProfiles[dayMaster] ?? {
      title: "균형형 동물",
      animal: "동물",
      line: "명식의 흐름을 자기 방식으로 쓰는 기운을 가진 동물",
      reason: "일간은 사주에서 나를 대표하는 기준이므로, 핵심 성향을 가장 직관적인 동물 비유로 압축해 보여줍니다.",
    }
  );
}

function shareCardStrengths(card: FinalReadingResponse["reading"]["share_card"]) {
  const strengths = Array.isArray(card.strengths) ? card.strengths.filter(Boolean).slice(0, 3) : [];
  return strengths.length > 0 ? strengths : ["기준 세우기", "현실 감각"];
}

function findElementInText(text: string): ElementKey | null {
  const normalizedText = text.replace(/\s+/g, " ");
  return elementOrder.find((key) => elementTextPatterns[key].some((pattern) => normalizedText.includes(pattern))) ?? null;
}

function findTenGodInText(text: string) {
  return Object.keys(tenGodProfiles).find((tenGod) => text.includes(tenGod)) ?? null;
}

function getPrimaryTenGod(result: FinalReadingResponse) {
  const counts = new Map<string, number>();

  Object.values(result.saju.ten_gods).forEach((tenGod) => {
    if (!tenGod || tenGod === "일간") return;
    counts.set(tenGod, (counts.get(tenGod) ?? 0) + 1);
  });

  return Array.from(counts.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
}

function getShareCardDensity(card: FinalReadingResponse["reading"]["share_card"]) {
  const totalLength = card.core_saju_feature.length + card.balancing_need.length + card.daily_element.length + shareCardStrengths(card).join("").length;

  if (totalLength > 230) return "tight";
  if (totalLength > 175) return "compact";
  return "normal";
}

function getEasyTermSummary(text: string, result: FinalReadingResponse) {
  const dayElement = isElementKey(result.saju.day_master_element) ? result.saju.day_master_element : "earth";
  const foundElement = findElementInText(text) ?? dayElement;
  const foundTenGod = findTenGodInText(text) ?? getPrimaryTenGod(result);
  const descriptions = [
    `일간 ${result.saju.day_master}은 사주에서 나 자신을 보는 기준입니다.`,
    `${elementProfiles[foundElement].term}은 ${elementProfiles[foundElement].plain}입니다.`,
  ];

  if (foundTenGod && tenGodProfiles[foundTenGod]) {
    descriptions.push(`${tenGodProfiles[foundTenGod].term}은 ${tenGodProfiles[foundTenGod].plain.replace("입니다.", "으로 봅니다.")}`);
  }

  return descriptions.join(" ");
}

function downloadDataUrl(dataUrl: string, fileName: string) {
  const link = document.createElement("a");
  link.download = fileName;
  link.href = dataUrl;
  link.click();
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

function CoverGlyph({ element }: { element: string }) {
  const color = primaryElementColor(element);

  return (
    <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-[38%] overflow-hidden lg:block" aria-hidden>
      <div className="absolute right-5 top-14 h-48 w-48 rounded-full border opacity-30 motion-safe:animate-pulse" style={{ borderColor: color }} />
      <div className="absolute right-20 top-24 h-32 w-32 rounded-full" style={{ backgroundColor: `${color}18` }} />
      <div className="absolute bottom-14 right-8 grid gap-3">
        {[0, 1, 2].map((line) => (
          <span key={line} className="block h-px w-44" style={{ backgroundColor: color, opacity: 0.34 - line * 0.06 }} />
        ))}
      </div>
    </div>
  );
}

function ElementBars({ result }: { result: FinalReadingResponse }) {
  const counts = result.saju.elements_count;
  const maxCount = Math.max(1, ...elementOrder.map((key) => counts[key] ?? 0));

  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <div className="mb-4 flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h4 className="text-sm font-black text-foreground">현재 기운 분포</h4>
          <p className="mt-1 break-keep text-xs font-bold leading-5 text-stone-500 dark:text-stone-400">강한 기운과 비어 있는 기운을 함께 봅니다.</p>
        </div>
        <div className="w-fit rounded-lg bg-surface-muted px-3 py-2 text-xs font-black text-stone-600 dark:text-stone-300">
          일간 {result.saju.day_master} · {elementName(result.saju.day_master_element)}
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

function DaewoonTimeline({ periods }: { periods: DaewoonPeriod[] }) {
  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <h4 className="mb-3 text-sm font-black text-foreground">대운 키워드</h4>
      <div className="grid min-w-0 gap-2 sm:grid-cols-3">
        {periods.slice(0, 3).map((period) => (
          <div key={`${period.order}-${period.pillar}`} className="min-w-0 rounded-lg bg-surface-muted px-3 py-3">
            <div className="flex min-w-0 items-center justify-between gap-3">
              <span className="font-serif text-lg font-black text-foreground">{period.pillar}</span>
              <span className="shrink-0 text-xs font-black text-stone-500 dark:text-stone-400">
                {period.age_start}-{period.age_end}세
              </span>
            </div>
            <p className="mt-1 break-keep text-xs font-bold leading-5 text-stone-600 dark:text-stone-300">
              {period.start_year}년 시작 · {period.stem_ten_god} · {elementName(period.main_element)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function EvidenceList({ items }: { items: string[] }) {
  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <h4 className="mb-3 text-sm font-black text-foreground">명리학적 근거</h4>
      <ul className="space-y-2 text-sm font-bold leading-6 text-stone-700 dark:text-stone-300">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className="flex min-w-0 gap-2 rounded-lg bg-surface-muted px-3 py-2">
            <span className="shrink-0 text-sage dark:text-[#c9d4bd]">{index + 1}</span>
            <span className="min-w-0 break-keep">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function PeriodGuidanceCard({ item }: { item: PeriodGuidanceItem }) {
  return (
    <article className="min-w-0 rounded-lg border border-border bg-background/70 p-4 dark:bg-[#242321]">
      <p className="text-xs font-black text-sage dark:text-[#c9d4bd]">{item.label}</p>
      <p className="mt-2 break-keep text-sm font-black leading-6 text-foreground">{item.saju_feature}</p>
      <div className="mt-4 grid min-w-0 gap-3 sm:grid-cols-2">
        <div className="min-w-0 rounded-lg bg-surface p-3">
          <p className="text-xs font-black text-sage dark:text-[#c9d4bd]">좋은 흐름</p>
          <p className="mt-2 break-keep text-sm font-semibold leading-6 text-stone-700 dark:text-stone-300">{item.good}</p>
        </div>
        <div className="min-w-0 rounded-lg bg-surface p-3">
          <p className="text-xs font-black text-terracotta dark:text-[#d58c6d]">조심할 점</p>
          <p className="mt-2 break-keep text-sm font-semibold leading-6 text-stone-700 dark:text-stone-300">{item.caution}</p>
        </div>
      </div>
    </article>
  );
}

function SummaryCard({ refNode, name, result }: { refNode: RefObject<HTMLDivElement | null>; name: string; result: FinalReadingResponse }) {
  const card = result.reading.share_card;
  const animalProfile = getAnimalProfile(result.saju.day_master);
  const strengths = shareCardStrengths(card);
  const density = getShareCardDensity(card);
  const titleClass = density === "tight" ? "text-[1.7rem] leading-8" : density === "compact" ? "text-3xl leading-9" : "text-[2rem] leading-10";
  const bodyClass = density === "tight" ? "text-[0.8rem] leading-5" : "text-sm leading-6";

  return (
    <div
      ref={refNode}
      className="mx-auto min-h-[34.75rem] w-full max-w-[22rem] overflow-hidden rounded-lg border border-[#d8d0c2] bg-[#F7F6F3] p-4 text-[#24211f] shadow-ritual sm:min-h-[39.125rem] sm:p-5"
    >
      <div className="flex min-h-[32.75rem] min-w-0 flex-col justify-between gap-3 sm:min-h-[36.625rem] sm:gap-4">
        <div className="min-w-0">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-black uppercase text-[#5A6B5D]">Saju-i · 실용 부적</p>
            <p className="rounded-lg bg-white/75 px-3 py-1 text-xs font-black text-[#5A6B5D]">{result.saju.day_master}</p>
          </div>
          <p className="mt-4 text-xs font-black text-[#8a8178] sm:mt-6">{name}님의 사주 동물</p>
          <h4 className={`mt-2 break-keep font-serif font-black tracking-normal text-[#24211f] [overflow-wrap:anywhere] ${titleClass}`}>{animalProfile.title}</h4>
          <p className="mt-3 break-keep text-sm font-black leading-6 text-[#5A6B5D] [overflow-wrap:anywhere]">{animalProfile.line}</p>
          <p className={`mt-3 break-keep font-bold text-[#5f5a52] [overflow-wrap:anywhere] sm:mt-4 ${bodyClass}`}>{card.core_saju_feature}</p>
        </div>

        <div className="min-w-0 space-y-3">
          <div className="rounded-lg border border-[#d8d0c2] bg-white/75 p-3 sm:p-4">
            <p className="text-xs font-black text-[#8a8178]">고민 해결 부적</p>
            <p className="mt-2 break-keep font-serif text-lg font-black leading-7 [overflow-wrap:anywhere]">{card.daily_element}</p>
          </div>

          <div className="rounded-lg border border-[#d8d0c2] bg-white/75 p-3">
            <p className="text-xs font-black text-[#8a8178]">강점</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {strengths.map((strength) => (
                <span key={strength} className="min-w-0 rounded-lg bg-[#eef1e9] px-2.5 py-1 text-xs font-black leading-5 text-[#5A6B5D] [overflow-wrap:anywhere]">
                  {strength}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-[#d8d0c2] bg-white/75 p-3">
            <p className="text-xs font-black text-[#8a8178]">보완할 기운</p>
            <p className={`mt-2 break-keep font-black text-[#24211f] [overflow-wrap:anywhere] ${bodyClass}`}>{card.balancing_need}</p>
          </div>

          <div className="border-t border-[#d8d0c2] pt-3">
            <p className="break-keep text-xs font-black leading-5 text-[#5A6B5D] [overflow-wrap:anywhere]">오늘은 강점을 쓰고, 부족한 기운은 작은 아이템으로 보완하세요.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ShareCardExplanation({ result }: { result: FinalReadingResponse }) {
  const { reading, saju } = result;
  const card = reading.share_card;
  const strengths = shareCardStrengths(card);
  const animalProfile = getAnimalProfile(saju.day_master);
  const cardText = [card.core_saju_feature, card.balancing_need, card.daily_element, card.daily_reason, strengths.join(" ")].join(" ");
  const dayElement = isElementKey(saju.day_master_element) ? saju.day_master_element : "earth";
  const focusElement = findElementInText(cardText) ?? dayElement;
  const dayMasterProfile = stemProfiles[saju.day_master];
  const tenGod = findTenGodInText(cardText) ?? getPrimaryTenGod(result);
  const tenGodProfile = tenGod ? tenGodProfiles[tenGod] : null;
  const strengthSentence = strengths.join(", ");

  const explanationItems = [
    {
      label: "왜 이 동물인가 · 일간(日干)",
      title: animalProfile.title,
      body: `${animalProfile.reason} 일간은 사주에서 나를 대표하는 기준 글자라서, ${dayMasterProfile?.term ?? `${saju.day_master} 일간`}의 성향을 먼저 동물 비유로 압축했습니다.`,
    },
    {
      label: "왜 이 부적인가 · 오행(五行)",
      title: `고민 해결 부적: ${card.daily_element}`,
      body: `${elementProfiles[focusElement].term}은 ${elementProfiles[focusElement].plain}입니다. ${card.daily_reason} 쉽게 말하면 ${elementProfiles[focusElement].daily}`,
    },
    {
      label: "십성(十星)으로 보면",
      title: tenGodProfile ? `${tenGodProfile.term}의 활용` : "강점 키워드",
      body: tenGodProfile
        ? `${tenGodProfile.plain} 이 카드에서는 그 힘을 ${strengthSentence}로 정리해 고민 해결에 바로 쓰게 했습니다.`
        : `십성은 일간을 기준으로 다른 글자가 어떤 역할을 하는지 보는 용어입니다. 이 카드에서는 지금 쓸 수 있는 힘을 ${strengthSentence}로 정리했습니다.`,
    },
  ];

  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface p-4 sm:p-5">
      <div className="mb-4 flex min-w-0 items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-sage text-white">
          <BookOpen size={18} aria-hidden />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-black text-sage dark:text-[#c9d4bd]">카드 풀이</p>
          <h4 className="mt-1 break-keep text-xl font-black leading-tight text-foreground">짧은 문장을 사주 용어로 풀어보면</h4>
        </div>
      </div>

      <div className="grid min-w-0 gap-3">
        <div className="min-w-0 rounded-lg border border-border bg-background/70 p-4 dark:bg-[#242321]">
          <p className="text-xs font-black text-sage dark:text-[#c9d4bd]">카드 핵심</p>
          <p className="mt-2 break-keep text-base font-black leading-7 text-foreground [overflow-wrap:anywhere]">{animalProfile.line}</p>
          <p className="mt-2 break-keep text-sm font-semibold leading-6 text-stone-600 [overflow-wrap:anywhere] dark:text-stone-300">{card.core_saju_feature}</p>
        </div>

        <div className="grid min-w-0 gap-3">
          {explanationItems.map((item) => (
            <article key={item.label} className="min-w-0 rounded-lg border border-border bg-background/70 p-4 dark:bg-[#242321]">
              <p className="text-xs font-black text-stone-500 dark:text-stone-400">{item.label}</p>
              <h5 className="mt-2 break-keep text-base font-black leading-7 text-foreground [overflow-wrap:anywhere]">{item.title}</h5>
              <p className="mt-2 break-keep text-sm font-semibold leading-6 text-stone-600 [overflow-wrap:anywhere] dark:text-stone-300">{item.body}</p>
            </article>
          ))}
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
  const animalProfile = getAnimalProfile(saju.day_master);
  const shareStrengths = shareCardStrengths(reading.share_card);

  async function copyShareText() {
    const shareText = [
      reading.reading_title,
      reading.desired_answer,
      reading.core_message,
      `사주 동물: ${animalProfile.title} - ${animalProfile.line}`,
      `핵심 사주 특징: ${reading.share_card.core_saju_feature}`,
      `고민 해결 부적: ${reading.share_card.daily_element}`,
      `강점: ${shareStrengths.join(", ")}`,
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
        backgroundColor: "#F7F6F3",
      });

      if (share) {
        const blob = await (await fetch(dataUrl)).blob();
        const file = new File([blob], "saju-summary-card.png", { type: "image/png" });
        if (typeof navigator.share === "function" && (!navigator.canShare || navigator.canShare({ files: [file] }))) {
          await navigator.share({
            files: [file],
            title: reading.reading_title,
            text: reading.core_message,
          });
          setExportStatus("공유 창을 열었습니다.");
          return;
        }
      }

      downloadDataUrl(dataUrl, "saju-summary-card.png");
      setExportStatus(share ? "이 브라우저에서는 공유 대신 PNG로 저장했습니다." : "PNG 저장을 시작했습니다.");
    } catch (error) {
      setExportStatus(error instanceof Error ? error.message : "요약 카드 생성에 실패했습니다.");
    }
  }

  return (
    <article className="w-full max-w-full space-y-4 overflow-hidden">
      <section className="relative overflow-hidden rounded-lg border border-border bg-surface p-4 shadow-ritual sm:p-6 lg:p-7 dark:shadow-ritual-dark">
        <CoverGlyph element={saju.day_master_element} />
        <div className="relative z-10 min-w-0">
          <div className="mb-6 flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="inline-flex max-w-full items-center gap-2 rounded-lg bg-surface-muted px-3 py-1.5 text-xs font-black text-sage dark:text-[#c9d4bd]">
                <Sparkles size={14} aria-hidden /> <span className="min-w-0 break-keep">{personaLabels[readingStyle]}</span>
              </p>
              <p className="mt-3 break-keep text-sm font-bold leading-6 text-stone-500 dark:text-stone-400">
                {saju.solar_date} · {saju.birth_time} · 일간 {saju.day_master}({elementName(saju.day_master_element)})
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

          <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(240px,0.45fr)]">
            <div className="min-w-0 max-w-3xl">
              <p className="mb-3 inline-flex rounded-lg bg-terracotta/10 px-3 py-1.5 text-xs font-black text-terracotta dark:text-[#d58c6d]">핵심 결론</p>
              <h2 className="break-keep font-serif text-3xl font-black leading-tight text-foreground sm:text-4xl">{reading.reading_title}</h2>
              <p className="mt-5 break-keep font-serif text-xl font-black leading-8 text-foreground sm:text-2xl">{reading.desired_answer}</p>
              <p className="mt-4 break-keep text-lg font-black leading-8 text-sage dark:text-[#c9d4bd]">{reading.core_message}</p>
              <p className="mt-5 break-keep rounded-lg bg-surface-muted px-4 py-3 text-sm font-bold leading-6 text-stone-600 dark:text-stone-300">
                상담 주제: {concernText}
              </p>
            </div>

            <div className="min-w-0 rounded-lg border border-border bg-background/70 p-4 dark:bg-[#242321]">
              <p className="text-xs font-black text-sage dark:text-[#c9d4bd]">근거 요약</p>
              <ul className="mt-3 space-y-2 text-sm font-bold leading-6 text-stone-700 dark:text-stone-300">
                {reading.saju_basis.slice(0, 3).map((item, index) => (
                  <li key={`${item}-${index}`} className="flex min-w-0 gap-2">
                    <span className="shrink-0 text-sage dark:text-[#c9d4bd]">{index + 1}</span>
                    <span className="min-w-0 break-keep">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-border bg-surface p-4 shadow-ritual sm:p-5 dark:shadow-ritual-dark">
        <SectionHeading index="01" icon={Star} label="사주 근거" title={reading.saju_insight.headline} description="고민이 생긴 이유를 실제 명식 흐름으로 풀이합니다." />
        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
          <div className="min-w-0">
            <p className="whitespace-pre-line break-keep text-base font-bold leading-8 text-stone-700 dark:text-stone-300">{reading.saju_insight.summary}</p>
            <p className="mt-4 whitespace-pre-line break-keep text-base font-semibold leading-8 text-stone-600 dark:text-stone-300">{reading.saju_insight.detail}</p>
          </div>
          <div className="grid min-w-0 gap-4">
            <ElementBars result={result} />
            <DaewoonTimeline periods={saju.daewoon} />
          </div>
        </div>
        <div className="mt-4 grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <EvidenceList items={reading.saju_basis} />
          <div className="min-w-0">
            <SajuPillarsTable saju={saju} />
          </div>
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-border bg-background/70 p-4 shadow-ritual sm:p-5 dark:bg-[#242321] dark:shadow-ritual-dark">
        <SectionHeading index="02" icon={ClipboardCheck} label="최종 해답" title={reading.clear_solution.headline} description="결론이 행동으로 이어지도록 기준을 정리합니다." />
        <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
          <p className="whitespace-pre-line break-keep text-base font-bold leading-8 text-stone-700 dark:text-stone-300">{reading.clear_solution.summary}</p>
          <p className="mt-4 whitespace-pre-line break-keep text-base font-semibold leading-8 text-stone-600 dark:text-stone-300">{reading.clear_solution.detail}</p>
        </div>

        <div className="mt-4 min-w-0">
          <h4 className="mb-3 text-sm font-black text-foreground">시기별 흐름</h4>
          <div className="grid min-w-0 gap-3">
            {reading.period_guidance.map((item) => (
              <PeriodGuidanceCard key={item.label} item={item} />
            ))}
          </div>
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-border bg-surface p-4 shadow-ritual sm:p-5 dark:shadow-ritual-dark">
        <SectionHeading index="03" icon={ShieldCheck} label="쓸 수 있는 강점" title={reading.secret_talent.headline} description="고민을 해결할 때 써야 할 타고난 힘을 짚습니다." />
        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="min-w-0 rounded-lg border border-border bg-surface-muted p-4">
            <p className="text-xs font-black text-sage dark:text-[#c9d4bd]">{reading.secret_talent.title}</p>
            <p className="mt-3 whitespace-pre-line break-keep text-base font-bold leading-8 text-stone-700 dark:text-stone-300">{reading.secret_talent.summary}</p>
          </div>
          <div className="min-w-0 rounded-lg border border-border bg-background/70 p-4 dark:bg-[#242321]">
            <p className="whitespace-pre-line break-keep text-base font-semibold leading-8 text-stone-600 dark:text-stone-300">{reading.secret_talent.detail}</p>
          </div>
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-border bg-background/70 p-4 shadow-ritual sm:p-5 dark:bg-[#242321] dark:shadow-ritual-dark">
        <SectionHeading index="04" icon={Gem} label="공유용 카드" title="핵심 카드와 쉬운 풀이" description="모바일 저장 비율의 카드 옆에 사주 용어를 풀어 설명합니다." />
        <div className="grid min-w-0 gap-5 md:grid-cols-[minmax(18rem,22rem)_minmax(0,1fr)] md:items-start">
          <SummaryCard refNode={summaryCardRef} name={trimmedName} result={result} />
          <div className="min-w-0 space-y-4">
            <ShareCardExplanation result={result} />

            <div className="flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                onClick={() => exportSummaryCard({ share: false })}
                className="flex h-12 flex-1 items-center justify-center gap-2 rounded-lg bg-sage px-4 text-sm font-black text-white transition hover:bg-[#4c5d50]"
              >
                <Download size={17} aria-hidden />
                PNG 저장
              </button>
              <button
                type="button"
                onClick={() => exportSummaryCard({ share: true })}
                className="flex h-12 flex-1 items-center justify-center gap-2 rounded-lg bg-terracotta px-4 text-sm font-black text-white transition hover:bg-[#b46d4d]"
              >
                <Share2 size={17} aria-hidden />
                공유
              </button>
            </div>
            {exportStatus && <p className="break-keep text-sm font-bold leading-6 text-stone-600 dark:text-stone-300">{exportStatus}</p>}
          </div>
        </div>
      </section>

      <section className="min-w-0 rounded-lg border border-border bg-surface p-4 shadow-ritual dark:shadow-ritual-dark">
        <div className="flex min-w-0 items-start gap-3 rounded-lg border border-terracotta/30 bg-terracotta/10 p-4">
          <CircleAlert className="mt-0.5 shrink-0 text-terracotta" size={18} aria-hidden />
          <p className="min-w-0 break-keep text-sm font-bold leading-6 text-stone-700 dark:text-stone-300">{reading.caution}</p>
        </div>
        <p className="mt-4 break-keep text-xs font-bold leading-5 text-stone-500 dark:text-stone-400">
          이 결과는 {trimmedName}님의 입력 정보와 답변을 바탕으로 생성된 참고용 리딩입니다.
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
