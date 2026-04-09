# MCP 자동화 구조 — 현재 구현 범위 & 남은 작업

> **데이터가 이미 DB에 있다고 가정**했을 때, 지금까지 구현된 흐름과 MCP 자동화 완성을 위해 필요한 작업을 정리합니다.

---

## 1. 데이터가 있다고 가정했을 때 “지금까지 구현된 것”

### 1.1 DB & 스키마

| 구분 | 내용 |
|------|------|
| **도메인 테이블** | `problems`, `reference_answers`, `user_answers`, `reasoning_tasks`, `reasoning_results`, `feedbacks`, `feedback_items` 등 |
| **임베딩 테이블** | `reference_answer_embeddings`, `user_answer_embeddings`, `reasoning_task_embeddings`, `feedback_embeddings` (pgvector 768차원) |
| **마이그레이션** | Alembic으로 위 테이블 생성 가능 (`alembic upgrade head`) |

### 1.2 임베딩 인프라

| 구분 | 내용 |
|------|------|
| **모델 경로** | `EMBEDDING_MODEL_PATH` → `artifacts/embedding_models/jhgan--ko-sroberta-multitask` (Sentence-BERT, 768차원) |
| **로더** | `app/core/ml/embeddings.py`: Sentence-BERT 형식이면 `sentence_transformers`, 아니면 HuggingFace `AutoModel` |
| **MCP 툴** | 중앙 MCP 서버의 `koelectra_embed_text(text)` → 위 임베더로 벡터 생성 후 반환 |

### 1.3 중앙 MCP 서버 (`hub/mcp/central_mcp_server.py`)

| 툴 | 용도 |
|----|------|
| **ExaOne** | `exaone_generate_text`, `exaone_generate_code`, `exaone_analyze_reference_data`, `exaone_analyze_submission_data`, `exaone_analyze_reasoning_data`, `exaone_analyze_feedback_data` |
| **KoELECTRA** | `koelectra_embed_text` (임베딩 마이그레이션에서 사용) |
| **통합** | `koelectra_to_exaone_pipeline` (임베딩 후 ExaOne 분석) |

- `get_minso_central_mcp_server()` 싱글톤으로 접근, `call_tool(tool_name, **kwargs)` 로 호출.

### 1.4 MinsoHub (라우팅 + 임베딩 마이그레이션)

| 기능 | 내용 |
|------|------|
| **process(domain, action, request)** | DecisionMaker로 policy/rule 판단 → policy면 도메인별 오케스트레이터, rule이면 서비스 직접 호출 |
| **trigger_embedding_migration(domain, batch_size)** | 도메인별로 DB 조회 → 텍스트 조합 → MCP `koelectra_embed_text` 호출 → 해당 `*_embeddings` 테이블에 저장 |

- **정책(오케스트레이터)**: `reasoning` → ReasoningHub, `feedback` → FeedbackOrchestrator (Phase 3 반영).
- **규칙(서비스)**: training, submission, reasoning(CRUD), feedback(CRUD) 등은 각 서비스로 직접 라우팅.

### 1.5 “데이터가 있을 때” 흐름 (수동 트리거 기준)

1. **Reference**
   - `reference_answers`에 행이 있음
   - `GET /api/v1/reference/embedding` 호출
   → 배치로 조회 → `_build_reference_text` → MCP `koelectra_embed_text` → `reference_answer_embeddings`에 저장

2. **Submission**
   - `user_answers`에 행이 있음
   - `GET /api/v1/submission/embedding` 호출
   → 배치로 조회 → `_build_submission_text` → MCP `koelectra_embed_text` → `user_answer_embeddings`에 저장

3. **Reasoning**
   - `reasoning_tasks`에 행이 있음
   - `GET /api/v1/reasoning/embedding` 호출
   → 배치로 조회 → `_build_reasoning_text` → MCP `koelectra_embed_text` → `reasoning_task_embeddings`에 저장

4. **Feedback**
   - `feedbacks`에 행이 있음
   - `GET /api/v1/feedback/embedding` 호출
   → 배치로 조회 → `_build_feedback_text` → MCP `koelectra_embed_text` → `feedback_embeddings`에 저장

