# KoELECTRA 파인튜닝 모듈

## 📋 개요

정책/규칙 판별을 위한 KoELECTRA 모델 파인튜닝 모듈입니다.

**핵심 원칙**:
- **실제 데이터 기준으로 코드 작성** - 실제 JSONL 파일을 읽어서 학습
- **더미데이터는 임시로만 사용** - 작업 중에 필요하면 더미데이터 생성 스크립트 실행
- **더미데이터 코드는 제거 가능** - `data_factory.py`는 나중에 제거해도 됨

---

## 🎯 사용 방법

### 1. 실제 데이터 준비 (프로덕션)

**실제 API 요청 로그를 수집하여 JSONL 형식으로 변환:**

```jsonl
{"text": "도메인: reasoning, 액션: comprehensive_analysis, 요청 요약: 사용자 답안 종합 분석 요청", "label": 1}
{"text": "도메인: training, 액션: create_training_data, 요청 요약: 학습 데이터 생성 요청", "label": 0}
```

**라벨 매핑**:
- `0`: rule (규칙 기반)
- `1`: policy (정책 기반)

**데이터 구조**:
```
training/data/policy_rule_classification/
├── train.jsonl    # 학습 데이터 (실제 데이터)
├── val.jsonl      # 검증 데이터 (실제 데이터)
└── test.jsonl     # 테스트 데이터 (실제 데이터)
```

### 2. 모델 학습 (실제 데이터 사용)

```bash
# 실제 데이터로 학습
python training/orchestration/train_koelectra_policy_rule.py \
    --data-dir training/data/policy_rule_classification \
    --output-dir artifacts/models/finetuned/koelectra-policy-rule \
    --num-epochs 5

# LoRA 사용 (메모리 절약)
python training/orchestration/train_koelectra_policy_rule.py \
    --data-dir training/data/policy_rule_classification \
    --output-dir artifacts/models/finetuned/koelectra-policy-rule \
    --use-lora \
    --num-epochs 3
```

### 3. 더미 데이터 생성 (임시 개발/테스트용)

⚠️ **실제 데이터가 준비되면 이 단계는 생략합니다.**

```bash
# 더미 학습 데이터 생성 (임시)
python training/orchestration/data_factory.py
```

**참고**: `data_factory.py`는 임시 개발용입니다. 실제 데이터가 준비되면 제거해도 됩니다.

---

## 📁 파일 구조

```
training/orchestration/
├── __init__.py
├── data_factory.py              # 더미 데이터 생성 (개발/테스트용)
├── train_koelectra_policy_rule.py  # 학습 스크립트 (실제 데이터 기준)
└── README.md

training/data/
└── policy_rule_classification/
    ├── train.jsonl              # 학습 데이터
    ├── val.jsonl                # 검증 데이터
    └── test.jsonl               # 테스트 데이터
```

---

## 🔧 코드 구조

### 실제 데이터 기준 코드

**`train_koelectra_policy_rule.py`**:
- 실제 JSONL 파일을 읽어서 학습
- 실제 데이터 형식 기준으로 작성
- 더미데이터와 독립적 (더미데이터 코드 제거해도 동작)

### 더미데이터 생성 (임시)

**`data_factory.py`**:
- ⚠️ 임시 개발/테스트용
- 실제 데이터가 준비되면 제거 가능
- 학습 스크립트와 독립적 (제거해도 학습 스크립트 동작)

---

## ✅ 체크리스트

### 개발 단계 (임시 더미 데이터 사용)
- [x] 더미 데이터 생성 스크립트 구현 (`data_factory.py`)
- [x] 학습 스크립트 구현 (실제 데이터 기준)
- [ ] 더미 데이터로 학습 파이프라인 검증
- [ ] 학습 스크립트 동작 확인

### 프로덕션 단계 (실제 데이터 사용)
- [ ] 실제 API 요청 로그 수집
- [ ] 정책/규칙 라벨링
- [ ] JSONL 형식으로 변환
- [ ] 실제 데이터로 학습
- [ ] 모델 성능 평가
- [ ] `data_factory.py` 제거 (선택사항)
- [ ] 프로덕션 배포

---

## 📚 참고

- `strategy/63.KOELECTRA_FINETUNING_STRATEGY.md` - 파인튜닝 전략
- `app/core/orchestration/decision_maker.py` - DecisionMaker 구현
- `app/core/ml/koelectra_loader.py` - KoELECTRA 로더
