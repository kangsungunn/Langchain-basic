# 🔄 모델 교체 작업: EXAONE → KoElectra

## 📋 개요

이 문서는 **EXAONE-2.4B 모델을 KoElectra-small-v3-discriminator 모델로 교체하는 작업**의 전체 흐름과 진행 과정을 기록합니다.

**⚠️ 중요**: 이 작업은 단순히 모델만 교체하는 것이 아닙니다. 모델 타입 변경(생성형 → 분류형)에 따라 **전체 파이프라인 구조, 학습 전략, 추론 방식, 데이터 처리 방식 등이 변경**될 수 있습니다. 이 문서는 그러한 변경사항을 모두 추적하고 반영합니다.

**목적**:
- EXAONE 기반 생성형 모델에서 KoElectra 기반 분류 모델로 전환
- 모델 아키텍처 변경에 따른 코드 수정 및 최적화
- **파이프라인 구조 및 전략 변경사항 추적**
- 전체 시스템 호환성 유지

**대상 모델**:
- **기존**: EXAONE-2.4B (CausalLM, 생성형)
- **신규**: KoElectra-small-v3-discriminator (SequenceClassification, 분류형)

**예상 변경 범위**:
- ✅ 모델 로드 코드
- ✅ 학습 파이프라인 구조
- ⏳ 추론 파이프라인 구조
- ✅ 데이터 처리 방식
- ⏳ 출력 형식 및 후처리
- ⏳ API 인터페이스
- ✅ 평가 메트릭

---

## 🎯 작업 목표

### 주요 변경사항

1. **모델 타입 변경**
   - `AutoModelForCausalLM` → `AutoModelForSequenceClassification`
   - 생성형 모델 → 분류 모델

2. **양자화 제거**
   - 4-bit 양자화 (QLoRA) 제거
   - 일반 모델 로드로 변경

3. **코드 간소화**
   - 복잡한 GPU 메모리 관리 제거
   - 간단한 모델 로드 로직으로 변경

4. **파이프라인 호환성**
   - 기존 데이터 처리 파이프라인 유지
   - 학습 및 추론 코드 수정

---

## 📊 전체 작업 흐름

```
┌─────────────────────────────────────────────────────────────┐
│              모델 교체 작업 흐름도                            │
│     (구조 및 전략 변경사항 포함)                              │
└─────────────────────────────────────────────────────────────┘

[Phase 1: 모델 준비] ✅
  KoElectra 모델 다운로드 및 확인
  └─> 모델 경로: app/models/.../koelectra-small-v3-discriminator
  └─> 모델 타입: SequenceClassification
  ↓
[Phase 2: 모델 로드 코드 수정] ✅
  load_model.py 수정 (EXAONE → KoElectra)
  └─> AutoModelForCausalLM → AutoModelForSequenceClassification
  └─> 4-bit 양자화 제거 → 일반 로드
  └─> 복잡한 GPU 메모리 관리 제거
  ↓
[Phase 3: 학습 파이프라인 재설계] ✅
  학습 파이프라인 구조 변경
  ├─> SFTTrainer → Trainer
  ├─> QLoRA → Full Finetuning / LoRA (옵션)
  ├─> 데이터 형식: instruction/input/output → text/label
  ├─> 손실 함수: CausalLM Loss → CrossEntropyLoss
  ├─> 평가 메트릭: Perplexity → Accuracy, F1, Precision, Recall
  └─> 파일: app/services/spam_classifier/train.py (신규 생성)
  ↓
[Phase 4: 추론 파이프라인 재설계] ⏳
  추론 구조 변경
  └─> model.generate() → model() → logits
  └─> 출력 형식: 텍스트 생성 → 분류 점수
  └─> 후처리 로직 추가 (JSON 형식 출력)
  ↓
[Phase 5: 통합 테스트] ⏳
  전체 파이프라인 테스트
  └─> 구조 변경 검증
  └─> 성능 비교
  ↓
[Phase 6: 문서 업데이트] ⏳
  관련 문서 및 전략 문서 업데이트
  └─> 구조 변경사항 반영
  └─> 새로운 전략 문서화
```

### 📐 상세 흐름도: Phase 3 (학습 파이프라인)

```
┌─────────────────────────────────────────────────────────────┐
│         Phase 3: 학습 파이프라인 상세 흐름도                  │
└─────────────────────────────────────────────────────────────┘

[Step 1] 모델 로드
    └─> load_koelectra_model()
    └─> AutoModelForSequenceClassification
    └─> AutoTokenizer
    └─> GPU로 이동 (.cuda())

[Step 2] 데이터셋 로드
    └─> Dataset.load_from_disk()
    └─> train_dataset, val_dataset

[Step 3] 데이터 형식 변환 및 검증
    ├─> convert_to_text_label_format()
    │   └─> instruction/input/output → text/label
    │   └─> BLOCK/ALLOW → 1/0
    ├─> validate_dataset()
    │   └─> 필수 컬럼 확인 (text, label)
    │   └─> 라벨 분포 확인
    └─> num_labels 최소값 보장 (≥ 2)

[Step 4] 데이터 전처리
    ├─> preprocess_function()
    │   └─> 토크나이징 (truncation=True, padding=False)
    │   └─> labels 추가
    └─> CustomDataCollator
        └─> 동적 패딩 (labels는 패딩하지 않음)

[Step 5] 학습 모드 설정
    ├─> Full Finetuning (기본)
    │   └─> 전체 모델 파라미터 학습
    └─> LoRA (옵션)
        └─> setup_lora_adapter()
        └─> target_modules: ["query", "key", "value", "dense"]

[Step 6] 학습 인자 설정
    └─> TrainingArguments
        ├─> 학습률: 2e-5
        ├─> 배치 크기: 16
        ├─> 최대 길이: 256
        ├─> eval_strategy: "steps" (주의: evaluation_strategy 아님!)
        └─> metric_for_best_model: "macro_f1"

[Step 7] Trainer 생성 및 학습
    ├─> Trainer / WeightedTrainer
    ├─> TrainingProgressCallback
    ├─> compute_metrics (평가 메트릭)
    └─> trainer.train()

[Step 8] 모델 저장
    ├─> trainer.save_model()
    ├─> tokenizer.save_pretrained()
    └─> metrics.json 저장
```

**⚠️ 주의**: 각 Phase에서 구조나 전략이 변경되면, 이 문서와 관련 전략 문서들이 함께 업데이트됩니다.

