import pytest

from app.schemas.saju import (
    BirthInfo,
    CalendarType,
    CurrentLuck,
    Gender,
    GenerateQuestionsRequest,
    PillarDetail,
    SajuData,
    TenGodScore,
    TimeLuckPillar,
)
from app.services.yonghuishin import analyze_yonghuishin


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
    pillars = {"year": pillar, "month": pillar, "day": pillar, "hour": pillar}
    luck_pillar = TimeLuckPillar(
        label="2026년 세운",
        year=2026,
        month=None,
        representative_date="2026-05-05",
        pillar="丙午",
        stem="丙",
        branch="午",
        stem_element="fire",
        branch_element="fire",
        stem_yin_yang="yang",
        branch_yin_yang="yang",
        stem_ten_god="식신",
        branch_ten_god="식신",
    )
    next_month_luck = TimeLuckPillar(
        label="2026년 6월 월운",
        year=2026,
        month=6,
        representative_date="2026-06-15",
        pillar="甲午",
        stem="甲",
        branch="午",
        stem_element="wood",
        branch_element="fire",
        stem_yin_yang="yang",
        branch_yin_yang="yang",
        stem_ten_god="비견",
        branch_ten_god="식신",
    )
    return SajuData(
        solar_date="1990-10-10",
        lunar_date={"lunar_year": 1990, "lunar_month": 8, "lunar_day": 22, "is_leap_month": False},
        birth_time="14:30",
        pillars=pillars,
        day_master="甲",
        day_master_element="wood",
        elements_count={"wood": 4, "fire": 0, "earth": 0, "metal": 0, "water": 4},
        ten_gods={"year_stem": "비견"},
        ten_god_scores=[TenGodScore(name="비견", score=0.8, count=1, positions=["year_stem"])],
        dominant_ten_god=TenGodScore(name="비견", score=0.8, count=1, positions=["year_stem"]),
        daewoon=[],
        current_luck=CurrentLuck(reference_date="2026-05-05", annual=luck_pillar, next_month=next_month_luck),
        yonghuishin=analyze_yonghuishin(pillars, "甲"),
        calculation_note="test",
        raw={},
    )
