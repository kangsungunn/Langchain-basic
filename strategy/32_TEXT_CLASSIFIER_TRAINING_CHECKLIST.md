# ✅ 텍스트 분류 학습 파이프라인 요구사항 체크리스트

## 📋 개요

`app/services/spam_classifier/train.py`가 요구사항을 모두 만족하는지 확인한 문서입니다.

**작성일**: 2025-01-01
**코드 파일**: `app/services/spam_classifier/train.py`

---

## ✅ 요구사항 체크리스트

### 1. 베이스 모델 및 태스크

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| 베이스 모델: `monologg/koelectra-small-v3-discriminator` | ✅ | `load_koelectra_model()` 사용 |
| 태스크: 텍스트 분류 (SequenceClassification) | ✅ | `AutoModelForSequenceClassification` 사용 |
| 다태스크 지원: spam, sentiment 등 | ✅ | `--task` 파라미터로 지원 |
| 생성 모델 관련 코드 제거 | ✅ | EXAONE 관련 코드 없음 |

### 2. 학습 모드

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| 기본값: full finetuning | ✅ | `--mode full` (기본값) |
| 옵션: LoRA (비양자화) | ✅ | `--mode lora` |
| QLoRA/4bit/bitsandbytes 금지 | ✅ | 사용하지 않음 |
| `prepare_model_for_kbit_training` 금지 | ✅ | 사용하지 않음 |

### 3. Trainer 및 학습 방식

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| Trainer 기반 학습 | ✅ | `Trainer` 사용 |
| SFTTrainer 사용 금지 | ✅ | 사용하지 않음 |
| `formatting_func` 사용 금지 | ✅ | 사용하지 않음 |
| `dataset_text_field` 사용 금지 | ✅ | 사용하지 않음 |
| `TaskType.SEQ_CLS` 사용 | ✅ | LoRA 모드에서 사용 |

### 4. 데이터 요구사항

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| Dataset에 `text` 컬럼 필수 | ✅ | `validate_dataset()`에서 검증 |
| Dataset에 `label` 컬럼 필수 | ✅ | `validate_dataset()`에서 검증 |
| label 없으면 명확한 에러 | ✅ | `ValueError` 발생 |
| 학습 시작 시 샘플 수 출력 | ✅ | `validate_dataset()`에서 출력 |
| 컬럼 목록 출력 | ✅ | `validate_dataset()`에서 출력 |
| label 분포 출력 | ✅ | 클래스별 count 및 비율 출력 |
| `load_from_disk()` 사용 | ✅ | HuggingFace Dataset 로드 |

### 5. 학습 모드 설계

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| `train.py` 하나에서 모드 선택 | ✅ | `--mode full/lora` 파라미터 |
| Full finetuning 구현 | ✅ | `mode="full"` |
| LoRA mode 구현 | ✅ | `mode="lora"` |
| `peft.get_peft_model` 사용 | ✅ | LoRA 모드에서 사용 |
| `target_modules` 기본값 | ✅ | `["query", "key", "value", "dense"]` |
| r=8 또는 16 기본값 | ✅ | `--lora-r 8` (기본값) |

### 6. TrainingArguments

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| `evaluation_strategy` 사용 (올바른 키) | ✅ | `eval_strategy` 아님! |
| `metric_for_best_model` 기본값 | ✅ | spam: `spam_recall`, 기타: `macro_f1` |
| `greater_is_better=True` | ✅ | 설정됨 |
| `remove_unused_columns=False` | ✅ | 설정됨 |
| fp16은 GPU에서만 활성화 | ✅ | `torch.cuda.is_available()` 체크 |
| `bf16=False` | ✅ | CUDA 호환성 고려 |

### 7. 평가 메트릭

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| `compute_metrics` 함수 구현 | ✅ | `compute_metrics()` 함수 |
| accuracy 계산 | ✅ | `accuracy_score` 사용 |
| macro_f1 계산 | ✅ | `f1_score(average="macro")` |
| class별 precision/recall | ✅ | 클래스별로 계산 |
| spam_recall (스팸 태스크) | ✅ | task=="spam"일 때 계산 |
| spam_f1 (스팸 태스크) | ✅ | task=="spam"일 때 계산 |
| best model 선정 기준 | ✅ | task에 따라 다르게 설정 |

