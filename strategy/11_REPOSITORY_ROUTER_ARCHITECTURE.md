# 🏗️ Repository 및 Router 패턴 아키텍처

## 📁 수정된 폴더 구조

```
app/
├── models/                    # 모델 레이어
│   ├── __init__.py
│   ├── base.py               # 추상 인터페이스 (BaseLLM, BaseEmbeddings)
│   ├── factory.py            # 모델 팩토리 (의존성 주입)
│   ├── midm/                 # 로컬 Llama 모델 파일
│   │   ├── config.json
│   │   ├── model.safetensors
│   │   ├── tokenizer.json
│   │   └── ...
│   └── providers/            # 모델 제공자 구현
│       ├── __init__.py
│       ├── openai_provider.py    # OpenAI 모델 구현
│       ├── custom_provider.py    # 커스텀 모델 직접 주입용
│       └── local_llama_provider.py  # 로컬 Llama 모델 (NEW)
│
├── repository/               # 데이터 접근 레이어 (Repository Pattern)
│   ├── __init__.py
│   ├── base.py              # 추상 Repository 인터페이스
│   └── vector_store_repository.py  # PGVector 접근 구현
│
├── services/                 # 비즈니스 로직 레이어
│   ├── __init__.py
│   ├── rag_service.py       # RAG 서비스
│   └── chat_service.py      # 채팅 서비스
│
├── router/                   # API 라우팅 레이어 (세분화)
│   ├── __init__.py
│   ├── chat_router.py       # 채팅 관련 엔드포인트
│   ├── health_router.py     # 헬스체크 엔드포인트
│   └── model_router.py      # 모델 관리 엔드포인트 (선택사항)
│
├── api/                      # API 레이어 (기존, 통합 관리)
│   ├── __init__.py
│   ├── routes.py            # 모든 라우터 통합
│   └── dependencies.py      # FastAPI 의존성 주입
│
├── config/                   # 설정 레이어
│   ├── __init__.py
│   └── settings.py          # 환경 변수 및 설정 관리
│
├── api_server.py            # 기존 API 서버 (레거시)
└── api_server_refactored.py # 리팩토링된 API 서버
```

## 🔄 수정된 의존성 주입 흐름

```
FastAPI App
    ↓
Router (router/)
    ↓ (의존성 주입)
Dependencies (api/dependencies.py)
    ↓
Services (services/)
    ↓
Repository (repository/) + Models (models/)
```

## 📦 새로 추가된 레이어

### 1. Repository 레이어 (`app/repository/`)

**목적**: 데이터베이스 접근을 추상화하여 비즈니스 로직과 분리

**장점**:
- 벡터 스토어 교체 시 서비스 레이어 수정 불필요
- 테스트 용이 (Mock Repository 사용 가능)
- 복잡한 쿼리 로직을 한 곳에서 관리

**구조**:
```python
# repository/base.py
class BaseVectorRepository(ABC):
    @abstractmethod
    def search(self, query: str, k: int) -> List[Document]:
        pass

    @abstractmethod
    def add_documents(self, documents: List[Document]) -> List[str]:
        pass

# repository/vector_store_repository.py
class PGVectorRepository(BaseVectorRepository):
    def __init__(self, vector_store: PGVector):
        self.vector_store = vector_store

    def search(self, query: str, k: int) -> List[Document]:
        return self.vector_store.similarity_search(query, k=k)
```

### 2. Router 레이어 (`app/router/`)

**목적**: API 엔드포인트를 기능별로 세분화

**장점**:
- 코드 가독성 향상
- 관심사 분리 (채팅, 헬스체크, 모델 관리 등)
- 팀 협업 시 충돌 최소화

**구조**:
```python
# router/chat_router.py
chat_router = APIRouter(prefix="/api/chat", tags=["chat"])

@chat_router.post("/rag")
async def chat_rag(...):
    ...

# router/health_router.py
health_router = APIRouter(tags=["health"])

@health_router.get("/health")
async def health_check():
    ...
```

### 3. 로컬 Llama 모델 지원 (`app/models/midm/`)

**목적**: `models/midm/` 폴더의 로컬 Llama 모델 활용

**구현 방법**:
- `models/providers/local_llama_provider.py` 추가
- HuggingFace Transformers 또는 llama.cpp 사용
- 환경 변수로 제어: `LLM_PROVIDER=local_llama`

## 🎯 수정된 모델 주입 방법

### 방법 1: 환경 변수로 제어 (권장)

