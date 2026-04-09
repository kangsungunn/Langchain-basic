  # Legal Answer Review System - 전체 폴더/파일 구조

> **목적**: 민사소송법 서술형 답안지 첨삭 시스템
> **아키텍처**: Modular Monolith + DDD + MCP + 약화된 스타 토폴로지

**중요**: `app/api/`는 **라우터 레이어(Router Layer)**입니다. 현재 버전은 `app/api/v1/`이며, 향후 `app/api/v2/`, `app/api/v3/` 등 버전별 폴더가 추가될 수 있습니다.

---

## 📁 전체 구조 (트리)

```
rag/
├── app/
│   ├── __init__.py
│   │
│   ├── api/                              # Router Layer (라우터 레이어) ⭐
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI 앱 진입점
│   │   │
│   │   └── v1/                           # API v1 (현재 버전)
│   │       ├── __init__.py
│   │       ├── reference.py              # Reference Domain 라우터
│   │       ├── submission.py             # Submission Domain 라우터
│   │       ├── reasoning.py              # Reasoning Domain 라우터
│   │       ├── feedback.py               # Feedback Domain 라우터
│   │       └── training.py               # Training Domain 라우터
│   │   # 향후 v2/, v3/ 등 버전별 폴더 추가 가능
│   │
│   ├── domain/                           # Domain Layer (DDD)
│   │   ├── __init__.py
│   │   │
│   │   ├── reference/                    # Reference Domain (기준 지식)
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── models/                   # 도메인 모델
│   │   │   │   ├── __init__.py
│   │   │   │   ├── problem.py           # 문제 모델
│   │   │   │   ├── model_answer.py      # 모범답안 모델
│   │   │   │   └── issue_structure.py   # 논점 구조 모델
│   │   │   │
│   │   │   ├── services/                 # 도메인 서비스
│   │   │   │   ├── __init__.py
│   │   │   │   ├── issue_extractor.py   # 논점 추출 (EXAONE 활용)
│   │   │   │   ├── structure_builder.py # 논점 구조 생성
│   │   │   │   └── reference_manager.py # 기준 지식 관리
│   │   │   │
│   │   │   └── repositories/             # 레포지토리
│   │   │       ├── __init__.py
│   │   │       ├── problem_repository.py
│   │   │       ├── model_answer_repository.py
│   │   │       └── issue_repository.py
│   │   │
│   │   ├── submission/                   # Submission Domain (제출 답안)
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── models/                   # 도메인 모델
│   │   │   │   ├── __init__.py
│   │   │   │   ├── submission.py        # 제출 답안 모델
│   │   │   │   ├── parsed_answer.py     # 파싱된 답안 모델
│   │   │   │   └── answer_structure.py  # 답안 구조 모델
│   │   │   │
│   │   │   ├── services/                 # 도메인 서비스
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ocr_service.py       # OCR 처리
│   │   │   │   ├── text_parser.py       # 텍스트 파싱
│   │   │   │   ├── structure_normalizer.py # 구조 정규화
│   │   │   │   └── submission_manager.py # 제출 답안 관리
│   │   │   │
│   │   │   └── repositories/             # 레포지토리
│   │   │       ├── __init__.py
│   │   │       └── submission_repository.py
│   │   │
│   │   ├── reasoning/                    # Reasoning Domain (추론) ⭐ HUB
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── models/                   # 도메인 모델
│   │   │   │   ├── __init__.py
│   │   │   │   ├── reasoning_state.py   # 추론 상태 모델
│   │   │   │   ├── issue_comparison.py  # 논점 비교 결과
│   │   │   │   ├── logic_analysis.py    # 논리 분석 결과
│   │   │   │   └── reasoning_result.py  # 추론 결과 모델
│   │   │   │
│   │   │   ├── agents/                   # LangGraph 에이전트
│   │   │   │   ├── __init__.py
│   │   │   │   ├── reasoning_agent.py   # 메인 추론 에이전트
│   │   │   │   ├── issue_detector.py    # 논점 인식
│   │   │   │   ├── logic_analyzer.py    # 논리 흐름 분석
│   │   │   │   └── expression_evaluator.py # 표현 평가
│   │   │   │
│   │   │   ├── orchestrators/            # 오케스트레이터 (Hub)
│   │   │   │   ├── __init__.py
│   │   │   │   └── reasoning_hub.py     # 중앙 허브 (스타 토폴로지)
│   │   │   │
│   │   │   └── repositories/             # 레포지토리
│   │   │       ├── __init__.py
│   │   │       └── reasoning_repository.py
│   │   │
│   │   ├── feedback/                     # Feedback Domain (피드백)
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── models/                   # 도메인 모델
│   │   │   │   ├── __init__.py
│   │   │   │   ├── feedback.py          # 피드백 모델
│   │   │   │   └── feedback_item.py     # 피드백 항목 모델
│   │   │   │
│   │   │   ├── services/                 # 도메인 서비스
│   │   │   │   ├── __init__.py
│   │   │   │   ├── feedback_generator.py # 피드백 생성
│   │   │   │   ├── tone_adjuster.py     # 톤 조정 (학습용)
│   │   │   │   ├── template_manager.py  # 피드백 템플릿 관리
│   │   │   │   └── feedback_manager.py  # 피드백 관리
│   │   │   │
│   │   │   └── repositories/             # 레포지토리
│   │   │       ├── __init__.py
│   │   │       └── feedback_repository.py
│   │   │
│   │   └── shared/                       # 공유 도메인 로직
│   │       ├── __init__.py
│   │       ├── value_objects.py         # 값 객체
│   │       ├── events.py                # 도메인 이벤트
│   │       └── exceptions.py            # 도메인 예외
│   │
│   ├── core/                             # Core Layer (Infrastructure)
│   │   ├── __init__.py
│   │   │
│   │   ├── config.py                     # 설정
│   │   │
│   │   ├── mcp/                          # MCP Protocol
│   │   │   ├── __init__.py
│   │   │   ├── protocol.py              # MCP 프로토콜 정의
│   │   │   ├── message.py               # 메시지 포맷
│   │   │   ├── transport.py             # 전송 계층
│   │   │   └── handlers.py              # 메시지 핸들러
│   │   │
│   │   ├── orchestration/                # 전역 오케스트레이션
│   │   │   ├── __init__.py
│   │   │   ├── base_orchestrator.py     # 기본 오케스트레이터
│   │   │   └── workflow_manager.py      # 워크플로우 관리
│   │   │
│   │   ├── ml/                           # ML 관련
│   │   │   ├── __init__.py
│   │   │   ├── model_loader.py          # 모델 로더 (EXAONE)
│   │   │   ├── inference.py             # 추론 엔진
│   │   │   └── embeddings.py            # 임베딩
│   │   │
│   │   ├── database/                     # 데이터베이스
│   │   │   ├── __init__.py
│   │   │   ├── connection.py            # DB 연결
│   │   │   ├── session.py               # 세션 관리
│   │   │   └── models.py                # SQLAlchemy 모델
│   │   │
│   │   └── utils/                        # 유틸리티
│   │       ├── __init__.py
│   │       ├── logger.py                # 로깅
│   │       ├── validators.py            # 검증
│   │       └── converters.py            # 변환 유틸
│   │
│   ├── main.py                           # 앱 진입점 (uvicorn)
│   └── requirements.txt                  # Python 의존성
│
├── artifacts/                            # ML 모델 저장소
│   └── models/
│       ├── base/                         # 베이스 모델
│       │   └── exaone-2.4b/             # EXAONE 베이스
│       │
│       └── finetuned/                    # 파인튜닝 모델
│           └── legal/                    # 법률 도메인 모델
│               └── final/                # 최종 모델
│
├── data/                                 # 데이터
│   ├── raw/                              # 원본 데이터
│   │   └── civil_procedure/             # 민사소송법
│   │       ├── problems/                # 문제
│   │       └── model_answers/           # 모범답안
│   │
│   └── processed/                        # 처리된 데이터
│       └── civil_procedure/
│           ├── train.jsonl              # 학습 데이터
│           ├── val.jsonl                # 검증 데이터
│           └── test.jsonl               # 테스트 데이터
│
├── database/                             # 데이터베이스 스키마
│   └── schema/
│       ├── reference_tables.sql         # Reference 테이블
│       ├── submission_tables.sql        # Submission 테이블
│       ├── reasoning_tables.sql         # Reasoning 테이블
│       ├── feedback_tables.sql          # Feedback 테이블
│       └── init.sql                     # 초기화 스크립트
│
├── training/                             # 모델 학습
│   ├── __init__.py
│   │
│   ├── legal/                            # 법률 도메인 학습
│   │   └── train_legal_model.py         # 법률 모델 학습
│   │
│   └── shared/                           # 공유 학습 스크립트
│       ├── __init__.py
│       ├── train_exaone_lora.py         # EXAONE LoRA 학습
│       ├── parse_legal_documents.py     # 법률 문서 파싱
│       └── data_preprocessor.py         # 데이터 전처리
│
├── frontend/                             # 프론트엔드 (Next.js)
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   │
│   └── src/
│       └── app/
│           ├── page.tsx                 # 메인 페이지
│           ├── globals.css
│           │
│           └── api/                     # API 라우트
│               ├── reference/
│               │   └── route.ts         # Reference API
│               ├── submission/
│               │   └── route.ts         # Submission API
│               ├── reasoning/
│               │   └── route.ts         # Reasoning API
│               └── feedback/
│                   └── route.ts         # Feedback API
│
├── tests/                                # 테스트
│   ├── __init__.py
│   │
│   ├── unit/                             # 단위 테스트
│   │   ├── domain/
│   │   │   ├── test_reference.py
│   │   │   ├── test_submission.py
│   │   │   ├── test_reasoning.py
│   │   │   └── test_feedback.py
│   │   │
│   │   └── core/
│   │       ├── test_mcp.py
│   │       └── test_ml.py
│   │
│   ├── integration/                      # 통합 테스트
│   │   ├── test_reference_submission.py
│   │   ├── test_reasoning_flow.py
│   │   └── test_end_to_end.py
│   │
│   └── fixtures/                         # 테스트 픽스처
│       ├── sample_problems.json
│       ├── sample_answers.json
│       └── sample_feedback.json
│
├── scripts/                              # 유틸리티 스크립트
│   ├── init_db.py                       # DB 초기화
│   ├── seed_data.py                     # 샘플 데이터 생성
│   ├── migrate.py                       # 마이그레이션
│   └── deploy.sh                        # 배포 스크립트
│
├── strategy/                             # 전략 문서
│   ├── PROJECT_STRUCTURE_OVERVIEW.md    # 프로젝트 구조 개요
│   ├── NEW_PROJECT_STRUCTURE.md         # 신규 구조 (이 문서)
│   ├── ORCHESTRATION_COMPARISON_ANALYSIS.md
│   ├── DOMAIN_DESIGN.md                 # 도메인 설계 문서
│   ├── MCP_PROTOCOL_SPEC.md             # MCP 프로토콜 명세
│   └── PHASE1_IMPLEMENTATION.md         # Phase 1 구현 계획
│
├── .env.example                          # 환경변수 예시
├── .gitignore
├── README.md                             # 프로젝트 소개
├── pyproject.toml                        # Python 프로젝트 설정
└── docker-compose.yml                    # Docker 구성
```

