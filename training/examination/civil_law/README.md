# 민사소송법 답안 분석 모델 - 간단한 학습 가이드

**목적**: EXAONE 기반 민사소송법 답안 분석 모델 Fine-tuning

---

## 📁 폴더 구조

```
training/examination/civil_law/
├── data/
│   ├── train_samples.json      # 학습 데이터 (5개 샘플)
│   └── valid_samples.json      # 검증 데이터 (2개 샘플)
├── train_simple.py             # 간단한 학습 스크립트
├── test_model.py               # 모델 테스트 스크립트
└── README.md                   # 이 파일
```

---

## 🚀 빠른 시작

### Step 1: 필요한 패키지 설치

```bash
pip install torch transformers scikit-learn
```

**또는** 프로젝트 전체 패키지 설치:

```bash
pip install -r ../../requirements.txt
```

---

### Step 2: 학습 실행

```bash
# civil_law 폴더에서 실행
cd training/examination/civil_law
python train_simple.py
```

**예상 소요 시간**:
- GPU: 5-10분
- CPU: 30분-1시간 (데이터가 작아서 비교적 빠름)

**출력 예시**:
```
============================================================
민사소송법 답안 분석 모델 - 간단한 학습
============================================================

📁 데이터 경로:
  - 학습: .../data/train_samples.json
  - 검증: .../data/valid_samples.json
  - 출력: .../artifacts/models/finetuned/legal/checkpoint_simple

📊 데이터 로드 중...
  - 학습 샘플: 5개
  - 검증 샘플: 2개

🤖 모델 로드 중...
  ✅ LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct 로드 완료

📦 데이터셋 생성 중...
  - 학습 데이터셋: 5개
  - 검증 데이터셋: 2개

⚙️ 학습 설정:
  - 에포크: 2
  - 배치 사이즈: 2
  - 학습률: 2e-05
  - GPU 사용: True

🚀 학습 시작!
------------------------------------------------------------
...
✅ 학습 완료!

📊 최종 평가:
  - eval_loss: 0.8532
  - eval_accuracy: 0.5000
  - eval_f1: 0.4500

💾 모델 저장 중: .../artifacts/models/finetuned/legal/final_simple
✅ 모델 저장 완료!

============================================================
학습 완료! 🎉
============================================================
```

---

### Step 3: 모델 테스트

```bash
python test_model.py
```

**출력 예시**:
```
============================================================
민사소송법 답안 분석 모델 - 테스트
============================================================

📂 모델 로드 중: .../artifacts/models/finetuned/legal/final_simple
✅ 모델 로드 완료 (Device: cuda)

============================================================
테스트 1: 낮은 품질 답안
============================================================

📝 입력 텍스트:
----------------------------------------------------------------------------
[문제] 갑은 을에게 금전을 대여하였으나 변제기가 도과하였다...
[모범답안] I. 서론...
[사용자답안] 돈을 빌려줬으니 돌려받으면 된다.
============================================================

🎯 예측 결과:
  - 쟁점 포함률: 낮음 (< 40%)
  - 신뢰도: 85.23%
  - 확률 분포:
    • 낮음 (< 40%): 85.23%
    • 중간 (40-70%): 12.45%
    • 높음 (> 70%): 2.32%

...
```

---

## 📊 학습 데이터 설명

### train_samples.json (5개)

민사소송법 기본 문제 5개:
1. **대여금 청구** - 소비대차계약, 변제기 도과
2. **매매계약** - 채무불이행, 계약해제
3. **불법행위** - 화재 손해배상
4. **연대보증** - 최고·검색의 항변권
5. **임대차** - 무단전대

각 샘플 구조:
```json
{
  "id": "train-001",
  "problem": "문제 텍스트...",
  "reference_answer": "모범 답안...",
  "user_answer": "사용자 답안...",
  "labels": {
    "issue_coverage": 0.3,
    "identified_issues": [...],
    "missing_issues": [...],
    "logic_score": 0.4,
    "expression_score": 0.5
  }
}
```

### valid_samples.json (2개)

