"""
로컬 Llama 모델 제공자

로컬에 저장된 Llama 모델을 로드하여 사용합니다.
"""
import os
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel

from app.models.base import BaseLLM


class LocalLlamaLLM(BaseLLM):
    """로컬 Llama 모델 구현

    HuggingFace Transformers를 사용하여 로컬 모델을 로드합니다.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: Optional[str] = None,
        device: str = "cpu",
        **kwargs
    ):
        """
        로컬 Llama 모델을 초기화합니다.

        Args:
            model_path: 모델 경로 (기본값: app/models/midm)
            model_name: 모델 이름 (기본값: local-llama)
            device: 디바이스 (cpu, cuda 등)
            **kwargs: 추가 설정

        사용 예시:
            # 방법 1: HuggingFace Pipeline
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from langchain_huggingface import HuggingFacePipeline

            model = AutoModelForCausalLM.from_pretrained(model_path)
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            pipeline = HuggingFacePipeline(model=model, tokenizer=tokenizer)

            # 방법 2: llama.cpp
            from langchain_community.llms import LlamaCpp

            llm = LlamaCpp(model_path="path/to/model.gguf")
        """
        self.model_path = model_path or os.getenv(
            "LOCAL_MODEL_PATH", "app/models/midm"
        )
        self.model_name = model_name or "local-llama"
        self.device = device
        self.kwargs = kwargs

        self._model: Optional[BaseChatModel] = None

    def get_model(self) -> BaseChatModel:
        """
        LLM 모델 인스턴스를 반환합니다.

        Midm-2.0-Mini-Instruct 모델을 로드합니다.

        Returns:
            LLM 모델 인스턴스
        """
        if self._model is None:
            try:
                from transformers import (
                    AutoModelForCausalLM,
                    AutoTokenizer,
                    pipeline as hf_pipeline
                )
                from langchain_huggingface import HuggingFacePipeline

                print(f"🔄 로컬 모델 로드 중: {self.model_path}")

                # Midm 모델 로드
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    torch_dtype="auto",
                    device_map="auto",
                    trust_remote_code=True  # Mi:dm 필수
                )

                tokenizer = AutoTokenizer.from_pretrained(self.model_path)

                print(f"✅ 모델 로드 완료: {self.model_name}")
                print(f"   디바이스: {self.device}")

                # Pipeline 생성
                pipe = hf_pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    max_new_tokens=self.kwargs.get("max_new_tokens", 512),
                    temperature=self.kwargs.get("temperature", 0.7),
                    do_sample=True,
                    top_p=self.kwargs.get("top_p", 0.9),
                )

                # LangChain 래퍼로 변환
                self._model = HuggingFacePipeline(pipeline=pipe)

            except ImportError as e:
                raise ImportError(
                    "로컬 모델을 사용하려면 필요한 패키지를 설치하세요:\n"
                    "pip install transformers torch langchain-huggingface accelerate"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"모델 로드 실패: {e}\n"
                    f"모델 경로: {self.model_path}\n"
                    "모델 파일이 올바른 위치에 있는지 확인하세요."
                ) from e

        return self._model

    def get_model_name(self) -> str:
        """모델 이름을 반환합니다."""
        return self.model_name

    def get_model_config(self) -> dict[str, Any]:
        """모델 설정을 반환합니다."""
        return {
            "provider": "local_llama",
            "model": self.model_name,
            "model_path": self.model_path,
            "device": self.device,
            **self.kwargs
        }

