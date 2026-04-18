import pytest

from app.schemas.saju import (
    BirthInfo,
    CalendarType,
    Gender,
    GenerateQuestionsRequest,
    PillarDetail,
    SajuData,
)


@pytest.fixture
def sample_request() -> GenerateQuestionsRequest:
    return GenerateQuestionsRequest(
        name="테스트",
        gender=Gender.male,
        initial_concern="올해 이직을 해도 될까요?",
        birth=BirthInfo(
            calendar_type=CalendarType.solar,
            year=1990,
            month=10,
            day=10,
            hour=14,
            minute=30,
        ),
    )


@pytest.fixture
def sample_saju_data() -> SajuData:
    pillar = PillarDetail(
        pillar="甲子",
        stem="甲",
        branch="子",
        stem_element="wood",
        branch_element="water",
        stem_yin_yang="yang",
        branch_yin_yang="yang",
        stem_ten_god="비견",
        branch_ten_god="편인",
    )
    return SajuData(
        solar_date="1990-10-10",
        lunar_date={"lunar_year": 1990, "lunar_month": 8, "lunar_day": 22, "is_leap_month": False},
        birth_time="14:30",
        pillars={"year": pillar, "month": pillar, "day": pillar, "hour": pillar},
        day_master="甲",
        day_master_element="wood",
        elements_count={"wood": 4, "fire": 0, "earth": 0, "metal": 0, "water": 4},
        ten_gods={"year_stem": "비견"},
        daewoon=[],
        calculation_note="test",
        raw={},
    )
