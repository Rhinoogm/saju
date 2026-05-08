from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


OptionId = Annotated[str, Field(pattern="^[A-D]$")]
OPTION_MARKER_RE = re.compile(r"\s*(?:\([A-D]\)|[A-D][.)]|[①②③④])\s*")


class CalendarType(str, Enum):
    solar = "solar"
    lunar = "lunar"


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class ReadingStyle(str, Enum):
    traditional = "traditional"
    empathetic = "empathetic"
    direct = "direct"


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


class TimeLuckPillar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    year: int
    month: int | None = None
    representative_date: str
    pillar: str
    stem: str
    branch: str
    stem_element: str
    branch_element: str
    stem_yin_yang: Literal["yang", "yin"]
    branch_yin_yang: Literal["yang", "yin"]
    stem_ten_god: str
    branch_ten_god: str


class CurrentLuck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_date: str
    annual: TimeLuckPillar
    next_month: TimeLuckPillar


class TenGodScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    score: float
    count: int
    positions: list[str] = Field(default_factory=list, max_length=8)


class YonghuishinCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element: str
    score: float | None = None
    reason: str


class GeokgukYongshinCandidate(YonghuishinCandidate):
    ten_god: str | None = None
    stem: str | None = None


class DayMasterStrength(BaseModel):
    model_config = ConfigDict(extra="forbid")

    support_score: float
    drain_score: float
    strength_index: float
    label: str
    evidence: list[str] = Field(..., min_length=1, max_length=5)


class GeokgukMonthSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month_branch: str
    selected_hidden_stem: str
    ten_god: str
    transmitted: bool


class GeokgukAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    selected_from_month: GeokgukMonthSource
    confidence: float
    damage: list[str] = Field(default_factory=list, max_length=5)


class SpecialGeokCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    confidence: float
    reason: str


class YongshinAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eokbu_yongshin: list[YonghuishinCandidate] = Field(default_factory=list)
    geokguk_yongshin: list[GeokgukYongshinCandidate] = Field(default_factory=list)
    johwu_yongshin: list[YonghuishinCandidate] = Field(default_factory=list)
    final_yongshin: list[YonghuishinCandidate] = Field(..., min_length=1, max_length=2)
    huishin: list[YonghuishinCandidate] = Field(..., min_length=1, max_length=2)
    gishin: list[YonghuishinCandidate] = Field(..., min_length=1, max_length=2)


class YonghuishinInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    strength_reading: str
    geokguk_reading: str
    yongshin_reading: str


class YonghuishinAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_power: dict[str, float]
    strength: DayMasterStrength
    geokguk: GeokgukAnalysis
    special_geok_candidates: list[SpecialGeokCandidate] = Field(default_factory=list, max_length=3)
    yongshin: YongshinAnalysis
    interpretation: YonghuishinInterpretation


class SajuData(BaseModel):
    solar_date: str
    lunar_date: dict[str, Any]
    birth_time: str
    pillars: dict[str, PillarDetail]
    day_master: str
    day_master_element: str
    elements_count: dict[str, int]
    ten_gods: dict[str, str]
    ten_god_scores: list[TenGodScore]
    dominant_ten_god: TenGodScore
    daewoon: list[DaewoonPeriod]
    current_luck: CurrentLuck
    yonghuishin: YonghuishinAnalysis
    calculation_note: str
    raw: dict[str, Any]


class QuestionOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern="^[A-D]$")
    label: str = Field(..., min_length=1, max_length=120)


class DiagnosticQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern="^q[1-5]$")
    type: Literal["single_choice"]
    text: str = Field(..., min_length=8, max_length=140)
    options: list[QuestionOption] = Field(..., min_length=4, max_length=4)
    intent_signal: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="이 질문이 확인하려는 상담 단계와 숨은 욕구.",
    )

    @model_validator(mode="after")
    def validate_options_for_type(self) -> "DiagnosticQuestion":
        if [option.id for option in self.options] != ["A", "B", "C", "D"]:
            raise ValueError("single_choice questions must include exactly four options with ids A, B, C, D")
        marker = OPTION_MARKER_RE.search(self.text)
        if marker is not None:
            self.text = self.text[: marker.start()].rstrip()
        if len(self.text) < 8:
            raise ValueError("question text must not be only option labels")
        return self


class QuestionGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: DiagnosticQuestion

    def require_question_id(self, expected_id: str) -> "QuestionGenerationOutput":
        if self.question.id != expected_id:
            raise ValueError(f"question id must be {expected_id}")
        return self


class ResponseMeta(BaseModel):
    provider: str
    model: str
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateQuestionsResponse(BaseModel):
    saju: SajuData
    question: DiagnosticQuestion
    meta: ResponseMeta


class QuestionAnswer(BaseModel):
    question_id: str = Field(..., pattern="^q[1-5]$")
    question: str = Field(..., min_length=1, max_length=180)
    answer: str = Field(..., min_length=1, max_length=400)
    selected_option_ids: list[OptionId] = Field(default_factory=list, max_length=1)
    selected_option_id: OptionId | None = None

    @field_validator("question", "answer")
    @classmethod
    def strip_answer_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def normalize_selected_option_ids(self) -> "QuestionAnswer":
        if self.selected_option_id is not None and not self.selected_option_ids:
            self.selected_option_ids = [self.selected_option_id]
        self.selected_option_ids = list(dict.fromkeys(self.selected_option_ids))
        return self


def _validate_answer_sequence(answers: list[QuestionAnswer], *, max_count: int) -> None:
    actual_ids = [answer.question_id for answer in answers]
    expected_ids = [f"q{index}" for index in range(1, len(actual_ids) + 1)]
    if actual_ids != expected_ids:
        raise ValueError(f"answers must include {', '.join(expected_ids)} in order")
    if len(actual_ids) > max_count:
        raise ValueError(f"answers must include at most q1 through q{max_count}")
    if len(set(actual_ids)) != len(actual_ids):
        raise ValueError("answers must not contain duplicate question ids")


class GenerateNextQuestionRequest(InitialProfile):
    answers: list[QuestionAnswer] = Field(..., min_length=1, max_length=4)

    @model_validator(mode="after")
    def validate_answer_ids(self) -> "GenerateNextQuestionRequest":
        _validate_answer_sequence(self.answers, max_count=4)
        return self


class GenerateNextQuestionResponse(BaseModel):
    question: DiagnosticQuestion
    meta: ResponseMeta


class FinalReadingRequest(InitialProfile):
    reading_style: ReadingStyle = ReadingStyle.traditional
    answers: list[QuestionAnswer] = Field(..., min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_answer_ids(self) -> "FinalReadingRequest":
        _validate_answer_sequence(self.answers, max_count=5)
        return self


class CompassSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(..., min_length=8, max_length=90)
    basis: str = Field(..., min_length=40, max_length=260)
    solution: str = Field(..., min_length=40, max_length=280)
    strength_animal: str = Field(..., min_length=8, max_length=90)


class ManseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(..., min_length=8, max_length=90)
    energy_overview: str = Field(..., min_length=40, max_length=240)
    key_traits: list[str] = Field(..., min_length=3, max_length=4)


class DualReadingSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=4, max_length=44)
    headline: str = Field(..., min_length=8, max_length=100)
    body: str = Field(..., min_length=80, max_length=520)


class DualReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weapon: DualReadingSection
    growth_hint: DualReadingSection


class HealingCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metaphor_sentence: str = Field(..., min_length=8, max_length=70)
    affirmation: str = Field(..., min_length=8, max_length=90)
    lucky_element: str = Field(..., min_length=1, max_length=20)
    color: str = Field(..., min_length=2, max_length=40)
    direction: str = Field(..., min_length=1, max_length=20)
    ritual: str = Field(..., min_length=20, max_length=180)
    interpretation: str = Field(..., min_length=60, max_length=360)


class SecretDoor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unexplored_area: str = Field(..., min_length=2, max_length=40)
    next_month_signal: str = Field(..., min_length=20, max_length=180)
    teaser: str = Field(..., min_length=50, max_length=320)


class FinalReadingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_title: str = Field(..., min_length=4, max_length=80)
    compass_summary: CompassSummary
    manse_summary: ManseSummary
    dual_reading: DualReading
    healing_card: HealingCard
    secret_door: SecretDoor
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
