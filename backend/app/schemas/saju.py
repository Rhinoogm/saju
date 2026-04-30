from __future__ import annotations

import re
from enum import Enum
from uuid import UUID
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


class ConcernCategory(str, Enum):
    romance = "romance"
    career = "career"
    finance = "finance"
    health = "health"
    academics = "academics"
    others = "others"


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
    label: str = Field(..., min_length=1, max_length=120)


class DiagnosticQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., pattern="^q[1-8]$")
    type: Literal["single_choice", "short_text"]
    text: str = Field(..., min_length=8, max_length=90)
    options: list[QuestionOption] = Field(..., max_length=4)
    intent_signal: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="이 질문이 확인하려는 숨은 욕구. 예: 돈, 인정, 안전, 도피, 관계 정리",
    )

    @model_validator(mode="after")
    def validate_options_for_type(self) -> "DiagnosticQuestion":
        if self.type == "single_choice" and len(self.options) < 2:
            raise ValueError("single_choice questions must include at least 2 options")
        if self.type == "short_text" and self.options:
            raise ValueError("short_text questions must not include options")
        if self.type == "single_choice":
            marker = OPTION_MARKER_RE.search(self.text)
            if marker is not None:
                self.text = self.text[: marker.start()].rstrip()
            if len(self.text) < 8:
                raise ValueError("question text must not be only option labels")
        return self


class QuestionGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[DiagnosticQuestion] = Field(..., min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_question_ids(self) -> "QuestionGenerationOutput":
        expected_ids = ["q5", "q6", "q7"]
        actual_ids = [question.id for question in self.questions]
        if actual_ids != expected_ids:
            raise ValueError("question ids must be q5, q6, q7 in order")
        if any(question.type != "single_choice" for question in self.questions):
            raise ValueError("custom questions must be single_choice")
        if any([option.id for option in question.options] != ["A", "B", "C", "D"] for question in self.questions):
            raise ValueError("custom questions must include exactly four options with ids A, B, C, D")
        return self


class ResponseMeta(BaseModel):
    provider: str
    model: str
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateQuestionsResponse(BaseModel):
    saju: SajuData
    category: ConcernCategory
    category_label: str
    questions: list[DiagnosticQuestion]
    meta: ResponseMeta


class QuestionAnswer(BaseModel):
    question_id: str = Field(..., pattern="^q[1-8]$")
    question: str = Field(..., min_length=1, max_length=180)
    answer: str = Field(..., min_length=1, max_length=400)
    selected_option_ids: list[OptionId] = Field(default_factory=list, max_length=4)
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


class GenerateCustomQuestionsRequest(InitialProfile):
    category: ConcernCategory
    fixed_answers: list[QuestionAnswer] = Field(..., min_length=3, max_length=4)

    @model_validator(mode="after")
    def validate_fixed_answer_ids(self) -> "GenerateCustomQuestionsRequest":
        actual_ids = [answer.question_id for answer in self.fixed_answers]
        required_ids = ["q1", "q2", "q3"]
        if actual_ids[:3] != required_ids:
            raise ValueError("fixed_answers must start with q1, q2, q3 in order")
        if len(actual_ids) == 4 and actual_ids[3] != "q4":
            raise ValueError("the optional fixed answer must be q4")
        if len(set(actual_ids)) != len(actual_ids):
            raise ValueError("fixed_answers must not contain duplicate question ids")
        return self


class GenerateCustomQuestionsResponse(BaseModel):
    questions: list[DiagnosticQuestion]
    meta: ResponseMeta


class FinalReadingRequest(InitialProfile):
    category: ConcernCategory | None = None
    reading_style: ReadingStyle = ReadingStyle.traditional
    answers: list[QuestionAnswer] = Field(..., min_length=6, max_length=8)

    @model_validator(mode="after")
    def validate_answer_ids(self) -> "FinalReadingRequest":
        actual_ids = [answer.question_id for answer in self.answers]
        required_ids = ["q1", "q2", "q3", "q5", "q6", "q7"]
        if len(set(actual_ids)) != len(actual_ids):
            raise ValueError("answers must not contain duplicate question ids")
        if [question_id for question_id in actual_ids if question_id not in {"q4", "q8"}] != required_ids:
            raise ValueError("answers must include q1, q2, q3, q5, q6, q7 in order, with optional q4 and q8")
        if "q4" in actual_ids and actual_ids.index("q4") != 3:
            raise ValueError("optional q4 answer must appear after q3")
        if "q8" in actual_ids and actual_ids.index("q8") != len(actual_ids) - 1:
            raise ValueError("optional q8 answer must appear after q7")
        return self


class ReadingSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=2, max_length=36)
    body: str = Field(..., min_length=60, max_length=700)


class ReadingCareSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=2, max_length=36)
    headline: str = Field(..., min_length=4, max_length=100)
    summary: str = Field(..., min_length=20, max_length=220)
    detail: str = Field(..., min_length=200, max_length=1200)


class LuckRecipeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., min_length=2, max_length=20)
    item: str = Field(..., min_length=1, max_length=40)
    reason: str = Field(..., min_length=10, max_length=180)


class FinalReadingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_title: str = Field(..., min_length=4, max_length=80)
    core_message: str = Field(..., min_length=8, max_length=120)
    situation_mirror: ReadingCareSection
    saju_insight: ReadingCareSection
    clear_solution: ReadingCareSection
    saju_vibe: ReadingCareSection
    secret_talent: ReadingCareSection
    answer_signals: list[str] = Field(..., min_length=3, max_length=5)
    answer_signal_summary: str = Field(..., min_length=30, max_length=180)
    saju_basis: list[str] = Field(..., min_length=3, max_length=5)
    timing_points: list[str] = Field(..., min_length=3, max_length=3)
    luck_recipe: list[LuckRecipeItem] = Field(..., min_length=4, max_length=4)
    re_engagement_hook: ReadingSection
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


class ReadingSessionStatus(str, Enum):
    payment_required = "payment_required"
    paid = "paid"
    fixed_questions_ready = "fixed_questions_ready"
    custom_questions_ready = "custom_questions_ready"
    final_ready = "final_ready"
    failed = "failed"


class ReadingSessionCreateRequest(InitialProfile):
    reading_style: ReadingStyle = ReadingStyle.traditional


class ReadingSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    order_id: UUID | None = None
    status: ReadingSessionStatus
    reading_style: ReadingStyle
    initial_profile: InitialProfile
    saju: SajuData | None = None
    category: ConcernCategory | None = None
    category_label: str | None = None
    fixed_questions: list[DiagnosticQuestion] | None = None
    fixed_answers: list[QuestionAnswer] | None = None
    custom_questions: list[DiagnosticQuestion] | None = None
    custom_answers: list[QuestionAnswer] | None = None
    final_result: FinalReadingResponse | None = None
    created_at: str | None = None
    updated_at: str | None = None


class FixedAnswersRequest(BaseModel):
    fixed_answers: list[QuestionAnswer] = Field(..., min_length=3, max_length=4)

    @model_validator(mode="after")
    def validate_fixed_answer_ids(self) -> "FixedAnswersRequest":
        actual_ids = [answer.question_id for answer in self.fixed_answers]
        required_ids = ["q1", "q2", "q3"]
        if actual_ids[:3] != required_ids:
            raise ValueError("fixed_answers must start with q1, q2, q3 in order")
        if len(actual_ids) == 4 and actual_ids[3] != "q4":
            raise ValueError("the optional fixed answer must be q4")
        if len(set(actual_ids)) != len(actual_ids):
            raise ValueError("fixed_answers must not contain duplicate question ids")
        return self


class CustomAnswersRequest(BaseModel):
    custom_answers: list[QuestionAnswer] = Field(..., min_length=3, max_length=4)

    @model_validator(mode="after")
    def validate_custom_answer_ids(self) -> "CustomAnswersRequest":
        actual_ids = [answer.question_id for answer in self.custom_answers]
        required_ids = ["q5", "q6", "q7"]
        if actual_ids[:3] != required_ids:
            raise ValueError("custom_answers must start with q5, q6, q7 in order")
        if len(actual_ids) == 4 and actual_ids[3] != "q8":
            raise ValueError("the optional custom answer must be q8")
        if len(set(actual_ids)) != len(actual_ids):
            raise ValueError("custom_answers must not contain duplicate question ids")
        return self


class CheckoutRequest(BaseModel):
    session_id: UUID
    product_code: str = Field(default="SAJU_FULL_READING", min_length=1, max_length=80)


class CheckoutResponse(BaseModel):
    order_id: UUID
    payment_id: str
    store_id: str
    channel_key: str
    order_name: str
    total_amount: int
    currency: str = "KRW"
    notice_urls: list[str]


class PaymentCompleteRequest(BaseModel):
    payment_id: str = Field(..., min_length=1, max_length=120)
    tx_id: str | None = Field(default=None, max_length=120)


class PaymentCompleteResponse(BaseModel):
    order_id: UUID
    session_id: UUID | None = None
    payment_id: str
    status: str
    credit_status: str | None = None


class AccountMeResponse(BaseModel):
    id: UUID
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    provider: str | None = None


class AccountOrderResponse(BaseModel):
    id: UUID
    payment_id: str
    product_code: str
    order_name: str
    amount_krw: int
    currency: str
    status: str
    paid_at: str | None = None
    created_at: str | None = None


class AccountReadingResponse(BaseModel):
    id: UUID
    status: ReadingSessionStatus
    reading_style: ReadingStyle
    order_id: UUID | None = None
    created_at: str | None = None
    updated_at: str | None = None
    has_final_result: bool = False
