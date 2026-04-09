# MCP 자동화 구조 전략 — ExaOne 자동 임베딩

> **EXAONE_MCP_AUTOMATION_STRUCTURE.md**를 참고하여, **현재 프로젝트 구조**(app/domain/v1/minso)에 맞춘 MCP 자동화 전략.
> 주제/서브도메인(soccer vs minso)은 무시하고, **구조/흐름/기능**만 중점적으로 정리.

---

## 1. 개요

### 1.1 목표

**ExaOne 모델을 활용한 MCP 기반 자동 임베딩 생성 시스템** 구축.

- **코드 생성 자동화**: ExaOne으로 SQLAlchemy ORM 임베딩 모델 코드 자동 생성
- **런타임 자동화**: API 호출 시 자동으로 임베딩 생성 및 DB 저장

### 1.2 두 가지 자동화 레벨

| 레벨 | 목적 | 실행 방식 | 위치 |
|------|------|-----------|------|
| **코드 생성 자동화** | 임베딩 모델 코드 생성 | 수동 실행 스크립트 | `app/alter_ollama/` |
| **런타임 자동화** | 실제 임베딩 데이터 생성 | API 호출 시 자동 | Orchestrator → MCP 서버 → KoELECTRA → DB |

---

## 2. 현재 상태 vs 강사님 구조 비교

### 2.1 현재 프로젝트 상태

| 컴포넌트 | 현재 상태 | 비고 |
|----------|-----------|------|
| **MCP 프로토콜** | ✅ `hub/mcp_central/` (protocol, message, transport) | 도메인 간 통신 프로토콜만 있음 |
| **FastMCP 서버** | ❌ 없음 | 중앙 MCP 서버(툴 제공) 필요 |
| **임베딩 모델** | ⚠️ `models/bases/*_embeddings.py` 파일만 있고 비어있음 | 코드 생성 필요 |
| **KoELECTRA** | ⚠️ `core/ml/koelectra_loader.py` (로더만) | 임베딩 생성 기능 없음 |
| **ExaOne** | ⚠️ `core/ml/model_loader.py` (로더만) | 코드 생성 기능 없음 |
| **Orchestrator** | ✅ `hub/orchestrators/` (MinsoHub, ReasoningHub) | LangGraph 없음, 임베딩 마이그레이션 없음 |
| **코드 생성 스크립트** | ❌ 없음 | `app/alter_ollama/` 필요 |
| **Redis** | ❌ 없음 | 백그라운드 작업용 (선택) |

### 2.2 강사님 구조 (EXAONE_MCP_AUTOMATION_STRUCTURE.md)

| 컴포넌트 | 강사님 구조 | 역할 |
|----------|-------------|------|
| **코드 생성** | `app/alter_ollama/*.py` | ExaOne으로 ORM 코드 생성 |
| **중앙 MCP 서버** | `hub/mcp/central_mcp_server.py` | FastMCP 기반, ExaOne/KoELECTRA 툴 제공 |
| **Orchestrator** | `hub/orchestrators/*.py` | LangGraph StateGraph, MCP 서버 툴 호출 |
| **API Router** | `api/v10/soccer/*_router.py` | Redis 백그라운드 작업 트리거 |

---

## 3. 핵심 컴포넌트 설계 전략

### 3.1 중앙 MCP 서버 (`hub/mcp_central/central_mcp_server.py`)

**역할**: ExaOne과 KoELECTRA 모델을 관리하고, **FastMCP 툴로 제공**.

#### 3.1.1 구조 설계

```
app/domain/v1/minso/hub/mcp_central/
├── __init__.py                    # (기존) protocol, message, transport re-export
├── protocol.py                    # (기존) MCP 프로토콜 정의
├── message.py                     # (기존) MCP 메시지 클래스
├── transport.py                   # (기존) MCP 전송 계층
└── central_mcp_server.py          # ← 새로 추가: FastMCP 기반 중앙 서버
```

#### 3.1.2 주요 기능 (툴)

**ExaOne 툴:**
- `exaone_generate_text` - 텍스트 생성
- `exaone_generate_code` - 코드 생성 (일반)
- `exaone_analyze_reference_data` - 모범답안 데이터 분석
- `exaone_analyze_submission_data` - 제출 답안 데이터 분석
- `exaone_analyze_reasoning_data` - 추론 데이터 분석
- `exaone_analyze_feedback_data` - 피드백 데이터 분석

**KoELECTRA 툴:**
- `koelectra_embed_text` - 텍스트 임베딩 생성 (768차원 벡터)
- `koelectra_classify_text` - 텍스트 분류 (정책/규칙 판단용, 기존 DecisionMaker와 통합 가능)

