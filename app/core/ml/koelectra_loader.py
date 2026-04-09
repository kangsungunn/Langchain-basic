"""
KoELECTRA 모델 로더

정책/규칙 판단을 위한 KoELECTRA 모델 로드 및 관리 (싱글톤)
"""

from pathlib import Path
from typing import Optional, Dict, Any
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.core.config import settings
from app.core.utils.logger import get_logger

logger = get_logger()


class KoELECTRALoader:
    """
    KoELECTRA 모델 로더 (싱글톤 패턴)

    사용법:
        loader = KoELECTRALoader.get_instance()
        result = loader.predict("도메인: reasoning, 액션: comprehensive_analysis, ...")
        # result: {"strategy": "policy" | "rule", "confidence": float}
    """

    _instance: Optional['KoELECTRALoader'] = None

    def __init__(
        self,
        model_path: Optional[str] = None
    ):
        """
        Args:
            model_path: KoELECTRA 모델 경로 (None이면 기본 경로 사용)
        """
        if KoELECTRALoader._instance is not None:
            raise RuntimeError("KoELECTRALoader는 싱글톤입니다. get_instance()를 사용하세요.")

        # 모델 경로 설정
        if model_path is None:
            # 1순위: 파인튜닝된 모델 경로 (환경 변수 또는 기본 경로)
            finetuned_path = Path(settings.PROJECT_ROOT) / "artifacts" / "models" / "finetuned" / "koelectra-policy-rule"
            base_path = Path(settings.PROJECT_ROOT) / "artifacts" / "models" / "base" / "koelectra-small-v3-discriminator"

            # 파인튜닝된 모델이 있으면 우선 사용, 없으면 베이스 모델 사용
            # pytorch_model.bin 또는 model.safetensors 중 하나라도 있으면 사용
            has_pytorch_model = (finetuned_path / "pytorch_model.bin").exists()
            has_safetensors = (finetuned_path / "model.safetensors").exists()

            if finetuned_path.exists() and (has_pytorch_model or has_safetensors):
                self.model_path = finetuned_path
            else:
                self.model_path = base_path
        else:
            self.model_path = Path(model_path)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # 모델 및 토크나이저 (lazy loading)
        self._model: Optional[AutoModelForSequenceClassification] = None
        self._tokenizer: Optional[AutoTokenizer] = None
        self._is_loaded = False

    @classmethod
    def get_instance(cls, model_path: Optional[str] = None) -> 'KoELECTRALoader':
        """
        싱글톤 인스턴스 반환

        Args:
            model_path: 모델 경로 (최초 호출 시에만 적용)

        Returns:
            KoELECTRALoader 인스턴스
        """
        if cls._instance is None:
            cls._instance = cls(model_path)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """
        싱글톤 인스턴스 리셋 (테스트용)

        주의: 이 메서드는 테스트 목적으로만 사용하세요.
        프로덕션 코드에서는 사용하지 마세요.
        """
        if cls._instance is not None:
            # 모델 언로드 (메모리 해제)
            if hasattr(cls._instance, '_model') and cls._instance._model is not None:
                del cls._instance._model
            if hasattr(cls._instance, '_tokenizer') and cls._instance._tokenizer is not None:
                del cls._instance._tokenizer
            cls._instance = None

    def _load_model(self):
        """모델 및 토크나이저 로드 (lazy loading)"""
        if self._is_loaded:
            return

        try:
            # 파인튜닝된 모델인지 확인
            is_finetuned = "finetuned" in str(self.model_path)
            model_type = "파인튜닝된 모델" if is_finetuned else "베이스 모델"
            logger.info(f"[LOAD] KoELECTRA {model_type} 로드 중: {self.model_path}")

            # 모델 경로 확인
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"KoELECTRA 모델을 찾을 수 없습니다: {self.model_path}\n"
                    f"💡 Hugging Face에서 모델을 다운로드하세요:\n"
                    f"   from transformers import AutoModelForSequenceClassification, AutoTokenizer\n"
                    f"   model = AutoModelForSequenceClassification.from_pretrained('monologg/koelectra-small-v3-discriminator')\n"
                    f"   tokenizer = AutoTokenizer.from_pretrained('monologg/koelectra-small-v3-discriminator')\n"
                    f"   model.save_pretrained('{self.model_path}')\n"
                    f"   tokenizer.save_pretrained('{self.model_path}')"
                )

            # 모델 및 토크나이저 로드
            self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            self._model = AutoModelForSequenceClassification.from_pretrained(str(self.model_path))
            self._model.to(self.device)
            self._model.eval()

            self._is_loaded = True
            model_type = "파인튜닝된 모델" if is_finetuned else "베이스 모델"
            logger.info(f"[OK] KoELECTRA {model_type} 로드 완료 (device: {self.device})")

        except Exception as e:
            logger.error(f"[ERROR] KoELECTRA 모델 로드 실패: {e}")
            raise

    def predict(self, text: str) -> Dict[str, Any]:
        """
        정책/규칙 판단

        Args:
            text: 판단할 텍스트 (프롬프트)

        Returns:
            {
                "strategy": "policy" | "rule",
                "confidence": float (0.0 ~ 1.0)
            }
        """
        # 모델 로드 (lazy loading)
        if not self._is_loaded:
            self._load_model()

        try:
            # 텍스트 토크나이징
            inputs = self._tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)

            # 추론
            with torch.no_grad():
                outputs = self._model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)

            # 결과 해석
            # 클래스 0: rule (규칙 기반)
            # 클래스 1: policy (정책 기반)
            rule_prob = probabilities[0][0].item()
            policy_prob = probabilities[0][1].item()

            if policy_prob > rule_prob:
                strategy = "policy"
                confidence = policy_prob
            else:
                strategy = "rule"
                confidence = rule_prob

            return {
                "strategy": strategy,
                "confidence": confidence,
                "probabilities": {
                    "rule": rule_prob,
                    "policy": policy_prob
                }
            }

        except Exception as e:
            logger.error(f"[ERROR] KoELECTRA 추론 실패: {e}")
            # 폴백: 기본값으로 규칙 기반 반환
            logger.warning("[FALLBACK] 규칙 기반으로 처리합니다.")
            return {
                "strategy": "rule",
                "confidence": 0.5,
                "probabilities": {
                    "rule": 0.5,
                    "policy": 0.5
                },
                "error": str(e)
            }

    def is_available(self) -> bool:
        """모델 사용 가능 여부 확인"""
        try:
            if not self._is_loaded:
                self._load_model()
            return self._is_loaded and self._model is not None
        except Exception:
            return False
