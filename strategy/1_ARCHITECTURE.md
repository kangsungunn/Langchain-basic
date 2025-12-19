# 🏗️ LangChain + PGVector 아키텍처 완벽 가이드

## 📊 전체 시스템 구조 도식화

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Compose 환경                          │
│                                                                      │
│  ┌────────────────────────┐        ┌──────────────────────────┐   │
│  │  langchain-app         │        │   langchain-pgvector     │   │
│  │  (Python Container)    │        │   (PostgreSQL + Vector)  │   │
│  │                        │        │                          │   │
│  │  ┌──────────────────┐ │        │  ┌────────────────────┐ │   │
│  │  │   app/main.py    │ │        │  │   PostgreSQL 16    │ │   │
│  │  │  또는 test_     │ │        │  │                    │ │   │
│  │  │  connection.py   │ │        │  │  ┌──────────────┐ │ │   │
│  │  └────────┬─────────┘ │        │  │  │  pgvector    │ │ │   │
│  │           │            │        │  │  │  확장 기능   │ │ │   │
│  │           │            │        │  │  └──────────────┘ │ │   │
│  │           ▼            │        │  │                    │ │   │
│  │  ┌──────────────────┐ │        │  │  ┌──────────────┐ │ │   │
│  │  │  LangChain Core  │ │        │  │  │   vectordb   │ │ │   │
│  │  │  - Documents     │ │        │  │  │   database   │ │ │   │
│  │  │  - Embeddings    │ │        │  │  └──────────────┘ │ │   │
│  │  └────────┬─────────┘ │        │  └────────────────────┘ │   │
│  │           │            │        │                          │   │
│  │           ▼            │        │                          │   │
│  │  ┌──────────────────┐ │  네트워크 │                          │   │
│  │  │ langchain-postgres│◄───────►│  Port 5432               │   │
│  │  │   (PGVector)     │ │ 연결    │                          │   │
│  │  └──────────────────┘ │        │                          │   │
│  │    - 벡터 저장       │        │                          │   │
│  │    - 유사도 검색     │        │                          │   │
│  └────────────────────────┘        └──────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   Docker Volume        │
                    │   pgvector_data        │
                    │   (영구 데이터 저장)   │
                    └────────────────────────┘
```

---

## 🔄 데이터 흐름 상세 분석

### 1️⃣ **문서 저장 흐름** (Write Operation)

```
[1] Python 코드에서 문서 생성
    ↓
    document = Document(
        page_content="LangChain은...",
        metadata={"topic": "intro"}
    )

[2] LangChain이 문서를 임베딩으로 변환
    ↓
    text = "LangChain은..."
    → embeddings.embed_documents([text])
    → vector = [0.1, 0.2, 0.3, ..., 0.384]  # 384차원 벡터

[3] PGVector가 PostgreSQL에 저장
    ↓
    INSERT INTO langchain_pg_embedding (
        collection_id,    -- 어느 컬렉션인지
        embedding,        -- [0.1, 0.2, ...] 벡터 데이터
        document,         -- "LangChain은..." 원본 텍스트
        cmetadata         -- {"topic": "intro"} 메타데이터
    )

[4] PostgreSQL이 디스크에 영구 저장
    ↓
    Docker Volume (pgvector_data)에 물리적으로 저장
```

---

### 2️⃣ **검색 흐름** (Search Operation)

```
[1] 사용자가 검색 쿼리 입력
    ↓
    query = "LangChain에 대해 알려줘"

[2] 쿼리를 벡터로 변환
    ↓
    query_vector = embeddings.embed_query(query)
    → [0.15, 0.25, 0.35, ..., 0.45]

[3] PostgreSQL에서 유사한 벡터 검색
    ↓
    SELECT
        document,
        cmetadata,
        embedding <=> %s as distance  -- 벡터 거리 계산
    FROM langchain_pg_embedding
    ORDER BY embedding <=> %s  -- 가장 가까운 순으로 정렬
    LIMIT 3

[4] 결과를 Python으로 반환
    ↓
    [
        Document("LangChain은...", metadata={...}),
        Document("PGVector는...", metadata={...}),
        ...
    ]
```

---

## 🧩 각 컴포넌트 상세 설명

### 🐍 **langchain-app 컨테이너**

**역할**: 애플리케이션 로직 실행

```python
# 이 컨테이너 안에서 실행되는 것들:

1. 문서 생성
   documents = [Document(page_content="...", metadata={...})]

2. 임베딩 모델 사용
   embeddings = DummyEmbeddings()  # 현재는 더미
   # 나중에: OpenAIEmbeddings()

