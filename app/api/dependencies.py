"""
API 의존성

FastAPI의 의존성 주입을 위한 함수들을 정의합니다.
"""
from functools import lru_cache

from app.models.base import BaseLLM, BaseEmbeddings
from app.models.factory import ModelFactory
from app.services.rag_service import RAGService
from app.services.chat_service import ChatService
from app.config.settings import get_db_settings
from app.repository.base import BaseVectorRepository
from app.repository.vector_store_repository import PGVectorRepository
from langchain_postgres import PGVector


@lru_cache()
def get_llm() -> BaseLLM:
    """
    LLM 모델 인스턴스를 반환합니다 (싱글톤).

    환경 변수나 설정에 따라 적절한 모델을 생성합니다.

    환경 변수:
        LLM_PROVIDER: 모델 제공자 (openai, local_llama 등)
        MIDM_MODEL_PATH: Midm 모델 경로 (기본값: app/models/midm)

    예시:
        # OpenAI 사용
        export LLM_PROVIDER=openai
        export OPENAI_API_KEY=sk-...

        # 로컬 Midm 모델 사용
        export LLM_PROVIDER=local_llama
        export MIDM_MODEL_PATH=app/models/midm
    """
    return ModelFactory.create_llm()


@lru_cache()
def get_embeddings() -> BaseEmbeddings:
    """
    Embeddings 모델 인스턴스를 반환합니다 (싱글톤).

    환경 변수나 설정에 따라 적절한 모델을 생성합니다.
    """
    return ModelFactory.create_embeddings()


@lru_cache()
def get_vector_store() -> PGVector:
    """
    벡터 스토어 인스턴스를 반환합니다 (싱글톤).
    """
    db_settings = get_db_settings()
    embeddings_provider = get_embeddings()

    # SSL 모드가 있는 경우 connection string에 추가
    ssl_param = f"?sslmode={db_settings.sslmode}" if db_settings.sslmode else ""
    connection_string = (
        f"postgresql+psycopg2://{db_settings.user}:{db_settings.password}"
        f"@{db_settings.host}:{db_settings.port}/{db_settings.name}{ssl_param}"
    )

    return PGVector(
        embeddings=embeddings_provider.get_embeddings(),
        collection_name=db_settings.collection_name,
        connection=connection_string,
        use_jsonb=True,
    )


@lru_cache()
def get_repository() -> BaseVectorRepository:
    """
    벡터 스토어 Repository 인스턴스를 반환합니다 (싱글톤).
    """
    vector_store = get_vector_store()
    return PGVectorRepository(vector_store=vector_store)


def get_rag_service() -> RAGService:
    """
    RAG 서비스 인스턴스를 반환합니다.
    """
    llm = get_llm()
    embeddings = get_embeddings()
    repository = get_repository()

    return RAGService(
        llm=llm,
        embeddings=embeddings,
        repository=repository,
    )


def get_chat_service() -> ChatService:
    """
    채팅 서비스 인스턴스를 반환합니다.
    """
    rag_service = get_rag_service()
    return ChatService(rag_service=rag_service)

