"""
설정 패키지

애플리케이션 설정을 관리하는 패키지입니다.
"""

from app.config.settings import get_db_settings

__all__ = ["get_db_settings"]

