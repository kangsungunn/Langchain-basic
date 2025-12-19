# 🏗️ 모델 주입 아키텍처

## 📁 폴더 구조

```
app/
├── models/                    # 모델 레이어
│   ├── __init__.py
│   ├── base.py               # 추상 인터페이스 (BaseLLM, BaseEmbeddings)
│   ├── factory.py            # 모델 팩토리 (의존성 주입)
│   └── providers/            # 모델 제공자 구현
│       ├── __init__.py
│       ├── openai_provider.py    # OpenAI 모델 구현
│       └── custom_provider.py    # 커스텀 모델 구현 (직접 주입용)
│
├── services/                 # 비즈니스 로직 레이어
│   ├── __init__.py
│   ├── rag_service.py       # RAG 서비스
│   └── chat_service.py      # 채팅 서비스
│
├── api/                      # API 레이어
│   ├── __init__.py
│   ├── routes.py            # API 엔드포인트 정의
│   └── dependencies.py      # FastAPI 의존성 주입
│
├── config/                   # 설정 레이어
│   ├── __init__.py
│   └── settings.py          # 환경 변수 및 설정 관리
│
├── api_server.py            # 기존 API 서버 (레거시)
├── api_server_refactored.py # 리팩토링된 API 서버
└── ...                      # 기타 스크립트들
```

## 🔄 의존성 주입 흐름

```
FastAPI App
    ↓
API Routes (routes.py)
    ↓ (의존성 주입)
Dependencies (dependencies.py)
    ↓
Services (rag_service.py, chat_service.py)
    ↓
Models (factory.py → providers/)
```

## 🎯 모델 주입 방법

### 방법 1: 환경 변수 사용 (기본)

```bash
# .env 파일 또는 환경 변수
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_key_here

EMBEDDINGS_PROVIDER=openai
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small
```

### 방법 2: 커스텀 모델 직접 주입

`app/api/dependencies.py`의 `get_llm()` 함수를 수정:

```python
from app.models.providers.custom_provider import CustomLLM
from langchain_ollama import ChatOllama  # 예시

def get_llm() -> BaseLLM:
    # 커스텀 모델 생성
    custom_model = ChatOllama(model="llama2")

    # CustomLLM으로 래핑
    return CustomLLM(model=custom_model, model_name="llama2")
```

### 방법 3: 팩토리 패턴 확장

새로운 제공자를 추가하려면:

1. `app/models/providers/`에 새 제공자 파일 생성
2. `BaseLLM` 또는 `BaseEmbeddings` 구현
3. `app/models/factory.py`의 `ModelFactory`에 추가

## 📝 주요 컴포넌트

### 1. Models (`app/models/`)

- **목적**: LLM과 Embeddings 모델의 추상화 및 관리
- **인터페이스**: `BaseLLM`, `BaseEmbeddings`
- **팩토리**: `ModelFactory` - 환경에 따라 적절한 모델 생성
- **제공자**: OpenAI, Custom 등 다양한 모델 지원

### 2. Services (`app/services/`)

- **RAGService**: RAG 로직 처리 (문서 검색, 답변 생성)
- **ChatService**: 채팅 비즈니스 로직 (RAG/일반 모드)

### 3. API (`app/api/`)

- **routes.py**: FastAPI 엔드포인트 정의
- **dependencies.py**: 의존성 주입 함수들

### 4. Config (`app/config/`)

- **settings.py**: 환경 변수 기반 설정 관리

## 🚀 사용 예시

### 리팩토링된 서버 실행

```bash
# api_server_refactored.py 사용
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --reload
```

### 커스텀 모델 주입 예시

```python
# app/api/dependencies.py 수정
from app.models.providers.custom_provider import CustomLLM
from your_custom_model import YourCustomModel

def get_llm() -> BaseLLM:
    custom_model = YourCustomModel(...)
    return CustomLLM(model=custom_model, model_name="your-model")
```

## 🔧 확장 가이드

### 새로운 모델 제공자 추가

1. `app/models/providers/your_provider.py` 생성
2. `BaseLLM` 또는 `BaseEmbeddings` 구현
3. `app/models/factory.py`의 `ModelFactory`에 추가

```python
# app/models/factory.py
elif provider.lower() == "your_provider":
    return YourProviderLLM(model_name=model_name, **kwargs)
```

## ✅ 장점

1. **관심사의 분리**: 각 레이어가 명확한 책임을 가짐
2. **의존성 주입**: 모델을 쉽게 교체 가능
3. **테스트 용이**: 각 컴포넌트를 독립적으로 테스트 가능
4. **확장성**: 새로운 모델 제공자를 쉽게 추가 가능
5. **유지보수성**: 코드 구조가 명확하고 이해하기 쉬움

