from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CalendarType(str, Enum):
    solar = "solar"
    lunar = "lunar"


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class BirthInfo(BaseModel):
    calendar_type: CalendarType = CalendarType.solar
    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: int = Field(..., ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    is_leap_month: bool = False
    city: str = Field(default="Seoul", max_length=80)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    use_solar_time: bool = False

    @field_validator("city")
    @classmethod
    def strip_city(cls, value: str) -> str:
        return value.strip() or "Seoul"


class InitialProfile(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    gender: Gender = Gender.other
    birth: BirthInfo
    initial_concern: str = Field(..., min_length=4, max_length=1200)

    @field_validator("name", "initial_concern")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class GenerateQuestionsRequest(InitialProfile):
    pass


class PillarDetail(BaseModel):
    pillar: str
    stem: str
    branch: str
    stem_element: str
    branch_element: str
    stem_yin_yang: Literal["yang", "yin"]
    branch_yin_yang: Literal["yang", "yin"]
    stem_ten_god: str | None = None
    branch_ten_god: str | None = None


class DaewoonPeriod(BaseModel):
    order: int
    age_start: int
    age_end: int
    start_year: int
    pillar: str
    stem: str
    branch: str
    stem_ten_god: str
    main_element: str


class SajuData(BaseModel):
    solar_date: str
    lunar_date: dict[str, Any]
    birth_time: str
    pillars: dict[str, PillarDetail]
    day_master: str
    day_master_element: str
    elements_count: dict[str, int]
    ten_gods: dict[str, str]
    daewoon: list[DaewoonPeriod]
    calculation_note: str
    raw: dict[str, Any]


class QuestionOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern="^[A-D]$")
    label: str = Field(..., min_length=1, max_length=80)


class DiagnosticQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern="^q[1-5]$")
    type: Literal["single_choice", "short_text"]
    text: str = Field(..., min_length=8, max_length=160)
    options: list[QuestionOption] = Field(..., max_length=4)
    intent_signal: str = Field(
        ...,
        min_length=2,
        max_length=80,
        description="이 질문이 확인하려는 숨은 욕구. 예: 돈, 인정, 안전, 도피, 관계 정리",
    )

    @model_validator(mode="after")
    def validate_options_for_type(self) -> "DiagnosticQuestion":
        if self.type == "single_choice" and len(self.options) < 2:
            raise ValueError("single_choice questions must include at least 2 options")
        if self.type == "short_text" and self.options:
            raise ValueError("short_text questions must not include options")
        return self


class QuestionGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[DiagnosticQuestion] = Field(..., min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_question_ids(self) -> "QuestionGenerationOutput":
        expected_ids = [f"q{index}" for index in range(1, 6)]
        actual_ids = [question.id for question in self.questions]
        if actual_ids != expected_ids:
            raise ValueError("question ids must be q1, q2, q3, q4, q5 in order")
        return self


class ResponseMeta(BaseModel):
    provider: str
    model: str
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateQuestionsResponse(BaseModel):
    saju: SajuData
    questions: list[DiagnosticQuestion]
    meta: ResponseMeta


class QuestionAnswer(BaseModel):
    question_id: str = Field(..., pattern="^q[1-5]$")
    question: str = Field(..., min_length=1, max_length=180)
    answer: str = Field(..., min_length=1, max_length=400)
    selected_option_id: str | None = Field(default=None, pattern="^[A-D]$")

    @field_validator("question", "answer")
    @classmethod
    def strip_answer_text(cls, value: str) -> str:
        return value.strip()


class FinalReadingRequest(InitialProfile):
    answers: list[QuestionAnswer] = Field(..., min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_answer_ids(self) -> "FinalReadingRequest":
        expected_ids = [f"q{index}" for index in range(1, 6)]
        actual_ids = [answer.question_id for answer in self.answers]
        if actual_ids != expected_ids:
            raise ValueError("answers must be submitted as q1, q2, q3, q4, q5 in order")
        return self


class FinalReadingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    desired_conclusion: str = Field(..., min_length=4, max_length=160)
    core_message: str = Field(..., min_length=8, max_length=220)
    final_text: str = Field(..., min_length=80, max_length=3500)
    answer_signals: list[str] = Field(..., min_length=3, max_length=5)
    saju_basis: list[str] = Field(..., min_length=3, max_length=5)
    action_steps: list[str] = Field(..., min_length=2, max_length=4)
    caution: str = Field(..., min_length=8, max_length=240)


class FinalReadingResponse(BaseModel):
    saju: SajuData
    reading: FinalReadingOutput
    meta: ResponseMeta


class SajuOnlyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    gender: Gender = Gender.other
    birth: BirthInfo

    @field_validator("name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class SajuOnlyResponse(BaseModel):
    saju: SajuData
