"""
Reference Domain - 모델 (단일 소스: minso.models.bases)

기준 지식 엔티티 정의
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import relationship  # pyright: ignore[reportMissingImports]

from app.core.database.connection import Base  # pyright: ignore[reportMissingImports]
from app.core.database.mixin import TimestampMixin  # pyright: ignore[reportMissingImports]


class Problem(Base, TimestampMixin):
    """
    문제 엔티티

    서술형 민사소송법 문제
    """
    __tablename__ = "problems"

    id = Column(String(36), primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)  # 문제 전문
    meta = Column(JSON, nullable=True)  # 추가 메타데이터 (난이도, 카테고리 등)

    # Relationships
    reference_answers = relationship("ReferenceAnswer", back_populates="problem", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Problem(id={self.id}, title={self.title[:30]}...)>"


class ReferenceAnswer(Base, TimestampMixin):
    """
    모범답안 엔티티

    문제에 대한 모범답안 및 논점 구조
    """
    __tablename__ = "reference_answers"

    id = Column(String(36), primary_key=True)
    problem_id = Column(String(36), ForeignKey("problems.id"), nullable=False)
    content = Column(Text, nullable=False)  # 모범답안 전문
    structure = Column(JSON, nullable=True)  # 답안 구조 (문단, 순서 등)

    # Relationships
    problem = relationship("Problem", back_populates="reference_answers")
    issues = relationship("Issue", back_populates="reference_answer", cascade="all, delete-orphan")
    embeddings = relationship("ReferenceAnswerEmbedding", back_populates="reference_answer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReferenceAnswer(id={self.id}, problem_id={self.problem_id})>"


class Issue(Base, TimestampMixin):
    """
    논점 엔티티

    모범답안으로부터 추출된 논점 (주논점, 부논점, 확장논점)
    """
    __tablename__ = "issues"

    id = Column(String(36), primary_key=True)
    reference_answer_id = Column(String(36), ForeignKey("reference_answers.id"), nullable=False)

    issue_type = Column(String(50), nullable=False)  # "main", "sub", "extended"
    title = Column(String(500), nullable=False)  # 논점 제목
    description = Column(Text, nullable=True)  # 논점 설명
    order = Column(Integer, nullable=False, default=0)  # 논점 순서

    # 논점 관련 키워드 및 관련 판례
    keywords = Column(JSON, nullable=True)  # ["소의 이익", "당사자적격"]
    related_cases = Column(JSON, nullable=True)  # 관련 판례

    # Relationships
    reference_answer = relationship("ReferenceAnswer", back_populates="issues")

    def __repr__(self):
        return f"<Issue(id={self.id}, type={self.issue_type}, title={self.title[:30]}...)>"
