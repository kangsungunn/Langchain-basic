"""
데이터베이스 연결 및 세션 관리 (호환성 레이어)

기존 코드와의 호환성을 위해 유지.
`from app.core.database import ...` 형태의 import가 동작하도록 패키지를 re-export.
"""

from app.core.database import (
    Base,
    get_session,
    SessionManager,
    get_session_factory,
    DatabaseConnection,
    get_database,
    TimestampMixin,
    SoftDeleteMixin,
    StatusMixin,
)

__all__ = [
    "Base",
    "get_session",
    "SessionManager",
    "get_session_factory",
    "DatabaseConnection",
    "get_database",
    "TimestampMixin",
    "SoftDeleteMixin",
    "StatusMixin",
]
