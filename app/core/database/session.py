"""
데이터베이스 세션 관리
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import InterfaceError, DBAPIError

from .connection import get_database

logger = logging.getLogger(__name__)


# 세션 팩토리 (lazy initialization)
_session_factory: async_sessionmaker = None


def get_session_factory() -> async_sessionmaker:
    """
    세션 팩토리 반환

    Returns:
        async_sessionmaker
    """
    global _session_factory

    # 매번 엔진 확인 (연결이 나중에 될 수 있음)
    db = get_database()
    engine = db.get_engine()

    if engine is None:
        raise RuntimeError(
            "데이터베이스 엔진이 초기화되지 않았습니다. "
            "서버 시작 시 DATABASE_URL이 설정되어 있는지 확인하세요."
        )

    # 엔진이 변경되었거나 세션 팩토리가 없으면 재생성
    if _session_factory is None or _session_factory.kw.get('bind') != engine:
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    데이터베이스 세션 의존성

    FastAPI 의존성 주입용

    Yields:
        AsyncSession
    """
    factory = get_session_factory()

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except (InterfaceError, DBAPIError) as rollback_e:
                # 연결이 이미 끊긴 경우 rollback 실패 가능. 원래 예외만 전파
                logger.warning("세션 rollback 실패 (연결 끊김 등): %s", rollback_e)
            raise
        finally:
            try:
                await session.close()
            except (InterfaceError, DBAPIError) as close_e:
                logger.warning("세션 close 실패: %s", close_e)


class SessionManager:
    """
    세션 관리자

    컨텍스트 매니저 패턴
    """

    def __init__(self):
        self.session: AsyncSession = None

    async def __aenter__(self) -> AsyncSession:
        """컨텍스트 진입"""
        factory = get_session_factory()
        self.session = factory()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 종료"""
        if exc_type is not None:
            await self.session.rollback()
        else:
            await self.session.commit()

        await self.session.close()
