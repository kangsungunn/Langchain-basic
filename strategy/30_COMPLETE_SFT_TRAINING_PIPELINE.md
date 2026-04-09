# 🎯 EXAONE 기반 스팸 필터 SFT 학습 완전 가이드

## 📋 개요

이 문서는 **EXAONE-2.4B 모델을 스팸 필터 에이전트로 학습시키기까지의 전체 파이프라인**을 단계별로 설명하고, 각 단계의 역할과 관련 이론을 상세히 다룹니다.

**목표**: CSV 원본 데이터부터 학습된 LoRA 어댑터까지의 완전한 ETL 파이프라인 구현

---

## 🗺️ 전체 파이프라인 개요

```
┌─────────────────────────────────────────────────────────────────┐
│              EXAONE 스팸 필터 학습 파이프라인                    │
└─────────────────────────────────────────────────────────────────┘

[Phase 1: Extract]
  CSV 파일 읽기 및 파싱
  ↓
[Phase 2: Transform - 데이터 변환]
  CSV → JSONL 변환 (extract_jsonl.py)
  JSONL → SFT JSONL 변환 (extract_dpo.py)
  데이터 품질 검증 및 분할 (transform_jsonl.py)
  HuggingFace Dataset 변환 (transform_jsonl.py)
  ↓
[Phase 3: Load - 모델 및 데이터 로드]
  EXAONE-2.4B 모델 로드 (4-bit 양자화) (load_model.py)
  HuggingFace Dataset 로드 (transform_jsonl.py)
  ↓
[Phase 4: Train - 학습]
  QLoRA 어댑터 설정 (lora_adapter.py)
  SFTTrainer 학습 실행 (lora_adapter.py)
  LoRA 어댑터 저장
  ↓
[Phase 5: Evaluate - 평가]
  검증 데이터셋 평가
  메트릭 계산
  ↓
[Phase 6: Deploy - 배포]
  에이전트 클래스 구현
  API 통합
```

---

## 📊 단계별 상세 설명

### Phase 1: Extract (추출)

#### 1.1 목적 및 역할

**목적**: 원본 CSV 데이터를 읽고 구조화된 JSONL 형식으로 변환

**역할**:
- CSV 파일 파싱 및 메타데이터 추출
- 스팸 판정 근거 자동 생성
- 신뢰도 자동 계산
- JSONL 포맷으로 저장 (스트리밍 처리 가능)

#### 1.2 구현 모듈

**파일**: `app/services/spam_agent/extract_jsonl.py`

**주요 기능**:
```python
class SpamDataConverter:
    def convert_csv_to_jsonl(
        self,
        csv_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        1. CSV 파일 읽기 (UTF-8-sig 인코딩)
        2. 메타데이터 추출 (날짜, 시간, 제목, 첨부파일)
        3. 첨부파일 파싱 (크기 정보 제거, 파일명만 추출)
        4. 스팸 판정 근거 자동 생성
        5. 신뢰도 자동 계산
        6. JSONL 포맷으로 저장
        """
```

**입력 데이터 구조**:
```csv
수신일자,수신시간,메일 종류,제목,첨부
2024-01-01,00:20:30,스팸,Offer,"Offer.docx (16.4 K), ..."
```

**출력 데이터 구조**:
```json
{
  "instruction": "다음 이메일 메타데이터를 분석하여 스팸 여부를 판정하세요.",
  "input": {
    "subject": "Offer",
    "attachments": ["Offer.docx", "Offer - contextual advertising.docx"],
    "date": "2024-01-01",
    "time": "00:20:30",
    "mail_type": "스팸"
  },
  "output": {
    "action": "BLOCK",
    "reason": "의심스러운 제목 패턴",
    "confidence": 0.95
  }
}
```

#### 1.3 이론: JSONL 포맷의 장점

**JSONL (JSON Lines)**은 LLM 학습의 사실상 표준 포맷입니다:

1. **메모리 효율성**
   - 전체 파일을 메모리에 로드할 필요 없음
   - 스트리밍 처리 가능
   - 대용량 데이터셋 처리에 적합

