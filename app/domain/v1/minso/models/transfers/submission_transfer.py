"""
Submission Domain - Transfer (DTO)

API 요청/응답 및 레이어 간 전달용 BaseModel.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ========== Enums ==========

class SubmissionType(str):
    """제출 타입"""
    TEXT = "text"
    IMAGE = "image"


class SubmissionStatus(str):
    """제출 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ========== AnswerStructure ==========

class ParagraphInfo(BaseModel):
    """문단 정보"""
    order: int = Field(..., description="문단 순서")
    content: str = Field(..., description="문단 내용")


class SentenceInfo(BaseModel):
    """문장 정보"""
    paragraph: int = Field(..., description="소속 문단 번호")
    order: int = Field(..., description="문장 순서")
    content: str = Field(..., description="문장 내용")


class AnswerStructureResponse(BaseModel):
    """답안 구조 응답"""
    id: str
    user_answer_id: str
    paragraphs: Optional[List[ParagraphInfo]] = None
    sentences: Optional[List[SentenceInfo]] = None
    paragraph_count: Optional[Dict[str, int]] = None
    sentence_count: Optional[Dict[str, Any]] = None
    word_count: Optional[Dict[str, int]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== UserAnswer ==========

class UserAnswerBase(BaseModel):
    """사용자 답안 기본"""
    problem_id: str = Field(..., description="문제 ID")
    submission_type: str = Field("text", description="제출 타입: text, image")


class UserAnswerCreateText(UserAnswerBase):
    """텍스트 답안 생성 요청"""
    submission_type: str = Field("text", description="제출 타입")
    content: str = Field(..., description="답안 텍스트")


class UserAnswerCreateImage(UserAnswerBase):
    """이미지 답안 생성 요청"""
    submission_type: str = Field("image", description="제출 타입")
    image_path: str = Field(..., description="업로드된 이미지 경로")
    meta: Optional[Dict[str, Any]] = Field(None, description="메타 (예: question_label로 설문 (1)/(2) 등 지정)")


class UserAnswerUpdate(BaseModel):
    """사용자 답안 수정 요청"""
    processed_content: Optional[str] = None
    status: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class UserAnswerResponse(BaseModel):
    """사용자 답안 응답"""
    id: str
    problem_id: str
    submission_type: str
    status: str
    raw_content: Optional[str] = None
    processed_content: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    structure: Optional[AnswerStructureResponse] = None

    class Config:
        from_attributes = True


class UserAnswerListResponse(BaseModel):
    """사용자 답안 목록 응답"""
    total: int
    items: List[UserAnswerResponse]


# ========== Structure Analysis ==========

class StructureAnalysisRequest(BaseModel):
    """구조 분석 요청"""
    auto_save: bool = Field(True, description="자동 저장 여부")


class StructureAnalysisResponse(BaseModel):
    """구조 분석 응답"""
    user_answer_id: str
    structure: AnswerStructureResponse
    analysis_summary: Dict[str, Any] = Field(..., description="분석 요약")


# ========== OCR ==========

class OCRRequest(BaseModel):
    """OCR 요청"""
    confidence_threshold: float = Field(0.6, description="신뢰도 임계값 (0.0-1.0)")


class OCRResponse(BaseModel):
    """OCR 응답"""
    user_answer_id: str
    extracted_text: str
    confidence: float = Field(..., description="평균 신뢰도")
    status: str
    meta: Dict[str, Any] = Field(..., description="OCR 메타데이터")


# ========== Analyze and Feedback (Phase 1: 제출 → 추론 → 피드백 한 번에) ==========

class AnalyzeAndFeedbackResponse(BaseModel):
    """답안 분석 및 피드백 생성 통합 응답 (제출 → 추론 → 피드백 파이프라인)"""
    user_answer_id: str = Field(..., description="사용자 답안 ID")
    reasoning_task_id: str = Field(..., description="추론 작업 ID")
    analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="추론 분석 요약")
    feedback: Any = Field(..., description="생성된 피드백 (FeedbackResponse)")  # feedback_transfer 의존 시 순환 참조 방지
    message: str = Field("분석 및 피드백 생성이 완료되었습니다.", description="안내 메시지")
    # 피드백이 어떤 문제·설문에 해당하는지 특정
    problem_id: Optional[str] = Field(None, description="문제 ID")
    problem_title: Optional[str] = Field(None, description="문제 제목")
    question_label: Optional[str] = Field(None, description="설문 구분 (예: 설문 (1), 설문 (2)) — user_answer.meta에서 조회")
