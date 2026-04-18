from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.saju import DaewoonPeriod, Gender, PillarDetail


ELEMENTS = ("wood", "fire", "earth", "metal", "water")
GENERATES = {
    "wood": "fire",
    "fire": "earth",
    "earth": "metal",
    "metal": "water",
    "water": "wood",
}
CONTROLS = {
    "wood": "earth",
    "earth": "water",
    "water": "fire",
    "fire": "metal",
    "metal": "wood",
}

STEMS: dict[str, dict[str, str]] = {
    "甲": {"element": "wood", "yin_yang": "yang", "ko": "갑"},
    "乙": {"element": "wood", "yin_yang": "yin", "ko": "을"},
    "丙": {"element": "fire", "yin_yang": "yang", "ko": "병"},
    "丁": {"element": "fire", "yin_yang": "yin", "ko": "정"},
    "戊": {"element": "earth", "yin_yang": "yang", "ko": "무"},
    "己": {"element": "earth", "yin_yang": "yin", "ko": "기"},
    "庚": {"element": "metal", "yin_yang": "yang", "ko": "경"},
    "辛": {"element": "metal", "yin_yang": "yin", "ko": "신"},
    "壬": {"element": "water", "yin_yang": "yang", "ko": "임"},
    "癸": {"element": "water", "yin_yang": "yin", "ko": "계"},
}

BRANCHES: dict[str, dict[str, str]] = {
    "子": {"element": "water", "yin_yang": "yang", "ko": "자"},
    "丑": {"element": "earth", "yin_yang": "yin", "ko": "축"},
    "寅": {"element": "wood", "yin_yang": "yang", "ko": "인"},
    "卯": {"element": "wood", "yin_yang": "yin", "ko": "묘"},
    "辰": {"element": "earth", "yin_yang": "yang", "ko": "진"},
    "巳": {"element": "fire", "yin_yang": "yin", "ko": "사"},
    "午": {"element": "fire", "yin_yang": "yang", "ko": "오"},
    "未": {"element": "earth", "yin_yang": "yin", "ko": "미"},
    "申": {"element": "metal", "yin_yang": "yang", "ko": "신"},
    "酉": {"element": "metal", "yin_yang": "yin", "ko": "유"},
    "戌": {"element": "earth", "yin_yang": "yang", "ko": "술"},
    "亥": {"element": "water", "yin_yang": "yin", "ko": "해"},
}

STEM_SEQUENCE = list(STEMS.keys())
BRANCH_SEQUENCE = list(BRANCHES.keys())
PILLAR_CYCLE = [
    STEM_SEQUENCE[i % len(STEM_SEQUENCE)] + BRANCH_SEQUENCE[i % len(BRANCH_SEQUENCE)]
    for i in range(60)
]


@dataclass(frozen=True)
class StemBranch:
    symbol: str
    element: str
    yin_yang: str


def _stem_info(stem: str) -> StemBranch:
    info = STEMS[stem]
    return StemBranch(symbol=stem, element=info["element"], yin_yang=info["yin_yang"])


def _branch_info(branch: str) -> StemBranch:
    info = BRANCHES[branch]
    return StemBranch(symbol=branch, element=info["element"], yin_yang=info["yin_yang"])


def ten_god(day_stem: str, target_stem_or_branch: str) -> str:
    day = _stem_info(day_stem)
    target = _stem_info(target_stem_or_branch) if target_stem_or_branch in STEMS else _branch_info(target_stem_or_branch)
    same_polarity = day.yin_yang == target.yin_yang

    if target.element == day.element:
        return "비견" if same_polarity else "겁재"
    if GENERATES[day.element] == target.element:
        return "식신" if same_polarity else "상관"
    if CONTROLS[day.element] == target.element:
        return "편재" if same_polarity else "정재"
    if CONTROLS[target.element] == day.element:
        return "편관" if same_polarity else "정관"
    if GENERATES[target.element] == day.element:
        return "편인" if same_polarity else "정인"

    raise ValueError(f"Cannot determine ten god for {day_stem} -> {target_stem_or_branch}")


def enrich_pillars(raw_saju: dict[str, Any]) -> dict[str, PillarDetail]:
    day_stem = raw_saju["day_stem"]
    result: dict[str, PillarDetail] = {}

    for key in ("year", "month", "day", "hour"):
        stem = raw_saju[f"{key}_stem"]
        branch = raw_saju[f"{key}_branch"]
        stem_info = _stem_info(stem)
        branch_info = _branch_info(branch)
        result[key] = PillarDetail(
            pillar=raw_saju[f"{key}_pillar"],
            stem=stem,
            branch=branch,
            stem_element=stem_info.element,
            branch_element=branch_info.element,
            stem_yin_yang=stem_info.yin_yang,  # type: ignore[arg-type]
            branch_yin_yang=branch_info.yin_yang,  # type: ignore[arg-type]
            stem_ten_god=ten_god(day_stem, stem) if key != "day" else "일간",
            branch_ten_god=ten_god(day_stem, branch),
        )

    return result


def count_elements(pillars: dict[str, PillarDetail]) -> dict[str, int]:
    counts = {element: 0 for element in ELEMENTS}
    for pillar in pillars.values():
        counts[pillar.stem_element] += 1
        counts[pillar.branch_element] += 1
    return counts


def flatten_ten_gods(pillars: dict[str, PillarDetail]) -> dict[str, str]:
    return {
        f"{key}_stem": value.stem_ten_god or ""
        for key, value in pillars.items()
    } | {
        f"{key}_branch": value.branch_ten_god or ""
        for key, value in pillars.items()
    }


def daewoon_direction(gender: Gender, year_stem: str) -> int:
    year_yin_yang = _stem_info(year_stem).yin_yang
    if gender == Gender.other:
        return 1
    if gender == Gender.male:
        return 1 if year_yin_yang == "yang" else -1
    return 1 if year_yin_yang == "yin" else -1


def build_daewoon(raw_saju: dict[str, Any], gender: Gender, count: int = 8) -> list[DaewoonPeriod]:
    direction = daewoon_direction(gender, raw_saju["year_stem"])
    month_pillar = raw_saju["month_pillar"]
    birth_year = int(raw_saju["birth_date"].split("-")[0])
    start_index = PILLAR_CYCLE.index(month_pillar)
    periods: list[DaewoonPeriod] = []

    for order in range(1, count + 1):
        cycle_index = (start_index + (direction * order)) % len(PILLAR_CYCLE)
        pillar = PILLAR_CYCLE[cycle_index]
        stem = pillar[0]
        branch = pillar[1]
        age_start = order * 10
        periods.append(
            DaewoonPeriod(
                order=order,
                age_start=age_start,
                age_end=age_start + 9,
                start_year=birth_year + age_start,
                pillar=pillar,
                stem=stem,
                branch=branch,
                stem_ten_god=ten_god(raw_saju["day_stem"], stem),
                main_element=STEMS[stem]["element"],
            )
        )

    return periods


def calculation_note(gender: Gender) -> str:
    if gender == Gender.other:
        return "대운 방향은 전통 계산식에 필요한 성별 값이 중립/기타로 입력되어 순행 기본값으로 산출했습니다. 대운 시작 나이는 MVP에서 10세 단위 근사값입니다."
    return "대운 시작 나이는 MVP에서 10세 단위 근사값입니다. 정확한 대운수는 절기 전후 시간 차 계산을 추가해 보정할 수 있습니다."

