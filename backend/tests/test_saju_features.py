from app.schemas.saju import FinalReadingRequest, GenerateCustomQuestionsRequest, Gender
from app.services.prompt_builder import build_custom_question_generation_prompt, build_final_reading_prompt
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


def test_custom_question_prompt_uses_initial_concern_and_fixed_answers(sample_request) -> None:
    payload = sample_request.model_dump(mode="json")
    payload["category"] = "career"
    payload["fixed_answers"] = [
        {
            "question_id": "q1",
            "question": "새롭게 원하는 방향은 어떤 것인가요?",
            "answer": "지금보다 더 성장할 수 있고 가슴 뛰는 새로운 일을 찾아보고 싶어요",
            "selected_option_ids": ["D"],
            "selected_option_id": "D",
        },
        {
            "question_id": "q2",
            "question": "이 목표를 향해 어떤 준비를 하고 계신가요?",
            "answer": "새로운 도전을 위해 이력서를 다듬고 채용 공고를 눈여겨보고 있어요",
            "selected_option_ids": ["A"],
        },
        {
            "question_id": "q3",
            "question": "일상에서 가장 크게 달라지길 기대하는 부분은 무엇인가요?",
            "answer": "내 능력을 온전히 발휘하고 있다는 깊은 성취감",
            "selected_option_ids": ["C"],
        },
    ]
    built = build_custom_question_generation_prompt(GenerateCustomQuestionsRequest(**payload))

    assert built.prompt.index("사용자 초기 입력") < built.prompt.index("고정 질문 답변")
    assert sample_request.initial_concern in built.prompt
    assert "직업" in built.prompt
    assert "내 능력을 온전히 발휘하고 있다는 깊은 성취감" in built.prompt
    assert "options를 정확히 4개" in built.prompt
    assert "사주 명식 데이터" not in built.prompt
    assert '"birth"' not in built.prompt
    assert '"selected_option_ids"' not in built.prompt
    assert '"selected_option_id"' not in built.prompt
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
        for index in [1, 2, 3, 5, 6, 7]
    ]
    payload["category"] = "career"
    built = build_final_reading_prompt(FinalReadingRequest(**payload), sample_saju_data)

    assert "프리미엄 맞춤형 사주 결과지" in built.prompt
    assert "hashtags" in built.prompt
    assert "situation_mirror" in built.prompt
    assert "saju_insight" in built.prompt
    assert "clear_solution" in built.prompt
    assert "re_engagement_hook" in built.prompt
    assert "saju_vibe" in built.prompt
    assert "luck_recipe" in built.prompt
    assert "전문가 데이터" in built.prompt
    assert "행운의 레시피" in built.prompt
    assert "timing_points" in built.prompt
    assert "고정 질문 및 맞춤 심층 질문 답변" in built.prompt
    assert "출력 예산" in built.prompt
    assert "감정 과잉 및 바이어스" in built.prompt
    assert "지금 마음이 향하는 곳" in built.prompt
    assert "answer_signal_summary" in built.prompt
    assert "지금 필요한 선택" in built.prompt
    assert "타고난 결" in built.prompt
    assert "강점으로 바뀌는 지점" in built.prompt
    assert "다음엔 이런 것도 궁금해질 거예요" in built.prompt
    assert sample_request.initial_concern in built.prompt
    assert built.schema_name == "FinalReadingOutput"
    assert "situation_mirror" in built.schema["properties"]
    assert "saju_insight" in built.schema["properties"]
    assert "clear_solution" in built.schema["properties"]
    assert "re_engagement_hook" in built.schema["properties"]
    assert "luck_recipe" in built.schema["properties"]
    assert "answer_signal_summary" in built.schema["properties"]
    assert "calculation_note" not in built.prompt
    assert '"birth"' not in built.prompt
    assert '"selected_option_ids"' not in built.prompt
    assert '"selected_option_id"' not in built.prompt
    assert "MVP" not in built.prompt


def test_calculation_note_does_not_expose_internal_mvp_wording() -> None:
    assert "MVP" not in calculation_note(Gender.male)
    assert "MVP" not in calculation_note(Gender.other)
