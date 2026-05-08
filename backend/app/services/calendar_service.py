from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sajupy import calculate_saju, lunar_to_solar, solar_to_lunar

from app.schemas.saju import CurrentLuck, InitialProfile, SajuData
from app.services.saju_features import (
    BRANCHES,
    STEMS,
    build_time_luck_pillar,
    build_daewoon,
    calculation_note,
    count_elements,
    dominant_ten_god as select_dominant_ten_god,
    enrich_pillars,
    flatten_ten_gods,
    score_ten_gods,
)
from app.services.yonghuishin import analyze_yonghuishin


class CalendarCalculationError(ValueError):
    pass


class CalendarService:
    def calculate(self, request: InitialProfile) -> SajuData:
        try:
            solar_birth = self._normalize_solar_birth(request)
            lunar_date = solar_to_lunar(
                solar_birth["year"],
                solar_birth["month"],
                solar_birth["day"],
            )
            raw_saju = self._calculate_raw_saju(request, solar_birth)
        except Exception as exc:
            raise CalendarCalculationError(str(exc)) from exc

        pillars = enrich_pillars(raw_saju)
        day_master = raw_saju["day_stem"]
        ten_gods = flatten_ten_gods(pillars)
        ten_god_scores = score_ten_gods(ten_gods)
        yonghuishin = analyze_yonghuishin(pillars, day_master)

        return SajuData(
            solar_date=f"{solar_birth['year']:04d}-{solar_birth['month']:02d}-{solar_birth['day']:02d}",
            lunar_date=lunar_date,
            birth_time=raw_saju.get("birth_time", f"{request.birth.hour:02d}:{request.birth.minute:02d}"),
            pillars=pillars,
            day_master=day_master,
            day_master_element=STEMS[day_master]["element"],
            elements_count=count_elements(pillars),
            ten_gods=ten_gods,
            ten_god_scores=ten_god_scores,
            dominant_ten_god=ten_god_scores[0] if ten_god_scores else select_dominant_ten_god(ten_gods),
            daewoon=build_daewoon(raw_saju, request.gender),
            current_luck=self._build_current_luck(day_master),
            yonghuishin=yonghuishin,
            calculation_note=calculation_note(request.gender),
            raw=_json_safe(raw_saju),
        )

    def _normalize_solar_birth(self, request: InitialProfile) -> dict[str, int]:
        birth = request.birth
        if birth.calendar_type.value == "solar":
            return {"year": birth.year, "month": birth.month, "day": birth.day}

        converted = lunar_to_solar(
            birth.year,
            birth.month,
            birth.day,
            is_leap_month=birth.is_leap_month,
        )
        return {
            "year": int(converted["solar_year"]),
            "month": int(converted["solar_month"]),
            "day": int(converted["solar_day"]),
        }

    def _calculate_raw_saju(self, request: InitialProfile, solar_birth: dict[str, int]) -> dict[str, Any]:
        birth = request.birth
        kwargs: dict[str, Any] = {
            "year": solar_birth["year"],
            "month": solar_birth["month"],
            "day": solar_birth["day"],
            "hour": birth.hour,
            "minute": birth.minute,
            "use_solar_time": birth.use_solar_time,
            "utc_offset": 9,
            "early_zi_time": True,
        }
        if birth.use_solar_time:
            if birth.longitude is not None:
                kwargs["longitude"] = birth.longitude
            else:
                kwargs["city"] = birth.city or "Seoul"

        return calculate_saju(**kwargs)

    def _build_current_luck(self, day_master: str, reference_date: date | None = None) -> CurrentLuck:
        reference = reference_date or datetime.now(ZoneInfo("Asia/Seoul")).date()
        next_year, next_month = _next_month(reference.year, reference.month)
        next_month_date = date(next_year, next_month, 15)

        annual_raw = _calculate_reference_saju(reference)
        next_month_raw = _calculate_reference_saju(next_month_date)

        return CurrentLuck(
            reference_date=reference.isoformat(),
            annual=build_time_luck_pillar(
                annual_raw,
                key="year",
                day_master=day_master,
                label=f"{reference.year}년 세운",
                year=reference.year,
                month=None,
                representative_date=reference.isoformat(),
            ),
            next_month=build_time_luck_pillar(
                next_month_raw,
                key="month",
                day_master=day_master,
                label=f"{next_year}년 {next_month}월 월운",
                year=next_year,
                month=next_month,
                representative_date=next_month_date.isoformat(),
            ),
        )


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _calculate_reference_saju(target_date: date) -> dict[str, Any]:
    return calculate_saju(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=12,
        minute=0,
        use_solar_time=False,
        utc_offset=9,
        early_zi_time=True,
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value
