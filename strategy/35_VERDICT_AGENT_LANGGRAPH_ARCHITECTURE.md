# 🏗️ Verdict Agent LangGraph 아키텍처 통합 문서

## 📋 개요

이 문서는 **LangGraph를 사용한 판정 에이전트 시스템**의 전체 아키텍처와 최근 작업 내용을 정리한 통합 전략 문서입니다.

**작성일**: 2025-01-15
**버전**: 1.0
**상태**: ✅ 구현 완료

**목적**:
- KoELECTRA 게이트웨이와 EXAONE 정밀 검사를 LangGraph로 연결
- FastAPI를 통한 RESTful API 제공
- 모듈화된 구조로 유지보수성 향상
- EXAONE을 LangChain Tool로 래핑하여 재사용성 확보

---

## 🎯 전체 시스템 아키텍처

### 시스템 구조도

```
┌─────────────────────────────────────────────────────────────────┐
│                  Verdict Agent 시스템 아키텍처                   │
└─────────────────────────────────────────────────────────────────┘

[사용자 요청]
    └─> FastAPI POST /api/mcp/filter
    ↓
[FastAPI Router Layer]
    └─> app/router/mcp_router.py
    └─> EmailFilterRequest → EmailFilterResponseState
    ↓
[LangGraph Workflow Layer]
    └─> app/services/verdict_agent/graph.py
    └─> build_verdict_agent_graph()
    ↓
    [START]
    ↓
    [1. KoELECTRA Gate Node]
    │   ├─> 모델: KoELECTRA (분류 모델)
    │   ├─> 역할: 빠른 1차 스팸 분류
    │   ├─> 출력: {spam_prob, label, confidence}
    │   └─> 실행 시간: ~0.05초
    │   ↓
    [2. Policy Router Node]
    │   ├─> 역할: 라우팅 결정
    │   ├─> spam_prob < 0.35 → 즉시 전달 (EXAONE 생략)
    │   ├─> 0.35 ≤ spam_prob ≤ 0.75 → EXAONE 호출
    │   └─> spam_prob > 0.75 → EXAONE 호출 (통지 문구 생성)
    │   ↓
    ├─> [조건부 분기]
    │   ├─> [3a. EXAONE Analyzer Node] (조건부)
    │   │   ├─> Tool: exaone_analyzer_tool
    │   │   ├─> 모델: EXAONE-2.4B (생성 모델, QLoRA)
    │   │   ├─> 역할: 위험 신호 분석 및 설명 생성
    │   │   ├─> 출력: {evidence, risk_summary, user_explanation}
    │   │   └─> 실행 시간: ~2-3초
    │   │   ↓
    │   └─> [3b. Policy Engine Node] (직접 경로)
    │       ↓
    [4. Policy Engine Node]
    │   ├─> 역할: 최종 판정 결정
    │   ├─> 입력: KoELECTRA 결과 + EXAONE 결과 (조건부)
    │   ├─> 로직: spam_prob + evidence + 시스템 룰
    │   └─> 출력: {final_action, policy_reason}
    │   ↓
    [END]
    ↓
[응답 반환]
    └─> EmailFilterResponseState
```

---

## 📁 모듈 구조 및 역할

### 1. 모델 분리 구조

#### `app/services/spam_classifier/` (KoELECTRA 전용)

**역할**: KoELECTRA 게이트웨이 관련 코드

**주요 파일**:
- `inference.py`: KoELECTRA 추론 모듈
  - `load_trained_model()`: 모델 로드
  - `predict_spam()`: 스팸 분류 수행
- `train.py`: KoELECTRA 학습 파이프라인
- `gate_graph.py`: 기존 Gate 그래프 (레거시, 참고용)

**책임**:
- 빠른 1차 스팸 분류
- 학습 및 추론 기능
- 게이트웨이 역할

#### `app/services/verdict_agent/` (EXAONE + LangGraph 통합)

**역할**: EXAONE 정밀 검사 및 LangGraph 워크플로우

**주요 파일**:
- `graph.py`: LangGraph 워크플로우 정의
  - `VerdictAgentState`: 상태 관리 (TypedDict)
  - `build_verdict_agent_graph()`: 그래프 빌드
  - `filter_email()`: 편의 함수
  - `exaone_analyzer_tool`: EXAONE Tool (LangChain Tool 래퍼)
- `exaone_inference.py`: EXAONE 추론 모듈
  - `load_exaone_model()`: 모델 로드
  - `analyze_with_exaone()`: 상세 분석 수행
- `load_model.py`: EXAONE 모델 로드 (4-bit 양자화)
- `lora_adapter.py`: EXAONE QLoRA 학습 파이프라인
- `base_model.py`: 기본 Pydantic 모델
  - `EmailFilterRequest`: 요청 모델
  - `KoElectraResult`: KoELECTRA 결과 모델
  - `ExaoneResult`: EXAONE 결과 모델
- `state_model.py`: 상태 관리 모델
  - `EmailFilterResponseState`: 응답 상태 모델

**책임**:
- EXAONE 정밀 검사
- LangGraph 워크플로우 관리
- Policy Engine 로직
- Tool 래핑 및 통합

#### `app/router/mcp_router.py` (FastAPI Router)

