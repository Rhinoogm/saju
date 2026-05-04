from app.schemas.saju import FinalReadingRequest, GenerateNextQuestionRequest, Gender
from app.services.prompt_builder import (
    FINAL_SYSTEM_PROMPT_DIRECT,
    FINAL_SYSTEM_PROMPT_TRADITIONAL,
    build_final_reading_prompt,
    build_question_generation_prompt,
)
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
    assert "desired_answer" in built.prompt
    assert "saju_insight" in built.prompt
    assert "clear_solution" in built.prompt
    assert "secret_talent" in built.prompt
    assert "period_guidance" in built.prompt
    assert "share_card" in built.prompt
    assert "strengths" in built.prompt
    assert "작은 체크 노트" in built.prompt
    assert "고객이 진짜 듣고 싶었던 말" in built.prompt
    assert "상담 분석 라벨을 절대 노출하지 않는다" in built.prompt
    assert "summary" in built.prompt
    assert "detail" in built.prompt
    assert "`body`를 절대 만들지 않는다" in built.prompt
    assert "스키마에 없는 추가 필드" in built.prompt
    assert "`caution`은 객체가 아니라 문자열 필드" in built.prompt
    assert "<qna_data>" in built.prompt
    assert "<budget_and_quality_control>" in built.prompt
    assert "구체 날짜" in built.prompt
    assert "이번 주" in built.prompt
    assert "여러 추천 목록처럼 늘어놓지 않는다" in built.prompt
    assert "데이터 격리(Anti-Anchoring)" in built.prompt
    assert "answer_signal_summary" not in built.prompt
    assert "situation_mirror" not in built.prompt
    assert "luck_recipe" not in built.prompt
    assert sample_request.initial_concern in built.prompt
    assert built.schema_name == "FinalReadingOutput"
    assert "desired_answer" in built.schema["properties"]
    assert "saju_insight" in built.schema["properties"]
    assert "clear_solution" in built.schema["properties"]
    assert "secret_talent" in built.schema["properties"]
    assert "period_guidance" in built.schema["properties"]
    assert "share_card" in built.schema["properties"]
    share_card_properties = built.schema["$defs"]["ShareCard"]["properties"]
    assert "strengths" in share_card_properties
    assert share_card_properties["strengths"]["minItems"] == 2
    assert share_card_properties["strengths"]["maxItems"] == 3
    assert "situation_mirror" not in built.schema["properties"]
    assert "luck_recipe" not in built.schema["properties"]
    assert "answer_signal_summary" not in built.schema["properties"]
    care_section_properties = built.schema["$defs"]["ReadingCareSection"]["properties"]
    assert "summary" in care_section_properties
    assert "detail" in care_section_properties
    assert "body" not in care_section_properties
    assert care_section_properties["detail"]["minLength"] == 200
    assert care_section_properties["detail"]["maxLength"] == 1200
    assert "고급 문학 에세이나 철학서" in FINAL_SYSTEM_PROMPT_TRADITIONAL
    assert "오만한 하대 화법" in FINAL_SYSTEM_PROMPT_DIRECT
    assert "hashtags" not in built.schema["properties"]
    assert "calculation_note" not in built.prompt
    assert '"birth"' not in built.prompt
    assert '"selected_option_ids"' not in built.prompt
    assert '"selected_option_id"' not in built.prompt
    assert "MVP" not in built.prompt


def test_calculation_note_does_not_expose_internal_mvp_wording() -> None:
    assert "MVP" not in calculation_note(Gender.male)
    assert "MVP" not in calculation_note(Gender.other)
