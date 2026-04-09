"""
Legal Answer Review System - FastAPI 메인 애플리케이션
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.minso import reference, submission, reasoning, feedback, training


# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="민사소송법 서술형 답안 첨삭 시스템",
    debug=settings.DEBUG,
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(reference.router, prefix=settings.API_PREFIX)
app.include_router(submission.router, prefix=settings.API_PREFIX)
app.include_router(reasoning.router, prefix=settings.API_PREFIX)
app.include_router(feedback.router, prefix=settings.API_PREFIX)
app.include_router(training.router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    print(f"\n🚀 {settings.APP_NAME} v{settings.APP_VERSION} 시작")
    print(f"   - API Prefix: {settings.API_PREFIX}")
    print(f"   - Debug: {settings.DEBUG}")

    # 데이터베이스 연결 (선택)
    # .env 로드 후 DATABASE_URL 다시 읽기 (클래스 변수는 모듈 로드 시점에 설정되므로)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from app.core.database import get_database
        db = get_database()
        db.connect(database_url)
        print("   ✅ 데이터베이스 연결 완료")
    else:
        print("   ⚠️  DATABASE_URL 없음 (DB 없이 실행)")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    print(f"\n🛑 {settings.APP_NAME} 종료")

    # 데이터베이스 연결 해제
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        from app.core.database import get_database
        db = get_database()
        await db.disconnect()


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": {
            "swagger": f"{settings.API_PREFIX}/docs",
            "redoc": f"{settings.API_PREFIX}/redoc",
            "openapi": f"{settings.API_PREFIX}/openapi.json"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