즉, **데이터가 넣어져 있다는 가정하에** “4개 도메인 모두 수동 API 한 번씩으로 임베딩을 Neon DB(각 `*_embeddings` 테이블)에 채우는 구조”까지는 구현된 상태입니다.

---

## 2. MCP 자동화 “완성”을 위해 남은 작업

전략 문서와 코드 기준. **Phase 1~4 구현으로 2.1(자동 임베딩 1건)·2.2(오케스트레이터 분리)·2.3(제출→추론→피드백 한 번에)·2.4(ExaOne 연동)는 반영된 상태**입니다. 아래는 당시 목표 대비 "남은 작업" 설명이며, 추가 개선(배치 임베딩, ReferenceOrchestrator 맵 등)은 선택입니다.

### 2.1 자동 임베딩 트리거 (선택)

| 현재 | 목표(문서 기준) |
|------|------------------|
| 임베딩은 **사람이** `GET /.../embedding` 호출할 때만 실행 | “API 호출 시 **자동으로** 임베딩 생성” |

**남은 작업 예시:**

- **옵션 A**: 새 데이터가 들어오는 API 성공 시, 해당 도메인에 대해 “방금 넣은 1건만” 임베딩해서 저장 (예: `POST /reference/answers` 성공 시 해당 `reference_answer` 1건만 임베딩).
- **옵션 B**: 주기적/배치 작업(Cron, Celery 등)으로 “아직 임베딩 안 된 행”만 조회해 채우기.

→ “완전 자동”으로 가려면 위 중 하나(또는 둘 다) 설계 후 구현 필요.

### 2.2 도메인별 오케스트레이터 분리 (선택)

| 현재 | 목표(문서 기준) |
|------|------------------|
| `feedback`, `reasoning` 모두 **ReasoningHub** 한 곳에서 처리 | 도메인별 전용 오케스트레이터 (FeedbackOrchestrator, ReferenceOrchestrator 등) |

**남은 작업:**

- `MinsoHub._get_orchestrator_map()` 에서 도메인별로 전용 오케스트레이터를 두고, 각자 `process(domain, action, request)` 및 필요 시 MCP 툴 호출하도록 분리.
- 지금도 동작은 하므로, “구조 정리/확장성” 목적이면 단계적으로 진행 가능.

### 2.3 엔드투엔드 자동 흐름 (제출 → 추론 → 피드백)

| 현재 | 목표 |
|------|------|
| 답안 제출(`submission`) / 추론 실행(`reasoning`) / 피드백 생성(`feedback`) 각각 **별도 API 호출** | “답안 제출 한 번”에 → 추론 자동 실행 → 그 결과로 피드백 자동 생성 |

**남은 작업:**

- 예: `POST /api/v1/submission/answers/text` (또는 image) 성공 시
  - 해당 답안으로 Reasoning 작업 생성 및 실행 (`hub.process(domain="reasoning", ...)`)
  - 그 결과로 Feedback 생성 (`hub.process(domain="feedback", action="generate", ...)`)
- 또는 “제출 후 자동 파이프라인” 전용 API 하나를 두고, 내부에서 submission → reasoning → feedback 순서로 `hub.process` 호출.

→ 이 부분이 연결되면 “제출만 하면 첨삭(피드백)까지 자동”인 MCP 자동화 흐름이 완성됩니다.

### 2.4 ExaOne 분석 툴의 실제 사용 (선택)

| 현재 | 목표 |
|------|------|
| MCP 서버에 `exaone_analyze_*_data`, `exaone_generate_code` 등 **툴은 등록됨** | 오케스트레이터/서비스에서 **실제로 호출**해 분석·코드 생성에 사용 |

**남은 작업:**

- Reasoning/Feedback 생성 시 `call_tool("exaone_analyze_reasoning_data", ...)` 등으로 ExaOne 분석 결과를 입력으로 쓰는지 확인.
- 코드 생성 자동화가 필요하면, 적절한 트리거(예: 모델 스키마 변경 시)에서 `exaone_generate_code` 호출하도록 연결.

