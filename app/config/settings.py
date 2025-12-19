"""
애플리케이션 설정

환경 변수에서 설정을 읽어오는 모듈입니다.
"""
import os
from functools import lru_cache
from dataclasses import dataclass


@dataclass
class DatabaseSettings:
    """데이터베이스 설정"""

    host: str
    port: str
    user: str
    password: str
    name: str
    collection_name: str
    sslmode: str = "require"


@lru_cache()
def get_db_settings() -> DatabaseSettings:
    """
    데이터베이스 설정을 반환합니다.

    환경 변수에서 읽어오며, 없으면 기본값을 사용합니다.
    """
    return DatabaseSettings(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "langchain"),
        password=os.getenv("POSTGRES_PASSWORD", "langchain123"),
        name=os.getenv("POSTGRES_DB", "vectordb"),
        collection_name=os.getenv("PGVECTOR_COLLECTION", "langchain_knowledge_base"),
        sslmode=os.getenv("POSTGRES_SSLMODE", "require"),
    )