**역할**: FastAPI 엔드포인트 제공

**주요 엔드포인트**:
- `POST /api/mcp/filter`: 이메일 필터링
- `GET /api/mcp/health`: 헬스 체크
- `GET /api/mcp/tools/exaone`: EXAONE Tool 정보

**책임**:
- HTTP 요청/응답 처리
- LangGraph 워크플로우 호출
- 에러 처리 및 응답 변환

---

## 🔄 LangGraph 워크플로우 상세

### 노드 정의

#### 1. `koelectra_gate_node`

**역할**: 1차 게이트웨이 (빠른 스팸 분류)

**입력**: `email_text`

**처리**:
1. KoELECTRA 모델 로드 (캐싱)
2. 텍스트 토크나이징
3. 스팸 분류 수행
4. 확률 및 신뢰도 계산

**출력**:
```python
{
    "koelectra_result": {
        "spam_prob": 0.85,
        "label": "spam",
        "confidence": "high"
    },
    "execution_time": {"koelectra": 0.05}
}
```

**실행 시간**: ~0.05초

#### 2. `policy_router_node`

**역할**: 라우팅 결정 (EXAONE 호출 여부)

**입력**: `koelectra_result` (spam_prob)

**라우팅 정책**:
```python
if spam_prob < 0.35:
    → 즉시 정상 전달 (EXAONE 호출 안 함)
    → exaone_called = False
elif spam_prob <= 0.75:
    → EXAONE 호출 필요 (애매한 구간)
    → exaone_called = True
else:  # spam_prob > 0.75
    → 격리/차단, EXAONE 호출 (통지 문구 생성)
    → exaone_called = True
```

**출력**:
```python
{
    "exaone_called": True/False,
    "current_step": "policy_router"
}
```

#### 3. `exaone_analyzer_node` (조건부)

**역할**: 2차 판별기 (위험 신호 분석)

**입력**: `email_text`, `exaone_called`

**처리**:
1. `exaone_called` 확인
2. EXAONE Tool 호출 (`exaone_analyzer_tool.invoke()`)
3. 위험 신호 분석 수행
4. 결과 반환

**출력**:
```python
{
    "exaone_result": {
        "evidence": ["URL_MISMATCH", "URGENT_MONEY"],
        "risk_summary": "이메일은 스팸으로 판단됩니다...",
        "user_explanation": "이 이메일은 다음과 같은 위험 신호를 보입니다..."
    },
    "execution_time": {"exaone": 2.3}
}
```

**실행 시간**: ~2-3초

**주의사항**:
- `action` 결정 금지 (Policy Engine에서 결정)
- `evidence` 코드만 생성
- `risk_summary`와 `user_explanation` 생성

#### 4. `policy_engine_node`

**역할**: 최종 판정 결정

**입력**: `koelectra_result`, `exaone_result` (조건부)

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

**출력**:
```python
{
    "final_action": "block",
    "policy_reason": "spam_prob(0.85) > 0.75, evidence_count(2) >= 1, 차단 결정"
}
```

**최종 action 타입**:
- `deliver`: 정상 전달
- `deliver_with_warning`: 경고와 함께 전달
- `quarantine`: 격리
- `block`: 차단

### 엣지 구조

```
START
  ↓
koelectra_gate (항상 실행)
  ↓
policy_router (항상 실행)
  ↓
  ├─> [조건부 분기: should_call_exaone()]
  │   ├─> exaone_called == True → exaone_analyzer
  │   └─> exaone_called == False → policy_engine
  ↓
exaone_analyzer (조건부)
  ↓
policy_engine (항상 실행)
  ↓
END
```

### 조건부 엣지 함수

```python
def should_call_exaone(state: VerdictAgentState) -> Literal["exaone", "policy_engine"]:
    """
    EXAONE 호출 여부 결정

    Returns:
        "exaone": EXAONE 호출 필요
        "policy_engine": EXAONE 생략, 바로 Policy Engine으로
    """
    if state.get("exaone_called", False):
        return "exaone"
    else:
        return "policy_engine"
```

---

## 🛠️ EXAONE Tool 래핑

### Tool 정의

**파일**: `app/services/verdict_agent/graph.py`

**구현**:
```python
@tool
def exaone_analyzer_tool(
    email_text: str,
    adapter_path: Optional[str] = None,
    base_model_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    EXAONE 스팸 분석 도구

    이메일 텍스트를 EXAONE 모델로 분석하여 위험 신호, 위험 요약, 사용자 설명을 생성합니다.
    """
    # 모델 로드 (캐싱)
    model, tokenizer = get_exaone_model(adapter_path, base_model_path)

    # EXAONE 분석 실행
    result = analyze_with_exaone(email_text, model, tokenizer)

    return result
```

### Tool 사용 방법

#### 1. LangGraph 노드에서 사용

```python
def exaone_analyzer_node(state: VerdictAgentState) -> Dict[str, Any]:
    # Tool을 직접 호출
    exaone_result = exaone_analyzer_tool.invoke({
        "email_text": email_text,
        "adapter_path": adapter_path,
        "base_model_path": base_model_path,
    })
    return {"exaone_result": exaone_result}
```

#### 2. FastAPI에서 Tool 정보 조회

