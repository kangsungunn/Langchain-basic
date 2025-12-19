"""
FastAPI 서버 - 리팩토링된 버전

의존성 주입을 사용한 깔끔한 구조의 API 서버입니다.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router.chat_router import chat_router
from app.router.health_router import health_router
from app.api.dependencies import get_llm, get_embeddings, get_vector_store


# FastAPI 앱 초기화
app = FastAPI(
    title="LangChain RAG Chatbot API",
    description="RAG를 사용한 지능형 챗봇 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 (기능별로 분리)
app.include_router(health_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    """API 루트 엔드포인트 - API 정보 반환"""
    return {
        "name": "LangChain RAG Chatbot API",
        "version": "1.0.0",
        "description": "RAG를 사용한 지능형 챗봇 API",
        "endpoints": {
            "health": "/health",
            "chat_rag": "/api/chat/rag",
            "chat_general": "/api/chat/general",
            "chat_legacy": "/api/chat"
        },
        "docs": "/docs"
    }


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행 - 모델 초기화"""
    print("🚀 FastAPI 서버 시작 중...")

    # 의존성 초기화 (캐시에 저장됨)
    llm = get_llm()
    embeddings = get_embeddings()
    vector_store = get_vector_store()

    print(f"✅ LLM 모델: {llm.get_model_name()}")
    print(f"✅ Embeddings 모델: {embeddings.get_model_name()}")
    print(f"✅ 벡터 스토어 초기화 완료")
    print("✅ 서버 준비 완료!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

