# minso 도메인 산개 참조 정리

> Phase 1~5 진행 시, **minso 밖**에서 feedback/reference/submission/reasoning을 참조하는 파일 목록입니다.
> training은 minso에서 제외되어 `app/domain/training` 및 루트 `training/` 에서 관리합니다.

---

## 1. Import 경로 불일치

- **실제 코드 위치**: `app/domain/v1/minso/{feedback|reference|submission|reasoning}/`
- **training**: `app/domain/training` (models, repos, schemas, services re-export) + 루트 `training/services.py`
- **현재 사용 중인 import**: **`app.domain.v1.minso.{feedback|reference|submission|reasoning}....`** (일괄 변경 완료), `app.domain.training....` (training 전용)
  → minso 도메인은 `app.domain.v1.minso.*` 기준으로 통일됨. training은 `app.domain.training` 별도.

---

## 2. minso 밖에서 참조하는 파일 (수정 대상)

### 2.1 API 라우터 (`app/api/v1/`)

| 파일 | 참조 내용 |
|------|------------|
| `feedback.py` | `app.domain.v1.minso.feedback.services`, `app.domain.v1.minso.feedback.schemas` |
| `reference.py` | `app.domain.v1.minso.reference.services`, `app.domain.v1.minso.reference.schemas` |
| `submission.py` | `app.domain.v1.minso.submission.services`, `app.domain.v1.minso.submission.schemas` |
| `reasoning.py` | `app.domain.v1.minso.reasoning.services`, `app.domain.v1.minso.reasoning.schemas` |
| `training.py` | `app.domain.training.services`, `app.domain.training.schemas`, `app.domain.training.models` |

### 2.2 오케스트레이션 (`app/core/orchestration/`)

| 파일 | 참조 내용 |
|------|------------|
| `nodes.py` | `app.domain.v1.minso.reasoning.orchestrators.reasoning_hub`, `app.domain.training.services`, `app.domain.v1.minso.submission.services`, `app.domain.v1.minso.reasoning.services`, `app.domain.v1.minso.reference.services`, `app.domain.v1.minso.feedback.services` |
| `strategies/rule_strategy.py` | `app.domain.training.services`, `app.domain.v1.minso.submission.services`, `app.domain.v1.minso.reasoning.services`, `app.domain.v1.minso.reference.services`, `app.domain.v1.minso.feedback.services` |
| `strategies/policy_strategy.py` | `app.domain.v1.minso.reasoning.orchestrators.reasoning_hub` |

### 2.3 유틸 (`app/core/utils/`)

| 파일 | 참조 내용 |
|------|------------|
| `test_data_factory.py` | `app.domain.v1.minso.submission.services`, `app.domain.v1.minso.submission.schemas`, `app.domain.v1.minso.reference.services`, `app.domain.v1.minso.reference.schemas`, `app.domain.v1.minso.reference.models`, `app.domain.v1.minso.reference.repositories` |

---

## 3. minso 내부 상호 참조 (Phase 1 이후 import만 정리)

- `reasoning/orchestrators/reasoning_hub.py` → feedback.services, reasoning.services (training 분리됨)
- `reasoning/services.py` → submission.repositories, reference.repositories
- `feedback/services.py` → reasoning.repositories
- training 관련: `app/domain/training` + 루트 `training/services.py` 에서 관리 (minso 내부 참조 없음)

Phase 1에서 **모델**을 `minso.models.bases` 로 통합한 뒤, 위 서비스/리포지토리는 **모델만** `from app.domain.v1.minso.models ...` 로 바꾸면 됩니다.
(나머지 서비스·리포지토리 경로는 Phase 3·4에서 hub/spokes 이전 시 정리)

---

## 4. 권장 조치

1. **Phase 1**
   - 모델을 `models/bases/` 로 이전하고, 기존 `feedback.models` 등은 `minso.models` 에서 re-export.
   - minso **내부**에서는 `from app.domain.v1.minso.models ...` 또는 기존 `from .models import ...`(패키지 내 re-export 유지) 사용.

2. **API / core 쪽 import 정리 (별도 작업)**
   - 옵션 A: `app/domain/__init__.py` 에서
     `from app.domain.v1.minso import feedback, reference, submission, reasoning` (training은 `app.domain.training` 별도)
     로 re-export 해서 기존 `app.domain.feedback` 등이 동작하도록 유지.
   - 옵션 B: `app.domain.feedback` → `app.domain.v1.minso.feedback` 등으로 **일괄 치환**.

이 문서는 Phase 진행하면서 참조 바꿀 때 함께 업데이트하면 됩니다.

---

## 5. Phase 1 완료 후 (models 통합)

- **단일 소스**: `app.domain.v1.minso.models` (및 `models.bases.feedback` 등)에 엔티티 정의.
- **기존 패키지**: `feedback.models`, `reference.models` 등은 `...models`(minso.models)에서 re-export 하므로,
  `from app.domain.v1.minso.feedback.models import Feedback` 등 **minso 내부·외부** 기존 사용처는 그대로 동작.
- **주의**: API·core 쪽은 여전히 `app.domain.feedback`(v1.minso 없음) 경로를 쓰고 있으면,
  실제 패키지가 `app.domain.v1.minso.feedback` 이므로 **import 경로가 잘못된 상태**일 수 있음.
  Phase 5 또는 별도 작업에서 `app.domain` re-export 또는 일괄 치환 필요.