2. **샘플 단위 처리**
   - 한 줄 = 한 샘플 구조
   - LLM 학습 루프와 완벽히 일치
   ```python
   for sample in dataset:
       train(sample)
   ```

3. **HuggingFace Datasets 호환성**
   - `datasets` 라이브러리가 JSONL을 기본 지원
   - 자동 캐싱 및 샤딩 지원

**실행 결과**:
- 입력: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.csv` (95,134개 샘플)
- 출력: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.jsonl` (95,133개 샘플)

---

### Phase 2: Transform (변환)

#### 2.1 Step 1: JSONL → SFT JSONL 변환

**목적**: 일반 JSONL을 SFT(Supervised Fine-Tuning) 학습용 형식으로 변환

**구현 모듈**: `app/services/spam_agent/extract_dpo.py`

**주요 기능**:
- 중복 제거 (subject + attachments 기준)
- Rule-based labeling
- Instruction 포맷 적용
- 데이터 정규화

**중복 제거 전략**:
- **기준**: `subject` + `attachments` 조합
- **효과**: 95,133개 → 24,571개 (약 74% 제거)
- **이유**: 동일한 패턴의 스팸 메일이 반복되는 경우가 많음

**SFT 데이터 구조**:
```json
{
  "instruction": "다음 이메일 메타데이터를 분석하여 스팸 여부를 판정하고 JSON 형식으로만 답하세요.",
  "input": {
    "subject": "Offer",
    "attachments": ["Offer.docx"],
    "received_at": "2024-01-01 00:20:30"
  },
  "output": {
    "action": "BLOCK",
    "reason": "스팸/광고성 키워드 패턴이 포함됨 / 첨부파일이 포함됨",
    "confidence": 0.99
  }
}
```

**출력 파일**: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.sft.jsonl`

#### 2.2 Step 2: 데이터 품질 검증 및 분할

**목적**: 데이터 품질 검증 및 Train/Validation/Test 분할

**구현 모듈**: `app/services/spam_agent/transform_jsonl.py`

**주요 기능**:

1. **데이터 품질 검증** (`DataQualityValidator`)
   - 필수 필드 존재 여부 확인
   - JSON 형식 유효성 검증
   - 데이터 타입 검증
   - 신뢰도 범위 검증 (0.0-1.0)

2. **데이터 분포 분석**
   - BLOCK/ALLOW 비율
   - 제목 길이 분포
   - 첨부파일 유무 비율
   - 신뢰도 분포

3. **Train/Validation/Test 분할**
   - **전략**: 80% / 10% / 10%
   - **방법**: 랜덤 시드 고정 (재현성 보장)
   - **결과**:
     - Train: 19,656개 (80%)
     - Validation: 2,457개 (10%)
     - Test: 2,458개 (10%)

**이론: Train/Validation/Test 분할의 이유**

1. **Train Set (80%)**
   - 모델 학습에 사용
   - 최대한 많은 데이터로 학습

2. **Validation Set (10%)**
   - 학습 중 모델 성능 평가
   - 하이퍼파라미터 튜닝
   - Early stopping 결정
   - 과적합 방지

3. **Test Set (10%)**
   - 최종 모델 성능 평가
   - 학습 과정에서 한 번도 사용하지 않음
   - 일반화 성능 측정

**참고**: 일부 프로젝트에서는 Train(90%) / Validation(10%)만 사용하기도 합니다. Test Set은 최종 배포 전 평가용으로 보관하는 것이 좋습니다.

#### 2.3 Step 3: HuggingFace Dataset 변환

**목적**: JSONL을 HuggingFace `datasets.Dataset` 객체로 변환하여 저장

**이론: HuggingFace Datasets의 장점**

1. **자동 최적화**
   - Arrow 포맷으로 저장 (메모리 효율적)
   - 자동 캐싱 및 샤딩
   - 멀티프로세싱 지원

2. **Trainer/TRL 호환성**
   - `SFTTrainer`가 직접 `Dataset` 객체를 받음
   - 자동 배치 생성 및 셔플링
   - 데이터 로딩 최적화

3. **메모리 효율성**
   - 스트리밍 처리 지원
   - 지연 평가 (lazy evaluation)
   - 디스크 캐싱

**구현 기능** (`transform_jsonl.py`):

```python
def create_datasets_from_examples(
    examples: List[Dict[str, Any]],
    add_text_field: bool = False
) -> Dataset:
    """
    예제 리스트를 HuggingFace Dataset 객체로 변환

    Args:
        examples: JSONL 예제 리스트
        add_text_field: SFT 학습용 'text' 필드 추가 여부

    Returns:
        HuggingFace Dataset 객체
    """