### 2.5 코드 생성 자동화 (이미 수동으로 완료된 부분)

- `app/alter_ollama/` 스크립트로 **임베딩 모델 코드**는 이미 생성·반영된 상태.
- “실행만 자동화”하려면: 스키마/도메인 변경 시 해당 스크립트를 CI/스크립트에서 한 번 돌리도록 정리하면 됨.

---

## 3. 요약 표

| 구분 | 상태 | 비고 |
|------|------|------|
| DB 스키마 + 임베딩 테이블 | ✅ 구현됨 | Alembic, pgvector |
| 임베딩 모델 경로/로더 (artifacts/embedding_models) | ✅ 구현됨 | Sentence-BERT 호환 |
| 중앙 MCP 서버 (ExaOne + KoELECTRA 툴) | ✅ 구현됨 | call_tool 사용 |
| 4개 도메인 임베딩 마이그레이션 (수동 API) | ✅ 구현됨 | Reference/Submission/Reasoning/Feedback |
| MinsoHub process / trigger_embedding_migration | ✅ 구현됨 | policy→오케스트레이터, rule→서비스 |
| **자동 임베딩** (신규 데이터 시 자동 1건 or 배치) | ❌ 미구현 | 선택 |
| **도메인별 전용 오케스트레이터** | ❌ 미구현 | ReasoningHub 통합 상태, 선택 |
| **제출 → 추론 → 피드백 한 번에** | ❌ 미구현 | 완성 시 “제출만 하면 첨삭까지” |
| **ExaOne 분석 툴을 흐름에 연결** | ⚠️ 부분적 | 툴은 있음, 호출처는 도메인별로 확인·연결 |

---

## 4. 남은 작업 단계별 진행 순서

아래 순서대로 진행하면 의존성이 꼬이지 않고, “제출 → 첨삭”까지 한 번에 되는 흐름을 먼저 완성한 뒤 부가 기능을 붙이기 좋습니다.

---

### Phase 1: 제출 → 추론 → 피드백 한 번에 (필수, 최우선) ✅ 구현됨

**목표**: 답안 제출 한 번으로 추론까지 돌리고, 그 결과로 피드백까지 자동 생성.

**구현 내용**: `POST /api/v1/submission/answers/{answer_id}/analyze-and-feedback`
- 답안 조회 → 해당 문제의 모범답안 1개 사용 → 종합 추론(comprehensive_analysis) → 피드백 생성(generate) → `AnalyzeAndFeedbackResponse` 반환.
- 에러: 404(답안 없음), 400(모범답안 없음), 500(추론/피드백 실패).

| 단계 | 작업 | 상세 |
|------|------|------|
| 1-1 | **제출 API에서 “제출 후 자동 파이프라인” 트리거 설계** | 제출 성공 시 어떤 식으로 reasoning → feedback 을 부를지 정하기 (같은 요청 안에서 순차 호출 vs 별도 백그라운드 태스크). |
| 1-2 | **Reasoning 작업 생성·실행** | 제출된 `user_answer_id` + 해당 문제의 `reference_answer_id`, `problem_id`로 ReasoningTask 생성 후, `hub.process(domain="reasoning", action="comprehensive_analysis" 또는 해당 액션)` 호출. |
| 1-3 | **추론 결과로 Feedback 생성** | 1-2 결과를 받아 `hub.process(domain="feedback", action="generate", request=...)` 호출해 Feedback 엔티티 생성·저장. |
| 1-4 | **API 형태 결정 및 구현** | (A) 기존 `POST /submission/answers/text` 등 성공 시 내부에서 1-2 → 1-3 호출, 또는 (B) 새 엔드포인트 예: `POST /submission/answers/{id}/analyze-and-feedback` 로 “이 답안 기준 추론+피드백 생성” 호출. |
| 1-5 | **에러/롤백 처리** | 추론 또는 피드백 생성 실패 시 사용자에게 알리고, 필요하면 부분 저장(예: reasoning만 저장) 정책 정하기. |

