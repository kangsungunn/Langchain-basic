# 🧪 2단계 필터링 시스템 테스트 전략

## 📋 개요

학습된 KoElectra 모델의 성능을 검증하고, EXAONE과 연계한 2단계 필터링 시스템을 구축하기 위한 단계별 전략입니다.

**목적**:
- KoElectra 모델 학습 성능 검증
- 2단계 필터링 시스템 구축 (KoElectra 1차 + EXAONE 2차)
- 로컬 환경에서 임시 테스트 인터페이스 구축

**시스템 구조**:
```
사용자 입력 (메일 텍스트)
    ↓
[1차 필터: KoElectra]
    ├─> 빠른 스팸 분류
    ├─> 출력: 스팸 확률, 예측 라벨
    └─> 스팸으로 판단되면 → [2차 필터: EXAONE]
    └─> 정상으로 판단되면 → ALLOW (종료)
    ↓
[2차 필터: EXAONE] (스팸 의심 시에만)
    ├─> 상세 판별 및 검증
    ├─> 출력: JSON 형식 (action, reason, confidence)
    └─> 최종 판정
```

---

## 🎯 단계별 전략

### ✅ Phase 1: KoElectra 추론 모듈 구현

**목표**: 학습된 KoElectra 모델로 스팸 분류 수행

**작업 내용**:
1. ✅ 추론 모듈 생성 (`app/services/spam_classifier/inference.py`)
2. ✅ 모델 로드 (학습된 모델, 자동 탐지 지원)
3. ✅ 텍스트 전처리 및 토크나이징
4. ✅ 분류 수행 및 확률 계산
5. ✅ 결과 반환 (라벨, 확률, 신뢰도)

**완료일**: 2025-01-14

**출력 형식**:
```python
{
    "label": 1,  # 0: ALLOW, 1: BLOCK
    "probability": 0.95,  # 스팸 확률
    "confidence": "high",  # high/medium/low
    "prediction": "BLOCK"
}
```

**주요 기능**:
- 학습된 모델 자동 탐지 (최신 run 디렉토리)
- 임계값 기반 스팸 판정
- 신뢰도 자동 계산 (high/medium/low)
- GPU 자동 감지 및 사용

---

### ✅ Phase 2: EXAONE 추론 모듈 구현

**목표**: EXAONE 모델로 상세 판별 수행

**작업 내용**:
1. ✅ EXAONE 추론 모듈 생성 (`app/services/spam_classifier/exaone_inference.py`)
2. ✅ 모델 로드 (기존 EXAONE 모델 경로 활용)
3. ✅ 프롬프트 템플릿 구성
4. ✅ JSON 형식 출력 파싱 (정규식 기반)
5. ✅ 결과 반환 (action, reason, confidence)

**완료일**: 2025-01-14

**출력 형식**:
```python
{
    "action": "BLOCK",  # "BLOCK" or "ALLOW"
    "reason": "이메일은 스팸으로 판단됩니다. 이유: ...",
    "confidence": 0.85  # 0.0~1.0
}
```

**주요 기능**:
- EXAONE 모델 로드 (bfloat16, device_map="auto")
- 프롬프트 템플릿으로 JSON 형식 요청
- 정규식 기반 JSON 파싱 (안전한 fallback)
- 에러 처리 및 기본값 제공

---

### ✅ Phase 3: 2단계 필터링 파이프라인 구현

**목표**: KoElectra와 EXAONE을 연계한 필터링 시스템 구축

**작업 내용**:
1. ✅ 파이프라인 모듈 생성 (`app/services/spam_classifier/pipeline.py`)
2. ✅ 1차 필터 (KoElectra) 실행
3. ✅ 조건부 2차 필터 (EXAONE) 실행
   - KoElectra가 스팸으로 판단하면 → EXAONE 실행
   - KoElectra가 정상으로 판단하면 → ALLOW (EXAONE 생략)
4. ✅ 결과 통합 및 반환
5. ✅ 실행 시간 측정

**완료일**: 2025-01-14