---

## 📝 진행 상황

### ✅ Phase 1: 모델 준비

**작업 내용**:
- KoElectra-small-v3-discriminator 모델 다운로드
- 모델 경로 확인 및 구조 파악

**완료일**: 2025-01-01

**모델 정보**:
- **모델명**: `monologg/koelectra-small-v3-discriminator`
- **모델 경로**: `app/models/models--monologg--koelectra-small-v3-discriminator/snapshots/7488f8db0f208beff4a1f3f9bb3ed04650a89ed7`
- **모델 타입**: SequenceClassification
- **용도**: 텍스트 분류 (스팸 필터링)

**다운로드 명령어**:
```bash
hf download monologg/koelectra-small-v3-discriminator
```

**모델 파일 구조**:
```
snapshots/7488f8db0f208beff4a1f3f9bb3ed04650a89ed7/
├── config.json
├── pytorch_model.bin
├── tokenizer_config.json
└── vocab.txt
```

**상태**: ✅ 완료

---

### ✅ Phase 2: 모델 로드 코드 수정

**작업 내용**:
- `app/services/spam_classifier/load_model.py` 수정
- EXAONE 관련 코드 제거
- KoElectra 모델 로드 함수 구현

**완료일**: 2025-01-01

#### 변경 전 (EXAONE)

```python
def load_exaone_model_4bit(
    model_path: Optional[str] = None,
    device_map: str = "auto",
    verbose: bool = True
) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
    """
    EXAONE-2.4B 모델을 4-bit 양자화로 로드
    """
    # 4-bit 양자화 설정
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # 모델 로드
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=bnb_config,
        device_map=device_map,
        trust_remote_code=True,
        local_files_only=True,
    )

    return model, tokenizer
```

#### 변경 후 (KoElectra)

```python
def load_koelectra_model(
    model_path: Optional[str] = None,
    verbose: bool = True
) -> Tuple[AutoModelForSequenceClassification, AutoTokenizer]:
    """
    koelectra-small-v3-discriminator 모델을 로드
    """
    # 모델 경로 설정
    if model_path is None:
        current_dir = Path(__file__).parent
        model_path_obj = current_dir.parent.parent / "models" / "models--monologg--koelectra-small-v3-discriminator" / "snapshots" / "7488f8db0f208beff4a1f3f9bb3ed04650a89ed7"
        model_path = str(model_path_obj.resolve())

    # 모델 로드 (양자화 없음)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_path,
        local_files_only=True,
    )

    if torch.cuda.is_available():
        model = model.cuda()

    # 토크나이저 로드
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        local_files_only=True,
    )

    return model, tokenizer
```

#### 주요 변경사항

| 항목 | EXAONE | KoElectra |
|------|--------|-----------|
| 모델 클래스 | `AutoModelForCausalLM` | `AutoModelForSequenceClassification` |
| 양자화 | 4-bit (NF4) | 없음 |
| 함수명 | `load_exaone_model_4bit()` | `load_koelectra_model()` |
| 반환 타입 | `Tuple[AutoModelForCausalLM, AutoTokenizer]` | `Tuple[AutoModelForSequenceClassification, AutoTokenizer]` |
| GPU 메모리 관리 | 복잡한 설정 | 간단한 `.cuda()` 호출 |
| `trust_remote_code` | 필수 | 불필요 |

**수정된 파일**:
- `app/services/spam_classifier/load_model.py`

**상태**: ✅ 완료

---

### ✅ Phase 3: 학습 파이프라인 재설계 및 구현

**작업 내용**:
- 범용 텍스트 분류 학습 파이프라인 구현 (`app/services/spam_classifier/train.py`)
- EXAONE (QLoRA + SFTTrainer) → KoElectra (Trainer, Full/LoRA 옵션)
- 데이터 형식 자동 변환 기능 추가
- 분류 모델에 맞는 학습 설정 및 평가 메트릭 구현

**완료일**: 2025-01-14

#### 📊 학습 파이프라인 구조 비교

**변경 전 (EXAONE - 생성형)**:
```
┌─────────────────────────────────────────────────┐
│         EXAONE 학습 파이프라인 구조              │
└─────────────────────────────────────────────────┘

[1] 모델 로드 (4-bit 양자화)
    └─> BitsAndBytesConfig (NF4)
    └─> AutoModelForCausalLM
    └─> device_map 설정

[2] 데이터 로드
    └─> instruction/input/output 형식
    └─> 프롬프트 템플릿 적용

[3] QLoRA 설정
    └─> prepare_model_for_kbit_training()
    └─> LoraConfig (target_modules: q_proj, k_proj, v_proj, o_proj)
    └─> get_peft_model()

[4] SFTTrainer 설정
    └─> formatting_func (프롬프트 포맷팅)
    └─> dataset_text_field="text"
    └─> max_seq_length
    └─> CausalLM 손실 함수

[5] 학습 실행
    └─> 생성형 학습 (다음 토큰 예측)
```

**변경 후 (KoElectra - 분류형)**:
```
┌─────────────────────────────────────────────────┐
│      KoElectra 학습 파이프라인 구조              │
└─────────────────────────────────────────────────┘

[1] 모델 로드 (일반 로드)
    └─> AutoModelForSequenceClassification
    └─> 간단한 .cuda() 호출

[2] 데이터 로드
    └─> Dataset.load_from_disk()
    └─> instruction/input/output → text/label 자동 변환

[3] 데이터 형식 변환 (자동)
    └─> convert_to_text_label_format()
    └─> BLOCK/ALLOW → 1/0 라벨 매핑

[4] 데이터 전처리
    └─> 토크나이징 (truncation, padding=False)
    └─> DataCollatorWithPadding (동적 패딩)

[5] 학습 모드 선택
    ├─> Full Finetuning (기본)
    │   └─> 전체 모델 파라미터 학습
    └─> LoRA (옵션)
        └─> LoraConfig (target_modules: query, key, value, dense)
        └─> TaskType.SEQ_CLS

[6] Trainer 설정
    └─> 일반 Trainer (SFTTrainer 아님)
    └─> CrossEntropyLoss (분류 손실)
    └─> compute_metrics (accuracy, F1, precision, recall)

[7] 학습 실행
    └─> 분류 학습 (라벨 예측)
```

#### 🔄 주요 변경사항 상세

##### 1. 학습 프레임워크 변경

