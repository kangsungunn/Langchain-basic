# 🔧 RAG 노드 OpenAI API 키 오류 수정 요약

## 문제 원인

LangGraph 모드에서 Exaone 모델을 사용하도록 설정했지만, RAG 노드에서 문서 검색을 위해 `get_rag_service()`를 호출할 때:
- `get_rag_service()` → `get_embeddings()` → `ModelFactory.create_embeddings()`
- 기본값이 `"openai"`이므로 OpenAI 임베딩을 사용하려고 시도
- `OPENAI_API_KEY`가 없어서 오류 발생

## 해결 방법

### 1. RAG 노드 수정 (`app/graph.py`)
- `get_rag_service()` 대신 `get_vector_store()`를 직접 사용
- 벡터 스토어 초기화 실패 시 에러 처리 추가
- 임베딩 모델 초기화 실패 시에도 일반 대화로 진행 가능하도록 수정

### 2. HuggingFace 임베딩 지원 추가 (`app/models/factory.py`)
- `EMBEDDINGS_PROVIDER=huggingface` 옵션 추가
- 로컬 HuggingFace 임베딩 모델 사용 가능 (API 키 불필요)
- 기본 모델: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (한국어 지원)

## 사용 방법

### 옵션 1: HuggingFace 로컬 임베딩 사용 (권장)

```bash
export EMBEDDINGS_PROVIDER=huggingface
export HUGGINGFACE_EMBEDDINGS_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

필요한 패키지 설치:
```bash
pip install sentence-transformers
```

### 옵션 2: OpenAI 임베딩 사용

```bash
export EMBEDDINGS_PROVIDER=openai
export OPENAI_API_KEY=sk-...
```

### 옵션 3: 커스텀 임베딩 사용

```bash
export EMBEDDINGS_PROVIDER=custom
# 코드에서 직접 임베딩 모델 주입 필요
```

## 변경 사항

1. **`app/graph.py`**:
   - RAG 노드에서 벡터 스토어 직접 사용
   - 임베딩 모델 초기화 실패 시 에러 처리 개선
   - 주석 수정: "MIDM 모델" → "Exaone 모델"

2. **`app/models/factory.py`**:
   - `huggingface` 프로바이더 추가
   - 로컬 HuggingFace 임베딩 모델 지원

## 주의사항

⚠️ **벡터 스토어 호환성**:
- 벡터 스토어는 이미 생성된 임베딩 모델을 사용합니다
- 임베딩 모델을 변경하면 기존 벡터와 호환되지 않을 수 있습니다
- 새로운 임베딩 모델 사용 시 벡터 스토어를 다시 생성해야 할 수 있습니다

## 테스트

1. 환경 변수 설정:
   ```bash
   export EMBEDDINGS_PROVIDER=huggingface
   ```

2. 서버 재시작:
   ```bash
   python -m uvicorn app.api_server_refactored:app --reload
   ```

3. 프론트엔드에서 LangGraph 모드 선택 후 테스트