**출력 형식**:
```python
{
    "final_decision": "BLOCK",  # 최종 판정
    "stage1_koelectra": {
        "label": 1,
        "probability": 0.95,
        "confidence": "high",
        "prediction": "BLOCK"
    },
    "stage2_exaone": {
        "action": "BLOCK",
        "reason": "이메일은 스팸으로 판단됩니다...",
        "confidence": 0.85
    } or None,  # 정상 판정 시 None
    "execution_time": {
        "stage1": 0.05,  # 초
        "stage2": 2.3,   # 초 (실행 안 되면 0.0)
        "total": 2.35    # 초
    }
}
```

**주요 기능**:
- 모델 자동 로드 (필요 시)
- 조건부 EXAONE 실행 (성능 최적화)
- 에러 처리 및 fallback
- 실행 시간 측정

---

### ✅ Phase 4: 테스트 인터페이스 구축

**목표**: 로컬에서 쉽게 테스트할 수 있는 UI 제공

**완료일**: 2025-01-14

#### ✅ 옵션 1: Streamlit 웹 UI (권장)

**장점**:
- 빠른 구현
- 직관적인 인터페이스
- 실시간 결과 표시
- 설정 변경 가능 (사이드바)

**구현 내용**:
1. ✅ Streamlit 앱 생성 (`app/services/spam_classifier/test_ui.py`)
2. ✅ 입력 폼 (메일 텍스트 입력)
3. ✅ 결과 표시 (1차/2차 필터 결과)
4. ✅ 실행 시간 표시
5. ✅ 설정 패널 (임계값, EXAONE 사용 여부)
6. ✅ 예시 텍스트 버튼

**실행 방법**:
```bash
pip install streamlit
streamlit run app/services/spam_classifier/test_ui.py
```

#### ✅ 옵션 2: CLI 인터페이스

**장점**:
- 간단한 구현
- 빠른 테스트
- 스크립트 자동화 가능

**구현 내용**:
1. ✅ CLI 스크립트 생성 (`app/services/spam_classifier/test_cli.py`)
2. ✅ 명령어 인자로 텍스트 입력
3. ✅ 파일 입력 지원
4. ✅ 결과 출력 (포맷팅된 텍스트)
5. ✅ 옵션 지원 (--no-exaone, --threshold 등)

**실행 방법**:
```bash
python app/services/spam_classifier/test_cli.py "테스트 메일 내용"
```

---

## 🛠️ 구현 상세

### Phase 1: KoElectra 추론 모듈

**파일**: `app/services/spam_classifier/inference.py`

**주요 함수**:
```python
def load_trained_model(model_path: str) -> Tuple[model, tokenizer]:
    """학습된 모델 로드"""
    pass

def predict_spam(
    text: str,
    model,
    tokenizer,
    threshold: float = 0.5
) -> Dict[str, Any]:
    """
    스팸 분류 수행

    Args:
        text: 입력 텍스트
        model: 학습된 KoElectra 모델
        tokenizer: 토크나이저
        threshold: 스팸 판정 임계값

    Returns:
        {
            "label": 0 or 1,
            "probability": float,
            "confidence": "high" | "medium" | "low",
            "prediction": "ALLOW" | "BLOCK"
        }
    """
    pass
```

**구현 단계**:
1. 학습된 모델 경로 확인 (`models/spam/full/run_*/`)
2. 모델 및 토크나이저 로드
3. 텍스트 토크나이징
4. 모델 추론 (logits 계산)
5. 확률 계산 (softmax)
6. 라벨 및 신뢰도 결정

---

### Phase 2: EXAONE 추론 모듈

**파일**: `app/services/spam_classifier/exaone_inference.py` (또는 기존 파일 활용)

