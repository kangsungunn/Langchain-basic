# 민사소송법(minso) 서브도메인 스타 토폴로지 통합 전략

> `app/domain/v1/minso` 하위의 **hub / spokes / models / shared** 4개 폴더를 기반으로,
> 기존 **feedback, reasoning, reference, submission, training** 폴더 및 코드를 통합하는 전략입니다.
> 구조 참고: `1.PROJECT_STRUCTURE_LEARNING.md`, `2.EMBEDDING_SYSTEM_ARCHITECTURE.md` (구조만 적용).

---

## 1. 목표 구조 (스타 토폴로지)

참고 문서의 **hub(중앙) / spokes(말단) / models(모델·상태) / shared(공통)** 역할을 minso에 맞게 적용합니다.

| 폴더 | 역할 (참고 문서 기준) | minso에서 담당할 것 |
|------|------------------------|----------------------|
| **hub/** | MCP·오케스트레이터·리포지토리·라우팅 | 첨삭 흐름 조율, 문제/답안/피드백/추론/학습 **중앙 조정**, 라우팅 |
| **spokes/** | 인프라·서비스·에이전트·툴 | 각 도메인별 **실제 처리**(피드백 생성, 추론 엔진, OCR, 학습 배치 등) |
| **models/** | ORM·상태·프롬프트 | 엔티티(bases), LangGraph 등 상태(states), 공통 스키마/타입 |
| **shared/** | 도메인 공통 | 이벤트, 예외, 값 객체(value_objects) |

---

## 2. 현재 minso 구조 vs 통합 후 매핑

### 2.1 현재 구조

```
minso/
├── hub/           # 거의 비어 있음 (mcp_central, orchestrators, repositories, routing __init__.py만)
├── spokes/        # 비어 있음
├── models/        # 비어 있음
├── shared/        # events, exceptions, value_objects (내용 최소)
├── feedback/      # models, repositories, schemas, services
├── reasoning/     # models, schemas, services, repositories + agents/, orchestrators/
├── reference/     # models, repositories, schemas, services
├── submission/    # models, repositories, schemas, services
└── training/      # models, repositories, schemas, services
```

### 2.2 통합 후 목표 구조 (참고 문서 구조만 적용)

```
minso/
├── hub/                           # 중앙: 조율·라우팅·집약 리포지토리
│   ├── mcp_central/               # (선택) 민사소송법용 MCP 툴
│   ├── orchestrators/             # 첨삭·추론·학습 오케스트레이터
│   │   ├── feedback_orchestrator.py
│   │   ├── reasoning_orchestrator.py   # reasoning.reasoning_hub 이동
│   │   └── training_orchestrator.py
│   ├── repositories/              # 집약 조회·트랜잭션 경계 (필요 시)
│   │   ├── feedback_repository.py
│   │   ├── reference_repository.py
│   │   ├── submission_repository.py
│   │   ├── reasoning_repository.py
│   │   └── training_repository.py
│   └── routing/                   # 요청/도메인 분기
│       └── request_classifier.py  # reasoning 분류 로직 등
│
├── spokes/                        # 말단: 실제 비즈니스·인프라
│   ├── services/                  # 도메인별 서비스 (기존 services 이동)
│   │   ├── feedback_service.py
│   │   ├── reference_service.py
│   │   ├── submission_service.py
│   │   ├── reasoning_service.py
│   │   └── training_service.py
│   ├── agents/                    # reasoning/agents → 여기
│   │   ├── expression_evaluator.py
│   │   ├── issue_detector.py
│   │   ├── logic_analyzer.py
│   │   └── reasoning_agent.py
│   └── infrastructure/            # (선택) OCR, 임베딩 등 외부 연동
│       └── ...
│
├── models/                        # 엔티티·상태·공통 타입
│   ├── bases/                     # ORM 엔티티 (기존 models 통합)
│   │   ├── feedback.py
│   │   ├── reference.py
│   │   ├── submission.py
│   │   ├── reasoning.py
│   │   └── training.py
│   ├── states/                    # (선택) LangGraph 등 상태 스키마
│   └── schemas/                   # (선택) Pydantic 등 공통 스키마만, 또는 API 레이어 유지
│
├── shared/                        # 도메인 공통
│   ├── events.py
│   ├── exceptions.py
│   └── value_objects.py
│
└── (기존 feedback, reasoning, reference, submission, training)
    → 옵션 A: deprecated re-export만 유지
    → 옵션 B: 삭제 후 import 경로 일괄 변경
```

---

## 3. 폴더별 이전 매핑 (어디로 옮길지)

### 3.1 models/

| 현재 위치 | 이전 대상 | 비고 |
|-----------|-----------|------|
| feedback/models.py | models/bases/feedback.py | Feedback, FeedbackItem 등 엔티티 |
| reference/models.py | models/bases/reference.py | Problem, ReferenceAnswer, Issue |
| submission/models.py | models/bases/submission.py | UserAnswer, AnswerStructure 등 |
| reasoning/models.py | models/bases/reasoning.py | ReasoningTask, ReasoningResult 등 |
| training/models.py | models/bases/training.py | TrainingData, TrainingJob, ModelVersion |

- **schemas**(Pydantic)는 API에서만 쓰면 `app/api/` 쪽에 두거나, 도메인 공통이면 `models/schemas/` 또는 각 spoke 서비스와 같은 레벨에 둘 수 있음. (참고 문서는 “모델 = ORM·상태” 위주이므로 스키마는 별도 결정.)

### 3.2 hub/

| 현재 위치 | 이전 대상 | 비고 |
|-----------|-----------|------|
| feedback/repositories.py | hub/repositories/feedback_repository.py | CRUD·집약 조회 |
| reference/repositories.py | hub/repositories/reference_repository.py | |
| submission/repositories.py | hub/repositories/submission_repository.py | |
| reasoning/repositories.py | hub/repositories/reasoning_repository.py | |
| training/repositories.py | hub/repositories/training_repository.py | |
| reasoning/orchestrators/reasoning_hub.py | hub/orchestrators/reasoning_orchestrator.py | 추론 흐름 조율 |
| reasoning 분류/라우팅 로직 | hub/routing/request_classifier.py | 요청 타입별 hub 라우팅 |

- 오케스트레이터가 “여러 spoke를 조합해 하나의 유스케이스”를 만든다면 `hub/orchestrators/`에 두고, 각 spoke는 “단일 책임”만 가진다.

### 3.3 spokes/

| 현재 위치 | 이전 대상 | 비고 |
|-----------|-----------|------|
| feedback/services.py | spokes/services/feedback_service.py | 피드백 생성·저장 등 |
| reference/services.py | spokes/services/reference_service.py | 문제/모범답안/논점 처리 |
| submission/services.py | spokes/services/submission_service.py | 제출 답안·OCR·구조 분석 |
| reasoning/services.py | spokes/services/reasoning_service.py | 추론 태스크 실행 |
| training/services.py | spokes/services/training_service.py | 학습 데이터·작업·모델 버전 |
| reasoning/agents/* | spokes/agents/ | expression_evaluator, issue_detector 등 |

- **FeedbackGenerator, ReasoningEngine, OCRService** 등 “실제 연산/외부 호출”은 spokes에 두고, hub는 이들을 **호출만** 하도록 유지.

### 3.4 shared/

| 현재 위치 | 이전 대상 | 비고 |
|-----------|-----------|------|
| (기존) shared/events, exceptions, value_objects | 유지 | |
| feedback/reasoning/... 에서 도메인 공통 타입·예외 | shared/value_objects.py, exceptions.py | 중복 제거 후 공통만 |

---

## 4. 전략 요약 (순서 권장)

### Phase 1: models 통합

1. `models/bases/` 생성 후 feedback/reference/submission/reasoning/training의 **models.py**를 각각 `models/bases/{도메인}.py`로 이전.
2. `models/__init__.py`에서 bases를 re-export.
3. 기존 `from app.domain.v1.minso.feedback.models import ...` 사용처를 `from app.domain.v1.minso.models.bases.feedback import ...` (또는 `models`에서 re-export)로 변경.

### Phase 2: shared 정리

1. feedback/reasoning/reference/submission/training에서 **도메인 공통** 예외·값 객체를 추출해 `shared/exceptions.py`, `shared/value_objects.py`에 반영.
2. 각 도메인 코드에서는 `from app.domain.v1.minso.shared import ...` 사용하도록 정리.

### Phase 3: spokes 통합

1. `spokes/services/` 생성 후 feedback/reference/submission/reasoning/training의 **services.py**를 각각 `spokes/services/{도메인}_service.py`로 이전.
2. `reasoning/agents/*`를 `spokes/agents/`로 이전.
3. 서비스·에이전트 내부 import를 **models**, **shared** 새 경로로 수정.
4. (선택) 외부 연동(OCR, 임베딩 등)이 있으면 `spokes/infrastructure/`에 배치.

### Phase 4: hub 통합

1. `hub/repositories/`에 feedback/reference/submission/reasoning/training의 **repositories.py**를 각각 `hub/repositories/{도메인}_repository.py`로 이전.
2. `reasoning/orchestrators/reasoning_hub.py`를 `hub/orchestrators/reasoning_orchestrator.py`로 이전.
3. 필요 시 `feedback_orchestrator`, `training_orchestrator` 등을 hub/orchestrators에 추가.
4. 라우팅/분류 로직을 `hub/routing/`으로 모음.
5. hub 코드는 **spokes 서비스·models·shared**만 참조하도록 하고, spokes는 hub를 참조하지 않도록 유지 (의존성: hub → spokes, hub → models, hub → shared).

### Phase 5: 기존 폴더 처리

- **옵션 A (점진적)**
  feedback, reasoning, reference, submission, training 폴더는 **deprecated**로 두고, `__init__.py`에서만 새 경로를 re-export.
  예: `from app.domain.v1.minso.models.bases.feedback import *` 등.
  이후 API·테스트를 새 경로로 바꾼 뒤 폴더 제거.

- **옵션 B (일괄)**
  위 1~4 완료 후, 기존 5개 폴더를 삭제하고 전체 코드베이스에서 import를 `hub`, `spokes`, `models`, `shared` 기준으로 일괄 변경.

---

## 5. 의존성 원칙 (참고 문서 구조 유지)

- **hub** → spokes, models, shared 사용 가능. (중앙이 말단·모델·공통을 알고 있음)
- **spokes** → models, shared만 사용. hub 참조 금지. (말단은 중앙을 알지 않음)
- **models** → shared만 사용 가능. hub/spokes 참조 금지.
- **shared** → 다른 도메인 폴더 참조 금지.

이렇게 하면 “스타 토폴로지”처럼 hub가 중앙에서 조율하고, spokes가 실제 작업을 수행하는 구조가 유지됩니다.

---

## 6. 체크리스트 (작업 시 참고)

- [x] models/bases/ 에 5개 도메인 엔티티 이전 및 import 변경 (Phase 1 완료)
- [x] shared에 공통 예외·값 객체 정리 (Phase 2 완료)
- [ ] spokes/services/, spokes/agents/ 이전 및 import 변경
- [ ] hub/repositories/, hub/orchestrators/, hub/routing/ 이전 및 import 변경
- [ ] API 라우터 등 외부에서 minso를 참조하는 부분을 새 경로로 변경
- [ ] 기존 feedback/reasoning/reference/submission/training 폴더: re-export 유지 또는 삭제
- [ ] 테스트·실행으로 회귀 없음 확인

이 전략에 따라 단계별로 옮기면, 강사님 구조(스타 토폴로지·hub/spokes/models/shared)만 참고한 민사소송법 첨삭 서브도메인 재구성이 가능합니다.

---

## 7. Phase 2 완료 요약 (shared 정리)

- **shared/exceptions.py**: `MinsoDomainError`, `EntityNotFoundError`, `DomainValidationError` 정의. 후二者는 `ValueError` 상속으로 기존 `except ValueError` 호환 유지.
- **shared/value_objects.py**: `EntityId`(NewType), 엔티티 종류 상수(`ENTITY_USER_ANSWER`, `ENTITY_REASONING_TASK` 등) 정의.
- **shared/events.py**: 도메인 이벤트 스텁 (`UserAnswerCreated`, `ReasoningTaskCompleted`, `FeedbackGenerated`, `TrainingJobStarted` 등). 발생·구독은 Phase 4 이후 구현 예정.
- **shared/__init__.py**: exceptions, value_objects, events re-export.
- **도메인 코드**: `feedback/services.py`, `reasoning/services.py`, `reasoning/repositories.py`, `reasoning/orchestrators/reasoning_hub.py`, `submission/services.py`, `training/services.py`에서 `raise ValueError`를 `EntityNotFoundError` / `DomainValidationError`로 교체. 엔티티 부재는 `EntityNotFoundError(entity_type, entity_id)`, 검증/비즈니스 규칙 위반은 `DomainValidationError(message)` 사용.
