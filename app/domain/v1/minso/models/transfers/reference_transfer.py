"""
Reference Domain - Transfer (DTO)

API 요청/응답 및 레이어 간 전달용 BaseModel.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ========== Issue ==========

class IssueBase(BaseModel):
    """논점 기본"""
    issue_type: str = Field(..., description="논점 타입: main, sub, extended")
    title: str = Field(..., description="논점 제목")
    description: Optional[str] = Field(None, description="논점 설명")
    order: int = Field(0, description="논점 순서")
    keywords: Optional[List[str]] = Field(None, description="관련 키워드")
    related_cases: Optional[List[str]] = Field(None, description="관련 판례")


class IssueCreate(IssueBase):
    """논점 생성 요청"""
    reference_answer_id: str = Field(..., description="모범답안 ID")


class IssueUpdate(BaseModel):
    """논점 수정 요청"""
    issue_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    keywords: Optional[List[str]] = None
    related_cases: Optional[List[str]] = None


class IssueResponse(IssueBase):
    """논점 응답"""
    id: str
    reference_answer_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== ReferenceAnswer ==========

class ReferenceAnswerBase(BaseModel):
    """모범답안 기본"""
    content: str = Field(..., description="모범답안 전문")
    structure: Optional[Dict[str, Any]] = Field(None, description="답안 구조")


class ReferenceAnswerCreate(ReferenceAnswerBase):
    """모범답안 생성 요청"""
    problem_id: str = Field(..., description="문제 ID")


class ReferenceAnswerUpdate(BaseModel):
    """모범답안 수정 요청"""
    content: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None


class ReferenceAnswerResponse(ReferenceAnswerBase):
    """모범답안 응답"""
    id: str
    problem_id: str
    created_at: datetime
    updated_at: datetime
    issues: List[IssueResponse] = []

    class Config:
        from_attributes = True


# ========== Problem ==========

class ProblemBase(BaseModel):
    """문제 기본"""
    title: str = Field(..., description="문제 제목")
    content: str = Field(..., description="문제 전문")
    meta: Optional[Dict[str, Any]] = Field(None, description="메타데이터")


class ProblemCreate(ProblemBase):
    """문제 생성 요청"""
    pass


class ProblemUpdate(BaseModel):
    """문제 수정 요청"""
    title: Optional[str] = None
    content: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class ProblemResponse(ProblemBase):
    """문제 응답"""
    id: str
    created_at: datetime
    updated_at: datetime
    reference_answers: List[ReferenceAnswerResponse] = []

    class Config:
        from_attributes = True


class ProblemListResponse(BaseModel):
    """문제 목록 응답"""
    total: int
    items: List[ProblemResponse]


# ========== Issue Extraction ==========

class IssueExtractionRequest(BaseModel):
    """논점 추출 요청"""
    reference_answer_id: str = Field(..., description="모범답안 ID")
    auto_save: bool = Field(True, description="자동 저장 여부")


class IssueExtractionResponse(BaseModel):
    """논점 추출 응답"""
    reference_answer_id: str
    extracted_issues: List[IssueResponse]
    total_extracted: int