**주요 함수**:
```python
def load_exaone_model(model_path: str) -> Tuple[model, tokenizer]:
    """EXAONE 모델 로드"""
    pass

def analyze_with_exaone(
    text: str,
    model,
    tokenizer
) -> Dict[str, Any]:
    """
    EXAONE으로 상세 분석

    Args:
        text: 입력 텍스트
        model: EXAONE 모델
        tokenizer: 토크나이저

    Returns:
        {
            "action": "BLOCK" | "ALLOW",
            "reason": str,
            "confidence": float
        }
    """
    pass
```

**프롬프트 템플릿 예시**:
```
다음 이메일을 분석하여 스팸 여부를 판단하세요.

이메일 내용:
{text}

다음 JSON 형식으로 답변하세요:
{
    "action": "BLOCK" 또는 "ALLOW",
    "reason": "판단 근거",
    "confidence": 0.0~1.0 사이의 값
}
```

**구현 단계**:
1. EXAONE 모델 로드 (기존 코드 확인)
2. 프롬프트 생성
3. 텍스트 생성 (`model.generate()`)
4. JSON 파싱
5. 결과 반환

---

### Phase 3: 2단계 필터링 파이프라인

**파일**: `app/services/spam_classifier/pipeline.py`

**주요 함수**:
```python
def two_stage_filtering(
    text: str,
    koelectra_model,
    koelectra_tokenizer,
    exaone_model=None,
    exaone_tokenizer=None,
    use_exaone: bool = True,
    koelectra_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    2단계 필터링 수행

    Args:
        text: 입력 텍스트
        koelectra_model: KoElectra 모델
        koelectra_tokenizer: KoElectra 토크나이저
        exaone_model: EXAONE 모델 (선택적)
        exaone_tokenizer: EXAONE 토크나이저 (선택적)
        use_exaone: EXAONE 사용 여부
        koelectra_threshold: KoElectra 스팸 판정 임계값

    Returns:
        통합 결과 딕셔너리
    """
    import time

    # 1차 필터: KoElectra
    start_time = time.time()
    stage1_result = predict_spam(text, koelectra_model, koelectra_tokenizer, koelectra_threshold)
    stage1_time = time.time() - start_time

    result = {
        "final_decision": "ALLOW",  # 기본값
        "stage1_koelectra": stage1_result,
        "stage2_exaone": None,
        "execution_time": {
            "stage1": stage1_time,
            "stage2": 0.0,
            "total": stage1_time
        }
    }

    # 2차 필터: EXAONE (조건부)
    if use_exaone and exaone_model and stage1_result["label"] == 1:
        # KoElectra가 스팸으로 판단한 경우에만 EXAONE 실행
        start_time = time.time()
        stage2_result = analyze_with_exaone(text, exaone_model, exaone_tokenizer)
        stage2_time = time.time() - start_time

        result["stage2_exaone"] = stage2_result
        result["execution_time"]["stage2"] = stage2_time
        result["execution_time"]["total"] += stage2_time

        # 최종 판정 (EXAONE 결과 우선)
        result["final_decision"] = stage2_result["action"]
    else:
        # KoElectra 결과만 사용
        result["final_decision"] = "BLOCK" if stage1_result["label"] == 1 else "ALLOW"

    return result
```

**구현 단계**:
1. KoElectra 추론 실행
2. 조건 확인 (스팸 판정 여부)
3. 조건부 EXAONE 추론 실행
4. 결과 통합
5. 실행 시간 측정

---

### Phase 4: 테스트 인터페이스

#### 옵션 1: Streamlit 웹 UI (권장)

**파일**: `app/services/spam_classifier/test_ui.py`

