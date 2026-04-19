from __future__ import annotations

import json
from dataclasses import dataclass

from app.schemas.saju import (
    FinalReadingOutput,
    FinalReadingRequest,
    GenerateQuestionsRequest,
    QuestionGenerationOutput,
    SajuData,
)
from app.services.prompt_store import PromptStore


QUESTION_SYSTEM_PROMPT = """너는 심리 분석가 겸 한국 명리학 상담가다.
사용자의 초기 고민과 사주 명식에서 드러나는 성향을 함께 보고, 사용자가 마음속으로 진짜 확인받고 싶은 결론을 추론하기 위한 진단 질문을 만든다.

Structured Output 규칙:
1. 응답은 반드시 제공된 JSON Schema와 정확히 일치하는 JSON 객체만 반환한다.
2. 루트 객체는 "questions" 키 하나만 가진다.
3. "questions"는 정확히 5개이며 id는 q1, q2, q3, q4, q5 순서다.
4. 최소 4개는 type="single_choice"로 만들고 options는 A-D 중 2-4개를 사용한다.
5. 최대 1개만 type="short_text"로 만들고 options는 빈 배열 []로 둔다.
6. 질문 문장은 사용자가 방어적으로 느끼지 않게 짧고 구체적으로 작성한다.
7. text에는 질문 문장만 작성하고 (A), A., ① 같은 선택지 표기나 option label을 절대 포함하지 않는다.
8. 선택지는 반드시 options 배열에만 작성한다.
9. 질문은 돈, 인정, 안전, 도피, 관계 정리, 성장 욕구 중 무엇이 강한지 구분할 수 있어야 한다.
10. intent_signal에는 질문이 판별하려는 숨은 욕구를 간결히 적는다.
11. 마크다운, 코드블록, 설명, 주석, 스키마 반복 출력은 절대 하지 않는다."""


FINAL_SYSTEM_PROMPT = """너는 하이엔드 명리 심리 상담가다.
사용자의 초기 고민, 사주 명식, 5개 진단 답변을 근거로 프리미엄 상담 리포트를 작성한다.
목표는 가볍고 막연한 운세가 아니라, 사용자가 "정확하다, 쉽게 이해된다, 속이 시원하다, 바로 움직일 기준이 생겼다"고 느끼는 결과를 제공하는 것이다.

작성 원칙:
1. 결론을 미루지 말고 첫 문장부터 사용자가 붙잡을 수 있는 방향을 선명하게 말한다.
2. 명리학 용어는 필요할 때만 쓰고, 반드시 일상적인 심리/상황 언어로 번역해 설명한다.
3. "진단 답변을 보니", "선택하신 답변에서"처럼 과정이 드러나는 표현은 final_text와 deep_sections에서 쓰지 않는다.
4. 사주 명식의 오행, 십성, 일간, 대운 근거와 사용자의 고민을 연결하되, 확인할 수 없는 세운/월운은 지어내지 않는다.
5. 계산 방식, 구현 단계명, 근사값, 보정 가능성 같은 내부 설명은 사용자 결과에 쓰지 않는다.
6. 관계, 퇴사, 이직, 금전 조언은 극단적 결정을 부추기지 말고 준비 조건과 행동 기준을 함께 둔다.
7. 의학, 법률, 투자 수익, 채용, 합격, 결혼 성사처럼 현실 결과를 확정 예언하지 않는다.
8. 말투는 따뜻하지만 흐리지 않게, 상담자가 핵심을 짚어 주는 단정한 한국어로 쓴다.

Structured Output 규칙:
1. 응답은 반드시 제공된 JSON Schema와 정확히 일치하는 JSON 객체만 반환한다.
2. 마크다운, 코드블록, 설명, 주석, 스키마 반복 출력은 절대 하지 않는다.
3. 모든 필드는 한국어로 작성한다."""


QUESTION_USER_PROMPT_TEMPLATE = """아래 입력을 보고, 사용자가 진짜 원하는 결론을 판별하기 위한 진단 질문 5개를 생성하라.

사용자 초기 입력:
{profile_json}

사주 명식 데이터:
{saju_json}

질문 설계 기준:
- q1-q2는 초기 고민의 표면 이유와 실제 압박 요인을 가른다.
- q3-q4는 사용자가 원하는 보상(돈/인정/안정/자유/관계 정리)을 가른다.
- q5는 결정을 미루게 하는 두려움이나 마지막 확인 욕구를 묻는다.
- 사용자가 선택지를 고르기만 해도 마음의 방향이 드러나야 한다.
- text에는 질문만 쓰고, 보기 표기와 option label은 options 배열에만 넣는다.
"""