```bash
# OpenAI 사용
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key

# 로컬 Llama 모델 사용
LLM_PROVIDER=local_llama
LOCAL_MODEL_PATH=app/models/midm
LOCAL_MODEL_DEVICE=cpu  # 또는 cuda
```

### 방법 2: 커스텀 모델 직접 주입

```python
# app/api/dependencies.py
from transformers import AutoModelForCausalLM, AutoTokenizer
from langchain_huggingface import HuggingFacePipeline

def get_llm() -> BaseLLM:
    model = AutoModelForCausalLM.from_pretrained("app/models/midm")
    tokenizer = AutoTokenizer.from_pretrained("app/models/midm")
    pipeline = HuggingFacePipeline(model=model, tokenizer=tokenizer)

    return CustomLLM(model=pipeline, model_name="local-llama")
```

## 📋 구현 권장 순서

### Phase 1: Repository 레이어 추가 ✅

1. `repository/base.py` - 추상 인터페이스
2. `repository/vector_store_repository.py` - PGVector 구현
3. `services/rag_service.py` 수정 - Repository 사용

### Phase 2: Router 세분화 ✅

1. `router/chat_router.py` - 채팅 엔드포인트
2. `router/health_router.py` - 헬스체크
3. `api/routes.py` 또는 `api_server_refactored.py` - 라우터 통합

### Phase 3: 로컬 Llama 모델 지원 ✅

1. `models/providers/local_llama_provider.py` - Llama 모델 로더
2. `models/factory.py` 수정 - `local_llama` 제공자 추가
3. 환경 변수 설정 추가

## 🔧 Repository vs Direct Access

### 기존 방식 (Direct Access)
```python
# services/rag_service.py
class RAGService:
    def __init__(self, vector_store: PGVector):
        self.vector_store = vector_store  # 직접 접근

    def search(self, query: str):
        return self.vector_store.similarity_search(query)
```

### 개선 방식 (Repository Pattern)
```python
# services/rag_service.py
class RAGService:
    def __init__(self, repository: BaseVectorRepository):
        self.repository = repository  # 추상화된 접근

    def search(self, query: str):
        return self.repository.search(query)
```

**장점**:
- PGVector → Chroma → FAISS로 교체 시 서비스 코드 변경 불필요
- 테스트 시 Mock Repository 사용 가능
- 복잡한 쿼리 로직을 Repository에서 관리

## 🎨 Router vs API

### 기존 구조 (api/)
```python
# api/routes.py - 모든 엔드포인트가 한 파일에
router = APIRouter()

@router.get("/health")
@router.post("/api/chat/rag")
@router.post("/api/chat/general")
# ... 모든 엔드포인트
```

### 개선 구조 (router/)
```python
# router/chat_router.py
chat_router = APIRouter(prefix="/api/chat", tags=["chat"])

@chat_router.post("/rag")
@chat_router.post("/general")

# router/health_router.py
health_router = APIRouter(tags=["health"])

@health_router.get("/health")

# api_server_refactored.py
app.include_router(chat_router)
app.include_router(health_router)
```

**장점**:
- 코드가 기능별로 분리되어 관리 용이
- API 문서가 태그별로 그룹화
- 대규모 프로젝트에서 팀 협업 용이

## 🚀 다음 단계 (권장사항)

1. **Repository 레이어 구현**
   - PGVector 접근을 Repository 패턴으로 래핑
   - 테스트 용이성 향상

2. **Router 세분화**
   - `api/routes.py`를 기능별로 분리
   - `router/chat_router.py`, `router/health_router.py` 등

3. **로컬 Llama 모델 지원**
   - `models/midm/` 폴더의 모델을 로드하는 Provider 추가
   - 환경 변수로 OpenAI ↔ Local 모델 전환 가능

4. **의존성 주입 개선**
   - Repository 의존성 추가
   - 라우터별 의존성 분리

## ✅ 최종 아키텍처 흐름

```
사용자 요청
    ↓
FastAPI App
    ↓
Router (기능별 분리)
    ↓
API Dependencies (의존성 주입)
    ↓
Service Layer (비즈니스 로직)
    ↓
Repository Layer (데이터 접근 추상화)
    ↓
Models + Vector Store (실제 데이터)
```

이 구조는:
- **유지보수 용이**: 각 레이어가 독립적
- **테스트 용이**: Mock 객체로 각 레이어 테스트
- **확장 가능**: 새로운 기능 추가 시 기존 코드 수정 최소화
- **유연성**: 모델, DB를 쉽게 교체 가능

