# 🚪 Gate 기반 스팸 필터링 시스템 구현 완료

## 📋 구현 완료 요약

요구사항에 맞춰 Gate 기반 스팸 필터링 시스템을 LangGraph로 구현했습니다.

---

## ✅ 완료된 작업

### 1. KoELECTRA 출력 스키마 수정 ✅

**파일**: `app/services/spam_classifier/inference.py`

**변경 사항**:
- `probability` → `spam_prob` 변경
- `label: 0|1` → `label: "spam"|"ham"` 변경
- `prediction` 필드 제거

**출력 형식**:
```python
{
    "spam_prob": float,  # 0~1
    "label": "spam" | "ham",
    "confidence": "low" | "medium" | "high"
}
```

**재학습 필요**: ❌ 불필요 (후처리만 변경)

---

### 2. EXAONE 출력 스키마 수정 ✅

**파일**: `app/services/spam_classifier/exaone_inference.py`

**변경 사항**:
- `action` 필드 제거 (정책 결정 금지)
- `reason` → `risk_summary` + `user_explanation` 분리
- `evidence` 배열 추가
- `confidence` 필드 제거

**출력 형식**:
```python
{
    "evidence": List[str],  # ["URL_MISMATCH", "URGENT_MONEY", ...]
    "risk_summary": str,  # 간단한 판독 요약
    "user_explanation": str  # 사용자에게 전달할 설명 문구
}
```

**프롬프트 변경**:
- "판정" 지시 제거
- `evidence` 코드 리스트 제공
- `action` 필드 사용 금지 명시

**재학습 필요**: ⚠️ 프롬프트 엔지니어링으로 시도 가능, 실패 시 재학습 필요

---

### 3. Policy Router 구현 ✅

**파일**: `app/services/spam_classifier/gate_graph.py`

**구현 내용**:
- `spam_prob` 기반 3단계 라우팅
- 임계값: 0.35, 0.75

**라우팅 정책**:
```python
if spam_prob < 0.35:
    → 즉시 정상 전달 (EXAONE 호출 금지)
elif spam_prob <= 0.75:
    → EXAONE 호출 (애매한 구간)
else:  # spam_prob > 0.75
    → 격리/차단, EXAONE 호출 (통지 문구 생성)
```

---

### 4. LangGraph 기반 재구성 ✅

**파일**: `app/services/spam_classifier/gate_graph.py`

**노드 구조**:
1. **koelectra_gate**: 1차 Gate (KoELECTRA 실행)
2. **policy_router**: Policy Router (라우팅 결정)
3. **exaone_analyzer**: 2차 판별기 (EXAONE 실행, 조건부)
4. **policy_engine**: Policy Engine (최종 action 결정)

**엣지 구조**:
```
START → koelectra_gate → policy_router → [exaone_analyzer | policy_engine] → policy_engine → END
```

**조건부 엣지**:
- `policy_router` → `should_call_exaone()` → `exaone_analyzer` 또는 `policy_engine`

---

### 5. Policy Engine 구현 ✅

**파일**: `app/services/spam_classifier/gate_graph.py`

**구현 내용**:
- `spam_prob` + `evidence` + 시스템 룰 기반 결정
- EXAONE의 `action` 사용 금지

**정책 결정 로직**:
```python
if spam_prob < 0.35:
    if evidence:
        → deliver_with_warning
    else:
        → deliver
elif spam_prob <= 0.75:
    if evidence_count >= 3:
        → quarantine
    elif evidence_count >= 1:
        → deliver_with_warning
    else:
        → deliver
else:  # spam_prob > 0.75
    if evidence:
        → block
    else:
        → quarantine (재학습 큐 전송)
```

**최종 action 타입**:
- `deliver`: 정상 전달
- `deliver_with_warning`: 경고와 함께 전달
- `quarantine`: 격리
- `block`: 차단

---

### 6. EXAONE 프롬프트 수정 ✅

**파일**: `app/services/spam_classifier/exaone_inference.py`

**변경 사항**:
- "판정" 지시 제거
- `evidence` 코드 리스트 제공
- `action` 필드 사용 금지 명시
- Few-shot 예시 포함

**새로운 프롬프트**:
```
당신은 이메일 스팸 분석 전문가입니다.
이메일을 분석하여 위험 신호(evidence), 위험 요약(risk_summary),
사용자 설명(user_explanation)만 제공하세요.
차단/전달 여부(action)는 결정하지 마세요.
```

---

## 📁 생성/수정된 파일

### 새로 생성된 파일
1. **`app/services/spam_classifier/gate_graph.py`**
   - LangGraph 기반 Gate 시스템
   - 노드/엣지 구조
   - Policy Router 및 Policy Engine

2. **`app/services/spam_classifier/test_gate_cli.py`**
   - Gate 시스템 전용 CLI 테스트 인터페이스

### 수정된 파일
1. **`app/services/spam_classifier/inference.py`**
   - KoELECTRA 출력 스키마 변경

2. **`app/services/spam_classifier/exaone_inference.py`**
   - EXAONE 출력 스키마 변경
   - 프롬프트 수정
   - 파싱 로직 수정

3. **`app/services/spam_classifier/pipeline.py`**
   - Policy Router 로직 추가 (하위 호환성 유지)
   - 출력 형식 업데이트

