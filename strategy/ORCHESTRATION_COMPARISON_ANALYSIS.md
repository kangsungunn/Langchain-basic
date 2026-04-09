# Orchestration 비교 분석

## 개요

시스템에 두 개의 orchestration 레이어가 존재합니다:
1. `app/core/shared/orchestration/` - 전역 오케스트레이션 레이어
2. `app/domain/admin/orchestrators/` - 도메인 특화 오케스트레이터

## 1. app/core/shared/orchestration/ (전역 레이어)

### 위치 및 역할
- **위치**: `app/core/shared/orchestration/`
- **계층**: Infrastructure/Core Layer (가장 상위)
- **역할**: **스타 토폴로지 아키텍처의 중앙 허브** (Star Node)

### 핵심 컴포넌트

#### 1.1. `star_node.py` (LegalStarNode)
```
역할: 최상위 라우팅 및 중앙 통제
- Gateway: 요청 분류 (examination, patent, trademark)
- 브랜치 레지스트리 관리
- 최종 판단 및 정책 적용
```

**주요 기능**:
- `route()`: 요청 타입에 따라 브랜치 선택 (examination/patent/trademark)
- `orchestrate()`: 전체 워크플로우 실행 (Gateway → Branch → Star Decision)
- `_execute_branch()`: 브랜치 실행 (현재 미구현, TODO)
- `_make_final_decision()`: 최종 법률 판단 (보수적 판단, 위험도 평가)

**특징**:
- **도메인 독립적**: 어떤 도메인이든 라우팅 가능
- **정책 중심**: 법률 정책, 위험도 평가, 보수적 판단
- **확장 가능**: 새로운 브랜치 동적 추가 가능

#### 1.2. `hub_router.py` (HubRouter)
```
역할: 중앙 집권화 브랜치 관리
- 브랜치 라우팅 결정
- 브랜치 헬스 체크
- 최종 액션 결정 (Star의 권한)
- DB 접근 독점
```

**주요 기능**:
- `route()`: 게이트웨이 결과 기반 브랜치 선택
- `decide_final_action()`: Star의 최종 액션 결정 (브랜치는 권장만)
- `save_to_db()`: 전체 워크플로우 DB 저장
- `_fallback_routing()`: 폴백 브랜치 관리

**특징**:
- **중앙 통제**: 모든 브랜치를 관리하고 제어
- **헬스 관리**: 브랜치 상태 모니터링
- **정책 적용**: 온톨로지 정책 기반 최종 결정
- **DB 독점**: 오직 Hub Router만 DB 접근 가능

#### 1.3. `hybrid_gateway.py` (HybridGateway)
```
역할: 하이브리드 라우팅 (규칙 + ML)
- 1단계: 규칙 기반 필터 (70-90%, 1-5ms)
- 2단계: ML 보조 (10-30%, 50-100ms)
```

**주요 기능**:
- `route()`: 규칙 우선 → ML 보조 순차 처리
- 통계 수집 및 성능 모니터링

**특징**:
- **성능 최적화**: 대부분 요청을 빠르게 처리
- **하이브리드**: 규칙 + ML 조합
- **경량**: 평균 지연 시간 < 20ms

### 1.4. 기타 컴포넌트
- `branch_registry.py`: 브랜치 레지스트리 관리
- `health_checker.py`: 브랜치 헬스 체크
- `ontology_manager.py`: 온톨로지 및 정책 관리
- `rule_engine.py`: 규칙 기반 라우팅
- `ml_assistant.py`: ML 기반 분류

### 아키텍처 패턴
```
┌─────────────────────────────────────────┐
│         HybridGateway                   │  ← 1차 필터
│   (규칙 70-90% + ML 10-30%)             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         HubRouter / StarNode            │  ← 중앙 허브
│   - 브랜치 라우팅                        │
│   - 헬스 체크                            │
│   - 정책 적용                            │
│   - DB 저장                              │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴──────┬──────────┐
       ▼              ▼          ▼
   Examination     Patent    Trademark   ← 브랜치
    Branch        Branch      Branch
```

---

## 2. app/domain/admin/orchestrators/ (도메인 레이어)

### 위치 및 역할
- **위치**: `app/domain/admin/orchestrators/`
- **계층**: Domain Layer (도메인 특화)
- **역할**: **특정 도메인(examination/patent/trademark)의 비즈니스 로직 실행**

### 핵심 컴포넌트

#### 2.1. `examination_flow.py` (ExaminationOrchestrator)
```
역할: 심사(examination) 도메인 오케스트레이터
- 특허 심사 모델 로드 (artifacts/models/finetuned/patent/final)
- 규칙기반 vs 정책기반 분기
- ExaminationService / ExaminationAgent 라우팅
```

**주요 기능**:
- `_load_model()`: 특허 심사 모델 로드
- `execute_examination()`: 심사 실행
- `_execute_rule_based()`: 규칙기반 심사 (ExaminationService)
- `_execute_policy_based()`: 정책기반 심사 (ExaminationAgent)

