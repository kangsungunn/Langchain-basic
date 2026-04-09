# 🎓 모델 훈련 가이드

## 📊 전체 흐름

```
data/raw/              artifacts/models/base/
(법률 데이터)          (베이스 모델)
    ↓                       ↓
data/processed/        training/
(전처리 완료)          (훈련 스크립트)
    ↓                       ↓
    ╰──────→ 학습 실행 ←────╯
                ↓
    artifacts/models/finetuned/
    (훈련된 모델 저장)
```

---

## ✅ 단계별 실행 절차

### **Step 0: 환경 확인** (사전 준비)

```powershell
# GPU 확인
nvidia-smi

# Python 패키지 확인
pip list | Select-String -Pattern "torch|transformers|datasets"

# 필요시 설치
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers datasets accelerate peft
```

---

### **Step 1: 베이스 모델 확인** ⭐ (필수!)

#### KoELECTRA 모델 다운로드

HuggingFace에서 다운로드:
- URL: https://huggingface.co/monologg/koelectra-small-v3-discriminator
- 저장 경로: `artifacts/models/base/koelectra-small-v3-discriminator/`

필요한 파일:
```
artifacts/models/base/koelectra-small-v3-discriminator/
├── config.json
├── pytorch_model.bin (또는 model.safetensors)
├── vocab.txt
├── tokenizer.json
├── tokenizer_config.json
└── special_tokens_map.json
```

#### EXAONE 모델 (이미 있음 ✅)

```
artifacts/models/base/exaone-2.4b/
├── config.json ✅
├── model-00001-of-00002.safetensors ✅
├── model-00002-of-00002.safetensors ✅
└── ... (18개 파일)
```

**검증:**
```powershell
# 모델 파일 확인
Test-Path "artifacts/models/base/koelectra-small-v3-discriminator/config.json"
Test-Path "artifacts/models/base/exaone-2.4b/config.json"
```

---

### **Step 2: 학습 데이터 준비**

#### 2-1. 원본 데이터 수집

```
data/raw/
├── patent_law/
│   ├── law_text.txt          # 특허법 조문
│   ├── precedents.jsonl      # 판례
│   └── examination_cases.jsonl  # 심사 사례
│
└── trademark_law/
    ├── law_text.txt
    ├── precedents.jsonl
    └── examination_cases.jsonl
```

**JSONL 형식 예시:**
```json
{"input": "발명의 명칭: 인공지능 기반 특허 분석 시스템\n설명: ...", "output": "registered", "grounds": "특허법 제29조"}
{"input": "상표명: Legal AI\n지정상품: 법률 자문", "output": "rejected", "grounds": "상표법 제33조 1항 7호"}
```

#### 2-2. 데이터 전처리

**수동으로 train/val/test 분할:**

```powershell
# 디렉토리 생성
New-Item -ItemType Directory -Path data/processed/patent -Force

# 수동으로 JSONL 파일 생성
# data/processed/patent/train.jsonl  (80%)
# data/processed/patent/val.jsonl    (10%)
# data/processed/patent/test.jsonl   (10%)
```

**또는 Python 스크립트로 분할:**

```python
# training/shared/split_data.py
import json
import random
from pathlib import Path

def split_data(input_path, output_dir, train_ratio=0.8, val_ratio=0.1):
    """데이터 분할"""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]

    random.shuffle(data)

    n = len(data)
    train_size = int(n * train_ratio)
    val_size = int(n * val_ratio)

    train_data = data[:train_size]
    val_data = data[train_size:train_size + val_size]
    test_data = data[train_size + val_size:]

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for name, subset in [("train", train_data), ("val", val_data), ("test", test_data)]:
        with open(f"{output_dir}/{name}.jsonl", 'w', encoding='utf-8') as f:
            for item in subset:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"✅ 분할 완료: train={len(train_data)}, val={len(val_data)}, test={len(test_data)}")

# 실행 예시
split_data("data/raw/patent_law/examination_cases.jsonl", "data/processed/patent")
```

**검증:**
```powershell
# 데이터 개수 확인
Get-Content data/processed/patent/train.jsonl | Measure-Object -Line
Get-Content data/processed/patent/val.jsonl | Measure-Object -Line
Get-Content data/processed/patent/test.jsonl | Measure-Object -Line
```

---

### **Step 3: 모델 훈련** 🚀

#### 3-1. 특허 모델 훈련

```powershell
# 훈련 실행
python training/examination/patent/train.py
```

**실행 과정:**
```
🔄 베이스 모델 로드 중: artifacts/models/base/koelectra-small-v3-discriminator
✅ 모델 로드 완료

🔄 데이터 로드 중: data/processed/patent
✅ 데이터 로드 완료: 1000 샘플

🔄 모델 훈련 시작
Epoch 1/3: 100%|████████████| 62/62 [02:30<00:00]
Epoch 2/3: 100%|████████████| 62/62 [02:28<00:00]
Epoch 3/3: 100%|████████████| 62/62 [02:29<00:00]
✅ 훈련 완료

✅ 모델 저장 완료: artifacts/models/finetuned/patent/final
📊 테스트 결과: {'eval_accuracy': 0.89, 'eval_loss': 0.32}
```

