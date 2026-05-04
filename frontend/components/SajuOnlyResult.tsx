"use client";

import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  CalendarClock,
  CircleAlert,
  Compass,
  RefreshCcw,
  Scale,
  Sparkles,
  Star,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

import { SajuPillarsTable } from "@/components/SajuPillarsTable";
import type { DaewoonPeriod, PillarDetail, SajuData } from "@/lib/api";

type ElementKey = "wood" | "fire" | "earth" | "metal" | "water";

const pillarLabels: Record<"year" | "month" | "day" | "hour", string> = {
  year: "연주",
  month: "월주",
  day: "일주",
  hour: "시주",
};

const pillarRoleLabels: Record<"year" | "month" | "day" | "hour", string> = {
  year: "초년·가문·첫인상",
  month: "사회성·직업 환경",
  day: "나 자신·가까운 관계",
  hour: "미래 방향·내면의 계획",
};

const pillarRoleDescriptions: Record<"year" | "month" | "day" | "hour", string> = {
  year: "연주는 바깥에서 처음 보이는 분위기와 어릴 때 익힌 기본 태도를 봅니다.",
  month: "월주는 현실 무대와 일하는 방식, 사회에서 힘을 쓰는 방향을 봅니다.",
  day: "일주는 일간을 중심으로 본인의 핵심 기질과 가까운 관계의 결을 봅니다.",
  hour: "시주는 앞으로 키워갈 재능, 장기 계획, 혼자 있을 때의 생각 흐름을 봅니다.",
};

const elementLabels: Record<ElementKey, string> = {
  wood: "목",
  fire: "화",
  earth: "토",
  metal: "금",
  water: "수",
};

const elementOrder = ["wood", "fire", "earth", "metal", "water"] as const;

const elementToneClass: Record<ElementKey, string> = {
  wood: "bg-[#eaf7f3] text-[#236f62]",
  fire: "bg-[#fff0ed] text-[#a43f30]",
  earth: "bg-[#fff6da] text-[#806118]",
  metal: "bg-[#f1efec] text-[#5d554e]",
  water: "bg-[#edf3fb] text-[#385f90]",
};

const elementBarColor: Record<ElementKey, string> = {
  wood: "#2f9d8c",
  fire: "#dd6654",
  earth: "#f1be4d",
  metal: "#8a8178",
  water: "#4f77a8",
};

const elementMeanings: Record<ElementKey, { role: string; high: string; low: string; care: string }> = {
  wood: {
    role: "성장, 기획, 관계 확장, 배움의 방향성",
    high: "새로운 일을 벌이고 배우는 힘이 잘 살아납니다. 다만 기준 없이 넓히면 마무리가 약해질 수 있습니다.",
    low: "시작 에너지와 장기 성장감이 부족하게 느껴질 수 있습니다. 작은 목표를 정해 꾸준히 키우는 방식이 보완점입니다.",
    care: "기록, 산책, 공부 루틴처럼 천천히 자라는 활동이 좋습니다.",
  },
  fire: {
    role: "표현, 열정, 주목도, 감정의 온도",
    high: "표현력과 추진 온도가 강합니다. 빠르게 드러내는 힘이 장점이지만 쉽게 달아오르면 피로도 함께 옵니다.",
    low: "기쁨과 표현을 밖으로 내보내는 일이 조심스러울 수 있습니다. 발표, 운동, 햇빛 노출이 흐름을 살립니다.",
    care: "짧은 발표, 콘텐츠 정리, 밝은 조명처럼 드러내는 장치를 늘리면 좋습니다.",
  },
  earth: {
    role: "중심, 현실감, 책임, 중재와 축적",
    high: "버티고 책임지는 힘이 강합니다. 안정감은 좋지만, 너무 많이 떠안으면 결정이 느려질 수 있습니다.",
    low: "현실을 붙잡는 중심감이 약해질 수 있습니다. 일정표, 예산표, 생활 루틴이 균형을 잡아줍니다.",
    care: "정리, 식사 리듬, 재정 점검처럼 생활의 바닥을 단단히 만드는 일이 좋습니다.",
  },
  metal: {
    role: "판단, 정리, 기준, 결단과 완성도",
    high: "분별력과 기준이 선명합니다. 완성도를 높이는 힘이 있으나 지나치면 스스로에게 엄격해질 수 있습니다.",
    low: "선 긋기와 결단이 흔들릴 수 있습니다. 우선순위 3개만 남기는 훈련이 도움이 됩니다.",
    care: "체크리스트, 물건 정리, 계약 조건 확인처럼 경계를 세우는 활동이 좋습니다.",
  },
  water: {
    role: "사고, 정보, 유연성, 이동과 회복",
    high: "생각의 폭과 적응력이 좋습니다. 정보 감각은 강하지만 고민이 길어지면 실행이 늦어질 수 있습니다.",
    low: "유연한 사고와 회복감이 마를 수 있습니다. 휴식, 수면, 자료 탐색 시간을 의식적으로 확보하세요.",
    care: "물 마시기, 독서, 이동, 조용한 회복 시간이 흐름을 부드럽게 합니다.",
  },
};

