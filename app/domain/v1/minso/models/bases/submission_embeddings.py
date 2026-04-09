"""
Submission Embedding - 모델 (자동 생성)

UserAnswer 엔티티의 임베딩 모델.
ExaOne 모델로 자동 생성됨.
"""

from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.core.database.connection import Base  # pyright: ignore[reportMissingImports]


class UserAnswerEmbedding(Base):
    """
    UserAnswer 임베딩 엔티티

    사용자 답안에 대한 벡터 임베딩 정보를 저장합니다.
    """
    __tablename__ = "user_answer_embeddings"

    id = Column(BigInteger, primary_key=True, autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자')
    user_answer_id = Column(String(36), ForeignKey("user_answers.id", ondelete='CASCADE'), nullable=False, comment='사용자 답안 ID')
    content = Column(Text, nullable=False, comment='임베딩 생성에 사용된 원본 텍스트')
    embedding = Column(Vector(768), nullable=False, comment='768차원 임베딩 벡터 (KoELECTRA)')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, comment='레코드 생성 시간')

    # Relationships
    user_answer = relationship("UserAnswer", back_populates="embeddings")

    def __repr__(self):
        return f"<UserAnswerEmbedding(id={self.id}, user_answer_id={self.user_answer_id})>"