```

**SFT 학습용 텍스트 필드 추가**:
- `add_text_field=True`일 때 자동으로 `text` 필드 생성
- EXAONE 프롬프트 형식으로 변환:
  ```
  [[system]]{instruction}[[endofturn]]
  [[user]]{user_prompt}[[endofturn]]
  [[assistant]]{response}[[endofturn]]
  ```

**저장 구조**:
```
app/data/spam_agent_processed/
├── train.jsonl                    # JSONL 형식
├── val.jsonl                      # JSONL 형식
├── train_dataset/                 # HuggingFace Dataset 객체
│   ├── data-00000-of-00001.arrow
│   ├── dataset_info.json
│   └── state.json
└── val_dataset/                   # HuggingFace Dataset 객체
    ├── data-00000-of-00001.arrow
    ├── dataset_info.json
    └── state.json
```

**사용 예시**:
```python
from app.services.spam_agent.transform_jsonl import DataQualityValidator

validator = DataQualityValidator()
train_dataset, val_dataset, test_dataset = validator.load_datasets(
    dataset_dir=Path("app/data/spam_agent_processed"),
    splits=["train", "val", "test"]
)

# SFTTrainer에서 직접 사용
trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,  # Dataset 객체 직접 전달
    eval_dataset=val_dataset,
    ...
)
```

---

### Phase 3: Load (로드)

#### 3.1 EXAONE-2.4B 모델 로드 (4-bit 양자화)

**목적**: 메모리 효율적으로 EXAONE-2.4B 모델을 GPU에 로드

**구현 모듈**: `app/services/spam_agent/load_model.py`

**주요 기능**:

```python
def load_exaone_model_4bit(
    model_path: Optional[str] = None,
    device_map: str = "auto",
    verbose: bool = True
) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
    """
    EXAONE-2.4B 모델을 4-bit 양자화로 로드

    Returns:
        (model, tokenizer) 튜플
    """