**완료 기준**: 답안 한 건 제출한 뒤, 별도 수동 호출 없이 DB에 reasoning 결과 + feedback 이 쌓임.

---

### Phase 2: 자동 임베딩 (선택) ✅ 구현됨

**목표**: 새 데이터가 생길 때마다 해당 1건만 임베딩하거나, “아직 임베딩 안 된 행”을 주기적으로 채우기.

| 단계 | 작업 | 상세 |
|------|------|------|
| 2-1 | **트리거 방식 결정** | (A) 생성 API 성공 시마다 해당 1건만 `trigger_embedding_migration`과 유사한 “1건만 임베딩” 로직 호출, 또는 (B) 별도 배치/스케줄러에서 “embedding 없는 행” 조회 후 배치 임베딩. |
| 2-2 | **1건 임베딩 헬퍼 추가** | MinsoHub(또는 서비스)에 `embed_one_feedback(feedback_id)` 같은 메서드 추가: 1건 조회 → 텍스트 구성 → MCP `koelectra_embed_text` → 해당 `*_embeddings` 에 1행 insert. Reference/Submission/Reasoning 도메인도 동일 패턴. |
| 2-3 | **생성 API에 훅 연결** | Feedback 생성 완료 시(Phase 1 이후) `embed_one_feedback(...)` 호출. 필요하면 Reference/Submission/Reasoning 생성 시에도 동일하게 1건 임베딩 훅. |

**구현 내용**: MinsoHub.embed_one(domain, entity_id) 추가. Feedback·Reasoning은 analyze-and-feedback 파이프라인에서, Reference는 POST /reference/answers, Submission은 POST /submission/answers/text·image 생성 시 각각 1건 자동 임베딩. 실패해도 생성 API는 성공 유지.

**완료 기준**: 새 Feedback(또는 Reference 등) 생성 후, 별도로 `GET /embedding` 호출하지 않아도 해당 1건이 `*_embeddings` 에 들어감.

---

### Phase 3: 도메인별 오케스트레이터 분리 (선택) ✅ 구현됨

**목표**: feedback / reference 등 도메인별 전용 오케스트레이터를 두어 확장성과 책임 분리.

| 단계 | 작업 | 상세 |
|------|------|------|
| 3-1 | **FeedbackOrchestrator 도입** | `hub/orchestrators/feedback_orchestrator.py` 생성, `process(domain="feedback", action, request)` 처리 (generate, generate_report 등). 기존 ReasoningHub에서 feedback 관련 부분 이전. |
| 3-2 | **MinsoHub 매핑 변경** | `_get_orchestrator_map()` 에서 `"feedback"` → `FeedbackOrchestrator(session)` 사용하도록 수정. |
| 3-3 | **ReferenceOrchestrator 등 추가** | reference 전용 정책 처리 필요 시 `ReferenceOrchestrator` 추가 후 맵에 등록. reasoning 은 기존 ReasoningHub 유지. |

**구현 내용**: FeedbackOrchestrator 구현 및 MinsoHub에 `"feedback"` → FeedbackOrchestrator 매핑. ReasoningHub는 reasoning 전용으로만 동작하도록 feedback 분기 제거. ReferenceOrchestrator는 스텁으로 두고, reference는 현재 전부 규칙 기반이므로 맵에는 미등록.

**완료 기준**: 도메인별로 전용 오케스트레이터가 연결되고, MinsoHub는 도메인만 바꿔서 위임하는 형태.

---

### Phase 4: ExaOne 분석 툴 실제 연동 ✅ 구현됨

**설계 원칙 (역할 분리)**
- **KoELECTRA**: 오케스트레이션 용도 (정책/규칙 판단, 임베딩 등). 스타 토폴로지의 중심이 아님.
- **ExaOne**: **스타 토폴로지의 중심 Hub** — 추론/피드백의 핵심 판단·생성은 ExaOne이 담당하도록 함.

