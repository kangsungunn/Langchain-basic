"""
KoELECTRA 파인튜닝 스크립트 (정책/규칙 판별)

실제 데이터 기준으로 작성된 코드입니다.
실제 JSONL 파일을 읽어서 학습합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import argparse
from typing import Dict, Any, List, Optional
import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding
)
from datasets import Dataset
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from app.core.config import settings
from app.core.utils.logger import get_logger

logger = get_logger()


def load_training_data(
    data_dir: str,
    split: str = "train"
) -> List[Dict[str, Any]]:
    """
    학습 데이터 로드

    실제 데이터 기준으로 작성된 코드입니다.
    실제 JSONL 파일에서 학습 데이터를 로드합니다.

    Args:
        data_dir: 데이터 디렉토리 경로 (실제 데이터 경로)
        split: 데이터 분할 ("train", "val", "test")

    Returns:
        list: 학습 데이터 리스트

    Raises:
        FileNotFoundError: 데이터 파일이 없을 경우
    """
    data_dir = Path(data_dir)
    file_path = data_dir / f"{split}.jsonl"

    if not file_path.exists():
        raise FileNotFoundError(
            f"데이터 파일을 찾을 수 없습니다: {file_path}\n"
            f"💡 실제 API 요청 로그를 수집하여 JSONL 형식으로 변환하세요."
        )

    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))

    logger.info(f"[OK] {split} 데이터 로드 완료: {len(data)}개")
    return data


def prepare_dataset(
    data: List[Dict[str, Any]],
    tokenizer: AutoTokenizer,
    max_length: int = 512
) -> Dataset:
    """
    데이터셋 준비

    실제 데이터 기준으로 작성된 코드입니다.
    실제 학습 데이터를 토크나이징하고 라벨을 준비합니다.

    Args:
        data: 실제 학습 데이터 리스트 (JSONL에서 로드된 데이터)
        tokenizer: 토크나이저
        max_length: 최대 길이

    Returns:
        Dataset: 준비된 데이터셋
    """
    texts = [item["text"] for item in data]
    labels = [item["label"] for item in data]

    # 토크나이징
    encodings = tokenizer(
        texts,
        truncation=True,
        padding=False,
        max_length=max_length,
        return_tensors=None
    )

    # 데이터셋 생성
    dataset = Dataset.from_dict({
        "input_ids": encodings["input_ids"],
        "attention_mask": encodings["attention_mask"],
        "labels": labels
    })

    return dataset


def compute_metrics(eval_pred):
    """
    평가 메트릭 계산

    실제 데이터 기준으로 작성된 코드입니다.

    Args:
        eval_pred: 평가 예측 결과

    Returns:
        dict: 평가 메트릭
    """
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)

    accuracy = accuracy_score(labels, predictions)
    f1 = f1_score(labels, predictions, average='weighted')
    precision = precision_score(labels, predictions, average='weighted')
    recall = recall_score(labels, predictions, average='weighted')

    return {
        "accuracy": accuracy,
        "f1": f1,
        "precision": precision,
        "recall": recall
    }


def train_koelectra(
    data_dir: str,
    output_dir: str,
    model_name: str = "monologg/koelectra-small-v3-discriminator",
    num_labels: int = 2,
    learning_rate: float = 2e-5,
    batch_size: int = 16,
    num_epochs: int = 3,
    max_length: int = 512,
    use_lora: bool = False
):
    """
    KoELECTRA 모델 파인튜닝

    실제 데이터 기준으로 작성된 코드입니다.
    실제 JSONL 파일을 읽어서 학습합니다.

    Args:
        data_dir: 실제 학습 데이터 디렉토리 경로
        output_dir: 모델 출력 디렉토리
        model_name: 베이스 모델 이름
        num_labels: 분류 클래스 수 (2: rule/policy)
        learning_rate: 학습률
        batch_size: 배치 크기
        num_epochs: 에폭 수
        max_length: 최대 길이
        use_lora: LoRA 사용 여부
    """
    logger.info("[START] KoELECTRA 파인튜닝 시작")
    logger.info(f"   - 데이터 디렉토리: {data_dir}")
    logger.info(f"   - 출력 디렉토리: {output_dir}")
    logger.info(f"   - 모델: {model_name}")

    # 1. 모델 및 토크나이저 로드
    logger.info("[LOAD] 모델 및 토크나이저 로드 중...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=num_labels
    )

    # LoRA 사용 여부
    if use_lora:
        from peft import LoraConfig, get_peft_model, TaskType
        logger.info("[CONFIG] LoRA 설정 중...")
        lora_config = LoraConfig(
            task_type=TaskType.SEQ_CLS,
            r=8,
            lora_alpha=16,
            lora_dropout=0.1,
            target_modules=["query", "key", "value", "dense"]
        )
        model = get_peft_model(model, lora_config)
        logger.info("[OK] LoRA 설정 완료")

    # 2. 데이터 로드
    logger.info("[LOAD] 학습 데이터 로드 중...")
    train_data = load_training_data(data_dir, "train")
    val_data = load_training_data(data_dir, "val")

    # 3. 데이터셋 준비
    logger.info("[PREPARE] 데이터셋 준비 중...")
    train_dataset = prepare_dataset(train_data, tokenizer, max_length)
    val_dataset = prepare_dataset(val_data, tokenizer, max_length)

    # 4. 데이터 콜레이터
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # 5. 학습 인자 설정
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_steps=100,
        logging_dir=f"{output_dir}/logs",
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=3,
        fp16=torch.cuda.is_available(),
    )

    # 6. Trainer 생성
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    # 7. 학습 실행
    logger.info("[TRAIN] 학습 시작...")
    trainer.train()

    # 8. 모델 저장
    logger.info("[SAVE] 모델 저장 중...")
    if use_lora:
        # LoRA 사용 시 어댑터만 저장
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
    else:
        # Full finetuning 시 전체 모델 저장
        trainer.save_model(output_dir)
        tokenizer.save_pretrained(output_dir)

    logger.info(f"[COMPLETE] 학습 완료! 모델 저장 위치: {output_dir}")

    # 9. 최종 평가
    logger.info("[EVAL] 최종 평가 중...")
    eval_results = trainer.evaluate()
    logger.info(f"[RESULT] 최종 평가 결과:")
    logger.info(f"   - Accuracy: {eval_results['eval_accuracy']:.4f}")
    logger.info(f"   - F1 Score: {eval_results['eval_f1']:.4f}")
    logger.info(f"   - Precision: {eval_results['eval_precision']:.4f}")
    logger.info(f"   - Recall: {eval_results['eval_recall']:.4f}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="KoELECTRA 파인튜닝 (정책/규칙 판별)")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="training/data/policy_rule_classification",
        help="학습 데이터 디렉토리"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/models/finetuned/koelectra-policy-rule",
        help="모델 출력 디렉토리"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="monologg/koelectra-small-v3-discriminator",
        help="베이스 모델 이름"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-5,
        help="학습률"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="배치 크기"
    )
    parser.add_argument(
        "--num-epochs",
        type=int,
        default=3,
        help="에폭 수"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="최대 길이"
    )
    parser.add_argument(
        "--use-lora",
        action="store_true",
        help="LoRA 사용"
    )

    args = parser.parse_args()

    train_koelectra(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        model_name=args.model_name,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        num_epochs=args.num_epochs,
        max_length=args.max_length,
        use_lora=args.use_lora
    )


if __name__ == "__main__":
    main()