```

#### 3.2 이론: 4-bit 양자화 (QLoRA)

**양자화(Quantization)**란 모델의 가중치를 낮은 비트로 표현하여 메모리 사용량을 줄이는 기법입니다.

**4-bit 양자화의 장점**:

1. **메모리 절약**
   - FP32 (32-bit): 원본 모델 크기
   - FP16 (16-bit): 절반 크기
   - **INT4 (4-bit)**: 약 1/8 크기
   - 2.4B 모델 → 약 1.2GB (4-bit)

2. **NF4 (NormalFloat4) 양자화**
   - 정규 분포를 따르는 가중치에 최적화
   - 균등 양자화보다 성능 저하 적음
   - QLoRA 논문에서 제안

3. **Double Quantization**
   - 양자화 상수(quantization constants)도 양자화
   - 추가 메모리 절약 (~0.4GB)

**BitsAndBytesConfig 설정**:
```python
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,                    # 4-bit 양자화 활성화
    bnb_4bit_quant_type="nf4",            # NF4 양자화 타입
    bnb_4bit_compute_dtype=torch.bfloat16,  # 계산 dtype (bfloat16)
    bnb_4bit_use_double_quant=True,       # Double Quantization 활성화
)
```

**GPU 메모리 요구사항**:
- **원본 모델 (FP32)**: ~9.6GB
- **4-bit 양자화**: ~1.5-2GB
- **학습 중 (gradient 포함)**: ~4-6GB

**주의사항**:
- 4-bit 양자화 모델은 **모든 레이어가 GPU에 있어야 함**
- CPU 오프로드 불가능
- `device_map={"": 0}` 명시적 설정 권장

#### 3.3 모델 로드 과정

1. **GPU 확인**
   ```python
   if not torch.cuda.is_available():
       raise RuntimeError("GPU가 필요합니다.")
   ```

2. **4-bit 양자화 설정**
   - `BitsAndBytesConfig` 생성

3. **모델 로드**
   ```python
   model = AutoModelForCausalLM.from_pretrained(
       model_path,
       quantization_config=bnb_config,
       device_map={"": 0},  # GPU 0에 모든 레이어 로드
       trust_remote_code=True,  # EXAONE 전용 코드 필요
       local_files_only=True,
   )
   ```

4. **토크나이저 로드**
   ```python
   tokenizer = AutoTokenizer.from_pretrained(
       model_path,
       trust_remote_code=True,
       local_files_only=True,
   )

   # Pad token 설정
   if tokenizer.pad_token is None:
       tokenizer.pad_token = tokenizer.eos_token
   tokenizer.padding_side = "right"
   ```

**로드 결과**:
- 모델: 4-bit 양자화된 EXAONE-2.4B
- GPU 메모리 사용량: ~1.5-2GB
- 총 파라미터: 1,333,813,760개
- 학습 가능 파라미터: 262,300,160개 (양자화 전)

---

### Phase 4: Train (학습)

#### 4.1 QLoRA 어댑터 설정

**목적**: 파라미터 효율적 파인튜닝을 위한 LoRA 어댑터 설정

**구현 모듈**: `app/services/spam_agent/lora_adapter.py`

**주요 기능**:

```python
def setup_qlora_adapter(
    model,
    lora_r: int = 8,
    lora_alpha: int = 16,
    lora_dropout: float = 0.05,
    target_modules: Optional[list] = None,
    verbose: bool = True
):
    """
    QLoRA 어댑터 설정 및 적용

    Returns:
        PEFT 모델 (LoRA 어댑터 적용됨)
    """
```

#### 4.2 이론: LoRA (Low-Rank Adaptation)

**LoRA의 핵심 아이디어**:

전체 모델을 학습하는 대신, **저차원 행렬(Low-Rank Matrix)을 추가**하여 학습합니다.

**수학적 표현**:
```
원본: W (d × d 크기)
LoRA: W + ΔW = W + BA
  - B: (d × r) 크기
  - A: (r × d) 크기
  - r << d (rank, 예: 8)
```

**메모리 효율성**:
- 전체 모델 학습: 모든 파라미터의 gradient 저장 필요
- LoRA 학습: 작은 어댑터만 학습 (약 0.1% 파라미터)

**LoRA 하이퍼파라미터**:

1. **r (rank)**: 8
   - LoRA 행렬의 차원
   - 작을수록 메모리 절약, 성능 저하 가능
   - 8-16이 일반적

2. **alpha**: 16
   - LoRA 스케일링 파라미터
   - `alpha/r` 비율이 학습률에 영향
   - 일반적으로 `alpha = 2 * r`

3. **dropout**: 0.05
   - 과적합 방지
   - 일반적으로 0.05-0.1

4. **target_modules**: `["q_proj", "k_proj", "v_proj", "o_proj"]`
   - LoRA를 적용할 모듈
   - Attention 레이어에 적용
   - EXAONE 구조에 맞춤

**QLoRA (Quantized LoRA)**:
- 4-bit 양자화 + LoRA 조합
- 메모리 효율성 극대화
- 성능 저하 최소화

**학습 가능 파라미터**:
```
trainable params: 2,764,800 || all params: 2,408,092,160 || trainable%: 0.1148
```
- 전체 파라미터의 약 0.11%만 학습
- 메모리 사용량 대폭 감소

#### 4.3 학습 프로세스

**구현 모듈**: `app/services/spam_agent/lora_adapter.py`

**주요 함수**:

```python
def train_qlora_sft(
    model_path: Optional[str] = None,
    train_dataset_path: Optional[str] = None,
    val_dataset_path: Optional[str] = None,
    output_dir: str = "./checkpoints/exaone-spam-filter",
    # QLoRA 설정
    lora_r: int = 8,
    lora_alpha: int = 16,
    lora_dropout: float = 0.05,
    # 학습 하이퍼파라미터
    learning_rate: float = 2e-4,
    num_train_epochs: int = 3,
    per_device_train_batch_size: int = 4,
    gradient_accumulation_steps: int = 4,
    max_length: int = 512,
    ...
) -> Dict[str, Any]:
    """
    QLoRA SFT 학습 실행

    Returns:
        학습 결과 딕셔너리
    """