이 설계를 따르면 Phase 4는 **필수**이다. 현재는 추론/피드백이 KoELECTRA+규칙에 의존하므로, ExaOne을 실제 흐름에 넣어야 “ExaOne이 Hub”인 구조가 됨.

**목표**: MCP에 등록된 `exaone_analyze_*_data`(및 필요 시 생성 툴)를 추론/피드백 생성 로직에서 **실제로 호출하고 그 결과를 사용**하도록 연동.

| 단계 | 작업 | 상세 |
|------|------|------|
| 4-1 | **호출 지점 정하기** | ReasoningHub 또는 Feedback 생성 로직에서 “모범답안/제출답안/추론결과/피드백” 중 어떤 것을 ExaOne에 넘겨 분석할지 결정. |
| 4-2 | **MCP call_tool 로 분석 호출** | `mcp_server.call_tool("exaone_analyze_reference_data", reference_data=...)` 등으로 호출하고, 반환값을 추론/피드백 생성 입력으로 사용. |
| 4-3 | **에러·폴백 처리** | ExaOne 로드 실패 또는 타임아웃 시 기존 규칙 기반 로직으로 폴백할지 정한 뒤 구현. |

**완료 기준**: 추론 또는 피드백 생성 시 ExaOne 분석 결과가 실제로 사용됨.

**구현 내용 (C·c·가 적용)**
- **호출 지점 (C)**
  - **추론**: `ReasoningEngine.comprehensive_analysis`에서 모범답안·제출답안을 ExaOne에 넘김 (`exaone_analyze_reference_data`, `exaone_analyze_submission_data`). 결과는 `summary.exaone_analysis` 및 `ReasoningResult`(result_type=`exaone_analysis`)에 보조로 저장.
  - **피드백**: `FeedbackGenerator.generate_from_reasoning` 완료 후 추론(task+results)을 ExaOne에 넘김 (`exaone_analyze_reasoning_data`). 결과는 `Feedback.meta["exaone_analysis"]`에 보조로 저장.
- **활용 (c, 1단계 a)**: ExaOne 결과는 자유 문장으로 보조 필드만 채움. 점수/쟁점은 기존 KoELECTRA+규칙 유지. 이후 구조화(b) 확장 가능.
- **폴백 (가)**: ExaOne 호출 실패 시 로그 후 기존 파이프라인만 사용. 서비스 중단 없음.

---

#### Phase 4 상세 설명 (구현 필요 여부 판단용)

**1. 현재 ExaOne 분석 툴이 하는 일**

MCP에 등록된 `exaone_analyze_*_data` 툴들은 모두 **동일한 패턴**으로 동작합니다.

- **입력**: 해당 도메인 데이터 딕셔너리 (예: `reference_data`, `submission_data`, `reasoning_data`, `feedback_data`)
- **처리**: JSON을 문자열로 만든 뒤, ExaOne LLM에 "다음 OO 데이터를 분석하고 주요 특징을 요약해주세요" 형태의 프롬프트로 전달
- **출력**: `{ "success": True, "analysis": "<ExaOne가 생성한 요약 텍스트>", ... }`
  → 즉 **자유 형식 요약문**만 반환하며, 점수·쟁점·구조화된 JSON 등은 반환하지 않음.

**2. 현재 추론/피드백 파이프라인 (Phase 4 반영)**

- **추론(ReasoningEngine)**
  - **ExaOne**: `comprehensive_analysis` 시 모범답안·제출답안을 MCP `exaone_analyze_reference_data`/`exaone_analyze_submission_data`로 분석. 성공 시 `summary.exaone_analysis` 및 결과 행(exaone_analysis)에 보조 저장. 실패 시 기존만 사용.
  - 쟁점: KoELECTRA 파인튜닝 + 규칙. 논리/표현: 휴리스틱·규칙.
- **피드백(FeedbackGenerator)**
  - 피드백 생성 후 추론(task+results)을 MCP `exaone_analyze_reasoning_data`로 분석. 성공 시 `Feedback.meta["exaone_analysis"]`에 보조 저장. 실패 시 기존 응답만 반환.

