# 📊 아키텍처 빠른 참조

## 현재 폴더 구조

```
app/
├── models/                     # 모델 레이어
│   ├── base.py                # 추상 인터페이스
│   ├── factory.py             # 모델 팩토리
│   ├── midm/                  # 로컬 Llama 모델 파일 (1.2B)
│   └── providers/
│       ├── openai_provider.py      # OpenAI
│       ├── custom_provider.py      # 커스텀 주입
│       └── local_llama_provider.py # 로컬 Llama
│
├── repository/                 # Repository 패턴 (데이터 접근 추상화)
│   ├── base.py                # 추상 Repository
│   └── vector_store_repository.py  # PGVector 구현
│
├── services/                   # 비즈니스 로직
│   ├── rag_service.py         # RAG 로직
│   └── chat_service.py        # 채팅 로직
│
├── router/                     # API 라우팅 (기능별 분리)
│   ├── chat_router.py         # 채팅 엔드포인트
│   └── health_router.py       # 헬스체크
│
├── api/                        # API 레이어
│   ├── routes.py              # 라우터 통합 (레거시)
│   └── dependencies.py        # 의존성 주입
│
└── config/                     # 설정
    └── settings.py            # 환경 변수 관리
```

## 주요 변경사항

### 1. Repository 레이어 추가 ✅
- **목적**: 벡터 스토어 접근을 추상화
- **장점**:
  - 벡터 DB 교체 용이 (PGVector → Chroma → FAISS)
  - 테스트 용이 (Mock Repository)
  - 비즈니스 로직과 데이터 접근 분리

### 2. Router 레이어 추가 ✅
- **목적**: API 엔드포인트를 기능별로 세분화
- **장점**:
  - 코드 가독성 향상
  - 관심사 분리 (채팅/헬스체크/모델 관리)
  - 팀 협업 시 충돌 최소화

### 3. 로컬 Llama 모델 지원 ✅
- **위치**: `models/midm/` (LlamaForCausalLM 1.2B)
- **Provider**: `local_llama_provider.py`
- **사용법**:
  - 환경 변수: `LLM_PROVIDER=local_llama`
  - 또는 `dependencies.py`에서 직접 주입

## 의존성 흐름

```
사용자 요청
    ↓
FastAPI App
    ↓
Router (chat_router.py, health_router.py)
    ↓ Depends()
Dependencies (api/dependencies.py)
    ↓
Service Layer (rag_service.py, chat_service.py)
    ↓
Repository Layer (vector_store_repository.py)
    ↓
Models (OpenAI, Local Llama) + Vector Store
```

## 모델 주입 방법

### 환경 변수로 전환
```bash
# OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# 로컬 Llama
export LLM_PROVIDER=local_llama
export LOCAL_MODEL_PATH=app/models/midm
```

### 직접 주입 (app/api/dependencies.py)
```python
@lru_cache()
def get_llm() -> BaseLLM:
    # HuggingFace 모델 로드
    model = AutoModelForCausalLM.from_pretrained("app/models/midm")
    tokenizer = AutoTokenizer.from_pretrained("app/models/midm")

    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
    hf_pipeline = HuggingFacePipeline(pipeline=pipe)

    return CustomLLM(model=hf_pipeline, model_name="local-llama")
```

## 서버 실행

### 리팩토링된 서버 (권장)
```bash
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --reload
```

### 레거시 서버
```bash
uvicorn app.api_server:app --host 0.0.0.0 --port 8000 --reload
```

## 주요 문서

- `10_MODEL_INJECTION_ARCHITECTURE.md` - 기본 아키텍처
- `11_REPOSITORY_ROUTER_ARCHITECTURE.md` - Repository/Router 패턴
- `13_LOCAL_MIDM_MODEL_SETUP.md` - Midm 모델 설정
- `14_LOCAL_MODEL_IMPLEMENTATION.md` - 구현 가이드

## 다음 단계 (선택사항)

1. **로컬 Llama 모델 활성화**
   - `14_LOCAL_MODEL_IMPLEMENTATION.md` 참고
   - HuggingFace Transformers 또는 llama.cpp 사용

2. **Repository 패턴 적용**
   - `services/rag_service.py`에서 Repository 사용
   - 벡터 DB 교체 용이

3. **Router 세분화 확장**
   - `router/model_router.py` - 모델 관리 API
   - `router/document_router.py` - 문서 업로드/삭제

4. **테스트 코드 작성**
   - Repository Mock 사용
   - 각 레이어 단위 테스트

