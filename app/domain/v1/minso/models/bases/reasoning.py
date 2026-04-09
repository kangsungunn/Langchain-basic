"""
Reasoning Domain - 모델 (단일 소스: minso.models.bases)

추론 작업 및 결과 엔티티
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.core.database.connection import Base  # pyright: ignore[reportMissingImports]
from app.core.database.mixin import TimestampMixin  # pyright: ignore[reportMissingImports]


class TaskType(str, enum.Enum):
    """추론 작업 타입"""
    ISSUE_ANALYSIS = "issue_analysis"  # 쟁점 분석
    LOGIC_EVALUATION = "logic_evaluation"  # 논리 평가
    EXPRESSION_REVIEW = "expression_review"  # 표현 검토
    COMPREHENSIVE = "comprehensive"  # 종합 분석


class TaskStatus(str, enum.Enum):
    """추론 작업 상태"""
    PENDING = "pending"  # 대기 중
    RUNNING = "running"  # 실행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패


class ReasoningTask(Base, TimestampMixin):
    """
    추론 작업 엔티티

    MCP를 통해 전달된 추론 요청
    """
    __tablename__ = "reasoning_tasks"

    id = Column(String(36), primary_key=True)

    # 작업 정보
    task_type = Column(SQLEnum(TaskType), nullable=False)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)

    # 입력 데이터
    user_answer_id = Column(String(36), nullable=False)  # Submission Domain
    reference_answer_id = Column(String(36), nullable=False)  # Reference Domain
    problem_id = Column(String(36), nullable=False)  # Reference Domain

    # MCP 메타데이터
    request_id = Column(String(36), nullable=True)  # MCP 요청 ID
    source_domain = Column(String(50), nullable=True)  # 요청 도메인

    # 작업 설정
    config = Column(JSON, nullable=True)  # 추론 설정 (temperature, max_tokens 등)

    # Relationships
    results = relationship("ReasoningResult", back_populates="task", cascade="all, delete-orphan")
    embeddings = relationship("ReasoningTaskEmbedding", back_populates="reasoning_task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReasoningTask(id={self.id}, type={self.task_type.value}, status={self.status.value})>"


class ReasoningResult(Base, TimestampMixin):
    """
    추론 결과 엔티티

    EXAONE 모델의 분석 결과
    """
    __tablename__ = "reasoning_results"

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey("reasoning_tasks.id"), nullable=False, index=True)

    # Relationships
    task = relationship("ReasoningTask", back_populates="results")

    # 분석 결과
    result_type = Column(String(50), nullable=False)  # issue, logic, expression 등
    content = Column(JSON, nullable=False)  # 구조화된 결과

    # 신뢰도 및 메트릭
    confidence = Column(Float, nullable=True)  # 신뢰도 (0.0-1.0)
    metrics = Column(JSON, nullable=True)  # 추가 메트릭

    # 메타데이터
    meta = Column(JSON, nullable=True)  # 모델 버전, 실행 시간 등

    def __repr__(self):
        return f"<ReasoningResult(id={self.id}, task_id={self.task_id}, type={self.result_type})>"