**3. "실제 연동"이 의미하는 것**

| 연동 방식 | 설명 | 추가 작업 |
|-----------|------|------------|
| **A. ExaOne을 추론/피드백의 입력으로 쓰기** | 모범답안·제출답안·추론결과 중 하나를 ExaOne에 넘겨 `exaone_analyze_*_data`를 호출하고, 그 반환값(analysis 텍스트)을 추론 또는 피드백 생성 로직의 입력으로 사용. | 호출 시점 결정, 반환 텍스트를 기존 구조(점수/쟁점/항목)에 매핑하거나 파싱하는 로직 필요. 현재 툴은 "요약"만 하므로 **구조화 출력(JSON 스키마)** 또는 파싱 규칙을 정해야 함. |
| **B. ExaOne을 보조 정보로만 쓰기** | 추론/피드백은 그대로 두고, ExaOne 분석 결과를 "참고 요약"처럼 피드백 본문에 덧붙임 (예: "ExaOne 요약: …"). | 호출 지점 1곳 + 응답에 필드 하나 추가하면 됨. 다만 품질 개선 효과는 제한적. |
| **C. Reference 전용 (논점 추출 등)** | `reference.py`의 논점 추출 API처럼, 모범답안만 ExaOne에 넘겨 구조화된 결과(예: 쟁점 목록)를 기대. | 현재 툴은 요약만 하므로, **프롬프트/후처리로 구조화**하거나, 별도 툴/스키마를 설계해야 함. |

**4. 설계 원칙이 "ExaOne = 스타 Hub"일 때**

- **Phase 4는 선택이 아니라 필수**이다.
  - KoELECTRA는 오케스트레이션(라우팅·임베딩 등)에 두고,
  - **추론/피드백의 중심**은 ExaOne이 되도록 Phase 4에서 실제 호출·반영을 구현해야 함.
- 구현 시 정해야 할 것:
  - 위 연동 방식 A/B/C 중 어떤 식으로 ExaOne을 **핵심 경로**에 넣을지.
  - ExaOne 출력을 **구조화(JSON 등)** 할지, 자유 문장을 파싱할지.
  - ExaOne 실패 시 **폴백**(KoELECTRA+규칙 유지 여부).

**5. 정리**

- Phase 4는 **"ExaOne 툴을 호출하고 그 결과를 추론/피드백 흐름에 반영하는 것"**까지를 말함.
- **ExaOne을 스타 토폴로지의 중심 Hub로 둔다는 설계**라면 이 작업은 **진행이 필요**함.
- 현재 툴은 자유 형식 요약만 나오므로, Hub로서 제대로 쓰려면 **프롬프트·출력 형식(JSON 등)·에러/폴백** 설계가 추가로 필요함.

---

### 진행 순서 요약

```
Phase 1 (필수)  →  Phase 2 (선택)  →  Phase 3 (선택)  →  Phase 4 (필수*)
제출→추론→피드백     자동 임베딩        오케스트레이터 분리   ExaOne 툴 연동
한 번에 연결         1건/배치          Feedback/Reference    ExaOne = 스타 Hub
```

- **Phase 1**을 먼저 끝내면 “답안 넣으면 첨삭까지 자동”인 메인 시나리오가 완성됩니다.
- **Phase 2**는 Phase 1으로 Feedback이 자동 생성된 뒤, 그걸 자동으로 임베딩까지 넣고 싶을 때 진행하면 됩니다.
- **Phase 3**는 구조 정리·고도화용으로, 여유 있을 때 진행하면 됩니다.
- **Phase 4**는 설계상 ExaOne을 스타 토폴로지의 중심 Hub로 둘 때 **필수**입니다. KoELECTRA는 오케스트레이션용, ExaOne이 추론/피드백의 중심이 되도록 연동해야 합니다.

이 문서는 “데이터를 넣었다고 가정했을 때 지금 구조가 어디까지 구현됐는지”와 “MCP 자동화 완성을 위해 무엇을 더 해야 하는지”, 그리고 **진행 순서**를 한 번에 보기 위한 요약입니다.
