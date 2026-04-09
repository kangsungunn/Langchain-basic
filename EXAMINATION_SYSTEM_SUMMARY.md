# 특허 심사 시스템 구조 요약

## 시스템 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP 요청 (POST)                          │
│   /admin/examination/examine                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  1️⃣ examination_router.py (FastAPI Router)                  │
│  역할: 요청 수신 및 검증                                       │
│  - examination_type 검증 (rule_based / policy_based)        │
│  - 필수 파라미터 검증                                          │
│  - ExaminationOrchestrator 호출                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  2️⃣ examination_flow.py (Orchestrator)                      │
│  역할: 모델 로드 및 분기 처리                                   │
│  - artifacts/models/finetuned/patent/final 모델 로드          │
│  - examination_type에 따라 분기:                              │
│    • rule_based → ExaminationService                        │
│    • policy_based → ExaminationAgent                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│ 3️⃣-A                 │  │ 3️⃣-B                 │
│ examination_         │  │ examination_         │
│ service.py           │  │ agent.py             │
│                      │  │                      │
│ 규칙기반 심사         │  │ 정책기반 심사         │
│ ─────────────        │  │ ─────────────        │
│ • 특허법 조문 기반    │  │ • LangGraph 워크플로우│
│ • 명세서 검토         │  │ • 3단계 분석:        │
│ • 모델 추론          │  │   1) analyze 노드    │
│ • 등록/거절 판단     │  │   2) reason 노드     │
│                      │  │   3) decide 노드     │
└──────────────────────┘  └──────────────────────┘
         │                         │
         └────────────┬────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    심사 결과 반환                              │