FINAL_USER_PROMPT_TEMPLATE = """아래 입력을 분석해 프리미엄 최종 사주풀이 리포트를 작성하라.

사용자 초기 입력:
{profile_json}

사주 명식 데이터:
{saju_json}

진단 질문 답변:
{answers_json}

리포트 구성:
- reading_title: 상담 리포트 제목. 20자 안팎의 짧고 선명한 제목으로 쓴다.
- desired_conclusion: 사용자가 마음속으로 가장 확인받고 싶어 하는 결론을 한 문장으로 적는다.
- core_message: 결과 화면 첫 영역에 들어갈 핵심 문장. 결론과 방향성을 한 문장의 짧은 단정문으로 쓴다.
- final_text: 2-3문단의 짧은 한국어 풀이. 첫 문장에서 결론을 말하고, 이후 심리 해석, 명식 근거, 행동 기준을 압축해 쓴다.
- summary_cards: 정확히 4개. title은 순서대로 "현재 핵심", "타고난 기질", "운의 흐름", "결정 기준"을 사용한다. headline은 짧은 결론, body는 쉬운 설명을 쓴다.
- deep_sections: 정확히 4개. title은 순서대로 "지금의 마음", "사주 기질", "시기 흐름", "고민에 대한 답"을 사용한다. 각 body는 2-4문장으로 쓴다.
- answer_signals: 사용자의 답변에서 읽은 심리 신호 3-5개. 과정 노출 문장 대신 "인정 욕구", "안전 확인 욕구"처럼 짧은 명사구로 쓴다.
- saju_basis: 명식 데이터에서 실제 사용한 근거 3-5개. 전문 용어만 나열하지 말고 해석을 함께 붙인다.
- timing_points: 대운 흐름과 현재 고민을 바탕으로 한 시기/리듬 포인트 2-4개. 확인되지 않은 연도·월은 지어내지 말고 "앞으로 2주", "한 달 안"처럼 실행 가능한 시간표로 표현한다.
- action_steps: 다음 2-4주 안에 실행할 현실 행동 2-4개.
- watchouts: 피해야 할 판단 방식이나 흔들릴 지점 2-3개.
- caution: 과장된 예언이 아니라 참고용 조언이라는 안전 문장을 적되, 흐름을 깨지 않게 짧게 작성한다.

품질 기준:
- 인기 사주/운세 서비스처럼 먼저 한눈에 요약되고, 아래에서 전문가 상담처럼 깊어지는 구조여야 한다.
- 사용자가 "내 상황을 쉽게 설명받았다"는 느낌을 받도록, 추상어보다 실제 판단 기준을 많이 쓴다.
- 같은 내용을 반복하지 말고 final_text는 700자 안팎으로 짧게 끝낸다.
- 계산 방식이나 구현 단계명 같은 내부 설명을 사용자 문장에 섞지 않는다.
- 불안감을 자극해 결제나 상담을 유도하는 문장은 쓰지 않는다.
"""


@dataclass(frozen=True)
class BuiltPrompt:
    system: str
    prompt: str
    schema: dict
    schema_name: str


def _resolve_system_prompt(store: PromptStore | None, name: str, default: str) -> str:
    if store is None:
        return default
    record = store.get_prompt(name)
    if record is None:
        return default
    content = record.content.strip()
    return content if content else default


def _render_prompt_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _compact_saju_payload(saju: SajuData) -> dict:
    return saju.model_dump(
        mode="json",
        exclude={
            "raw": True,
            "calculation_note": True,
        },
    )


def _profile_payload(profile: GenerateQuestionsRequest | FinalReadingRequest) -> dict:
    return {
        "name": profile.name,
        "gender": profile.gender.value,
        "birth": profile.birth.model_dump(mode="json"),
        "initial_concern": profile.initial_concern,
    }


def build_question_generation_prompt(profile: GenerateQuestionsRequest, saju: SajuData, *, prompt_store: PromptStore | None = None) -> BuiltPrompt:
    schema = QuestionGenerationOutput.model_json_schema()
    template = _resolve_system_prompt(prompt_store, "question_user_prompt", QUESTION_USER_PROMPT_TEMPLATE)
    prompt = _render_prompt_template(
        template,
        {
            "profile_json": json.dumps(_profile_payload(profile), ensure_ascii=False, indent=2),
            "saju_json": json.dumps(_compact_saju_payload(saju), ensure_ascii=False, indent=2),
        },
    )
    return BuiltPrompt(
        system=_resolve_system_prompt(prompt_store, "question_system_prompt", QUESTION_SYSTEM_PROMPT),
        prompt=prompt,
        schema=schema,
        schema_name="QuestionGenerationOutput",
    )


def build_final_reading_prompt(payload: FinalReadingRequest, saju: SajuData, *, prompt_store: PromptStore | None = None) -> BuiltPrompt:
    schema = FinalReadingOutput.model_json_schema()
    answers_payload = [answer.model_dump(mode="json") for answer in payload.answers]
    template = _resolve_system_prompt(prompt_store, "final_user_prompt", FINAL_USER_PROMPT_TEMPLATE)
    prompt = _render_prompt_template(
        template,
        {
            "profile_json": json.dumps(_profile_payload(payload), ensure_ascii=False, indent=2),
            "saju_json": json.dumps(_compact_saju_payload(saju), ensure_ascii=False, indent=2),
            "answers_json": json.dumps(answers_payload, ensure_ascii=False, indent=2),
        },
    )
    return BuiltPrompt(
        system=_resolve_system_prompt(prompt_store, "final_system_prompt", FINAL_SYSTEM_PROMPT),
        prompt=prompt,
        schema=schema,
        schema_name="FinalReadingOutput",
    )