4. **`app/services/spam_classifier/test_cli.py`**
   - 출력 형식 업데이트 (하위 호환성 유지)

---

## 🎯 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│              Gate 기반 스팸 필터링 시스템                    │
└─────────────────────────────────────────────────────────────┘

[사용자 입력]
    └─> 이메일 텍스트
    ↓
[LangGraph START]
    ↓
[1차 Gate: KoELECTRA]
    ├─> 입력: 이메일 텍스트
    ├─> 출력: {spam_prob, label, confidence}
    └─> 실행 시간: ~0.05초
    ↓
[Policy Router]
    ├─> spam_prob < 0.35 → deliver (EXAONE 호출 안 함)
    ├─> 0.35 ≤ spam_prob ≤ 0.75 → EXAONE 호출
    └─> spam_prob > 0.75 → quarantine/block (EXAONE 호출)
    ↓
    ├─> [EXAONE 호출 안 함] → Policy Engine
    └─> [EXAONE 호출] → EXAONE Analyzer
    ↓
[2차 판별기: EXAONE] (조건부)
    ├─> 입력: 이메일 텍스트
    ├─> 출력: {evidence, risk_summary, user_explanation}
    ├─> 주의: action 결정 금지
    └─> 실행 시간: ~2-3초
    ↓
[Policy Engine]
    ├─> 입력: spam_prob + evidence + 시스템 룰
    ├─> 출력: final_action + policy_reason
    └─> 최종 action 결정
    ↓
[LangGraph END]
    └─> 결과 반환
```

---

## 🚀 사용 방법

### 방법 1: LangGraph 기반 Gate 시스템 (권장)

```powershell
# 기본 사용
python app/services/spam_classifier/test_gate_cli.py "테스트 메일 내용"

# 인터랙티브 모드
python app/services/spam_classifier/test_gate_cli.py

# 디버그 모드
python app/services/spam_classifier/test_gate_cli.py "테스트 메일" --debug-exaone
```

### 방법 2: 기존 파이프라인 (하위 호환)

```powershell
python app/services/spam_classifier/test_cli.py "테스트 메일 내용"
```

---

## 📊 출력 예시

### Gate 시스템 출력

```
================================================================================
필터링 결과
================================================================================

✅ 전달 (최종 판정: deliver)
정책 근거: spam_prob(0.250) < 0.35, 정상 전달

[1차 Gate: KoELECTRA]
  라벨: ham
  스팸 확률: 0.2500 (25.00%)
  신뢰도: high
  실행 시간: 0.233초

[Policy Router]
  라우팅: spam_prob(0.250) < 0.35 → 즉시 전달 (EXAONE 호출 안 함)

[2차 판별기: EXAONE]
  실행 안 됨 (Policy Router 결정)

총 실행 시간: 0.233초
================================================================================
```

---

## ⚠️ 주의사항

### 1. EXAONE 재학습 필요 여부

**현재 상태**:
- 프롬프트 엔지니어링으로 시도 가능
- 학습 데이터는 `action/reason/confidence` 형식
- 새로운 형식(`evidence/risk_summary/user_explanation`)으로 생성 가능 여부 불확실

**권장 사항**:
1. 프롬프트 엔지니어링으로 먼저 테스트
2. 품질이 낮으면 재학습 데이터 준비

### 2. 모델 캐싱

**현재 구현**:
- 전역 변수로 모델 캐싱 (`_koelectra_model`, `_exaone_model`)
- 첫 호출 시 로드, 이후 재사용

**개선 필요**:
- 멀티스레드 환경 고려
- 모델 경로 변경 시 캐시 무효화

### 3. 하위 호환성

**기존 코드**:
- `pipeline.py`는 기존 형식 유지 (하위 호환)
- `test_cli.py`는 두 형식 모두 지원

**권장 사항**:
- 새로운 프로젝트는 `gate_graph.py` 사용
- 기존 코드는 점진적 마이그레이션

---

## 🔍 검증 체크리스트

- [x] KoELECTRA 출력: `spam_prob`, `label: "spam"|"ham"`
- [x] EXAONE 출력: `evidence`, `risk_summary`, `user_explanation` (action 제거)
- [x] Policy Router: spam_prob 기반 3단계 라우팅 (0.35, 0.75)
- [x] LangGraph: 노드/엣지 구조
- [x] Policy Engine: 최종 action 결정 (EXAONE의 action 사용 안 함)
- [x] EXAONE 프롬프트: evidence만 생성, action 금지

---

## 📝 다음 단계

### 즉시 테스트 가능

1. **Gate 시스템 테스트**
   ```powershell
   python app/services/spam_classifier/test_gate_cli.py "교수님 급해요!"
   ```

2. **EXAONE 출력 형식 확인**
   - 디버그 모드로 실제 응답 확인
   - `evidence` 배열 생성 여부 확인

### 필요 시 작업

1. **EXAONE 재학습 데이터 준비** (프롬프트 엔지니어링 실패 시)
   - `evidence` 코드 정의
   - 학습 데이터 변환 스크립트 작성

2. **모델 캐싱 개선**
   - Thread-safe 캐싱
   - 캐시 무효화 로직

3. **성능 최적화**
   - 배치 처리 지원
   - 비동기 처리

---

**작성일**: 2025-01-14
**버전**: 1.0
**상태**: ✅ 구현 완료
