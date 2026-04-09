# DDD 재구성 빠른 시작 가이드

## 🚀 즉시 실행 가능한 작업

### Phase 1: 현재 상태 정리 (Day 1 - 오늘 완료 가능)

#### 1단계: 백업 생성

```powershell
# 1. Git 커밋 (안전 장치)
git add -A
git commit -m "백업: DDD 재구성 시작 전"
git tag -a "before-ddd-refactoring" -m "DDD 재구성 전 백업"

# 2. 압축 백업 (선택)
Compress-Archive -Path training/services/, app/graph.py -DestinationPath "backup_$(Get-Date -Format 'yyyyMMdd').zip"
```

#### 2단계: 불필요한 코드 식별

**즉시 삭제 가능 (이미 마이그레이션됨):**
```powershell
# app/services/ → app/domain/으로 이미 마이그레이션됨
# 검증 후 삭제
if (Test-Path app/domain/spam_filter) {
    Write-Host "✅ app/domain/spam_filter 존재 확인"
    # 백업
    Rename-Item app/services app/services_backup
    Write-Host "🗑️ app/services → app/services_backup 이름 변경"
}

# app/graph.py → app/domain/chat/orchestrators/로 이미 마이그레이션됨
if (Test-Path app/domain/chat/orchestrators/graph.py) {
    Write-Host "✅ app/domain/chat/orchestrators/graph.py 존재 확인"
    # 백업
    Rename-Item app/graph.py app/graph_legacy.py
    Write-Host "🗑️ app/graph.py → app/graph_legacy.py 이름 변경"
}
```

#### 3단계: training/services/ 분석

```powershell
# training/services/ 폴더 구조 확인
Get-ChildItem -Path training/services/ -Recurse -File |
    Select-Object FullName, Length, LastWriteTime |
    Format-Table -AutoSize > training_services_analysis.txt

Write-Host "📊 분석 결과: training_services_analysis.txt"
```

**분석 결과에 따른 조치:**

| 파일 | 현재 위치 | 새 위치 | 액션 |
|------|----------|--------|------|
| `spam_classifier/train.py` | `training/services/` | `training/koelectra/train.py` | 이동 + 통합 |
| `spam_classifier/inference.py` | `training/services/` | `app/infrastructure/models/koelectra/inference.py` | 이동 + 분리 |
| `verdict_agent/exaone_inference.py` | `training/services/` | `app/infrastructure/models/exaone/inference.py` | 이동 + 분리 |
| `verdict_agent/lora_adapter.py` | `training/services/` | `training/exaone/train_lora.py` | 이동 + 통합 |
| `gateway/*` | `training/services/` | `app/domain/shared/gateway/` | 이동 |
| `hub/*` | `training/services/` | `app/application/orchestrators/hub/` | 이동 |
| `branches/*` | `training/services/` | `app/domain/spam_filter/agents/` | 이동 |

---

### Phase 2: Infrastructure Layer 구축 (Day 1-2)

#### 스텝 1: 폴더 구조 생성

```powershell
# Infrastructure Layer 폴더 생성
$infraFolders = @(
    "app/infrastructure",
    "app/infrastructure/models",
    "app/infrastructure/models/koelectra",
    "app/infrastructure/models/exaone",
    "app/infrastructure/persistence",
    "app/infrastructure/external",
    "app/infrastructure/config"
)

foreach ($folder in $infraFolders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force
        New-Item -ItemType File -Path "$folder/__init__.py"
        Write-Host "✅ 생성: $folder"
    }
}
```

#### 스텝 2: KoELECTRA Infrastructure 구현

**파일 1: `app/infrastructure/models/koelectra/loader.py`**

