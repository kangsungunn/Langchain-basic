"""
Submission Domain - 모델 (단일 소스: minso.models.bases)

사용자 답안 엔티티 정의
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum

from app.core.database.connection import Base  # pyright: ignore[reportMissingImports]
from app.core.database.mixin import TimestampMixin  # pyright: ignore[reportMissingImports]


class SubmissionType(str, enum.Enum):
    """제출 타입"""
    TEXT = "text"  # 텍스트 직접 입력
    IMAGE = "image"  # 이미지 업로드 (OCR 필요)


class SubmissionStatus(str, enum.Enum):
    """제출 상태"""
    PENDING = "pending"  # 대기 중
    PROCESSING = "processing"  # 처리 중 (OCR 등)
    COMPLETED = "completed"  # 완료
    FAILED = "failed"  # 실패


class UserAnswer(Base, TimestampMixin):
    """
    사용자 답안 엔티티

    사용자가 제출한 서술형 답안
    """
    __tablename__ = "user_answers"

    id = Column(String(36), primary_key=True)
    problem_id = Column(String(36), nullable=False)  # Reference Domain의 Problem ID

    # 제출 정보
    submission_type = Column(SQLEnum(SubmissionType), nullable=False, default=SubmissionType.TEXT)
    status = Column(SQLEnum(SubmissionStatus), nullable=False, default=SubmissionStatus.PENDING)

    # 답안 내용
    raw_content = Column(Text, nullable=True)  # 원본 내용 (TEXT) 또는 이미지 경로 (IMAGE)
    processed_content = Column(Text, nullable=True)  # 처리된 텍스트 (OCR 결과 또는 정제된 텍스트)

    # 메타데이터
    meta = Column(JSON, nullable=True)  # OCR 신뢰도, 이미지 정보 등

    # Relationships
    structure = relationship("AnswerStructure", back_populates="user_answer", uselist=False, cascade="all, delete-orphan")
    embeddings = relationship("UserAnswerEmbedding", back_populates="user_answer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserAnswer(id={self.id}, problem_id={self.problem_id}, type={self.submission_type.value})>"


class AnswerStructure(Base, TimestampMixin):
    """
    답안 구조 엔티티

    사용자 답안의 구조화된 정보 (문단, 문장 분리)
    """
    __tablename__ = "answer_structures"

    id = Column(String(36), primary_key=True)
    user_answer_id = Column(String(36), ForeignKey("user_answers.id"), nullable=False, unique=True)

    # 구조화된 데이터
    paragraphs = Column(JSON, nullable=True)  # [{"order": 1, "content": "..."}, ...]
    sentences = Column(JSON, nullable=True)  # [{"paragraph": 1, "order": 1, "content": "..."}, ...]

    # 통계 정보
    paragraph_count = Column(JSON, nullable=True)  # {"total": 3}
    sentence_count = Column(JSON, nullable=True)  # {"total": 15, "per_paragraph": [5, 6, 4]}
    word_count = Column(JSON, nullable=True)  # {"total": 250}

    # Relationships
    user_answer = relationship("UserAnswer", back_populates="structure")

    def __repr__(self):
        return f"<AnswerStructure(id={self.id}, user_answer_id={self.user_answer_id})>"