```

**학습 단계**:

1. **모델 로드**
   ```python
   model, tokenizer = load_exaone_model_4bit(model_path=model_path)
   ```

2. **QLoRA 어댑터 설정**
   ```python
   model = setup_qlora_adapter(
       model,
       lora_r=lora_r,
       lora_alpha=lora_alpha,
       lora_dropout=lora_dropout,
   )
   ```

3. **데이터셋 로드**
   ```python
   train_dataset, val_dataset, _ = validator.load_datasets(
       dataset_dir=Path(train_dataset_path),
       splits=["train", "val"]
   )
   ```

4. **텍스트 필드 자동 추가** (없는 경우)
   - EXAONE 프롬프트 형식으로 변환
   - `text` 필드 생성

5. **학습 인자 설정**
   ```python
   training_args = TrainingArguments(
       output_dir=output_dir,
       num_train_epochs=num_train_epochs,
       per_device_train_batch_size=per_device_train_batch_size,
       gradient_accumulation_steps=gradient_accumulation_steps,
       learning_rate=learning_rate,
       warmup_steps=100,
       max_steps=-1,  # epochs 사용
       logging_steps=10,
       save_steps=100,
       eval_steps=100,
       save_strategy="steps",
       eval_strategy="steps",
       fp16=False,  # BFloat16 양자화 모델과 호환
       bf16=True,   # BFloat16 사용
       optim="paged_adamw_8bit",
       lr_scheduler_type="cosine",
       save_total_limit=3,
   )
   ```

6. **SFTTrainer 생성 및 학습**
   ```python
   trainer = SFTTrainer(
       model=model,
       args=training_args,
       train_dataset=train_dataset,
       eval_dataset=val_dataset,
       tokenizer=tokenizer,
       max_seq_length=max_length,
       dataset_text_field="text",
       packing=False,
       formatting_func=formatting_func,
       callbacks=[TrainingProgressCallback()],
   )

   train_result = trainer.train()
   ```

7. **모델 저장**
   ```python
   trainer.save_model(str(final_model_path))
   tokenizer.save_pretrained(str(final_model_path))
   ```

#### 4.4 이론: SFT (Supervised Fine-Tuning)

**SFT의 목적**:
- Instruction-following 능력 향상
- 도메인 특화 지식 주입
- 출력 형식 학습 (JSON 형식 등)

**SFTTrainer의 장점**:
1. **자동 프롬프트 처리**
   - `text` 필드를 자동으로 토크나이징
   - Loss 계산 시 label masking 자동 처리

2. **최적화된 학습 루프**
   - Gradient checkpointing
   - Mixed precision training
   - DataLoader 최적화

3. **메모리 효율성**
   - Packing 지원 (여러 샘플을 하나의 시퀀스로)
   - Gradient accumulation
   - 8-bit optimizer

#### 4.5 하이퍼파라미터 설명

**학습률 (Learning Rate)**: 2e-4
- LoRA 학습에는 일반적으로 1e-4 ~ 5e-4 사용
- 너무 크면 불안정, 너무 작으면 학습 느림

**배치 크기 (Batch Size)**: 4
- GPU 메모리에 맞춰 조정
- 효과적 배치 크기 = `per_device_batch_size × gradient_accumulation_steps` = 16

**에폭 (Epochs)**: 3
- 데이터셋을 3번 반복 학습
- 과적합 방지를 위해 조기 종료 가능

**최대 길이 (Max Length)**: 512 tokens
- 시퀀스 길이 제한
- 메모리 사용량과 성능의 트레이드오프

**Warmup Steps**: 100
- 학습 초기 학습률을 점진적으로 증가
- 불안정한 학습 방지

**Mixed Precision**: BFloat16
- 4-bit 양자화 모델과 호환
- FP16과 충돌하므로 BFloat16 사용

#### 4.6 학습 모니터링

**콜백 함수** (`TrainingProgressCallback`):
- 각 스텝마다 Loss, Learning Rate, Epoch 출력
- 학습 진행 상황 실시간 확인

**저장된 메트릭**:
- `train_loss`: 학습 손실
- `train_runtime`: 학습 시간
- `train_samples_per_second`: 처리 속도

**체크포인트 관리**:
- `save_steps=100`: 100 스텝마다 저장
- `save_total_limit=3`: 최근 3개만 유지
- `load_best_model_at_end=True`: 최고 성능 모델 로드

---

## 📁 생성된 파일 구조

```
app/
├── data/
│   ├── 한국우편사업진흥원_스팸메일 수신차단 목록_20241231.csv  # 원본
│   ├── 한국우편사업진흥원_스팸메일 수신차단 목록_20241231.jsonl  # Phase 1 출력
│   ├── 한국우편사업진흥원_스팸메일 수신차단 목록_20241231.sft.jsonl  # Phase 2.1 출력
│   └── spam_agent_processed/  # Phase 2.2, 2.3 출력
│       ├── train.jsonl
│       ├── val.jsonl
│       ├── train_dataset/  # HuggingFace Dataset
│       └── val_dataset/    # HuggingFace Dataset
│
├── models/
│   └── exaone-2.4b/  # 베이스 모델
│
├── checkpoints/
│   └── exaone-spam-filter/  # Phase 4 출력
│       ├── checkpoint-100/
│       ├── checkpoint-200/
│       └── final_model/  # 최종 LoRA 어댑터
│           ├── adapter_config.json
│           ├── adapter_model.safetensors
│           └── training_config.json
│
└── services/
    └── spam_agent/
        ├── extract_jsonl.py      # Phase 1
        ├── extract_dpo.py         # Phase 2.1
        ├── transform_jsonl.py      # Phase 2.2, 2.3
        ├── load_model.py          # Phase 3
        └── lora_adapter.py        # Phase 4
