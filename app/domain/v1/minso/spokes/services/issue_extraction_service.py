"""
논점 추출 서비스 — 학습된 ExaOne (LoRA)로 문제 지문 → 논점 목록

- 입력: problem_content (str)
- 출력: List[str] (큰 논점 제목 목록)
- 베이스: artifacts/models/base/exaone-2.4b + LoRA: artifacts/models/finetuned/exaone-issue-extraction
"""

from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

_load_lock = threading.Lock()

# 학습 시 사용한 instruction (train_exaone_lora.PROMPT_TEMPLATE와 일치)
DEFAULT_INSTRUCTION = (
    "다음 민사소송법 사례 문제에서, 답안에 반드시 다뤄야 할 논점(쟁점)을 나열하세요. "
    "논점 제목만 한 줄에 하나씩 출력하세요."
)
PROMPT_PREFIX = "[질문] "
PROMPT_MID = "\n\n[답변] "


class IssueExtractionService:
    """
    문제 지문만으로 논점(큰 쟁점) 목록을 추출합니다.
    학습된 ExaOne LoRA를 사용하며, 로드는 첫 호출 시 지연 로딩합니다.
    """

    _instance: Optional["IssueExtractionService"] = None
    _model = None
    _tokenizer = None
    _adapter_path: Optional[Path] = None
    _base_path: Optional[Path] = None

    def __init__(
        self,
        adapter_path: Optional[str | Path] = None,
        base_model_path: Optional[str | Path] = None,
    ):
        if adapter_path is None:
            try:
                from app.core.config import settings
                root = Path(settings.PROJECT_ROOT)
                adapter_path = getattr(
                    settings, "EXAONE_ISSUE_EXTRACTION_ADAPTER_PATH", None
                ) or str(root / "artifacts" / "models" / "finetuned" / "exaone-issue-extraction")
            except Exception:
                root = Path(__file__).resolve().parents[6]  # project root
                adapter_path = str(root / "artifacts" / "models" / "finetuned" / "exaone-issue-extraction")
        if base_model_path is None:
            try:
                from app.core.config import settings
                root = Path(settings.PROJECT_ROOT)
                base_model_path = getattr(settings, "EXAONE_BASE_MODEL_PATH", None) or str(
                    root / "artifacts" / "models" / "base" / "exaone-2.4b"
                )
            except Exception:
                root = Path(__file__).resolve().parents[6]
                base_model_path = str(root / "artifacts" / "models" / "base" / "exaone-2.4b")

        self._adapter_path = Path(adapter_path)
        self._base_path = Path(base_model_path)

    @classmethod
    def get_instance(
        cls,
        adapter_path: Optional[str | Path] = None,
        base_model_path: Optional[str | Path] = None,
    ) -> "IssueExtractionService":
        if cls._instance is None:
            cls._instance = cls(adapter_path=adapter_path, base_model_path=base_model_path)
        return cls._instance

    def _ensure_loaded(self) -> bool:
        if self._model is not None and self._tokenizer is not None:
            return True
        with _load_lock:
            if self._model is not None and self._tokenizer is not None:
                return True
            if not self._base_path.exists():
                logger.warning("ExaOne 베이스 모델 경로 없음: %s", self._base_path)
                return False
            if not self._adapter_path.exists() or not (self._adapter_path / "adapter_config.json").exists():
                logger.warning("논점 추출 LoRA 어댑터 경로 없음: %s", self._adapter_path)
                return False
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer
                from peft import PeftModel

                self._tokenizer = AutoTokenizer.from_pretrained(
                    str(self._adapter_path),
                    trust_remote_code=True,
                    local_files_only=True,
                )
                if self._tokenizer.pad_token is None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token

                base = AutoModelForCausalLM.from_pretrained(
                    str(self._base_path),
                    trust_remote_code=True,
                    local_files_only=True,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="cuda:0" if torch.cuda.is_available() else None,
                )
                self._model = PeftModel.from_pretrained(base, str(self._adapter_path))
                self._model.eval()
                logger.info("논점 추출 모델 로드 완료: %s", self._adapter_path)
                return True
            except Exception as e:
                logger.exception("논점 추출 모델 로드 실패: %s", e)
                return False

    def extract_issues(
        self,
        problem_content: str,
        instruction: Optional[str] = None,
        max_new_tokens: int = 256,
        temperature: float = 0.3,
    ) -> List[str]:
        """
        문제 지문에서 논점(큰 쟁점) 목록을 추출합니다.

        Args:
            problem_content: 문제/설문 전체 텍스트
            instruction: 지시문 (None이면 기본 문구 사용)
            max_new_tokens: 최대 생성 토큰
            temperature: 생성 온도 (낮을수록 일관적)

        Returns:
            논점 제목 문자열 목록. 모델 로드 실패 시 빈 리스트.
        """
        if not problem_content or not problem_content.strip():
            return []

        if not self._ensure_loaded():
            return []

        instruction = instruction or DEFAULT_INSTRUCTION
        prompt = PROMPT_PREFIX + instruction + "\n\n" + (problem_content.strip()) + PROMPT_MID

        try:
            import torch

            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024,
            )
            if hasattr(self._model, "device"):
                device = next(self._model.parameters()).device
            else:
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            inputs = {k: v.to(device) for k, v in inputs.items()}

            logger.info("논점 추출: 추론 중...")
            with torch.no_grad():
                out = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=temperature > 0,
                    temperature=temperature if temperature > 0 else None,
                    pad_token_id=self._tokenizer.pad_token_id or self._tokenizer.eos_token_id,
                    eos_token_id=self._tokenizer.eos_token_id,
                )
            logger.info("논점 추출: 추론 완료")

            # 생성된 부분만 디코딩 (프롬프트 제외)
            gen_start = inputs["input_ids"].shape[1]
            generated = self._tokenizer.decode(out[0][gen_start:], skip_special_tokens=True)

            # "[답변]" 이후만 취하고, 한 줄씩 논점으로 파싱
            if "[답변]" in generated:
                generated = generated.split("[답변]")[-1].strip()
            lines = [line.strip() for line in generated.splitlines() if line.strip()]
            # 빈 줄·숫자만 있는 줄 제거, 앞의 "1.", "2." 등 제거
            issues = []
            for line in lines:
                line = re.sub(r"^\s*\d+[.,)\s]*", "", line).strip()
                if line and len(line) > 1:
                    issues.append(line)
            return issues[:30]  # 상한
        except Exception as e:
            logger.exception("논점 추출 추론 실패: %s", e)
            return []


def extract_issues_from_problem(
    problem_content: str,
    adapter_path: Optional[str | Path] = None,
    base_model_path: Optional[str | Path] = None,
) -> List[str]:
    """
    문제 지문만 넣어 논점 목록을 반환하는 편의 함수.

    서비스 싱글톤을 사용합니다.
    """
    svc = IssueExtractionService.get_instance(
        adapter_path=adapter_path,
        base_model_path=base_model_path,
    )
    return svc.extract_issues(problem_content)
