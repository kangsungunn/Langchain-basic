"""
Feedback Domain - 모델 (단일 소스: minso.models.bases)

피드백 엔티티 정의
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum

from app.core.database.connection import Base  # pyright: ignore[reportMissingImports]
from app.core.database.mixin import TimestampMixin  # pyright: ignore[reportMissingImports]


class FeedbackType(str, enum.Enum):
    """피드백 타입"""
    ISSUE = "issue"  # 쟁점 피드백
    LOGIC = "logic"  # 논리 피드백
    EXPRESSION = "expression"  # 표현 피드백
    COMPREHENSIVE = "comprehensive"  # 종합 피드백


class FeedbackSeverity(str, enum.Enum):
    """피드백 심각도"""
    INFO = "info"  # 정보성
    SUGGESTION = "suggestion"  # 제안
    WARNING = "warning"  # 주의
    CRITICAL = "critical"  # 심각


class Feedback(Base, TimestampMixin):
    """
    피드백 엔티티

    사용자 답안에 대한 종합 피드백
    """
    __tablename__ = "feedbacks"

    id = Column(String(36), primary_key=True)

    # 연관 정보
    user_answer_id = Column(String(36), nullable=False, index=True)
    reasoning_task_id = Column(String(36), nullable=True)  # 추론 작업 ID (옵션)

    # 피드백 타입
    feedback_type = Column(SQLEnum(FeedbackType), nullable=False)

    # 점수 및 평가
    overall_score = Column(Float, nullable=True)  # 종합 점수 (0.0-100.0)
    scores = Column(JSON, nullable=True)  # 세부 점수 {"issue": 80, "logic": 75, "expression": 85}

    # 요약
    summary = Column(Text, nullable=True)  # 피드백 요약
    strengths = Column(JSON, nullable=True)  # 강점 리스트
    weaknesses = Column(JSON, nullable=True)  # 약점 리스트

    # 메타데이터
    meta = Column(JSON, nullable=True)  # 추가 메타데이터

    # Relationships
    items = relationship("FeedbackItem", back_populates="feedback", cascade="all, delete-orphan")
    embeddings = relationship("FeedbackEmbedding", back_populates="feedback", cascade="all, delete-orphan")
    corrections = relationship("FeedbackCorrection", back_populates="feedback", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Feedback(id={self.id}, type={self.feedback_type.value}, score={self.overall_score})>"


class FeedbackCorrectionType(str, enum.Enum):
    """피드백에 대한 사용자 의견 유형 (학습용)"""
    CORRECTION = "correction"   # 정정: "이 부분은 틀렸다, 이렇게 내려라"
    ADDITION = "addition"       # 추가/강조: "이런 포인트를 더 넣어라"


class FeedbackCorrection(Base, TimestampMixin):
    """
    피드백에 대한 사용자 정정/추가 요청 (학습용)

    사용자가 첨삭 결과를 보고 "이건 틀렸다 / 이렇게 해라", "이런 점을 더 강조해라" 등을
    입력하면 저장하고, 나중에 SFT/RAG 등으로 모델 개선에 활용할 수 있음.
    """
    __tablename__ = "feedback_corrections"

    id = Column(String(36), primary_key=True)
    feedback_id = Column(String(36), ForeignKey("feedbacks.id", ondelete="CASCADE"), nullable=False, index=True)

    correction_type = Column(String(20), nullable=False)  # 'correction' | 'addition' (DB enum 대신 문자열로 저장해 PostgreSQL enum 대소문자 이슈 방지)
    content = Column(Text, nullable=False)  # 사용자가 입력한 정정/추가 요청 내용

    meta = Column(JSON, nullable=True)  # 추후 원본 피드백 스냅샷 등

    feedback = relationship("Feedback", back_populates="corrections")

    def __repr__(self):
        t = getattr(self.correction_type, "value", self.correction_type)
        return f"<FeedbackCorrection(id={self.id}, type={t}, feedback_id={self.feedback_id})>"


class FeedbackItem(Base, TimestampMixin):
    """
    피드백 항목 엔티티

    개별 피드백 항목 (쟁점별, 문단별 등)
    """
    __tablename__ = "feedback_items"

    id = Column(String(36), primary_key=True)
    feedback_id = Column(String(36), ForeignKey("feedbacks.id"), nullable=False, index=True)

    # 항목 정보
    item_type = Column(String(50), nullable=False)  # issue, logic_coherence, grammar 등
    severity = Column(SQLEnum(FeedbackSeverity), nullable=False, default=FeedbackSeverity.INFO)

    # 위치 정보
    location = Column(JSON, nullable=True)  # {"paragraph": 2, "sentence": 3}

    # 피드백 내용
    title = Column(String(255), nullable=False)  # 피드백 제목
    description = Column(Text, nullable=False)  # 상세 설명
    suggestion = Column(Text, nullable=True)  # 개선 제안

    # 점수 (옵션)
    score = Column(Float, nullable=True)  # 항목별 점수

    # 메타데이터
    meta = Column(JSON, nullable=True)

    # Relationships
    feedback = relationship("Feedback", back_populates="items")

    def __repr__(self):
        return f"<FeedbackItem(id={self.id}, type={self.item_type}, severity={self.severity.value})>"
