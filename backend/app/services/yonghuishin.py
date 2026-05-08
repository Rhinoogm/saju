from __future__ import annotations

from dataclasses import dataclass

from app.schemas.saju import (
    DayMasterStrength,
    GeokgukAnalysis,
    GeokgukMonthSource,
    GeokgukYongshinCandidate,
    PillarDetail,
    SpecialGeokCandidate,
    YonghuishinAnalysis,
    YonghuishinCandidate,
    YonghuishinInterpretation,
    YongshinAnalysis,
)
from app.services.saju_features import CONTROLS, ELEMENTS, GENERATES, STEMS, ten_god


ELEMENT_LABELS = {
    "wood": "목",
    "fire": "화",
    "earth": "토",
    "metal": "금",
    "water": "수",
}

HIDDEN_STEMS: dict[str, list[tuple[str, float]]] = {
    "子": [("癸", 1.0)],
    "丑": [("己", 0.6), ("癸", 0.3), ("辛", 0.1)],
    "寅": [("甲", 0.7), ("丙", 0.2), ("戊", 0.1)],
    "卯": [("乙", 1.0)],
    "辰": [("戊", 0.6), ("乙", 0.3), ("癸", 0.1)],
    "巳": [("丙", 0.6), ("戊", 0.2), ("庚", 0.2)],
    "午": [("丁", 0.7), ("己", 0.3)],
    "未": [("己", 0.6), ("丁", 0.2), ("乙", 0.2)],
    "申": [("庚", 0.6), ("壬", 0.2), ("戊", 0.2)],
    "酉": [("辛", 1.0)],
    "戌": [("戊", 0.6), ("辛", 0.2), ("丁", 0.2)],
    "亥": [("壬", 0.7), ("甲", 0.3)],
}

PILLAR_STEM_WEIGHT = {
    "year": 0.8,
    "month": 1.0,
    "day": 1.0,
    "hour": 0.8,
}

PILLAR_BRANCH_WEIGHT = {
    "year": 0.8,
    "month": 1.6,
    "day": 1.0,
    "hour": 0.8,
}

MONTH_BRANCH_MAIN_ELEMENT = {
    "寅": "wood",
    "卯": "wood",
    "辰": "earth",
    "巳": "fire",
    "午": "fire",
    "未": "earth",
    "申": "metal",
    "酉": "metal",
    "戌": "earth",
    "亥": "water",
    "子": "water",
    "丑": "earth",
}

GEOKGUK_BY_TEN_GOD = {
    "비견": "건록격 또는 비견격",
    "겁재": "겁재격",
    "식신": "식신격",
    "상관": "상관격",
    "편재": "편재격",
    "정재": "정재격",
    "편관": "칠살격 / 편관격",
    "정관": "정관격",
    "편인": "편인격",
    "정인": "정인격",
}


@dataclass(frozen=True)
class DayElementRelations:
    peer: str
    mother: str
    child: str
    wealth: str
    officer: str


def analyze_yonghuishin(pillars: dict[str, PillarDetail], day_master: str) -> YonghuishinAnalysis:
    element_power = _compute_element_power(pillars, day_master)
    relations = _day_element_relations(STEMS[day_master]["element"])
    roots = _root_branches(day_master, pillars)
    strength = _judge_strength(pillars, day_master, element_power, relations, roots)
    geokguk = _judge_geokguk(pillars, day_master)
    special_candidates = _detect_special_geok(strength, element_power, relations, roots, pillars)

    eokbu = _select_eokbu_yongshin(strength, element_power, relations, roots)
    geokguk_yongshin = _select_geokguk_yongshin(geokguk, day_master, relations)
    johwu = _select_johwu_yongshin(pillars["month"].branch)
    yongshin = _merge_yongshin_candidates(
        day_master=day_master,
        element_power=element_power,
        strength=strength,
        geokguk=geokguk,
        eokbu=eokbu,
        geokguk_yongshin=geokguk_yongshin,
        johwu=johwu,
        relations=relations,
    )

    return YonghuishinAnalysis(
        element_power={key: round(value, 3) for key, value in element_power.items()},
        strength=strength,
        geokguk=geokguk,
        special_geok_candidates=special_candidates,
        yongshin=yongshin,
        interpretation=_render_interpretation(day_master, pillars, strength, geokguk, yongshin),
    )