| 항목 | EXAONE | KoElectra |
|------|--------|-----------|
| **Trainer 클래스** | `SFTTrainer` (TRL) | `Trainer` (Transformers) |
| **용도** | 생성형 모델 전용 | 범용 학습 (분류 포함) |
| **데이터 형식** | `text` 필드 (프롬프트) | `text` + `label` 필드 |
| **손실 함수** | CausalLM Loss (다음 토큰 예측) | CrossEntropyLoss (라벨 분류) |
| **평가 메트릭** | Perplexity, BLEU 등 | Accuracy, F1, Precision, Recall |

**이유**:
- `SFTTrainer`는 생성형 모델(CausalLM) 전용
- 분류 모델은 `Trainer` 사용이 표준
- `SFTTrainer`는 `text` 필드를 자동으로 프롬프트로 처리하지만, 분류 모델은 `text`와 `label`이 분리되어야 함

##### 2. 데이터 형식 자동 변환

**문제**: 기존 데이터가 `instruction/input/output` 형식

**해결**: `convert_to_text_label_format()` 함수 구현

```python
def convert_to_text_label_format(dataset: Dataset, task: str = "spam") -> Dataset:
    """
    instruction/input/output → text/label 자동 변환

    변환 로직:
    1. input에서 subject, attachments, received_at 추출
    2. 텍스트 형식으로 조합: "제목: {subject}\n첨부파일: {attachments}\n수신일시: {received_at}"
    3. output에서 action 추출 (BLOCK/ALLOW)
    4. 라벨 매핑: BLOCK=1, ALLOW=0
    """
    label_map = {"BLOCK": 1, "ALLOW": 0}
    # ... 변환 로직
```

**장점**:
- 기존 데이터 형식과 호환
- 자동 변환으로 수동 작업 불필요
- 다양한 데이터 형식 지원 가능

##### 3. 학습 모드: Full vs LoRA

**Full Finetuning (기본)**:
- 전체 모델 파라미터 학습
- 더 높은 성능 가능
- 더 많은 메모리 필요

**LoRA (옵션)**:
- 일부 파라미터만 학습 (어댑터)
- 메모리 효율적
- 빠른 학습

**선택 기준**:
- 모델이 작으면 (KoElectra-small) Full Finetuning 권장
- 메모리가 부족하면 LoRA 사용

##### 4. 평가 메트릭 구현

```python
def compute_metrics(eval_pred, task: str = "spam"):
    """
    분류 모델 평가 메트릭 계산

    기본 메트릭:
    - accuracy: 전체 정확도
    - macro_f1: 클래스별 F1 평균

    클래스별 메트릭:
    - class_{i}_precision
    - class_{i}_recall
    - class_{i}_f1

    스팸 태스크 특화:
    - spam_precision (Class 1)
    - spam_recall (Class 1)
    - spam_f1 (Class 1)
    """
```

#### 🐛 에러 해결 및 오개념 정정

##### 에러 1: `No module named 'sklearn'`

**문제**: `scikit-learn` 라이브러리 미설치

**해결**:
```bash
pip install scikit-learn
```

**오개념 정정**:
- ❌ "이미 설치되어 있다"고 가정
- ✅ 각 conda 환경마다 별도로 설치 필요 (`torch313` 환경)

##### 에러 2: OpenMP 라이브러리 중복

**문제**: `OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll already initialized`

**원인**: 여러 라이브러리가 OpenMP를 중복 링크

**해결**:
```powershell
$env:KMP_DUPLICATE_LIB_OK="TRUE"
```

**오개념 정정**:
- ❌ "에러가 아니라 경고"라고 무시
- ✅ 성능 저하 및 크래시 가능성 있음, 환경 변수 설정 필요

##### 에러 3: `evaluation_strategy` vs `eval_strategy`

**문제**: `TrainingArguments.__init__() got an unexpected keyword argument 'evaluation_strategy'`

**원인**: Transformers 라이브러리 버전에 따라 파라미터명이 다름

**해결**: `evaluation_strategy` → `eval_strategy`

**오개념 정정**:
- ❌ "항상 `evaluation_strategy` 사용"
- ✅ Transformers 버전에 따라 다름 (최신 버전은 `eval_strategy`)

##### 에러 4: 배치 크기 불일치

**문제**: `Expected input batch_size (1664) to match target batch_size (16)`

**원인**:
1. `DataCollatorWithPadding`이 `labels`도 패딩하려고 시도
2. `WeightedTrainer.compute_loss()`에서 `logits.view(-1, ...)` 사용 (시퀀스 분류는 불필요)

**해결**:

1. **커스텀 DataCollator 구현**:
```python
class CustomDataCollator(DataCollatorWithPadding):
    def __call__(self, features):
        # labels를 별도로 추출 (패딩하지 않음)
        labels = [f.pop("labels") for f in features]
        batch = super().__call__(features)
        batch["labels"] = torch.tensor(labels, dtype=torch.long)
        return batch
```

2. **WeightedTrainer 수정**:
```python
# ❌ 잘못된 코드 (토큰 분류용)
loss = loss_fct(logits.view(-1, num_labels), labels.view(-1))

# ✅ 올바른 코드 (시퀀스 분류용)
# logits: [batch_size, num_labels]
# labels: [batch_size]
loss = loss_fct(logits, labels)
```

**오개념 정정**:
- ❌ "모든 분류 모델에서 `view(-1, ...)` 필요"
- ✅ 시퀀스 분류: `[batch_size, num_labels]` 형태 유지
- ✅ 토큰 분류: `[batch_size * seq_length, num_labels]` 형태로 flatten

##### 에러 5: `num_labels=1` 문제

**문제**:
- 데이터에 라벨이 1개만 있음 (Class 1: 100%)
- `num_labels=1`로 설정되면 회귀 문제로 처리됨
- `Found dtype Long but expected Float` 에러 발생

**원인**:
- 회귀 문제(`num_labels=1`)는 `labels`가 Float 타입이어야 함
- 분류 문제는 `labels`가 Long 타입

**해결**:
```python
# num_labels 최소값 보장 (분류 문제는 최소 2개 클래스 필요)
if num_labels_train < 2:
    num_labels_train = 2  # 이진 분류로 처리
```

**오개념 정정**:
- ❌ "데이터에 라벨이 1개면 `num_labels=1` 사용"
- ✅ 분류 문제는 최소 2개 클래스 필요 (이진 분류)
- ✅ `num_labels=1`은 회귀 문제 (연속값 예측)