3. PGVector 초기화 및 사용
   vector_store = PGVector(
       embeddings=embeddings,
       connection="postgresql://..."  # pgvector 컨테이너로 연결
   )

4. 데이터 저장/조회
   vector_store.add_documents(documents)
   results = vector_store.similarity_search("query")
```

**환경 변수로 pgvector 찾기**:
```yaml
environment:
  POSTGRES_HOST: pgvector  # ← Docker가 이 이름을 IP로 변환
  POSTGRES_PORT: 5432
  POSTGRES_DB: vectordb
```

---

### 🐘 **langchain-pgvector 컨테이너**

**역할**: 벡터 데이터베이스 서버

**내부 구조**:
```
PostgreSQL 16 서버
├── pgvector 확장 설치됨
│   └── 벡터 데이터 타입 지원 (vector)
│   └── 벡터 연산 함수들
│       ├── <=> (코사인 거리)
│       ├── <-> (L2 거리)
│       └── <#> (내적)
│
└── vectordb 데이터베이스
    └── 테이블들:
        ├── langchain_pg_collection
        │   └── 컬렉션 정보 저장
        │       (예: "test_connection", "langchain_demo")
        │
        └── langchain_pg_embedding
            └── 실제 벡터 데이터 저장
                ├── id (PK)
                ├── collection_id (FK)
                ├── embedding (vector 타입)
                ├── document (text)
                ├── cmetadata (jsonb)
                └── custom_id
```

---

## 🔗 네트워크 연결 상세

### Docker 네트워크: `langchain_default`

```
langchain-app 컨테이너
    IP: 172.18.0.3 (자동 할당)
    내부에서 "pgvector"라는 이름으로 접근
         ↓
    Docker DNS가 "pgvector" → 172.18.0.2로 변환
         ↓
langchain-pgvector 컨테이너
    IP: 172.18.0.2
    포트: 5432 (PostgreSQL 기본 포트)
```

**연결 문자열 분석**:
```python
connection_string = "postgresql+psycopg2://langchain:langchain123@pgvector:5432/vectordb"
                    │                      │         │           │        │    │
                    │                      │         │           │        │    └─ 데이터베이스명
                    │                      │         │           │        └─ 포트
                    │                      │         │           └─ 호스트 (컨테이너명)
                    │                      │         └─ 비밀번호
                    │                      └─ 사용자명
                    └─ 드라이버 (psycopg2 사용)
```

---

## 🗄️ 데이터 저장소 구조

### Docker Volume: `pgvector_data`

```
호스트 머신 (Windows)
    └── Docker Desktop
        └── Docker Volume: pgvector_data
            └── PostgreSQL 데이터 파일들
                ├── base/
                │   └── vectordb 데이터베이스 파일
                ├── pg_wal/ (트랜잭션 로그)
                └── pg_tblspc/ (테이블스페이스)
```

**영구성 보장**:
- 컨테이너를 삭제해도 Volume은 남아있음
- `docker-compose down -v` 해야만 Volume 삭제
- 데이터가 호스트에 저장되어 안전

---

## 🎯 실제 예제로 이해하기

### 시나리오: "LangChain에 대해 알려줘" 검색

#### **Step 1: 데이터 저장 (사전 작업)**

```python
# 1. 문서 생성
doc = Document(
    page_content="LangChain은 LLM 애플리케이션 개발 프레임워크입니다.",
    metadata={"topic": "intro"}
)

# 2. 임베딩으로 변환
text = "LangChain은 LLM 애플리케이션 개발 프레임워크입니다."
vector = [0.1, 0.2, 0.3, ..., 0.384]  # 384차원

# 3. PostgreSQL에 저장
```

**PostgreSQL 테이블에 저장된 모습**:
```sql
-- langchain_pg_embedding 테이블
| id | collection_id | embedding           | document                        | cmetadata        |
|----|---------------|---------------------|---------------------------------|------------------|
| 1  | uuid-123...   | [0.1, 0.2, 0.3,...] | LangChain은 LLM 애플리케이션... | {"topic":"intro"}|
```

#### **Step 2: 검색 수행**

```python
# 1. 검색 쿼리
query = "LangChain에 대해 알려줘"

# 2. 쿼리를 벡터로 변환
query_vector = [0.15, 0.25, 0.35, ..., 0.45]

# 3. PostgreSQL에서 유사도 계산
results = vector_store.similarity_search(query, k=1)
```

**내부에서 실행되는 SQL**:
```sql
SELECT
    document,
    cmetadata,
    embedding <=> '[0.15, 0.25, 0.35, ...]'::vector as distance
