"""
모델 팩토리

환경 변수나 설정에 따라 적절한 모델을 생성하는 팩토리 클래스입니다.
"""
import os
from typing import Optional

from app.models.base import BaseLLM, BaseEmbeddings
from app.models.providers.openai_provider import OpenAILLM, OpenAIEmbeddingsProvider
from app.models.providers.custom_provider import CustomLLM, CustomEmbeddingsProvider
from app.models.providers.local_llama_provider import LocalLlamaLLM


class ModelFactory:
    """모델을 생성하는 팩토리 클래스"""

    @staticmethod
    def create_llm(
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> BaseLLM:
        """
        LLM 모델을 생성합니다.

        Args:
            provider: 모델 제공자 (openai, custom 등). None이면 환경 변수에서 읽음
            model_name: 모델 이름. None이면 기본값 사용
            **kwargs: 모델별 추가 설정

        Returns:
            BaseLLM 인스턴스
        """
        provider = provider or os.getenv("LLM_PROVIDER", "openai")

        if provider.lower() == "openai":
            return OpenAILLM(model_name=model_name, **kwargs)
        elif provider.lower() == "custom":
            return CustomLLM(model_name=model_name, **kwargs)
        elif provider.lower() == "local_llama":
            return LocalLlamaLLM(model_name=model_name, **kwargs)
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {provider}")

    @staticmethod
    def create_embeddings(
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> BaseEmbeddings:
        """
        Embeddings 모델을 생성합니다.

        Args:
            provider: 모델 제공자 (openai, custom 등). None이면 환경 변수에서 읽음
            model_name: 모델 이름. None이면 기본값 사용
            **kwargs: 모델별 추가 설정

        Returns:
            BaseEmbeddings 인스턴스
        """
        provider = provider or os.getenv("EMBEDDINGS_PROVIDER", "openai")

        if provider.lower() == "openai":
            return OpenAIEmbeddingsProvider(model_name=model_name, **kwargs)
        elif provider.lower() == "custom":
            return CustomEmbeddingsProvider(model_name=model_name, **kwargs)
        else:
            raise ValueError(f"지원하지 않는 Embeddings 제공자: {provider}")

