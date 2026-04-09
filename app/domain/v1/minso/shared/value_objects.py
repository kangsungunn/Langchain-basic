"""
minso 도메인 공통 값 객체(Value Objects)

EntityId 타입과 엔티티 종류 상수.
EntityNotFoundError 등에서 entity_type 으로 사용.
"""

from typing import NewType

# ---------------------------------------------------------------------------
# 식별자 타입
# ---------------------------------------------------------------------------

EntityId = NewType("EntityId", str)
"""
엔티티 식별자. UUID 문자열 등.
타입 힌트용이며 런타임 검증은 하지 않음.
"""

# ---------------------------------------------------------------------------
# 엔티티 종류 상수 (EntityNotFoundError.entity_type 등에 사용)
# ---------------------------------------------------------------------------

ENTITY_USER_ANSWER = "user_answer"
ENTITY_REASONING_TASK = "reasoning_task"
ENTITY_REASONING_RESULT = "reasoning_result"
ENTITY_FEEDBACK = "feedback"
ENTITY_FEEDBACK_ITEM = "feedback_item"
ENTITY_TRAINING_DATA = "training_data"
ENTITY_TRAINING_JOB = "training_job"
ENTITY_PROBLEM = "problem"
ENTITY_REFERENCE_ANSWER = "reference_answer"