```

---

## 🚀 실행 방법

### 전체 파이프라인 실행

```bash
# 1. CSV → JSONL 변환
python app/services/spam_agent/extract_jsonl.py

# 2. JSONL → SFT JSONL 변환
python app/services/spam_agent/extract_dpo.py

# 3. 데이터 품질 검증 및 분할 + HuggingFace Dataset 변환
python app/services/spam_agent/transform_jsonl.py --create-datasets

# 4. QLoRA SFT 학습
python app/services/spam_agent/lora_adapter.py \
    --epochs 1 \
    --batch-size 1 \
    --gradient-accumulation 8 \
    --max-length 256 \
    --save-steps 200 \
    --no-fp16
```

### 최소 설정으로 학습 (GPU 메모리 절약)

```bash
python app/services/spam_agent/lora_adapter.py \
    --epochs 1 \
    --batch-size 1 \
    --gradient-accumulation 8 \
    --max-length 256 \
    --save-steps 200 \
    --lora-r 4 \
    --no-fp16
```

---

## 📊 데이터 통계

### Phase별 데이터 변화

| Phase | 파일 | 샘플 수 | 크기 | 설명 |
|-------|------|---------|------|------|
| 원본 | CSV | 95,134 | 9.4MB | 원본 CSV 파일 |
| Phase 1 | JSONL | 95,133 | 34MB | JSONL 변환 |
| Phase 2.1 | SFT JSONL | 24,571 | 9.4MB | 중복 제거 후 |
| Phase 2.2 | Train | 19,656 | - | 80% 분할 |
| Phase 2.2 | Val | 2,457 | - | 10% 분할 |
| Phase 2.2 | Test | 2,458 | - | 10% 분할 |

### 학습 설정

| 항목 | 값 | 설명 |
|------|-----|------|
| 모델 | EXAONE-2.4B | 베이스 모델 |
| 양자화 | 4-bit (NF4) | 메모리 절약 |
| LoRA rank | 8 | 어댑터 차원 |
| LoRA alpha | 16 | 스케일링 |
| 학습률 | 2e-4 | 기본값 |
| 배치 크기 | 1-4 | GPU 메모리에 따라 조정 |
| 그래디언트 누적 | 4-8 | 효과적 배치 크기 유지 |
| 에폭 | 1-3 | 기본 3, 테스트 시 1 |
| 최대 길이 | 256-512 | 기본 512, 메모리 절약 시 256 |

---

## ⚠️ 주의사항 및 트러블슈팅

### 1. GPU 메모리 부족

**증상**: `ValueError: Some modules are dispatched on the CPU or the disk`

**해결 방법**:
- 배치 크기 줄이기 (`--batch-size 1`)
- 최대 길이 줄이기 (`--max-length 256`)
- LoRA rank 줄이기 (`--lora-r 4`)
- GPU 메모리 캐시 정리 (`torch.cuda.empty_cache()`)

### 2. BFloat16 호환성

**증상**: `NotImplementedError: "_amp_foreach_non_finite_check_and_unscale_cuda" not implemented for 'BFloat16'`

**해결 방법**:
- `fp16=False`, `bf16=True` 명시적 설정
- 4-bit 양자화 모델은 BFloat16 사용 필수

### 3. 데이터셋 텍스트 필드 없음

**증상**: `ValueError: 데이터셋에 'text' 필드가 없습니다`

**해결 방법**:
- `lora_adapter.py`가 자동으로 `text` 필드 추가
- 또는 `transform_jsonl.py --add-text-field` 옵션 사용

### 4. Windows 파일 인코딩 문제

**증상**: `OSError: [Errno 22] Invalid argument` (한글 파일명)

**해결 방법**:
- `Path` 객체를 `str`로 변환
- 절대 경로 사용
- `glob` 패턴으로 파일 찾기

---

## 📈 예상 학습 시간

### 하드웨어별 예상 시간

| GPU | VRAM | 배치 크기 | 예상 시간 (1 에폭) |
|-----|------|-----------|-------------------|
| RTX 3050 | 6GB | 1 | ~4-6시간 |
| RTX 3060 | 12GB | 4 | ~1-2시간 |
| RTX 3090 | 24GB | 8 | ~30분-1시간 |

### 최소 설정 (메모리 절약)

- 배치 크기: 1
- 그래디언트 누적: 8
- 최대 길이: 256
- LoRA rank: 4
- 예상 시간: ~6-8시간 (RTX 3050, 1 에폭)

---

## 🎯 다음 단계

### 완료된 작업

- [x] CSV → JSONL 변환
- [x] JSONL → SFT JSONL 변환
- [x] 데이터 품질 검증 및 분할
- [x] HuggingFace Dataset 변환
- [x] EXAONE-2.4B 모델 로드 (4-bit 양자화)
- [x] QLoRA 어댑터 설정
- [x] SFTTrainer 학습 실행
- [x] LoRA 어댑터 저장

### 다음 작업

- [ ] 학습된 모델 평가 (Test Set)
- [ ] 에이전트 클래스 구현
- [ ] API 엔드포인트 추가
- [ ] DPO 학습 파이프라인 구현
- [ ] 배포 및 최적화

---

## 📚 참고 자료

### 논문

- [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314)
- [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
- [DPO: Direct Preference Optimization](https://arxiv.org/abs/2305.18290)

### 문서

- [HuggingFace Transformers](https://huggingface.co/docs/transformers)
- [HuggingFace Datasets](https://huggingface.co/docs/datasets)
- [TRL (SFTTrainer)](https://huggingface.co/docs/trl)
- [PEFT (LoRA)](https://huggingface.co/docs/peft)

### 모델

- [EXAONE-3.5 GitHub](https://github.com/LG-AI-EXAONE/EXAONE-3.5)

---

**작성일**: 2025-01-01
**버전**: 1.0
**상태**: 완료된 파이프라인 문서화
