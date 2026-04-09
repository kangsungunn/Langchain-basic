# 테스트 체크리스트

## 📌 개요

**목적**: Star Topology Hybrid Architecture의 전체 워크플로우 검증
**주체**: 개발자/테스터
**역할**: 각 컴포넌트 및 통합 테스트 수행

---

## ✅ 완료된 테스트

### Phase 1-5: 단위 테스트

**주체**: `test_hybrid_gateway.py`, `test_hub_router.py`, `test_langgraph_workflow.py`
**역할**: 각 컴포넌트 단위 테스트

| 테스트 파일 | 주체 | 역할 | 상태 |
|------------|------|------|------|
| `test_hybrid_gateway.py` | Gateway 테스트 | 규칙 기반 + ML 보조 검증 | ✅ 통과 |
| `test_hub_router.py` | Hub Router 통합 테스트 | 브랜치 선택, 폴백 처리 검증 | ✅ 통과 |
| `test_langgraph_workflow.py` | LangGraph 워크플로우 테스트 | 전체 워크플로우 검증 (4개 테스트) | ✅ 통과 |

**테스트 결과**:
- ✅ `test_spam_detection()`: 스팸 이메일 감지
- ✅ `test_normal_email()`: 정상 이메일 처리
- ✅ `test_performance()`: 성능 측정 (<5초)
- ✅ `test_workflow_stats()`: Gateway, Hub Router, Branch 통계

---

## 🔄 추가 테스트 필요 항목

### 1. FastAPI 엔드포인트 테스트 (우선순위: 높음)

**주체**: 개발자/테스터
**역할**: 실제 HTTP API로 전체 워크플로우 테스트

**테스트 방법**:

#### 방법 A: Swagger UI (추천)

**주체**: 개발자/테스터
**역할**: 브라우저를 통한 API 테스트

1. **FastAPI 서버 실행**
   ```bash
   uvicorn app.main:app --reload
   ```
   **주체**: `app/main.py` (FastAPI Application)
   **역할**: HTTP 서버 시작

2. **브라우저에서 접속**
   - http://localhost:8000/docs

3. **`/api/mcp/workflow` 엔드포인트 선택**

4. **요청 본문 입력**
   ```json
   {
     "text": "긴급송금 필요! 계좌번호 알려주세요!",
     "user_id": "test_user",
     "save_to_db": false
   }
   ```

5. **Execute 클릭**

6. **응답 확인**
   ```json
   {
     "final_action": "quarantine",
     "policy_reason": "...",
     "gateway": {...},
     "hub_router": {...},
     "branch": {...},
     "db": null,
     "performance": {...}
   }
   ```

**주체별 검증**:
- ✅ `gateway`: Gateway (HybridGateway)가 정상 라우팅
- ✅ `hub_router`: Hub Router (Star)가 브랜치 선택
- ✅ `branch`: Branch (SpamAgent)가 분석 수행
- ✅ `final_action`: Star가 최종 액션 결정

**체크리스트**:
- [ ] 서버 정상 실행
- [ ] POST 요청 성공 (200 OK)
- [ ] 응답 형식 확인
- [ ] 각 단계별 결과 확인

---

#### 방법 B: PowerShell 스크립트

**주체**: `test_api.ps1` 또는 `test_api_simple.ps1`
**역할**: 자동화된 API 테스트

```powershell
# test_api.ps1 실행
.\test_api.ps1
```

---

### 2. DB 저장 테스트 (우선순위: 높음)

**주체**: 개발자/테스터
**역할**: Star가 DB에 전체 워크플로우 저장 확인

**전제 조건**:
- ⚠️ **DB 테이블 생성 필요!** (`strategy/40_DB_SETUP_AND_TESTING_GUIDE.md` 참고)

**테스트 방법**:

#### 방법 A: Swagger UI (추천)

**주체**: 개발자/테스터
**역할**: `save_to_db=true`로 요청

1. **요청 본문 입력**
   ```json
   {
     "text": "긴급송금 필요! 계좌번호 알려주세요!",
     "user_id": "test_user",
     "save_to_db": true
   }
   ```

2. **응답 확인**
   ```json
   {
     "db": {
       "saved": true,
       "input_text_id": 1,
       "routing_log_id": 1,
       "branch_result_id": 1,
       "policy_decision_id": 1
     }
   }
   ```

**주체**: `db_save_node` (Hub Router)
**역할**: 4개 테이블에 한 번에 저장

#### 방법 B: PowerShell 스크립트