```python
# app/infrastructure/models/koelectra/loader.py
"""
KoELECTRA 모델 로더 (싱글톤)

역할: artifacts/models/에서 KoELECTRA 모델 로드 및 캐싱
"""

import os
from typing import Tuple, Optional
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

# 싱글톤 캐시
_koelectra_model = None
_koelectra_tokenizer = None

def get_koelectra_model(
    model_path: Optional[str] = None
) -> Tuple[AutoModelForSequenceClassification, AutoTokenizer]:
    """
    KoELECTRA 모델 로드 (싱글톤)

    Args:
        model_path: 모델 경로 (기본값: 환경 변수)

    Returns:
        (model, tokenizer)
    """
    global _koelectra_model, _koelectra_tokenizer

    if _koelectra_model is None or _koelectra_tokenizer is None:
        # 환경 변수에서 경로 가져오기
        if model_path is None:
            model_path = os.getenv(
                "KOELECTRA_TRAINED_PATH",
                "artifacts/models/trained/koelectra/spam_classifier/full/run_20260114_143241"
            )

        # 모델 로드
        print(f"🔄 KoELECTRA 모델 로드 중: {model_path}")
        _koelectra_model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            num_labels=2
        )
        _koelectra_tokenizer = AutoTokenizer.from_pretrained(model_path)

        # GPU 사용 가능하면 이동
        if torch.cuda.is_available():
            _koelectra_model = _koelectra_model.cuda()

        print("✅ KoELECTRA 모델 로드 완료")

    return _koelectra_model, _koelectra_tokenizer

def clear_koelectra_cache():
    """모델 캐시 초기화 (메모리 절약용)"""
    global _koelectra_model, _koelectra_tokenizer
    _koelectra_model = None
    _koelectra_tokenizer = None
    print("🗑️ KoELECTRA 캐시 초기화")
```

**파일 2: `app/infrastructure/models/koelectra/inference.py`**

```python
# app/infrastructure/models/koelectra/inference.py
"""
KoELECTRA 추론 (Gateway 역할)

역할: 1차 스팸 분류 + 라우팅 결정
"""

from typing import Dict
import torch
from .loader import get_koelectra_model

class KoELECTRAGateway:
    """
    1차 Gateway: KoELECTRA 기반 스팸 분류

    스타 토폴로지:
    - 빠른 1차 필터링 (50-100ms)
    - 라우팅 결정: normal / spam_agent / exaone_review
    """

    def __init__(self, model_path: str = None):
        self.model, self.tokenizer = get_koelectra_model(model_path)
        self.model.eval()  # 평가 모드

    @torch.no_grad()
    def predict(self, text: str) -> Dict[str, any]:
        """
        스팸 확률 예측 + 라우팅 결정

        Args:
            text: 입력 텍스트

        Returns:
            {
                "is_spam": bool,
                "spam_prob": float,
                "confidence": float,
                "route": str,  # "normal" | "spam_agent" | "exaone_review"
                "latency_ms": float
            }
        """
        import time
        start_time = time.time()

        # 토큰화
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )

        # GPU 이동
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        # 추론
        outputs = self.model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)
        spam_prob = probs[0][1].item()  # 스팸 확률

        # 라우팅 결정
        route = self._decide_route(spam_prob)

        latency_ms = (time.time() - start_time) * 1000

        return {
            "is_spam": spam_prob > 0.5,
            "spam_prob": spam_prob,
            "confidence": max(spam_prob, 1 - spam_prob),
            "route": route,
            "latency_ms": latency_ms
        }

    def _decide_route(self, spam_prob: float) -> str:
        """
        라우팅 결정

        규칙:
        - spam_prob > 0.8: 확실한 스팸 → spam_agent
        - spam_prob < 0.2: 확실한 정상 → normal
        - 0.2 <= spam_prob <= 0.8: 모호함 → exaone_review
        """
        if spam_prob > 0.8:
            return "spam_agent"
        elif spam_prob < 0.2:
            return "normal"
        else:
            return "exaone_review"
```

**파일 3: `.env.example`** (환경 변수 예시)

```bash
# KoELECTRA 모델 경로
KOELECTRA_BASE_PATH=artifacts/models/base/koelectra-small-v3-discriminator
KOELECTRA_TRAINED_PATH=artifacts/models/trained/koelectra/spam_classifier/full/run_20260114_143241

# EXAONE 모델 경로
EXAONE_BASE_PATH=artifacts/models/base/exaone-2.4b
EXAONE_ADAPTER_PATH=artifacts/models/trained/exaone/adapter/checkpoint-3000

# 데이터베이스
DATABASE_URL=postgresql://user:pass@localhost:5432/mcp_agent

# S3 (옵션)
MODEL_STORAGE=local  # 또는 s3
S3_BUCKET=mcp-agent-models
AWS_REGION=ap-northeast-2
```

#### 스텝 3: EXAONE Infrastructure 구현

**파일 4: `app/infrastructure/models/exaone/loader.py`**

