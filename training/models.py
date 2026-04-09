"""
Training - 모델 (루트 training/ 폴더)

학습 데이터 및 작업 관리 엔티티.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, ForeignKey, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.orm import relationship
import enum

from app.core.database.connection import Base
from app.core.database.mixin import TimestampMixin


class TrainingDataStatus(str, enum.Enum):
    """학습 데이터 상태"""
    PENDING = "pending"
    PROCESSED = "processed"
    USED = "used"


class TrainingJobStatus(str, enum.Enum):
    """학습 작업 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelVersionStatus(str, enum.Enum):
    """모델 버전 상태"""
    TRAINING = "training"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class TrainingData(Base, TimestampMixin):
    """학습 데이터 엔티티"""
    __tablename__ = "training_data"

    id = Column(String(36), primary_key=True)
    problem_id = Column(String(36), nullable=True)
    reference_answer_id = Column(String(36), nullable=True)
    user_answer_id = Column(String(36), nullable=True)
    problem_text = Column(Text, nullable=False)
    reference_answer_text = Column(Text, nullable=False)
    user_answer_text = Column(Text, nullable=False)
    labels = Column(JSON, nullable=False)
    status = Column(SQLEnum(TrainingDataStatus), nullable=False, default=TrainingDataStatus.PENDING)
    meta = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<TrainingData(id={self.id}, status={self.status.value})>"


class TrainingJob(Base, TimestampMixin):
    """학습 작업 엔티티"""
    __tablename__ = "training_jobs"

    id = Column(String(36), primary_key=True)
    job_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(TrainingJobStatus), nullable=False, default=TrainingJobStatus.PENDING)
    config = Column(JSON, nullable=False)
    training_data_ids = Column(JSON, nullable=True)
    train_size = Column(Integer, nullable=True)
    val_size = Column(Integer, nullable=True)
    current_epoch = Column(Integer, nullable=True, default=0)
    total_epochs = Column(Integer, nullable=True)
    progress = Column(Float, nullable=True, default=0.0)
    metrics = Column(JSON, nullable=True)
    loss_history = Column(JSON, nullable=True)
    model_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    model_versions = relationship(
        "ModelVersion",
        foreign_keys="ModelVersion.training_job_id",
        back_populates="training_job"
    )

    def __repr__(self):
        return f"<TrainingJob(id={self.id}, status={self.status.value}, progress={self.progress})>"


class ModelVersion(Base, TimestampMixin):
    """모델 버전 엔티티"""
    __tablename__ = "model_versions"

    id = Column(String(36), primary_key=True)
    training_job_id = Column(String(36), ForeignKey("training_jobs.id"), nullable=True)
    version = Column(String(50), nullable=False, unique=True)
    model_path = Column(String(500), nullable=False)
    base_model = Column(String(255), nullable=False)
    status = Column(SQLEnum(ModelVersionStatus), nullable=False, default=ModelVersionStatus.TRAINING)
    is_active = Column(Boolean, nullable=False, default=False)
    metrics = Column(JSON, nullable=True)
    test_metrics = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    training_config = Column(JSON, nullable=True)
    data_info = Column(JSON, nullable=True)

    training_job = relationship(
        "TrainingJob",
        foreign_keys=[training_job_id],
        back_populates="model_versions"
    )

    def __repr__(self):
        return f"<ModelVersion(id={self.id}, version={self.version}, status={self.status.value})>"
