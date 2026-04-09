"""
구조화된 로깅

애플리케이션 전역 로거
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from app.core.config import settings


class Logger:
    """
    구조화된 로거

    싱글톤 패턴으로 전역 로거 제공
    """

    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None

    def __init__(self):
        if Logger._instance is not None:
            raise RuntimeError("Logger는 싱글톤입니다. get_instance()를 사용하세요.")

        self._setup_logger()

    @classmethod
    def get_instance(cls) -> 'Logger':
        """
        싱글톤 인스턴스 반환

        Returns:
            Logger 인스턴스
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _setup_logger(self):
        """로거 설정"""
        # 로거 생성
        self._logger = logging.getLogger(settings.APP_NAME)
        self._logger.setLevel(getattr(logging, settings.LOG_LEVEL))

        # 기존 핸들러 제거
        self._logger.handlers.clear()

        # 포맷터
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 콘솔 핸들러 (Windows 인코딩 문제 해결)
        # Windows에서 이모지 출력을 위한 인코딩 처리
        try:
            if sys.platform == 'win32':
                # Windows에서 UTF-8 모드 활성화
                import io
                if hasattr(sys.stdout, 'reconfigure'):
                    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                else:
                    # Python 3.7 이하 호환
                    sys.stdout = io.TextIOWrapper(
                        sys.stdout.buffer,
                        encoding='utf-8',
                        errors='replace',
                        line_buffering=True
                    )
        except Exception:
            pass  # 인코딩 설정 실패 시 무시

        # StreamHandler 생성 (UTF-8 인코딩 보장)
        try:
            if sys.platform == 'win32':
                import io
                # UTF-8로 인코딩된 스트림 생성
                utf8_stream = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding='utf-8',
                    errors='replace',
                    line_buffering=True
                )
                console_handler = logging.StreamHandler(utf8_stream)
            else:
                console_handler = logging.StreamHandler(sys.stdout)
        except Exception:
            # 폴백: 기본 StreamHandler 사용
            console_handler = logging.StreamHandler(sys.stdout)

        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # 파일 핸들러 (선택)
        if settings.LOG_FILE:
            log_path = settings.PROJECT_ROOT / settings.LOG_FILE
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs):
        """디버그 로그"""
        self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """정보 로그"""
        self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """경고 로그"""
        self._logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """에러 로그"""
        self._logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """치명적 로그"""
        self._logger.critical(message, extra=kwargs)

    def exception(self, message: str, **kwargs):
        """예외 로그 (스택 트레이스 포함)"""
        self._logger.exception(message, extra=kwargs)


# 전역 함수 (편의성)
def get_logger() -> Logger:
    """
    전역 Logger 인스턴스 반환

    Returns:
        Logger 인스턴스
    """
    return Logger.get_instance()


# 간편 함수
def debug(message: str, **kwargs):
    """디버그 로그"""
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs):
    """정보 로그"""
    get_logger().info(message, **kwargs)


def warning(message: str, **kwargs):
    """경고 로그"""
    get_logger().warning(message, **kwargs)


def error(message: str, **kwargs):
    """에러 로그"""
    get_logger().error(message, **kwargs)


def critical(message: str, **kwargs):
    """치명적 로그"""
    get_logger().critical(message, **kwargs)


def exception(message: str, **kwargs):
    """예외 로그"""
    get_logger().exception(message, **kwargs)