```python
# app/infrastructure/models/exaone/loader.py
"""
EXAONE 모델 로더 (싱글톤)

역할: EXAONE 베이스 모델 + LoRA 어댑터 로드
"""

import os
from typing import Tuple, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

_exaone_model = None
_exaone_tokenizer = None

def get_exaone_model(
    base_path: Optional[str] = None,
    adapter_path: Optional[str] = None
) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
    """
    EXAONE 모델 + LoRA 어댑터 로드 (싱글톤)

    Args:
        base_path: 베이스 모델 경로
        adapter_path: LoRA 어댑터 경로 (옵션)

    Returns:
        (model, tokenizer)
    """
    global _exaone_model, _exaone_tokenizer

    if _exaone_model is None or _exaone_tokenizer is None:
        # 환경 변수에서 경로 가져오기
        if base_path is None:
            base_path = os.getenv(
                "EXAONE_BASE_PATH",
                "artifacts/models/base/exaone-2.4b"
            )

        if adapter_path is None:
            adapter_path = os.getenv(
                "EXAONE_ADAPTER_PATH",
                None  # 어댑터 없이도 동작
            )

        # 베이스 모델 로드
        print(f"🔄 EXAONE 베이스 모델 로드 중: {base_path}")
        _exaone_model = AutoModelForCausalLM.from_pretrained(
            base_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )

        # LoRA 어댑터 로드 (옵션)
        if adapter_path and os.path.exists(adapter_path):
            print(f"🔄 LoRA 어댑터 로드 중: {adapter_path}")
            from peft import PeftModel
            _exaone_model = PeftModel.from_pretrained(
                _exaone_model,
                adapter_path
            )
            print("✅ LoRA 어댑터 로드 완료")

        _exaone_tokenizer = AutoTokenizer.from_pretrained(
            base_path,
            trust_remote_code=True
        )

        print("✅ EXAONE 모델 로드 완료")

    return _exaone_model, _exaone_tokenizer
```

**파일 5: `app/infrastructure/models/exaone/inference.py`**

```python
# app/infrastructure/models/exaone/inference.py
"""
EXAONE 추론 (Star Node 역할)

역할: 중앙 의사결정 + 최종 판단
"""

from typing import Dict, Optional
import torch
from .loader import get_exaone_model

class EXAONEStarNode:
    """
    중앙 Star Node: EXAONE 기반 최종 의사결정

    스타 토폴로지:
    - 모호한 케이스 최종 판단
    - 브랜치 결과 검토
    - 정책 기반 의사결정
    """

    def __init__(self, base_path: str = None, adapter_path: str = None):
        self.model, self.tokenizer = get_exaone_model(base_path, adapter_path)
        self.model.eval()

    @torch.no_grad()
    def analyze(
        self,
        text: str,
        gateway_result: Dict[str, any],
        context: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        최종 분석 및 의사결정

        Args:
            text: 원본 텍스트
            gateway_result: KoELECTRA 1차 결과
            context: 추가 컨텍스트

        Returns:
            {
                "final_decision": str,  # "block" | "deliver" | "quarantine"
                "reason": str,
                "evidence": List[str],
                "confidence": float,
                "latency_ms": float
            }
        """
        import time
        start_time = time.time()

        # 프롬프트 생성
        prompt = self._build_prompt(text, gateway_result, context)

        # EXAONE 추론
        inputs = self.tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.1,
            do_sample=True,
            top_p=0.9
        )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 응답 파싱
        result = self._parse_response(response, gateway_result)
        result["latency_ms"] = (time.time() - start_time) * 1000

        return result

    def _build_prompt(
        self,
        text: str,
        gateway_result: Dict,
        context: Optional[Dict]
    ) -> str:
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

    def _parse_response(
        self,
        response: str,
        gateway_result: Dict
    ) -> Dict[str, any]:
        """EXAONE 응답 파싱"""
        # 간단한 파싱 (실제로는 더 정교하게)
        lines = response.split('\n')

        decision = "quarantine"  # 기본값
        reason = "EXAONE 판단 중"
        evidence = []

        for line in lines:
            if line.startswith("결정:"):
                decision = line.split(":")[1].strip().lower()
            elif line.startswith("이유:"):
                reason = line.split(":")[1].strip()
            elif line.startswith("증거:"):
                evidence = [e.strip() for e in line.split(":")[1].split(",")]

        return {
            "final_decision": decision,
            "reason": reason,
            "evidence": evidence,
            "confidence": 0.8  # EXAONE은 높은 신뢰도
        }
```

