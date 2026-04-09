"""
데이터베이스 연결 관리

NeonDB (PostgreSQL) 연결
"""

from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from app.core.config import settings
from app.core.database.base import Base  # 새로운 Base 사용 (DeclarativeBase)


class DatabaseConnection:
    """
    데이터베이스 연결 관리 (싱글톤)
    """

    _instance: Optional['DatabaseConnection'] = None
    _engine: Optional[AsyncEngine] = None

    def __init__(self):
        if DatabaseConnection._instance is not None:
            raise RuntimeError("DatabaseConnection은 싱글톤입니다. get_instance()를 사용하세요.")

        self._engine = None
        self._is_connected = False

    @classmethod
    def get_instance(cls) -> 'DatabaseConnection':
        """
        싱글톤 인스턴스 반환

        Returns:
            DatabaseConnection 인스턴스
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connect(self, database_url: Optional[str] = None) -> AsyncEngine:
        """
        데이터베이스 연결

        Args:
            database_url: 데이터베이스 URL (None이면 설정에서 가져옴)

        Returns:
            AsyncEngine
        """
        if self._engine is not None and self._is_connected:
            print("✅ 데이터베이스가 이미 연결되어 있습니다.")
            return self._engine

        try:
            # DATABASE_URL 가져오기
            url = database_url or settings.DATABASE_URL

            if not url:
                print("⚠️  DATABASE_URL이 설정되지 않았습니다.")
                print("💡 .env 파일에 DATABASE_URL을 설정하세요.")
                return None

            # asyncpg는 대부분의 쿼리 파라미터를 지원하지 않으므로 모두 제거
            # ssl 설정만 connect_args에 추가
            from urllib.parse import urlparse, parse_qs, urlunparse
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # sslmode 처리 (asyncpg는 ssl 파라미터 사용)
            connect_args = {}
            if 'sslmode' in query_params:
                sslmode = query_params['sslmode'][0]
                if sslmode in ['require', 'prefer', 'allow']:
                    connect_args['ssl'] = True
                elif sslmode == 'disable':
                    connect_args['ssl'] = False

            # URL 재구성 (모든 쿼리 파라미터 제거 - asyncpg가 지원하지 않음)
            clean_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                '',  # 모든 쿼리 파라미터 제거
                parsed.fragment
            ))

            print(f"🔄 데이터베이스 연결 중...")

            # 비동기 엔진 생성
            self._engine = create_async_engine(
                clean_url,
                echo=settings.DB_ECHO,  # SQL 로그 출력 여부
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_pre_ping=True,  # 연결 확인
                pool_recycle=1200,  # 20분 (종합 분석 등 장시간 요청 동안 연결 유지)
                connect_args=connect_args if connect_args else None,
            )

            self._is_connected = True
            print(f"✅ 데이터베이스 연결 완료")

            return self._engine

        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            self._engine = None
            self._is_connected = False
            return None

    async def disconnect(self):
        """
        데이터베이스 연결 해제
        """
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._is_connected = False
            print("✅ 데이터베이스 연결 해제 완료")

    def get_engine(self) -> Optional[AsyncEngine]:
        """
        엔진 반환

        Returns:
            AsyncEngine 또는 None
        """
        return self._engine

    def is_connected(self) -> bool:
        """
        연결 상태 확인

        Returns:
            bool: 연결 여부
        """
        return self._is_connected


# 전역 함수
def get_database() -> DatabaseConnection:
    """
    전역 DatabaseConnection 인스턴스 반환

    Returns:
        DatabaseConnection 인스턴스
    """
    return DatabaseConnection.get_instance()


# Base를 export (호환성을 위해)
__all__ = ["DatabaseConnection", "get_database", "Base"]
