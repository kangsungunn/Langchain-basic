"""
민사소송법 답안 분석 모델 - 간단한 학습 스크립트

EXAONE 기반 LoRA Fine-tuning (메모리 효율적)
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
    TrainerCallback
)
from peft import LoraConfig, get_peft_model, TaskType  # pyright: ignore[reportMissingImports]
from sklearn.metrics import accuracy_score, f1_score
import numpy as np

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class LegalAnswerDataset(Dataset):
    """법률 답안 분석 데이터셋"""

    def __init__(self, samples: List[Dict[str, Any]], tokenizer, max_length: int = 512):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]

        # 입력 텍스트 구성: [문제] [모범답안] [사용자답안]
        input_text = f"""[문제] {sample['problem']}
[모범답안] {sample['reference_answer']}
[사용자답안] {sample['user_answer']}"""

        # 토큰화 (메모리 절약을 위해 max_length 줄임)
        encoding = self.tokenizer(
            input_text,
            max_length=256,  # 512 → 256으로 줄여서 메모리 절약
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        # 레이블: 쟁점 포함률을 3단계로 분류 (0: 낮음, 1: 중간, 2: 높음)
        issue_coverage = sample['labels']['issue_coverage']
        if issue_coverage < 0.4:
            label = 0  # 낮음
        elif issue_coverage < 0.7:
            label = 1  # 중간
        else:
            label = 2  # 높음

        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


def load_data(data_path: str) -> List[Dict[str, Any]]:
    """데이터 로드 (JSONL 형식)"""
    samples = []
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:  # 빈 줄 무시
                samples.append(json.loads(line))
    return samples


def compute_metrics(eval_pred):
    """평가 메트릭 계산"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)

    accuracy = accuracy_score(labels, predictions)
    f1 = f1_score(labels, predictions, average='weighted')

    return {
        'accuracy': accuracy,
        'f1': f1
    }


class ProgressCallback(TrainerCallback):
    """학습 진행률 콜백 (파일에 저장)"""

    def __init__(self, progress_file: Path, total_epochs: int):
        self.progress_file = progress_file
        self.total_epochs = total_epochs

    def on_epoch_end(self, args, state, control, **kwargs):
        """에포크 종료 시 진행률 저장"""
        current_epoch = state.epoch
        progress = current_epoch / self.total_epochs

        progress_data = {
            "current_epoch": int(current_epoch),
            "total_epochs": self.total_epochs,
            "progress": float(progress),
            "loss": float(state.log_history[-1].get("loss", 0.0)) if state.log_history else 0.0
        }

        # 파일에 진행률 저장
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)

        print(f"📊 진행률 저장: {progress*100:.1f}% (Epoch {current_epoch}/{self.total_epochs})")

    def on_log(self, args, state, control, **kwargs):
        """로그 기록 시에도 진행률 업데이트 (더 세밀한 모니터링)"""
        if state.log_history:
            current_epoch = state.epoch
            progress = current_epoch / self.total_epochs

            progress_data = {
                "current_epoch": int(current_epoch),
                "total_epochs": self.total_epochs,
                "progress": float(progress),
                "loss": float(state.log_history[-1].get("loss", 0.0))
            }

            # 파일에 진행률 저장
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)