**통합 파이프라인:**
- `koelectra_to_exaone_pipeline` - KoELECTRA 임베딩 생성 후 ExaOne으로 분석

#### 3.1.3 구현 방식

```python
from fastmcp import FastMCP

class MinsoCentralMCPServer:
    """중앙 MCP 서버 (FastMCP 기반)"""

    _instance: Optional["MinsoCentralMCPServer"] = None

    def __init__(self):
        self.mcp = FastMCP("Minso Central MCP Server")
        self.exaone_llm = None  # 지연 로딩
        self.koelectra_model = None  # 지연 로딩
        self._register_tools()

    def _register_tools(self):
        """MCP 툴 등록"""
        # @self.mcp.tool() 데코레이터로 툴 등록
        ...

    @classmethod
    def get_instance(cls) -> "MinsoCentralMCPServer":
        """싱글톤 인스턴스"""
        ...
```

**의존성:**
- `core/ml/model_loader.py` (ExaOne 로더) - **사용만**, core는 그대로 유지
- `core/ml/koelectra_loader.py` (KoELECTRA 로더) - **사용만**, core는 그대로 유지
- `fastmcp` 패키지 (requirements.txt에 이미 있음)

#### 3.1.4 결정 필요 사항

**Q1. 중앙 MCP 서버 위치**
- **옵션 A**: `hub/mcp_central/central_mcp_server.py` (기존 mcp_central 폴더에 추가)
- **옵션 B**: `hub/mcp/central_mcp_server.py` (새 폴더 생성, mcp_central과 분리)
- **추천**: **옵션 A**. 기존 mcp_central 폴더에 추가하는 것이 자연스러움.

**Q2. 모델 로딩 방식**
- **옵션 A**: 중앙 서버에서 직접 로드 (core/ml 로더 사용)
- **옵션 B**: core/ml 로더를 싱글톤으로 사용 (중앙 서버는 래퍼만)
- **추천**: **옵션 B**. core/ml의 싱글톤 로더를 재사용하여 메모리 효율성.

**Q3. FastMCP vs 기존 MCPTransport**
- **현재**: `mcp_central/transport.py`에 MCPTransport (도메인 간 메시지 전송)
- **강사님**: FastMCP 기반 서버 (툴 제공)
- **결정 필요**:
  - **A) FastMCP 서버 추가** (기존 transport와 별개, 툴 제공용)
  - **B) 기존 transport 확장** (툴 기능 추가)
  - **추천**: **옵션 A**. FastMCP는 툴 제공, transport는 도메인 간 통신. 역할 분리.

---

### 3.2 코드 생성 자동화 (`app/alter_ollama/`)

**역할**: ExaOne 모델로 SQLAlchemy ORM 임베딩 모델 코드 자동 생성.

#### 3.2.1 구조 설계

```
app/alter_ollama/
├── ollama_feedback_embeddings.py    # FeedbackEmbedding 모델 코드 생성
├── ollama_reference_embeddings.py    # ReferenceEmbedding 모델 코드 생성
├── ollama_submission_embeddings.py  # SubmissionEmbedding 모델 코드 생성
└── ollama_reasoning_embeddings.py   # ReasoningEmbedding 모델 코드 생성
```

#### 3.2.2 작동 방식

1. **기존 모델 파일 읽기**: `models/bases/feedback.py` 등
2. **프롬프트 구성**: 기존 모델 코드 + Alembic 스키마 참고하여 SQLAlchemy ORM 코드 생성 요청
3. **ExaOne 모델 로드**: `core/ml/model_loader.py` 사용 또는 직접 로드
4. **코드 생성**: Chat template 사용하여 코드 생성
5. **코드 추출 및 저장**: `models/bases/feedback_embeddings.py` 등에 저장

#### 3.2.3 결정 필요 사항

**Q4. ExaOne 모델 경로**
- **현재**: `core/ml/model_loader.py`에서 `artifacts/models/base/exaone-2.4b` 사용
- **강사님**: `artifacts/base-models/exaone-2.4b`
- **결정 필요**: 경로 통일 또는 환경 변수로 설정 가능하게?

**Q5. 코드 생성 스크립트 실행 방식**
- **옵션 A**: 독립 실행 (각 스크립트 직접 실행)
- **옵션 B**: 통합 스크립트 (모든 임베딩 모델 한 번에 생성)
- **추천**: **옵션 A**. 필요할 때만 선택적으로 생성.

