from datetime import date

from app.schemas.saju import FinalReadingRequest, GenerateNextQuestionRequest, Gender
from app.services.calendar_service import CalendarService
from app.services.prompt_builder import (
    FINAL_SYSTEM_PROMPT_DIRECT,
    FINAL_SYSTEM_PROMPT_TRADITIONAL,
    build_final_reading_prompt,
    build_question_generation_prompt,
)
from app.services.prompt_store import PromptStore
from app.services.saju_features import build_daewoon, calculation_note, enrich_pillars, score_ten_gods, ten_god
from app.services.yonghuishin import analyze_yonghuishin


def test_ten_god_mapping_for_gap_day_master() -> None:
    assert ten_god("甲", "甲") == "비견"
    assert ten_god("甲", "乙") == "겁재"
    assert ten_god("甲", "丙") == "식신"
    assert ten_god("甲", "丁") == "상관"
    assert ten_god("甲", "戊") == "편재"
    assert ten_god("甲", "己") == "정재"
    assert ten_god("甲", "庚") == "편관"
    assert ten_god("甲", "辛") == "정관"
    assert ten_god("甲", "壬") == "편인"
    assert ten_god("甲", "癸") == "정인"


def test_daewoon_uses_direction_from_gender_and_year_stem() -> None:
    raw = {
        "year_stem": "甲",
        "month_pillar": "甲子",
        "day_stem": "甲",
        "birth_date": "1990-10-10",
    }

    forward = build_daewoon(raw, Gender.male, count=2)
    backward = build_daewoon(raw, Gender.female, count=2)

    assert [period.pillar for period in forward] == ["乙丑", "丙寅"]
    assert [period.pillar for period in backward] == ["癸亥", "壬戌"]


def test_current_luck_uses_fixed_reference_date() -> None:
    luck = CalendarService()._build_current_luck("甲", date(2026, 5, 5))

    assert luck.reference_date == "2026-05-05"
    assert luck.annual.pillar == "丙午"
    assert luck.annual.stem_ten_god == "식신"
    assert luck.next_month.label == "2026년 6월 월운"
    assert luck.next_month.representative_date == "2026-06-15"
    assert luck.next_month.pillar == "甲午"


def test_ten_god_scores_rank_by_weight_then_priority() -> None:
    scores = score_ten_gods(
        {
            "year_stem": "겁재",
            "year_branch": "비견",
            "month_stem": "정재",
            "month_branch": "정재",
            "day_stem": "일간",
            "day_branch": "편인",
            "hour_stem": "비견",
            "hour_branch": "겁재",
        }
    )

    assert scores[0].name == "정재"
    assert scores[0].score == 2.6
    assert scores[0].positions == ["month_stem", "month_branch"]
    assert [score.name for score in scores[1:3]] == ["비견", "겁재"]


def _raw_chart(*, year: str, month: str, day: str, hour: str) -> dict:
    return {
        "year_pillar": year,
        "month_pillar": month,
        "day_pillar": day,
        "hour_pillar": hour,
        "year_stem": year[0],
        "year_branch": year[1],
        "month_stem": month[0],
        "month_branch": month[1],
        "day_stem": day[0],
        "day_branch": day[1],
        "hour_stem": hour[0],
        "hour_branch": hour[1],
    }


def test_yonghuishin_power_uses_hidden_stems_and_month_season() -> None:
    pillars = enrich_pillars(_raw_chart(year="庚午", month="丙戌", day="戊申", hour="己未"))
    analysis = analyze_yonghuishin(pillars, "戊")

    assert analysis.element_power["earth"] > 5
    assert analysis.element_power["fire"] > 2
    assert analysis.strength.label == "극신강"
    assert "월령 戌" in analysis.strength.evidence[0]
    assert analysis.yongshin.final_yongshin[0].element == "wood"
    assert analysis.yongshin.gishin[0].element == "earth"


def test_yonghuishin_weak_chart_selects_supporting_yongshin() -> None:
    pillars = enrich_pillars(_raw_chart(year="庚申", month="辛酉", day="甲午", hour="庚申"))
    analysis = analyze_yonghuishin(pillars, "甲")

    assert analysis.strength.label == "극신약"
    assert analysis.yongshin.final_yongshin[0].element == "water"
    assert analysis.yongshin.huishin[0].element == "wood"
    assert analysis.yongshin.gishin[0].element == "metal"


def test_question_prompt_uses_initial_concern_step_guide_and_previous_answers(sample_request) -> None:
    payload = sample_request.model_dump(mode="json")
    payload["answers"] = [
        {
            "question_id": "q1",
            "question": "이 고민을 떠올릴 때 가장 큰 감정은 무엇인가요?",
            "answer": "잘못 선택할까 봐 커지는 불안과 초조함",
            "selected_option_ids": ["D"],
            "selected_option_id": "D",
        },
    ]
    built = build_question_generation_prompt(GenerateNextQuestionRequest(**payload), target_question_id="q2")

    assert built.prompt.index("<step_guide>") < built.prompt.index("<user_profile>") < built.prompt.index("<previous_answers>")
    assert sample_request.initial_concern in built.prompt
    assert "통제 소재 파악" in built.prompt
    assert "잘못 선택할까 봐 커지는 불안과 초조함" in built.prompt
    assert "options는 정확히 4개" in built.system
    assert "사주 명식 데이터" not in built.prompt
    assert '"birth"' not in built.prompt
    assert '"selected_option_ids"' not in built.prompt
    assert '"selected_option_id"' not in built.prompt
    assert built.schema_name == "QuestionGenerationOutput"
    assert built.schema["$defs"]["DiagnosticQuestion"]["properties"]["intent_signal"]["minLength"] == 1
    assert "question" in built.schema["properties"]


