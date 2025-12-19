"""
모델 베이스 클래스

LLM과 Embeddings의 추상 인터페이스를 정의합니다.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings


class BaseLLM(ABC):
    """LLM 모델의 추상 인터페이스"""

    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """LLM 모델 인스턴스를 반환합니다."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """모델 이름을 반환합니다."""
        pass

    @abstractmethod
    def get_model_config(self) -> dict[str, Any]:
        """모델 설정을 반환합니다."""
        pass


class BaseEmbeddings(ABC):
    """Embeddings 모델의 추상 인터페이스"""

    @abstractmethod
    def get_embeddings(self) -> Embeddings:
        """Embeddings 인스턴스를 반환합니다."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """모델 이름을 반환합니다."""
        pass

    @abstractmethod
    def get_model_config(self) -> dict[str, Any]:
        """모델 설정을 반환합니다."""
        pass

