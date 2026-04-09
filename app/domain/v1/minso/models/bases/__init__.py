"""
minso 도메인 엔티티 (단일 소스)

Feedback, Reference, Submission, Reasoning ORM 모델 및 Enum.
(Training은 루트 training/ 패키지에서만 관리)
"""

from .feedback import (
    FeedbackType,
    FeedbackSeverity,
    FeedbackCorrectionType,
    Feedback,
    FeedbackItem,
    FeedbackCorrection,
)
from .reference import (
    Problem,
    ReferenceAnswer,
    Issue,
)
from .submission import (
    SubmissionType,
    SubmissionStatus,
    UserAnswer,
    AnswerStructure,
)
from .reasoning import (
    TaskType,
    TaskStatus,
    ReasoningTask,
    ReasoningResult,
)
from .feedback_embeddings import FeedbackEmbedding
from .reference_embeddings import ReferenceAnswerEmbedding
from .submission_embeddings import UserAnswerEmbedding
from .reasoning_embeddings import ReasoningTaskEmbedding

__all__ = [
    # Feedback
    "FeedbackType",
    "FeedbackSeverity",
    "FeedbackCorrectionType",
    "Feedback",
    "FeedbackItem",
    "FeedbackCorrection",
    "FeedbackEmbedding",
    # Reference
    "Problem",
    "ReferenceAnswer",
    "Issue",
    "ReferenceAnswerEmbedding",
    # Submission
    "SubmissionType",
    "SubmissionStatus",
    "UserAnswer",
    "AnswerStructure",
    "UserAnswerEmbedding",
    # Reasoning
    "TaskType",
    "TaskStatus",
    "ReasoningTask",
    "ReasoningResult",
    "ReasoningTaskEmbedding",
]