---

## 📋 각 폴더/파일 역할 요약

### 1. `/app/api` - Router Layer (라우터 레이어) ⭐

**역할**: FastAPI 라우터 (API 엔드포인트 정의)

**구조**:
- `app/api/` = 라우터 레이어 (API Layer)
- `app/api/v1/` = 현재 버전의 API
- 향후 `app/api/v2/`, `app/api/v3/` 등 버전별 폴더 추가 가능

| 파일 | 역할 |
|------|------|
| `main.py` | FastAPI 앱 초기화, 미들웨어, CORS |
| `v1/reference.py` | Reference Domain 라우터 |
| `v1/submission.py` | Submission Domain 라우터 |
| `v1/reasoning.py` | Reasoning Domain 라우터 |
| `v1/feedback.py` | Feedback Domain 라우터 |
| `v1/training.py` | Training Domain 라우터 |

---

### 2. `/app/domain` - Domain Layer (DDD)

#### 2.1 `reference/` - Reference Domain

**역할**: 기준 지식 관리 (문제, 모범답안, 논점 구조)

| 파일 | 역할 |
|------|------|
| `models/problem.py` | 문제 도메인 모델 |
| `models/model_answer.py` | 모범답안 도메인 모델 |
| `models/issue_structure.py` | 논점 구조 도메인 모델 |
| `services/issue_extractor.py` | EXAONE으로 논점 추출 |
| `services/structure_builder.py` | 논점 구조 생성 |
| `repositories/problem_repository.py` | 문제 CRUD |

#### 2.2 `submission/` - Submission Domain

**역할**: 제출 답안 처리 (OCR, 파싱, 구조화)

| 파일 | 역할 |
|------|------|
| `models/submission.py` | 제출 답안 도메인 모델 |
| `models/parsed_answer.py` | 파싱된 답안 모델 |
| `services/ocr_service.py` | OCR 처리 (Tesseract, Google Vision) |
| `services/text_parser.py` | 텍스트 파싱 (문단/문장 분해) |
| `services/structure_normalizer.py` | 법학 서술형 구조화 |

#### 2.3 `reasoning/` - Reasoning Domain ⭐ HUB

**역할**: 비교·추론 (EXAONE, LangGraph)

| 파일 | 역할 |
|------|------|
| `models/reasoning_state.py` | LangGraph 상태 모델 |
| `agents/reasoning_agent.py` | 메인 추론 에이전트 |
| `agents/issue_detector.py` | 논점 인식 브랜치 |
| `agents/logic_analyzer.py` | 논리 흐름 분석 브랜치 |
| `agents/expression_evaluator.py` | 표현 평가 브랜치 |
| `orchestrators/reasoning_hub.py` | 중앙 허브 (스타 토폴로지) |

#### 2.4 `feedback/` - Feedback Domain

**역할**: 피드백 생성 (학습용 톤)