**Q6. 생성된 코드 검증**
- **옵션 A**: 자동 검증 없음 (수동 확인)
- **옵션 B**: SQLAlchemy 문법 검증, import 확인 등
- **추천**: **옵션 A + B (선택)**. 기본은 수동 확인, 필요 시 검증 로직 추가.

---

### 3.3 Orchestrator 확장 (`hub/orchestrators/`)

**역할**: 임베딩 마이그레이션 트리거, MCP 서버 툴 호출.

#### 3.3.1 구조 설계

**기존 Orchestrator 유지:**
- `minso_hub.py` - 중앙 허브 (정책/규칙 판단)
- `reasoning_orchestrator.py` - 정책 처리

**새로 추가/확장:**
- 각 Orchestrator에 `trigger_embedding_migration()` 메서드 추가
- 또는 별도 `embedding_orchestrator.py` 생성

#### 3.3.2 임베딩 마이그레이션 흐름

```python
async def trigger_embedding_migration(self) -> Dict[str, Any]:
    """
    1. 데이터 조회 (예: 모든 Feedback 조회)
    2. 텍스트 조합 (content, summary 등)
    3. MCP 서버 툴 호출 (koelectra_embed_text)
    4. DB 저장 (*_embeddings 테이블)
    """
```

#### 3.3.3 LangGraph 사용 여부

**현재**: LangGraph 없음 (MinsoHub는 직접 분기)

**강사님 구조**: LangGraph StateGraph 사용
```
START → validate → determine_strategy → [policy_process | rule_process] → finalize → END
```

**결정 필요:**
- **Q7. LangGraph 도입 여부**
  - **옵션 A**: LangGraph 도입 (강사님 구조와 동일)
  - **옵션 B**: 현재 구조 유지 (MinsoHub 직접 분기)
  - **추천**: **옵션 B (현재 유지)**. 임베딩 마이그레이션은 단순 워크플로우이므로 LangGraph 불필요할 수 있음.
    다만, 나중에 복잡한 워크플로우가 필요하면 LangGraph 도입 고려.

---

### 3.4 API Router 확장 (`app/api/v1/minso/`)

**역할**: HTTP 엔드포인트로 임베딩 작업 트리거.

#### 3.4.1 엔드포인트 설계

**MCP 기반 임베딩 (경로 1):**
```
GET /api/v1/minso/feedback/embedding
GET /api/v1/minso/reference/embedding
GET /api/v1/minso/submission/embedding
GET /api/v1/minso/reasoning/embedding
```

**로컬 임베딩 (경로 2, 선택):**
```
POST /api/v1/minso/feedback/embedding/index
POST /api/v1/minso/reference/embedding/index
...
```

#### 3.4.2 백그라운드 작업 처리

**강사님 구조**: Redis를 통한 백그라운드 작업

**현재 프로젝트**: Redis 없음

**결정 필요:**
- **Q8. 백그라운드 작업 처리 방식**
  - **옵션 A**: Redis 도입 (강사님 구조와 동일)
  - **옵션 B**: FastAPI BackgroundTasks 사용 (Redis 없이)
  - **옵션 C**: 동기 처리 (작은 데이터셋)
  - **추천**: **옵션 B (BackgroundTasks)**. Redis 없이도 가능. 필요 시 나중에 Redis 추가.

---

### 3.5 KoELECTRA 임베딩 기능 확장 (`core/ml/koelectra_loader.py`)

**현재**: 정책/규칙 판단만 (`predict()` 메서드)

**필요**: 임베딩 생성 기능 추가

#### 3.5.1 확장 방안

**옵션 A**: `KoELECTRALoader`에 `embed_text()` 메서드 추가
```python
def embed_text(self, text: str) -> List[float]:
    """텍스트를 768차원 벡터로 변환"""
    # last_hidden_state[:, 0, :] 사용
```

**옵션 B**: 별도 `KoELECTRAEmbedder` 클래스 생성 (`core/ml/embeddings.py`)

**추천**: **옵션 A**. 기존 로더에 기능 추가가 자연스러움.

#### 3.5.2 결정 필요 사항

**Q9. KoELECTRA 임베딩 기능 위치**
- **옵션 A**: `core/ml/koelectra_loader.py`에 `embed_text()` 추가
- **옵션 B**: `core/ml/embeddings.py`에 별도 클래스
- **추천**: **옵션 A**. KoELECTRA 로더에 임베딩 기능 추가.

---

### 3.6 임베딩 모델 (`models/bases/*_embeddings.py`)

**현재**: 파일만 있고 비어있음

**필요**: SQLAlchemy ORM 모델 코드

#### 3.6.1 모델 구조 (강사님 구조 참고)