**구현 예시**:
```python
import streamlit as st
from app.services.spam_classifier.inference import load_trained_model, predict_spam
from app.services.spam_classifier.pipeline import two_stage_filtering

st.title("🧪 스팸 필터링 테스트")

# 모델 로드
@st.cache_resource
def load_models():
    koelectra_model, koelectra_tokenizer = load_trained_model("models/spam/full/run_...")
    # EXAONE 모델은 선택적
    return koelectra_model, koelectra_tokenizer

koelectra_model, koelectra_tokenizer = load_models()

# 입력 폼
text_input = st.text_area("메일 내용을 입력하세요:", height=200)

if st.button("분석하기"):
    if text_input:
        # 2단계 필터링 실행
        result = two_stage_filtering(
            text_input,
            koelectra_model,
            koelectra_tokenizer
        )

        # 결과 표시
        st.subheader("📊 분석 결과")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("최종 판정", result["final_decision"])
        with col2:
            st.metric("총 실행 시간", f"{result['execution_time']['total']:.2f}초")

        # 1차 필터 결과
        st.subheader("1차 필터 (KoElectra)")
        st.json(result["stage1_koelectra"])

        # 2차 필터 결과
        if result["stage2_exaone"]:
            st.subheader("2차 필터 (EXAONE)")
            st.json(result["stage2_exaone"])
    else:
        st.warning("메일 내용을 입력해주세요.")
```

**실행 방법**:
```bash
streamlit run app/services/spam_classifier/test_ui.py
```

#### 옵션 2: CLI 인터페이스

**파일**: `app/services/spam_classifier/test_cli.py`

**구현 예시**:
```python
import argparse
from app.services.spam_classifier.pipeline import two_stage_filtering
from app.services.spam_classifier.inference import load_trained_model

def main():
    parser = argparse.ArgumentParser(description="스팸 필터링 테스트")
    parser.add_argument("--text", type=str, required=True, help="메일 텍스트")
    parser.add_argument("--model-path", type=str, help="학습된 모델 경로")
    parser.add_argument("--no-exaone", action="store_true", help="EXAONE 사용 안 함")

    args = parser.parse_args()

    # 모델 로드
    model, tokenizer = load_trained_model(args.model_path)

    # 2단계 필터링
    result = two_stage_filtering(
        args.text,
        model,
        tokenizer,
        use_exaone=not args.no_exaone
    )

    # 결과 출력
    print("\n" + "=" * 80)
    print("분석 결과")
    print("=" * 80)
    print(f"최종 판정: {result['final_decision']}")
    print(f"\n1차 필터 (KoElectra):")
    print(f"  - 예측: {result['stage1_koelectra']['prediction']}")
    print(f"  - 확률: {result['stage1_koelectra']['probability']:.4f}")
    print(f"  - 신뢰도: {result['stage1_koelectra']['confidence']}")
    if result['stage2_exaone']:
        print(f"\n2차 필터 (EXAONE):")
        print(f"  - 판정: {result['stage2_exaone']['action']}")
        print(f"  - 근거: {result['stage2_exaone']['reason']}")
        print(f"  - 신뢰도: {result['stage2_exaone']['confidence']:.4f}")
    print(f"\n실행 시간:")
    print(f"  - 1차: {result['execution_time']['stage1']:.3f}초")
    print(f"  - 2차: {result['execution_time']['stage2']:.3f}초")
    print(f"  - 총: {result['execution_time']['total']:.3f}초")
    print("=" * 80)

if __name__ == "__main__":
    main()
```

**실행 방법**:
```bash
python app/services/spam_classifier/test_cli.py --text "테스트 메일 내용"
```

---

## 📊 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│              2단계 필터링 시스템 아키텍처                    │
└─────────────────────────────────────────────────────────────┘

[사용자 입력]
    └─> 메일 텍스트 입력
    ↓
[인터페이스 레이어]
    ├─> Streamlit UI (옵션 1)
    └─> CLI (옵션 2)
    ↓
[파이프라인 레이어]
    └─> two_stage_filtering()
    ↓
[1차 필터: KoElectra]
    ├─> 모델 로드: 학습된 KoElectra 모델
    ├─> 추론: 텍스트 → logits → 확률
    ├─> 판정: threshold 기반 스팸/정상 분류
    └─> 출력: {label, probability, confidence, prediction}
    ↓
    ├─> [정상 판정] → ALLOW (종료)
    └─> [스팸 판정] → 2차 필터로 전달
    ↓