##### 에러 6: `metric_for_best_model` 오류

**문제**: `metric_for_best_model='eval_spam_recall'`이 평가 메트릭에 없음

**원인**:
- 데이터에 라벨이 1개만 있어서 `spam_recall`이 계산되지 않음
- `compute_metrics`에서 `num_labels >= 2`이고 실제로 라벨 1이 존재할 때만 계산

**해결**:
```python
# 동적으로 사용 가능한 메트릭 선택
if metric_for_best_model is None:
    if task == "spam":
        metric_for_best_model = "macro_f1"  # 항상 계산됨
    else:
        metric_for_best_model = "macro_f1"
```

**오개념 정정**:
- ❌ "태스크에 따라 고정된 메트릭 사용"
- ✅ 실제로 계산되는 메트릭에 따라 동적으로 선택

#### 📁 생성/수정된 파일

| 파일 경로 | 변경 내용 | 상태 |
|----------|----------|------|
| `app/services/spam_classifier/train.py` | 범용 텍스트 분류 학습 파이프라인 (신규 생성) | ✅ 완료 |
| `app/services/spam_classifier/load_model.py` | KoElectra 모델 로드 (Phase 2에서 완료) | ✅ 완료 |

#### 🎯 학습 파이프라인 구성 요소

```
┌─────────────────────────────────────────────────────────────┐
│              학습 파이프라인 구성 요소                        │
└─────────────────────────────────────────────────────────────┘

[1] 모델 로드 모듈
    └─> load_koelectra_model()
    └─> AutoModelForSequenceClassification
    └─> AutoTokenizer

[2] 데이터 처리 모듈
    ├─> load_from_disk() - 데이터셋 로드
    ├─> convert_to_text_label_format() - 형식 변환
    ├─> validate_dataset() - 데이터 검증
    └─> preprocess_function() - 토크나이징

[3] 학습 설정 모듈
    ├─> TrainingArguments - 학습 하이퍼파라미터
    ├─> setup_lora_adapter() - LoRA 설정 (옵션)
    └─> CustomDataCollator - 배치 처리

[4] 학습 실행 모듈
    ├─> Trainer / WeightedTrainer - 학습 실행
    ├─> TrainingProgressCallback - 진행 상황 출력
    └─> compute_metrics() - 평가 메트릭 계산

[5] 모델 저장 모듈
    ├─> trainer.save_model() - 모델 저장
    ├─> tokenizer.save_pretrained() - 토크나이저 저장
    └─> metrics.json - 평가 결과 저장
```

#### 📊 학습 실행 예시

```bash
# Full finetuning (기본)
$env:KMP_DUPLICATE_LIB_OK="TRUE"; python app/services/spam_classifier/train.py --task spam --mode full

# LoRA mode
$env:KMP_DUPLICATE_LIB_OK="TRUE"; python app/services/spam_classifier/train.py --task spam --mode lora

# 최소 설정으로 빠른 테스트
$env:KMP_DUPLICATE_LIB_OK="TRUE"; python app/services/spam_classifier/train.py --task spam --mode full --epochs 1 --batch-size 4 --save-steps 50
```

#### ✅ 완료된 기능

- [x] 범용 텍스트 분류 학습 파이프라인 구현
- [x] Full finetuning 모드 지원
- [x] LoRA 모드 지원 (옵션)
- [x] 데이터 형식 자동 변환 (instruction/input/output → text/label)
- [x] 클래스 불균형 대응 (WeightedTrainer)
- [x] 다양한 평가 메트릭 (accuracy, F1, precision, recall)
- [x] 스팸 태스크 특화 메트릭 (spam_recall, spam_f1)
- [x] 학습 진행 상황 출력 (TrainingProgressCallback)
- [x] 모델 및 메트릭 자동 저장

**상태**: ✅ 완료

---

### ⏳ Phase 4: 추론 코드 수정

**작업 내용**:
- 추론 파이프라인 수정
- 생성형 추론 → 분류형 추론으로 변경
- 출력 형식 변경 (텍스트 생성 → 분류 점수)

**예상 작업**:
1. `model.generate()` → `model()` 변경
2. 출력 파싱 로직 수정
3. JSON 형식 출력 유지

**상태**: ⏳ 진행 예정

---

### ⏳ Phase 5: 통합 테스트

**작업 내용**:
- 전체 파이프라인 테스트
- 모델 로드 테스트
- 학습 파이프라인 테스트
- 추론 파이프라인 테스트

**상태**: ⏳ 진행 예정

---

### ⏳ Phase 6: 문서 업데이트

**작업 내용**:
- 전략 문서 업데이트
- API 문서 업데이트
- 사용 가이드 업데이트

**상태**: ⏳ 진행 예정

---

## 📊 전체 파이프라인 비교 요약

### EXAONE vs KoElectra 파이프라인 비교

| 항목 | EXAONE (생성형) | KoElectra (분류형) | 변경 이유 |
|------|----------------|-------------------|----------|
| **모델 클래스** | `AutoModelForCausalLM` | `AutoModelForSequenceClassification` | 모델 타입 변경 |
| **모델 로드** | 4-bit 양자화 + `device_map` | 일반 로드 + `.cuda()` | 모델 크기 작아서 양자화 불필요 |
| **Trainer** | `SFTTrainer` (TRL) | `Trainer` (Transformers) | 분류 모델은 Trainer 사용 |
| **데이터 형식** | `text` (프롬프트) | `text` + `label` | 분류 모델은 라벨 필요 |
| **데이터 변환** | 프롬프트 템플릿 적용 | instruction/input/output → text/label | 자동 변환 기능 추가 |
| **학습 방식** | QLoRA (필수) | Full Finetuning (기본) / LoRA (옵션) | 모델이 작아서 Full 가능 |
| **손실 함수** | CausalLM Loss | CrossEntropyLoss | 분류 손실 함수 사용 |
| **배치 처리** | SFTTrainer 내부 처리 | CustomDataCollator | labels 패딩 방지 필요 |
| **평가 메트릭** | Perplexity, BLEU | Accuracy, F1, Precision, Recall | 분류 메트릭 사용 |
| **출력 형식** | 생성된 텍스트 (JSON) | 분류 점수 (logits) | 추론 단계에서 변경 예정 |

### 학습 파이프라인 단계별 비교