FROM langchain_pg_embedding
ORDER BY distance ASC  -- 거리가 가까운 순
LIMIT 1;
```

**결과**:
```python
[
    Document(
        page_content="LangChain은 LLM 애플리케이션 개발 프레임워크입니다.",
        metadata={"topic": "intro"}
    )
]
```

---

## 🔍 현재 구현 vs 실제 프로덕션

### 현재 구조 (테스트용)

```
사용자 입력
    ↓
DummyEmbeddings (더미 벡터 생성)
    ↓ [0, 1, 2, 3, ..., 383] (단순 숫자 나열)
PGVector (저장/검색)
    ↓
결과 반환 (의미 없는 검색)
```

**문제점**:
- 더미 임베딩은 실제 의미를 반영하지 못함
- "LangChain"과 "사과"가 같은 벡터로 변환됨
- 검색 결과가 무의미함

---

### 실제 프로덕션 구조 (목표)

```
사용자 입력: "LangChain에 대해 알려줘"
    ↓
OpenAI Embeddings API
    ↓ [0.234, -0.123, 0.456, ...] (의미 있는 벡터)
    실제 단어/문장의 의미를 수치로 표현
    ↓
PGVector (저장/검색)
    ↓ 의미적으로 유사한 문서 찾기
OpenAI ChatGPT API
    ↓ 검색된 문서를 기반으로 답변 생성
사용자에게 답변
```

---

## 📦 컴포넌트 간 의존성

```
docker-compose.yaml
    ↓ 정의
┌─────────────────────────────────┐
│  pgvector (독립적으로 실행 가능) │
└────────────┬────────────────────┘
             ↓ depends_on
┌─────────────────────────────────┐
│  langchain-app                  │
│  (pgvector가 healthy 되면 시작) │
└─────────────────────────────────┘
```

**Healthcheck의 역할**:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U langchain -d vectordb"]
  # → PostgreSQL이 준비되었는지 5초마다 확인
  # → 준비되면 langchain-app 시작
```

---

## 💡 핵심 개념 정리

### 1. **임베딩 (Embedding)이란?**

텍스트를 숫자 벡터로 변환하는 것:

```
"LangChain은 좋다"  →  [0.234, -0.123, 0.456, ...]
"LangChain is good" →  [0.240, -0.120, 0.450, ...]
"날씨가 좋다"       →  [-0.500, 0.800, -0.200, ...]

# 비슷한 의미 → 비슷한 벡터
# 다른 의미 → 다른 벡터
```

### 2. **벡터 유사도 검색이란?**

두 벡터 간의 거리를 계산하여 유사도 측정:

```
Query Vector:    [0.234, -0.123, 0.456]
Document1 Vector: [0.240, -0.120, 0.450]  ← 거리: 0.01 (매우 가까움!)
Document2 Vector: [-0.500, 0.800, -0.200] ← 거리: 1.50 (멀리 떨어짐)

→ Document1이 더 유사함!
```

### 3. **PGVector의 역할**

PostgreSQL에서 벡터를 효율적으로 저장하고 검색:

```sql
-- 벡터 저장
INSERT INTO embeddings (vec) VALUES ('[0.1, 0.2, 0.3]');

-- 벡터 검색 (가장 유사한 것 찾기)
SELECT * FROM embeddings
ORDER BY vec <=> '[0.15, 0.25, 0.35]'  -- 거리 계산
LIMIT 5;
```

---

## 🎓 이해 체크 퀴즈

1. **Q**: langchain-app이 pgvector를 어떻게 찾나요?
   **A**: Docker DNS가 "pgvector"라는 이름을 172.18.0.2 IP로 변환

2. **Q**: 벡터 데이터는 어디에 저장되나요?
   **A**: PostgreSQL의 langchain_pg_embedding 테이블 → Docker Volume

3. **Q**: 컨테이너를 삭제하면 데이터가 사라지나요?
   **A**: 아니요. Docker Volume에 저장되어 있어서 보존됨

4. **Q**: 더미 임베딩과 실제 임베딩의 차이는?
   **A**: 더미는 [0,1,2,3...], 실제는 의미를 반영한 벡터

---

## 🚀 다음 단계: OpenAI 챗봇으로

현재까지 완성된 것:
- ✅ Docker 환경 구성
- ✅ LangChain ↔ PGVector 연결
- ✅ 벡터 저장/검색 기능

다음에 추가할 것:
- 🎯 OpenAI Embeddings (의미 있는 벡터)
- 🎯 OpenAI ChatGPT (대화 생성)
- 🎯 RAG 시스템 (검색 + 생성)
- 🎯 FastAPI (웹 API)
- 🎯 프론트엔드 (채팅 UI)

준비되셨으면 다음 단계로 진행하겠습니다! 🚀

