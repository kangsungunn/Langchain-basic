# app/core·api 정리 요약

> 기준: **app/api**, **app/domain** 이 기준. core는 인프라·오케스트레이션만 유지.

---

## 1. 제거·통합한 항목

### app/core

| 항목 | 이유 |
|------|------|
| **app/core/database.py** (파일) | `app/core/database/` 패키지와 동일 경로. Python은 패키지 우선이라 이 파일은 로드되지 않던 dead code. 패키지 `__init__.py`에 mixin re-export 추가 후 삭제. |
| **app/core/database/models.py** | 비어 있음. 도메인 모델은 app/domain, training에만 두기로 한 구조와 일치하므로 제거. |

### app/api

| 항목 | 이유 |
|------|------|
| **app/api/v1/feedback_router.py** | 비어 있음. 실제 라우터는 `feedback.py`. |
| **app/api/v1/reasoning_router.py** | 비어 있음. 실제 라우터는 `reasoning.py`. |
| **app/api/v1/reference_router.py** | 비어 있음. 실제 라우터는 `reference.py`. |
| **app/api/v1/submission_router.py** | 비어 있음. 실제 라우터는 `submission.py`. |

---

## 2. 통일한 진입점

- **DB**: `from app.core.database import get_session, Base, TimestampMixin, ...` 한 곳에서만 사용.
- **API**의 `get_session` import를 `app.core.database.session` → `app.core.database` 로 변경해 core 진입점 통일.

---

## 3. 유지한 구조 (중복 아님)

| 위치 | 역할 | 비고 |
|------|------|------|
| **core/database/** | connection, session, base, mixin | 도메인/API가 사용하는 인프라. domain에 두지 않음. |
| **core/orchestration/** | workflow, decision_maker, nodes, strategies | 정책/규칙 라우팅·워크플로우. domain 서비스를 호출하는 glue. |
| **core/orchestration/models/states/** | WorkflowState, BaseWorkflowState | LangGraph 워크플로우 상태. domain/models/states(도메인 상태)와 별개. |
| **core/ml/** | embeddings, inference, model_loader | 도메인 spoke가 사용하는 인프라. |
| **core/utils/** | logger, test_data_factory, pdf_parser 등 | 공용 유틸. |
| **core/mcp/** | 프로토콜·전송 | MCP 인프라. |
| **api/v1/*.py** | feedback, reference, submission, reasoning, training | 각각 하나의 라우터 모듈. domain 서비스·transfers만 참조. |

---

## 4. 기준 정리

- **app/domain**: 비즈니스 로직·엔티티·DTO (minso hub/spokes/models, training).
- **app/api**: HTTP 진입점만. domain 서비스·transfers 참조.
- **app/core**: DB, 세션, 오케스트레이션, ML, MCP, 공용 유틸. domain·api를 기준으로 두고, 그에 맞춰 중복만 제거함.