| 단계 | EXAONE | KoElectra | 설명 |
|------|--------|-----------|------|
| **1. 모델 로드** | 4-bit 양자화 설정 | 일반 로드 | KoElectra는 작아서 양자화 불필요 |
| **2. 데이터 로드** | instruction/input/output | instruction/input/output | 동일 (자동 변환) |
| **3. 데이터 변환** | 프롬프트 템플릿 | text/label 변환 | 분류 모델용 형식으로 변환 |
| **4. 전처리** | 토크나이징 (프롬프트) | 토크나이징 (텍스트) | 동일하지만 입력 형식 다름 |
| **5. 학습 설정** | QLoRA 설정 | Full/LoRA 선택 | 모델 크기에 따라 선택 |
| **6. Trainer** | SFTTrainer | Trainer | 분류 모델은 Trainer 사용 |
| **7. 학습 실행** | 생성형 학습 | 분류형 학습 | 손실 함수 및 목표 다름 |
| **8. 평가** | Perplexity 계산 | 분류 메트릭 계산 | Accuracy, F1 등 |

---

## 🔍 모델 비교

### EXAONE-2.4B vs KoElectra-small-v3-discriminator

| 항목 | EXAONE-2.4B | KoElectra-small-v3-discriminator |
|------|-------------|----------------------------------|
| **모델 타입** | CausalLM (생성형) | SequenceClassification (분류형) |
| **파라미터 수** | 2.4B | ~14M (small) |
| **용도** | 텍스트 생성 | 텍스트 분류 |
| **출력** | 시퀀스 생성 | 분류 점수/라벨 |
| **양자화** | 4-bit (QLoRA) | 불필요 |
| **메모리** | ~1.5-2GB (4-bit) | ~50MB |
| **학습 방식** | QLoRA (어댑터) | Fine-tuning (전체/부분) |
| **추론 방식** | `generate()` | `forward()` → logits |
| **한국어 지원** | ✅ 우수 | ✅ 우수 |
| **스팸 필터링** | 생성형 (JSON 출력) | 분류형 (점수 출력) |

### 장단점 비교

#### EXAONE-2.4B

**장점**:
- 생성형 모델로 유연한 출력 형식
- JSON 형식으로 구조화된 응답 생성 가능
- 근거(reason)와 신뢰도(confidence)를 자연어로 생성

**단점**:
- 큰 모델 크기 (메모리 부담)
- 양자화 필요 (복잡도 증가)
- 생성형 특성상 출력 형식 불안정 가능
- 학습 비용 높음

#### KoElectra-small-v3-discriminator

**장점**:
- 작은 모델 크기 (빠른 추론)
- 분류 모델로 안정적인 출력
- 양자화 불필요 (간단한 로드)
- 학습 비용 낮음
- 분류 태스크에 최적화

**단점**:
- 생성형 출력 불가 (JSON 형식 직접 생성 어려움)
- 근거(reason) 생성 불가 (별도 처리 필요)
- 모델 크기 제한으로 표현력 한계

---

## 🛠️ 기술적 변경사항

### 1. 모델 로드

**변경 전**:
```python
# 4-bit 양자화 설정
bnb_config = BitsAndBytesConfig(...)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map={"": 0},
    trust_remote_code=True,
)
```

**변경 후**:
```python
# 일반 모델 로드
model = AutoModelForSequenceClassification.from_pretrained(
    model_path,
    local_files_only=True,
)
if torch.cuda.is_available():
    model = model.cuda()
```

### 2. 추론 방식

**변경 전 (생성형)**:
```python
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(
    **inputs,
    max_new_tokens=50,
    temperature=0.7,
)
response = tokenizer.decode(outputs[0])
```

**변경 후 (분류형)**:
```python
inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
with torch.no_grad():
    outputs = model(**inputs)
logits = outputs.logits
probs = torch.softmax(logits, dim=-1)
predicted_class = torch.argmax(probs, dim=-1)
```

### 3. 학습 설정

**변경 전 (QLoRA + SFTTrainer)**:
```python
# QLoRA 설정
from peft import prepare_model_for_kbit_training, LoraConfig, get_peft_model

model = prepare_model_for_kbit_training(model)
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    task_type=TaskType.CAUSAL_LM,
)
model = get_peft_model(model, lora_config)

# SFTTrainer 설정
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    formatting_func=formatting_func,  # 프롬프트 포맷팅
    dataset_text_field="text",
    max_seq_length=512,
    ...
)
```

**변경 후 (Full/LoRA + Trainer)**:
```python
# Full Finetuning (기본)
# 모델 그대로 사용, 추가 설정 불필요

# 또는 LoRA (옵션)
from peft import LoraConfig, get_peft_model, TaskType

lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["query", "key", "value", "dense"],  # KoElectra 구조
    task_type=TaskType.SEQ_CLS,  # 분류 태스크
)
model = get_peft_model(model, lora_config)

# Trainer 설정
from transformers import Trainer, TrainingArguments

training_args = TrainingArguments(
    output_dir="./models",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    eval_strategy="steps",  # evaluation_strategy 아님!
    ...
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics,  # 분류 메트릭
    ...
)
```

### 4. 데이터 처리

**변경 전 (생성형)**:
```python
# 프롬프트 템플릿 적용
def formatting_func(examples):
    prompt = f"""다음 이메일을 분석하여 스팸 여부를 판단하세요.

이메일:
제목: {examples['subject']}
첨부파일: {examples['attachments']}
수신일시: {examples['received_at']}

답변:"""
    return {"text": prompt}

dataset = dataset.map(formatting_func)
```

**변경 후 (분류형)**:
```python
# 텍스트 + 라벨 형식으로 변환
def convert_to_text_label_format(dataset):
    def convert_example(example):
        # 텍스트 생성
        text = f"제목: {example['input']['subject']}\n첨부파일: {example['input']['attachments']}\n수신일시: {example['input']['received_at']}"

        # 라벨 추출
        action = example['output']['action']  # "BLOCK" or "ALLOW"
        label = 1 if action == "BLOCK" else 0

        return {"text": text, "label": label}

    return dataset.map(convert_example)

# 토크나이징
def preprocess_function(examples):
    tokenized = tokenizer(
        examples["text"],
        truncation=True,
        padding=False,  # DataCollator에서 처리
        max_length=256,
    )
    tokenized["labels"] = examples["label"]
    return tokenized

dataset = dataset.map(preprocess_function, batched=True)
```

### 5. 손실 함수