**주체**: `test_api_with_db.ps1`
**역할**: 자동화된 DB 저장 테스트

```powershell
.\test_api_with_db.ps1
```

**체크리스트**:
- [ ] DB 테이블 생성 완료 (4개 테이블)
- [ ] `save_to_db=true` 요청 성공
- [ ] `db.saved: true` 응답 확인
- [ ] DB에 실제 데이터 저장 확인:
  - [ ] `input_texts` 테이블
  - [ ] `routing_logs` 테이블
  - [ ] `branch_results` 테이블
  - [ ] `policy_decisions` 테이블

**DB 확인 쿼리** (Neon DB 콘솔):
```sql
-- Neon DB 콘솔에서 실행
SELECT * FROM input_texts ORDER BY created_at DESC LIMIT 5;
SELECT * FROM routing_logs ORDER BY created_at DESC LIMIT 5;
SELECT * FROM branch_results ORDER BY created_at DESC LIMIT 5;
SELECT * FROM policy_decisions ORDER BY created_at DESC LIMIT 5;
```

**주체**: 개발자/운영자
**역할**: DB 데이터 확인

---

### 3. 통합 시나리오 테스트 (우선순위: 중간)

**주체**: 개발자/테스터
**역할**: 실제 사용 시나리오 시뮬레이션

#### 시나리오 1: 스팸 이메일 차단

**주체**: 사용자 → Gateway → Hub Router → Branch → Star
**역할**: 스팸 이메일 감지 및 차단

**요청**:
```bash
curl -X POST "http://localhost:8000/api/mcp/workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "긴급송금 필요! 계좌번호 알려주세요! 당첨되셨습니다!",
    "user_id": "user_001",
    "save_to_db": true
  }'
```

**예상 결과**:
- `gateway.route`: "spam_agent" (규칙 기반)
- `branch.label`: "spam"
- `branch.evidence`: 3개 이상
- `final_action`: "block" 또는 "quarantine"

**주체별 검증**:
- ✅ Gateway: 규칙 기반 라우팅
- ✅ Hub Router: spam_agent 선택
- ✅ Branch: 스팸 판정 (evidence 3개 이상)
- ✅ Star: block/quarantine 결정

---

#### 시나리오 2: 정상 이메일 전달

**주체**: 사용자 → Gateway → Hub Router → Branch → Star
**역할**: 정상 이메일 허용

**요청**:
```bash
curl -X POST "http://localhost:8000/api/mcp/workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "회의 일정을 조율하고 싶습니다. 다음 주 화요일 오후 2시는 어떠신가요?",
    "user_id": "user_002",
    "save_to_db": true
  }'
```

**예상 결과**:
- `gateway.route`: "default_agent" 또는 "spam_agent" (ML 보조)
- `branch.label`: "ham"
- `final_action`: "deliver"

**주체별 검증**:
- ✅ Gateway: ML 보조 라우팅 (모호한 경우)
- ✅ Hub Router: 브랜치 선택
- ✅ Branch: 정상 판정
- ✅ Star: deliver 결정

---

#### 시나리오 3: Gateway 거부 (인젝션 패턴)

**주체**: 사용자 → Gateway
**역할**: 보안 위협 차단 (Hub Router 도달 전)

**요청**:
```bash
curl -X POST "http://localhost:8000/api/mcp/workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "SELECT * FROM users; --",
    "user_id": "user_003",
    "save_to_db": false
  }'
```

**예상 결과**:
- `gateway.route`: "reject"
- `final_action`: "reject"
- `policy_reason`: "인젝션 패턴 감지"

**주체별 검증**:
- ✅ Gateway: SecurityRules가 인젝션 감지
- ⏸️ Hub Router: 도달 안함 (Gateway에서 차단)
- ⏸️ Branch: 실행 안함

---

#### 시나리오 4: 폴백 처리 (비활성 브랜치)

**주체**: 사용자 → Gateway → Hub Router → default_agent
**역할**: 비활성 브랜치 요청 시 폴백 처리

**요청**:
```bash
curl -X POST "http://localhost:8000/api/mcp/workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "환불 요청합니다. 제품이 불량입니다.",
    "user_id": "user_004",
    "save_to_db": false
  }'
```

**예상 결과**:
- `gateway.route`: "refund_agent"
- `hub_router.selected_branch`: "default_agent" (폴백)
- `hub_router.fallback_used`: true

**주체별 검증**:
- ✅ Gateway: refund_agent 라우팅
- ✅ Hub Router: refund_agent 비활성 → default_agent 폴백
- ✅ Branch: default_agent 실행

