"""
minso 도메인 모델

단일 소스: models.bases (Feedback, Reference, Submission, Reasoning 엔티티).
Training은 루트 training/ 패키지에서만 관리.
"""
# pyright: reportMissingImports=false
from .bases import (  # pyright: ignore[reportUnknownMemberType]
    # Feedback
    FeedbackType,
    FeedbackSeverity,
    FeedbackCorrectionType,
    Feedback,
    FeedbackItem,
    FeedbackCorrection,
    FeedbackEmbedding,
    # Reference
    Problem,
    ReferenceAnswer,
    Issue,
    ReferenceAnswerEmbedding,
    # Submission
    SubmissionType,
    SubmissionStatus,
    UserAnswer,
    AnswerStructure,
    UserAnswerEmbedding,
    # Reasoning
    TaskType,
    TaskStatus,
    ReasoningTask,
    ReasoningResult,
    ReasoningTaskEmbedding,
)

__all__ = [
    "FeedbackType",
    "FeedbackSeverity",
    "FeedbackCorrectionType",
    "Feedback",
    "FeedbackItem",
    "FeedbackCorrection",
    "FeedbackEmbedding",
    "Problem",
    "ReferenceAnswer",
    "Issue",
    "ReferenceAnswerEmbedding",
    "SubmissionType",
    "SubmissionStatus",
    "UserAnswer",
    "AnswerStructure",
    "UserAnswerEmbedding",
    "TaskType",
    "TaskStatus",
    "ReasoningTask",
    "ReasoningResult",
    "ReasoningTaskEmbedding",
]