**변경 전 (생성형)**:
```python
# CausalLM Loss (다음 토큰 예측)
# 모델 내부에서 자동 처리
# logits: [batch_size, seq_length, vocab_size]
# labels: [batch_size, seq_length] (shifted)
loss = CrossEntropyLoss(logits.view(-1, vocab_size), labels.view(-1))
```

**변경 후 (분류형)**:
```python
# CrossEntropyLoss (라벨 분류)
# logits: [batch_size, num_labels]
# labels: [batch_size]
loss = CrossEntropyLoss(logits, labels)  # view(-1) 불필요!
```

---

## 📁 파일 변경 내역

### 수정된 파일

| 파일 경로 | 변경 내용 | 상태 |
|----------|----------|------|
| `app/services/spam_classifier/load_model.py` | EXAONE → KoElectra 모델 로드 | ✅ 완료 |
| `app/services/spam_classifier/train.py` | 범용 텍스트 분류 학습 파이프라인 (신규 생성) | ✅ 완료 |
| `app/services/spam_classifier/extract_dpo.py` | 추론 파이프라인 수정 | ⏳ 예정 |
| `app/services/spam_classifier/transform_jsonl.py` | 데이터 처리 수정 | ⏳ 예정 |

### 새로 생성된 파일

| 파일 경로 | 설명 | 상태 |
|----------|------|------|
| `strategy/31_MODEL_MIGRATION_EXAONE_TO_KOELECTRA.md` | 모델 교체 작업 문서 | ✅ 완료 |
| `strategy/32_TEXT_CLASSIFIER_TRAINING_CHECKLIST.md` | 텍스트 분류 학습 체크리스트 | ✅ 완료 |

---

## 🚨 주의사항

### 1. 모델 타입 불일치

**문제**: EXAONE은 생성형, KoElectra는 분류형 모델

**해결**:
- 추론 코드 전면 수정 필요
- 출력 형식 변경 필요
- JSON 형식 출력을 위한 후처리 로직 추가

### 2. 데이터 형식 호환성

**문제**: 기존 데이터가 생성형 모델용으로 설계됨

**해결**:
- 데이터 전처리 로직 수정
- 분류 모델용 입력 형식으로 변환
- 라벨 인코딩 추가

### 3. 학습 파이프라인 변경

**문제**: QLoRA 학습 파이프라인을 일반 Fine-tuning으로 변경

**해결**:
- `app/services/spam_classifier/train.py` 신규 생성
- 범용 텍스트 분류 학습 파이프라인 구현
- Full Finetuning 및 LoRA 모드 지원
- 분류 모델 학습 설정 추가
- 손실 함수 변경 (CausalLM → CrossEntropyLoss)

### 4. 에러 해결 및 오개념 정정

**주요 에러 및 해결**:
1. **sklearn 모듈 없음** → 각 conda 환경마다 별도 설치 필요
2. **OpenMP 라이브러리 중복** → `KMP_DUPLICATE_LIB_OK=TRUE` 환경 변수 설정
3. **evaluation_strategy 오류** → `eval_strategy` 사용 (Transformers 버전 차이)
4. **배치 크기 불일치** → CustomDataCollator 구현, WeightedTrainer 수정
5. **num_labels=1 문제** → 최소 2로 강제 설정 (분류는 이진 분류 이상 필요)
6. **metric_for_best_model 오류** → 동적으로 사용 가능한 메트릭 선택

**오개념 정정**:
- ❌ "모든 분류 모델에서 `view(-1, ...)` 필요" → ✅ 시퀀스 분류는 불필요
- ❌ "데이터에 라벨이 1개면 `num_labels=1` 사용" → ✅ 분류는 최소 2개 클래스 필요
- ❌ "태스크에 따라 고정된 메트릭 사용" → ✅ 실제 계산되는 메트릭에 따라 동적 선택

---

## 📚 참고 자료

### 모델 정보