#### 2.2. `patent_flow.py` (PatentOrchestrator)
```
역할: 특허(patent) 도메인 오케스트레이터
- 특허 분석 모델 로드 (artifacts/models/finetuned/patent/final)
- 규칙기반 vs 정책기반 분기
- PatentService / PatentAgent 라우팅
```

#### 2.3. `trademark_flow.py` (TrademarkOrchestrator)
```
역할: 상표(trademark) 도메인 오케스트레이터
- 상표 분석 모델 로드 (artifacts/models/finetuned/trademark/final)
- 규칙기반 vs 정책기반 분기
- TrademarkService / TrademarkAgent 라우팅
```

### 공통 패턴
모든 도메인 오케스트레이터는 동일한 패턴을 따릅니다:

```python
class DomainOrchestrator:
    def __init__(self, model_path):
        self.model = None
        self.tokenizer = None
        self._load_model()  # 모델 로드

    async def execute_analysis(self, analysis_type, text, ...):
        # 분석 유형에 따라 분기
        if analysis_type == "rule_based":
            return await self._execute_rule_based(...)
        elif analysis_type == "policy_based":
            return await self._execute_policy_based(...)

    async def _execute_rule_based(self, ...):
        # DomainService로 라우팅
        return await self.domain_service.analyze_by_rule(...)

    async def _execute_policy_based(self, ...):
        # DomainAgent로 라우팅 (LangGraph)
        return await self.domain_agent.analyze_by_policy(...)
```

### 아키텍처 패턴
```
FastAPI Router
      │
      ▼
DomainOrchestrator
  (model load)
      │
      ├─ rule_based ──→ DomainService (규칙기반)
      │                   └─ 조문 기반 판단
      │
      └─ policy_based ─→ DomainAgent (정책기반)
                          └─ LangGraph 워크플로우
                             (analyze → reason → decide)
```

---

## 3. 비교 분석

### 3.1. 역할 비교

| 측면 | `app/core/shared/orchestration/` | `app/domain/admin/orchestrators/` |
|------|----------------------------------|-----------------------------------|
| **계층** | Infrastructure/Core (최상위) | Domain Layer (도메인 특화) |
| **범위** | 전역 (시스템 전체) | 도메인 특화 (examination/patent/trademark) |
| **책임** | 라우팅, 정책, 헬스, DB 저장 | 비즈니스 로직, 모델 실행 |
| **의존성** | 도메인 독립적 | 도메인 의존적 |
| **확장성** | 수평 확장 (새 브랜치 추가) | 수직 확장 (도메인 내 로직) |

### 3.2. 기능 비교

#### `core/shared/orchestration/`의 기능:
1. **1차 라우팅**: 요청을 어느 브랜치로 보낼지 결정
2. **정책 적용**: 법률 정책, 위험도 평가, 보수적 판단
3. **중앙 통제**: 브랜치 헬스 체크, 폴백 관리
4. **DB 저장**: 전체 워크플로우 저장 (HubRouter만 DB 접근)
5. **하이브리드 게이트웨이**: 규칙 + ML 조합

#### `domain/admin/orchestrators/`의 기능:
1. **모델 로드**: 각 도메인별 파인튜닝 모델 로드
2. **2차 라우팅**: 규칙기반 vs 정책기반 분기
3. **비즈니스 로직**: 도메인 특화 분석 실행
4. **서비스/에이전트 조율**: Service (규칙) vs Agent (LangGraph)

### 3.3. 호출 순서

```
1. FastAPI Router
   └─> DomainOrchestrator (domain/admin/orchestrators/)
       ├─> Service (규칙기반)
       └─> Agent (정책기반, LangGraph)

별도로:
2. FastAPI Router (범용)
   └─> HybridGateway (core/shared/orchestration/)
       └─> HubRouter/StarNode
           └─> Branch (examination/patent/trademark)
```

---

## 4. 역할 중복 여부 판단

### 4.1. 중복되는 부분

#### ❌ 중복: 라우팅 로직
- **`StarNode.route()`**: examination/patent/trademark 라우팅
- **`DomainOrchestrator.execute_*()`**: rule_based/policy_based 라우팅

두 레이어가 모두 "라우팅"을 수행하지만, **레벨이 다릅니다**:
- StarNode: 1차 라우팅 (도메인 선택)
- DomainOrchestrator: 2차 라우팅 (분석 방법 선택)

### 4.2. 중복되지 않는 부분

#### ✅ 독립적: 책임 분리
1. **StarNode (core/shared/orchestration/)**:
   - 전역 라우팅 및 정책 적용
   - 브랜치 헬스 관리
   - DB 저장
   - 법률 정책, 위험도 평가

2. **DomainOrchestrator (domain/admin/orchestrators/)**:
   - 도메인 모델 로드 및 실행
   - 비즈니스 로직 처리
   - Service/Agent 조율

---

## 5. 통합 필요성 판단

### 5.1. 통합 가능한 시나리오

