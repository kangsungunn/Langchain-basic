# DDD 기반 MCP 자동화 에이전트 재구성 전략

## 📋 목차

1. [현재 상황 분석](#현재-상황-분석)
2. [DDD 아키텍처 설계](#ddd-아키텍처-설계)
3. [폴더별 역할 정의](#폴더별-역할-정의)
4. [스타 토폴로지 구현 전략](#스타-토폴로지-구현-전략)
5. [코드 통합 및 정리 전략](#코드-통합-및-정리-전략)
6. [마이그레이션 로드맵](#마이그레이션-로드맵)

---

## 현재 상황 분석

### 📂 기존 폴더 구조

```
langchain/
├── app/                    # EC2 배포 대상 (실행 환경)
│   ├── domain/            # 도메인 구조 (이미 생성됨)
│   │   ├── spam_filter/
│   │   ├── chat/
│   │   ├── training/
│   │   └── shared/
│   ├── api/               # API 엔드포인트
│   └── main.py           # FastAPI 서버
│
├── training/              # 모델 훈련 영역
│   └── services/         # 기존 코드 (정리 필요)
│       ├── spam_classifier/
│       ├── verdict_agent/
│       ├── spam_agent_rc/
│       ├── gateway/
│       ├── hub/
│       └── branches/
│
└── artifacts/            # S3 배포 대상 (모델 저장소)
    └── models/
        ├── base/         # 기본 모델 (KoELECTRA, EXAONE)
        └── trained/      # 훈련된    어댑터/체크포인트
            ├── koelectra/
            └── exaone/
```

### 🎯 핵심 요구사항

1. **스타 토폴로지 유지**
   - Gateway: KoELECTRA (1차 필터링)
   - Star Node: EXAONE (중앙 의사결정)
   - LangGraph 오케스트레이션

2. **DDD 레이어 분리**
   - Domain: 비즈니스 로직
   - Application: 유즈케이스 + 오케스트레이션
   - Infrastructure: 모델, DB, 외부 서비스
   - Interface: API, 이벤트 핸들러

3. **배포 구조 명확화**
   - `training/`: 모델 훈련 (개발자용)
   - `artifacts/`: 모델 저장소 (S3 배포)
   - `app/`: 실행 환경 (EC2 배포)

---

## DDD 아키텍처 설계

### 🏗️ DDD 레이어 구조

```
┌─────────────────────────────────────────────────────────────┐
│ Interface Layer (인터페이스 레이어)                           │
│ - FastAPI 엔드포인트                                          │
│ - 이벤트 핸들러                                                │
│ - CLI 인터페이스                                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Application Layer (애플리케이션 레이어)                        │
│ - 유즈케이스 (Use Cases)                                      │
│ - LangGraph 오케스트레이션                                    │
│ - 워크플로우 조정                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Domain Layer (도메인 레이어)                                  │
│ - 비즈니스 로직                                                │
│ - 도메인 모델                                                  │
│ - 도메인 서비스                                                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Infrastructure Layer (인프라 레이어)                          │
│ - 모델 로딩/추론 (KoELECTRA, EXAONE)                         │
│ - DB 접근 (PostgreSQL + PGVector)                           │
│ - 외부 API                                                    │
└─────────────────────────────────────────────────────────────┘
```

### 📦 app/ 폴더의 DDD 매핑

```
app/
├── interface/              # Interface Layer (새로 생성)
│   ├── api/               # REST API
│   │   ├── v1/
│   │   │   ├── spam_filter/
│   │   │   ├── chat/
│   │   │   └── training/
│   │   └── dependencies.py
│   ├── cli/               # CLI 인터페이스
│   └── events/            # 이벤트 핸들러
│
├── application/            # Application Layer (새로 생성)
│   ├── use_cases/         # 유즈케이스
│   │   ├── spam_filter/
│   │   │   ├── filter_email_use_case.py
│   │   │   └── analyze_spam_use_case.py
│   │   ├── chat/
│   │   │   ├── chat_use_case.py
│   │   │   └── rag_query_use_case.py
│   │   └── training/
│   │       └── train_adapter_use_case.py
│   │
│   ├── orchestrators/     # LangGraph 오케스트레이션
│   │   ├── star_topology/
│   │   │   ├── graph.py
│   │   │   ├── nodes.py
│   │   │   └── state.py
│   │   ├── spam_filter/
│   │   │   └── spam_filter_graph.py
│   │   └── chat/
│   │       └── chat_graph.py
│   │
│   └── dto/               # Data Transfer Objects
│       ├── spam_filter/
│       ├── chat/
│       └── training/
│
├── domain/                 # Domain Layer (기존 유지 + 정리)
│   ├── spam_filter/
│   │   ├── entities/      # 엔티티 (순수 비즈니스 객체)
│   │   ├── value_objects/ # 값 객체
│   │   ├── services/      # 도메인 서비스
│   │   ├── repositories/  # 리포지토리 인터페이스
│   │   └── events/        # 도메인 이벤트
│   │
│   ├── chat/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── services/
│   │   └── repositories/
│   │
│   ├── training/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── services/
│   │
│   └── shared/
│       ├── entities/
│       ├── value_objects/
│       └── services/
│
├── infrastructure/         # Infrastructure Layer (새로 생성)
│   ├── models/            # ML 모델 (KoELECTRA, EXAONE)
│   │   ├── koelectra/
│   │   │   ├── loader.py
│   │   │   ├── inference.py
│   │   │   └── training.py
│   │   └── exaone/
│   │       ├── loader.py
│   │       ├── inference.py
│   │       └── adapter_manager.py
│   │
│   ├── persistence/       # 데이터 영속성
│   │   ├── database/
│   │   │   ├── models.py
│   │   │   ├── connection.py
│   │   │   └── crud.py
│   │   └── repositories/ # 리포지토리 구현
│   │       ├── spam_filter_repository.py
│   │       ├── chat_repository.py
│   │       └── training_repository.py
│   │
│   ├── external/          # 외부 서비스
│   │   ├── s3_client.py
│   │   └── embedding_client.py
│   │
│   └── config/            # 설정 관리
│       ├── settings.py
│       └── model_config.py
│
├── main.py                # FastAPI 애플리케이션
└── graph.py               # 레거시 (제거 예정)
```

---

## 폴더별 역할 정의

### 🎯 1. `training/` - 모델 훈련 전용 영역

**목적**: 모델 훈련, 파인튜닝, 실험

**구조**:
```
training/
├── koelectra/            # KoELECTRA 훈련
│   ├── train.py         # 훈련 스크립트
│   ├── dataset.py       # 데이터셋 로더
│   ├── config.yaml      # 훈련 설정
│   └── evaluate.py      # 평가 스크립트
│
├── exaone/              # EXAONE 훈련
│   ├── train_lora.py    # LoRA 파인튜닝
│   ├── dataset.py       # 데이터셋 로더
│   ├── config.yaml      # 훈련 설정
│   └── merge_adapter.py # 어댑터 병합
│
├── shared/              # 공통 훈련 유틸
│   ├── data_processing/
│   ├── metrics/
│   └── callbacks/
│
└── README.md            # 훈련 가이드
```

**역할**:
1. **데이터 전처리**: `app/data/` → 훈련 데이터셋 생성
2. **모델 훈련**: 기본 모델 로드 → 파인튜닝 → 어댑터 저장
3. **결과 저장**: 훈련된 모델 → `artifacts/models/trained/`
4. **독립 실행**: `training/` 폴더만으로 훈련 가능

**흐름**:
```
app/data/*.jsonl  →  training/*/dataset.py  →  훈련 실행  →  artifacts/models/trained/
```

---

### 🗂️ 2. `artifacts/` - 모델 저장소 (S3 배포 대상)

**목적**: 모델 파일 중앙 저장소

**구조**:
```
artifacts/
├── models/
│   ├── base/                    # 기본 모델 (불변)
│   │   ├── koelectra-small-v3-discriminator/
│   │   │   ├── config.json
│   │   │   ├── vocab.txt
│   │   │   └── pytorch_model.bin
│   │   └── exaone-2.4b/
│   │       ├── config.json
│   │       └── pytorch_model.bin
│   │
│   └── trained/                 # 훈련된 모델 (버전 관리)
│       ├── koelectra/
│       │   └── spam_classifier/
│       │       └── full/
│       │           └── run_20260114_143241/  # 타임스탬프 버전
│       │               ├── config.json
│       │               ├── pytorch_model.bin
│       │               └── metrics.json
│       │
│       └── exaone/
│           └── adapter/
│               └── checkpoint-3000/          # 체크포인트 버전
│                   ├── adapter_config.json
│                   ├── adapter_model.bin
│                   └── training_config.json
│
└── README.md                    # 모델 버전 관리 가이드
```

**역할**:
1. **모델 버전 관리**: 타임스탬프/체크포인트 기반
2. **S3 동기화**: `aws s3 sync artifacts/ s3://your-bucket/artifacts/`
3. **EC2 다운로드**: 배포 시 S3에서 다운로드
4. **불변성**: 훈련 완료 후 수정 금지

**S3 배포 스크립트** (`scripts/sync_artifacts.sh`):
```bash
#!/bin/bash
# artifacts를 S3에 업로드
aws s3 sync artifacts/models/ s3://mcp-agent-models/models/ \
  --exclude "*.pyc" \
  --exclude "__pycache__/*"

echo "✅ Models synced to S3"
```

---

### 🚀 3. `app/` - 실행 환경 (EC2 배포 대상)

**목적**: 프로덕션 실행 환경

**역할**:
1. **모델 로딩**: `artifacts/models/` 또는 S3에서 로드
2. **API 제공**: FastAPI 서버
3. **LangGraph 실행**: 스타 토폴로지 워크플로우
4. **DB 연동**: PostgreSQL + PGVector

**배포 흐름**:
```
1. EC2 인스턴스 시작
2. S3에서 artifacts 다운로드:
   aws s3 sync s3://mcp-agent-models/models/ /opt/app/artifacts/models/
3. FastAPI 서버 시작:
   uvicorn app.main:app --host 0.0.0.0 --port 8000
4. 모델 로딩 (지연 로딩):
   첫 요청 시 artifacts/models/에서 모델 로드
```

**환경 변수** (`.env`):
```bash
# 모델 경로 설정
KOELECTRA_MODEL_PATH=artifacts/models/base/koelectra-small-v3-discriminator
KOELECTRA_TRAINED_PATH=artifacts/models/trained/koelectra/spam_classifier/full/run_20260114_143241

EXAONE_MODEL_PATH=artifacts/models/base/exaone-2.4b
EXAONE_ADAPTER_PATH=artifacts/models/trained/exaone/adapter/checkpoint-3000

# S3 설정 (옵션)
MODEL_STORAGE=s3  # 또는 local
S3_BUCKET=mcp-agent-models
```

---

## 스타 토폴로지 구현 전략

### 🌟 아키텍처 레이어 매핑

```
┌─────────────────────────────────────────────────────────────┐
│ Interface Layer (app/interface/)                            │
│ POST /api/v1/spam-filter/filter                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Application Layer (app/application/)                        │
│ - Use Case: FilterEmailUseCase                             │
│ - Orchestrator: StarTopologyGraph (LangGraph)              │
│   ├─ gateway_node ───────────────────────┐                 │
│   ├─ hub_router_node                     │                 │
│   ├─ branch_node                         │                 │
│   ├─ policy_decision_node                │                 │
│   └─ db_save_node                        │                 │
└──────────────────────────────────────────┼─────────────────┘
                          ↓                │
┌─────────────────────────────────────────┼─────────────────┐
│ Domain Layer (app/domain/)              │                 │
│ - SpamFilterService                     │                 │
│ - GatewayService ◄──────────────────────┘                 │
│ - HubRouterService                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Infrastructure Layer (app/infrastructure/)                  │
│ - KoELECTRA Model (Gateway) ◄── artifacts/models/base/     │
│ - EXAONE Model (Star) ◄──────── artifacts/models/trained/  │
│ - PostgreSQL (DB)                                           │
└─────────────────────────────────────────────────────────────┘
```

### 🔄 스타 토폴로지 흐름

**1차 Gateway (KoELECTRA) - Infrastructure Layer**

위치: `app/infrastructure/models/koelectra/`

```python
# app/infrastructure/models/koelectra/inference.py
class KoELECTRAInference:
    """
    1차 Gateway: KoELECTRA 기반 스팸 분류

    역할: 빠른 1차 필터링 (규칙 기반 + ML 보조)
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None

    def load_model(self):
        """artifacts/models/에서 KoELECTRA 로드"""
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_path
        )
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)

    def predict(self, text: str) -> dict:
        """
        스팸 확률 예측

        Returns:
            {
                "is_spam": bool,
                "spam_prob": float,
                "confidence": float,
                "route": str  # "spam_agent" | "normal" | "exaone_review"
            }
        """
        # KoELECTRA 추론
        inputs = self.tokenizer(text, return_tensors="pt")
        outputs = self.model(**inputs)
        spam_prob = outputs.logits.softmax(dim=1)[0][1].item()

        # 라우팅 결정
        if spam_prob > 0.8:
            route = "spam_agent"  # 확실한 스팸 → 브랜치로
        elif spam_prob < 0.2:
            route = "normal"  # 확실한 정상 → 통과
        else:
            route = "exaone_review"  # 모호함 → EXAONE 검토

        return {
            "is_spam": spam_prob > 0.5,
            "spam_prob": spam_prob,
            "confidence": max(spam_prob, 1 - spam_prob),
            "route": route
        }
```

**중앙 Star Node (EXAONE) - Infrastructure Layer**

위치: `app/infrastructure/models/exaone/`

```python
# app/infrastructure/models/exaone/inference.py
class EXAONEInference:
    """
    중앙 Star Node: EXAONE 기반 의사결정

    역할:
    - 모호한 케이스 최종 판단
    - 브랜치 결과 검토
    - 정책 기반 최종 결정
    """

    def __init__(self, base_model_path: str, adapter_path: str = None):
        self.base_model_path = base_model_path
        self.adapter_path = adapter_path
        self.model = None
        self.tokenizer = None

    def load_model_with_adapter(self):
        """
        EXAONE 베이스 + LoRA 어댑터 로드

        artifacts/models/base/exaone-2.4b +
        artifacts/models/trained/exaone/adapter/checkpoint-3000
        """
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        # 베이스 모델 로드
        self.model = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            torch_dtype="bfloat16",
            device_map="auto",
            trust_remote_code=True
        )

        # LoRA 어댑터 로드 (옵션)
        if self.adapter_path:
            self.model = PeftModel.from_pretrained(
                self.model,
                self.adapter_path
            )

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_path,
            trust_remote_code=True
        )

    def analyze(
        self,
        text: str,
        gateway_result: dict,
        context: dict = None
    ) -> dict:
        """
        최종 분석 및 의사결정

        Args:
            text: 원본 텍스트
            gateway_result: KoELECTRA 결과
            context: 추가 컨텍스트

        Returns:
            {
                "final_decision": str,  # "block" | "deliver" | "quarantine"
                "reason": str,
                "evidence": List[str],
                "confidence": float
            }
        """
        # EXAONE 프롬프트 생성
        prompt = self._build_prompt(text, gateway_result, context)

        # EXAONE 추론
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            do_sample=True
        )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 응답 파싱
        return self._parse_response(response, gateway_result)

    def _build_prompt(self, text: str, gateway_result: dict, context: dict) -> str:
        """EXAONE 프롬프트 생성"""
        return f"""[[system]]
당신은 이메일 보안 전문가입니다. 다음 이메일이 스팸인지 최종 판단하세요.

1차 필터(KoELECTRA) 결과:
- 스팸 확률: {gateway_result['spam_prob']:.2f}
- 신뢰도: {gateway_result['confidence']:.2f}
- 라우팅: {gateway_result['route']}

이메일 내용:
{text}

다음 형식으로 답변하세요:
결정: [block/deliver/quarantine]
이유: [1-2문장 설명]
증거: [핵심 증거 나열]
[[endofturn]]

[[assistant]]
"""
```

**LangGraph 오케스트레이션 - Application Layer**

위치: `app/application/orchestrators/star_topology/`

```python
# app/application/orchestrators/star_topology/graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict

class StarTopologyState(TypedDict):
    """스타 토폴로지 상태"""
    text: str
    gateway_result: dict
    exaone_result: dict
    final_decision: dict

def gateway_node(state: StarTopologyState) -> dict:
    """1차 Gateway 노드 (KoELECTRA)"""
    from app.infrastructure.models.koelectra.inference import KoELECTRAInference

    # KoELECTRA 추론
    koelectra = get_koelectra_model()  # 싱글톤
    result = koelectra.predict(state["text"])

    return {"gateway_result": result}

def exaone_node(state: StarTopologyState) -> dict:
    """중앙 Star Node (EXAONE)"""
    from app.infrastructure.models.exaone.inference import EXAONEInference

    # EXAONE 추론
    exaone = get_exaone_model()  # 싱글톤
    result = exaone.analyze(
        text=state["text"],
        gateway_result=state["gateway_result"]
    )

    return {"exaone_result": result}

def decision_node(state: StarTopologyState) -> dict:
    """최종 의사결정 노드"""
    gateway = state["gateway_result"]
    exaone = state.get("exaone_result")

    # 라우팅 결정에 따라 최종 판단
    if gateway["route"] == "normal":
        # 확실한 정상 → 통과
        final_decision = {
            "action": "deliver",
            "reason": "1차 필터 통과 (정상)",
            "confidence": gateway["confidence"]
        }
    elif gateway["route"] == "spam_agent":
        # 확실한 스팸 → 차단
        final_decision = {
            "action": "block",
            "reason": "1차 필터 차단 (스팸)",
            "confidence": gateway["confidence"]
        }
    else:
        # 모호함 → EXAONE 결과 사용
        final_decision = exaone

    return {"final_decision": final_decision}

def build_star_topology_graph():
    """스타 토폴로지 그래프 빌드"""
    graph = StateGraph(StarTopologyState)

    # 노드 추가
    graph.add_node("gateway", gateway_node)
    graph.add_node("exaone", exaone_node)
    graph.add_node("decision", decision_node)

    # 엣지 정의
    graph.set_entry_point("gateway")

    # 조건부 엣지: gateway 결과에 따라 분기
    graph.add_conditional_edges(
        "gateway",
        lambda state: "exaone" if state["gateway_result"]["route"] == "exaone_review" else "decision",
        {
            "exaone": "exaone",
            "decision": "decision"
        }
    )

    graph.add_edge("exaone", "decision")
    graph.add_edge("decision", END)

    return graph.compile()
```

**Use Case - Application Layer**

위치: `app/application/use_cases/spam_filter/`

```python
# app/application/use_cases/spam_filter/filter_email_use_case.py
from app.application.orchestrators.star_topology.graph import build_star_topology_graph

class FilterEmailUseCase:
    """
    이메일 필터링 유즈케이스

    스타 토폴로지 실행:
    1. KoELECTRA Gateway (1차 필터)
    2. EXAONE Star Node (최종 판단)
    3. 결과 반환 + DB 저장
    """

    def __init__(self):
        self.graph = build_star_topology_graph()

    def execute(self, email_text: str) -> dict:
        """
        이메일 필터링 실행

        Args:
            email_text: 이메일 본문

        Returns:
            {
                "action": "deliver" | "block" | "quarantine",
                "reason": str,
                "confidence": float,
                "gateway_result": dict,
                "exaone_result": dict (옵션)
            }
        """
        # 1. LangGraph 실행
        initial_state = {
            "text": email_text,
            "gateway_result": None,
            "exaone_result": None,
            "final_decision": None
        }

        result = self.graph.invoke(initial_state)

        # 2. DB 저장 (선택적)
        # self._save_to_db(result)

        return {
            "action": result["final_decision"]["action"],
            "reason": result["final_decision"]["reason"],
            "confidence": result["final_decision"]["confidence"],
            "gateway_result": result["gateway_result"],
            "exaone_result": result.get("exaone_result")
        }
```

**API 엔드포인트 - Interface Layer**

위치: `app/interface/api/v1/spam_filter/`

```python
# app/interface/api/v1/spam_filter/filter_router.py
from fastapi import APIRouter
from app.application.use_cases.spam_filter.filter_email_use_case import FilterEmailUseCase

router = APIRouter(prefix="/spam-filter", tags=["spam-filter"])

@router.post("/filter")
async def filter_email(email_text: str):
    """
    이메일 필터링 API

    스타 토폴로지:
    - 1차: KoELECTRA Gateway
    - 중앙: EXAONE Star Node
    - LangGraph 오케스트레이션
    """
    use_case = FilterEmailUseCase()
    result = use_case.execute(email_text)

    return {
        "status": "success",
        "data": result
    }
```

---

## 코드 통합 및 정리 전략

### 📋 정리 대상 코드

#### 1. `training/services/` → 정리 대상

**삭제할 파일** (역할 중복):
```
training/services/
├── spam_classifier/      # 제거 (training/koelectra/로 통합)
│   ├── train.py         # → training/koelectra/train.py
│   ├── inference.py     # → app/infrastructure/models/koelectra/
│   └── ...
│
├── verdict_agent/        # 제거 (training/exaone/로 통합)
│   ├── exaone_inference.py  # → app/infrastructure/models/exaone/
│   ├── lora_adapter.py      # → training/exaone/train_lora.py
│   └── ...
│
├── gateway/              # 제거 (app/domain/shared/로 통합)
│   ├── hybrid_gateway.py
│   ├── ml_assistant.py
│   └── rules/
│
├── hub/                  # 제거 (app/application/orchestrators/로 통합)
│   ├── hub_router.py
│   ├── branch_registry.py
│   └── ...
│
└── branches/             # 제거 (app/domain/spam_filter/로 통합)
    ├── spam_agent.py
    └── ...
```

**통합 매핑**:
| 기존 위치 | 새 위치 | 역할 |
|----------|--------|------|
| `training/services/spam_classifier/train.py` | `training/koelectra/train.py` | 훈련 전용 |
| `training/services/spam_classifier/inference.py` | `app/infrastructure/models/koelectra/inference.py` | 추론 전용 |
| `training/services/verdict_agent/exaone_inference.py` | `app/infrastructure/models/exaone/inference.py` | 추론 전용 |
| `training/services/verdict_agent/lora_adapter.py` | `training/exaone/train_lora.py` | 훈련 전용 |
| `training/services/gateway/` | `app/domain/shared/gateway/` | 도메인 로직 |
| `training/services/hub/` | `app/application/orchestrators/hub/` | 오케스트레이션 |

#### 2. `app/services/` → 제거 대상

**상태**: 이미 `app/domain/`으로 마이그레이션됨

**삭제 명령**:
```bash
# 백업 후 삭제
mv app/services/ app/services_backup/
# 검증 후:
# rm -rf app/services_backup/
```

#### 3. `app/graph.py` → 제거 대상

**이유**: `app/application/orchestrators/star_topology/graph.py`로 대체됨

**삭제 명령**:
```bash
# 백업 후 삭제
mv app/graph.py app/graph_legacy.py
# 검증 후:
# rm app/graph_legacy.py
```

### 🔄 코드 통합 전략

#### Step 1: Infrastructure Layer 통합

**KoELECTRA 모델 통합**

```bash
# 1. infrastructure/models/koelectra/ 생성
mkdir -p app/infrastructure/models/koelectra

# 2. 추론 코드 이동
cat > app/infrastructure/models/koelectra/inference.py <<'EOF'
# training/services/spam_classifier/inference.py의 추론 로직만 추출
# 훈련 관련 코드 제거
EOF

# 3. 로더 생성
cat > app/infrastructure/models/koelectra/loader.py <<'EOF'
# 모델 로딩 로직 (싱글톤)
# artifacts/models/에서 로드
EOF
```

**EXAONE 모델 통합**

```bash
# 1. infrastructure/models/exaone/ 생성
mkdir -p app/infrastructure/models/exaone

# 2. 추론 코드 이동
cat > app/infrastructure/models/exaone/inference.py <<'EOF'
# training/services/verdict_agent/exaone_inference.py의 추론 로직만 추출
EOF

# 3. 어댑터 관리자 생성
cat > app/infrastructure/models/exaone/adapter_manager.py <<'EOF'
# LoRA 어댑터 로딩/관리
# artifacts/models/trained/exaone/adapter/ 관리
EOF
```

#### Step 2: Application Layer 통합

**LangGraph 오케스트레이터 통합**

```bash
# 1. orchestrators/star_topology/ 생성
mkdir -p app/application/orchestrators/star_topology

# 2. 기존 graph.py 재구성
mv app/graph.py app/application/orchestrators/star_topology/graph_legacy.py

# 3. 새 그래프 작성 (위의 예제 참조)
cat > app/application/orchestrators/star_topology/graph.py <<'EOF'
# 스타 토폴로지 그래프
EOF
```

#### Step 3: Training 폴더 정리

**KoELECTRA 훈련 통합**

```bash
# 1. training/koelectra/ 생성
mkdir -p training/koelectra

# 2. 훈련 스크립트 통합
cat > training/koelectra/train.py <<'EOF'
# training/services/spam_classifier/train.py + pipeline.py 통합
# 단일 훈련 스크립트로 정리
EOF

# 3. 설정 파일 생성
cat > training/koelectra/config.yaml <<'EOF'
model:
  base_path: artifacts/models/base/koelectra-small-v3-discriminator
  save_path: artifacts/models/trained/koelectra/spam_classifier

training:
  epochs: 3
  batch_size: 16
  learning_rate: 2e-5

data:
  train_path: app/data/spam_agent_processed/train.jsonl
  val_path: app/data/spam_agent_processed/val.jsonl
  test_path: app/data/spam_agent_processed/test.jsonl
EOF
```

**EXAONE 훈련 통합**

```bash
# 1. training/exaone/ 생성
mkdir -p training/exaone

# 2. LoRA 훈련 스크립트
cat > training/exaone/train_lora.py <<'EOF'
# training/services/verdict_agent/lora_adapter.py + load_model.py 통합
EOF

# 3. 설정 파일
cat > training/exaone/config.yaml <<'EOF'
model:
  base_path: artifacts/models/base/exaone-2.4b
  adapter_save_path: artifacts/models/trained/exaone/adapter

lora:
  r: 8
  lora_alpha: 16
  target_modules: ["q_proj", "v_proj"]

training:
  epochs: 3
  batch_size: 4
  learning_rate: 1e-4

data:
  train_path: app/data/spam_agent_processed/train.jsonl
  val_path: app/data/spam_agent_processed/val.jsonl
EOF
```

### 📝 삭제 체크리스트

**Phase 1: 백업 생성**
```bash
# 1. 전체 백업
tar -czf backup_$(date +%Y%m%d).tar.gz training/services/ app/services/ app/graph.py

# 2. Git 커밋
git add -A
git commit -m "백업: DDD 재구성 전"
```

**Phase 2: 안전 삭제**
```bash
# 1. training/services/ 제거
rm -rf training/services/

# 2. app/services/ 제거 (이미 domain/으로 마이그레이션됨)
rm -rf app/services/

# 3. app/graph.py 제거
rm app/graph.py

# 4. 기타 레거시 파일 제거
rm app/api_server.py           # api_server_refactored.py로 대체됨
rm app/chatbot_rag.py          # domain/chat/으로 대체됨
rm app/build_knowledge_base.py # domain/training/으로 대체됨
```

**Phase 3: 검증**
```bash
# 1. import 에러 확인
python -m pytest tests/ -v

# 2. API 테스트
pytest tests/integration/test_api.py

# 3. 모델 로딩 테스트
python -c "
from app.infrastructure.models.koelectra.loader import get_koelectra_model
from app.infrastructure.models.exaone.loader import get_exaone_model
print('✅ 모델 로딩 성공')
"
```

---

## 마이그레이션 로드맵

### 📅 Week 1: Infrastructure Layer 구축

**Day 1-2: 모델 Infrastructure 생성**
- [ ] `app/infrastructure/models/koelectra/` 생성
  - [ ] `loader.py`: 모델 로딩 (싱글톤)
  - [ ] `inference.py`: 추론 로직
  - [ ] `training.py`: 훈련 인터페이스 (참조용)
- [ ] `app/infrastructure/models/exaone/` 생성
  - [ ] `loader.py`: 모델 + 어댑터 로딩
  - [ ] `inference.py`: 추론 로직
  - [ ] `adapter_manager.py`: LoRA 어댑터 관리
- [ ] 환경 변수 설정 (`.env`)

**Day 3: Persistence Infrastructure**
- [ ] `app/infrastructure/persistence/database/` 구조 유지
- [ ] `app/infrastructure/persistence/repositories/` 구현 검증
- [ ] S3 클라이언트 생성 (`app/infrastructure/external/s3_client.py`)

**Day 4-5: Training 폴더 재구성**
- [ ] `training/koelectra/` 생성 및 통합
  - [ ] `train.py`: 단일 훈련 스크립트
  - [ ] `config.yaml`: 훈련 설정
  - [ ] `dataset.py`: 데이터셋 로더
- [ ] `training/exaone/` 생성 및 통합
  - [ ] `train_lora.py`: LoRA 파인튜닝
  - [ ] `config.yaml`: 훈련 설정
  - [ ] `merge_adapter.py`: 어댑터 병합
- [ ] `training/services/` 삭제

**검증:**
```bash
# 모델 로딩 테스트
python -c "from app.infrastructure.models.koelectra.loader import get_koelectra_model; get_koelectra_model()"
python -c "from app.infrastructure.models.exaone.loader import get_exaone_model; get_exaone_model()"

# 훈련 테스트 (dry-run)
cd training/koelectra && python train.py --dry-run
cd training/exaone && python train_lora.py --dry-run
```

---

### 📅 Week 2: Application Layer 구축

**Day 6-7: LangGraph 오케스트레이터**
- [ ] `app/application/orchestrators/star_topology/` 생성
  - [ ] `graph.py`: 스타 토폴로지 그래프
  - [ ] `nodes.py`: 노드 정의
  - [ ] `state.py`: 상태 정의
- [ ] 기존 `app/graph.py` 제거
- [ ] 조건부 라우팅 구현 (gateway → exaone/decision)

**Day 8-9: Use Cases 구현**
- [ ] `app/application/use_cases/spam_filter/`
  - [ ] `filter_email_use_case.py`
  - [ ] `analyze_spam_use_case.py`
- [ ] `app/application/use_cases/chat/`
  - [ ] `chat_use_case.py`
  - [ ] `rag_query_use_case.py`
- [ ] DTO 정의 (`app/application/dto/`)

**Day 10: Domain Layer 정리**
- [ ] `app/domain/spam_filter/` 재정리
  - [ ] `entities/`: 비즈니스 객체
  - [ ] `services/`: 도메인 서비스 (추론 제외)
- [ ] `app/domain/shared/gateway/` 이동
  - [ ] `training/services/gateway/` → `app/domain/shared/gateway/`

**검증:**
```bash
# LangGraph 테스트
python -c "
from app.application.orchestrators.star_topology.graph import build_star_topology_graph
graph = build_star_topology_graph()
result = graph.invoke({'text': '테스트 이메일'})
print(result)
"

# Use Case 테스트
pytest tests/application/use_cases/test_filter_email_use_case.py
```

---

### 📅 Week 3: Interface Layer & 통합

**Day 11-12: API 재구성**
- [ ] `app/interface/api/v1/spam_filter/` 생성
  - [ ] `filter_router.py`: Use Case 연동
- [ ] `app/main.py` 업데이트
  - [ ] 새 라우터 등록
  - [ ] 기존 라우터 제거
- [ ] `app/router/` 제거 (백업 후)

**Day 13: Artifacts & 배포 준비**
- [ ] S3 동기화 스크립트 (`scripts/sync_artifacts.sh`)
- [ ] EC2 배포 스크립트 업데이트 (`scripts/setup-ec2.sh`)
- [ ] 환경 변수 문서화 (`.env.example`)

**Day 14: 통합 테스트 & 정리**
- [ ] 통합 테스트 실행
  - [ ] API 엔드투엔드 테스트
  - [ ] 스타 토폴로지 플로우 테스트
  - [ ] 모델 로딩/추론 테스트
- [ ] 레거시 코드 삭제
  - [ ] `app/services/` 제거
  - [ ] `app/graph.py` 제거
  - [ ] `training/services/` 제거
- [ ] 문서화 업데이트

**최종 검증:**
```bash
# 1. 전체 테스트 스위트
pytest tests/ -v --cov=app

# 2. API 테스트
./test_api.ps1

# 3. 배포 테스트 (로컬)
docker-compose up --build

# 4. EC2 배포 시뮬레이션
./scripts/setup-ec2.sh --dry-run
```

---

## 📊 최종 폴더 구조

```
langchain/
├── app/                              # EC2 배포 대상
│   ├── interface/                   # Interface Layer
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── spam_filter/
│   │   │       │   └── filter_router.py
│   │   │       ├── chat/
│   │   │       └── training/
│   │   ├── cli/
│   │   └── events/
│   │
│   ├── application/                 # Application Layer
│   │   ├── use_cases/
│   │   │   ├── spam_filter/
│   │   │   │   ├── filter_email_use_case.py
│   │   │   │   └── analyze_spam_use_case.py
│   │   │   ├── chat/
│   │   │   └── training/
│   │   ├── orchestrators/
│   │   │   ├── star_topology/
│   │   │   │   ├── graph.py
│   │   │   │   ├── nodes.py
│   │   │   │   └── state.py
│   │   │   ├── spam_filter/
│   │   │   └── chat/
│   │   └── dto/
│   │
│   ├── domain/                      # Domain Layer
│   │   ├── spam_filter/
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   ├── services/
│   │   │   └── repositories/
│   │   ├── chat/
│   │   ├── training/
│   │   └── shared/
│   │       ├── gateway/
│   │       └── services/
│   │
│   ├── infrastructure/              # Infrastructure Layer
│   │   ├── models/
│   │   │   ├── koelectra/
│   │   │   │   ├── loader.py
│   │   │   │   ├── inference.py
│   │   │   │   └── training.py
│   │   │   └── exaone/
│   │   │       ├── loader.py
│   │   │       ├── inference.py
│   │   │       └── adapter_manager.py
│   │   ├── persistence/
│   │   │   ├── database/
│   │   │   └── repositories/
│   │   ├── external/
│   │   │   ├── s3_client.py
│   │   │   └── embedding_client.py
│   │   └── config/
│   │       ├── settings.py
│   │       └── model_config.py
│   │
│   └── main.py
│
├── training/                        # 모델 훈련 전용
│   ├── koelectra/
│   │   ├── train.py
│   │   ├── dataset.py
│   │   ├── config.yaml
│   │   └── evaluate.py
│   ├── exaone/
│   │   ├── train_lora.py
│   │   ├── dataset.py
│   │   ├── config.yaml
│   │   └── merge_adapter.py
│   ├── shared/
│   │   ├── data_processing/
│   │   ├── metrics/
│   │   └── callbacks/
│   └── README.md
│
├── artifacts/                       # S3 배포 대상
│   └── models/
│       ├── base/
│       │   ├── koelectra-small-v3-discriminator/
│       │   └── exaone-2.4b/
│       └── trained/
│           ├── koelectra/
│           │   └── spam_classifier/
│           └── exaone/
│               └── adapter/
│
├── scripts/                         # 배포 스크립트
│   ├── sync_artifacts.sh           # S3 동기화
│   ├── setup-ec2.sh                # EC2 배포
│   └── train_models.sh             # 훈련 실행
│
└── tests/                           # 테스트
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 🎯 핵심 원칙

### 1. **Clear Separation of Concerns**

| 레이어 | 역할 | 예시 |
|--------|------|------|
| **Interface** | 외부 통신 | FastAPI 라우터 |
| **Application** | 유즈케이스 + 오케스트레이션 | FilterEmailUseCase, LangGraph |
| **Domain** | 비즈니스 로직 | SpamFilterService |
| **Infrastructure** | 기술 구현 | KoELECTRA/EXAONE 모델 |

### 2. **Dependency Rule**

```
Interface → Application → Domain ← Infrastructure
```

- Domain은 Infrastructure에 의존하지 않음 (인터페이스로 역전)
- Infrastructure는 Domain 인터페이스 구현

### 3. **Folder Responsibility**

| 폴더 | 책임 | 배포 대상 |
|------|------|----------|
| `training/` | 모델 훈련 | ❌ (개발자용) |
| `artifacts/` | 모델 저장 | ✅ S3 |
| `app/` | 실행 환경 | ✅ EC2 |

### 4. **Star Topology Flow**

```
User Request (Interface)
    ↓
FilterEmailUseCase (Application)
    ↓
StarTopologyGraph (Application - LangGraph)
    ├─ gateway_node → KoELECTRAInference (Infrastructure)
    ├─ exaone_node → EXAONEInference (Infrastructure)
    └─ decision_node → Final Decision
    ↓
Response (Interface)
```

---

## 📚 참고 문서

- [36_STAR_TOPOLOGY_HYBRID_ARCHITECTURE.md](strategy/36_STAR_TOPOLOGY_HYBRID_ARCHITECTURE.md): 스타 토폴로지 상세 설계
- [DOMAIN_STRUCTURE_COMPLETE.md](DOMAIN_STRUCTURE_COMPLETE.md): 도메인 구조 전환 완료
- [DOMAIN_MIGRATION_STRATEGY.md](DOMAIN_MIGRATION_STRATEGY.md): 도메인 마이그레이션 전략

---

## ✅ 체크리스트

### Infrastructure Layer
- [ ] `app/infrastructure/models/koelectra/` 구현
- [ ] `app/infrastructure/models/exaone/` 구현
- [ ] S3 클라이언트 구현
- [ ] 모델 경로 환경 변수 설정

### Application Layer
- [ ] `app/application/orchestrators/star_topology/` 구현
- [ ] Use Cases 구현
- [ ] DTO 정의

### Domain Layer
- [ ] Domain Services 정리
- [ ] Repository 인터페이스 정의

### Interface Layer
- [ ] API 라우터 재구성
- [ ] `app/main.py` 업데이트

### Training
- [ ] `training/koelectra/` 통합
- [ ] `training/exaone/` 통합
- [ ] `training/services/` 삭제

### Cleanup
- [ ] `app/services/` 삭제
- [ ] `app/graph.py` 삭제
- [ ] 레거시 코드 제거

### Documentation
- [ ] README 업데이트
- [ ] API 문서 생성
- [ ] 배포 가이드 작성

---

**문서 버전**: 1.0
**작성일**: 2026-01-20
**다음 업데이트**: 마이그레이션 완료 후

