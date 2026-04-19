from app.schemas.saju import FinalReadingRequest, Gender
from app.services.prompt_builder import build_final_reading_prompt, build_question_generation_prompt
from app.services.saju_features import build_daewoon, calculation_note, ten_god


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


def test_prompt_places_initial_concern_before_chart_data(sample_request, sample_saju_data) -> None:
    built = build_question_generation_prompt(sample_request, sample_saju_data)

    assert built.prompt.index("사용자 초기 입력") < built.prompt.index("사주 명식 데이터")
    assert sample_request.initial_concern in built.prompt
    assert built.schema_name == "QuestionGenerationOutput"
    assert built.schema["$defs"]["DiagnosticQuestion"]["properties"]["intent_signal"]["minLength"] == 1


def test_final_prompt_requests_report_structure(sample_request, sample_saju_data) -> None:
    payload = sample_request.model_dump(mode="json")
    payload["answers"] = [
        {
            "question_id": f"q{index}",
            "question": f"질문 {index}",
            "answer": "조건을 확인하고 움직이고 싶습니다.",
            "selected_option_ids": ["A", "B"],
        }
        for index in range(1, 6)
    ]
    built = build_final_reading_prompt(FinalReadingRequest(**payload), sample_saju_data)

    assert "프리미엄 최종 사주풀이 리포트" in built.prompt
    assert "summary_cards" in built.prompt
    assert "deep_sections" in built.prompt
    assert "timing_points" in built.prompt
    assert "진단 질문 답변" in built.prompt
    assert "한 줄의 명쾌한 답" in built.prompt
    assert "사주 용어와 쉬운 번역" in built.prompt
    assert sample_request.initial_concern in built.prompt
    assert built.schema_name == "FinalReadingOutput"
    assert "summary_cards" in built.schema["properties"]
    assert "calculation_note" not in built.prompt
    assert "MVP" not in built.prompt


def test_calculation_note_does_not_expose_internal_mvp_wording() -> None:
    assert "MVP" not in calculation_note(Gender.male)
    assert "MVP" not in calculation_note(Gender.other)
