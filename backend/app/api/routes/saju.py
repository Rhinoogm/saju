from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas.saju import (
    FinalReadingOutput,
    FinalReadingRequest,
    FinalReadingResponse,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    QuestionGenerationOutput,
    ResponseMeta,
)
from app.services.calendar_service import CalendarCalculationError, CalendarService
from app.services.llm.base import LLMProvider, LLMProviderError, LLMResponse, LLMTimeoutError
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.prompt_builder import build_final_reading_prompt, build_question_generation_prompt

router = APIRouter(prefix="/api", tags=["saju"])


def get_calendar_service() -> CalendarService:
    return CalendarService()


def get_llm_provider(settings: Settings = Depends(get_settings)) -> LLMProvider:
    if settings.llm_provider == "groq":
        return GroqProvider(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            model=settings.groq_model,
            timeout_seconds=settings.groq_timeout_seconds,
            temperature=settings.groq_temperature,
        )

    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        temperature=settings.ollama_temperature,
        format_mode=settings.ollama_format_mode,
    )


def _meta(response: LLMResponse) -> ResponseMeta:
    return ResponseMeta(
        provider=response.provider,
        model=response.model,
        raw_metadata=response.raw_metadata,
    )


async def _call_llm(llm_provider: LLMProvider, *, system: str, prompt: str, schema: dict, schema_name: str) -> LLMResponse:
    try:
        return await llm_provider.generate(
            system=system,
            prompt=prompt,
            schema=schema,
            schema_name=schema_name,
        )
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def _parse_questions(content: str) -> QuestionGenerationOutput:
    try:
        return QuestionGenerationOutput.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM returned invalid question JSON: {content[:500]}",
        ) from exc


def _parse_final_reading(content: str) -> FinalReadingOutput:
    try:
        return FinalReadingOutput.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM returned invalid final reading JSON: {content[:500]}",
        ) from exc


@router.post("/generate-questions", response_model=GenerateQuestionsResponse)
async def generate_questions(
    payload: GenerateQuestionsRequest,
    calendar_service: CalendarService = Depends(get_calendar_service),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> GenerateQuestionsResponse:
    try:
        saju = calendar_service.calculate(payload)
    except CalendarCalculationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    built_prompt = build_question_generation_prompt(payload, saju)
    llm_response = await _call_llm(
        llm_provider,
        system=built_prompt.system,
        prompt=built_prompt.prompt,
        schema=built_prompt.schema,
        schema_name=built_prompt.schema_name,
    )
    output = _parse_questions(llm_response.content)

    return GenerateQuestionsResponse(
        saju=saju,
        questions=output.questions,
        meta=_meta(llm_response),
    )


@router.post("/final-reading", response_model=FinalReadingResponse)
async def final_reading(
    payload: FinalReadingRequest,
    calendar_service: CalendarService = Depends(get_calendar_service),
    llm_provider: LLMProvider = Depends(get_llm_provider),
) -> FinalReadingResponse:
    try:
        saju = calendar_service.calculate(payload)
    except CalendarCalculationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    built_prompt = build_final_reading_prompt(payload, saju)
    llm_response = await _call_llm(
        llm_provider,
        system=built_prompt.system,
        prompt=built_prompt.prompt,
        schema=built_prompt.schema,
        schema_name=built_prompt.schema_name,
    )
    output = _parse_final_reading(llm_response.content)

    return FinalReadingResponse(
        saju=saju,
        reading=output,
        meta=_meta(llm_response),
    )
