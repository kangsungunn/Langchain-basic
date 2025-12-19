"""
OpenAI 모델 제공자

OpenAI의 LLM과 Embeddings를 구현합니다.
"""
import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.models.base import BaseLLM, BaseEmbeddings


class OpenAILLM(BaseLLM):
    """OpenAI LLM 구현"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        OpenAI LLM을 초기화합니다.

        Args:
            model_name: 모델 이름 (기본값: gpt-4o-mini)
            temperature: 온도 설정 (기본값: 0.7)
            api_key: OpenAI API 키 (기본값: 환경 변수에서 읽음)
            **kwargs: 추가 설정
        """
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.kwargs = kwargs

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다!")

        self._model: Optional[ChatOpenAI] = None

    def get_model(self) -> ChatOpenAI:
        """LLM 모델 인스턴스를 반환합니다."""
        if self._model is None:
            self._model = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=self.api_key,
                **self.kwargs
            )
        return self._model

    def get_model_name(self) -> str:
        """모델 이름을 반환합니다."""
        return self.model_name

    def get_model_config(self) -> dict[str, Any]:
        """모델 설정을 반환합니다."""
        return {
            "provider": "openai",
            "model": self.model_name,
            "temperature": self.temperature,
            **self.kwargs
        }


class OpenAIEmbeddingsProvider(BaseEmbeddings):
    """OpenAI Embeddings 구현"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        OpenAI Embeddings를 초기화합니다.

        Args:
            model_name: 모델 이름 (기본값: text-embedding-3-small)
            api_key: OpenAI API 키 (기본값: 환경 변수에서 읽음)
            **kwargs: 추가 설정
        """
        self.model_name = model_name or os.getenv(
            "OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small"
        )
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.kwargs = kwargs

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다!")

        self._embeddings: Optional[OpenAIEmbeddings] = None

    def get_embeddings(self) -> OpenAIEmbeddings:
        """Embeddings 인스턴스를 반환합니다."""
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                model=self.model_name,
                api_key=self.api_key,
                **self.kwargs
            )
        return self._embeddings

    def get_model_name(self) -> str:
        """모델 이름을 반환합니다."""
        return self.model_name

    def get_model_config(self) -> dict[str, Any]:
        """모델 설정을 반환합니다."""
        return {
            "provider": "openai",
            "model": self.model_name,
            **self.kwargs
        }