#### 스텝 4: 테스트 스크립트

**파일 6: `tests/infrastructure/test_models.py`**

```python
# tests/infrastructure/test_models.py
"""
Infrastructure Layer 테스트
"""

def test_koelectra_loading():
    """KoELECTRA 모델 로딩 테스트"""
    from app.infrastructure.models.koelectra.loader import get_koelectra_model

    model, tokenizer = get_koelectra_model()
    assert model is not None
    assert tokenizer is not None
    print("✅ KoELECTRA 로딩 성공")

def test_koelectra_inference():
    """KoELECTRA 추론 테스트"""
    from app.infrastructure.models.koelectra.inference import KoELECTRAGateway

    gateway = KoELECTRAGateway()
    result = gateway.predict("긴급! 계좌번호를 확인하세요!")

    assert "spam_prob" in result
    assert "route" in result
    assert result["route"] in ["normal", "spam_agent", "exaone_review"]
    print(f"✅ KoELECTRA 추론 성공: {result}")

def test_exaone_loading():
    """EXAONE 모델 로딩 테스트"""
    from app.infrastructure.models.exaone.loader import get_exaone_model

    model, tokenizer = get_exaone_model()
    assert model is not None
    assert tokenizer is not None
    print("✅ EXAONE 로딩 성공")

def test_exaone_inference():
    """EXAONE 추론 테스트"""
    from app.infrastructure.models.exaone.inference import EXAONEStarNode

    star_node = EXAONEStarNode()

    # 모의 gateway 결과
    gateway_result = {
        "spam_prob": 0.6,
        "confidence": 0.6,
        "route": "exaone_review"
    }

    result = star_node.analyze(
        text="긴급! 계좌번호를 확인하세요!",
        gateway_result=gateway_result
    )

    assert "final_decision" in result
    assert result["final_decision"] in ["block", "deliver", "quarantine"]
    print(f"✅ EXAONE 추론 성공: {result}")

if __name__ == "__main__":
    print("🧪 Infrastructure Layer 테스트 시작\n")

    print("1️⃣ KoELECTRA 테스트...")
    test_koelectra_loading()
    test_koelectra_inference()

    print("\n2️⃣ EXAONE 테스트...")
    test_exaone_loading()
    test_exaone_inference()

    print("\n✅ 모든 테스트 통과!")
```

**실행:**

```powershell
# .env 파일 생성
Copy-Item .env.example .env

# 테스트 실행
python tests/infrastructure/test_models.py
```

---

### Phase 3: Application Layer 구축 (Day 3-4)

#### 스텝 1: 폴더 구조 생성

```powershell
# Application Layer 폴더 생성
$appFolders = @(
    "app/application",
    "app/application/use_cases",
    "app/application/use_cases/spam_filter",
    "app/application/orchestrators",
    "app/application/orchestrators/star_topology",
    "app/application/dto"
)

foreach ($folder in $appFolders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force
        New-Item -ItemType File -Path "$folder/__init__.py"
        Write-Host "✅ 생성: $folder"
    }
}
```

#### 스텝 2: LangGraph 오케스트레이터

**파일 7: `app/application/orchestrators/star_topology/state.py`**

```python
# app/application/orchestrators/star_topology/state.py
"""
스타 토폴로지 상태 정의
"""

from typing import TypedDict, Optional, Dict, Any

class StarTopologyState(TypedDict):
    """스타 토폴로지 워크플로우 상태"""

    # 입력
    text: str
    context: Optional[Dict[str, Any]]

    # Gateway 결과
    gateway_result: Optional[Dict[str, Any]]

    # EXAONE 결과
    exaone_result: Optional[Dict[str, Any]]

    # 최종 결정
    final_decision: Optional[Dict[str, Any]]

    # 메타데이터
    trace_id: str
    current_step: str
```

**파일 8: `app/application/orchestrators/star_topology/nodes.py`**

