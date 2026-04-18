from app.schemas.saju import Gender
from app.services.prompt_builder import build_question_generation_prompt
from app.services.saju_features import build_daewoon, ten_god


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