```python
class FeedbackEmbedding(Base, TimestampMixin):
    """피드백 임베딩"""
    __tablename__ = "feedback_embeddings"

    id = Column(BigInteger, primary_key=True)
    feedback_id = Column(String(36), ForeignKey("feedbacks.id"), nullable=False)
    content = Column(Text, nullable=False)  # 임베딩할 텍스트
    embedding = Column(VECTOR(768), nullable=False)  # pgvector
    created_at = Column(DateTime, ...)
```

#### 3.6.2 결정 필요 사항

**Q10. 임베딩 모델 생성 방식**
- **옵션 A**: 코드 생성 스크립트로 자동 생성 (강사님 구조)
- **옵션 B**: 수동 작성
- **추천**: **옵션 A**. ExaOne으로 자동 생성하는 것이 강사님 구조와 일치.

**Q11. pgvector 사용 여부**
- **현재**: requirements.txt에 `pgvector` 있음
- **필요**: VECTOR(768) 타입 사용
- **결정 필요**: pgvector 확장 설치 및 Alembic 마이그레이션 필요.

---

## 4. 전체 워크플로우 설계

### 4.1 코드 생성 워크플로우 (수동 실행)

```
1. 스크립트 실행
   python app/alter_ollama/ollama_feedback_embeddings.py

2. ExaOne 모델 로드
   core/ml/model_loader.py 또는 직접 로드

3. 프롬프트 구성
   - 기존 models/bases/feedback.py 읽기
   - Alembic 스키마 참고
   - SQLAlchemy ORM 코드 생성 요청

4. 코드 생성
   ExaOne Chat template 사용

5. 코드 저장
   models/bases/feedback_embeddings.py

6. Alembic 마이그레이션
   alembic revision --autogenerate
   alembic upgrade head
```

### 4.2 런타임 자동화 워크플로우 (API 호출)

```
1. API 요청
   GET /api/v1/minso/feedback/embedding

2. Router 처리
   app/api/v1/minso/feedback.py
   - BackgroundTasks 또는 동기 처리
   - Orchestrator 호출

3. Orchestrator 실행
   hub/orchestrators/feedback_orchestrator.py (또는 기존 orchestrator 확장)
   - trigger_embedding_migration() 호출
   - 데이터 조회 (모든 Feedback)
   - 텍스트 조합

4. MCP 서버 툴 호출
   hub/mcp_central/central_mcp_server.py
   - koelectra_embed_text(text=content) 호출
   - KoELECTRA 모델로 768차원 벡터 생성

5. DB 저장
   FeedbackEmbedding 테이블에 저장
   - feedback_id, content, embedding, created_at

6. 응답 반환
   처리 완료 상태 및 통계 정보
```

---

## 5. 단계별 구현 전략

### Phase 1: 기반 구축 (필수)

**목표**: 코드 생성 스크립트 + 중앙 MCP 서버 기본 구조

1. **코드 생성 스크립트** (`app/alter_ollama/`)
   - `ollama_feedback_embeddings.py` 생성
   - ExaOne 모델 로드 (core/ml/model_loader.py 사용 또는 직접)
   - 프롬프트 구성 로직
   - 코드 생성 및 저장

2. **중앙 MCP 서버** (`hub/mcp_central/central_mcp_server.py`)
   - FastMCP 서버 기본 구조
   - 싱글톤 패턴
   - ExaOne 툴 1개 (`exaone_generate_code`) 등록
   - KoELECTRA 툴 1개 (`koelectra_embed_text`) 등록

3. **KoELECTRA 임베딩 기능** (`core/ml/koelectra_loader.py`)
   - `embed_text()` 메서드 추가
   - 768차원 벡터 생성 로직

**결정 필요**: Q1, Q2, Q3, Q4, Q5, Q6, Q9

---

### Phase 2: 임베딩 모델 생성 (필수)

**목표**: 임베딩 모델 코드 생성 및 DB 스키마 생성

1. **코드 생성 실행**
   - 4개 스크립트 실행 (feedback, reference, submission, reasoning)
   - 생성된 코드 검증 및 수정

2. **Alembic 마이그레이션**
   - `*_embeddings` 테이블 생성
   - pgvector 확장 설치 확인

**결정 필요**: Q10, Q11

---

### Phase 3: Orchestrator 확장 (필수)

**목표**: 임베딩 마이그레이션 트리거 기능

1. **Orchestrator 메서드 추가**
   - `trigger_embedding_migration()` 구현
   - 데이터 조회 로직
   - 텍스트 조합 로직
   - MCP 서버 툴 호출
   - DB 저장 로직