```python
@mcp_router.get("/tools/exaone")
async def get_exaone_tool_info():
    return {
        "name": exaone_analyzer_tool.name,
        "description": exaone_analyzer_tool.description,
        "args_schema": exaone_analyzer_tool.args_schema.schema(),
        "available": EXAONE_AVAILABLE,
    }
```

### Tool의 장점

1. **재사용성**: 다른 LangGraph 워크플로우에서도 사용 가능
2. **표준화**: LangChain Tool 표준 준수
3. **자동 문서화**: Tool 스키마 자동 생성
4. **에러 처리**: Tool 내부에서 에러 처리 및 기본값 반환

---

## 📊 모델 학습 상태

### EXAONE 학습 상태

**현재 상태**: Step 3000, Epoch 2.44 / 3.0 (약 81% 완료)

**체크포인트 위치**: `./checkpoints/exaone-spam-filter-v2/checkpoint-3000`

**학습 정보**:
- **데이터셋**: `app/data/spam_agent_processed_v2/`
  - 학습: 19,656 샘플
  - 검증: 2,457 샘플
- **하이퍼파라미터**:
  - LoRA r: 8
  - LoRA alpha: 16
  - 학습률: 2e-4
  - 배치 크기: 4 (효과적: 16)
  - 최대 길이: 512 tokens
- **학습 방식**: QLoRA (4-bit 양자화 + LoRA)

**최종 모델 저장 위치**: `app/models/exaone/` (학습 완료 시)

**추가 학습 방법**:
```powershell
# Epoch 4까지 추가 학습 (현재 2.44에서 4.0까지)
$env:KMP_DUPLICATE_LIB_OK="TRUE"; python app/services/spam_agent_rc/lora_adapter.py --output-dir ./checkpoints/exaone-spam-filter-v2 --resume-from-checkpoint ./checkpoints/exaone-spam-filter-v2/checkpoint-3000 --train-dataset app/data/spam_agent_processed_v2/train_dataset --val-dataset app/data/spam_agent_processed_v2/val_dataset --epochs 4 --batch-size 2 --gradient-accumulation 8 --save-steps 100
```

### KoELECTRA 학습 상태

**학습 완료**: ✅

**모델 위치**: `models/spam/full/run_*/`

**학습 정보**:
- **모델**: KoElectra-small-v3-discriminator
- **학습 방식**: Full Finetuning
- **용도**: 1차 게이트웨이 (빠른 스팸 분류)

---

## 🔌 FastAPI 통합

### 엔드포인트 구조

#### 1. 이메일 필터링 엔드포인트

**경로**: `POST /api/mcp/filter`

**요청 모델**: `EmailFilterRequest`
```python
{
    "email_text": str,
    "koelectra_model_path": Optional[str],
    "exaone_adapter_path": Optional[str],
    "exaone_base_model_path": Optional[str]
}
```

**응답 모델**: `EmailFilterResponseState`
```python
{
    "final_action": str,  # "deliver", "deliver_with_warning", "quarantine", "block"
    "policy_reason": str,
    "koelectra": {
        "spam_prob": float,
        "label": str,  # "spam" | "ham"
        "confidence": str  # "high" | "medium" | "low"
    },
    "exaone": Optional[{
        "evidence": List[str],
        "risk_summary": str,
        "user_explanation": str
    }],
    "execution_time": Dict[str, float],
    "exaone_called": bool
}
```

**사용 예시**:
```bash
curl -X POST "http://localhost:8000/api/mcp/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "email_text": "제목: 특별 할인 안내\n내용: 지금 바로 구매하세요!"
  }'
```

#### 2. EXAONE Tool 정보 엔드포인트

**경로**: `GET /api/mcp/tools/exaone`

**응답**:
```python
{
    "name": "exaone_analyzer_tool",
    "description": "EXAONE 스팸 분석 도구...",
    "args_schema": {...},
    "available": true
}
```

#### 3. 헬스 체크 엔드포인트

**경로**: `GET /api/mcp/health`

**응답**:
```python
{
    "status": "healthy",
    "koelectra_available": true,
    "exaone_available": true
}
```

---

## 📦 모델 및 데이터 구조

### Pydantic 모델 구조

#### 기본 모델 (`base_model.py`)

```python
class EmailFilterRequest(BaseModel):
    """이메일 필터링 요청 모델"""
    email_text: str
    koelectra_model_path: Optional[str]
    exaone_adapter_path: Optional[str]
    exaone_base_model_path: Optional[str]

class KoElectraResult(BaseModel):
    """KoELECTRA 결과 모델"""
    spam_prob: float
    label: str  # "spam" | "ham"
    confidence: str  # "high" | "medium" | "low"

class ExaoneResult(BaseModel):
    """EXAONE 결과 모델"""
    evidence: List[str]
    risk_summary: str
    user_explanation: str
```

#### 상태 관리 모델 (`state_model.py`)

```python
class EmailFilterResponseState(BaseModel):
    """이메일 필터링 응답 상태 모델"""
    final_action: str
    policy_reason: str
    koelectra: KoElectraResult
    exaone: Optional[ExaoneResult]
    execution_time: Dict[str, float]
    exaone_called: bool
```

### LangGraph State 구조