def _compute_element_power(pillars: dict[str, PillarDetail], day_master: str) -> dict[str, float]:
    power = {element: 0.0 for element in ELEMENTS}
    visible_stems = {pillar.stem for key, pillar in pillars.items() if key != "day"}

    for key, pillar in pillars.items():
        power[pillar.stem_element] += PILLAR_STEM_WEIGHT[key]
        branch_weight = PILLAR_BRANCH_WEIGHT[key]
        for hidden_stem, hidden_weight in HIDDEN_STEMS[pillar.branch]:
            power[STEMS[hidden_stem]["element"]] += branch_weight * hidden_weight
            if hidden_stem in visible_stems:
                power[STEMS[hidden_stem]["element"]] += 0.15

    root_count = len(_root_branches(day_master, pillars))
    if root_count:
        power[STEMS[day_master]["element"]] += min(0.4, root_count * 0.12)

    month_element = MONTH_BRANCH_MAIN_ELEMENT[pillars["month"].branch]
    for element in ELEMENTS:
        power[element] *= _season_multiplier(month_element, element)

    return power


def _season_multiplier(month_element: str, target_element: str) -> float:
    if target_element == month_element:
        return 1.3
    if GENERATES[month_element] == target_element:
        return 1.15
    if GENERATES[target_element] == month_element:
        return 1.0
    if CONTROLS[month_element] == target_element:
        return 0.85
    if CONTROLS[target_element] == month_element:
        return 0.7
    return 1.0


def _day_element_relations(day_element: str) -> DayElementRelations:
    mother = next(element for element in ELEMENTS if GENERATES[element] == day_element)
    officer = next(element for element in ELEMENTS if CONTROLS[element] == day_element)
    return DayElementRelations(
        peer=day_element,
        mother=mother,
        child=GENERATES[day_element],
        wealth=CONTROLS[day_element],
        officer=officer,
    )


def _root_branches(day_master: str, pillars: dict[str, PillarDetail]) -> list[str]:
    day_element = STEMS[day_master]["element"]
    roots: list[str] = []
    for pillar in pillars.values():
        if any(STEMS[stem]["element"] == day_element and weight >= 0.3 for stem, weight in HIDDEN_STEMS[pillar.branch]):
            roots.append(pillar.branch)
    return roots


def _judge_strength(
    pillars: dict[str, PillarDetail],
    day_master: str,
    element_power: dict[str, float],
    relations: DayElementRelations,
    roots: list[str],
) -> DayMasterStrength:
    support_score = element_power[relations.peer] + element_power[relations.mother]
    drain_score = element_power[relations.child] + element_power[relations.wealth] + element_power[relations.officer]
    base = support_score / max(0.001, support_score + drain_score)
    index = base
    evidence: list[str] = []

    month_branch = pillars["month"].branch
    month_element = MONTH_BRANCH_MAIN_ELEMENT[month_branch]
    if month_element == relations.peer:
        index += 0.08
        evidence.append(f"월령 {month_branch}이 일간 오행과 같아 계절 세력을 얻습니다.")
    elif month_element == relations.mother:
        index += 0.05
        evidence.append(f"월령 {month_branch}이 일간을 생하는 기운이라 보조 세력이 있습니다.")
    else:
        evidence.append(f"월령 {month_branch}의 중심은 {ELEMENT_LABELS[month_element]}이라 일간 세력과 거리를 둡니다.")

    if roots:
        index += 0.06
        evidence.append(f"지지 {', '.join(roots[:3])}에 일간의 뿌리가 확인됩니다.")
    else:
        evidence.append("지지 지장간에서 일간의 뚜렷한 뿌리는 약합니다.")

    support_stems_count = sum(
        1
        for key, pillar in pillars.items()
        if key != "day" and pillar.stem_element in {relations.peer, relations.mother}
    )
    if support_stems_count >= 2:
        index += 0.04
        evidence.append("천간에 비겁·인성 계열이 반복되어 일간을 돕습니다.")

    total_power = sum(element_power.values())
    if element_power[relations.officer] + element_power[relations.wealth] > total_power * 0.52:
        index -= 0.04
        evidence.append("재성·관성 세력이 커서 일간이 감당해야 할 압박도 큽니다.")

    index = max(0.0, min(1.0, index))
    return DayMasterStrength(
        support_score=round(support_score, 3),
        drain_score=round(drain_score, 3),
        strength_index=round(index, 3),
        label=_strength_label(index),
        evidence=evidence[:5],
    )


