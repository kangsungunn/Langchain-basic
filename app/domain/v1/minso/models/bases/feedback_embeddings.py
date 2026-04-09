"""
Feedback Embedding - 모델 (자동 생성)

Feedback 엔티티의 임베딩 모델.
ExaOne 모델로 자동 생성됨.
"""

from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.core.database.connection import Base  # pyright: ignore[reportMissingImports]


class FeedbackEmbedding(Base):
    """
    Feedback 임베딩 엔티티

    피드백에 대한 벡터 임베딩 정보를 저장합니다.
    """
    __tablename__ = "feedback_embeddings"

    id = Column(BigInteger, primary_key=True, autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자')
    feedback_id = Column(String(36), ForeignKey("feedbacks.id", ondelete='CASCADE'), nullable=False, comment='피드백 ID')
    content = Column(Text, nullable=False, comment='임베딩 생성에 사용된 원본 텍스트')
    embedding = Column(Vector(768), nullable=False, comment='768차원 임베딩 벡터 (KoELECTRA)')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, comment='레코드 생성 시간')

    # Relationships
    feedback = relationship("Feedback", back_populates="embeddings")

    def __repr__(self):
        return f"<FeedbackEmbedding(id={self.id}, feedback_id={self.feedback_id})>"
