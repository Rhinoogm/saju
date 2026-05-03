from __future__ import annotations

from dataclasses import dataclass


COUNSELING_QUESTION_IDS = ("q1", "q2", "q3", "q4", "q5")


@dataclass(frozen=True)
class CounselingStepGuide:
    id: str
    step: int
    title: str
    framework: str
    objective: str
    base_question: str
    base_options: tuple[str, str, str, str]
    intent_signal: str

    def as_prompt_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "step": self.step,
            "title": self.title,
            "framework": self.framework,
            "objective": self.objective,
            "base_question": self.base_question,
            "base_options": list(self.base_options),
            "intent_signal": self.intent_signal,
        }


COUNSELING_STEP_GUIDES: tuple[CounselingStepGuide, ...] = (
    CounselingStepGuide(
        id="q1",
        step=1,
        title="감정의 명료화",
        framework="CBT 자동적 사고 탐색을 위한 현재 감정 확인",
        objective="내담자가 고민을 떠올릴 때 가장 크게 지배받는 핵심 감정을 파악한다.",
        base_question="지금 이 고민을 떠올리실 때, 마음속에서 가장 크게 느껴지는 감정은 무엇인가요?",
        base_options=(
            "무언가 잘못될 것 같은 불안과 초조함",
            "내 힘으로는 어찌할 수 없을 것 같은 막막함과 무기력",
            "반드시 이루어졌으면 하는 간절함과 기대",
            "나 혼자서 감당해야 한다는 외로움과 부담감",
        ),
        intent_signal="감정 명료화",
    ),
    CounselingStepGuide(
        id="q2",
        step=2,
        title="통제 소재 파악",
        framework="Julian Rotter의 통제 소재 이론",
        objective="내담자가 문제의 해결 주체를 자신, 타인, 환경 중 어디에 두고 있는지 확인한다.",
        base_question="이 고민이 최종적으로 어떤 결과로 이어질지 결정하는 가장 큰 요인은 무엇이라고 생각하시나요?",
        base_options=(
            "나의 구체적인 선택과 앞으로의 노력",
            "나를 둘러싼 주변 사람들의 도움이나 반응",
            "내가 통제할 수 없는 운명이나 시기적인 타이밍",
            "아직은 무엇이 결과를 바꿀지 잘 모르겠음",
        ),
        intent_signal="통제 소재",
    ),
    CounselingStepGuide(
        id="q3",
        step=3,
        title="핵심 신념 및 결핍 확인",
        framework="Maslow 욕구 위계와 CBT Schema",
        objective="고민을 통해 채우고자 하는 안정, 인정, 애정, 자율성의 심리적 욕구를 확인한다.",
        base_question="만약 누군가 이 고민에 대해 딱 한 마디를 해준다면, 어떤 말이 가장 위로가 될까요?",
        base_options=(
            "큰 문제 없이 지금처럼 무탈할 거예요.",
            "당신은 충분히 그럴 자격과 능력이 있어요.",
            "당신의 마음을 이해해요. 제가 곁에 있을게요.",
            "당신의 생각과 선택이 맞아요. 그대로 밀고 나가세요.",
        ),
        intent_signal="핵심 욕구",
    ),
    CounselingStepGuide(
        id="q4",
        step=4,
        title="변화 준비도 및 행동 동기",
        framework="Motivational Interviewing",
        objective="내담자가 현재 행동할 준비가 되어 있는지, 정서적 지지를 원하는 상태인지 판별한다.",
        base_question="현재 이 고민을 해결하기 위해 본인에게 가장 필요한 것은 무엇이라고 생각하시나요?",
        base_options=(
            "상황을 바꿀 수 있는 현실적이고 구체적인 방법과 계획",
            "내가 생각한 방향이 틀리지 않았다는 확인과 지지",
            "결국엔 다 잘 풀릴 것이라는 무조건적인 희망과 긍정",
            "복잡한 내 마음을 스스로 정리할 수 있는 객관적인 시각",
        ),
        intent_signal="변화 준비도",
    ),
    CounselingStepGuide(
        id="q5",
        step=5,
        title="해결중심 투사",
        framework="SFBT 기적 질문 변형",
        objective="내담자가 무의식적으로 바라는 결말과 해결의 형태를 확인한다.",
        base_question="만약 내일 아침 이 고민이 기적처럼 흔적도 없이 사라진다면, 그 이유는 무엇일까요?",
        base_options=(
            "내가 스스로 용기를 내어 행동하고 상황을 부딪혀 바꿨기 때문에",
            "나를 힘들게 하거나 신경 쓰이게 하던 사람이나 외부 요인이 변했기 때문에",
            "시간이 흐르면서 걱정했던 것과 달리 자연스럽게 상황이 풀렸기 때문에",
            "예상치 못한 새로운 기회나 도와줄 사람이 나타났기 때문에",
        ),
        intent_signal="희망 해결상",
    ),
)


_GUIDES_BY_ID = {guide.id: guide for guide in COUNSELING_STEP_GUIDES}


def counseling_step_for_question_id(question_id: str) -> CounselingStepGuide:
    try:
        return _GUIDES_BY_ID[question_id]
    except KeyError as exc:
        raise ValueError(f"unknown counseling question id: {question_id}") from exc


def next_counseling_question_id(answer_count: int) -> str:
    if answer_count < 0 or answer_count >= len(COUNSELING_QUESTION_IDS):
        raise ValueError("answer_count must be between 0 and 4")
    return COUNSELING_QUESTION_IDS[answer_count]