def _strength_label(index: float) -> str:
    if index < 0.3:
        return "극신약"
    if index < 0.43:
        return "신약"
    if index <= 0.57:
        return "중화"
    if index <= 0.7:
        return "신강"
    return "극신강"


def _judge_geokguk(pillars: dict[str, PillarDetail], day_master: str) -> GeokgukAnalysis:
    month_branch = pillars["month"].branch
    visible_stems = {pillar.stem for key, pillar in pillars.items() if key != "day"}
    hidden_stems = HIDDEN_STEMS[month_branch]
    transmitted_stem = next((stem for stem, _ in hidden_stems if stem in visible_stems), None)
    selected_stem = transmitted_stem or hidden_stems[0][0]
    selected_ten_god = ten_god(day_master, selected_stem)
    damage = _geokguk_damage(selected_ten_god, pillars)
    confidence = 0.78 if transmitted_stem else 0.56
    confidence -= min(0.18, len(damage) * 0.06)

    return GeokgukAnalysis(
        name=GEOKGUK_BY_TEN_GOD[selected_ten_god],
        selected_from_month=GeokgukMonthSource(
            month_branch=month_branch,
            selected_hidden_stem=selected_stem,
            ten_god=selected_ten_god,
            transmitted=transmitted_stem is not None,
        ),
        confidence=round(max(0.35, confidence), 2),
        damage=damage,
    )


def _geokguk_damage(selected_ten_god: str, pillars: dict[str, PillarDetail]) -> list[str]:
    visible_ten_gods = [
        pillar.stem_ten_god
        for key, pillar in pillars.items()
        if key != "day" and pillar.stem_ten_god and pillar.stem_ten_god != "일간"
    ]
    damage: list[str] = []
    if selected_ten_god == "정관" and "상관" in visible_ten_gods:
        damage.append("상관이 정관을 직접 건드릴 수 있어 격의 순도가 낮아집니다.")
    if selected_ten_god == "식신" and any(item in visible_ten_gods for item in ("편인", "정인")):
        damage.append("인성 기운이 식신의 자연스러운 발산을 누를 수 있습니다.")
    if selected_ten_god in {"편관", "정관"} and {"편관", "정관"}.issubset(set(visible_ten_gods)):
        damage.append("관성 계열이 섞여 책임과 압박의 결이 복합적입니다.")
    if not damage:
        damage.append("월령 중심 기운을 크게 깨는 손상 신호는 약합니다.")
    return damage


def _detect_special_geok(
    strength: DayMasterStrength,
    element_power: dict[str, float],
    relations: DayElementRelations,
    roots: list[str],
    pillars: dict[str, PillarDetail],
) -> list[SpecialGeokCandidate]:
    total = sum(element_power.values())
    candidates: list[SpecialGeokCandidate] = []
    drain_groups = {
        "종재격 후보": (relations.wealth, "재성 세력이 전체 흐름을 주도합니다."),
        "종살격 후보": (relations.officer, "관살 세력이 일간을 강하게 압박합니다."),
        "종아격 / 종식상격 후보": (relations.child, "식상 세력이 밖으로 새는 흐름을 키웁니다."),
    }
    if strength.strength_index < 0.3 and not roots:
        for name, (element, reason) in drain_groups.items():
            ratio = element_power[element] / max(0.001, total)
            if ratio >= 0.55:
                candidates.append(SpecialGeokCandidate(name=name, confidence=round(min(0.72, ratio), 2), reason=reason))

    top_element, top_power = max(element_power.items(), key=lambda item: item[1])
    top_ratio = top_power / max(0.001, total)
    month_element = MONTH_BRANCH_MAIN_ELEMENT[pillars["month"].branch]
    if top_ratio > 0.65 and month_element in {top_element, next(element for element in ELEMENTS if GENERATES[element] == top_element)}:
        candidates.append(
            SpecialGeokCandidate(
                name="전왕격 후보",
                confidence=round(min(0.76, top_ratio), 2),
                reason=f"{ELEMENT_LABELS[top_element]} 기운이 원국에서 한 방향으로 강하게 모입니다.",
            )
        )
    return candidates[:3]


