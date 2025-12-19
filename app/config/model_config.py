"""
모델 설정

로컬 모델 및 제공자별 설정을 관리합니다.
"""
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class MidmModelConfig:
    """Midm 모델 설정"""

    model_path: str
    model_name: str
    device: str
    max_new_tokens: int
    temperature: float
    top_p: float
    trust_remote_code: bool


@lru_cache()
def get_midm_config() -> MidmModelConfig:
    """
    Midm 모델 설정을 반환합니다.

    환경 변수에서 읽어오며, 없으면 기본값을 사용합니다.
    """
    return MidmModelConfig(
        model_path=os.getenv("MIDM_MODEL_PATH", "app/models/midm"),
        model_name=os.getenv("MIDM_MODEL_NAME", "midm-2.0-mini-instruct"),
        device=os.getenv("MIDM_DEVICE", "auto"),
        max_new_tokens=int(os.getenv("MIDM_MAX_NEW_TOKENS", "512")),
        temperature=float(os.getenv("MIDM_TEMPERATURE", "0.7")),
        top_p=float(os.getenv("MIDM_TOP_P", "0.9")),
        trust_remote_code=True,  # Mi:dm 필수
    )

