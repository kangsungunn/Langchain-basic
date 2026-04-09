"""
Training - Schemas (루트 training/ 폴더)

API 요청/응답 스키마 정의
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class TrainingDataCreate(BaseModel):
    """학습 데이터 생성 요청"""
    problem_id: Optional[str] = None
    reference_answer_id: Optional[str] = None
    user_answer_id: Optional[str] = None
    problem_text: str = Field(..., description="문제 텍스트")
    reference_answer_text: str = Field(..., description="모범답안 텍스트")
    user_answer_text: str = Field(..., description="사용자 답안 텍스트")
    labels: Dict[str, Any] = Field(..., description="라벨")
    meta: Optional[Dict[str, Any]] = None


class TrainingDataResponse(BaseModel):
    """학습 데이터 응답"""
    id: str
    problem_id: Optional[str]
    reference_answer_id: Optional[str]
    user_answer_id: Optional[str]
    problem_text: str
    reference_answer_text: str
    user_answer_text: str
    labels: Dict[str, Any]
    status: str
    meta: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingJobCreate(BaseModel):
    """학습 작업 생성 요청"""
    job_name: str = Field(..., description="작업 이름")
    config: Dict[str, Any] = Field(..., description="학습 설정")
    training_data_ids: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None


class TrainingJobResponse(BaseModel):
    """학습 작업 응답"""
    id: str
    job_name: str
    status: str
    config: Dict[str, Any]
    training_data_ids: Optional[List[str]]
    train_size: Optional[int]
    val_size: Optional[int]
    current_epoch: Optional[int]
    total_epochs: Optional[int]
    progress: Optional[float]
    metrics: Optional[Dict[str, Any]]
    loss_history: Optional[List[float]]
    model_path: Optional[str]
    model_version_id: Optional[str]
    error_message: Optional[str]
    error_traceback: Optional[str]
    meta: Optional[Dict[str, Any]]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelVersionCreate(BaseModel):
    """모델 버전 생성 요청"""
    version: str
    model_path: str
    base_model: str
    metrics: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    training_config: Optional[Dict[str, Any]] = None
    data_info: Optional[Dict[str, Any]] = None


class ModelVersionResponse(BaseModel):
    """모델 버전 응답"""
    id: str
    training_job_id: Optional[str]
    version: str
    model_path: str
    base_model: str
    status: str
    is_active: bool
    metrics: Optional[Dict[str, Any]]
    test_metrics: Optional[Dict[str, Any]]
    description: Optional[str]
    training_config: Optional[Dict[str, Any]]
    data_info: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingDataListResponse(BaseModel):
    """학습 데이터 목록 응답"""
    total: int
    items: List[TrainingDataResponse]


class TrainingJobListResponse(BaseModel):
    """학습 작업 목록 응답"""
    total: int
    items: List[TrainingJobResponse]


class ModelVersionListResponse(BaseModel):
    """모델 버전 목록 응답"""
    total: int
    items: List[ModelVersionResponse]