검증용 문제 2개:
1. **교통사고** - 손해배상의 범위
2. **착오** - 의사표시 취소

---

## 🎯 모델 목표

**분류 작업**: 사용자 답안의 쟁점 포함률을 3단계로 분류

- **Class 0 (낮음)**: 쟁점 포함률 < 40%
- **Class 1 (중간)**: 쟁점 포함률 40-70%
- **Class 2 (높음)**: 쟁점 포함률 > 70%

---

## 🔧 학습 설정

```python
TrainingArguments(
    num_train_epochs=2,              # 2 에포크 (빠른 테스트)
    per_device_train_batch_size=2,   # 배치 사이즈 2
    learning_rate=2e-5,              # 학습률
    weight_decay=0.01,               # 가중치 감쇠
    eval_strategy="epoch",           # 에포크마다 평가
    save_strategy="epoch",           # 에포크마다 저장
    fp16=True,                       # Mixed Precision (GPU)
)
```

---

## 📈 예상 성능

**주의**: 학습 데이터가 매우 작으므로 (5개), 성능은 제한적입니다.

**실제 프로덕션에서는**:
- 최소 100-500개 샘플 권장
- 더 많은 에포크 (5-10)
- 데이터 증강 (Augmentation)

**현재 목표**:
- ✅ 학습 파이프라인 동작 확인
- ✅ 모델 로드/저장 검증
- ✅ 추론 테스트
- ⚠️ 실제 성능은 데이터 추가 후 개선 필요

---

## 🚨 트러블슈팅

### 1. EXAONE 모델을 찾을 수 없음

**증상**:
```
⚠️ EXAONE 로드 실패: ...
⚠️ 대체 모델 사용: distilbert-base-uncased
```

**해결**:
- EXAONE 모델이 없으면 작은 대체 모델 사용
- 실제 EXAONE 사용하려면 Hugging Face에서 다운로드
- 또는 `artifacts/models/` 에 미리 준비

### 2. GPU 메모리 부족

**증상**:
```
CUDA out of memory
```

**해결**:
```python
# train_simple.py 수정
per_device_train_batch_size=1  # 배치 사이즈 줄이기
```

### 3. 학습이 너무 느림

**해결**:
- GPU 사용 확인: `torch.cuda.is_available()`
- 에포크 수 줄이기: `num_train_epochs=1`
- 더 작은 모델 사용

---

## 📚 다음 단계

### 1. 데이터 확장

더 많은 샘플 추가:
```bash
# data/ 폴더에 더 많은 샘플 추가
train_samples.json  # 5개 → 50개 → 500개
```

### 2. 학습 개선

- 더 많은 에포크
- Hyperparameter Tuning
- Data Augmentation

### 3. API 연동

```python
# app/domain/reasoning/services.py
from app.core.ml.model_loader import ModelLoader
from app.core.ml.inference import InferenceEngine

# 학습된 모델 사용
loader = ModelLoader.get_instance(
    model_path="artifacts/models/finetuned/legal/final_simple"
)
loader.load()

engine = InferenceEngine(loader)
result = engine.predict("답안 텍스트...")
```

### 4. 전체 플로우 테스트

```bash
# 1. 서버 시작
uvicorn app.main:app --reload

# 2. API 테스트
POST /api/v1/reasoning/analyze/issues
{
  "user_answer_id": "...",
  "reference_answer_id": "...",
  "problem_id": "..."
}
```

---

## 💡 팁

1. **작게 시작**: 5개 샘플로 파이프라인 검증
2. **점진적 확장**: 데이터 추가 → 재학습 → 평가
3. **로그 확인**: `artifacts/models/.../logs/` 에서 학습 과정 모니터링
4. **체크포인트 활용**: 중간 체크포인트로 테스트

---

## 📞 문제 해결

학습 중 문제가 발생하면:

1. **로그 확인**: 에러 메시지 전체 확인
2. **환경 점검**: Python 버전, GPU 상태
3. **데이터 검증**: JSON 파일 형식 확인
4. **간단한 테스트**: 작은 배치, 1 에포크로 시작

---

**Happy Training! 🚀**
