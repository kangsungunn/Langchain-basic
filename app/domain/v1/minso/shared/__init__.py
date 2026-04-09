"""
minso 도메인 공통(shared)

예외, 값 객체, 도메인 이벤트를 re-export.
"""

from app.domain.v1.minso.shared.exceptions import (
    DomainValidationError,
    EntityNotFoundError,
    MinsoDomainError,
)
from app.domain.v1.minso.shared.value_objects import (
    ENTITY_FEEDBACK,
    ENTITY_FEEDBACK_ITEM,
    ENTITY_PROBLEM,
    ENTITY_REASONING_RESULT,
    ENTITY_REASONING_TASK,
    ENTITY_REFERENCE_ANSWER,
    ENTITY_TRAINING_DATA,
    ENTITY_TRAINING_JOB,
    ENTITY_USER_ANSWER,
    EntityId,
)
from app.domain.v1.minso.shared.events import (
    FeedbackGenerated,
    MinsoDomainEvent,
    ReasoningTaskCompleted,
    ReasoningTaskStarted,
    TrainingJobCompleted,
    TrainingJobStarted,
    UserAnswerCreated,
    UserAnswerProcessed,
)

__all__ = [
    # exceptions
    "MinsoDomainError",
    "EntityNotFoundError",
    "DomainValidationError",
    # value_objects
    "EntityId",
    "ENTITY_USER_ANSWER",
    "ENTITY_REASONING_TASK",
    "ENTITY_REASONING_RESULT",
    "ENTITY_FEEDBACK",
    "ENTITY_FEEDBACK_ITEM",
    "ENTITY_TRAINING_DATA",
    "ENTITY_TRAINING_JOB",
    "ENTITY_PROBLEM",
    "ENTITY_REFERENCE_ANSWER",
    # events
    "MinsoDomainEvent",
    "UserAnswerCreated",
    "UserAnswerProcessed",
    "ReasoningTaskStarted",
    "ReasoningTaskCompleted",
    "FeedbackGenerated",
    "TrainingJobStarted",
    "TrainingJobCompleted",
]
