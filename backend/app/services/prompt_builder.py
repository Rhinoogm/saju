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


QUESTION_SYSTEM_PROMPT = """너는 심리 분석가 겸 한국 명리학 상담가다.
사용자의 초기 고민과 사주 명식에서 드러나는 성향을 함께 보고, 사용자가 마음속으로 진짜 확인받고 싶은 결론을 추론하기 위한 진단 질문을 만든다.

Structured Output 규칙:
1. 응답은 반드시 제공된 JSON Schema와 정확히 일치하는 JSON 객체만 반환한다.
2. 루트 객체는 "questions" 키 하나만 가진다.
3. "questions"는 정확히 5개이며 id는 q1, q2, q3, q4, q5 순서다.
4. 최소 4개는 type="single_choice"로 만들고 options는 A-D 중 2-4개를 사용한다.
5. 최대 1개만 type="short_text"로 만들고 options는 빈 배열 []로 둔다.
6. 질문 문장은 사용자가 방어적으로 느끼지 않게 짧고 구체적으로 작성한다.
7. 질문은 돈, 인정, 안전, 도피, 관계 정리, 성장 욕구 중 무엇이 강한지 구분할 수 있어야 한다.
8. intent_signal에는 질문이 판별하려는 숨은 욕구를 간결히 적는다.
9. 마크다운, 코드블록, 설명, 주석, 스키마 반복 출력은 절대 하지 않는다."""


FINAL_SYSTEM_PROMPT = """너는 심리 분석가 겸 한국 명리학 상담가다.
사용자의 초기 고민, 사주 명식, 5개 진단 답변을 함께 분석해 사용자가 마음속으로 가장 확인받고 싶어 하는 결론을 파악한다.
그 결론을 사주 명식의 근거와 연결해 직관적이고 명확한 최종 풀이로 작성한다.

작성 원칙:
1. 사용자가 듣고 싶어 하는 방향을 회피하지 말고 첫 문단에서 선명하게 말한다.
2. 답변에서 드러난 욕구를 먼저 짚고, 그 다음 사주 명식의 오행/십성/대운 근거로 받쳐준다.
3. 말투는 따뜻하지만 흐리지 않게, 답답함을 풀어주는 문장으로 쓴다.
4. 의학, 법률, 투자, 채용, 합격, 결혼 성사처럼 현실 결과를 확정 예언하지 않는다.
5. 위험하거나 극단적인 선택을 부추기지 않는다. 관계/퇴사/이직 조언은 준비 조건과 행동 기준을 함께 둔다.

Structured Output 규칙:
1. 응답은 반드시 제공된 JSON Schema와 정확히 일치하는 JSON 객체만 반환한다.
2. 마크다운, 코드블록, 설명, 주석, 스키마 반복 출력은 절대 하지 않는다."""


@dataclass(frozen=True)
class BuiltPrompt:
    system: str
    prompt: str
    schema: dict
    schema_name: str


def _compact_saju_payload(saju: SajuData) -> dict:
    return saju.model_dump(
        mode="json",
        exclude={
            "raw": True,
        },
    )


def _profile_payload(profile: GenerateQuestionsRequest | FinalReadingRequest) -> dict:
    return {
        "name": profile.name,
        "gender": profile.gender.value,
        "birth": profile.birth.model_dump(mode="json"),
        "initial_concern": profile.initial_concern,
    }


def build_question_generation_prompt(profile: GenerateQuestionsRequest, saju: SajuData) -> BuiltPrompt:
    schema = QuestionGenerationOutput.model_json_schema()
    prompt = f"""아래 입력을 보고, 사용자가 진짜 원하는 결론을 판별하기 위한 진단 질문 5개를 생성하라.

사용자 초기 입력:
{json.dumps(_profile_payload(profile), ensure_ascii=False, indent=2)}

사주 명식 데이터:
{json.dumps(_compact_saju_payload(saju), ensure_ascii=False, indent=2)}

질문 설계 기준:
- q1-q2는 초기 고민의 표면 이유와 실제 압박 요인을 가른다.
- q3-q4는 사용자가 원하는 보상(돈/인정/안정/자유/관계 정리)을 가른다.
- q5는 결정을 미루게 하는 두려움이나 마지막 확인 욕구를 묻는다.
- 사용자가 선택지를 고르기만 해도 마음의 방향이 드러나야 한다.
"""
    return BuiltPrompt(
        system=QUESTION_SYSTEM_PROMPT,
        prompt=prompt,
        schema=schema,
        schema_name="QuestionGenerationOutput",
    )


def build_final_reading_prompt(payload: FinalReadingRequest, saju: SajuData) -> BuiltPrompt:
    schema = FinalReadingOutput.model_json_schema()
    answers_payload = [answer.model_dump(mode="json") for answer in payload.answers]
    prompt = f"""아래 입력을 분석해 최종 사주풀이를 작성하라.

사용자 초기 입력:
{json.dumps(_profile_payload(payload), ensure_ascii=False, indent=2)}

사주 명식 데이터:
{json.dumps(_compact_saju_payload(saju), ensure_ascii=False, indent=2)}

진단 질문 답변:
{json.dumps(answers_payload, ensure_ascii=False, indent=2)}

최종 풀이 구성:
- desired_conclusion: 사용자가 마음속으로 가장 확인받고 싶어 하는 결론을 한 문장으로 적는다.
- core_message: 사용자가 바로 붙잡을 수 있는 핵심 문장을 적는다.
- final_text: 5-8문단의 자연스러운 한국어 풀이로 작성한다. 첫 문단에서 결론을 분명히 말한다.
- answer_signals: 답변에서 읽은 심리 신호 3-5개.
- saju_basis: 명식 데이터에서 실제 사용한 근거 3-5개.
- action_steps: 다음 2-4주 안에 실행할 현실 행동 2-4개.
- caution: 과장된 예언이 아니라 참고용 조언이라는 안전 문장을 적되, 흐름을 깨지 않게 짧게 작성한다.
"""
    return BuiltPrompt(
        system=FINAL_SYSTEM_PROMPT,
        prompt=prompt,
        schema=schema,
        schema_name="FinalReadingOutput",
    )
