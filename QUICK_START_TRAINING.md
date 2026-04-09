# 🚀 빠른 학습 시작 가이드

**목표**: 간단한 샘플 데이터로 EXAONE 모델 Fine-tuning 테스트

---

## ⚡ 3단계로 시작하기

### Step 1: 패키지 설치 (1분)

```bash
# 프로젝트 루트에서
pip install -r app/requirements.txt

# 또는 최소 필수만
pip install torch transformers scikit-learn
```

---

### Step 2: 학습 실행 (5-30분)

```bash
# 학습 폴더로 이동
cd training/examination/civil_law

# 학습 시작
python train_simple.py
```

**예상 시간**:
- 🖥️ **GPU**: 5-10분
- 💻 **CPU**: 30분-1시간

**자동으로 실행되는 작업**:
1. 📊 학습 데이터 로드 (5개 샘플)
2. 🤖 EXAONE 모델 로드 (없으면 작은 대체 모델)
3. 🚀 2 에포크 학습
4. 💾 모델 저장: `artifacts/models/finetuned/legal/final_simple/`

---

### Step 3: 모델 테스트 (1분)

```bash
# 같은 폴더에서
python test_model.py
```

**테스트 결과**:
- ✅ 3가지 답안 품질 (낮음/중간/높음) 자동 테스트
- ✅ 예측 결과 및 신뢰도 출력
- ✅ 모델 동작 확인

---

## 📊 학습 데이터

**위치**: `training/examination/civil_law/data/`

- `train_samples.json` - 학습용 5개 샘플
- `valid_samples.json` - 검증용 2개 샘플

**샘플 주제**:
1. 대여금 청구 (소비대차)
2. 매매계약 (채무불이행)
3. 불법행위 (화재 손해배상)
4. 연대보증 (최고·검색의 항변권)
5. 임대차 (무단전대)

---

## 🎯 학습 목표

**분류 작업**: 사용자 답안의 쟁점 포함률을 3단계로 분류

```
Class 0: 낮음   (<40%)  - 쟁점 파악 부족
Class 1: 중간   (40-70%) - 일부 쟁점 포함
Class 2: 높음   (>70%)  - 대부분 쟁점 포함
```

---

## 📁 출력 파일

학습 후 생성되는 파일:

```
artifacts/models/finetuned/legal/
├── checkpoint_simple/          # 학습 중 체크포인트
│   ├── checkpoint-1/
│   ├── checkpoint-2/
│   └── logs/                   # 학습 로그
└── final_simple/               # 최종 모델 ⭐
    ├── pytorch_model.bin       # 모델 가중치
    ├── config.json             # 모델 설정
    ├── tokenizer_config.json   # 토크나이저 설정
    └── ...
```

---

## 🔍 테스트 예시

### 입력

```
[문제] 갑은 을에게 금전을 대여하였으나 변제기가 도과하였다...
[모범답안] I. 서론... II. 소비대차계약... III. 변제기 도과...
[사용자답안] 돈을 빌려줬으니 돌려받으면 된다.
```

### 출력

```
🎯 예측 결과:
  - 쟁점 포함률: 낮음 (< 40%)
  - 신뢰도: 85.23%
  - 확률 분포:
    • 낮음 (< 40%): 85.23%
    • 중간 (40-70%): 12.45%
    • 높음 (> 70%): 2.32%
```

---

## ⚠️ 주의사항

### 1. 현재는 테스트 목적

- ✅ 학습 파이프라인 검증
- ✅ 모델 로드/저장 확인
- ⚠️ **실제 성능은 제한적** (데이터 5개만)

### 2. 실제 프로덕션에서는

- 📈 **최소 100-500개 샘플** 필요
- 🔁 **5-10 에포크** 학습
- 📊 **데이터 증강** (Augmentation)
- 🎛️ **Hyperparameter Tuning**

### 3. EXAONE 모델을 못 찾으면

```
⚠️ EXAONE 로드 실패
⚠️ 대체 모델 사용: distilbert-base-uncased
```

**해결**: 작은 대체 모델로 자동 전환 (파이프라인 테스트 가능)

---

## 🚨 트러블슈팅

### GPU 메모리 부족

```python
# train_simple.py 에서 배치 사이즈 줄이기
per_device_train_batch_size=1  # 2 → 1
```

### 학습이 너무 느림

```python
# 에포크 줄이기
num_train_epochs=1  # 2 → 1
```

### 패키지 설치 오류

```bash
# 개별 설치
pip install torch
pip install transformers
pip install scikit-learn
```

---

## 📈 다음 단계

### 1. 데이터 확장 (추천)

```bash
# data/train_samples.json 에 더 많은 샘플 추가
5개 → 50개 → 500개
```

### 2. 학습 개선

- 더 많은 에포크 (5-10)
- Learning Rate 조정
- Batch Size 증가

### 3. API 연동

```python
# app/domain/reasoning/services.py 에서 사용
from app.core.ml.model_loader import ModelLoader

loader = ModelLoader.get_instance(
    model_path="artifacts/models/finetuned/legal/final_simple"
)
loader.load()
```

### 4. 전체 플로우 테스트

```bash
# 1. DB 연동
# 2. 서버 시작
uvicorn app.main:app --reload

# 3. API 테스트
POST /api/v1/reasoning/analyze/comprehensive
```

---

## 📚 상세 문서

더 자세한 내용은:
- `training/examination/civil_law/README.md` - 상세 가이드
- `strategy/45.SYSTEM_ARCHITECTURE_OVERVIEW.md` - 시스템 아키텍처

---

## 💡 팁

1. **작게 시작**: 5개 샘플로 파이프라인 검증
2. **로그 확인**: `artifacts/models/.../logs/` 에서 학습 과정 확인
3. **점진적 확장**: 데이터 추가 → 재학습 → 평가
4. **체크포인트 활용**: 중간 결과로 테스트

---

## 🎉 완료!

학습이 완료되면:

✅ **모델 저장**: `artifacts/models/finetuned/legal/final_simple/`
✅ **테스트 완료**: 3가지 답안 품질 분류 확인
✅ **다음 단계 준비**: DB 연동 또는 데이터 확장

**Happy Training! 🚀**

---

## ❓ 문제 해결

문제가 발생하면:

1. **로그 확인**: 에러 메시지 전체 복사
2. **환경 점검**: `python --version`, `nvidia-smi`
3. **간단한 테스트**: 1 에포크, 배치 1로 시작
4. **상세 가이드 참조**: `training/examination/civil_law/README.md`