```python
class VerdictAgentState(TypedDict):
    """판정 에이전트 상태"""
    # 입력
    email_text: str

    # 모델 경로 (선택적)
    koelectra_model_path: Optional[str]
    exaone_adapter_path: Optional[str]
    exaone_base_model_path: Optional[str]

    # 중간 결과
    koelectra_result: Optional[Dict[str, Any]]
    exaone_result: Optional[Dict[str, Any]]

    # 최종 결과
    final_action: Optional[Literal["deliver", "deliver_with_warning", "quarantine", "block"]]
    policy_reason: Optional[str]

    # 메타데이터
    execution_time: Dict[str, float]
    exaone_called: bool
    current_step: Optional[str]
    error_message: Optional[str]
    retry_count: int
```

---

## 🔄 데이터 흐름

### 전체 데이터 흐름도

```
[1. 사용자 요청]
    {
        "email_text": "제목: 특별 할인...",
        "koelectra_model_path": null,
        "exaone_adapter_path": null,
        "exaone_base_model_path": null
    }
    ↓
[2. FastAPI Router]
    EmailFilterRequest → filter_email()
    ↓
[3. LangGraph 초기화]
    initial_state = {
        "email_text": "...",
        "koelectra_result": None,
        "exaone_result": None,
        ...
    }
    ↓
[4. KoELECTRA Gate Node]
    입력: email_text
    출력: {
        "koelectra_result": {
            "spam_prob": 0.65,
            "label": "spam",
            "confidence": "high"
        }
    }
    ↓
[5. Policy Router Node]
    입력: spam_prob = 0.65
    판단: 0.35 ≤ 0.65 ≤ 0.75 → EXAONE 호출 필요
    출력: {
        "exaone_called": True
    }
    ↓
[6. EXAONE Analyzer Node]
    입력: email_text, exaone_called = True
    처리: exaone_analyzer_tool.invoke()
    출력: {
        "exaone_result": {
            "evidence": ["URGENT_MONEY", "SUSPICIOUS_URL"],
            "risk_summary": "이메일은 스팸으로 판단됩니다...",
            "user_explanation": "이 이메일은 다음과 같은 위험 신호를 보입니다..."
        }
    }
    ↓
[7. Policy Engine Node]
    입력: spam_prob=0.65, evidence_count=2
    판단: 0.35 ≤ 0.65 ≤ 0.75, evidence_count=2 ≥ 1 → deliver_with_warning
    출력: {
        "final_action": "deliver_with_warning",
        "policy_reason": "spam_prob(0.65) 범위 내, evidence_count(2) >= 1, 경고와 함께 전달"
    }
    ↓
[8. 응답 변환]
    VerdictAgentState → EmailFilterResponseState
    ↓
[9. 사용자 응답]
    {
        "final_action": "deliver_with_warning",
        "policy_reason": "...",
        "koelectra": {...},
        "exaone": {...},
        "execution_time": {...},
        "exaone_called": true
    }
```

---

## 🎓 각 단계의 역할 및 기능

### Phase 1: KoELECTRA 게이트웨이

**목적**: 빠른 1차 스팸 분류

**기능**:
- 텍스트를 입력받아 스팸 확률 계산
- 신뢰도 자동 계산 (high/medium/low)
- 실행 시간: ~0.05초

**출력**:
- `spam_prob`: 스팸 확률 (0~1)
- `label`: "spam" 또는 "ham"
- `confidence`: "high", "medium", "low"

**역할**:
- 대부분의 정상 메일을 빠르게 필터링
- 스팸 의심 메일만 다음 단계로 전달

### Phase 2: Policy Router

**목적**: 라우팅 결정 (EXAONE 호출 여부)

**기능**:
- `spam_prob` 기반 3단계 라우팅
- 비용 효율적인 EXAONE 호출 제어

**라우팅 정책**:
1. **spam_prob < 0.35**: 즉시 정상 전달 (EXAONE 생략)
2. **0.35 ≤ spam_prob ≤ 0.75**: EXAONE 호출 (애매한 구간)
3. **spam_prob > 0.75**: EXAONE 호출 (통지 문구 생성)

**역할**:
- 성능 최적화 (불필요한 EXAONE 호출 방지)
- 비용 절감 (EXAONE은 느리고 리소스 집약적)

### Phase 3: EXAONE 정밀 검사 (조건부)

**목적**: 위험 신호 분석 및 설명 생성

**기능**:
- LangChain Tool로 래핑된 EXAONE 분석
- 위험 신호 코드 생성 (`evidence`)
- 위험 요약 및 사용자 설명 생성

**출력**:
- `evidence`: 위험 신호 코드 리스트 (예: ["URL_MISMATCH", "URGENT_MONEY"])
- `risk_summary`: 간단한 판독 요약
- `user_explanation`: 사용자에게 전달할 설명 문구

**역할**:
- 상세한 위험 분석
- 사용자 친화적인 설명 제공
- **주의**: `action` 결정 금지 (Policy Engine에서 결정)

**실행 시간**: ~2-3초

### Phase 4: Policy Engine

**목적**: 최종 판정 결정

**기능**:
- KoELECTRA 결과와 EXAONE 결과를 종합
- 시스템 룰 기반 최종 action 결정
- 판정 근거 생성

