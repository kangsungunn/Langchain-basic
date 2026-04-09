# ExaOne MCP 자동화 구조 문서

## 📋 개요

이 문서는 프로젝트에서 ExaOne 모델을 활용한 MCP(Model Context Protocol) 기반 자동 임베딩 생성 시스템의 구조와 작동 방식을 설명합니다.

## 🏗️ 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    자동화 시스템 구조                          │
└─────────────────────────────────────────────────────────────┘

1. 코드 생성 단계 (app/alter_ollama/)
   ┌─────────────────────────────────────┐
   │  ExaOne 모델로 SQLAlchemy ORM 코드 생성 │
   │  - ollama_player_embeddings.py      │
   │  - ollama_team_embeddings.py        │
   │  - ollama_stadium_embeddings.py     │
   │  - ollama_schedule_embeddings.py    │
   └─────────────────────────────────────┘
                    ↓
   [생성된 임베딩 모델 파일]
   - app/domain/v10/soccer/models/bases/
     * player_embeddings.py
     * team_embeddings.py
     * stadium_embeddings.py
     * schedule_embeddings.py

2. 런타임 자동화 단계 (MCP 기반)
   ┌─────────────────────────────────────┐
   │  API 요청 (GET /api/v10/soccer/.../embedding) │
   └─────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────┐
   │  Router (app/api/v10/soccer/*_router.py) │
   │  - Redis 작업 등록                   │
   │  - 백그라운드 태스크 트리거           │
   └─────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────┐
   │  Orchestrator                        │
   │  (app/domain/v10/soccer/hub/orchestrators/) │
   │  - PlayerOrchestrator                │
   │  - TeamOrchestrator                  │
   │  - StadiumOrchestrator               │
   │  - ScheduleOrchestrator               │
   └─────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────┐
   │  중앙 MCP 서버                       │
   │  (app/domain/v10/soccer/hub/mcp/    │
   │   central_mcp_server.py)             │
   │  - ExaOne 툴: exaone_generate_code   │
   │  - KoELECTRA 툴: koelectra_embed_text│
   └─────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────┐
   │  임베딩 생성 및 DB 저장              │
   │  - KoELECTRA로 벡터 생성             │
   │  - *_embeddings 테이블에 저장        │
   └─────────────────────────────────────┘
```

## 📁 주요 폴더 및 파일 구조

### 1. 코드 생성 스크립트 (`app/alter_ollama/`)

이 폴더는 **ExaOne 모델을 사용하여 SQLAlchemy ORM 임베딩 모델 코드를 자동 생성**하는 독립적인 스크립트들을 포함합니다.

#### 파일 목록
- `ollama_player_embeddings.py` - PlayerEmbedding 모델 코드 생성
- `ollama_team_embeddings.py` - TeamEmbedding 모델 코드 생성
- `ollama_stadium_embeddings.py` - StadiumEmbedding 모델 코드 생성
- `ollama_schedule_embeddings.py` - ScheduleEmbedding 모델 코드 생성

#### 작동 방식
각 스크립트는 다음과 같은 프로세스를 따릅니다:

1. **기존 모델 파일 읽기**
   ```python
   # 예: players.py 파일 읽기
   players_file = Path("app/domain/v10/soccer/models/bases/players.py")
   players_content = players_file.read_text(encoding="utf-8")
   ```

2. **프롬프트 구성**
   - 기존 모델 코드와 Alembic 마이그레이션 스키마를 참고하여 프롬프트 작성
   - SQLAlchemy ORM 코드 생성 요구사항 포함

3. **ExaOne 모델 로드 및 코드 생성**
   ```python
   model_path = "artifacts/base-models/exaone-2.4b"
   tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
   model = AutoModelForCausalLM.from_pretrained(model_path, ...)
   
   # Chat template 사용
   messages = [
       {"role": "system", "content": "You are EXAONE..."},
       {"role": "user", "content": prompt}
   ]
   outputs = model.generate(...)
   ```

4. **생성된 코드 추출 및 저장**
   - 생성된 텍스트에서 코드 부분만 추출
   - `app/domain/v10/soccer/models/bases/` 경로에 저장

#### 실행 방법
```bash
# 각 스크립트를 직접 실행
python app/alter_ollama/ollama_player_embeddings.py
python app/alter_ollama/ollama_team_embeddings.py
python app/alter_ollama/ollama_stadium_embeddings.py
python app/alter_ollama/ollama_schedule_embeddings.py
```

#### 주의사항
- 이 스크립트들은 **모델 코드 생성**을 위한 것이며, 실제 임베딩 데이터 생성과는 별개입니다.
- 생성된 코드는 Alembic 마이그레이션과 함께 사용되어 데이터베이스 스키마를 생성합니다.

---

### 2. 중앙 MCP 서버 (`app/domain/v10/soccer/hub/mcp/central_mcp_server.py`)

중앙 MCP 서버는 **ExaOne과 KoELECTRA 모델을 관리하고, MCP 툴로 제공**하는 핵심 컴포넌트입니다.

#### 주요 기능

##### 2.1 ExaOne 툴 제공
- `exaone_generate_text` - 텍스트 생성
- `exaone_generate_code` - 코드 생성 (일반적인 코드 생성용)
- `exaone_analyze_player_data` - 선수 데이터 분석
- `exaone_analyze_team_data` - 팀 데이터 분석
- `exaone_analyze_schedule_data` - 경기 일정 데이터 분석
- `exaone_analyze_stadium_data` - 경기장 데이터 분석

##### 2.2 KoELECTRA 툴 제공
- `koelectra_embed_text` - 텍스트 임베딩 생성 (768차원 벡터)
- `koelectra_classify_text` - 텍스트 분류

##### 2.3 통합 파이프라인
- `koelectra_to_exaone_pipeline` - KoELECTRA 임베딩 생성 후 ExaOne으로 분석

#### 모델 로딩 방식
- **지연 로딩 (Lazy Loading)**: 모델은 필요할 때만 로드됩니다.
- **싱글톤 패턴**: 서버 인스턴스는 싱글톤으로 관리되어 메모리 효율성을 높입니다.

```python
class SoccerCentralMCPServer:
    _instance: Optional["SoccerCentralMCPServer"] = None
    
    def _load_exaone_model(self):
        """ExaOne 모델을 로드합니다 (지연 로딩)."""
        if self.exaone_llm is None:
            # 모델 로드 로직
            ...
```

#### 툴 호출 방법
```python
from app.domain.v10.soccer.hub.mcp import get_soccer_central_mcp_server

# 중앙 MCP 서버 가져오기
central_mcp = get_soccer_central_mcp_server()

# 툴 호출
result = await central_mcp.call_tool("koelectra_embed_text", text="임베딩할 텍스트")
```

---

### 3. Orchestrator (`app/domain/v10/soccer/hub/orchestrators/`)

Orchestrator는 **LangGraph StateGraph를 사용하여 데이터 처리 워크플로우를 관리**합니다.

#### 파일 목록
- `player_orchestrator.py` - 선수 데이터 처리
- `team_orchestrator.py` - 팀 데이터 처리
- `stadium_orchestrator.py` - 경기장 데이터 처리
- `schedule_orchestrator.py` - 경기 일정 데이터 처리
- `chat_orchestrator.py` - 채팅 처리

#### 주요 메서드

##### 3.1 임베딩 마이그레이션 트리거
```python
async def trigger_embedding_migration(self) -> Dict[str, Any]:
    """임베딩 마이그레이션을 트리거합니다."""
    # 1. 데이터 조회
    # 2. 텍스트 조합
    # 3. MCP 서버 툴 호출 (koelectra_embed_text)
    # 4. DB 저장
```

##### 3.2 LangGraph 워크플로우
각 Orchestrator는 다음과 같은 노드 구조를 가집니다:

```
START → validate → determine_strategy → [policy_process | rule_process] → finalize → END
```

- **validate**: 데이터 검증
- **determine_strategy**: 정책 기반 vs 규칙 기반 판단
- **policy_process**: MCP 서버를 통한 정책 기반 처리 (ExaOne 사용)
- **rule_process**: 규칙 기반 처리 (직접 처리)
- **finalize**: 최종 결과 정리

#### 중앙 MCP 서버 연동
```python
class PlayerOrchestrator:
    def __init__(self):
        # 중앙 MCP 서버 연결
        self.central_mcp = get_soccer_central_mcp_server()
        self.mcp = self.central_mcp.get_mcp_server()
    
    async def _call_central_tool(self, tool_name: str, **kwargs):
        """중앙 MCP 서버의 툴을 호출합니다."""
        result = await self.central_mcp.call_tool(tool_name, **kwargs)
        return result
```

---

### 4. API 라우터 (`app/api/v10/soccer/`)

API 라우터는 **HTTP 엔드포인트를 통해 임베딩 작업을 트리거**합니다.

#### 주요 엔드포인트

##### 4.1 MCP 기반 임베딩 (경로 1)
```
GET /api/v10/soccer/player/embedding
GET /api/v10/soccer/team/embedding
GET /api/v10/soccer/stadium/embedding
GET /api/v10/soccer/schedule/embedding
```

**작동 흐름**:
1. API 요청 수신
2. Redis에 작업 등록
3. 백그라운드 태스크로 `_run_embedding_migration_async` 실행
4. Orchestrator의 `trigger_embedding_migration()` 호출
5. MCP 서버 툴 호출 → 임베딩 생성 → DB 저장

##### 4.2 로컬 임베딩 (경로 2)
```
POST /api/v10/soccer/player/embedding/index
POST /api/v10/soccer/team/embedding/index
...
```

**작동 흐름**:
1. API 요청 수신
2. Service의 `run_batch_indexing()` 호출
3. EmbeddingClient를 직접 사용 (MCP 미사용)
4. DB 저장

#### 관련 파일
- `player_router.py` - 선수 관련 API
- `team_router.py` - 팀 관련 API
- `stadium_router.py` - 경기장 관련 API
- `schedule_router.py` - 경기 일정 관련 API

---

## 🔄 자동화 워크플로우 상세

### 시나리오 1: 선수 임베딩 자동 생성

```
1. 클라이언트 요청
   GET /api/v10/soccer/player/embedding

2. Router 처리 (player_router.py)
   - Redis 작업 등록
   - 백그라운드 태스크 시작

3. Orchestrator 실행 (PlayerOrchestrator)
   - trigger_embedding_migration() 호출
   - 선수 데이터 조회
   - 텍스트 조합 (이름, 포지션, 팀 등)

4. MCP 서버 툴 호출
   - central_mcp.call_tool("koelectra_embed_text", text=content)
   - KoELECTRA 모델로 768차원 벡터 생성

5. DB 저장
   - PlayerEmbedding 테이블에 저장
   - player_id, content, embedding, created_at

6. 응답 반환
   - 처리 완료 상태 및 통계 정보
```

### 시나리오 2: 정책 기반 데이터 처리

```
1. Orchestrator의 determine_strategy 노드
   - 복잡도 분석
   - 정책 기반 vs 규칙 기반 판단

2. 정책 기반 처리 (policy_process 노드)
   - MCP 서버의 ExaOne 툴 호출
   - exaone_analyze_player_data() 등 사용
   - 데이터 분석 및 변환

3. 결과 저장 및 반환
```

---

## 🛠️ 핵심 컴포넌트 상세 설명

### 1. ExaOne 모델

#### 모델 경로
```
artifacts/base-models/exaone-2.4b
```

#### 사용 목적
1. **코드 생성**: SQLAlchemy ORM 모델 코드 자동 생성 (`app/alter_ollama/`)
2. **데이터 분석**: 선수/팀/경기장/일정 데이터 분석 (MCP 툴)
3. **텍스트 생성**: 일반적인 텍스트 생성 작업

#### 모델 로딩
- **중앙 MCP 서버**: `central_mcp_server.py`의 `_load_exaone_model()` 메서드
- **지연 로딩**: 필요할 때만 로드하여 메모리 효율성 향상
- **디바이스**: CUDA 사용 가능 시 GPU, 아니면 CPU

### 2. KoELECTRA 모델

#### 모델 경로
```
artifacts/models--monologg--koelectra-small-v3-discriminator
```

#### 사용 목적
- **임베딩 생성**: 텍스트를 768차원 벡터로 변환
- **텍스트 분류**: 분류 작업 수행

#### 임베딩 생성 프로세스
```python
# 1. 토크나이저로 텍스트 토큰화
inputs = tokenizer(text, return_tensors="pt", ...)

# 2. 모델에 통과
with torch.no_grad():
    outputs = model(**inputs)
    embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy().tolist()[0]

# 3. 768차원 벡터 반환
```

### 3. MCP (Model Context Protocol)

#### FastMCP 프레임워크 사용
- FastMCP를 사용하여 MCP 서버 구현
- 툴을 데코레이터로 등록: `@self.mcp.tool()`

#### 툴 등록 예시
```python
@self.mcp.tool()
def koelectra_embed_text(text: str) -> Dict[str, Any]:
    """KoELECTRA로 텍스트를 임베딩합니다."""
    # 구현 로직
    ...
```

---

## 📊 데이터베이스 스키마

### 임베딩 테이블 구조

모든 임베딩 테이블은 유사한 구조를 가집니다:

```sql
-- 예: player_embeddings 테이블
CREATE TABLE player_embeddings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    player_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);
```

### 관련 모델 파일
- `app/domain/v10/soccer/models/bases/player_embeddings.py`
- `app/domain/v10/soccer/models/bases/team_embeddings.py`
- `app/domain/v10/soccer/models/bases/stadium_embeddings.py`
- `app/domain/v10/soccer/models/bases/schedule_embeddings.py`

---

## 🔧 설정 및 의존성

### 필수 모델 파일
1. **ExaOne 모델**: `artifacts/base-models/exaone-2.4b`
2. **KoELECTRA 모델**: `artifacts/models--monologg--koelectra-small-v3-discriminator`

### 주요 라이브러리
- `transformers` - Hugging Face 모델 로딩
- `torch` - PyTorch (모델 실행)
- `fastmcp` - MCP 서버 구현
- `langgraph` - 워크플로우 관리
- `pgvector` - PostgreSQL 벡터 확장

### 환경 변수
- 데이터베이스 연결 정보
- Redis 연결 정보 (백그라운드 작업용)

---

## 🚀 사용 예시

### 1. 임베딩 모델 코드 생성

```bash
# 선수 임베딩 모델 코드 생성
python app/alter_ollama/ollama_player_embeddings.py

# 생성된 파일 확인
cat app/domain/v10/soccer/models/bases/player_embeddings.py
```

### 2. API를 통한 임베딩 생성

```bash
# 선수 임베딩 생성 트리거
curl -X GET http://localhost:8000/api/v10/soccer/player/embedding

# 배치 인덱싱 (MCP 미사용)
curl -X POST http://localhost:8000/api/v10/soccer/player/embedding/index
```

### 3. 프로그래밍 방식 호출

```python
from app.domain.v10.soccer.hub.orchestrators import PlayerOrchestrator

# Orchestrator 생성
orchestrator = PlayerOrchestrator()

# 임베딩 마이그레이션 실행
result = await orchestrator.trigger_embedding_migration()
print(result)
```

---

## 📝 주의사항 및 제한사항

### 1. 코드 생성 스크립트 (`app/alter_ollama/`)
- ⚠️ **독립 실행**: MCP 자동화 시스템과는 별개로 작동합니다.
- ⚠️ **수동 실행**: 필요할 때만 수동으로 실행하여 모델 코드를 생성합니다.
- ✅ **일회성 작업**: 새로운 임베딩 모델이 필요할 때만 실행합니다.

### 2. MCP 자동화 시스템
- ✅ **런타임 자동화**: API 호출 시 자동으로 임베딩 생성
- ✅ **백그라운드 처리**: Redis를 통한 비동기 작업 처리
- ✅ **확장 가능**: 새로운 엔티티 추가 시 Orchestrator와 Router만 추가하면 됨

### 3. 모델 로딩
- ⚠️ **메모리 사용량**: ExaOne과 KoELECTRA 모델은 상당한 메모리를 사용합니다.
- ✅ **지연 로딩**: 필요할 때만 로드하여 메모리 효율성 향상
- ✅ **싱글톤 패턴**: 중앙 MCP 서버는 싱글톤으로 관리

---

## 🔍 문제 해결

### 모델을 찾을 수 없는 경우
```python
# 모델 경로 확인
model_path = "artifacts/base-models/exaone-2.4b"
if not Path(model_path).exists():
    print(f"모델 경로를 확인하세요: {model_path}")
```

### MCP 툴 호출 실패
```python
# 중앙 MCP 서버 초기화 확인
central_mcp = get_soccer_central_mcp_server()
if central_mcp is None:
    print("중앙 MCP 서버 초기화 실패")
```

### 임베딩 생성 실패
- KoELECTRA 모델이 제대로 로드되었는지 확인
- CUDA 사용 가능 여부 확인 (GPU 메모리 부족 시 CPU 사용)

---

## 📚 관련 문서

- `docs/architecture/1.PROJECT_STRUCTURE_LEARNING.md` - 프로젝트 구조 전체 개요
- `docs/architecture/mcp_structure_analysis.md` - MCP 아키텍처 분석
- `md_files/mcp_wrapper_refactoring_summary.md` - MCP 리팩토링 요약

---

## 🎯 요약

### 두 가지 자동화 레벨

1. **코드 생성 자동화** (`app/alter_ollama/`)
   - ExaOne 모델로 SQLAlchemy ORM 코드 자동 생성
   - 수동 실행 필요
   - 모델 스키마 변경 시 사용

2. **런타임 자동화** (MCP 기반)
   - API 호출 시 자동으로 임베딩 생성
   - Orchestrator → MCP 서버 → KoELECTRA → DB 저장
   - 완전 자동화된 워크플로우

### 핵심 파일 위치

| 기능 | 파일 경로 |
|------|----------|
| 코드 생성 스크립트 | `app/alter_ollama/*.py` |
| 중앙 MCP 서버 | `app/domain/v10/soccer/hub/mcp/central_mcp_server.py` |
| Orchestrator | `app/domain/v10/soccer/hub/orchestrators/*.py` |
| API Router | `app/api/v10/soccer/*_router.py` |
| 임베딩 모델 | `app/domain/v10/soccer/models/bases/*_embeddings.py` |

---

*문서 작성일: 2026-02-05*
*프로젝트: hague-app-v6-main*