**결과 확인:**
```powershell
# 저장된 모델 확인
Get-ChildItem artifacts/models/finetuned/patent/ -Recurse

# 예상 결과:
# artifacts/models/finetuned/patent/
# ├── final/
# │   ├── config.json
# │   ├── pytorch_model.bin
# │   └── tokenizer files
# ├── checkpoint-500/
# ├── logs/
# └── eval_results.json
```

---

### **Step 4: 모델 평가 및 검증**

#### 4-1. 간단한 테스트

```python
# test_patent_model.py
from transformers import AutoModelForSequenceClassification, AutoTokenizer

model_path = "artifacts/models/finetuned/patent/final"

model = AutoModelForSequenceClassification.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)

# 테스트
text = "발명의 명칭: 블록체인 기반 특허 관리 시스템"
inputs = tokenizer(text, return_tensors="pt")
outputs = model(**inputs)

probs = outputs.logits.softmax(dim=1)
print(f"등록 가능: {probs[0][1]:.2%}")
print(f"거절 가능: {probs[0][0]:.2%}")
```

#### 4-2. 전체 테스트 셋 평가

```powershell
python training/examination/patent/evaluate.py
```

---

### **Step 5: 모델 통합 (app/core/로)**

훈련이 완료되면 `app/core/shared/models/`에서 로드 가능:

```python
# app/core/shared/models/loader.py
from transformers import AutoModelForSequenceClassification, AutoTokenizer

def load_patent_model():
    """특허 모델 로드"""
    model_path = "artifacts/models/finetuned/patent/final"

    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path)

    return model, tokenizer
```

---

## 📋 전체 체크리스트

### Phase 1: 사전 준비
- [ ] GPU 확인 (`nvidia-smi`)
- [ ] Python 패키지 설치 (`transformers`, `datasets`, `torch`)
- [ ] 폴더 구조 확인

### Phase 2: 베이스 모델
- [ ] KoELECTRA 다운로드 (HuggingFace에서 수동)
- [x] EXAONE 확인 (이미 있음)
- [ ] 모델 파일 검증 (`artifacts/models/base/`)

### Phase 3: 데이터 준비
- [ ] 원본 데이터 수집 (`data/raw/`)
- [ ] JSONL 형식 변환
- [ ] train/val/test 분할 (`data/processed/`)
- [ ] 데이터 개수 확인

### Phase 4: 훈련
- [ ] 훈련 스크립트 실행 (`training/examination/patent/train.py`)
- [ ] 훈련 로그 모니터링
- [ ] 모델 저장 확인 (`artifacts/models/finetuned/`)
- [ ] 평가 결과 확인 (`eval_results.json`)

### Phase 5: 검증
- [ ] 간단한 추론 테스트
- [ ] 정확도 확인 (목표: 85% 이상)
- [ ] app/core/에서 로드 가능 확인

---

## 🚨 트러블슈팅

### 문제 1: GPU 메모리 부족

**증상:**
```
RuntimeError: CUDA out of memory
```

**해결:**
```python
# train.py에서 배치 크기 줄이기
trainer.train(
    batch_size=8,  # 16 → 8
)
```

### 문제 2: 베이스 모델이 없음

**증상:**
```
OSError: artifacts/models/base/koelectra-small-v3-discriminator does not appear to have a file named config.json
```

**해결:**
HuggingFace에서 모델을 다운로드하여 `artifacts/models/base/koelectra-small-v3-discriminator/` 경로에 저장

### 문제 3: 데이터 형식 오류

**증상:**
```
KeyError: 'input'
```

**해결:**
JSONL 파일이 올바른 형식인지 확인:
```json
{"input": "...", "output": "..."}
```

---

## 📊 예상 소요 시간

| 단계 | 소요 시간 |
|------|----------|
| 베이스 모델 다운로드 | 10-30분 |
| 데이터 준비 | 1-2시간 |
| 훈련 (1,000 샘플, 3 epochs) | 10-30분 |
| 평가 및 검증 | 10분 |
| **총계** | **2-4시간** |

---

## 🎯 다음 단계

훈련 완료 후:

1. **상표 모델 훈련**
   ```powershell
   python training/examination/trademark/train.py
   ```

2. **EXAONE 파인튜닝 (LoRA)**
   ```powershell
   python training/dispute/train_exaone_lora.py
   ```

3. **app/core/ 통합**
   - 모델 로더 작성
   - API 엔드포인트 연결
   - 테스트

---

**작성일**: 2026-01-20
**버전**: 1.0
