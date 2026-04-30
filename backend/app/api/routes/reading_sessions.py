from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.routes.saju import (
    _call_llm,
    _invalid_final_reading_http_error,
    _meta,
    _parse_final_reading,
    _parse_questions,
    LLMInvalidOutputError,
    get_calendar_service,
    get_llm_provider,
    get_prompt_store,
)
from app.config import Settings, get_settings
from app.schemas.saju import (
    CustomAnswersRequest,
    DiagnosticQuestion,
    FinalReadingRequest,
    FinalReadingResponse,
    FixedAnswersRequest,
    GenerateCustomQuestionsRequest,
    GenerateCustomQuestionsResponse,
    GenerateQuestionsResponse,
    ReadingSessionCreateRequest,
    ReadingSessionResponse,
    ResponseMeta,
)
from app.services.calendar_service import CalendarCalculationError, CalendarService
from app.services.concern_questions import CONCERN_CATEGORY_LABELS, SUBJECTIVE_QUESTION_TEXT, classify_initial_concern, fixed_questions_for_category
from app.services.llm.base import LLMProvider
from app.services.prompt_builder import build_custom_question_generation_prompt, build_final_reading_prompt
from app.services.prompt_store import PromptStore
from app.services.rate_limiter import enforce_llm_rate_limit
from app.services.reading_repository import ReadingRepository, get_reading_repository
from app.services.supabase_auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api/reading-sessions", tags=["reading-sessions"])


@router.post("", response_model=ReadingSessionResponse)
async def create_reading_session(
    payload: ReadingSessionCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
) -> ReadingSessionResponse:
    return await repo.create_session(current_user.id, payload)


@router.get("/{session_id}", response_model=ReadingSessionResponse)
async def get_reading_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
) -> ReadingSessionResponse:
    session = await repo.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return session


@router.post("/{session_id}/generate-questions", response_model=GenerateQuestionsResponse)
async def generate_session_questions(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
    calendar_service: CalendarService = Depends(get_calendar_service),
) -> GenerateQuestionsResponse:
    session = await _require_paid_session(repo, current_user.id, session_id)
    try:
        saju = calendar_service.calculate(session.initial_profile)
    except CalendarCalculationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    category = classify_initial_concern(session.initial_profile.initial_concern)
    questions = fixed_questions_for_category(category)
    result = GenerateQuestionsResponse(
        saju=saju,
        category=category,
        category_label=CONCERN_CATEGORY_LABELS[category],
        questions=questions,
        meta=ResponseMeta(provider="system", model="fixed-question-bank", raw_metadata={"category": category.value}),
    )
    await repo.save_fixed_questions(current_user.id, session_id, result)
    return result


@router.put("/{session_id}/fixed-answers", response_model=ReadingSessionResponse)
async def save_fixed_answers(
    session_id: UUID,
    payload: FixedAnswersRequest,
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
) -> ReadingSessionResponse:
    await _require_paid_session(repo, current_user.id, session_id)
    await repo.save_fixed_answers(current_user.id, session_id, payload)
    session = await repo.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return session


@router.post(
    "/{session_id}/generate-custom-questions",
    response_model=GenerateCustomQuestionsResponse,
    dependencies=[Depends(enforce_llm_rate_limit)],
)
async def generate_session_custom_questions(
    session_id: UUID,
    request: Request,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
    settings: Settings = Depends(get_settings),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    prompt_store: PromptStore | None = Depends(get_prompt_store),
) -> GenerateCustomQuestionsResponse:
    session = await _require_paid_session(repo, current_user.id, session_id)
    if session.category is None or session.fixed_answers is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Fixed questions and answers are required")

    payload = GenerateCustomQuestionsRequest(
        **session.initial_profile.model_dump(),
        category=session.category,
        fixed_answers=session.fixed_answers,
    )
    built_prompt = build_custom_question_generation_prompt(payload, prompt_store=prompt_store)
    llm_response = await _call_llm(
        llm_provider,
        request=request,
        http_response=response,
        settings=settings,
        system=built_prompt.system,
        prompt=built_prompt.prompt,
        schema=built_prompt.schema,
        schema_name=built_prompt.schema_name,
        max_output_tokens=settings.llm_custom_questions_max_output_tokens,
    )
    output = _parse_questions(llm_response.content)
    questions = [
        *output.questions,
        DiagnosticQuestion(
            id="q8",
            type="short_text",
            text=SUBJECTIVE_QUESTION_TEXT,
            options=[],
            intent_signal="추가 설명",
        ),
    ]
    result = GenerateCustomQuestionsResponse(questions=questions, meta=_meta(llm_response))
    await repo.save_custom_questions(current_user.id, session_id, result)
    return result


@router.put("/{session_id}/custom-answers", response_model=ReadingSessionResponse)
async def save_custom_answers(
    session_id: UUID,
    payload: CustomAnswersRequest,
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
) -> ReadingSessionResponse:
    await _require_paid_session(repo, current_user.id, session_id)
    await repo.save_custom_answers(current_user.id, session_id, payload)
    session = await repo.get_session(current_user.id, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return session


@router.post(
    "/{session_id}/final-reading",
    response_model=FinalReadingResponse,
    dependencies=[Depends(enforce_llm_rate_limit)],
)
async def generate_session_final_reading(
    session_id: UUID,
    request: Request,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    repo: ReadingRepository = Depends(get_reading_repository),
    calendar_service: CalendarService = Depends(get_calendar_service),
    settings: Settings = Depends(get_settings),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    prompt_store: PromptStore | None = Depends(get_prompt_store),
) -> FinalReadingResponse:
    session = await _require_owned_session(repo, current_user.id, session_id)
    if session.final_result is not None:
        return session.final_result
    if not await repo.has_available_credit(current_user.id, session_id):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Payment required")
    if session.category is None or session.fixed_answers is None or session.custom_answers is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Questions and answers are required")

    answers = [*session.fixed_answers, *session.custom_answers]
    payload = FinalReadingRequest(
        **session.initial_profile.model_dump(),
        category=session.category,
        reading_style=session.reading_style,
        answers=answers,
    )
    try:
        saju = calendar_service.calculate(payload)
    except CalendarCalculationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    built_prompt = build_final_reading_prompt(payload, saju, prompt_store=prompt_store)
    llm_response = await _call_llm(
        llm_provider,
        request=request,
        http_response=response,
        settings=settings,
        system=built_prompt.system,
        prompt=built_prompt.prompt,
        schema=built_prompt.schema,
        schema_name=built_prompt.schema_name,
        max_output_tokens=settings.llm_final_reading_max_output_tokens,
    )
    try:
        output = _parse_final_reading(llm_response.content)
    except LLMInvalidOutputError as exc:
        raise _invalid_final_reading_http_error(exc) from exc

    result = FinalReadingResponse(saju=saju, reading=output, meta=_meta(llm_response))
    try:
        return await repo.save_final_result_and_consume_credit(current_user.id, session_id, result)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


async def _require_owned_session(repo: ReadingRepository, user_id: str, session_id: UUID) -> ReadingSessionResponse:
    session = await repo.get_session(user_id, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return session


async def _require_paid_session(repo: ReadingRepository, user_id: str, session_id: UUID) -> ReadingSessionResponse:
    session = await _require_owned_session(repo, user_id, session_id)
    if session.final_result is not None:
        return session
    if not await repo.has_available_credit(user_id, session_id):
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Payment required")
    return session