**정책 결정 로직**:
- `spam_prob` + `evidence_count` + 시스템 룰
- EXAONE의 `action` 사용 금지 (독립적 판정)

**출력**:
- `final_action`: "deliver", "deliver_with_warning", "quarantine", "block"
- `policy_reason`: 판정 근거

**역할**:
- 최종 판정 결정
- 일관된 정책 적용
- 추적 가능한 판정 근거 제공

---

## 🔧 기술 스택 및 의존성

### 핵심 라이브러리

1. **LangGraph**: 워크플로우 오케스트레이션
2. **LangChain**: Tool 래핑 및 통합
3. **FastAPI**: RESTful API 제공
4. **Pydantic**: 데이터 검증 및 모델 정의
5. **Transformers**: 모델 로드 및 추론
6. **PEFT**: LoRA 어댑터 관리

### 모델 정보

#### KoELECTRA
- **모델**: `monologg/koelectra-small-v3-discriminator`
- **타입**: SequenceClassification (분류 모델)
- **용도**: 1차 게이트웨이
- **학습 방식**: Full Finetuning
- **위치**: `models/spam/full/run_*/`

#### EXAONE
- **모델**: EXAONE-2.4B
- **타입**: CausalLM (생성 모델)
- **용도**: 2차 정밀 검사
- **학습 방식**: QLoRA (4-bit 양자화 + LoRA)
- **베이스 모델**: `app/models/original/exaone-2.4b/`
- **어댑터**: `./checkpoints/exaone-spam-filter-v2/checkpoint-3000/`
- **최종 모델**: `app/models/exaone/` (학습 완료 시)

---

## 📝 파일 구조 및 역할

### 전체 파일 구조

```
app/
├── router/
│   └── mcp_router.py              # FastAPI 라우터
│
├── services/
│   ├── spam_classifier/           # KoELECTRA 전용
│   │   ├── inference.py           # KoELECTRA 추론
│   │   ├── train.py               # KoELECTRA 학습
│   │   └── ...
│   │
│   └── verdict_agent/             # EXAONE + LangGraph 통합
│       ├── graph.py                # LangGraph 워크플로우
│       ├── exaone_inference.py     # EXAONE 추론
│       ├── load_model.py          # EXAONE 모델 로드 (4-bit)
│       ├── lora_adapter.py        # EXAONE QLoRA 학습
│       ├── base_model.py          # 기본 Pydantic 모델
│       ├── state_model.py         # 상태 관리 모델
│       └── __init__.py            # 패키지 export
│
└── models/
    ├── original/
    │   └── exaone-2.4b/           # EXAONE 베이스 모델
    └── exaone/                     # EXAONE 최종 모델 (학습 완료 시)

checkpoints/
└── exaone-spam-filter-v2/
    └── checkpoint-3000/            # EXAONE 학습 체크포인트
```

### 주요 파일 상세

#### `app/services/verdict_agent/graph.py`

**역할**: LangGraph 워크플로우 정의 및 실행

**주요 구성 요소**:
- `VerdictAgentState`: 상태 관리 (TypedDict)
- `get_koelectra_model()`: KoELECTRA 모델 캐싱
- `get_exaone_model()`: EXAONE 모델 캐싱
- `exaone_analyzer_tool`: EXAONE Tool (LangChain Tool)
- `koelectra_gate_node`: 1차 게이트웨이 노드
- `policy_router_node`: 라우팅 노드
- `exaone_analyzer_node`: 2차 판별기 노드
- `policy_engine_node`: 최종 판정 노드
- `should_call_exaone()`: 조건부 엣지 함수
- `build_verdict_agent_graph()`: 그래프 빌드
- `filter_email()`: 편의 함수

#### `app/services/verdict_agent/exaone_inference.py`

**역할**: EXAONE 추론 모듈

**주요 함수**:
- `load_exaone_model()`: EXAONE 모델 로드 (LoRA 어댑터 포함)
- `analyze_with_exaone()`: 상세 분석 수행

**출력 형식**:
```python
{
    "evidence": List[str],  # 위험 신호 코드
    "risk_summary": str,    # 위험 요약
    "user_explanation": str # 사용자 설명
}
```

**주의사항**:
- `action` 결정 금지 (Policy Engine에서 결정)
- `evidence` 코드만 생성

#### `app/services/verdict_agent/base_model.py`

**역할**: 기본 Pydantic 모델 정의

**모델**:
- `EmailFilterRequest`: 요청 모델
- `KoElectraResult`: KoELECTRA 결과 모델
- `ExaoneResult`: EXAONE 결과 모델

#### `app/services/verdict_agent/state_model.py`

**역할**: 상태 관리 모델 정의

**모델**:
- `EmailFilterResponseState`: 응답 상태 모델 (State 접미사)

#### `app/router/mcp_router.py`

**역할**: FastAPI 라우터

**엔드포인트**:
- `POST /api/mcp/filter`: 이메일 필터링
- `GET /api/mcp/health`: 헬스 체크
- `GET /api/mcp/tools/exaone`: EXAONE Tool 정보

---

## 🚀 사용 방법

### 1. FastAPI 서버 실행

```bash
# 서버 시작
uvicorn app.api_server_refactored:app --reload --port 8000
```

### 2. API 호출 예시

#### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/mcp/filter",
    json={
        "email_text": "제목: 특별 할인 안내\n내용: 지금 바로 구매하세요!"
    }
)

result = response.json()
print(f"최종 판정: {result['final_action']}")
print(f"KoELECTRA 확률: {result['koelectra']['spam_prob']}")
if result['exaone']:
    print(f"EXAONE 위험 신호: {result['exaone']['evidence']}")
```

#### cURL

```bash
curl -X POST "http://localhost:8000/api/mcp/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "email_text": "제목: 특별 할인 안내\n내용: 지금 바로 구매하세요!"
  }'
```

### 3. Python 코드에서 직접 사용

```python
from app.services.verdict_agent.graph import filter_email

# 필터링 실행
result = filter_email(
    email_text="제목: 특별 할인 안내\n내용: 지금 바로 구매하세요!",
    koelectra_model_path=None,  # 기본값 사용
    exaone_adapter_path=None,   # 기본값 사용
    exaone_base_model_path=None # 기본값 사용
)

print(f"최종 판정: {result['final_action']}")
print(f"정책 근거: {result['policy_reason']}")
```

### 4. EXAONE Tool 직접 사용

```python
from app.services.verdict_agent.graph import exaone_analyzer_tool

# Tool 직접 호출
result = exaone_analyzer_tool.invoke({
    "email_text": "테스트 메일 내용",
    "adapter_path": "./checkpoints/exaone-spam-filter-v2/checkpoint-3000",
    "base_model_path": "app/models/original/exaone-2.4b"
})

print(f"위험 신호: {result['evidence']}")
print(f"위험 요약: {result['risk_summary']}")
```

---

## 🔍 모델 캐싱 전략

### 캐싱 메커니즘

**구현 위치**: `app/services/verdict_agent/graph.py`

**전역 변수**:
```python
_koelectra_model = None
_koelectra_tokenizer = None
_exaone_model = None
_exaone_tokenizer = None
```

**캐싱 함수**:
```python
def get_koelectra_model(model_path: Optional[str] = None):
    """KoELECTRA 모델 가져오기 (캐싱)"""
    global _koelectra_model, _koelectra_tokenizer
    if _koelectra_model is None or _koelectra_tokenizer is None:
        _koelectra_model, _koelectra_tokenizer = load_trained_model(
            model_path, verbose=False
        )
    return _koelectra_model, _koelectra_tokenizer

def get_exaone_model(adapter_path: Optional[str] = None, base_model_path: Optional[str] = None):
    """EXAONE 모델 가져오기 (캐싱)"""
    global _exaone_model, _exaone_tokenizer
    if _exaone_model is None or _exaone_tokenizer is None:
        _exaone_model, _exaone_tokenizer = load_exaone_model(
            adapter_path=adapter_path,
            base_model_path=base_model_path,
            verbose=False
        )
    return _exaone_model, _exaone_tokenizer
