"""
임베딩 생성 모듈

BaseEmbedder 인터페이스 및 구현체들.
- artifacts/embedding_models: Sentence-BERT 형식(예: jhgan/ko-sroberta-multitask) → sentence_transformers 로드
- 그 외: HuggingFace AutoModel(KoELECTRA 등) 로드
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Any
from pathlib import Path
import os
import torch
from transformers import AutoModel, AutoTokenizer

from app.core.config import settings
from app.core.utils.logger import get_logger

logger = get_logger()


def _is_sentence_transformer_path(model_path: Path) -> bool:
    """경로가 Sentence-BERT(sentence_transformers) 형식인지 확인 (modules.json 존재)"""
    return (model_path / "modules.json").exists()


class BaseEmbedder(ABC):
    """
    임베딩 생성기 기본 인터페이스

    다양한 임베딩 모델을 교체 가능하도록 추상화.
    """

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        텍스트를 임베딩 벡터로 변환

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (리스트)
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        여러 텍스트를 배치로 임베딩

        Args:
            texts: 임베딩할 텍스트 리스트

        Returns:
            임베딩 벡터 리스트
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        임베딩 차원 반환

        Returns:
            임베딩 벡터 차원 (예: 768)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        모델 사용 가능 여부 확인

        Returns:
            사용 가능 여부
        """
        pass


class KoELECTRAEmbedder(BaseEmbedder):
    """
    통합 임베딩 생성기

    - artifacts/embedding_models (Sentence-BERT 형식, modules.json 있음): sentence_transformers 로드
    - 그 외: HuggingFace AutoModel(KoELECTRA 등) 로드
    출력은 항상 768차원 벡터(DB schema와 호환).
    """

    _instance: Optional['KoELECTRAEmbedder'] = None

    def __init__(self, model_path: Optional[str] = None):
        """
        Args:
            model_path: 임베딩 모델 경로 (None이면 설정/환경 변수 또는 기본 경로 사용)
        """
        if KoELECTRAEmbedder._instance is not None:
            raise RuntimeError("KoELECTRAEmbedder는 싱글톤입니다. get_instance()를 사용하세요.")

        # 모델 경로: 인자 > EMBEDDING_MODEL_PATH 설정 > KOELECTRA_EMBEDDING_MODEL_PATH
        if model_path is not None:
            self.model_path = Path(model_path)
        else:
            self.model_path = Path(settings.EMBEDDING_MODEL_PATH)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Lazy loading: Sentence-BERT 또는 AutoModel
        self._sentence_model: Any = None  # sentence_transformers.SentenceTransformer
        self._model: Optional[AutoModel] = None
        self._tokenizer: Optional[AutoTokenizer] = None
        self._is_loaded = False
        self._dimension = 768

    @classmethod
    def get_instance(cls, model_path: Optional[str] = None) -> 'KoELECTRAEmbedder':
        """
        싱글톤 인스턴스 반환

        Args:
            model_path: 모델 경로 (최초 호출 시에만 적용)

        Returns:
            KoELECTRAEmbedder 인스턴스
        """
        if cls._instance is None:
            cls._instance = cls(model_path)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """싱글톤 인스턴스 리셋 (테스트용)"""
        if cls._instance is not None:
            if hasattr(cls._instance, '_sentence_model') and cls._instance._sentence_model is not None:
                del cls._instance._sentence_model
            if hasattr(cls._instance, '_model') and cls._instance._model is not None:
                del cls._instance._model
            if hasattr(cls._instance, '_tokenizer') and cls._instance._tokenizer is not None:
                del cls._instance._tokenizer
            cls._instance = None

    def _load_model(self):
        """모델 로드 (lazy): Sentence-BERT 형식이면 sentence_transformers, 아니면 AutoModel"""
        if self._is_loaded:
            return

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"임베딩 모델 경로를 찾을 수 없습니다: {self.model_path}\n"
                f"💡 artifacts/embedding_models 에 모델을 두거나 .env에 EMBEDDING_MODEL_PATH 를 설정하세요.\n"
                f"   예: jhgan/ko-sroberta-multitask 를 저장한 경로 (modules.json 포함)"
            )

        try:
            if _is_sentence_transformer_path(self.model_path):
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError:
                    raise ImportError(
                        "Sentence-BERT 형식 모델을 쓰려면 sentence_transformers 가 필요합니다: pip install sentence-transformers"
                    )
                logger.info(f"[LOAD] 임베딩 모델 로드 중 (Sentence-BERT): {self.model_path}")
                self._sentence_model = SentenceTransformer(str(self.model_path), device=self.device)
                self._dimension = self._sentence_model.get_sentence_embedding_dimension()
                self._is_loaded = True
                logger.info(f"[OK] 임베딩 모델 로드 완료 (device: {self.device}, dimension: {self._dimension})")
                return
            else:
                logger.info(f"[LOAD] 임베딩 모델 로드 중 (AutoModel): {self.model_path}")
                self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
                self._model = AutoModel.from_pretrained(str(self.model_path))
                assert self._model is not None
                self._model.to(self.device)
                self._model.eval()
                self._is_loaded = True
                logger.info(f"[OK] 임베딩 모델 로드 완료 (device: {self.device}, dimension: {self._dimension})")
        except Exception as e:
            logger.error(f"[ERROR] 임베딩 모델 로드 실패: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """
        텍스트를 임베딩 벡터로 변환 (차원은 모델에 따름, DB는 768 가정)

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (리스트)
        """
        if not self._is_loaded:
            self._load_model()

        try:
            if self._sentence_model is not None:
                emb = self._sentence_model.encode(text, convert_to_numpy=True)
                return emb.tolist()
            # AutoModel
            assert self._tokenizer is not None and self._model is not None
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            with torch.no_grad():
                outputs = self._model(**inputs)
                embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy().tolist()[0]
            return embedding
        except Exception as e:
            logger.error(f"[ERROR] 임베딩 생성 실패: {e}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        여러 텍스트를 배치로 임베딩

        Args:
            texts: 임베딩할 텍스트 리스트

        Returns:
            임베딩 벡터 리스트
        """
        if not self._is_loaded:
            self._load_model()

        try:
            if self._sentence_model is not None:
                emb = self._sentence_model.encode(texts, convert_to_numpy=True)
                return emb.tolist()
            # AutoModel
            assert self._tokenizer is not None and self._model is not None
            inputs = self._tokenizer(
                texts,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            with torch.no_grad():
                outputs = self._model(**inputs)
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy().tolist()
            return embeddings
        except Exception as e:
            logger.error(f"[ERROR] 배치 임베딩 생성 실패: {e}")
            raise

    def get_dimension(self) -> int:
        """임베딩 차원 반환 (로드 후 결정, 일반적으로 768)"""
        if not self._is_loaded:
            self._load_model()
        return self._dimension

    def is_available(self) -> bool:
        """모델 사용 가능 여부 확인"""
        try:
            if not self._is_loaded:
                self._load_model()
            return self._is_loaded and (self._sentence_model is not None or self._model is not None)
        except Exception:
            return False


# 전역 인스턴스 접근 함수
def get_koelectra_embedder(model_path: Optional[str] = None) -> KoELECTRAEmbedder:
    """
    KoELECTRA 임베딩 생성기 인스턴스 반환

    Args:
        model_path: 모델 경로 (최초 호출 시에만 적용)

    Returns:
        KoELECTRAEmbedder 인스턴스
    """
    return KoELECTRAEmbedder.get_instance(model_path)
