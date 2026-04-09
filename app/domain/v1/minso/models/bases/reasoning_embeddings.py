"""
Reasoning Embedding - 모델 (자동 생성)

ReasoningTask 엔티티의 임베딩 모델.
ExaOne 모델로 자동 생성됨.
"""

from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.core.database.connection import Base  # pyright: ignore[reportMissingImports]


class ReasoningTaskEmbedding(Base):
    """
    ReasoningTask 임베딩 엔티티

    추론 작업에 대한 벡터 임베딩 정보를 저장합니다.
    """
    __tablename__ = "reasoning_task_embeddings"

    id = Column(BigInteger, primary_key=True, autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자')
    reasoning_task_id = Column(String(36), ForeignKey("reasoning_tasks.id", ondelete='CASCADE'), nullable=False, comment='추론 작업 ID')
    content = Column(Text, nullable=False, comment='임베딩 생성에 사용된 원본 텍스트')
    embedding = Column(Vector(768), nullable=False, comment='768차원 임베딩 벡터 (KoELECTRA)')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, comment='레코드 생성 시간')

    # Relationships
    reasoning_task = relationship("ReasoningTask", back_populates="embeddings")

    def __repr__(self):
        return f"<ReasoningTaskEmbedding(id={self.id}, reasoning_task_id={self.reasoning_task_id})>"