const tenGodOrder = ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"] as const;

const tenGodMeanings: Record<string, { title: string; summary: string; keyword: string }> = {
  비견: {
    title: "자기 기준",
    summary: "내가 납득해야 움직이는 힘입니다. 독립성과 주체성이 살아나지만 고집으로 보이지 않게 조율이 필요합니다.",
    keyword: "자립",
  },
  겁재: {
    title: "경쟁과 추진",
    summary: "사람 속에서 힘을 내고 판을 키우는 기운입니다. 승부감은 장점이고, 돈과 관계의 경계는 관리 포인트입니다.",
    keyword: "확장",
  },
  식신: {
    title: "생산과 꾸준함",
    summary: "내가 가진 것을 안정적으로 표현하고 결과물로 만드는 힘입니다. 일상 루틴과 실력이 쌓일수록 좋아집니다.",
    keyword: "성과",
  },
  상관: {
    title: "표현과 변화",
    summary: "기존 틀을 바꾸고 말과 감각으로 돌파하는 힘입니다. 자유로운 발상은 강점이고, 말의 날카로움은 조심해야 합니다.",
    keyword: "개성",
  },
  편재: {
    title: "활동 재물",
    summary: "기회를 빠르게 보고 움직이는 현실 감각입니다. 사업성, 영업력, 네트워크에 유리하지만 과한 확장은 점검이 필요합니다.",
    keyword: "기회",
  },
  정재: {
    title: "안정 재물",
    summary: "계획적으로 쌓고 관리하는 힘입니다. 신뢰와 성실함이 장점이며, 지나친 안전 확인은 속도를 늦출 수 있습니다.",
    keyword: "관리",
  },
  편관: {
    title: "압박 돌파",
    summary: "어려운 과제를 견디고 돌파하는 힘입니다. 책임 있는 역할에 강하지만 긴장과 부담을 오래 쌓지 않는 것이 중요합니다.",
    keyword: "승부",
  },
  정관: {
    title: "질서와 명예",
    summary: "규칙, 신뢰, 책임을 통해 인정받는 힘입니다. 안정된 조직과 역할에서 강하고, 과한 체면은 내려놓을 필요가 있습니다.",
    keyword: "신뢰",
  },
  편인: {
    title: "직감과 탐구",
    summary: "남들이 놓치는 맥락을 읽는 감각입니다. 연구와 전문성에 좋지만 생각이 안으로만 돌면 고립감이 생길 수 있습니다.",
    keyword: "통찰",
  },
  정인: {
    title: "학습과 보호",
    summary: "배우고 흡수하며 보호받는 흐름입니다. 자격, 공부, 문서운에 유리하고, 지나친 확인 욕구는 줄이는 것이 좋습니다.",
    keyword: "학습",
  },
  일간: {
    title: "나 자신",
    summary: "사주의 중심축입니다. 다른 십성은 이 일간을 기준으로 관계와 역할을 해석합니다.",
    keyword: "중심",
  },
};