```

**장점**:
- 첫 호출 시 모델 로드, 이후 재사용
- 메모리 효율적
- 빠른 응답 시간

**주의사항**:
- 모델 경로 변경 시 캐시 무효화 필요
- 멀티스레드 환경 고려 필요 (현재는 단일 스레드 가정)

---

## 📈 성능 최적화

### 1. 조건부 EXAONE 호출

**최적화**: Policy Router를 통한 조건부 호출

**효과**:
- 정상 메일 (spam_prob < 0.35)은 EXAONE 생략
- 약 60-70%의 EXAONE 호출 감소 예상
- 전체 응답 시간 단축

### 2. 모델 캐싱

**최적화**: 전역 변수로 모델 캐싱

**효과**:
- 첫 호출 후 모델 재사용
- 모델 로드 시간 절약 (~40초 → 0초)

### 3. 배치 처리 (향후 개선)

**예상 최적화**:
- 여러 이메일을 배치로 처리
- GPU 활용률 향상

---

## ⚠️ 주의사항 및 제한사항

### 1. EXAONE 학습 상태

**현재 상태**: Step 3000, Epoch 2.44 / 3.0 (약 81% 완료)

**권장 사항**:
- 현재 체크포인트로도 사용 가능 (약 81% 학습 완료)
- 추가 학습을 원하면 `--epochs 4` 또는 `--epochs 5`로 설정

### 2. 모델 경로

**EXAONE 어댑터 경로**:
- 기본값: `checkpoints/exaone-spam-filter/final_model`
- 현재 사용 가능: `checkpoints/exaone-spam-filter-v2/checkpoint-3000`

**EXAONE 베이스 모델 경로**:
- 기본값: `app/models/exaone-2.4b`
- 실제 위치: `app/models/original/exaone-2.4b`

### 3. GPU 메모리

**요구사항**:
- EXAONE: 최소 3GB GPU 메모리
- KoELECTRA: ~50MB GPU 메모리

**최적화**:
- EXAONE은 4-bit 양자화 사용
- 모델 캐싱으로 메모리 재사용

### 4. 실행 시간

**예상 실행 시간**:
- KoELECTRA: ~0.05초
- EXAONE: ~2-3초
- 전체 (EXAONE 호출 시): ~2.5-3초
- 전체 (EXAONE 생략 시): ~0.05초

---

## 🔄 최근 작업 내용 요약

### 1. LangGraph 통합 (2025-01-15)

**작업 내용**:
- KoELECTRA와 EXAONE을 LangGraph로 연결
- 상태 관리 기능 추가
- 조건부 엣지 구현

**파일**:
- `app/services/verdict_agent/graph.py` (신규 생성)

### 2. FastAPI 통합 (2025-01-15)

**작업 내용**:
- FastAPI 라우터 생성 (`mcp_router.py`)
- RESTful API 엔드포인트 제공
- Tool 정보 조회 엔드포인트 추가

**파일**:
- `app/router/mcp_router.py` (신규 생성)

### 3. 모델 분리 및 리팩토링 (2025-01-15)

**작업 내용**:
- EXAONE 관련 코드를 `verdict_agent`로 이동
- KoELECTRA 관련 코드는 `spam_classifier`에 유지
- Pydantic 모델 분리 (base_model, state_model)

**파일**:
- `app/services/verdict_agent/base_model.py` (신규 생성)
- `app/services/verdict_agent/state_model.py` (신규 생성)
- `app/services/verdict_agent/__init__.py` (업데이트)

### 4. EXAONE Tool 래핑 (2025-01-15)

**작업 내용**:
- EXAONE 분석 기능을 LangChain Tool로 래핑
- `@tool` 데코레이터 사용
- Tool 정보 조회 엔드포인트 추가

**파일**:
- `app/services/verdict_agent/graph.py` (업데이트)

### 5. EXAONE 학습 진행 (2025-01-15)

**작업 내용**:
- Step 3000, Epoch 2.44까지 학습 완료
- 체크포인트 저장 및 모델 경로 수정
- 추가 학습 방법 정리

**파일**:
- `app/services/spam_agent_rc/lora_adapter.py` (업데이트)
- `app/services/spam_agent_rc/load_model.py` (업데이트)

---

## 📚 학습 가이드

### 전체 시스템 이해를 위한 학습 순서

#### 1단계: 기본 개념 이해

**학습 내용**:
- LangGraph 기본 개념
- LangChain Tool 개념
- FastAPI 기본 사용법

**참고 자료**:
- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangChain Tools 문서](https://python.langchain.com/docs/modules/tools/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)

#### 2단계: 모델 구조 이해

**학습 내용**:
- KoELECTRA: 분류 모델의 역할
- EXAONE: 생성 모델의 역할
- 두 모델의 차이점과 협업 방식

**참고 파일**:
- `app/services/spam_classifier/inference.py`
- `app/services/verdict_agent/exaone_inference.py`

#### 3단계: LangGraph 워크플로우 이해

**학습 내용**:
- 노드와 엣지의 개념
- 상태 관리 (TypedDict)
- 조건부 엣지 구현

**참고 파일**:
- `app/services/verdict_agent/graph.py`

#### 4단계: Tool 래핑 이해

**학습 내용**:
- LangChain Tool의 역할
- `@tool` 데코레이터 사용법
- Tool을 노드에서 사용하는 방법

**참고 파일**:
- `app/services/verdict_agent/graph.py` (exaone_analyzer_tool)

#### 5단계: FastAPI 통합 이해

**학습 내용**:
- Pydantic 모델 정의
- FastAPI 라우터 구조
- 요청/응답 변환

**참고 파일**:
- `app/router/mcp_router.py`
- `app/services/verdict_agent/base_model.py`
- `app/services/verdict_agent/state_model.py`

#### 6단계: 전체 흐름 이해

**학습 내용**:
- 사용자 요청부터 응답까지의 전체 흐름
- 각 단계의 역할과 데이터 변환
- 에러 처리 및 예외 상황

**실습**:
- API 호출 테스트
- 각 노드의 출력 확인
- 실행 시간 측정

---

## 🎯 핵심 개념 정리

### 1. LangGraph의 역할

**목적**: 복잡한 워크플로우를 노드와 엣지로 표현

**장점**:
- 시각적 이해 용이
- 상태 관리 자동화
- 조건부 분기 구현 용이
- 재사용 가능한 노드 구성

**구성 요소**:
- **노드**: 각 단계의 처리 로직
- **엣지**: 노드 간 연결 (선형 또는 조건부)
- **State**: 노드 간 공유되는 상태 데이터

### 2. Tool 래핑의 목적

**목적**: 기능을 표준화된 인터페이스로 제공

**장점**:
- 다른 LangGraph 워크플로우에서 재사용 가능
- 자동 문서화 (스키마 생성)
- 에러 처리 표준화
- LangChain 생태계와 통합

**사용 시나리오**:
- EXAONE 분석 기능을 Tool로 래핑
- 다른 에이전트에서도 EXAONE Tool 사용 가능
- Tool 정보를 API로 제공

### 3. 모델 분리의 이유

**KoELECTRA (`spam_classifier`)**:
- 빠른 1차 분류
- 독립적으로 사용 가능
- 학습 및 추론 기능

**EXAONE (`verdict_agent`)**:
- 정밀 검사
- LangGraph와 통합
- Tool로 래핑

**장점**:
- 모듈화 및 유지보수성 향상
- 책임 분리 (Single Responsibility)
- 재사용성 향상

### 4. Policy Engine의 역할

**목적**: 최종 판정 결정

**중요 원칙**:
- EXAONE의 `action` 사용 금지
- 독립적인 정책 결정
- 추적 가능한 근거 제공

**입력**:
- KoELECTRA 결과 (spam_prob)
- EXAONE 결과 (evidence, risk_summary, user_explanation)

**출력**:
- final_action: "deliver", "deliver_with_warning", "quarantine", "block"
- policy_reason: 판정 근거

---

## 🔧 확장 가능성

### 향후 개선 방향

#### 1. 추가 에이전트 통합

**가능성**:
- 다른 분류 모델 추가
- 외부 API 통합
- 벡터 검색 통합

**구현 방법**:
- 새로운 노드 추가
- 조건부 엣지 확장
- Tool로 래핑

#### 2. 배치 처리 지원

**개선 사항**:
- 여러 이메일 동시 처리
- GPU 활용률 향상
- 처리량 증가

#### 3. 비동기 처리

**개선 사항**:
- FastAPI 비동기 처리 활용
- 동시 요청 처리
- 응답 시간 단축

#### 4. 모니터링 및 로깅

**개선 사항**:
- 실행 시간 로깅
- 에러 추적
- 성능 메트릭 수집

---

## 📋 체크리스트

### 구현 완료 항목

- [x] LangGraph 워크플로우 구현
- [x] KoELECTRA 게이트웨이 노드
- [x] Policy Router 노드
- [x] EXAONE Analyzer 노드
- [x] Policy Engine 노드
- [x] 조건부 엣지 구현
- [x] EXAONE Tool 래핑
- [x] FastAPI 통합
- [x] Pydantic 모델 분리
- [x] 모델 캐싱
- [x] 에러 처리

### 테스트 권장 항목

- [ ] 단위 테스트 (각 노드)
- [ ] 통합 테스트 (전체 워크플로우)
- [ ] 성능 테스트 (동시 요청)
- [ ] 에러 시나리오 테스트

### 문서화 완료 항목

- [x] 아키텍처 문서
- [x] API 문서 (FastAPI 자동 생성)
- [x] 코드 주석
- [x] 사용 가이드

---

## 📚 관련 문서

### 전략 문서

1. **`31_MODEL_MIGRATION_EXAONE_TO_KOELECTRA.md`**
   - EXAONE에서 KoELECTRA로 모델 교체 작업
   - 학습 파이프라인 구조 변경

2. **`32_TEXT_CLASSIFIER_TRAINING_CHECKLIST.md`**
   - 텍스트 분류 학습 체크리스트
   - KoELECTRA 학습 요구사항

3. **`33_TWO_STAGE_FILTERING_TEST_STRATEGY.md`**
   - 2단계 필터링 테스트 전략
   - 테스트 인터페이스 구축

4. **`34_GATE_BASED_FILTERING_IMPLEMENTATION.md`**
   - Gate 기반 필터링 구현
   - Policy Router 및 Policy Engine

### 코드 파일

- `app/services/verdict_agent/graph.py`: LangGraph 워크플로우
- `app/router/mcp_router.py`: FastAPI 라우터
- `app/services/verdict_agent/base_model.py`: 기본 모델
- `app/services/verdict_agent/state_model.py`: 상태 모델

---

## 🎓 학습 팁

### 1. 단계별 학습

**권장 순서**:
1. 기본 개념 이해 (LangGraph, Tool)
2. 개별 노드 이해 (각 노드의 역할)
3. 전체 흐름 이해 (데이터 흐름)
4. 실제 사용 (API 호출)

### 2. 코드 읽기 순서

**권장 순서**:
1. `base_model.py` → 데이터 구조 이해
2. `graph.py` (노드 함수들) → 각 단계의 로직 이해
3. `graph.py` (build_verdict_agent_graph) → 전체 구조 이해
4. `mcp_router.py` → API 통합 이해

### 3. 디버깅 방법

**추천 방법**:
1. 각 노드의 출력 확인
2. `current_step` 필드로 진행 상황 추적
3. `execution_time`으로 성능 분석
4. `error_message`로 에러 추적

---

## 📝 요약

### 핵심 아키텍처

**시스템 구조**:
- LangGraph 기반 워크플로우
- KoELECTRA 게이트웨이 (1차 필터)
- EXAONE 정밀 검사 (2차 필터, 조건부)
- Policy Engine (최종 판정)

**모듈 구조**:
- `spam_classifier`: KoELECTRA 전용
- `verdict_agent`: EXAONE + LangGraph 통합
- `router`: FastAPI 엔드포인트

**주요 기능**:
- 조건부 EXAONE 호출 (성능 최적화)
- EXAONE Tool 래핑 (재사용성)
- 모델 캐싱 (응답 시간 단축)
- 상태 관리 (추적 가능성)

### 현재 상태

**EXAONE 학습**: Step 3000, Epoch 2.44 / 3.0 (약 81% 완료)
**KoELECTRA 학습**: ✅ 완료
**LangGraph 통합**: ✅ 완료
**FastAPI 통합**: ✅ 완료
**Tool 래핑**: ✅ 완료

---

**작성일**: 2025-01-15
**마지막 업데이트**: 2025-01-15
**버전**: 1.0
**상태**: ✅ 구현 완료
