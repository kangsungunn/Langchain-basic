"""
커스텀 모델 제공자

사용자가 직접 주입할 커스텀 모델을 위한 인터페이스입니다.
"""
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from app.models.base import BaseLLM, BaseEmbeddings


class CustomLLM(BaseLLM):
    """커스텀 LLM 구현

    사용자가 직접 모델을 주입할 수 있도록 합니다.
    """

    def __init__(
        self,
        model: Optional[BaseChatModel] = None,
        model_name: Optional[str] = None,
        **kwargs
    ):
        """
        커스텀 LLM을 초기화합니다.

        Args:
            model: 직접 주입할 LangChain BaseChatModel 인스턴스
            model_name: 모델 이름 (기본값: custom)
            **kwargs: 추가 설정
        """
        if model is None:
            raise ValueError("커스텀 LLM을 사용하려면 model 인스턴스를 주입해야 합니다!")

        self._model = model
        self.model_name = model_name or "custom"
        self.kwargs = kwargs

    def get_model(self) -> BaseChatModel:
        """LLM 모델 인스턴스를 반환합니다."""
        return self._model

    def get_model_name(self) -> str:
        """모델 이름을 반환합니다."""
        return self.model_name

    def get_model_config(self) -> dict[str, Any]:
        """모델 설정을 반환합니다."""
        return {
            "provider": "custom",
            "model": self.model_name,
            **self.kwargs
        }


class CustomEmbeddingsProvider(BaseEmbeddings):
    """커스텀 Embeddings 구현

    사용자가 직접 모델을 주입할 수 있도록 합니다.
    """

    def __init__(
        self,
        embeddings: Optional[Embeddings] = None,
        model_name: Optional[str] = None,
        **kwargs
    ):
        """
        커스텀 Embeddings를 초기화합니다.

        Args:
            embeddings: 직접 주입할 LangChain Embeddings 인스턴스
            model_name: 모델 이름 (기본값: custom)
            **kwargs: 추가 설정
        """
        if embeddings is None:
            raise ValueError(
                "커스텀 Embeddings를 사용하려면 embeddings 인스턴스를 주입해야 합니다!"
            )

        self._embeddings = embeddings
        self.model_name = model_name or "custom"
        self.kwargs = kwargs

    def get_embeddings(self) -> Embeddings:
        """Embeddings 인스턴스를 반환합니다."""
        return self._embeddings

    def get_model_name(self) -> str:
        """모델 이름을 반환합니다."""
        return self.model_name

    def get_model_config(self) -> dict[str, Any]:
        """모델 설정을 반환합니다."""
        return {
            "provider": "custom",
            "model": self.model_name,
            **self.kwargs
        }

