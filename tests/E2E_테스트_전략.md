# 1번: E2E/통합 테스트 — 전략 및 역할 분리

## 이 테스트가 검증하는 것 (목표·전체 구성에서의 위치)

### 시스템 전체 목표

**민사소송법 서술형 답안 첨삭**: 사용자가 제출한 답안을 모범답안·문제와 비교해 **추론(쟁점/논리/표현 분석)**을 하고, 그 결과를 바탕으로 **피드백(첨삭)**을 만들어 주는 흐름.

### 전체 구성에서 이 테스트의 의미

| 구분 | 설명 |
|------|------|
| **검증 대상** | **“제출 → 추론 → 피드백 한 번에”** API 한 번 호출로 끝까지 도는지 |
| **대상 API** | `POST /api/v1/submission/answers/{answer_id}/analyze-and-feedback` |
| **테스트 성공 시 의미** | ① 사용자 답안 1개만 있으면, ② 해당 문제의 모범답안을 자동으로 찾아서 ③ 추론(종합 분석)을 실행하고 ④ 그 결과로 피드백을 생성해 ⑤ 한 번에 응답으로 돌려주는 **전체 파이프라인**이 정상 동작한다는 뜻입니다. |
| **검증하지 않는 것** | 추론/피드백의 **품질**(채점 정확도, 문장 품질 등). “끊기지 않고 결과가 나온다”까지만 봅니다. |

즉, **“답안 하나 넣으면 첨삭까지 한 번에 받을 수 있는지”**를 자동으로 확인하는 테스트입니다.

---

## ExaOne·데이터 형식에 대한 정리

### ExaOne이 완전 base 모델(학습 없음)인 경우

- **이 테스트는 ExaOne 학습 여부와 무관하게 설계되어 있습니다.**
- Phase 4에서 ExaOne을 쓰는 구간이 **실패하거나 모델이 없으면** → 기존 **KoELECTRA + 규칙 기반**만으로 추론·피드백을 만들고 200을 반환합니다(폴백).
- 따라서 **ExaOne이 base 모델이어도 테스트는 통과할 수 있습니다.**
  (ExaOne 호출이 성공하면 `exaone_analysis` 필드가 붙고, 실패하면 그 필드만 없을 뿐입니다.)
- 나중에 ExaOne을 학습시키면, 같은 API·같은 테스트로 “ExaOne이 붙었을 때도 흐름이 유지되는지”를 추가로 확인하면 됩니다.

### JSONL 데이터 형식

- **우리가 “이 형식이어야 한다”고 요구한 것이 아닙니다.**
  말씀해 주신 경로의 파일(`gy_saeryejip_all.jsonl` 등) **실제 구조**를 보고,
  그걸 DB의 `problems` / `reference_answers`에 넣기 위해 **시딩 스크립트에서 매핑**한 것입니다.
- **현재 시딩이 가정한 형식**
  - **문제**: 한 줄당 `{"id", "title", "content", "questions"}` (id로 문제 식별)
  - **모범답안**: 한 줄당 `{"id", "answers": [{"question_number", "points", "answer"}]}` (id는 문제 id와 1:1, 첫 번째 `answer` 문자열을 모범답안 본문으로 사용)
- **당신 쪽 JSONL이 이와 다르면** (필드 이름·중첩 구조가 다르면) 알려주시면, **그 형식에 맞게 시딩 매핑을 수정**하면 됩니다. “표준 형식”을 강제하는 것이 아니라, **지금 쓰는 데이터에 맞추는 것**이 목적입니다.

---

## 테스트 목표 (기술적)

- `POST .../analyze-and-feedback` 한 번 호출로:
  - **응답**: 200, `user_answer_id`, `reasoning_task_id`, `analysis_summary`, `feedback` 존재
  - **동작**: ExaOne 없어도 기존 KoELECTRA+규칙으로 분석·피드백 생성되어 200 반환
- (선택) DB에 reasoning_task, reasoning_results, feedback, 임베딩 행 생성 여부 검증

---

## 역할 분리

### 내가 할 일 (AI)

- [x] `tests/integration/test_analyze_and_feedback_e2e.py` 작성
  - 서버 기동 가정, httpx로 API 호출
  - 전제: 문제 1개 + 모범답안 1개 존재 (또는 테스트에서 안내 메시지)
  - 제출답안 생성 → `analyze-and-feedback` 호출 → 응답 구조·필드 검증
- [ ] 테스트 실행 방법을 이 문서와 스크립트 docstring에 명시

### 당신이 할 일 (직접)

1. **백엔드 서버 기동**
   - 터미널에서 `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` 또는 `run_backend.bat` 등으로 서버 실행
   - `DATABASE_URL` 등 `.env` 설정 확인

2. **테스트 데이터 준비**
   - **옵션 A**: 이미 문제·모범답안이 DB에 있음 → 그대로 사용
   - **옵션 B**: 하드코딩 1건 시딩 → `python database/seed_data.py`
   - **옵션 C**: 민사소송법 JSONL 시딩 → `python database/seed_data.py --from-jsonl`
     (데이터: `data/raw/civil_procedure/problems/gy_saeryejip_all.jsonl`, `model_answers/gy_saeryejip_all.jsonl`. 자세한 경로는 `data/DATA_AND_MODELS.md` 참고)

3. **테스트 실행**
   - `python -m pytest tests/integration/test_analyze_and_feedback_e2e.py -v`
   - 또는 `python tests/integration/test_analyze_and_feedback_e2e.py` (스크립트로 실행 가능하게 작성 시)

4. **결과 확인**
   - 통과/실패 로그 확인, 실패 시 응답 메시지로 원인 파악

---

## 확인이 필요한 사항 (애매한 부분)

1. **테스트 DB**
   - **현재**: 테스트가 **실행 중인 서버(localhost:8000) + 그 서버가 쓰는 DB**를 그대로 사용합니다. 별도 테스트 전용 DB를 쓰지 않습니다.
   - **질문**: 지금처럼 “실서비스와 같은 DB”로 E2E만 검증해도 될까요? (테스트 전용 DB를 쓰려면 설정·마이그레이션 분리 등이 필요합니다.)

2. **테스트 데이터**
   - **현재**: “문제 목록 조회 → 첫 문제 + 해당 모범답안 사용 → 없으면 스킵 또는 실패 메시지” 방식입니다. 테스트 안에서 문제/모범답안을 직접 생성하지 않습니다.
   - **질문**: 문제·모범답안은 **항상 시딩/수동으로 미리 넣어 둔다**고 가정해도 될까요? 아니면 테스트에서 **문제·모범답안까지 API로 생성**하는 방식을 원하시나요?

3. **ExaOne 유무**
   - **현재**: ExaOne이 없어도 200 + 기존 분석·피드백만 나오면 성공으로 보는 테스트로 작성합니다. ExaOne이 있으면 `analysis_summary.exaone_analysis`, `feedback.meta.exaone_analysis` 존재 여부는 **선택 검증**으로 넣을 수 있습니다.
   - **질문**: ExaOne 있을 때/없을 때 **둘 다** 검증하는 옵션을 테스트에 넣어둘까요, 아니면 “ExaOne 없이 200만 나오면 통과”만 해도 될까요?

위 세 가지에 대한 선호만 알려주시면, 그에 맞춰 테스트 코드와 실행 방법을 최종 정리하겠습니다.

**기본 동작**: 답변 없이도 현재 테스트는 **실 DB + 문제/모범답안 시딩 가정 + ExaOne 없어도 200·필드 검증**으로 동작합니다. 선호가 있으면 알려주시면 그에 맞춰 수정합니다.