#### 시나리오 A: StarNode가 DomainOrchestrator를 브랜치로 사용
```python
class LegalStarNode:
    def _init_branches(self):
        self.branches = {
            BranchType.EXAMINATION: ExaminationOrchestrator(),
            BranchType.PATENT: PatentOrchestrator(),
            BranchType.TRADEMARK: TrademarkOrchestrator(),
        }

    def _execute_branch(self, branch_type, request):
        orchestrator = self.branches[branch_type]
        return await orchestrator.execute_analysis(
            analysis_type=request["analysis_type"],
            text=request["text"],
            ...
        )
```

**장점**:
- 단일 진입점 (StarNode)
- 중앙 집권화 라우팅
- 정책 및 헬스 관리 통합

**단점**:
- 복잡도 증가
- 도메인 로직이 Infrastructure 레이어에 의존

### 5.2. 분리 유지 시나리오

#### 현재 구조 유지
```
FastAPI Router (도메인별)
      │
      ▼
DomainOrchestrator (독립적)
      │
      ├─> Service (규칙기반)
      └─> Agent (정책기반)

별도:
FastAPI Router (범용)
      │
      ▼
HybridGateway → StarNode → Branch
```

**장점**:
- **관심사 분리** (Separation of Concerns)
- 도메인 독립성 유지
- 각 레이어 독립적 개발/배포 가능
- 테스트 용이

**단점**:
- 중복된 라우팅 로직 (1차/2차)
- 두 개의 orchestration 레이어 관리

---

## 6. 최종 판단 및 권장사항

### 6.1. 현재 상태 평가

#### ✅ **분리 유지 권장**

**이유**:
1. **서로 다른 책임**:
   - `core/shared/orchestration`: 전역 라우팅, 정책, 헬스, DB
   - `domain/admin/orchestrators`: 도메인 비즈니스 로직

2. **서로 다른 사용 패턴**:
   - StarNode: 범용 법률 AI 시스템 (미래 확장)
   - DomainOrchestrator: 현재 특화 도메인 (examination/patent/trademark)

3. **독립적 진화**:
   - StarNode는 온톨로지, 정책, 멀티 브랜치 관리 방향으로 진화
   - DomainOrchestrator는 도메인 모델, 비즈니스 로직 방향으로 진화

4. **관심사 분리 원칙**:
   - Infrastructure vs Domain Layer 명확히 분리

### 6.2. 개선 권장사항

#### ⚠️ 주의: 직접 코드 수정하지 않음 (분석만)

#### 1. 명확한 역할 정의 문서화
- `core/shared/orchestration/README.md` 작성
- `domain/admin/orchestrators/README.md` 작성
- 각 레이어의 책임 명시

#### 2. StarNode의 브랜치 구현
현재 StarNode의 `_execute_branch()`가 미구현 상태입니다.

**옵션 A**: DomainOrchestrator를 브랜치로 통합
```python
# star_node.py
def _init_branches(self):
    from app.domain.admin.orchestrators import (
        ExaminationOrchestrator,
        PatentOrchestrator,
        TrademarkOrchestrator
    )

    self.branches = {
        BranchType.EXAMINATION: ExaminationOrchestrator(),
        BranchType.PATENT: PatentOrchestrator(),
        BranchType.TRADEMARK: TrademarkOrchestrator(),
    }
```

**옵션 B**: 별도 브랜치 구현 (미래 확장 고려)
```python
# star_node.py
def _init_branches(self):
    self.branches = {
        BranchType.EXAMINATION: ExaminationBranch(),  # 새로운 Branch 클래스
        BranchType.PATENT: PatentBranch(),
        BranchType.TRADEMARK: TrademarkBranch(),
    }
```

#### 3. 명명 일관성
- `core/shared/orchestration` → 유지 (Infrastructure)
- `domain/admin/orchestrators` → 유지 (Domain)

#### 4. 인터페이스 정의
두 레이어 간 명확한 인터페이스 정의:
```python
# core/shared/orchestration/base_branch.py
class BaseBranch(ABC):
    @abstractmethod
    async def analyze(self, request: Dict[str, Any]) -> BranchResult:
        pass

# domain/admin/orchestrators/examination_flow.py
class ExaminationOrchestrator(BaseBranch):
    async def analyze(self, request: Dict[str, Any]) -> BranchResult:
        # 구현
        pass
```

---

## 7. 결론

### 현재 구조의 적절성: ✅ **적절함**

두 orchestration 레이어는 **서로 다른 책임**을 가지며, **관심사 분리** 원칙에 부합합니다:

1. **`core/shared/orchestration/`**:
   - Infrastructure Layer
   - 전역 라우팅, 정책, 헬스, DB
   - 도메인 독립적

2. **`domain/admin/orchestrators/`**:
   - Domain Layer
   - 비즈니스 로직, 모델 실행
   - 도메인 특화

### 권장 조치:
1. **현재 구조 유지**
2. StarNode의 브랜치 구현 (옵션 A 또는 B)
3. 각 레이어 문서화
4. 명확한 인터페이스 정의

### 미래 확장:
- StarNode: 온톨로지, 멀티 브랜치, 정책 엔진 확장
- DomainOrchestrator: 도메인 모델, 비즈니스 로직 심화

**최종 판단: 두 레이어는 통합할 필요 없이 분리 유지가 적절합니다.**