def test_final_prompt_requests_report_structure(sample_request, sample_saju_data) -> None:
    payload = sample_request.model_dump(mode="json")
    payload["answers"] = [
        {
            "question_id": f"q{index}",
            "question": f"질문 {index}",
            "answer": "조건을 확인하고 움직이고 싶습니다.",
            "selected_option_ids": ["A"],
        }
        for index in [1, 2, 3, 4, 5]
    ]
    built = build_final_reading_prompt(FinalReadingRequest(**payload), sample_saju_data)

    assert "프리미엄 사주 앱 'Saju-i'" in built.prompt
    assert "hashtags" not in built.prompt
    assert "해시태그" not in built.prompt
    assert "compass_summary" in built.prompt
    assert "manse_summary" in built.prompt
    assert "dual_reading" in built.prompt
    assert "healing_card" in built.prompt
    assert "secret_door" in built.prompt
    assert "final_yongshin[0]" in built.prompt
    assert "current_luck" in built.prompt
    assert "dominant_ten_god" in built.prompt
    assert "고객이 진짜 듣고 싶었던 말" in built.prompt
    assert "두려워하는 선택 기준" not in built.prompt
    assert "5단계 답변으로 듣고 싶은 말 추론" in built.prompt
    assert "긍정적인 작용" in built.prompt
    assert "한글(한자)" in built.prompt
    assert "쉬운 설명" in built.prompt
    assert "strength_animal" in built.prompt
    assert "첫 카드 섹션 헤드라인" in built.prompt
    assert "원국" in built.prompt
    assert "용신" in built.prompt
    assert "희신" in built.prompt
    assert "기신" in built.prompt
    assert "오행 균형" in built.prompt
    assert "상담 분석 라벨을 절대 노출하지 않는다" in built.prompt
    assert "q3의 핵심 결핍" in built.prompt
    assert "q4 행동 동기" in built.prompt
    assert "다른 카테고리의 십성" in built.prompt
    assert "스키마에 없는 추가 필드" in built.prompt
    assert "`caution`은 객체가 아니라 문자열 필드" in built.prompt
    assert "<qna_data>" in built.prompt
    assert "<budget_and_quality_control>" in built.prompt
    assert "1차원적 맵핑" in built.prompt
    assert "데이터 격리(Anti-Anchoring)" in built.prompt
    assert "answer_signal_summary" not in built.prompt
    assert "situation_mirror" not in built.prompt
    assert "luck_recipe" not in built.prompt
    assert "share_card" not in built.prompt
    assert sample_request.initial_concern in built.prompt
    assert built.schema_name == "FinalReadingOutput"
    assert "compass_summary" in built.schema["properties"]
    assert "manse_summary" in built.schema["properties"]
    assert "dual_reading" in built.schema["properties"]
    assert "healing_card" in built.schema["properties"]
    assert "secret_door" in built.schema["properties"]
    healing_card_properties = built.schema["$defs"]["HealingCard"]["properties"]
    assert "metaphor_sentence" in healing_card_properties
    assert "affirmation" in healing_card_properties
    assert "direction" in healing_card_properties
    assert "situation_mirror" not in built.schema["properties"]
    assert "luck_recipe" not in built.schema["properties"]
    assert "answer_signal_summary" not in built.schema["properties"]
    compass_properties = built.schema["$defs"]["CompassSummary"]["properties"]
    assert "basis" in compass_properties
    assert "solution" in compass_properties
    assert "고급 문학 에세이나 철학서" in FINAL_SYSTEM_PROMPT_TRADITIONAL
    assert "오만한 하대 화법" in FINAL_SYSTEM_PROMPT_DIRECT
    assert "hashtags" not in built.schema["properties"]
    assert "calculation_note" not in built.prompt
    assert '"birth"' not in built.prompt
    assert '"selected_option_ids"' not in built.prompt
    assert '"selected_option_id"' not in built.prompt
    assert "MVP" not in built.prompt


def test_final_prompt_falls_back_when_saved_prompt_lacks_bento_marker(sample_request, sample_saju_data, tmp_path) -> None:
    payload = sample_request.model_dump(mode="json")
    payload["answers"] = [
        {
            "question_id": f"q{index}",
            "question": f"질문 {index}",
            "answer": "조건을 확인하고 움직이고 싶습니다.",
            "selected_option_ids": ["A"],
        }
        for index in [1, 2, 3, 4, 5]
    ]
    store = PromptStore(str(tmp_path / "prompts.sqlite3"))
    store.init()
    store.set_prompt("final_user_prompt", "old prompt with share_card.strengths")
    store.set_prompt("final_system_prompt_direct", "old direct prompt without share card exception")

    built = build_final_reading_prompt(FinalReadingRequest(**{**payload, "reading_style": "direct"}), sample_saju_data, prompt_store=store)

    assert "old prompt" not in built.prompt
    assert "compass_summary" in built.prompt
    assert "strength_animal" in built.prompt
    assert "healing_card_tone_exception" in built.system


def test_calculation_note_does_not_expose_internal_mvp_wording() -> None:
    assert "MVP" not in calculation_note(Gender.male)
    assert "MVP" not in calculation_note(Gender.other)