---

### 4. 에러 핸들링 테스트 (우선순위: 중간)

**주체**: 개발자/테스터
**역할**: 예외 상황 처리 확인

**테스트 케이스**:
- [ ] 빈 텍스트 입력
- [ ] 매우 긴 텍스트 (10,000자 초과)
- [ ] 잘못된 JSON 요청
- [ ] DB 연결 실패 시나리오
- [ ] 모델 로드 실패 시나리오

**주체별 검증**:
- ✅ Gateway: 입력 검증 실패 처리
- ✅ Hub Router: 브랜치 로드 실패 시 폴백
- ✅ Branch: 모델 추론 실패 시 에러 반환
- ✅ Star: 에러 상황에서 안전한 응답 반환

---

### 5. 성능 테스트 (우선순위: 낮음)

**주체**: 개발자/테스터
**역할**: 실제 부하 테스트

**테스트 방법**:
```bash
# 여러 요청 동시 실행
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/mcp/workflow" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"테스트 메시지 $i\", \"save_to_db\": false}" &
done
wait
```

**체크리스트**:
- [ ] 동시 요청 처리 확인
- [ ] 평균 응답 시간 측정
- [ ] 메모리 사용량 확인
- [ ] GPU 메모리 사용량 확인

**주체별 성능 목표**:
- Gateway (규칙): 1-5ms
- Gateway (ML): 50-100ms
- Hub Router: 1-3ms
- Branch (EXAONE): 100-200ms
- DB 저장: 10-20ms
- **전체 (평균)**: 20-300ms

---

## 📊 현재 완료도

| 항목 | 상태 | 비고 |
|------|------|------|
| **Phase 1-5 구현** | ✅ 100% | 모든 컴포넌트 구현 완료 |
| **단위 테스트** | ✅ 100% | test_langgraph_workflow.py 통과 |
| **FastAPI 통합** | ✅ 100% | 서버 실행 및 API 테스트 성공 |
| **DB 저장** | ⏳ 0% | 테이블 생성 후 테스트 필요 |
| **통합 시나리오** | ⏳ 0% | 실제 사용 케이스 테스트 필요 |
| **에러 핸들링** | ⏳ 0% | 예외 상황 테스트 필요 |

**전체 완료도**: **약 70%** (구현 100%, 테스트 40%)

---

## 🎯 다음 단계 추천 순서

### 필수 (약 15분)
1. **DB 테이블 생성** (필수)
   - `strategy/40_DB_SETUP_AND_TESTING_GUIDE.md` 참고
   - 약 5분 소요
   - **주체**: 개발자/운영자
   - **역할**: PostgreSQL 테이블 초기화

2. **FastAPI 서버 실행 및 기본 테스트** (필수)
   - 서버 실행
   - 기본 API 호출 테스트
   - 약 10분 소요
   - **주체**: 개발자/테스터
   - **역할**: HTTP API 검증

3. **DB 저장 테스트** (필수)
   - `save_to_db=true` 요청
   - DB 데이터 확인
   - 약 10분 소요
   - **주체**: 개발자/테스터
   - **역할**: DB 저장 기능 검증

### 권장 (약 15분)
4. **통합 시나리오 테스트** (권장)
   - 4개 시나리오 실행
   - 약 15분 소요
   - **주체**: 개발자/테스터
   - **역할**: 실제 사용 케이스 검증

### 선택 (약 10분)
5. **에러 핸들링 테스트** (선택)
   - 예외 상황 확인
   - 약 10분 소요
   - **주체**: 개발자/테스터
   - **역할**: 예외 처리 검증

---

## 📝 테스트 스크립트 (자동화)

**향후 자동화 테스트 스크립트 작성 가능**:
- `test_api_endpoints.py` - FastAPI 엔드포인트 테스트
- `test_db_integration.py` - DB 저장 통합 테스트
- `test_error_handling.py` - 에러 핸들링 테스트

**주체**: 개발자
**역할**: 자동화 테스트 스크립트 작성

---

## 📚 참고 문서

- `strategy/40_DB_SETUP_AND_TESTING_GUIDE.md`: DB 설정 및 테스트 가이드
- `strategy/PHASE5_COMPLETE_SUMMARY.md`: Phase 5 완료 요약
- `strategy/36_STAR_TOPOLOGY_HYBRID_ARCHITECTURE.md`: 전체 아키텍처

---

**마지막 업데이트**: Phase 5 완료 시점