```python
# app/application/orchestrators/star_topology/nodes.py
"""
스타 토폴로지 노드 정의
"""

from typing import Dict, Any
from .state import StarTopologyState

def gateway_node(state: StarTopologyState) -> Dict[str, Any]:
    """
    Gateway 노드: KoELECTRA 1차 필터링
    """
    from app.infrastructure.models.koelectra.inference import KoELECTRAGateway

    # 싱글톤으로 모델 재사용
    gateway = KoELECTRAGateway()
    result = gateway.predict(state["text"])

    return {
        "gateway_result": result,
        "current_step": "gateway"
    }

def exaone_node(state: StarTopologyState) -> Dict[str, Any]:
    """
    EXAONE Star Node: 최종 의사결정
    """
    from app.infrastructure.models.exaone.inference import EXAONEStarNode

    star_node = EXAONEStarNode()
    result = star_node.analyze(
        text=state["text"],
        gateway_result=state["gateway_result"],
        context=state.get("context")
    )

    return {
        "exaone_result": result,
        "current_step": "exaone"
    }

def decision_node(state: StarTopologyState) -> Dict[str, Any]:
    """
    최종 의사결정 노드
    """
    gateway = state["gateway_result"]
    exaone = state.get("exaone_result")

    # 라우팅 결정에 따라 최종 판단
    if gateway["route"] == "normal":
        # 확실한 정상 → 통과
        final_decision = {
            "action": "deliver",
            "reason": "1차 필터 통과 (정상)",
            "confidence": gateway["confidence"],
            "method": "gateway_only"
        }
    elif gateway["route"] == "spam_agent":
        # 확실한 스팸 → 차단
        final_decision = {
            "action": "block",
            "reason": "1차 필터 차단 (스팸)",
            "confidence": gateway["confidence"],
            "method": "gateway_only"
        }
    else:
        # 모호함 → EXAONE 결과 사용
        final_decision = {
            "action": exaone["final_decision"],
            "reason": exaone["reason"],
            "confidence": exaone["confidence"],
            "method": "exaone_review"
        }

    return {
        "final_decision": final_decision,
        "current_step": "decision"
    }
```

**파일 9: `app/application/orchestrators/star_topology/graph.py`**

```python
# app/application/orchestrators/star_topology/graph.py
"""
스타 토폴로지 LangGraph 정의
"""

from langgraph.graph import StateGraph, END
from .state import StarTopologyState
from .nodes import gateway_node, exaone_node, decision_node

def build_star_topology_graph():
    """
    스타 토폴로지 그래프 빌드

    플로우:
    START → gateway → [조건부] exaone → decision → END
    """
    graph = StateGraph(StarTopologyState)

    # 노드 추가
    graph.add_node("gateway", gateway_node)
    graph.add_node("exaone", exaone_node)
    graph.add_node("decision", decision_node)

    # 시작점
    graph.set_entry_point("gateway")

    # 조건부 엣지: gateway 결과에 따라 분기
    def should_use_exaone(state: StarTopologyState) -> str:
        """EXAONE 사용 여부 결정"""
        route = state["gateway_result"]["route"]
        return "exaone" if route == "exaone_review" else "decision"

    graph.add_conditional_edges(
        "gateway",
        should_use_exaone,
        {
            "exaone": "exaone",
            "decision": "decision"
        }
    )

    # exaone → decision
    graph.add_edge("exaone", "decision")

    # decision → END
    graph.add_edge("decision", END)

    return graph.compile()

# 싱글톤 그래프
_star_topology_graph = None

def get_star_topology_graph():
    """스타 토폴로지 그래프 가져오기 (싱글톤)"""
    global _star_topology_graph
    if _star_topology_graph is None:
        _star_topology_graph = build_star_topology_graph()
    return _star_topology_graph
```

#### 스텝 3: Use Case 구현

**파일 10: `app/application/use_cases/spam_filter/filter_email_use_case.py`**

