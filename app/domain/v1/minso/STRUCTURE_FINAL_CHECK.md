# app/domain/v1 구조 최종 점검

> Star 토폴로지 통합 후, 의도한 대로 분리되었는지 최종 확인한 결과입니다.

---

## 1. 전체 구조 요약

```
app/domain/v1/
├── __init__.py
├── minso/
│   ├── hub/           # 중앙: 리포지토리, 오케스트레이터, 라우팅
│   ├── spokes/        # 말단: 서비스, 에이전트
│   ├── models/        # 엔티티(bases), DTO(transfers), 상태(states)
│   ├── shared/        # 예외, 값객체, 이벤트
│   └── (feedback|reasoning|reference|submission 폴더 없음 — 삭제 완료)
└── patent/             # (빈 패키지)
```

---

## 2. 역할별 분리 확인

### 2.1 hub (중앙)

| 항목 | 의도 | 실제 | 판정 |
|------|------|------|------|
| **repositories/** | 데이터 접근 단일 소스 | feedback/reference/submission/reasoning 리포지토리 구현체, `minso.models`만 참조 | ✅ |
| **orchestrators/** | 정책/라우팅, spokes만 참조 | `reasoning_orchestrator.py`만 구현(ReasoningHub), `spokes.services`·shared만 import | ✅ |
| **routing/** | 요청 분기 | `__init__.py`만 있음 (빈 폴더) | ⚠️ stub |
| **mcp_central/** | MCP 툴 | `__init__.py`만 있음 (빈 폴더) | ⚠️ stub |

- **의존성**: hub.repositories → `minso.models`만 사용. hub.orchestrators → `spokes.services` + shared만 사용. **역할 분리 OK.**

### 2.2 spokes (말단)

| 항목 | 의도 | 실제 | 판정 |
|------|------|------|------|
| **services/** | 도메인별 비즈니스 로직 | feedback/reference/submission/reasoning_service 구현, hub.repositories + models + shared 사용 | ✅ |
| **agents/** | 에이전트 | 4개 파일 모두 내용 없음 | ⚠️ stub |
| **infrastructure/** | OCR 등 인프라 | `__init__.py`만 있음 | ⚠️ stub |

- **의존성**: spokes.services → hub.repositories, models, models.transfers, shared만 사용. **API/외부는 spokes만 보는 구조 유지.**

### 2.3 models

| 항목 | 의도 | 실제 | 판정 |
|------|------|------|------|
| **bases/** | ORM 엔티티 단일 소스 | feedback/reference/submission/reasoning 엔티티, `core.database`만 참조 | ✅ |
| **transfers/** | API/레이어 간 DTO | Pydantic 모델만, 도메인별 `*_transfer.py` | ✅ |
| **states/** | 워크플로우 상태(TypedDict 등) | `__init__.py`·feedback_state 등 파일 존재하나 내용 없음 | ⚠️ stub |
| **enums/** | 공통 Enum | `__init__.py`만 있음. Enum은 bases/transfers에 각각 정의 | ⚠️ stub |

- **bases vs transfers**: bases = DB 엔티티+Enum, transfers = 요청/응답 DTO. 서비스는 bases(ORM) + transfers(DTO) 구분해서 사용. **분리 OK.**

### 2.4 shared

| 항목 | 의도 | 실제 | 판정 |
|------|------|------|------|
| 예외 / 값객체 / 이벤트 | 도메인 공통 | exceptions, value_objects, events 정의 후 `__init__.py`에서 re-export | ✅ |

---

## 3. 의존성 방향 검증

- **API (`app/api/v1/`)**: `spokes.services.*` + `models.transfers` 만 사용. hub/models.bases 직접 참조 없음. ✅
- **Spokes 서비스**: `hub.repositories`, `models`, `models.transfers`, `shared` 만 사용. ✅
- **Hub 리포지토리**: `models`(엔티티) + (reasoning만) `shared`(예외/값객체). ✅
- **Hub 오케스트레이터**: `spokes.services`, `shared` 만 사용. ✅
- **models.bases**: `app.core.database` 만 참조. 다른 도메인 레이어 없음. ✅

**역할별로 의도한 방향으로만 의존하고 있음.**

---

## 4. Training 분리

- Training 도메인은 minso 밖: `app.domain.training` + 루트 `training/` 에서 관리.
- minso 내부에 training 폴더/서비스 없음. **의도대로 분리됨.**

---

## 5. 애매한 부분 (판단 필요)

1. **hub/orchestrators**
   - `reasoning_orchestrator.py`만 구현됨.
   - `feedback_orchestrator.py`, `reference_orchestrator.py`, `submission_orchestrator.py`, `chat_orchestrator.py` 는 **빈 파일**.
   - → 나중에 채울 stub인지, 불필요하면 정리할지 결정 필요.

2. **hub/routing, hub/mcp_central**
   - 디렉터리만 있고 내용 없음.
   - → placeholder로 둘지, 사용 계획 없으면 제거할지 결정 필요.

3. **spokes/agents**
   - feedback/reference/reasoning/submission_agent.py 모두 **빈 파일**.
   - → stub으로 둘지, 구현 예정 없으면 제거할지 결정 필요.

4. **models/states, models/enums**
   - states: 파일은 있으나 비어 있음. enums: `__init__.py`만 있음.
   - → LangGraph 상태/공통 Enum 계획에 맞춰 채울지, 아니면 정리할지 결정 필요.

5. **SCATTERED_REFERENCES.md**
   - 내용이 레거시 경로(feedback.services, reference.models 등) 기준으로 되어 있음.
   - → “Phase 5 완료, 레거시 폴더 삭제됨”으로 갱신할지 결정 필요.

---

## 6. 최종 결론

- **역할 분리**: hub(리포지토리·오케스트레이터) / spokes(서비스) / models(bases·transfers) / shared 는 의도대로 분리되어 있음.
- **의존성**: API → spokes·transfers, Spokes → hub·models·shared, Hub → models 또는 spokes·shared 만 사용. 역방향/순환 없음.
- **레거시 폴더**: feedback, reasoning, reference, submission 제거 완료.
- **애매한 부분**: 위 5항은 구조적 하자 없고, “나중에 채울 stub vs 정리” 수준이므로 필요 시 판단만 하면 됨.

이 문서는 점검 시점 기준 최종 구조 확인용입니다.