- [KoElectra GitHub](https://github.com/monologg/KoELECTRA)
- [KoElectra HuggingFace](https://huggingface.co/monologg/koelectra-small-v3-discriminator)
- [EXAONE GitHub](https://github.com/LG-AI-EXAONE/EXAONE-3.5)

### 관련 문서

- `strategy/28_EXAONE_TRAINING_LOOP_STRATEGY.md`: EXAONE 학습 전략
- `strategy/30_COMPLETE_SFT_TRAINING_PIPELINE.md`: 전체 SFT 파이프라인

---

## 📅 작업 일정

| Phase | 작업 내용 | 시작일 | 완료일 | 상태 |
|-------|----------|--------|--------|------|
| Phase 1 | 모델 준비 | 2025-01-01 | 2025-01-01 | ✅ 완료 |
| Phase 2 | 모델 로드 코드 수정 | 2025-01-01 | 2025-01-01 | ✅ 완료 |
| Phase 3 | 학습 파이프라인 재설계 | 2025-01-14 | 2025-01-14 | ✅ 완료 |
| Phase 4 | 추론 코드 수정 | - | - | ⏳ 예정 |
| Phase 5 | 통합 테스트 | - | - | ⏳ 예정 |
| Phase 6 | 문서 업데이트 | - | - | ⏳ 예정 |

---

## 🔄 업데이트 로그

### 2025-01-01

**Phase 1 완료**: KoElectra 모델 다운로드 및 확인
- 모델 경로: `app/models/models--monologg--koelectra-small-v3-discriminator/snapshots/7488f8db0f208beff4a1f3f9bb3ed04650a89ed7`
- 모델 파일 확인 완료

**Phase 2 완료**: 모델 로드 코드 수정
- `app/services/spam_classifier/load_model.py` 수정 완료
- EXAONE 관련 코드 제거
- KoElectra 모델 로드 함수 구현
- 코드 간소화 완료

### 2025-01-14

**Phase 3 완료**: 학습 파이프라인 재설계 및 구현
- `app/services/spam_classifier/train.py` 신규 생성
- 범용 텍스트 분류 학습 파이프라인 구현
- EXAONE (QLoRA + SFTTrainer) → KoElectra (Trainer, Full/LoRA) 전환
- 데이터 형식 자동 변환 기능 추가
- 여러 에러 해결 및 오개념 정정
- 학습 성공적으로 완료

**주요 성과**:
- ✅ Full finetuning 및 LoRA 모드 지원
- ✅ 데이터 형식 자동 변환 (instruction/input/output → text/label)
- ✅ 클래스 불균형 대응 (WeightedTrainer)
- ✅ 다양한 평가 메트릭 구현
- ✅ 학습 진행 상황 실시간 출력

**다음 작업**: Phase 4 (추론 파이프라인 재설계)

---

## 📝 구조 및 전략 변경사항 추적

### 변경사항 카테고리

이 섹션은 모델 교체 과정에서 발생하는 **구조적 변경사항**과 **전략적 변경사항**을 추적합니다.

#### 1. 파이프라인 구조 변경

**현재 상태**: KoElectra 기반 분류형 파이프라인 (학습 완료)

**완료된 변경사항**:
- [x] 학습 파이프라인 구조 변경
  - SFTTrainer → Trainer
  - 생성형 학습 → 분류형 학습
  - QLoRA → Full/LoRA 옵션
- [ ] 추론 파이프라인 구조 변경 (Phase 4 예정)
- [x] 데이터 처리 파이프라인 구조 변경
  - instruction/input/output → text/label 자동 변환
  - DataCollatorWithPadding 커스터마이징
- [x] 평가 파이프라인 구조 변경
  - 생성형 메트릭 → 분류형 메트릭 (accuracy, F1, precision, recall)

**변경 내용**:
- 학습 파이프라인: `app/services/spam_classifier/train.py` 신규 생성
- 데이터 처리: `convert_to_text_label_format()` 함수로 자동 변환
- 평가 메트릭: `compute_metrics()` 함수로 분류 메트릭 계산

#### 2. 학습 전략 변경

**현재 상태**: Full Finetuning (기본) + LoRA (옵션)

**완료된 변경사항**:
- [x] 학습 방식 변경 (QLoRA → Full Finetuning / LoRA)
  - Full Finetuning: 전체 모델 파라미터 학습 (기본)
  - LoRA: 어댑터 방식 학습 (옵션, 메모리 효율적)
- [x] 하이퍼파라미터 전략 변경
  - 학습률: 2e-5 (기본값)
  - 배치 크기: 16 (기본값)
  - 최대 길이: 256 tokens
  - FP16 자동 감지
- [x] 데이터 형식 변경
  - instruction/input/output → text/label 자동 변환
  - BLOCK/ALLOW → 1/0 라벨 매핑
- [x] 손실 함수 변경
  - CausalLM Loss → CrossEntropyLoss
  - 시퀀스 분류 손실 함수 사용

**변경 내용**:
- Trainer 클래스: `SFTTrainer` → `Trainer`
- 손실 함수: 생성형 손실 → 분류형 손실 (CrossEntropyLoss)
- 데이터 형식: 프롬프트 기반 → 텍스트+라벨 기반
- 평가 메트릭: Perplexity → Accuracy, F1, Precision, Recall

#### 3. 추론 전략 변경

**현재 상태**: 생성형 추론 (`model.generate()`)

**예상 변경사항**:
- [ ] 추론 방식 변경 (생성형 → 분류형)
- [ ] 출력 형식 변경
- [ ] 후처리 로직 추가
- [ ] JSON 형식 출력 유지 방법

**변경 내용** (작업 진행 시 업데이트):
- TBD

#### 4. 데이터 처리 전략 변경

**현재 상태**: 분류 모델용 데이터 형식 (자동 변환 지원)

**완료된 변경사항**:
- [x] 입력 데이터 형식 변경
  - instruction/input/output → text/label 자동 변환
  - `convert_to_text_label_format()` 함수 구현
- [x] 라벨 인코딩 추가
  - BLOCK → 1
  - ALLOW → 0
  - 자동 매핑 처리
- [x] 데이터 전처리 로직 변경
  - 토크나이징: truncation=True, padding=False
  - DataCollatorWithPadding으로 동적 패딩
  - labels는 패딩하지 않음 (커스텀 DataCollator)
- [x] 평가 메트릭 변경
  - 생성형 메트릭 제거
  - 분류 메트릭 추가 (accuracy, F1, precision, recall)
  - 스팸 태스크 특화 메트릭 (spam_recall, spam_f1)

**변경 내용**:
- 데이터 변환: `convert_to_text_label_format()` 함수로 자동 처리
- 전처리: `preprocess_function()`으로 토크나이징
- 배치 처리: `CustomDataCollator`로 labels 패딩 방지
- 평가: `compute_metrics()` 함수로 분류 메트릭 계산

#### 5. API 인터페이스 변경

**현재 상태**: 생성형 모델 API

**예상 변경사항**:
- [ ] API 입력 형식 변경
- [ ] API 출력 형식 변경
- [ ] 에러 처리 변경

**변경 내용** (작업 진행 시 업데이트):
- TBD

---

## 🎯 전략 문서 연동

이 모델 교체 작업으로 인해 변경되는 전략 문서들을 추적합니다.

### 영향받는 전략 문서

| 문서 | 영향 범위 | 업데이트 상태 |
|------|----------|--------------|
| `28_EXAONE_TRAINING_LOOP_STRATEGY.md` | 학습 전략 전체 | ⏳ 업데이트 예정 |
| `30_COMPLETE_SFT_TRAINING_PIPELINE.md` | 파이프라인 구조 | ⏳ 업데이트 예정 |
| 기타 관련 문서 | TBD | ⏳ 확인 필요 |

### 전략 문서 업데이트 계획

- [ ] 각 Phase 완료 시 관련 전략 문서 검토
- [ ] 구조 변경사항 전략 문서에 반영
- [ ] 새로운 전략 문서 생성 (필요 시)

---

## 🧩 학습 파이프라인 구성 요소 상세 설명

### 1. 모델 로드 모듈 (`load_koelectra_model`)

**역할**: KoElectra 모델과 토크나이저를 메모리에 로드

**주요 기능**:
- 모델 경로 자동 탐지
- `AutoModelForSequenceClassification`로 모델 로드
- GPU 사용 가능 시 자동으로 GPU로 이동
- 토크나이저 로드

**입력**: `model_path` (선택적)
**출력**: `(model, tokenizer)` 튜플

### 2. 데이터 처리 모듈

#### 2.1 데이터셋 로드 (`load_from_disk`)

**역할**: 디스크에 저장된 데이터셋을 메모리로 로드

**주요 기능**:
- HuggingFace Dataset 형식으로 로드
- 학습/검증 데이터셋 분리 로드
- 기본 경로 자동 탐지

#### 2.2 데이터 형식 변환 (`convert_to_text_label_format`)

**역할**: 기존 데이터 형식을 분류 모델용 형식으로 변환

**변환 과정**:
```
입력 (instruction/input/output):
{
  "instruction": "...",
  "input": {
    "subject": "이메일 제목",
    "attachments": ["file1.pdf"],
    "received_at": "2025-01-01 10:00:00"
  },
  "output": {
    "action": "BLOCK"
  }
}

↓ 변환

출력 (text/label):
{
  "text": "제목: 이메일 제목\n첨부파일: file1.pdf\n수신일시: 2025-01-01 10:00:00",
  "label": 1  # BLOCK=1, ALLOW=0
}
```

**주요 기능**:
- 자동 형식 감지 및 변환
- 라벨 매핑 (BLOCK/ALLOW → 1/0)
- 텍스트 조합 (subject + attachments + received_at)

#### 2.3 데이터 검증 (`validate_dataset`)

**역할**: 데이터셋의 유효성 검증

**검증 항목**:
- 필수 컬럼 존재 여부 (text, label)
- 라벨 분포 확인
- 샘플 수 확인

**출력**: `(num_labels, label_distribution)` 튜플

#### 2.4 데이터 전처리 (`preprocess_function`)

**역할**: 텍스트를 토큰으로 변환

**처리 과정**:
1. 텍스트 토크나이징
   - `truncation=True`: 최대 길이 초과 시 자름
   - `padding=False`: DataCollator에서 동적 패딩
   - `max_length=256`: 최대 토큰 수
2. 라벨 추가
   - 각 샘플의 라벨을 그대로 유지

**출력**: `{"input_ids": [...], "attention_mask": [...], "labels": [...]}`

#### 2.5 배치 처리 (`CustomDataCollator`)

**역할**: 배치 단위로 데이터를 패딩하고 텐서로 변환

**주요 기능**:
- 동적 패딩: 배치 내 최대 길이에 맞춰 패딩
- labels는 패딩하지 않음 (각 샘플당 하나의 라벨)
- 텐서 변환: 리스트 → PyTorch 텐서

**중요**: labels는 패딩하지 않아야 함 (배치 크기와 일치해야 함)

### 3. 학습 설정 모듈

#### 3.1 TrainingArguments

**역할**: 학습 하이퍼파라미터 설정

**주요 파라미터**:
- `num_train_epochs`: 에폭 수 (기본: 3)
- `per_device_train_batch_size`: 배치 크기 (기본: 16)
- `learning_rate`: 학습률 (기본: 2e-5)
- `eval_strategy`: 평가 전략 (기본: "steps")
- `save_steps`: 저장 간격 (기본: 100)
- `fp16`: FP16 사용 여부 (GPU 자동 감지)

**주의사항**:
- `evaluation_strategy` ❌ → `eval_strategy` ✅ (Transformers 버전 차이)

#### 3.2 LoRA 설정 (`setup_lora_adapter`)

**역할**: LoRA 어댑터를 모델에 적용 (옵션)

**주요 설정**:
- `r`: LoRA rank (기본: 8)
- `lora_alpha`: LoRA alpha (기본: 16)
- `target_modules`: LoRA 적용 모듈 (KoElectra: ["query", "key", "value", "dense"])
- `task_type`: TaskType.SEQ_CLS (분류 태스크)

**사용 시점**: `mode="lora"`일 때만 사용

### 4. 학습 실행 모듈

#### 4.1 Trainer / WeightedTrainer

**역할**: 실제 학습 실행

**Trainer**:
- 기본 학습 실행
- CrossEntropyLoss 사용

**WeightedTrainer**:
- 클래스 불균형 대응
- 가중치가 적용된 CrossEntropyLoss 사용
- `use_class_weight=True`일 때 사용

**주요 메서드**:
- `train()`: 학습 실행
- `evaluate()`: 평가 실행
- `save_model()`: 모델 저장

#### 4.2 TrainingProgressCallback

**역할**: 학습 진행 상황 실시간 출력

**출력 정보**:
- Step 수
- Epoch 수
- Loss 값
- Learning rate
- 평가 메트릭 (accuracy, F1 등)

#### 4.3 compute_metrics

**역할**: 평가 메트릭 계산

**계산 메트릭**:
- `accuracy`: 전체 정확도
- `macro_f1`: 클래스별 F1 평균
- `class_{i}_precision/recall/f1`: 클래스별 메트릭
- `spam_precision/recall/f1`: 스팸 태스크 특화 메트릭 (라벨 2개 이상일 때)

**입력**: `(predictions, labels)` 튜플
**출력**: 메트릭 딕셔너리

### 5. 모델 저장 모듈

**역할**: 학습된 모델과 메트릭 저장

**저장 내용**:
- 모델 가중치 (`pytorch_model.bin`)
- 모델 설정 (`config.json`)
- 토크나이저 파일들
- `metrics.json`: 학습 결과 및 평가 메트릭

**저장 경로**: `models/{task}/{mode}/run_{timestamp}/`

---

## 📋 요약

### 완료된 작업

1. ✅ **Phase 1**: KoElectra 모델 준비
2. ✅ **Phase 2**: 모델 로드 코드 수정
3. ✅ **Phase 3**: 학습 파이프라인 재설계 및 구현
   - 범용 텍스트 분류 학습 파이프라인 구현
   - Full Finetuning 및 LoRA 모드 지원
   - 데이터 형식 자동 변환
   - 다양한 평가 메트릭 구현
   - 여러 에러 해결 및 오개념 정정

### 핵심 변경사항

1. **모델 타입**: 생성형 (CausalLM) → 분류형 (SequenceClassification)
2. **학습 프레임워크**: SFTTrainer → Trainer
3. **학습 방식**: QLoRA → Full Finetuning / LoRA
4. **데이터 형식**: 프롬프트 기반 → 텍스트+라벨 기반
5. **손실 함수**: CausalLM Loss → CrossEntropyLoss
6. **평가 메트릭**: Perplexity → Accuracy, F1, Precision, Recall

### 다음 단계

- ⏳ **Phase 4**: 추론 파이프라인 재설계
- ⏳ **Phase 5**: 통합 테스트
- ⏳ **Phase 6**: 문서 업데이트

---

**작성일**: 2025-01-01
**마지막 업데이트**: 2025-01-14
**버전**: 2.0
**상태**: 진행 중 (Phase 3 완료)