[2차 필터: EXAONE] (조건부)
    ├─> 모델 로드: EXAONE-2.4B 모델
    ├─> 프롬프트 생성: JSON 형식 요청
    ├─> 추론: 텍스트 생성 (model.generate())
    ├─> 파싱: JSON 추출
    └─> 출력: {action, reason, confidence}
    ↓
[결과 통합]
    ├─> 최종 판정 결정
    ├─> 실행 시간 측정
    └─> 결과 반환
    ↓
[사용자 출력]
    └─> 분석 결과 표시
```

---

## 🔧 구현 체크리스트

### ✅ Phase 1: KoElectra 추론 모듈
- [x] `app/services/spam_classifier/inference.py` 생성
- [x] `load_trained_model()` 함수 구현
- [x] `predict_spam()` 함수 구현
- [x] 확률 계산 및 신뢰도 결정 로직
- [x] 최신 모델 자동 탐지 기능
- [ ] 단위 테스트 (추가 권장)

### ✅ Phase 2: EXAONE 추론 모듈
- [x] `exaone_inference.py` 생성
- [x] `load_exaone_model()` 함수 구현
- [x] `analyze_with_exaone()` 함수 구현
- [x] 프롬프트 템플릿 구성
- [x] JSON 파싱 로직 (정규식 기반, 안전한 fallback)
- [x] 에러 처리
- [ ] 단위 테스트 (추가 권장)

### ✅ Phase 3: 2단계 필터링 파이프라인
- [x] `app/services/spam_classifier/pipeline.py` 생성
- [x] `two_stage_filtering()` 함수 구현
- [x] 조건부 EXAONE 실행 로직
- [x] 결과 통합 로직
- [x] 실행 시간 측정
- [x] 모델 자동 로드 기능
- [ ] 통합 테스트 (실제 테스트 권장)

### ✅ Phase 4: 테스트 인터페이스
- [x] Streamlit UI 구현 (옵션 1)
  - [x] `test_ui.py` 생성
  - [x] 입력 폼 구현
  - [x] 결과 표시 구현
  - [x] 설정 패널 구현
  - [x] 예시 텍스트 버튼
  - [ ] UI 테스트 (실제 실행 권장)
- [x] CLI 인터페이스 구현 (옵션 2)
  - [x] `test_cli.py` 생성
  - [x] 명령어 인자 파싱
  - [x] 결과 출력 포맷팅
  - [x] 파일 입력 지원
  - [ ] CLI 테스트 (실제 실행 권장)

---

## 🚀 빠른 시작 가이드

### ✅ 구현 완료 상태

다음 파일들이 이미 생성되어 있습니다:
- ✅ `app/services/spam_classifier/inference.py` - KoElectra 추론 모듈
- ✅ `app/services/spam_classifier/exaone_inference.py` - EXAONE 추론 모듈
- ✅ `app/services/spam_classifier/pipeline.py` - 2단계 필터링 파이프라인
- ✅ `app/services/spam_classifier/test_cli.py` - CLI 테스트 인터페이스
- ✅ `app/services/spam_classifier/test_ui.py` - Streamlit 웹 UI

### 📝 실행 방법

#### 방법 1: CLI 인터페이스 (간단한 테스트)

**Windows PowerShell 사용 시**:
```powershell
# 기본 사용
python app/services/spam_classifier/test_cli.py "테스트 메일 내용"

# EXAONE 없이 테스트 (1차 필터만)
python app/services/spam_classifier/test_cli.py "테스트 메일 내용" --no-exaone

# 파일에서 읽기
python app/services/spam_classifier/test_cli.py --file test_email.txt

# 모델 경로 지정 (PowerShell에서는 한 줄로 작성)
python app/services/spam_classifier/test_cli.py "테스트 메일" --koelectra-path models/spam/full/run_20260114_143241 --exaone-adapter-path checkpoints/exaone-spam-filter/final_model

# 여러 줄로 작성하려면 백틱(`) 사용
python app/services/spam_classifier/test_cli.py "테스트 메일" `
  --koelectra-path models/spam/full/run_20260114_143241 `
  --exaone-adapter-path checkpoints/exaone-spam-filter/final_model