2. **MCP 서버 연동**
   - Orchestrator에서 중앙 MCP 서버 호출
   - `koelectra_embed_text` 툴 사용

**결정 필요**: Q7

---

### Phase 4: API Router 확장 (필수)

**목표**: HTTP 엔드포인트로 임베딩 트리거

1. **엔드포인트 추가**
   - `GET /api/v1/minso/{domain}/embedding` 엔드포인트
   - Orchestrator 호출

2. **백그라운드 처리**
   - BackgroundTasks 또는 동기 처리

**결정 필요**: Q8

---

### Phase 5: 고급 기능 (선택)

**목표**: ExaOne 분석 툴, 통합 파이프라인 등

1. **ExaOne 분석 툴 추가**
   - `exaone_analyze_*_data` 툴들
   - 데이터 분석 및 변환

2. **통합 파이프라인**
   - `koelectra_to_exaone_pipeline` 툴

---

## 6. 결정 필요 사항 요약

| 번호 | 항목 | 옵션 | 추천 |
|------|------|------|------|
| **Q1** | 중앙 MCP 서버 위치 | A) hub/mcp_central/ | B) hub/mcp/ | **A** |
| **Q2** | 모델 로딩 방식 | A) 중앙 서버 직접 로드 | B) core/ml 로더 사용 | **B** |
| **Q3** | FastMCP vs MCPTransport | A) FastMCP 서버 추가 | B) transport 확장 | **A** |
| **Q4** | ExaOne 모델 경로 | 통일 또는 환경 변수 | **환경 변수** |
| **Q5** | 코드 생성 실행 방식 | A) 독립 실행 | B) 통합 스크립트 | **A** |
| **Q6** | 생성된 코드 검증 | A) 수동 | B) 자동 검증 | **A (필요 시 B)** |
| **Q7** | LangGraph 도입 여부 | A) 도입 | B) 현재 구조 유지 | **B (필요 시 A)** |
| **Q8** | 백그라운드 작업 | A) Redis | B) BackgroundTasks | C) 동기 | **B** |
| **Q9** | KoELECTRA 임베딩 위치 | A) koelectra_loader.py | B) embeddings.py | **A** |
| **Q10** | 임베딩 모델 생성 | A) 코드 생성 | B) 수동 | **A** |
| **Q11** | pgvector 사용 | 설치 및 마이그레이션 필요 | **필수** |

---

## 7. 파일 구조 최종 설계

### 7.1 새로 생성할 파일

```
app/
├── alter_ollama/                          # ← 새 폴더
│   ├── ollama_feedback_embeddings.py
│   ├── ollama_reference_embeddings.py
│   ├── ollama_submission_embeddings.py
│   └── ollama_reasoning_embeddings.py
│
app/domain/v1/minso/
├── hub/
│   ├── mcp_central/
│   │   └── central_mcp_server.py         # ← 새 파일
│   └── orchestrators/
│       └── (기존 파일에 메서드 추가 또는 새 파일)
│
app/core/ml/
└── koelectra_loader.py                   # ← embed_text() 메서드 추가
```

### 7.2 수정할 파일

```
app/domain/v1/minso/models/bases/
├── feedback_embeddings.py                # ← 코드 생성으로 채움
├── reference_embeddings.py                # ← 코드 생성으로 채움
├── submission_embeddings.py               # ← 코드 생성으로 채움
└── reasoning_embeddings.py                # ← 코드 생성으로 채움

app/api/v1/minso/
├── feedback.py                            # ← embedding 엔드포인트 추가
├── reference.py                           # ← embedding 엔드포인트 추가
├── submission.py                          # ← embedding 엔드포인트 추가
└── reasoning.py                           # ← embedding 엔드포인트 추가
```

---

## 8. 다음 단계

1. **Q1~Q11 결정**: 위 결정 사항에 대한 선택
2. **Phase 1 시작**: 코드 생성 스크립트 + 중앙 MCP 서버 기본 구조
3. **단계별 구현**: Phase 1 → 2 → 3 → 4 → 5 순서로 진행

---

## 9. 참고 사항

- **강사님 구조**: `app/domain/v10/soccer/` 기준이지만, 우리는 `app/domain/v1/minso/` 기준으로 적용
- **주제 차이**: soccer(선수/팀/경기장/일정) vs minso(피드백/참조/제출/추론)
- **구조/흐름/기능**만 중점적으로 파악하여 적용
- **core/ml**: ExaOne/KoELECTRA 로더는 core에 유지, domain은 사용만

이 전략 문서는 **구조/흐름/기능** 중심으로 작성되었으며, 세부 구현은 Q1~Q11 결정 후 진행합니다.
