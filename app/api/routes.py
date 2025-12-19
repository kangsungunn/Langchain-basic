"""
API 라우트

FastAPI 공통 엔드포인트를 정의합니다.
채팅 관련 엔드포인트는 app.router.chat_router를 참고하세요.
"""

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""

    status: str
    message: str


# 라우터 생성
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    return HealthResponse(status="healthy", message="RAG Chatbot API is running")