def _select_eokbu_yongshin(
    strength: DayMasterStrength,
    element_power: dict[str, float],
    relations: DayElementRelations,
    roots: list[str],
) -> list[YonghuishinCandidate]:
    if strength.label in {"극신약", "신약"}:
        candidates: list[YonghuishinCandidate] = []
        if element_power[relations.officer] >= max(element_power[relations.wealth], element_power[relations.child]) * 0.9:
            candidates.append(_candidate(relations.mother, 1.0, "관성 압박을 통관하고 약한 일간을 생하는 인성 기운입니다."))
        if element_power[relations.wealth] >= max(element_power[relations.officer], element_power[relations.child]) * 0.9 or not roots:
            candidates.append(_candidate(relations.peer, 0.82, "일간의 직접적인 기준과 버팀을 보강하는 비겁 기운입니다."))
        if not candidates:
            candidates.extend(
                [
                    _candidate(relations.mother, 0.9, "소모된 일간을 회복시키는 인성 기운입니다."),
                    _candidate(relations.peer, 0.72, "일간의 뿌리와 자기 기준을 더하는 비겁 기운입니다."),
                ]
            )
        return _unique_candidates(candidates)

    if strength.label in {"신강", "극신강"}:
        if element_power[relations.peer] >= element_power[relations.mother]:
            return _unique_candidates(
                [
                    _candidate(relations.officer, 1.0, "강한 비겁을 기준과 책임으로 다듬는 관성 기운입니다."),
                    _candidate(relations.child, 0.78, "왕한 일간의 힘을 밖으로 흘려 보내는 식상 기운입니다."),
                ]
            )
        return _unique_candidates(
            [
                _candidate(relations.wealth, 1.0, "과한 인성을 현실 감각으로 조절하는 재성 기운입니다."),
                _candidate(relations.child, 0.76, "막힌 힘을 표현과 생산성으로 풀어내는 식상 기운입니다."),
            ]
        )

    return _unique_candidates(
        [
            _candidate(relations.child, 0.62, "중화 명조에서는 흐름을 만들고 표현하는 식상 기운을 먼저 봅니다."),
            _candidate(relations.mother, 0.54, "균형을 잃지 않도록 해석과 회복을 돕는 인성 기운입니다."),
        ]
    )


def _select_geokguk_yongshin(
    geokguk: GeokgukAnalysis,
    day_master: str,
    relations: DayElementRelations,
) -> list[GeokgukYongshinCandidate]:
    selected_stem = geokguk.selected_from_month.selected_hidden_stem
    selected_element = STEMS[selected_stem]["element"]
    selected_ten_god = geokguk.selected_from_month.ten_god
    sangshin = _sangshin_elements(selected_ten_god, relations)
    candidates = [
        GeokgukYongshinCandidate(
            element=selected_element,
            score=0.9,
            ten_god=selected_ten_god,
            stem=selected_stem,
            reason=f"월지 {geokguk.selected_from_month.month_branch}의 {selected_stem}이 일간 {day_master} 기준 {selected_ten_god}으로 작동합니다.",
        )
    ]
    for element in sangshin:
        candidates.append(
            GeokgukYongshinCandidate(
                element=element,
                score=0.54,
                ten_god=None,
                stem=None,
                reason=f"{geokguk.name}이 매끄럽게 작동하도록 돕는 상신 후보입니다.",
            )
        )
    return _unique_geokguk_candidates(candidates)


def _sangshin_elements(ten_god_name: str, relations: DayElementRelations) -> list[str]:
    if ten_god_name in {"정관", "편관"}:
        return [relations.wealth, relations.mother]
    if ten_god_name in {"정인", "편인"}:
        return [relations.officer, relations.peer]
    if ten_god_name in {"식신", "상관"}:
        return [relations.wealth, relations.mother]
    if ten_god_name in {"정재", "편재"}:
        return [relations.child, relations.officer]
    return [relations.officer, relations.child]