```

**Linux/Mac Bash 사용 시**:
```bash
# 기본 사용
python app/services/spam_classifier/test_cli.py "테스트 메일 내용"

# 여러 줄로 작성 (백슬래시 사용)
python app/services/spam_classifier/test_cli.py "테스트 메일" \
  --koelectra-path models/spam/full/run_20260114_143241 \
  --exaone-adapter-path checkpoints/exaone-spam-filter/final_model
```

#### 방법 2: Streamlit 웹 UI (권장)

**설치**:
```bash
pip install streamlit
```

**실행**:
```bash
streamlit run app/services/spam_classifier/test_ui.py
```

브라우저에서 `http://localhost:8501`로 접속하여 사용할 수 있습니다.

#### 방법 3: Python 코드에서 직접 사용

```python
from app.services.spam_classifier.pipeline import two_stage_filtering

# 2단계 필터링 실행
result = two_stage_filtering(
    "테스트 메일 내용",
    use_exaone=True,
    koelectra_threshold=0.5
)

print(f"최종 판정: {result['final_decision']}")
print(f"1차 필터 확률: {result['stage1_koelectra']['probability']:.4f}")
if result['stage2_exaone']:
    print(f"2차 필터 근거: {result['stage2_exaone']['reason']}")
```

### 🔍 단계별 테스트 가이드

#### Step 1: KoElectra 단독 테스트

먼저 KoElectra 모델만으로 테스트하여 기본 동작을 확인합니다.

```bash
# KoElectra 추론 모듈 직접 테스트
python app/services/spam_classifier/inference.py "테스트 메일 내용"
```

**예상 출력**:
```
[정보] 모델 로드 중: models/spam/full/run_xxx
[완료] 모델 로드 완료
[완료] 토크나이저 로드 완료

================================================================================
스팸 분류 결과
================================================================================
입력 텍스트: 테스트 메일 내용...

예측: BLOCK
확률: 0.9234
신뢰도: high
================================================================================
```

#### Step 2: EXAONE 단독 테스트 (선택적)

EXAONE 모델이 정상 작동하는지 확인합니다.

```bash
# EXAONE 추론 모듈 직접 테스트
python app/services/spam_classifier/exaone_inference.py "테스트 메일 내용"
```

**주의**: EXAONE 모델 로드에 시간이 걸릴 수 있습니다.

#### Step 3: 2단계 필터링 파이프라인 테스트

전체 파이프라인을 테스트합니다.

```bash
# 파이프라인 테스트
python app/services/spam_classifier/pipeline.py "테스트 메일 내용"
```

#### Step 4: 웹 UI로 통합 테스트

가장 편리한 방법으로 다양한 시나리오를 테스트합니다.

```bash
streamlit run app/services/spam_classifier/test_ui.py
```

### 🧪 테스트 시나리오 실행

#### 시나리오 1: 명확한 스팸 메일

```bash
python app/services/spam_classifier/test_cli.py "제목: 무료 상품 받으세요! 지금 당장 클릭하세요! 한정 특가!"
```

**예상 결과**:
- 1차 필터: BLOCK (확률 > 0.9, high confidence)
- 2차 필터: BLOCK (reason: "스팸으로 판단됩니다...")
- 최종 판정: BLOCK

#### 시나리오 2: 정상 메일

```bash
python app/services/spam_classifier/test_cli.py "제목: 회의 안내\n내용: 내일 오후 2시 회의실에서 회의가 있습니다."
```

**예상 결과**:
- 1차 필터: ALLOW (확률 < 0.3, high confidence)
- 2차 필터: 실행 안 됨
- 최종 판정: ALLOW

#### 시나리오 3: 애매한 메일

```bash
python app/services/spam_classifier/test_cli.py "제목: 특별 할인 안내\n내용: 고객님을 위한 특별 할인 혜택을 드립니다."
```

**예상 결과**:
- 1차 필터: BLOCK (확률 0.5~0.7, medium confidence)
- 2차 필터: 상세 분석 수행
- 최종 판정: EXAONE 결과에 따라 결정