const stemProfiles: Record<string, { title: string; summary: string; strength: string; caution: string }> = {
  甲: {
    title: "큰 나무처럼 방향을 세우는 일간",
    summary: "갑목은 위로 곧게 자라는 힘입니다. 목표가 분명할수록 빠르게 성장하고, 원칙과 명분이 있어야 마음이 움직입니다.",
    strength: "장기 계획, 리더십, 새로운 분야를 개척하는 일에 강합니다.",
    caution: "한번 정한 방향을 쉽게 꺾지 않아 주변 속도와 온도 차가 생길 수 있습니다.",
  },
  乙: {
    title: "풀과 덩굴처럼 유연하게 자라는 일간",
    summary: "을목은 부드럽게 파고들어 기회를 만드는 힘입니다. 관계의 결을 읽고 상황에 맞춰 적응하는 감각이 좋습니다.",
    strength: "협업, 기획 보조, 브랜딩, 섬세한 조율에서 장점이 드러납니다.",
    caution: "너무 맞춰주다 보면 자기 기준이 흐려질 수 있어 선 긋기가 필요합니다.",
  },
  丙: {
    title: "태양처럼 드러나고 밝히는 일간",
    summary: "병화는 밖으로 빛을 내는 힘입니다. 분위기를 환하게 만들고, 명확하게 보여주고 설명할 때 강해집니다.",
    strength: "발표, 홍보, 교육, 리더 역할처럼 사람 앞에 서는 일에 유리합니다.",
    caution: "감정과 판단이 빠르게 올라와 쉬는 타이밍을 놓치기 쉽습니다.",
  },
  丁: {
    title: "촛불처럼 집중해서 밝히는 일간",
    summary: "정화는 필요한 곳에 온기와 집중을 주는 힘입니다. 섬세한 감각과 몰입도가 좋아 작은 차이를 크게 만듭니다.",
    strength: "디자인, 상담, 콘텐츠, 분석처럼 감도와 집중력이 필요한 일에 강합니다.",
    caution: "주변 분위기에 예민하게 반응해 혼자 소진될 수 있습니다.",
  },
  戊: {
    title: "산처럼 중심을 잡는 일간",
    summary: "무토는 쉽게 흔들리지 않는 중심의 힘입니다. 큰 그림을 보고 사람과 일을 묶어 안정시키는 역할을 합니다.",
    strength: "관리, 운영, 조직의 중심 역할, 장기 프로젝트에 강합니다.",
    caution: "변화가 필요한 순간에도 익숙한 방식을 오래 붙잡을 수 있습니다.",
  },
  己: {
    title: "밭처럼 길러내고 축적하는 일간",
    summary: "기토는 현실을 다지고 쓸모 있게 만드는 힘입니다. 사람과 자원을 살피며 차근차근 결과를 키워갑니다.",
    strength: "교육, 케어, 실무 관리, 재정 정리처럼 축적형 업무에 강합니다.",
    caution: "걱정이 많아지면 결정보다 보완에 시간을 오래 쓸 수 있습니다.",
  },
  庚: {
    title: "큰 쇠처럼 결단하고 다듬는 일간",
    summary: "경금은 불필요한 것을 잘라내고 핵심을 남기는 힘입니다. 기준이 명확하고 어려운 상황에서 결단력이 살아납니다.",
    strength: "전략, 문제 해결, 기술, 규정 정비처럼 구조를 세우는 일에 강합니다.",
    caution: "표현이 직선적으로 나가면 가까운 관계에서 차갑게 느껴질 수 있습니다.",
  },
  辛: {
    title: "보석처럼 섬세하게 완성도를 높이는 일간",
    summary: "신금은 정확도와 품질을 중시하는 힘입니다. 작은 차이를 알아보고 결과물의 완성도를 끌어올립니다.",
    strength: "브랜드, 품질관리, 미감, 문서와 데이터 검토에 장점이 있습니다.",
    caution: "기준이 높아 스스로를 쉽게 부족하다고 느낄 수 있습니다.",
  },
  壬: {
    title: "큰 물처럼 흐름을 읽고 확장하는 일간",
    summary: "임수는 넓게 보고 빠르게 연결하는 힘입니다. 정보, 사람, 장소가 바뀔수록 시야가 열립니다.",
    strength: "전략 기획, 유통, 연구, 해외·이동성이 있는 일에 강합니다.",
    caution: "생각의 폭이 넓어 결론을 미루거나 방향이 자주 바뀔 수 있습니다.",
  },
  癸: {
    title: "비와 이슬처럼 깊이 스며드는 일간",
    summary: "계수는 조용히 관찰하고 핵심을 흡수하는 힘입니다. 섬세한 정보와 감정을 잘 읽고, 깊게 이해한 뒤 움직입니다.",
    strength: "리서치, 글쓰기, 상담, 데이터 분석처럼 세밀한 이해가 필요한 일에 강합니다.",
    caution: "불확실성을 오래 곱씹으면 걱정이 커져 실행이 늦어질 수 있습니다.",
  },
};