def _select_johwu_yongshin(month_branch: str) -> list[YonghuishinCandidate]:
    if month_branch in {"亥", "子", "丑"}:
        return [
            _candidate("fire", 0.9, "한습한 계절감을 덥히고 마음의 온도를 회복시키는 조후 기운입니다."),
            _candidate("earth", 0.55, "차갑게 흩어진 흐름을 머물게 하는 보조 조후 기운입니다."),
        ]
    if month_branch in {"巳", "午", "未"}:
        return [
            _candidate("water", 0.9, "조열한 계절감을 식히고 생각의 여백을 돌려주는 조후 기운입니다."),
            _candidate("metal", 0.55, "뜨거운 흐름을 서늘한 기준으로 정리하는 보조 조후 기운입니다."),
        ]
    if month_branch in {"寅", "卯", "辰"}:
        return [
            _candidate("fire", 0.78, "봄의 생장을 밖으로 드러나게 하는 조후 기운입니다."),
            _candidate("water", 0.56, "새로 자라는 기운이 마르지 않게 돕는 보조 조후 기운입니다."),
        ]
    return [
        _candidate("water", 0.78, "가을의 건조함에 유연함과 휴식을 더하는 조후 기운입니다."),
        _candidate("fire", 0.56, "서늘한 기운에 온기와 표현력을 보태는 보조 조후 기운입니다."),
    ]


def _merge_yongshin_candidates(
    *,
    day_master: str,
    element_power: dict[str, float],
    strength: DayMasterStrength,
    geokguk: GeokgukAnalysis,
    eokbu: list[YonghuishinCandidate],
    geokguk_yongshin: list[GeokgukYongshinCandidate],
    johwu: list[YonghuishinCandidate],
    relations: DayElementRelations,
) -> YongshinAnalysis:
    weights = _merge_weights(strength, geokguk)
    scores = {element: 0.0 for element in ELEMENTS}
    for candidate in eokbu:
        scores[candidate.element] += weights["eokbu"] * (candidate.score or 0.0)
    for candidate in geokguk_yongshin:
        scores[candidate.element] += weights["geokguk"] * (candidate.score or 0.0)
    for candidate in johwu:
        scores[candidate.element] += weights["johwu"] * (candidate.score or 0.0)

    for element, penalty in _damage_penalties(element_power, strength, relations).items():
        scores[element] -= 0.3 * penalty

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    final_element = ranked[0][0]
    second_element = next((element for element, score in ranked[1:] if score > 0 and element != final_element), None)
    final_candidates = [
        _candidate(
            final_element,
            round(ranked[0][1], 3),
            f"억부·격국·조후 기준을 통합했을 때 {ELEMENT_LABELS[final_element]} 기운이 가장 우선됩니다.",
        )
    ]
    if second_element:
        final_candidates.append(
            _candidate(
                second_element,
                round(scores[second_element], 3),
                f"{ELEMENT_LABELS[final_element]} 용신의 작동을 보조하는 다음 후보입니다.",
            )
        )

    hui_element = _select_huishin(final_element, ranked, relations)
    gishin_element = _select_gishin(element_power, strength, scores, relations)
    return YongshinAnalysis(
        eokbu_yongshin=eokbu,
        geokguk_yongshin=geokguk_yongshin,
        johwu_yongshin=johwu,
        final_yongshin=final_candidates,
        huishin=[
            _candidate(
                hui_element,
                round(max(scores.get(hui_element, 0.0), 0.1), 3),
                f"{ELEMENT_LABELS[final_element]} 용신이 일상에서 부드럽게 작동하도록 돕는 희신입니다.",
            )
        ],
        gishin=[
            _candidate(
                gishin_element,
                round(-abs(scores.get(gishin_element, 0.1)), 3),
                f"현재 균형에서는 {ELEMENT_LABELS[gishin_element]} 기운이 과해지면 부담이 커지기 쉽습니다.",
            )
        ],
    )