def train_model(
    train_path: str,
    val_path: str,
    output_dir: str,
    base_model_path: Optional[str] = None,
    num_epochs: int = 2,
    batch_size: int = 1,
    learning_rate: float = 2e-5,
    lora_r: int = 8,
    lora_alpha: int = 16,
    lora_dropout: float = 0.1,
    progress_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    모델 학습 함수 (API에서 호출 가능)

    Args:
        train_path: 학습 데이터 경로 (JSONL)
        val_path: 검증 데이터 경로 (JSONL)
        output_dir: 출력 디렉토리
        base_model_path: 베이스 모델 경로 (None이면 기본 경로 사용)
        num_epochs: 학습 에포크 수
        batch_size: 배치 사이즈
        learning_rate: 학습률
        lora_r: LoRA rank
        lora_alpha: LoRA alpha
        lora_dropout: LoRA dropout

    Returns:
        Dict[str, Any]: 학습 결과 (metrics, model_path 등)
    """
    print("=" * 60)
    print("민사소송법 답안 분석 모델 - 간단한 학습")
    print("=" * 60)

    train_path = Path(train_path)
    val_path = Path(val_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📁 데이터 경로:")
    print(f"  - 학습: {train_path}")
    print(f"  - 검증: {val_path}")
    print(f"  - 출력: {output_dir}")

    # 데이터 로드
    print("\n📊 데이터 로드 중...")
    train_samples = load_data(str(train_path))
    valid_samples = load_data(str(val_path))

    print(f"  - 학습 샘플: {len(train_samples)}개")
    print(f"  - 검증 샘플: {len(valid_samples)}개")

    # 모델 및 토크나이저 로드
    print("\n🤖 모델 로드 중...")

    # 로컬 EXAONE 모델 사용
    if base_model_path is None:
        local_model_path = project_root / "artifacts" / "models" / "base" / "exaone-2.4b"
    else:
        local_model_path = Path(base_model_path)

    try:
        print(f"  📂 로컬 모델 경로: {local_model_path}")

        # GPU 메모리 캐시 정리
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print(f"  🧹 GPU 메모리 캐시 정리 완료")

        tokenizer = AutoTokenizer.from_pretrained(str(local_model_path))
        base_model = AutoModelForSequenceClassification.from_pretrained(
            str(local_model_path),
            num_labels=3,  # 낮음, 중간, 높음
            problem_type="single_label_classification",
            trust_remote_code=True,  # EXAONE custom code 허용
            dtype=torch.float16 if torch.cuda.is_available() else torch.float32  # 메모리 절약
        )

        # LoRA 설정
        print(f"  🔧 LoRA 설정 적용 중...")
        lora_config = LoraConfig(
            task_type=TaskType.SEQ_CLS,  # Sequence Classification
            r=lora_r,  # LoRA rank (낮을수록 메모리 절약, 4-16 권장)
            lora_alpha=lora_alpha,  # LoRA alpha (보통 r의 2배)
            lora_dropout=lora_dropout,  # Dropout
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],  # EXAONE attention 모듈
            bias="none",  # Bias는 학습하지 않음
        )

        # LoRA 모델 생성
        model = get_peft_model(base_model, lora_config)
        model.print_trainable_parameters()  # 학습 가능한 파라미터 수 출력

        # 모델을 학습 모드로 설정
        model.train()

        # Gradient Checkpointing 활성화 (메모리 절약)
        if hasattr(model, 'gradient_checkpointing_enable'):
            model.gradient_checkpointing_enable()
            print(f"  ✅ Gradient Checkpointing 활성화")

        print(f"  ✅ EXAONE LoRA 모델 로드 완료")
    except Exception as e:
        print(f"  ⚠️ 로컬 EXAONE 로드 실패: {e}")
        print(f"  ⚠️ 대체 모델 사용: distilbert-base-uncased")
        tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        model = AutoModelForSequenceClassification.from_pretrained(
            "distilbert-base-uncased",
            num_labels=3
        )

    # 데이터셋 생성
    print("\n📦 데이터셋 생성 중...")
    train_dataset = LegalAnswerDataset(train_samples, tokenizer)
    valid_dataset = LegalAnswerDataset(valid_samples, tokenizer)

    print(f"  - 학습 데이터셋: {len(train_dataset)}개")
    print(f"  - 검증 데이터셋: {len(valid_dataset)}개")

    # 학습 설정
    print("\n⚙️ 학습 설정:")
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=2,  # 배치 사이즈 2 효과를 위해 accumulation 사용
        learning_rate=learning_rate,
        weight_decay=0.01,
        logging_dir=str(output_dir / "logs"),
        logging_steps=1,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=2,
        report_to="none",  # 외부 로깅 비활성화
        fp16=False,  # FP16과 gradient clipping 충돌 방지
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),  # BF16 사용 (지원되는 경우)
        dataloader_pin_memory=False,  # 메모리 절약
        gradient_checkpointing=True,  # 메모리 절약
        # max_grad_norm 제거 (FP16/BF16과 충돌 가능)
    )

    print(f"  - 에포크: {training_args.num_train_epochs}")
    print(f"  - 배치 사이즈: {training_args.per_device_train_batch_size}")
    print(f"  - Gradient Accumulation: {training_args.gradient_accumulation_steps}")
    print(f"  - 학습률: {training_args.learning_rate}")
    print(f"  - GPU 사용: {torch.cuda.is_available()}")

    # Callback 설정
    callbacks = [EarlyStoppingCallback(early_stopping_patience=2)]

    # 진행률 파일이 제공되면 ProgressCallback 추가
    if progress_file:
        progress_file_path = Path(progress_file)
        progress_file_path.parent.mkdir(parents=True, exist_ok=True)
        callbacks.append(ProgressCallback(progress_file_path, num_epochs))

    # Trainer 생성
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=valid_dataset,
        compute_metrics=compute_metrics,
        callbacks=callbacks
    )

    # 학습 시작
    print("\n🚀 학습 시작!")
    print("-" * 60)

    try:
        trainer.train()

        print("\n✅ 학습 완료!")

        # 최종 평가
        print("\n📊 최종 평가:")
        eval_results = trainer.evaluate()
        for key, value in eval_results.items():
            print(f"  - {key}: {value:.4f}")

        # 모델 저장 (LoRA 가중치만 저장)
        final_output_dir = output_dir / "final"
        final_output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n💾 LoRA 모델 저장 중: {final_output_dir}")
        # LoRA 가중치만 저장 (메모리 효율적)
        model.save_pretrained(str(final_output_dir))
        tokenizer.save_pretrained(str(final_output_dir))

        print("\n✅ 모델 저장 완료!")
        print(f"\n📍 저장 위치: {final_output_dir}")

        # 결과 반환
        return {
            "success": True,
            "metrics": eval_results,
            "model_path": str(final_output_dir),
            "train_size": len(train_samples),
            "val_size": len(valid_samples)
        }

    except Exception as e:
        print(f"\n❌ 학습 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def main():
    """명령줄 실행용 메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="민사소송법 답안 분석 모델 학습")
    parser.add_argument("--train-path", type=str, required=True, help="학습 데이터 경로")
    parser.add_argument("--val-path", type=str, required=True, help="검증 데이터 경로")
    parser.add_argument("--output-dir", type=str, required=True, help="출력 디렉토리")
    parser.add_argument("--base-model-path", type=str, default=None, help="베이스 모델 경로")
    parser.add_argument("--num-epochs", type=int, default=2, help="학습 에포크 수")
    parser.add_argument("--batch-size", type=int, default=1, help="배치 사이즈")
    parser.add_argument("--learning-rate", type=float, default=2e-5, help="학습률")

    args = parser.parse_args()

    result = train_model(
        train_path=args.train_path,
        val_path=args.val_path,
        output_dir=args.output_dir,
        base_model_path=args.base_model_path,
        num_epochs=args.num_epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate
    )

    if result and result.get("success"):
        print("\n" + "=" * 60)
        print("학습 완료! 🎉")
        print("=" * 60)
        print(f"\n다음 단계:")
        print(f"  1. 모델 테스트: python test_model.py")
        print(f"  2. API 서버 시작: uvicorn app.main:app --reload")
        print(f"  3. 추론 테스트: POST /api/v1/reasoning/analyze/issues")
    else:
        print("\n❌ 학습 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