interface SajuOnlyResultProps {
  saju: SajuData;
  onBack: () => void;
  onRestart: () => void;
}

function elementLabel(key: string) {
  return elementLabels[key as ElementKey] ?? key;
}

function yinYangLabel(value: PillarDetail["stem_yin_yang"]) {
  return value === "yang" ? "양" : "음";
}

function getElementCount(saju: SajuData, key: ElementKey) {
  return saju.elements_count[key] ?? 0;
}

function getElementLevel(count: number) {
  if (count === 0) return { label: "비어 있음", className: "border-stone-200 bg-white text-stone-500" };
  if (count === 1) return { label: "약함", className: "border-[#f0dfc4] bg-[#fff8e8] text-[#8a6115]" };
  if (count <= 3) return { label: "균형", className: "border-[#cce8e2] bg-[#f4fbf8] text-mint" };
  return { label: "강함", className: "border-[#f0d5dc] bg-[#fff7f8] text-berry" };
}

function countTenGods(saju: SajuData) {
  const counts = new Map<string, number>();

  Object.values(saju.ten_gods).forEach((god) => {
    if (!god || god === "일간") return;
    counts.set(god, (counts.get(god) ?? 0) + 1);
  });

  return Array.from(counts.entries()).sort((a, b) => {
    if (b[1] !== a[1]) return b[1] - a[1];
    return tenGodOrder.indexOf(a[0] as (typeof tenGodOrder)[number]) - tenGodOrder.indexOf(b[0] as (typeof tenGodOrder)[number]);
  });
}

function joinLabels(labels: string[]) {
  if (labels.length === 0) return "없음";
  return labels.join(", ");
}

function SectionHeading({ icon: Icon, eyebrow, title, description }: { icon: LucideIcon; eyebrow: string; title: string; description?: string }) {
  return (
    <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="inline-flex items-center gap-2 text-xs font-black text-mint">
          <Icon size={15} strokeWidth={2.5} aria-hidden />
          {eyebrow}
        </p>
        <h3 className="mt-2 break-keep text-xl font-black leading-8 text-ink">{title}</h3>
      </div>
      {description && <p className="max-w-md break-keep text-sm font-bold leading-6 text-stone-500">{description}</p>}
    </div>
  );
}

function InsightCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-[0_10px_30px_rgba(83,64,42,0.05)]">
      <p className="text-xs font-black text-stone-500">{title}</p>
      <p className="mt-2 break-keep text-base font-black leading-7 text-ink">{body}</p>
    </div>
  );
}

function ElementBalance({ saju }: { saju: SajuData }) {
  const maxCount = Math.max(1, ...elementOrder.map((key) => getElementCount(saju, key)));

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
      <SectionHeading
        icon={BarChart3}
        eyebrow="오행 균형"
        title="많은 기운은 자연스럽게 쓰이고, 약한 기운은 의식적으로 보완합니다."
        description="천간 4개와 지지 4개의 주 오행을 합산한 분포입니다."
      />

      <div className="grid gap-3">
        {elementOrder.map((key) => {
          const count = getElementCount(saju, key);
          const level = getElementLevel(count);
          const meaning = elementMeanings[key];
          const width = count === 0 ? 0 : Math.max(8, (count / maxCount) * 100);
          const interpretation = count >= 4 ? meaning.high : count <= 1 ? meaning.low : `${meaning.role}이 과하거나 비지 않고 비교적 자연스럽게 쓰입니다.`;

          return (
            <div key={key} className="rounded-lg border border-stone-200 bg-[#fbfcf8] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex h-8 min-w-8 items-center justify-center rounded-lg px-2 text-sm font-black ${elementToneClass[key]}`}>
                    {elementLabels[key]}
                  </span>
                  <div>
                    <p className="text-sm font-black text-ink">{meaning.role}</p>
                    <p className="text-xs font-bold text-stone-500">{count}개</p>
                  </div>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-black ${level.className}`}>{level.label}</span>
              </div>
              <div className="mt-3 h-3 overflow-hidden rounded-full bg-stone-100">
                <div className="h-full rounded-full" style={{ width: `${width}%`, backgroundColor: elementBarColor[key] }} aria-hidden />
              </div>
              <p className="mt-3 break-keep text-sm font-semibold leading-6 text-stone-700">{interpretation}</p>
              <p className="mt-2 break-keep text-xs font-bold leading-5 text-stone-500">보완법: {meaning.care}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function TenGodSummary({ saju }: { saju: SajuData }) {
  const tenGodCounts = countTenGods(saju);

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
      <SectionHeading
        icon={Scale}
        eyebrow="십성 해석"
        title="십성은 일간이 세상과 관계 맺는 방식을 보여줍니다."
        description="천간과 지지에 반복해서 나타나는 십성을 우선해서 봅니다."
      />

      {tenGodCounts.length > 0 ? (
        <div className="grid gap-3 md:grid-cols-2">
          {tenGodCounts.map(([god, count]) => {
            const meaning = tenGodMeanings[god];
            return (
              <div key={god} className="rounded-lg border border-stone-200 bg-[#fbfcf8] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-black text-ink">{god}</p>
                    <p className="mt-1 text-xs font-black text-mint">{meaning?.title ?? "관계 방식"}</p>
                  </div>
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-black text-stone-600 shadow-sm">{count}회</span>
                </div>
                <p className="mt-3 break-keep text-sm font-semibold leading-6 text-stone-700">
                  {meaning?.summary ?? "일간을 기준으로 드러나는 관계와 역할의 반복 신호입니다."}
                </p>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-lg border border-stone-200 bg-[#fbfcf8] p-4 text-sm font-bold leading-6 text-stone-600">
          반복해서 두드러지는 십성이 없습니다. 이 경우에는 일간과 오행 균형, 각 기둥의 역할을 함께 보는 편이 좋습니다.
        </div>
      )}
    </section>
  );
}

function PillarReading({ name, detail }: { name: "year" | "month" | "day" | "hour"; detail: PillarDetail }) {
  const stemGod = detail.stem_ten_god ?? "일간";
  const branchGod = detail.branch_ten_god ?? "—";
  const stemMeaning = tenGodMeanings[stemGod];
  const branchMeaning = tenGodMeanings[branchGod];

  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-[0_10px_30px_rgba(83,64,42,0.05)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black text-mint">{pillarLabels[name]} · {pillarRoleLabels[name]}</p>
          <h4 className="mt-1 text-2xl font-black text-ink">{detail.pillar}</h4>
        </div>
        <div className="flex gap-2">
          <span className={`rounded-lg px-2.5 py-1 text-xs font-black ${elementToneClass[detail.stem_element as ElementKey] ?? "bg-cloud text-stone-600"}`}>
            천간 {elementLabel(detail.stem_element)}
          </span>
          <span className={`rounded-lg px-2.5 py-1 text-xs font-black ${elementToneClass[detail.branch_element as ElementKey] ?? "bg-cloud text-stone-600"}`}>
            지지 {elementLabel(detail.branch_element)}
          </span>
        </div>
      </div>

      <p className="mt-3 break-keep text-sm font-semibold leading-6 text-stone-700">{pillarRoleDescriptions[name]}</p>

      <div className="mt-4 grid gap-2 text-sm font-bold text-stone-700 sm:grid-cols-2">
        <div className="rounded-lg bg-[#f7f8f5] px-3 py-3">
          <p className="text-xs font-black text-stone-500">천간</p>
          <p className="mt-1 text-base font-black text-ink">
            {detail.stem} · {yinYangLabel(detail.stem_yin_yang)}{elementLabel(detail.stem_element)} · {stemGod}
          </p>
          <p className="mt-2 break-keep text-xs font-bold leading-5 text-stone-500">
            {stemMeaning?.summary ?? "겉으로 드러나는 태도와 선택 방식입니다."}
          </p>
        </div>
        <div className="rounded-lg bg-[#f7f8f5] px-3 py-3">
          <p className="text-xs font-black text-stone-500">지지</p>
          <p className="mt-1 text-base font-black text-ink">
            {detail.branch} · {yinYangLabel(detail.branch_yin_yang)}{elementLabel(detail.branch_element)} · {branchGod}
          </p>
          <p className="mt-2 break-keep text-xs font-bold leading-5 text-stone-500">
            {branchMeaning?.summary ?? "안쪽에 깔린 환경, 습관, 관계의 바탕입니다."}
          </p>
        </div>
      </div>
    </div>
  );
}

function PillarDetailSection({ saju }: { saju: SajuData }) {
  return (
    <section className="rounded-lg border border-stone-200 bg-[#fffdf8] p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
      <SectionHeading
        icon={BookOpen}
        eyebrow="네 기둥 풀이"
        title="같은 글자라도 어느 기둥에 있느냐에 따라 쓰임이 달라집니다."
        description="연주, 월주, 일주, 시주의 역할을 나누어 읽습니다."
      />
      <div className="grid gap-3 lg:grid-cols-2">
        {(["year", "month", "day", "hour"] as const).map((key) => (
          <PillarReading key={key} name={key} detail={saju.pillars[key]} />
        ))}
      </div>
    </section>
  );
}

function DaewoonCard({ period }: { period: DaewoonPeriod }) {
  const meaning = tenGodMeanings[period.stem_ten_god];
  const elementKey = period.main_element as ElementKey;

  return (
    <div className="min-w-0 rounded-lg border border-stone-200 bg-white p-4 shadow-[0_10px_30px_rgba(83,64,42,0.05)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black text-stone-500">
            {period.age_start}-{period.age_end}세
          </p>
          <p className="mt-1 text-2xl font-black text-ink">{period.pillar}</p>
        </div>
        <span className={`rounded-lg px-2.5 py-1 text-xs font-black ${elementToneClass[elementKey] ?? "bg-cloud text-stone-600"}`}>
          {elementLabel(period.main_element)}
        </span>
      </div>
      <p className="mt-3 text-xs font-black text-mint">{period.start_year}년 시작 · {period.stem_ten_god}</p>
      <p className="mt-2 break-keep text-sm font-semibold leading-6 text-stone-700">
        {meaning?.summary ?? "이 시기에는 해당 십성의 역할과 오행이 주요 흐름으로 작동합니다."}
      </p>
    </div>
  );
}

function DaewoonSection({ saju }: { saju: SajuData }) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
      <SectionHeading
        icon={TrendingUp}
        eyebrow="대운 흐름"
        title="10년 단위로 들어오는 큰 환경의 변화를 봅니다."
        description="현재 계산은 10세 단위 참고값이며, 절기 차이까지 보정하면 시작 나이가 달라질 수 있습니다."
      />
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {saju.daewoon.map((period) => (
          <DaewoonCard key={`${period.order}-${period.pillar}`} period={period} />
        ))}
      </div>
    </section>
  );
}

export function SajuOnlyResult({ saju, onBack, onRestart }: SajuOnlyResultProps) {
  const dayProfile = stemProfiles[saju.day_master];
  const elementCounts = elementOrder.map((key) => ({ key, count: getElementCount(saju, key) }));
  const maxElementCount = Math.max(...elementCounts.map((item) => item.count));
  const minElementCount = Math.min(...elementCounts.map((item) => item.count));
  const strongestElements = elementCounts.filter((item) => item.count === maxElementCount).map((item) => elementLabels[item.key]);
  const weakestElements = elementCounts.filter((item) => item.count === minElementCount).map((item) => elementLabels[item.key]);
  const tenGodCounts = countTenGods(saju);
  const mainTenGod = tenGodCounts[0]?.[0];
  const mainTenGodMeaning = mainTenGod ? tenGodMeanings[mainTenGod] : null;

  return (
    <article className="space-y-5">
      <header className="rounded-lg border border-[#eadfce] bg-[#fffaf7] p-5 shadow-soft sm:p-7">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-ink text-2xl font-black text-white shadow-sm">
              {saju.day_master}
            </div>
            <div>
              <p className="inline-flex items-center gap-2 rounded-lg bg-[#fff0b9] px-3 py-1.5 text-xs font-black text-[#6e5428]">
                <CalendarClock size={14} aria-hidden /> 만세력 보기
              </p>
              <h2 className="mt-3 break-keep text-3xl font-black leading-tight text-ink sm:text-4xl">명식과 기운을 한눈에 풀어봤습니다.</h2>
              <p className="mt-3 text-sm font-bold leading-6 text-stone-500">
                {saju.solar_date} · {saju.birth_time} · 일간 {saju.day_master}({elementLabel(saju.day_master_element)})
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onBack}
              className="flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 bg-white px-3 text-sm font-bold text-stone-600 transition hover:border-mint hover:text-mint"
            >
              <ArrowLeft size={16} aria-hidden />
              입력으로
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
      </header>

      <section className="grid gap-3 md:grid-cols-3">
        <InsightCard
          title="일간 핵심"
          body={dayProfile?.title ?? `${saju.day_master} 일간은 ${elementLabel(saju.day_master_element)} 기운을 중심으로 해석합니다.`}
        />
        <InsightCard title="강한 오행" body={`${joinLabels(strongestElements)} 기운이 가장 많이 보입니다. 자연스럽게 자주 쓰는 방식입니다.`} />
        <InsightCard
          title="주요 십성"
          body={
            mainTenGod
              ? `${mainTenGod}(${mainTenGodMeaning?.keyword ?? "핵심"}) 기운이 두드러집니다. ${mainTenGodMeaning?.title ?? "반복되는 역할"}을 먼저 봅니다.`
              : "특정 십성이 강하게 반복되기보다 여러 역할이 분산되어 있습니다."
          }
        />
      </section>

      <SajuPillarsTable saju={saju} />

      <section className="rounded-lg border border-[#cce8e2] bg-[#f4fbf8] p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
        <SectionHeading
          icon={Compass}
          eyebrow="일간 풀이"
          title={dayProfile?.title ?? "일간은 사주의 중심입니다."}
          description="일간은 나 자신을 대표하는 천간이며, 십성과 오행 해석의 기준점입니다."
        />
        <div className="grid gap-3 lg:grid-cols-3">
          <div className="rounded-lg border border-white/80 bg-white/80 p-4 lg:col-span-2">
            <p className="break-keep text-base font-bold leading-8 text-stone-700">
              {dayProfile?.summary ?? `${saju.day_master} 일간은 ${elementLabel(saju.day_master_element)}의 성향을 중심으로 자신을 표현합니다.`}
            </p>
          </div>
          <div className="grid gap-3">
            <div className="rounded-lg border border-white/80 bg-white/80 p-4">
              <p className="mb-1 flex items-center gap-2 text-xs font-black text-mint">
                <Star size={14} aria-hidden /> 강점
              </p>
              <p className="break-keep text-sm font-bold leading-6 text-stone-700">{dayProfile?.strength ?? elementMeanings[saju.day_master_element as ElementKey]?.role}</p>
            </div>
            <div className="rounded-lg border border-white/80 bg-white/80 p-4">
              <p className="mb-1 flex items-center gap-2 text-xs font-black text-berry">
                <Sparkles size={14} aria-hidden /> 주의점
              </p>
              <p className="break-keep text-sm font-bold leading-6 text-stone-700">{dayProfile?.caution ?? "강한 기운은 장점이지만 과하면 피로가 되므로 균형을 같이 봅니다."}</p>
            </div>
          </div>
        </div>
      </section>

      <ElementBalance saju={saju} />

      <section className="rounded-lg border border-[#f0dfc4] bg-[#fff8e8] p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
        <SectionHeading
          icon={CircleAlert}
          eyebrow="균형 포인트"
          title={`${joinLabels(weakestElements)} 기운은 의식적으로 채워주면 좋습니다.`}
          description="약한 기운은 없어서 나쁘다는 뜻이 아니라, 자동으로 잘 쓰이지 않는 영역이라는 뜻입니다."
        />
        <div className="grid gap-3 md:grid-cols-2">
          {elementCounts
            .filter((item) => item.count === minElementCount)
            .map(({ key }) => (
              <div key={key} className="rounded-lg border border-[#f0dfc4] bg-white p-4">
                <p className={`mb-3 inline-flex rounded-lg px-2.5 py-1 text-xs font-black ${elementToneClass[key]}`}>{elementLabels[key]} 보완</p>
                <p className="break-keep text-sm font-semibold leading-6 text-stone-700">{elementMeanings[key].low}</p>
                <p className="mt-2 break-keep text-xs font-bold leading-5 text-stone-500">{elementMeanings[key].care}</p>
              </div>
            ))}
        </div>
      </section>

      <TenGodSummary saju={saju} />
      <PillarDetailSection saju={saju} />
      <DaewoonSection saju={saju} />

      <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-[0_14px_36px_rgba(83,64,42,0.06)] sm:p-6">
        <div className="flex items-start gap-3 rounded-lg border border-[#f0dfc4] bg-[#fff8e8] p-4">
          <CircleAlert className="mt-0.5 shrink-0 text-coral" size={18} aria-hidden />
          <div>
            <p className="break-keep text-sm font-black leading-6 text-ink">계산 참고</p>
            <p className="mt-1 break-keep text-sm font-bold leading-6 text-stone-700">{saju.calculation_note}</p>
            <p className="mt-2 break-keep text-xs font-bold leading-5 text-stone-500">
              이 탭은 모델을 호출하지 않고 만세력 계산값, 오행, 십성, 대운 데이터를 바탕으로 고정 해석 문구를 조합해 보여줍니다.
            </p>
          </div>
        </div>
      </section>
    </article>
  );
}