def _merge_weights(strength: DayMasterStrength, geokguk: GeokgukAnalysis) -> dict[str, float]:
    if geokguk.confidence >= 0.72:
        return {"eokbu": 0.3, "geokguk": 0.5, "johwu": 0.2}
    if strength.label == "중화":
        return {"eokbu": 0.25, "geokguk": 0.5, "johwu": 0.25}
    return {"eokbu": 0.45, "geokguk": 0.35, "johwu": 0.2}


def _damage_penalties(
    element_power: dict[str, float],
    strength: DayMasterStrength,
    relations: DayElementRelations,
) -> dict[str, float]:
    penalties = {element: 0.0 for element in ELEMENTS}
    total = sum(element_power.values())
    for element, power in element_power.items():
        ratio = power / max(0.001, total)
        if ratio > 0.38:
            penalties[element] += min(0.9, ratio)

    if strength.label in {"극신약", "신약"}:
        penalties[relations.officer] += 0.35
        penalties[relations.wealth] += 0.2
    elif strength.label in {"신강", "극신강"}:
        penalties[relations.peer] += 0.35
        penalties[relations.mother] += 0.2
    return penalties


def _select_huishin(final_element: str, ranked: list[tuple[str, float]], relations: DayElementRelations) -> str:
    if final_element == relations.mother:
        return relations.peer
    if final_element == relations.peer:
        return relations.mother
    for element, score in ranked:
        if element != final_element and score > 0:
            return element
    return next(element for element in ELEMENTS if GENERATES[element] == final_element)


def _select_gishin(
    element_power: dict[str, float],
    strength: DayMasterStrength,
    scores: dict[str, float],
    relations: DayElementRelations,
) -> str:
    if strength.label in {"극신약", "신약"}:
        return max([relations.officer, relations.wealth, relations.child], key=lambda element: element_power[element])
    if strength.label in {"신강", "극신강"}:
        return max([relations.peer, relations.mother], key=lambda element: element_power[element])
    return min(scores.items(), key=lambda item: item[1])[0]


def _render_interpretation(
    day_master: str,
    pillars: dict[str, PillarDetail],
    strength: DayMasterStrength,
    geokguk: GeokgukAnalysis,
    yongshin: YongshinAnalysis,
) -> YonghuishinInterpretation:
    day_element = STEMS[day_master]["element"]
    month_branch = pillars["month"].branch
    final = yongshin.final_yongshin[0]
    hui = yongshin.huishin[0]
    gi = yongshin.gishin[0]
    return YonghuishinInterpretation(
        summary=(
            f"{day_master} 일간은 월령 {month_branch}의 영향을 크게 받으며, "
            f"v1 휴리스틱 기준 {strength.label}에 가깝습니다."
        ),
        strength_reading=(
            f"일간을 돕는 {ELEMENT_LABELS[day_element]} 계열과 인성 세력은 {strength.support_score}이고, "
            f"소모·제어 세력은 {strength.drain_score}로 계산됩니다."
        ),
        geokguk_reading=(
            f"월령 지장간 기준 {geokguk.name}으로 보며, "
            f"성격 신뢰도는 {geokguk.confidence}입니다."
        ),
        yongshin_reading=(
            f"최종 용신은 {ELEMENT_LABELS[final.element]}, 희신은 {ELEMENT_LABELS[hui.element]}, "
            f"기신은 {ELEMENT_LABELS[gi.element]} 기운으로 판단합니다."
        ),
    )


def _candidate(element: str, score: float | None, reason: str) -> YonghuishinCandidate:
    return YonghuishinCandidate(element=element, score=score, reason=reason)


def _unique_candidates(candidates: list[YonghuishinCandidate]) -> list[YonghuishinCandidate]:
    seen: set[str] = set()
    unique: list[YonghuishinCandidate] = []
    for candidate in candidates:
        if candidate.element in seen:
            continue
        seen.add(candidate.element)
        unique.append(candidate)
    return unique


def _unique_geokguk_candidates(candidates: list[GeokgukYongshinCandidate]) -> list[GeokgukYongshinCandidate]:
    seen: set[str] = set()
    unique: list[GeokgukYongshinCandidate] = []
    for candidate in candidates:
        key = f"{candidate.element}:{candidate.ten_god}:{candidate.stem}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique
