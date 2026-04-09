# 민사소송법 답안 자동 첨삭 AI — 개인 프로젝트 기술서
> PPT 제작 프롬프트 입력용 | 2026년 1월 기준

---

## SLIDE 1 | 표지

**프로젝트명**: 민사소송법 서술형 답안 자동 첨삭 AI  
**부제**: LLM 기반 법학 도메인 특화 피드백 시스템  
**작성자**: 개인 프로젝트  
**기간**: 2025년 하반기 ~ 2026년 1월 (진행 중)  
**키워드**: FastAPI / DDD / KoELECTRA / LoRA / Star Topology / Orchestrator

---

## SLIDE 2 | 프로젝트 배경 및 목표

### 배경
- 변리사 시험 민사소송법 과목: 서술형 답안의 **쟁점 분석, 논리 구성, 표현** 능력이 핵심
- 기존에는 강사가 직접 첨삭 → 시간·비용 부담, 일관성 부족
- 모범답안과 비교하여 **자동으로 쟁점 포함 여부, 논리 강도, 표현 수준**을 평가하는 AI 시스템 필요

### 최종 목표
```
[관리자] 학습 데이터(PDF/JSONL) 업로드
         → 자동 학습 → 모델 저장 → NeonDB에 저장

[사용자] 답안지(PDF) 업로드
         → 자동 분석 → 쟁점/논리/표현 피드백 → 점수 제공
```

### 핵심 원칙
- 관리자가 데이터를 넣는 것 외의 모든 과정 → **완전 자동화**
- 사용자는 답안 파일만 올리면 첨삭 결과 수신

---

## SLIDE 3 | 전체 시스템 아키텍처

### 계층 구조 (4-Layer Architecture)

```
┌─────────────────────────────────────┐
│  FRONTEND  (Next.js 15, App Router)  │
│  - 첨삭 홈화면 / PDF 업로드 / 결과뷰 │
│  - 관리자 페이지 (학습 데이터 관리)  │
└──────────────────┬──────────────────┘
                   │ HTTP
┌──────────────────▼──────────────────┐
│   ROUTER LAYER  (app/api/v1/)        │
│   FastAPI 라우터 — 44개 엔드포인트   │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│  ORCHESTRATOR LAYER                  │
│  WorkflowManager → DecisionMaker    │
│  KoELECTRA 판단 → 정책/규칙 분기   │
│  ├─ PolicyStrategy → Star Topology  │
│  └─ RuleStrategy   → Direct Service │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│  DOMAIN LAYER  (DDD 4개 도메인)      │
│  Reference / Submission / Reasoning / Feedback │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│  INFRASTRUCTURE                      │
│  PostgreSQL(NeonDB) / EXAONE / Alembic │
└─────────────────────────────────────┘
```

---

## SLIDE 4 | 핵심 기술 스택

| 분류 | 기술 | 용도 |
|------|------|------|
| **Backend** | FastAPI (Python) | 비동기 REST API 서버 |
| **Frontend** | Next.js 15 (App Router) | 관리자/사용자 화면 |
| **Database** | PostgreSQL (NeonDB) | 서버리스 클라우드 DB |
| **ORM** | SQLAlchemy 2.0 (Async) | 비동기 DB 접근 |
| **Migration** | Alembic | 스키마 버전 관리 |
| **ML - 추론** | EXAONE (LG AI Research) | 답안 쟁점/논리/표현 분석 |
| **ML - 분기** | KoELECTRA (monologg) | 정책/규칙 기반 판단 |
| **ML - 학습** | LoRA (PEFT) | 경량 파인튜닝 |
| **아키텍처** | DDD + Modular Monolith | 도메인 분리 설계 |
| **패턴** | GoF Strategy Pattern | 오케스트레이터 분기 |
| **스타일링** | Tailwind CSS | 프론트엔드 UI |
| **데이터 포맷** | JSONL | 학습 데이터 표준 포맷 |
| **검증** | Pydantic v2 | 요청/응답 데이터 검증 |

---

## SLIDE 5 | DDD 4개 도메인 구조

### 도메인 맵

```
[Reference Domain]          [Submission Domain]
 - 문제(Problem)              - 사용자 답안(UserAnswer)
 - 모범 답안(ReferenceAnswer)  - 답안 구조 분석
 - 쟁점(Issue)                - OCR 처리(이미지 답안)
        │                              │
        └──────────┬───────────────────┘
                   ▼
          [Reasoning Domain]  ← ⭐ STAR TOPOLOGY HUB
           - ReasoningTask
           - ReasoningEngine
             ├─ 쟁점 분석 (analyze_issues)
             ├─ 논리 평가 (evaluate_logic)
             ├─ 표현 검토 (review_expression)
             └─ 종합 분석 (comprehensive_analysis)
                   │
                   ▼
          [Feedback Domain]
           - Feedback (종합 점수, 요약)
           - FeedbackItem (개별 항목, 심각도)
           - FeedbackGenerator
```

### 각 도메인 구성 원칙
모든 도메인은 동일한 4계층 구조 적용:
```
models.py → schemas.py → repositories.py → services.py
(DB 엔티티)  (Pydantic)   (CRUD 레이어)     (비즈니스 로직)
```

---

## SLIDE 6 | 오케스트레이터 아키텍처 (핵심)

### 설계 목표
강사님 제시 패턴 기반:
> "프론트 → 라우터 → 오케스트레이터 → (정책기반: Star Topology / 규칙기반: Direct Service)"

### 구현된 플로우

```
HTTP Request
    │
    ▼
[Router Layer]  app/api/v1/
    │  WorkflowManager 호출
    ▼
[WorkflowManager]  ← 중앙 오케스트레이터
    │
    ├──▶ [DecisionMaker]
    │        ├─ 1단계: 사전 필터링
    │        │   RULE_BASED_ACTIONS 목록 확인
    │        │   POLICY_BASED_ACTIONS 목록 확인
    │        │
    │        └─ 2단계: KoELECTRA 추론 (모호한 경우)
    │             프롬프트 구성 → 모델 추론 → policy/rule 판단
    │
    ├─ 판단: "rule" ──▶ [RuleStrategy]
    │                    도메인 서비스 직접 호출
    │                    (TrainingDataService, UserAnswerService 등)
    │
    └─ 판단: "policy" ─▶ [PolicyStrategy]
                          ReasoningHub (Star Topology)
                          → ReasoningEngine / FeedbackGenerator
```

### GoF 전략 패턴 적용

```python
# 인터페이스 (ABC)
class RoutingStrategy:
    async def route(domain, action, request, session) -> Any: ...

# 정책 기반: Star Topology
class PolicyStrategy(RoutingStrategy):
    async def route(...):
        hub = ReasoningHub(session)
        return await hub.process(domain, action, request)

# 규칙 기반: Direct Service
class RuleStrategy(RoutingStrategy):
    async def route(...):
        service = ServiceMap[domain](session)
        return await service.method(request)
```

---

## SLIDE 7 | KoELECTRA 기반 판단 엔진

### 역할
API 요청을 받았을 때 → ML 추론이 필요한지 / 단순 CRUD인지 자동 판단

### 판단 기준

| 유형 | 판단 기준 | 예시 액션 | 처리 방향 |
|------|----------|-----------|----------|
| **규칙 기반** | 단순 CRUD, 파라미터 기반 | create_training_data, get_answers | Direct Service |
| **정책 기반** | ML 추론 필요, 복잡한 비즈니스 로직 | comprehensive_analysis, generate_feedback | Star Topology |

### KoELECTRA 프롬프트 구조

```
다음은 민사소송법 답안 첨삭 시스템의 API 요청입니다.

도메인: {domain}
액션: {action}
요청 요약: {request_summary}

이 요청을 처리하기 위해:
1. ML 모델(EXAONE 등) 추론이 필요한가요?
2. 복잡한 비즈니스 로직이나 여러 도메인 간 협업이 필요한가요?
3. Star 토폴로지(Reasoning Hub)를 통한 중앙 집중식 처리가 필요한가요?

위 질문 중 하나라도 "예"라면 → 정책 기반 (policy)
모두 "아니오"라면 → 규칙 기반 (rule)
```

### 싱글톤 + Lazy Loading

```python
class KoELECTRALoader:
    _instance = None  # 싱글톤

    def _load_model(self):  # Lazy loading (첫 호출 시에만 로드)
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_path)

    def predict(self, text) -> {"strategy": "policy"|"rule", "confidence": float}
```

---

## SLIDE 8 | 데이터 흐름 (사용자 첨삭 요청)

```
[1] 사용자 — 답안 PDF/텍스트 업로드
             POST /api/v1/submission/answers/text
                     │
                     ▼
[2] 답안 구조 자동 분석
    - 문단 분리 / 문장 분리 / 단어 수 통계
    - AnswerStructure 생성 및 DB 저장
                     │
                     ▼
[3] 종합 추론 실행 (오케스트레이터 → Star Topology)
    POST /api/v1/reasoning/analyze/comprehensive
    │
    ├─ 쟁점 분석: 모범답안 쟁점 vs 사용자 답안 비교
    │             coverage_rate: 67%
    │
    ├─ 논리 평가: 논리 일관성, 논증 강도
    │             coherence_score: 0.78
    │
    └─ 표현 검토: 명료성, 격식성, 문법
                  clarity_score: 0.75
                     │
                     ▼
[4] 피드백 자동 생성 (오케스트레이터 → Star Topology)
    POST /api/v1/feedback/generate
    │
    ├─ FeedbackItem (INFO): "소비대차계약의 성립 — 올바르게 서술"
    ├─ FeedbackItem (CRITICAL): "변제기 도과 — 누락됨, 반드시 포함 필요"
    └─ FeedbackItem (WARNING): "논리 비약 발견 — 근거 보강 필요"
                     │
                     ▼
[5] 종합 점수 + 리포트 반환
    {
      "overall_score": 74.5,
      "scores": {"issue": 67, "logic": 78, "expression": 82},
      "summary": "쟁점 파악 일부 미흡, 논리 구성은 양호..."
    }
```

---

## SLIDE 9 | ML 자동화 파이프라인 (학습 데이터)

### 관리자 데이터 입력 흐름

```
[관리자]
  │
  ├─ 방법 1: JSONL 직접 업로드 (수동)
  │   프론트 관리자 페이지 → POST /api/v1/training/data
  │   필드: problem_text, reference_answer_text, user_answer_text
  │
  └─ 방법 2: PDF 업로드 (자동 파싱 시도)
      pdfplumber 텍스트 추출 → 구조 파싱 → JSONL 변환
      ※ 이미지 기반 PDF는 텍스트 레이어 없음 → 수동 보완 필요
              │
              ▼
[TrainingData DB 저장]
 - problem_text, reference_answer_text, user_answer_text
 - labels (issue_coverage, logic_score, expression_score)
              │
              ▼
[TrainingJob 생성 및 실행]
 - LoRA Fine-tuning (EXAONE base 모델 기반)
 - 학습 진행률 모니터링 (progress, current_epoch, loss_history)
              │
              ▼
[ModelVersion DB 저장]
 - 학습된 모델 버전 관리
 - artifacts/models/finetuned/legal/final/ 경로 저장
              │
              ▼
[자동 배포 — ModelLoader (싱글톤)]
 - 새 버전 감지 → 모델 교체
 - ReasoningEngine에서 즉시 사용 가능
```

### LoRA 경량 파인튜닝 원리

```
[EXAONE Base Model - 2.4B 파라미터 (고정)]
         +
[LoRA Adapter - 전체의 0.1%만 학습]
         ↓
메모리 절약 + 도메인 특화 성능 향상
```

---

## SLIDE 10 | 프론트엔드 구조 (Next.js 15)

### 페이지 구성

```
frontend/src/app/
├── page.tsx                      # 메인 홈 (첨삭 서비스 소개)
│   - 답안지 첨삭 버튼 → 파일 업로드 화면
│   - 관리자 버튼 → 관리자 페이지
│
├── v1/
│   ├── main/                     # 사용자 첨삭 화면
│   │   - PDF/텍스트 드래그 업로드
│   │   - 첨삭 시작 버튼
│   │   - 분석 결과 3분할 뷰
│   │     (쟁점 분석 / 논리 평가 / 표현 검토)
│   │
│   └── admin/                    # 관리자 화면
│       - 학습 데이터셋 업로드 (JSONL/PDF)
│       - 업로드 결과 표시
│       - 학습된 내용 요약 코멘트 표시
│
└── api/v1/
    ├── submission/route.ts        # 답안 제출 API 연동
    ├── reasoning/route.ts         # 추론 API 연동
    ├── feedback/route.ts          # 피드백 API 연동
    └── admin/training/route.ts    # 학습 데이터 업로드 API 연동
```

### 프론트-백엔드 연결 구조

```
Next.js App Router
  → /api/v1/* (Next.js API Route)
    → FastAPI Backend (localhost:8000/api/v1/*)
      → WorkflowManager (오케스트레이터)
```

---

## SLIDE 11 | 데이터베이스 설계

### 테이블 구조 (NeonDB / PostgreSQL)

```
problems ──────────────────────────────┐
(id, title, content, meta)             │
         │                             │
         ▼                             │
reference_answers                      │
(id, problem_id, content, structure)   │
         │                             │
         ▼                             │
issues                                 │
(id, reference_answer_id,              │
 issue_type, title, keywords)          │
                                       │
user_answers ──────────────────────────┤
(id, problem_id, submission_type,      │
 raw_content, processed_content,       │
 status)                               │
         │                             │
         ▼                             │
answer_structures                      │
(id, user_answer_id,                   │
 paragraphs, sentences, word_count)    │
         │                             │
         ▼                             │
reasoning_tasks ◄──────────────────────┘
(id, task_type, status,
 user_answer_id, reference_answer_id)
         │
         ▼
reasoning_results
(id, task_id, result_type,
 content, confidence, metrics)
         │
         ▼
feedbacks
(id, user_answer_id, reasoning_task_id,
 overall_score, scores, summary)
         │
         ▼
feedback_items
(id, feedback_id, item_type,
 severity, title, description, suggestion)
```

### 공통 믹스인 (TimestampMixin)
모든 테이블에 `created_at`, `updated_at` 자동 관리

### 마이그레이션 관리
Alembic으로 스키마 버전 관리 (현재 버전: `a637b9e3a950`)

---

## SLIDE 12 | API 설계 (44개 엔드포인트)

### 엔드포인트 분류

| 도메인 | 엔드포인트 수 | 주요 기능 |
|--------|-------------|----------|
| Reference | 16개 | 문제/모범답안/쟁점 CRUD |
| Submission | 10개 | 답안 제출, 구조 분석, OCR |
| Reasoning | 10개 | 쟁점/논리/표현/종합 분석 |
| Feedback | 8개 | 피드백 생성, 리포트 |
| Training | 별도 | 학습 데이터/작업/모델 버전 관리 |

### 핵심 엔드포인트

```bash
# 종합 분석 (오케스트레이터 → 정책 기반)
POST /api/v1/reasoning/analyze/comprehensive

# 피드백 자동 생성 (오케스트레이터 → 정책 기반)
POST /api/v1/feedback/generate

# 학습 데이터 등록 (오케스트레이터 → 규칙 기반)
POST /api/v1/training/data

# 전체 첨삭 리포트
POST /api/v1/feedback/report
```

