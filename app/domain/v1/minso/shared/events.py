"""
minso 도메인 이벤트 (스텁)

향후 이벤트 기반 처리(이벤트 버스, 아웃박스 등) 시 사용할 도메인 이벤트 정의.
현재는 스텁이며, 발생·구독 로직은 Phase 4 이후 통합 시 구현 예정.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# 공통 (타입/마커용, 필드 없음)
# ---------------------------------------------------------------------------


class MinsoDomainEvent:
    """minso 도메인 이벤트 마커. 하위 이벤트 클래스가 공통으로 상속."""
    pass


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UserAnswerCreated(MinsoDomainEvent):
    """사용자 답안 생성됨."""
    user_answer_id: str
    problem_id: Optional[str] = None
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class UserAnswerProcessed(MinsoDomainEvent):
    """사용자 답안 처리 완료(구조 분석/OCR 등)."""
    user_answer_id: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Reasoning
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReasoningTaskStarted(MinsoDomainEvent):
    """추론 작업 시작됨."""
    task_id: str
    user_answer_id: str
    task_type: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ReasoningTaskCompleted(MinsoDomainEvent):
    """추론 작업 완료됨."""
    task_id: str
    user_answer_id: str
    result_type: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeedbackGenerated(MinsoDomainEvent):
    """피드백 생성됨."""
    feedback_id: str
    user_answer_id: str
    reasoning_task_id: str
    feedback_type: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrainingJobStarted(MinsoDomainEvent):
    """학습 작업 시작됨."""
    job_id: str
    job_name: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class TrainingJobCompleted(MinsoDomainEvent):
    """학습 작업 완료됨."""
    job_id: str
    job_name: str
    status: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
