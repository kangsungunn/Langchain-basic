"""
ExaOne LoRA SFT — 논점 추출 (문제 지문 → 논점 목록)

- 입력: SFT 형식 JSONL (instruction, input, output) — train.jsonl, val.jsonl
- 베이스: artifacts/models/base/exaone-2.4b (Causal LM)
- 학습: LoRA 적용 후 "[질문] ... [답변] ..." 형식으로 답변 부분만 loss 계산
- 출력: LoRA 어댑터 저장 (artifacts/models/finetuned/exaone-issue-extraction)

실행은 프로젝트 루트에서:
  python -m training.shared.train_exaone_lora --data-dir training/data/issue_extraction --output-dir artifacts/models/finetuned/exaone-issue-extraction
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
)
from peft import LoraConfig, get_peft_model, TaskType  # type: ignore

# 프로젝트 루트
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from app.core.config import settings
except ImportError:
    settings = None

DEFAULT_BASE_MODEL = "artifacts/models/base/exaone-2.4b"
PROMPT_TEMPLATE = "[질문] {instruction}\n\n{input_text}\n\n[답변] "


def _get_base_model_path() -> Path:
    if settings is not None and getattr(settings, "EXAONE_BASE_MODEL_PATH", None):
        return Path(settings.EXAONE_BASE_MODEL_PATH)
    return _project_root / "artifacts" / "models" / "base" / "exaone-2.4b"


def load_sft_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class IssueExtractionDataset(torch.utils.data.Dataset):
    """SFT (instruction, input, output) → input_ids, attention_mask, labels (loss only on output)."""

    def __init__(
        self,
        samples: List[Dict[str, Any]],
        tokenizer: AutoTokenizer,
        max_prompt_length: int = 1024,
        max_response_length: int = 256,
    ):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_prompt_length = max_prompt_length
        self.max_response_length = max_response_length
        self.pad_token_id = tokenizer.pad_token_id or tokenizer.eos_token_id

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        s = self.samples[idx]
        instruction = s.get("instruction", "")
        input_text = s.get("input", "")
        output_text = s.get("output", "")

        prompt = PROMPT_TEMPLATE.format(instruction=instruction, input_text=input_text)
        # 답변만 학습: prompt 토큰은 labels에서 -100
        enc_prompt = self.tokenizer(
            prompt,
            truncation=True,
            max_length=self.max_prompt_length,
            add_special_tokens=True,
            return_tensors=None,
        )
        enc_response = self.tokenizer(
            output_text,
            truncation=True,
            max_length=self.max_response_length,
            add_special_tokens=False,
            return_tensors=None,
        )
        # EOS를 답 끝에 추가 (선택)
        if self.tokenizer.eos_token_id is not None and (
            not enc_response["input_ids"] or enc_response["input_ids"][-1] != self.tokenizer.eos_token_id
        ):
            enc_response["input_ids"].append(self.tokenizer.eos_token_id)
            enc_response["attention_mask"].append(1)

        input_ids = enc_prompt["input_ids"] + enc_response["input_ids"]
        attention_mask = enc_prompt["attention_mask"] + enc_response["attention_mask"]
        labels = [-100] * len(enc_prompt["input_ids"]) + enc_response["input_ids"]

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


def get_data_collator(tokenizer: AutoTokenizer, pad_to_multiple_of: Optional[int] = 8):
    """패딩 시 labels의 패딩 위치는 -100으로."""

    pad_id = tokenizer.pad_token_id or tokenizer.eos_token_id

    def collate_fn(examples: List[Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
        max_len = max(e["input_ids"].size(0) for e in examples)
        if pad_to_multiple_of:
            max_len = ((max_len + pad_to_multiple_of - 1) // pad_to_multiple_of) * pad_to_multiple_of
        input_ids = []
        attention_mask = []
        labels = []
        for e in examples:
            pad_len = max_len - e["input_ids"].size(0)
            input_ids.append(
                torch.cat([e["input_ids"], torch.full((pad_len,), pad_id, dtype=torch.long)])
            )
            attention_mask.append(
                torch.cat([e["attention_mask"], torch.zeros(pad_len, dtype=torch.long)])
            )
            labels.append(
                torch.cat([e["labels"], torch.full((pad_len,), -100, dtype=torch.long)])
            )
        return {
            "input_ids": torch.stack(input_ids),
            "attention_mask": torch.stack(attention_mask),
            "labels": torch.stack(labels),
        }

    return collate_fn


def train(
    data_dir: str | Path,
    output_dir: str | Path,
    base_model_path: Optional[str | Path] = None,
    num_epochs: int = 3,
    batch_size: int = 2,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-5,
    max_prompt_length: int = 1024,
    max_response_length: int = 256,
    lora_r: int = 8,
    lora_alpha: int = 16,
    lora_dropout: float = 0.1,
) -> Dict[str, Any]:
    """
    ExaOne 논점 추출 LoRA SFT 학습.

    Args:
        data_dir: train.jsonl, val.jsonl 이 있는 디렉터리
        output_dir: LoRA 어댑터 및 로그 저장 경로
        base_model_path: ExaOne 베이스 모델 경로 (None이면 설정/기본값)
        num_epochs: 에폭 수
        batch_size: per-device 배치 크기
        gradient_accumulation_steps: 그래디언트 누적
        learning_rate: 학습률
        max_prompt_length: 프롬프트 최대 토큰
        max_response_length: 답변 최대 토큰
        lora_r, lora_alpha, lora_dropout: LoRA 설정

    Returns:
        학습 결과 dict (success, model_path, metrics 등)
    """
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_path = Path(base_model_path) if base_model_path else _get_base_model_path()
    if not base_path.exists():
        raise FileNotFoundError(f"베이스 모델 경로가 없습니다: {base_path}")

    train_path = data_dir / "train.jsonl"
    val_path = data_dir / "val.jsonl"
    if not train_path.exists():
        raise FileNotFoundError(f"학습 데이터 없음: {train_path}")
    if not val_path.exists():
        raise FileNotFoundError(f"검증 데이터 없음: {val_path}")

    print("[1/5] 토크나이저·모델 로드")
    tokenizer = AutoTokenizer.from_pretrained(
        str(base_path),
        trust_remote_code=True,
        local_files_only=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        str(base_path),
        trust_remote_code=True,
        local_files_only=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )

    print("[2/5] LoRA 설정")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    # Gradient checkpointing 사용 시 LoRA로 그래디언트가 흐르도록 필요 (없으면 backward 시 grad_fn 오류)
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()

    print("[3/5] 데이터 로드")
    train_samples = load_sft_jsonl(train_path)
    val_samples = load_sft_jsonl(val_path)
    train_dataset = IssueExtractionDataset(
        train_samples, tokenizer, max_prompt_length, max_response_length
    )
    val_dataset = IssueExtractionDataset(
        val_samples, tokenizer, max_prompt_length, max_response_length
    )
    data_collator = get_data_collator(tokenizer)

    print("[4/5] 학습 인자 설정")
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_ratio=0.05,
        logging_dir=str(output_dir / "logs"),
        logging_steps=5,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        bf16=False,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
    )

    print("[5/5] 학습 실행")
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    eval_result = trainer.evaluate()
    print("검증 loss:", eval_result.get("eval_loss", "N/A"))

    return {
        "success": True,
        "model_path": str(output_dir),
        "eval_loss": eval_result.get("eval_loss"),
        "train_samples": len(train_samples),
        "val_samples": len(val_samples),
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="ExaOne LoRA SFT — 논점 추출")
    ap.add_argument(
        "--data-dir",
        type=str,
        default="training/data/issue_extraction",
        help="train.jsonl, val.jsonl 디렉터리",
    )
    ap.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/models/finetuned/exaone-issue-extraction",
        help="LoRA 저장 경로",
    )
    ap.add_argument("--base-model-path", type=str, default=None, help="ExaOne 베이스 모델 경로")
    ap.add_argument("--num-epochs", type=int, default=3, help="에폭 수")
    ap.add_argument("--batch-size", type=int, default=2, help="per-device 배치 크기")
    ap.add_argument("--gradient-accumulation-steps", type=int, default=4, help="그래디언트 누적")
    ap.add_argument("--learning-rate", type=float, default=2e-5, help="학습률")
    ap.add_argument("--max-prompt-length", type=int, default=1024, help="프롬프트 최대 토큰")
    ap.add_argument("--max-response-length", type=int, default=256, help="답변 최대 토큰")
    ap.add_argument("--lora-r", type=int, default=8, help="LoRA r")
    ap.add_argument("--lora-alpha", type=int, default=16, help="LoRA alpha")
    ap.add_argument("--lora-dropout", type=float, default=0.1, help="LoRA dropout")

    args = ap.parse_args()

    result = train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        base_model_path=args.base_model_path or None,
        num_epochs=args.num_epochs,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        max_prompt_length=args.max_prompt_length,
        max_response_length=args.max_response_length,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
    )

    if result.get("success"):
        print("\n학습 완료. 저장 경로:", result["model_path"])
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
