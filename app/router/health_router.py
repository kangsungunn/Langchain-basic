"""
헬스체크 라우터

서버 상태를 확인하는 엔드포인트입니다.
"""
from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    message: str


health_router = APIRouter(tags=["health"])


@health_router.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    return HealthResponse(
        status="healthy",
        message="RAG Chatbot API is running"
    )