| 파일 | 역할 |
|------|------|
| `models/feedback.py` | 피드백 도메인 모델 |
| `services/feedback_generator.py` | 피드백 생성 |
| `services/tone_adjuster.py` | 톤 조정 (학습용) |
| `services/template_manager.py` | 피드백 템플릿 관리 |

---

### 3. `/app/core` - Core Layer (Infrastructure)

**역할**: 인프라, 공통 기능

| 폴더 | 역할 |
|------|------|
| `mcp/` | MCP 프로토콜 구현 |
| `ml/` | ML 모델 로더, 추론 엔진 |
| `database/` | DB 연결, 세션 관리 |
| `utils/` | 로깅, 검증, 변환 유틸 |

---

### 4. `/artifacts` - ML 모델 저장소

```
artifacts/models/
├── base/
│   └── exaone-2.4b/          # EXAONE 베이스 모델
│
└── finetuned/
    └── legal/
        └── final/             # 법률 파인튜닝 모델
```

---

### 5. `/data` - 데이터

```
data/
├── raw/
│   └── civil_procedure/      # 민사소송법 원본
│
└── processed/
    └── civil_procedure/      # 학습용 데이터
```

---

### 6. `/database` - 데이터베이스 스키마

| 파일 | 역할 |
|------|------|
| `reference_tables.sql` | problems, model_answers, issues 테이블 |
| `submission_tables.sql` | submissions, parsed_answers 테이블 |
| `reasoning_tables.sql` | reasoning_results 테이블 |
| `feedback_tables.sql` | feedbacks 테이블 |

---

### 7. `/training` - 모델 학습

| 파일 | 역할 |
|------|------|
| `legal/train_legal_model.py` | 법률 도메인 모델 학습 |
| `shared/train_exaone_lora.py` | EXAONE LoRA 학습 |
| `shared/parse_legal_documents.py` | 법률 문서 파싱 |

---

### 8. `/frontend` - Next.js 프론트엔드

```
frontend/src/app/
├── page.tsx                  # 메인 페이지
└── api/
    ├── reference/route.ts    # Reference API
    ├── submission/route.ts   # Submission API
    ├── reasoning/route.ts    # Reasoning API
    └── feedback/route.ts     # Feedback API
```

---

### 9. `/tests` - 테스트

```
tests/
├── unit/                     # 단위 테스트
│   └── domain/
│       ├── test_reference.py
│       ├── test_submission.py
│       ├── test_reasoning.py
│       └── test_feedback.py
│
└── integration/              # 통합 테스트
    └── test_end_to_end.py
```

---

### 10. `/strategy` - 전략 문서

**역할**: 아키텍처, 설계, 구현 계획 문서

---

## 🎯 핵심 포인트

### DDD 경계 (Bounded Context)

```
1. Reference Domain    → 기준 지식의 세계
2. Submission Domain   → 제출 답안의 세계
3. Reasoning Domain    → 추론의 세계 (HUB) ⭐
4. Feedback Domain     → 피드백의 세계
```

### MCP 통신 경로

```
Reference ──MCP──▶ Reasoning Hub
Submission ──MCP──▶ Reasoning Hub
Reasoning Hub ──MCP──▶ Feedback
```

### 스타 토폴로지 (약화된)

```
         Reference
              ↓
         Submission
              ↓
    ┌─────────────────┐
    │ Reasoning Hub   │ ← EXAONE
    │  (Orchestrator) │
    └─────────────────┘
              ↓
         Feedback
```

---

## 📝 생성 순서 권장

### Phase 1: 기본 구조 (빈 폴더/파일)
```bash
# 1. 메인 폴더
app/
  api/
  domain/
  core/

# 2. 도메인 폴더
domain/
  reference/
  submission/
  reasoning/
  feedback/
  shared/

# 3. 각 도메인 하위
domain/reference/
  models/
  services/
  repositories/

# ... (반복)
```

### Phase 2: 핵심 파일
```
1. app/api/main.py
2. app/domain/reasoning/orchestrators/reasoning_hub.py
3. app/core/mcp/protocol.py
4. app/core/ml/model_loader.py
```

### Phase 3: 데이터베이스
```
database/schema/*.sql
```

### Phase 4: 테스트
```
tests/unit/
tests/integration/
```

---

## 🚀 다음 단계

1. **사용자**: 빈 폴더/파일 생성
2. **AI**: 각 파일 코드 작성
3. **구현 순서**:
   - Phase 1: Reference Domain (기준 지식 관리)
   - Phase 2: Submission Domain (답안 처리)
   - Phase 3: Reasoning Domain (추론 엔진)
   - Phase 4: Feedback Domain (피드백 생성)

---

**작성일**: 2026-01-22
**버전**: 1.0
**목적**: 민사소송법 서술형 답안지 첨삭 시스템 구조