---

## SLIDE 13 | 구현 패턴 & 설계 원칙

### 1. Domain-Driven Design (DDD)
- 4개 독립 도메인: Reference / Submission / Reasoning / Feedback
- 각 도메인: Models → Schemas → Repositories → Services 4계층

### 2. Weakened Star Topology
- Reasoning Domain이 Hub 역할
- 다른 도메인은 MCP 프로토콜로 Reasoning Hub와 통신

### 3. GoF 전략 패턴 (Strategy Pattern)
- `RoutingStrategy` 인터페이스 (ABC)
- `PolicyStrategy` (정책 기반) / `RuleStrategy` (규칙 기반)

### 4. 싱글톤 패턴
- `KoELECTRALoader`: 모델 한 번만 로드, 전역 공유
- `ModelLoader`: ML 모델 싱글톤 관리
- `DatabaseConnection`: DB 연결 풀 싱글톤

### 5. Mixin 패턴
```python
class TimestampMixin:
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

class UserAnswer(Base, TimestampMixin):
    # created_at, updated_at 자동 포함
```

### 6. 비동기 처리 (AsyncIO)
- FastAPI + SQLAlchemy Async + asyncpg
- 모든 DB 및 ML 연산 비동기 처리

---

## SLIDE 14 | 테스트 결과

### 오케스트레이터 통합 테스트 결과 (2026-01-27)

| 테스트 항목 | 유형 | 결과 | HTTP 코드 |
|------------|------|------|----------|
| 학습 데이터 생성 | 규칙 기반 | ✅ 성공 | 201 |
| 종합 분석 (comprehensive_analysis) | 정책 기반 | ✅ 성공 | 200 |
| 피드백 자동 생성 (generate) | 정책 기반 | ✅ 성공 | 200 |

### 오케스트레이터 로그 확인

```
================================================================================
[ORCHESTRATOR] 요청 처리 시작
   도메인: feedback | 액션: generate
================================================================================
[DECISION] 정책 기반 판단 (사전 필터링): feedback.generate
[STRATEGY] 정책 기반 전략: Star 토폴로지로 라우팅 - feedback.generate
[REASONING HUB] 처리 시작: feedback.generate
[FEEDBACK] 종합 피드백 생성 완료: 종합 74.5점
================================================================================
[ORCHESTRATOR] 요청 처리 완료 | 전략: policy | 액션: generate
================================================================================
```

### DB 마이그레이션 현황

| 마이그레이션 | 내용 | 상태 |
|------------|------|------|
| `a1e0c566a622` | 전체 초기 테이블 생성 | ✅ 완료 |
| `deaccc34e525` | Training Domain 추가 | ✅ 완료 |
| `550c0fbdd8ea` | reasoning_results.updated_at 추가 | ✅ 완료 |
| `a637b9e3a950` | feedback_items.updated_at 추가 | ✅ 완료 |

---

## SLIDE 15 | 구현 단계별 진행 현황

### Phase 완료 현황

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 0 | Core 기반 (ML, DB, MCP, Config, Logger) | ✅ 완료 |
| Phase 1 | Reference Domain (16개 API) | ✅ 완료 |
| Phase 2 | Submission Domain (10개 API) | ✅ 완료 |
| Phase 3 | Reasoning Domain (10개 API, 더미 분석) | ✅ 완료 |
| Phase 4 | Feedback Domain (8개 API) | ✅ 완료 |
| Phase 5 | 오케스트레이터 (KoELECTRA + GoF 전략 패턴) | ✅ 완료 |
| Phase 6 | EXAONE 실제 모델 Fine-tuning | 🔜 진행 예정 |
| Phase 7 | OCR 실제 연동 | 🔜 예정 |
| Phase 8 | 프론트엔드 완성 | 🔜 진행 중 |

---

## SLIDE 16 | 해결한 기술적 난제들