```python
# app/application/use_cases/spam_filter/filter_email_use_case.py
"""
이메일 필터링 유즈케이스
"""

import uuid
from typing import Dict, Any
from app.application.orchestrators.star_topology.graph import get_star_topology_graph

class FilterEmailUseCase:
    """
    이메일 필터링 유즈케이스

    스타 토폴로지 실행:
    1. KoELECTRA Gateway (1차)
    2. EXAONE Star Node (최종) - 필요시
    3. 결과 반환
    """

    def __init__(self):
        self.graph = get_star_topology_graph()

    def execute(self, email_text: str) -> Dict[str, Any]:
        """
        이메일 필터링 실행

        Args:
            email_text: 이메일 본문

        Returns:
            {
                "action": "deliver" | "block" | "quarantine",
                "reason": str,
                "confidence": float,
                "method": str,  # "gateway_only" | "exaone_review"
                "trace_id": str,
                "gateway_result": dict,
                "exaone_result": dict (옵션)
            }
        """
        # 초기 상태
        trace_id = str(uuid.uuid4())
        initial_state = {
            "text": email_text,
            "context": None,
            "gateway_result": None,
            "exaone_result": None,
            "final_decision": None,
            "trace_id": trace_id,
            "current_step": "start"
        }

        # LangGraph 실행
        result = self.graph.invoke(initial_state)

        # 결과 반환
        return {
            "action": result["final_decision"]["action"],
            "reason": result["final_decision"]["reason"],
            "confidence": result["final_decision"]["confidence"],
            "method": result["final_decision"]["method"],
            "trace_id": trace_id,
            "gateway_result": result["gateway_result"],
            "exaone_result": result.get("exaone_result")
        }
```

**테스트:**

```python
# tests/application/test_use_cases.py
def test_filter_email_use_case():
    """FilterEmailUseCase 테스트"""
    from app.application.use_cases.spam_filter.filter_email_use_case import FilterEmailUseCase

    use_case = FilterEmailUseCase()

    # 테스트 1: 확실한 스팸
    result1 = use_case.execute("긴급! 계좌번호를 확인하세요! 당첨되셨습니다!")
    print(f"테스트 1 (확실한 스팸): {result1}")
    assert result1["method"] == "gateway_only"
    assert result1["action"] == "block"

    # 테스트 2: 확실한 정상
    result2 = use_case.execute("안녕하세요, 회의 일정을 공유드립니다.")
    print(f"테스트 2 (확실한 정상): {result2}")
    assert result2["method"] == "gateway_only"
    assert result2["action"] == "deliver"

    # 테스트 3: 모호한 케이스 (EXAONE 검토)
    result3 = use_case.execute("무료 체험판을 제공합니다. 관심 있으시면 연락주세요.")
    print(f"테스트 3 (모호한 케이스): {result3}")
    # 이 경우 EXAONE이 판단

    print("✅ 모든 테스트 통과!")

if __name__ == "__main__":
    test_filter_email_use_case()
```

---

### 오늘 바로 실행할 명령어 요약

```powershell
# 1. 백업
git add -A && git commit -m "백업: DDD 재구성 시작"

# 2. 폴더 구조 생성
$folders = @(
    "app/infrastructure/models/koelectra",
    "app/infrastructure/models/exaone",
    "app/application/use_cases/spam_filter",
    "app/application/orchestrators/star_topology"
)
foreach ($f in $folders) { New-Item -ItemType Directory -Path $f -Force; New-Item -ItemType File -Path "$f/__init__.py" }

# 3. .env 파일 생성
Copy-Item .env.example .env

# 4. 위의 파일들 생성 (코드 복사-붙여넣기)

# 5. 테스트 실행
python tests/infrastructure/test_models.py
python tests/application/test_use_cases.py

# 6. API 테스트 (다음 단계)
```

---

## 다음 단계 프리뷰

**Day 3-4: Interface Layer (API)**
- FastAPI 라우터 생성
- Use Case 연동
- Swagger 문서 생성

**Day 5: Training 폴더 정리**
- `training/koelectra/` 통합
- `training/exaone/` 통합
- `training/services/` 삭제

**Day 6-7: 통합 테스트 & 배포**
- 엔드투엔드 테스트
- S3 동기화
- EC2 배포

---

## 문제 해결

### 모델 로딩 실패 시

```powershell
# artifacts/models/ 경로 확인
Get-ChildItem artifacts/models/ -Recurse -Directory

# 환경 변수 확인
Get-Content .env | Select-String "MODEL"
```

### Import 에러 시

```powershell
# Python 경로 확인
python -c "import sys; print('\n'.join(sys.path))"

# 패키지 설치 확인
pip list | Select-String -Pattern "transformers|torch|langchain"
```

---

**이 가이드로 오늘 바로 시작할 수 있습니다!** 🚀

각 단계를 순서대로 따라하면 DDD 재구성의 첫 단계(Infrastructure Layer)가 완성됩니다.
