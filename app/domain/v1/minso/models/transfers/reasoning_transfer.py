"""
Reasoning Domain - Transfer (DTO)

API 요청/응답 및 레이어 간 전달용 BaseModel.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ========== Enums ==========

class TaskType(str):
    """추론 작업 타입"""
    ISSUE_ANALYSIS = "issue_analysis"
    LOGIC_EVALUATION = "logic_evaluation"
    EXPRESSION_REVIEW = "expression_review"
    COMPREHENSIVE = "comprehensive"


class TaskStatus(str):
    """추론 작업 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ========== ReasoningResult ==========

class IssueAnalysisResult(BaseModel):
    """쟁점 분석 결과"""
    identified_issues: List[str] = Field(..., description="식별된 쟁점 목록")
    missing_issues: List[str] = Field(..., description="누락된 쟁점 목록")
    coverage_rate: float = Field(..., description="쟁점 포함률 (0.0-1.0)")
    details: Dict[str, Any] = Field(default_factory=dict, description="상세 분석")


class LogicEvaluationResult(BaseModel):
    """논리 평가 결과"""
    coherence_score: float = Field(..., description="논리 일관성 점수 (0.0-1.0)")
    argument_strength: float = Field(..., description="논증 강도 (0.0-1.0)")
    weak_points: List[str] = Field(default_factory=list, description="논리적 약점")
    suggestions: List[str] = Field(default_factory=list, description="개선 제안")


class ExpressionReviewResult(BaseModel):
    """표현 검토 결과"""
    clarity_score: float = Field(..., description="명료성 점수 (0.0-1.0)")
    formality_score: float = Field(..., description="격식성 점수 (0.0-1.0)")
    issues: List[Dict[str, str]] = Field(default_factory=list, description="표현 문제")
    improvements: List[Dict[str, str]] = Field(default_factory=list, description="개선안")


class ReasoningResultResponse(BaseModel):
    """추론 결과 응답"""
    id: str
    task_id: str
    result_type: str
    content: Dict[str, Any]
    confidence: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ========== ReasoningTask ==========

class ReasoningTaskCreate(BaseModel):
    """추론 작업 생성 요청"""
    task_type: str = Field(..., description="작업 타입")
    user_answer_id: str = Field(..., description="사용자 답안 ID")
    reference_answer_id: str = Field(..., description="모범 답안 ID")
    problem_id: str = Field(..., description="문제 ID")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추론 설정")


class ReasoningTaskUpdate(BaseModel):
    """추론 작업 수정 요청"""
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ReasoningTaskResponse(BaseModel):
    """추론 작업 응답"""
    id: str
    task_type: str
    status: str
    user_answer_id: str
    reference_answer_id: str
    problem_id: str
    request_id: Optional[str] = None
    source_domain: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    results: List[ReasoningResultResponse] = []

    class Config:
        from_attributes = True


class ReasoningTaskListResponse(BaseModel):
    """추론 작업 목록 응답"""
    total: int
    items: List[ReasoningTaskResponse]


# ========== Analysis Request/Response ==========

class IssueAnalysisRequest(BaseModel):
    """쟁점 분석 요청"""
    user_answer_id: str = Field(..., description="사용자 답안 ID")
    reference_answer_id: str = Field(..., description="모범 답안 ID")
    problem_id: str = Field(..., description="문제 ID")
    save_result: bool = Field(True, description="결과 저장 여부")


class LogicEvaluationRequest(BaseModel):
    """논리 평가 요청"""
    user_answer_id: str = Field(..., description="사용자 답안 ID")
    reference_answer_id: str = Field(..., description="모범 답안 ID")
    problem_id: str = Field(..., description="문제 ID")
    save_result: bool = Field(True, description="결과 저장 여부")


class ExpressionReviewRequest(BaseModel):
    """표현 검토 요청"""
    user_answer_id: str = Field(..., description="사용자 답안 ID")
    save_result: bool = Field(True, description="결과 저장 여부")


class ComprehensiveAnalysisRequest(BaseModel):
    """종합 분석 요청"""
    user_answer_id: str = Field(..., description="사용자 답안 ID")
    reference_answer_id: Optional[str] = Field(None, description="모범 답안 ID (선택사항)")
    problem_id: Optional[str] = Field(None, description="문제 ID (선택사항)")
    save_result: bool = Field(True, description="결과 저장 여부")
    extracted_issues: Optional[List[str]] = Field(None, description="모범답안 없을 때 사용할 논점 목록 (논점 추출 모델 결과)")


class AnalysisResponse(BaseModel):
    """분석 응답"""
    task_id: str
    task_type: str
    status: str
    results: List[ReasoningResultResponse] = []
    summary: Dict[str, Any] = Field(default_factory=dict, description="분석 요약")