### 1. SQLAlchemy 세션 지속성 문제
- **문제**: `Instance '<ReasoningTask>' is not persistent within this Session`
- **원인**: 비동기 세션에서 객체 flush 전 refresh 시도
- **해결**: `session.add()` → `session.flush()` 순서 명시적 처리

### 2. DB 스키마 불일치 오류
- **문제**: `UndefinedColumnError: column updated_at does not exist`
- **원인**: `TimestampMixin` 추가 후 기존 테이블에 컬럼 미반영
- **해결**: Alembic 마이그레이션으로 `reasoning_results`, `feedback_items` 컬럼 추가

### 3. Windows 인코딩 문제
- **문제**: `UnicodeEncodeError: 'cp949' codec can't encode character`
- **원인**: 로그 메시지 내 이모지 → Windows 기본 인코딩(cp949) 불일치
- **해결**: `sys.stdout.reconfigure(encoding='utf-8')` 적용

### 4. JSONL 필드명 불일치
- **문제**: 업로드한 JSONL의 `problem`, `reference_answer`가 미인식
- **원인**: 백엔드 기대값은 `problem_text`, `reference_answer_text`
- **해결**: 프론트 API Route에서 대체 필드명 매핑 처리

### 5. Pydantic 422 오류
- **문제**: `ComprehensiveAnalysisRequest` 필수 필드 미충족
- **원인**: 학습 전 참조 답안/문제 ID가 없는 경우
- **해결**: 필드를 `Optional`로 변경, 없는 경우 더미 데이터 사용

---

## SLIDE 17 | 향후 계획

### 단기 (1~2개월)
1. **EXAONE Fine-tuning 완료**
   - 민사소송법 JSONL 데이터셋 구축
   - LoRA 학습 파이프라인 실행
   - ReasoningEngine에 실제 모델 연동

2. **프론트엔드 완성**
   - 첨삭 결과 시각화 (점수 차트, 쟁점 하이라이팅)
   - 실시간 분석 진행 표시

### 중기 (3~6개월)
3. **OCR 연동**
   - 필기 답안 이미지 → 텍스트 변환
   - Google Vision API 또는 Tesseract

4. **자동화 완성**
   - MCP Agent: 데이터 변경 감지 → 자동 학습 트리거
   - WebSocket 기반 실시간 학습 진행 모니터링

### 장기
5. **배포**
   - AWS EC2 + NeonDB 클라우드 배포
   - CI/CD 파이프라인 구축

---

## SLIDE 18 | 프로젝트 요약 (정리)

### 구현된 것

```
✅ 4-Layer 아키텍처 (Frontend → Router → Orchestrator → Domain)
✅ DDD 기반 4개 도메인 (Reference / Submission / Reasoning / Feedback)
✅ KoELECTRA 기반 정책/규칙 자동 판단 오케스트레이터
✅ GoF 전략 패턴 (PolicyStrategy / RuleStrategy)
✅ Weakened Star Topology (Reasoning Hub 중심)
✅ FastAPI 비동기 REST API (44개 엔드포인트)
✅ PostgreSQL(NeonDB) + Alembic 마이그레이션
✅ LoRA 기반 경량 파인튜닝 파이프라인 구조
✅ Next.js 15 관리자/사용자 프론트엔드
✅ JSONL 기반 학습 데이터 업로드 및 관리
```

### 기술적 강점

| 강점 | 내용 |
|------|------|
| 확장성 | 새 분석 타입 추가 시 Strategy만 추가 |
| 유지보수성 | DDD 도메인 분리로 독립적 수정 가능 |
| 성능 | 비동기 처리로 높은 동시성 |
| 자동화 | 데이터 입력 후 모든 과정 자동 처리 |
| AI 통합 | KoELECTRA + EXAONE 이중 모델 구조 |

---

*본 기술서는 2026년 1월 27일 기준 프로젝트 상태를 반영합니다.*  
*참고 파일: `strategy/` 폴더 내 전략 문서 53~57번*
