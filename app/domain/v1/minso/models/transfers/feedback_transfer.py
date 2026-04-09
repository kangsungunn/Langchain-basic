"""
Feedback Domain - Transfer (DTO)

API 요청/응답 및 레이어 간 전달용 BaseModel.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ========== Enums ==========

class FeedbackType(str):
    """피드백 타입"""
    ISSUE = "issue"
    LOGIC = "logic"
    EXPRESSION = "expression"
    COMPREHENSIVE = "comprehensive"


class FeedbackSeverity(str):
    """피드백 심각도"""
    INFO = "info"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    CRITICAL = "critical"


# ========== FeedbackItem ==========

class FeedbackItemBase(BaseModel):
    """피드백 항목 기본"""
    item_type: str = Field(..., description="항목 타입")
    severity: str = Field("info", description="심각도")
    location: Optional[Dict[str, Any]] = None
    title: str = Field(..., description="제목")
    description: str = Field(..., description="설명")
    suggestion: Optional[str] = None
    score: Optional[float] = None


class FeedbackItemCreate(FeedbackItemBase):
    """피드백 항목 생성 요청"""
    pass


class FeedbackItemResponse(FeedbackItemBase):
    """피드백 항목 응답"""
    id: str
    feedback_id: str
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Feedback ==========

class FeedbackBase(BaseModel):
    """피드백 기본"""
    user_answer_id: str = Field(..., description="사용자 답안 ID")
    feedback_type: str = Field(..., description="피드백 타입")


class FeedbackCreate(FeedbackBase):
    """피드백 생성 요청"""
    reasoning_task_id: Optional[str] = None
    overall_score: Optional[float] = None
    scores: Optional[Dict[str, float]] = None
    summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None


class FeedbackUpdate(BaseModel):
    """피드백 수정 요청"""
    overall_score: Optional[float] = None
    scores: Optional[Dict[str, float]] = None
    summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None


class FeedbackResponse(BaseModel):
    """피드백 응답"""
    id: str
    user_answer_id: str
    reasoning_task_id: Optional[str] = None
    feedback_type: str
    overall_score: Optional[float] = None
    scores: Optional[Dict[str, float]] = None
    summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    items: List[FeedbackItemResponse] = []

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    """피드백 목록 응답"""
    total: int
    items: List[FeedbackResponse]


# ========== Generation ==========

class GenerateFeedbackRequest(BaseModel):
    """피드백 생성 요청"""
    user_answer_id: str = Field(..., description="사용자 답안 ID")
    reasoning_task_id: str = Field(..., description="추론 작업 ID")
    feedback_type: str = Field(..., description="피드백 타입: issue, logic, expression, comprehensive")
    include_suggestions: bool = Field(True, description="개선 제안 포함 여부")


class GenerateFeedbackResponse(BaseModel):
    """피드백 생성 응답"""
    feedback: FeedbackResponse
    generation_summary: Dict[str, Any] = Field(..., description="생성 요약")


# ========== Report ==========

class FeedbackReportRequest(BaseModel):
    """피드백 리포트 생성 요청"""
    user_answer_id: str = Field(..., description="사용자 답안 ID")
    include_comprehensive: bool = Field(True, description="종합 피드백 포함 여부")


class FeedbackReportResponse(BaseModel):
    """피드백 리포트 응답"""
    user_answer_id: str
    feedbacks: List[FeedbackResponse]
    report_summary: Dict[str, Any] = Field(..., description="리포트 요약")
    generated_at: datetime


# ========== Feedback Correction (학습용) ==========

class FeedbackCorrectionCreate(BaseModel):
    """피드백에 대한 사용자 정정/추가 요청 (학습용)"""
    correction_type: str = Field(..., description="correction(정정) | addition(추가/강조)")
    content: str = Field(..., min_length=1, description="의견 내용")


class FeedbackCorrectionResponse(BaseModel):
    """피드백 정정 응답"""
    id: str
    feedback_id: str
    correction_type: str
    content: str
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
