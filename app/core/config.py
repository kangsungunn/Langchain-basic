"""
애플리케이션 설정

환경 변수 기반 설정 관리
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """
    애플리케이션 설정

    환경 변수 또는 기본값 사용
    """

    # 프로젝트 루트
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # 애플리케이션
    APP_NAME = "Legal Answer Review System"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # 데이터베이스
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))

    # ML 모델
    MODEL_PATH = os.getenv(
        "MODEL_PATH",
        str(PROJECT_ROOT / "artifacts" / "models" / "finetuned" / "legal" / "final")
    )
    USE_GPU = os.getenv("USE_GPU", "true").lower() == "true"

    # ExaOne 모델 경로 (코드 생성용)
    EXAONE_BASE_MODEL_PATH = os.getenv(
        "EXAONE_BASE_MODEL_PATH",
        str(PROJECT_ROOT / "artifacts" / "models" / "base" / "exaone-2.4b")
    )
    EXAONE_ADAPTER_PATH = os.getenv("EXAONE_ADAPTER_PATH", None)  # LoRA 어댑터 경로 (선택)
    # ExaOne 비활성화 (True면 로드·호출 안 함. PDF/OCR/나머지 파이프라인만 검증할 때 사용)
    SKIP_EXAONE = os.getenv("SKIP_EXAONE", "false").lower() in ("true", "1", "yes")
    # ExaOne 전용 워커 URL (설정 시 메인 프로세스에서 ExaOne 로드 안 함, HTTP로 워커 호출. 웹서버와 같은 프로세스에서 CUDA 멈춤 회피)
    EXAONE_WORKER_URL: Optional[str] = os.getenv("EXAONE_WORKER_URL", "").strip() or None

    # 임베딩 모델 경로 (artifacts/embedding_models 아래 모델 사용, 768차원 호환)
    # 예: jhgan--ko-sroberta-multitask (Sentence-BERT 형식)
    EMBEDDING_MODEL_PATH = os.getenv(
        "EMBEDDING_MODEL_PATH",
        os.getenv(
            "KOELECTRA_EMBEDDING_MODEL_PATH",  # 하위 호환
            str(PROJECT_ROOT / "artifacts" / "embedding_models" / "jhgan--ko-sroberta-multitask")
        )
    )

    # API
    API_PREFIX = "/api/v1"
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    # 로깅
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

    # MCP
    MCP_TIMEOUT = float(os.getenv("MCP_TIMEOUT", "30.0"))

    @classmethod
    def load_from_env(cls, env_file: str = ".env"):
        """
        .env 파일에서 환경 변수 로드

        Args:
            env_file: .env 파일 경로
        """
        env_path = cls.PROJECT_ROOT / env_file

        if not env_path.exists():
            try:
                print(f"⚠️  .env 파일이 없습니다: {env_path}")
                print("💡 .env.example을 복사하여 .env 파일을 생성하세요.")
            except UnicodeEncodeError:
                print(f"[WARNING] .env file not found: {env_path}")
                print("[TIP] Copy .env.example to create .env file.")
            return

        # python-dotenv가 있으면 사용
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
            try:
                print(f"✅ .env 파일 로드 완료: {env_path}")
            except UnicodeEncodeError:
                print(f"[OK] Loaded .env file: {env_path}")
        except ImportError:
            try:
                print("⚠️  python-dotenv가 설치되지 않았습니다.")
                print("💡 수동으로 환경 변수를 설정하거나 python-dotenv를 설치하세요.")
            except UnicodeEncodeError:
                print("[WARNING] python-dotenv is not installed.")
                print("[TIP] Set environment variables manually or install python-dotenv.")

    @classmethod
    def print_config(cls):
        """설정 출력 (디버깅용)"""
        print("\n" + "="*60)
        print(f"  {cls.APP_NAME} - 설정")
        print("="*60)
        print(f"  버전: {cls.APP_VERSION}")
        print(f"  디버그: {cls.DEBUG}")
        print(f"  데이터베이스: {cls.DATABASE_URL[:30]}..." if cls.DATABASE_URL else "  데이터베이스: None")
        print(f"  모델 경로: {cls.MODEL_PATH}")
        print(f"  GPU 사용: {cls.USE_GPU}")
        print(f"  로그 레벨: {cls.LOG_LEVEL}")
        print("="*60 + "\n")


# 전역 설정 인스턴스
settings = Settings()

# .env 파일 자동 로드
settings.load_from_env()