---

## 📝 테스트 시나리오

### 시나리오 1: 명확한 스팸 메일

**입력**:
```
제목: 무료 상품 받으세요!
내용: 지금 당장 클릭하세요! 한정 특가!
```

**예상 결과**:
- 1차 필터: BLOCK (확률 > 0.9)
- 2차 필터: BLOCK (reason: "스팸으로 판단됩니다...")

### 시나리오 2: 정상 메일

**입력**:
```
제목: 회의 안내
내용: 내일 오후 2시 회의실에서 회의가 있습니다.
```

**예상 결과**:
- 1차 필터: ALLOW (확률 < 0.3)
- 2차 필터: 실행 안 됨 (1차에서 정상 판정)

### 시나리오 3: 애매한 메일

**입력**:
```
제목: 특별 할인 안내
내용: 고객님을 위한 특별 할인 혜택을 드립니다.
```

**예상 결과**:
- 1차 필터: BLOCK (확률 0.5~0.7)
- 2차 필터: 상세 분석 수행
- 최종 판정: EXAONE 결과에 따라 결정

---

## ⚠️ 주의사항

### 1. 모델 경로 확인

**학습된 모델 경로**:
- ✅ KoElectra: `models/spam/full/run_20260114_143241/`
- ✅ EXAONE LoRA 어댑터: `checkpoints/exaone-spam-filter/final_model/`
- ✅ EXAONE 베이스 모델: `app/models/exaone-2.4b/`
- 최신 모델 자동 탐지 로직 구현 완료

### 2. EXAONE 모델 로드

**주의사항**:
- EXAONE 모델은 LoRA 어댑터로 학습됨
- 베이스 모델에 어댑터를 로드해야 함 (PEFT 사용)
- EXAONE 모델은 큰 메모리 필요
- GPU 메모리 부족 시 CPU 사용 고려
- 로드 시간이 길 수 있음 (캐싱 권장)

### 3. 성능 최적화

**최적화 포인트**:
- 모델 로드는 한 번만 수행 (캐싱)
- EXAONE은 조건부 실행 (스팸 의심 시에만)
- 배치 처리 고려 (여러 메일 동시 처리)

### 4. 에러 처리

**필수 에러 처리**:
- 모델 로드 실패
- 추론 실패
- JSON 파싱 실패 (EXAONE)
- 메모리 부족

---

## 📚 참고 자료

### 관련 문서
- `strategy/31_MODEL_MIGRATION_EXAONE_TO_KOELECTRA.md`: 모델 교체 작업
- `strategy/32_TEXT_CLASSIFIER_TRAINING_CHECKLIST.md`: 학습 체크리스트

### 코드 참고
- `app/services/spam_classifier/train.py`: 학습 코드
- `app/services/spam_classifier/load_model.py`: 모델 로드 코드
- `app/graph.py`: EXAONE 모델 로드 예시

---

## 📋 다음 단계

### 즉시 실행 가능한 작업

1. **KoElectra 단독 테스트**
   ```bash
   python app/services/spam_classifier/inference.py "테스트 메일"
   ```

2. **2단계 필터링 테스트 (CLI)**
   ```bash
   python app/services/spam_classifier/test_cli.py "테스트 메일"
   ```

3. **웹 UI 실행**
   ```bash
   pip install streamlit
   streamlit run app/services/spam_classifier/test_ui.py
   ```

### 추가 개선 사항 (선택적)

- [ ] 모델 캐싱 (한 번 로드 후 재사용)
- [ ] 배치 처리 지원 (여러 메일 동시 처리)
- [ ] 결과 저장 기능 (로그 파일)
- [ ] 성능 벤치마크 (다양한 메일 샘플로 테스트)
- [ ] 에러 복구 로직 강화

---

**작성일**: 2025-01-14
**마지막 업데이트**: 2025-01-14
**버전**: 1.0
**상태**: ✅ 구현 완료 (테스트 권장)
