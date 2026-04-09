"""
ML 모델 로더

EXAONE 모델 로드 및 관리 (싱글톤)
"""

from pathlib import Path
from typing import Optional
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from peft import PeftModel  # LoRA 지원


class ModelLoader:
    """
    EXAONE 모델 로더 (싱글톤 패턴)

    사용법:
        loader = ModelLoader.get_instance()
        model = loader.get_model()
        tokenizer = loader.get_tokenizer()
    """

    _instance: Optional['ModelLoader'] = None

    def __init__(
        self,
        model_path: str = "artifacts/models/finetuned/legal/final_simple",
        base_model_path: Optional[str] = None
    ):
        """
        Args:
            model_path: 모델 경로 (LoRA 어댑터 또는 전체 모델)
            base_model_path: Base 모델 경로 (LoRA 사용 시 필요, None이면 EXAONE 기본 경로)
        """
        if ModelLoader._instance is not None:
            raise RuntimeError("ModelLoader는 싱글톤입니다. get_instance()를 사용하세요.")

        self.model_path = Path(model_path)
        self.base_model_path = Path(base_model_path) if base_model_path else Path("artifacts/models/base/exaone-2.4b")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # 모델 및 토크나이저 (lazy loading)
        self._model: Optional[AutoModelForSequenceClassification] = None
        self._tokenizer: Optional[AutoTokenizer] = None

        # LoRA 여부 감지
        self._is_lora = (self.model_path / "adapter_config.json").exists()

        # 로드 상태
        self._is_loaded = False

    @classmethod
    def get_instance(
        cls,
        model_path: str = "artifacts/models/finetuned/legal/final_simple",
        base_model_path: Optional[str] = None
    ) -> 'ModelLoader':
        """
        싱글톤 인스턴스 반환

        Args:
            model_path: 모델 경로 (첫 호출 시에만 사용)
            base_model_path: Base 모델 경로 (첫 호출 시에만 사용)

        Returns:
            ModelLoader 인스턴스
        """
        if cls._instance is None:
            cls._instance = cls(model_path, base_model_path)
        return cls._instance

    def load(self) -> bool:
        """
        모델 및 토크나이저 로드 (LoRA 지원)

        Returns:
            bool: 로드 성공 여부
        """
        if self._is_loaded:
            print("✅ 모델이 이미 로드되어 있습니다.")
            return True

        try:
            if not self.model_path.exists():
                print(f"⚠️  모델 경로가 존재하지 않습니다: {self.model_path}")
                print(f"💡 다음 경로에 모델을 학습하거나 다운로드하세요:")
                print(f"   - training/examination/civil_law/train_simple.py 실행")
                print(f"   - 또는 사전 학습된 모델 복사")
                return False

            print(f"🔄 모델 로드 중: {self.model_path}")

            # 토크나이저 로드
            self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            print(f"  ✅ 토크나이저 로드 완료")

            # LoRA 모델인 경우
            if self._is_lora:
                print(f"  🔄 LoRA 모델 감지, Base 모델 로드 중: {self.base_model_path}")

                if not self.base_model_path.exists():
                    print(f"  ⚠️  Base 모델이 없습니다: {self.base_model_path}")
                    print(f"  ⚠️  LoRA 어댑터만 있어 추론 불가. Base 모델을 다운로드하세요.")
                    return False

                # Base 모델 로드
                base_model = AutoModelForSequenceClassification.from_pretrained(
                    str(self.base_model_path),
                    num_labels=3,
                    trust_remote_code=True
                )

                # LoRA 어댑터 로드
                self._model = PeftModel.from_pretrained(base_model, str(self.model_path))
                print(f"  ✅ LoRA 어댑터 로드 완료")

            else:
                # 전체 모델 로드
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    str(self.model_path)
                )
                print(f"  ✅ 전체 모델 로드 완료")

            self._model.to(self.device)
            self._model.eval()  # 추론 모드
            print(f"  ✅ 모델 준비 완료 (device: {self.device})")

            self._is_loaded = True
            return True

        except Exception as e:
            print(f"❌ 모델 로드 실패: {e}")
            import traceback
            traceback.print_exc()
            self._model = None
            self._tokenizer = None
            return False

    def get_model(self) -> Optional[AutoModelForSequenceClassification]:
        """
        모델 반환 (자동 로드)

        Returns:
            모델 또는 None
        """
        if not self._is_loaded:
            self.load()
        return self._model

    def get_tokenizer(self) -> Optional[AutoTokenizer]:
        """
        토크나이저 반환 (자동 로드)

        Returns:
            토크나이저 또는 None
        """
        if not self._is_loaded:
            self.load()
        return self._tokenizer

    def is_loaded(self) -> bool:
        """
        로드 상태 확인

        Returns:
            bool: 로드 여부
        """
        return self._is_loaded

    def get_device(self) -> str:
        """
        디바이스 반환

        Returns:
            str: "cuda" 또는 "cpu"
        """
        return self.device

    def unload(self):
        """
        모델 언로드 (메모리 해제)
        """
        if self._model is not None:
            del self._model
            self._model = None

        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        self._is_loaded = False

        # CUDA 메모리 정리
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print("✅ 모델 언로드 완료")

    def reload(self, model_path: Optional[str] = None, base_model_path: Optional[str] = None) -> bool:
        """
        모델 리로드 (새 모델 경로로)

        Args:
            model_path: 새 모델 경로 (None이면 현재 경로 유지)
            base_model_path: 새 Base 모델 경로 (None이면 현재 경로 유지)

        Returns:
            bool: 리로드 성공 여부
        """
        # 기존 모델 언로드
        self.unload()

        # 새 경로 설정
        if model_path:
            self.model_path = Path(model_path)
        if base_model_path:
            self.base_model_path = Path(base_model_path)

        # LoRA 여부 재감지
        self._is_lora = (self.model_path / "adapter_config.json").exists()

        # 새 모델 로드
        return self.load()


# 전역 함수 (편의성)
def get_model_loader() -> ModelLoader:
    """
    전역 ModelLoader 인스턴스 반환

    Returns:
        ModelLoader 인스턴스
    """
    return ModelLoader.get_instance()
