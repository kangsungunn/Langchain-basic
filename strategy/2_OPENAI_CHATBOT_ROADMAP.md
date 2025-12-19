# 🤖 OpenAI 챗봇 구현 로드맵

## 📍 현재 위치

```
[✅ 완료] Docker 환경
[✅ 완료] LangChain + PGVector 연결
[✅ 완료] 벡터 저장/검색 기본
[🎯 진행 중] OpenAI 연동
[⏳ 대기] RAG 챗봇
[⏳ 대기] FastAPI 서버
[⏳ 대기] 웹 UI
```

---

## 🎯 최종 목표 시스템

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자 인터페이스                        │
│                    (웹 브라우저 채팅 UI)                        │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP Request
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI 서버                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  POST /chat                                              │  │
│  │  - 사용자 질문 받기                                      │  │
│  │  - RAG 처리                                              │  │
│  │  - 답변 반환                                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
┌──────────────────┐           ┌──────────────────┐
│  OpenAI API      │           │  PGVector DB     │
│                  │           │                  │
│  1. Embeddings   │◄─────────►│  벡터 저장소     │
│     (벡터 변환)  │           │  (문서 검색)     │
│                  │           │                  │
│  2. ChatGPT      │           │                  │
│     (답변 생성)  │           │                  │
└──────────────────┘           └──────────────────┘
```

---

## 📋 단계별 구현 계획

### Phase 1: OpenAI API 연동 (기본) ⭐ 시작 지점

**목표**: OpenAI Embeddings와 ChatGPT 연결

**구현 내용**:
- OpenAI API 키 설정
- 실제 임베딩 모델 사용 (더미 제거)
- 간단한 챗봇 대화 테스트

**예상 시간**: 30분

---

### Phase 2: RAG 시스템 구현

**목표**: 검색 기반 답변 생성 (Retrieval-Augmented Generation)

**구현 내용**:
- 지식 베이스 구축 (문서 업로드)
- 질문 → 관련 문서 검색 → 답변 생성
- 대화 히스토리 관리

**예상 시간**: 1시간

---

### Phase 3: FastAPI 서버 구축

**목표**: REST API로 챗봇 서비스 제공

**구현 내용**:
- FastAPI 서버 구현
- `/chat` 엔드포인트
- `/upload` 문서 업로드 엔드포인트
- CORS 설정

**예상 시간**: 1시간

---

### Phase 4: 웹 UI 개발

**목표**: 사용자 친화적인 채팅 인터페이스

**구현 내용**:
- HTML/CSS/JavaScript 채팅 UI
- 실시간 메시지 표시
- 문서 업로드 기능

**예상 시간**: 1-2시간

---

## 🎬 Phase 1 상세 가이드

### 필요한 것

1. **OpenAI API 키** (필수)
   - https://platform.openai.com/api-keys 에서 생성
   - 무료 크레딧 또는 결제 설정 필요

2. **환경 설정**
   - `.env` 파일로 API 키 관리
   - Docker 환경 변수 설정

### 구현할 파일들

```
langchain/
├── .env                          # 🆕 API 키 저장
├── docker-compose.yaml           # 🔄 환경 변수 추가
├── requirements.txt              # 🔄 패키지 추가
├── app/
│   ├── chatbot_basic.py         # 🆕 기본 챗봇
│   ├── chatbot_rag.py           # 🆕 RAG 챗봇
│   └── upload_knowledge.py      # 🆕 지식 베이스 구축
└── knowledge/                    # 🆕 업로드할 문서들
    └── sample_docs.txt
```

### 코드 구조 미리보기

#### 1. OpenAI Embeddings 사용

```python
# 더미 임베딩 (현재)
embeddings = DummyEmbeddings()  # ❌

# 실제 OpenAI 임베딩 (변경 후)
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"  # ✅ 저렴하고 빠름
)
```

#### 2. 기본 챗봇 대화

```python
from langchain_openai import ChatOpenAI

chat = ChatOpenAI(
    model="gpt-4o-mini",  # 저렴한 모델
    temperature=0.7
)

response = chat.invoke("안녕하세요!")
print(response.content)
# → "안녕하세요! 무엇을 도와드릴까요?"
```

#### 3. RAG 챗봇 (검색 + 생성)

```python
# 1. 사용자 질문
question = "LangChain이 뭐야?"

# 2. 관련 문서 검색
docs = vector_store.similarity_search(question, k=3)

# 3. 검색된 문서를 컨텍스트로 사용
context = "\n".join([doc.page_content for doc in docs])

# 4. ChatGPT에게 질문 + 컨텍스트 제공
prompt = f"""
다음 정보를 참고하여 질문에 답변해주세요.

[참고 정보]
{context}

[질문]
{question}

[답변]
"""

response = chat.invoke(prompt)
print(response.content)
```

---

## 💰 비용 예상 (OpenAI)

### Embeddings (텍스트 → 벡터 변환)

| 모델 | 가격 | 용도 |
|------|------|------|
| text-embedding-3-small | $0.02 / 1M tokens | **추천**: 저렴하고 빠름 |
| text-embedding-3-large | $0.13 / 1M tokens | 높은 품질 필요시 |

**예시**:
- 문서 1000개 (각 500단어) = 약 750,000 tokens
- 비용: $0.015 (약 20원)

### ChatGPT (답변 생성)

| 모델 | 입력 | 출력 | 용도 |
|------|------|------|------|
| gpt-4o-mini | $0.15 / 1M | $0.60 / 1M | **추천**: 가성비 최고 |
| gpt-4o | $2.50 / 1M | $10.00 / 1M | 최고 품질 |

**예시**:
- 대화 100회 (각 500 토큰)
- 비용: $0.0375 (약 50원)

**결론**: 테스트하면서 몇 달러면 충분합니다! 💵

---

## 🎯 Phase 1 구현 체크리스트

시작하기 전 확인:

- [ ] OpenAI API 키 발급받기
- [ ] API 키 결제 수단 등록 (필수)
- [ ] Docker 컨테이너 실행 중 확인

구현 단계:

- [ ] `.env` 파일 생성 및 API 키 설정
- [ ] `requirements.txt`에 `langchain-openai` 추가
- [ ] 기본 OpenAI 챗봇 테스트
- [ ] OpenAI Embeddings로 벡터 저장
- [ ] OpenAI Embeddings로 유사도 검색
- [ ] RAG 기본 구조 구현

---

## 🚦 시작 준비 완료?

다음 중 하나를 선택해주세요:

1. **OpenAI API 키가 이미 있어요**
   → 바로 Phase 1 구현 시작! 🚀

2. **OpenAI API 키가 없어요**
   → API 키 발급 방법 안내해드리겠습니다 📝

3. **구조를 더 이해하고 싶어요**
   → 추가 설명이나 다이어그램 제공 📊

4. **다른 LLM을 사용하고 싶어요** (예: Claude, Ollama)
   → 대안 방법 안내 🔄

어떤 것을 진행할까요?