### 8. 클래스 불균형 대응

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| `--class-weight` 옵션 제공 | ✅ | `--class-weight` 플래그 |
| train labels 기준 class weight 계산 | ✅ | `WeightedTrainer`에서 계산 |
| `CrossEntropyLoss(weight=...)` 적용 | ✅ | `WeightedTrainer.compute_loss()` 오버라이드 |

### 9. 출력 구조

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| `models/{task}/{mode}/run_{timestamp}/` 구조 | ✅ | 구현됨 |
| `config.json` 저장 | ✅ | `trainer.save_model()` |
| `pytorch_model.bin` 또는 `safetensors` 저장 | ✅ | `trainer.save_model()` |
| `tokenizer` 파일들 저장 | ✅ | `tokenizer.save_pretrained()` |
| `metrics.json` 저장 | ✅ | 별도로 저장 |

### 10. 주의사항 준수

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| `SFTTrainer` 사용 금지 | ✅ | 사용하지 않음 |
| `formatting_func` 사용 금지 | ✅ | 사용하지 않음 |
| `dataset_text_field` 사용 금지 | ✅ | 사용하지 않음 |
| `eval_strategy` 같은 잘못된 키 사용 금지 | ✅ | `evaluation_strategy` 사용 |
| `max_length` 기본값 128 또는 256 | ✅ | 기본값 256 |
| accuracy만 보고 best model 선정하지 않음 | ✅ | task별로 다른 메트릭 사용 |

### 11. 문서화

| 요구사항 | 상태 | 비고 |
|---------|------|------|
| 파일 상단 주석: "생성 모델이 아닌 분류 모델 학습용" | ✅ | 주석 추가 |
| "EXAONE은 verdict/설명 생성 전용으로 분리됨" | ✅ | 주석 추가 |
| 실행 예시 CLI 주석 | ✅ | docstring 및 argparse epilog에 포함 |

---

## 📊 코드 구조 요약

### 주요 함수

1. **`train_classifier()`**: 메인 학습 함수
   - 다태스크 지원 (`task` 파라미터)
   - 학습 모드 선택 (`mode` 파라미터)
   - 데이터 검증 및 전처리
   - LoRA 설정 (옵션)
   - Trainer 생성 및 학습

2. **`validate_dataset()`**: 데이터셋 검증
   - `text`, `label` 컬럼 필수 확인
   - 라벨 분포 계산 및 출력
   - 샘플 수 및 컬럼 목록 출력

3. **`compute_metrics()`**: 평가 메트릭 계산
   - accuracy, macro_f1
   - 클래스별 precision/recall
   - 스팸 태스크 특화 메트릭

4. **`setup_lora_adapter()`**: LoRA 설정
   - `TaskType.SEQ_CLS` 사용
   - KoElectra 구조에 맞는 target_modules

5. **`WeightedTrainer`**: 클래스 불균형 대응
   - `CrossEntropyLoss(weight=...)` 적용

### CLI 인터페이스

```bash
# Full finetuning (기본)
python train.py --task spam --mode full

# LoRA mode
python train.py --task sentiment --mode lora --lora-r 16

# 클래스 불균형 대응
python train.py --task spam --mode full --class-weight
```

---

## ✅ 최종 검증 결과

**전체 요구사항 만족도: 100%**

모든 요구사항이 구현되었으며, 요구사항에 명시된 금지 사항도 모두 준수되었습니다.

### 주요 개선사항

1. ✅ 다태스크 지원 추가
2. ✅ Full finetuning 모드 추가
3. ✅ 데이터 검증 강화 (text+label 필수)
4. ✅ 평가 메트릭 구현
5. ✅ 클래스 불균형 대응 추가
6. ✅ 출력 디렉토리 구조 개선
7. ✅ TrainingArguments 키 수정 (`evaluation_strategy`)
8. ✅ max_length 기본값 조정 (256)

---

**검증 완료일**: 2025-01-01
**검증자**: AI Assistant
**상태**: ✅ 모든 요구사항 만족