│  {                                                           │
│    "success": true,                                          │
│    "examination_type": "rule_based" / "policy_based",       │
│    "result": { ... },                                        │
│    "message": "심사가 성공적으로 완료되었습니다."               │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## 핵심 컴포넌트

### 1. examination_router.py
- **위치**: `app/api/admin/examination_router.py`
- **역할**: FastAPI 라우터
- **책임**:
  - HTTP 요청 수신
  - 입력 검증 (Pydantic 모델)
  - 에러 핸들링
  - 오케스트레이터 호출

**주요 엔드포인트**:
- `POST /admin/examination/examine` - 심사 실행

### 2. examination_flow.py
- **위치**: `app/domain/admin/orchestrators/examination_flow.py`
- **역할**: 오케스트레이터
- **책임**:
  - 파인튜닝된 모델 로드 (`artifacts/models/finetuned/patent/final`)
  - examination_type에 따라 분기
  - 서비스/에이전트 초기화 및 관리

**주요 메서드**:
- `execute_examination()` - 심사 실행
- `_execute_rule_based()` - 규칙기반 심사 라우팅
- `_execute_policy_based()` - 정책기반 심사 라우팅

### 3-A. examination_service.py
- **위치**: `app/domain/admin/services/examination_service.py`
- **역할**: 규칙기반 심사 서비스
- **책임**:
  - 특허법 조문 기반 검토
  - 모델을 사용한 명세서 분석
  - 등록/거절 판단

**주요 메서드**:
- `examine_by_rule()` - 규칙기반 심사 수행
- `_get_article_content()` - 조문 내용 조회
- `_interpret_result()` - 결과 해석

### 3-B. examination_agent.py
- **위치**: `app/domain/admin/agents/examination_agent.py`
- **역할**: 정책기반 심사 에이전트
- **책임**:
  - LangGraph 워크플로우 구성
  - 복잡한 정책 분석
  - 다단계 추론

**LangGraph 워크플로우**:
1. **analyze 노드**: 특허 텍스트 분석
2. **reason 노드**: 정책 기반 추론
3. **decide 노드**: 최종 결정

## 데이터 흐름

### 규칙기반 심사 (Rule-based)

```
입력 → 라우터 → 오케스트레이터 → 규칙기반 서비스
                     ↓
              모델 로드 (특허 모델)
                     ↓
              조문 + 명세서 결합
                     ↓
              모델 추론 (등록/거절)
                     ↓
              결과 해석 및 반환
```

**입력 데이터**:
```json
{
  "examination_type": "rule_based",
  "patent_text": "특허 명세서...",
  "article_number": "제29조"
}
```

**출력 데이터**:
```json
{
  "method": "rule_based",
  "article_number": "제29조",
  "decision": "등록 가능",
  "confidence": 0.8945,
  "analysis": "..."
}
```

### 정책기반 심사 (Policy-based)

```
입력 → 라우터 → 오케스트레이터 → 정책기반 에이전트
                     ↓
              모델 로드 (특허 모델)
                     ↓
              LangGraph 워크플로우 시작
                     ↓
         ┌────────────┼────────────┐
         ▼            ▼            ▼
     analyze      reason       decide
     (분석)       (추론)       (결정)
         │            │            │
         └────────────┴────────────┘
                     ↓
              결과 포맷팅 및 반환
```

**입력 데이터**:
```json
{
  "examination_type": "policy_based",
  "patent_text": "특허 명세서...",
  "query": "이 발명이 진보성을 갖는가?"
}
```

**출력 데이터**:
```json
{
  "method": "policy_based",
  "query": "이 발명이 진보성을 갖는가?",
  "decision": "등록 가능",
  "confidence": 0.9124,
  "reasoning": "...",
  "workflow_steps": ["특허 분석 완료", "정책 추론 완료", "최종 결정: 등록 가능"]
}
```

## 파일 구조

```
rag/
├── app/
│   ├── main.py                                    # FastAPI 앱
│   ├── requirements.txt                           # 의존성
│   ├── api/
│   │   └── admin/
│   │       ├── __init__.py
│   │       └── examination_router.py              # 1️⃣ 라우터
│   └── domain/
│       └── admin/
│           ├── orchestrators/
│           │   ├── __init__.py
│           │   └── examination_flow.py            # 2️⃣ 오케스트레이터
│           ├── services/
│           │   ├── __init__.py
│           │   └── examination_service.py         # 3️⃣-A 규칙기반
│           └── agents/
│               ├── __init__.py
│               └── examination_agent.py           # 3️⃣-B 정책기반
│
├── artifacts/
│   └── models/
│       └── finetuned/
│           └── patent/
│               └── final/                         # 파인튜닝 모델
│
├── training/
│   └── examination/
│       └── patent/
│           └── train.py                           # 모델 학습
│
├── test_examination_api.py                        # API 테스트
├── example_examination_usage.py                   # 사용 예제
├── EXAMINATION_API_GUIDE.md                       # 상세 가이드
└── EXAMINATION_SYSTEM_SUMMARY.md                  # 이 파일
```

## 사용 방법

### 1단계: 모델 학습

```bash
python training/examination/patent/train.py
```

### 2단계: 서버 실행

```bash
uvicorn app.main:app --reload
```

### 3단계: API 호출

**규칙기반 심사**:
```bash
curl -X POST "http://localhost:8000/admin/examination/examine" \
  -H "Content-Type: application/json" \
  -d '{
    "examination_type": "rule_based",
    "patent_text": "특허 명세서...",
    "article_number": "제29조"
  }'
```

**정책기반 심사**:
```bash
curl -X POST "http://localhost:8000/admin/examination/examine" \
  -H "Content-Type: application/json" \
  -d '{
    "examination_type": "policy_based",
    "patent_text": "특허 명세서...",
    "query": "이 발명이 진보성을 갖는가?"
  }'
```

### 4단계: 테스트 실행

```bash
# 전체 테스트
python test_examination_api.py

# 간단한 예제
python example_examination_usage.py
```

## 핵심 기술 스택

- **웹 프레임워크**: FastAPI
- **ML 프레임워크**: Transformers (HuggingFace)
- **모델**: KoELECTRA (또는 EXAONE)
- **워크플로우**: LangGraph
- **언어 모델**: LangChain
- **데이터베이스**: PostgreSQL (NeonDB)

## 확장 가능성

1. **새로운 심사 유형 추가**: orchestrator에서 분기 추가
2. **데이터베이스 연동**: 조문 데이터를 DB에서 조회
3. **벡터 DB 통합**: 유사 판례 검색
4. **배치 처리**: 여러 특허 동시 처리
5. **캐싱**: Redis 등을 활용한 결과 캐싱

## 참고 문서

- **상세 API 가이드**: `EXAMINATION_API_GUIDE.md`
- **테스트 스크립트**: `test_examination_api.py`
- **사용 예제**: `example_examination_usage.py`
- **Swagger UI**: `http://localhost:8000/docs`
