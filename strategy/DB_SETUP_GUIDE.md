# DB Layer 설정 가이드

## 📁 주체별 파일 역할

### 🗄️ **Database Layer** - Hub Router (Star)만 접근 가능

```
app/database/
├── __init__.py              # 📦 Database 패키지 초기화
│   주체: Hub Router (Star)
│   역할: DB 관련 모든 모듈 export
│
├── connection.py            # 🔌 DB 연결 관리
│   주체: Hub Router (Star)
│   역할: PostgreSQL 연결, 세션 제공, DB 초기화
│   메서드:
│     - get_db(): DB 세션 제공 (FastAPI Dependency)
│     - init_db(): 테이블 생성
│     - check_db_connection(): 연결 상태 체크
│
├── models.py                # 📋 DB 테이블 스키마 (SQLAlchemy ORM)
│   주체: Hub Router (Star)
│   역할: 4개 테이블 정의
│   테이블:
│     - InputText: 입력 텍스트 저장
│     - RoutingLog: Gateway → Hub Router → Branch 라우팅 기록
│     - BranchResultRecord: Branch 실행 결과 저장
│     - PolicyDecision: Star의 최종 액션 결정 저장
│
└── repositories.py          # 🔧 DB CRUD 작업
    주체: Hub Router (Star)
    역할: 각 테이블에 대한 CRUD 리포지토리 제공
    리포지토리:
      - InputTextRepository: 입력 텍스트 CRUD
      - RoutingLogRepository: 라우팅 로그 CRUD
      - BranchResultRepository: 브랜치 결과 CRUD
      - PolicyDecisionRepository: 정책 결정 CRUD
      - StarRepository: 전체 워크플로우 통합 저장 (⭐ 핵심!)
```

---

## 🚀 설치 및 초기화

### 1단계: PostgreSQL 설치

**Windows**:
```bash
# PostgreSQL 다운로드 및 설치
https://www.postgresql.org/download/windows/
```

**MacOS**:
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux**:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

---

### 2단계: 데이터베이스 생성

```bash
# PostgreSQL에 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE spam_filter_db;

# 종료
\q
```

---

### 3단계: DB 의존성 설치

```bash
# DB Layer 의존성 설치
pip install -r requirements-db.txt
```

**설치 내용**:
- `psycopg2-binary`: PostgreSQL 드라이버
- `sqlalchemy`: ORM
- `alembic`: DB 마이그레이션 (선택사항)

---

### 4단계: 환경 변수 설정

`.env` 파일 생성 (`.env.example` 참고):

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/spam_filter_db
```

---

### 5단계: DB 초기화 (테이블 생성)

```bash
# DB 초기화 스크립트 실행
python scripts/init_db.py
```

**출력 예시**:
```
======================================================================
PostgreSQL 데이터베이스 초기화
======================================================================

[1/2] DB 연결 확인 중...
✅ DB 연결 성공!

[2/2] 테이블 생성 중...
[DB] 데이터베이스 테이블 생성 중...
[DB] 데이터베이스 초기화 완료!

✅ 데이터베이스 초기화 완료!

생성된 테이블:
  1. input_texts         - 입력 텍스트
  2. routing_logs        - 라우팅 로그
  3. branch_results      - 브랜치 실행 결과
  4. policy_decisions    - 정책 결정 기록

======================================================================
```

---

### 6단계: DB 테스트

```bash
# DB CRUD 테스트
python scripts/test_db.py
```

---

## 📊 테이블 구조

### 1. **input_texts** (입력 텍스트)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer (PK) | 고유 ID |
| `text` | Text | 원본 텍스트 |
| `text_hash` | String(64) | SHA-256 해시 (중복 체크용) |
| `user_id` | String(100) | 사용자 ID |
| `source` | String(50) | 입력 소스 (web, api, email, ...) |
| `created_at` | DateTime | 생성 시간 |

**주체**: Hub Router (Star)
**역할**: 사용자가 입력한 원본 텍스트 저장

---

### 2. **routing_logs** (라우팅 로그)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer (PK) | 고유 ID |
| `input_text_id` | Integer (FK) | 입력 텍스트 ID |
| `gateway_route` | String(50) | Gateway 라우팅 결정 |
| `gateway_confidence` | Float | Gateway 신뢰도 |
| `gateway_method` | String(20) | Gateway 방법 (rule_based, ml_assisted) |
| `gateway_matched_rules` | Array | Gateway 매칭된 규칙들 |
| `gateway_reason` | Text | Gateway 근거 |
| `gateway_latency_ms` | Float | Gateway 지연 시간 |
| `selected_branch` | String(50) | Hub Router가 선택한 브랜치 |
| `fallback_used` | Integer | 폴백 사용 여부 (0: False, 1: True) |
| `ontology_version` | String(20) | 온톨로지 버전 |
| `created_at` | DateTime | 생성 시간 |

**주체**: Hub Router (Star)
**역할**: Gateway → Hub Router → Branch 라우팅 과정 기록

---

### 3. **branch_results** (브랜치 실행 결과)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer (PK) | 고유 ID |
| `input_text_id` | Integer (FK) | 입력 텍스트 ID |
| `branch_name` | String(50) | 브랜치 이름 |
| `task_type` | String(50) | 태스크 타입 (spam, refund, ...) |
| `label` | String(50) | 라벨 (spam, ham, ...) |
| `confidence` | Float | 신뢰도 |
| `recommended_action` | String(50) | 브랜치 권장 액션 |
| `reasoning` | Text | 분석 근거 |
| `evidence` | Array | 증거 리스트 |
| `latency_ms` | Float | 브랜치 실행 시간 |
| `metadata` | JSON | 추가 메타데이터 |
| `created_at` | DateTime | 생성 시간 |

**주체**: Hub Router (Star)
**역할**: Branch가 반환한 BranchResult 저장
⚠️ **주의**: Branch는 직접 저장하지 않음! Hub Router만 저장

---

### 4. **policy_decisions** (정책 결정 기록)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer (PK) | 고유 ID |
| `input_text_id` | Integer (FK) | 입력 텍스트 ID |
| `branch_name` | String(50) | 브랜치 이름 |
| `branch_recommended_action` | String(50) | 브랜치 권장 액션 |
| `branch_confidence` | Float | 브랜치 신뢰도 |
| `branch_evidence_count` | Integer | 증거 개수 |
| `final_action` | String(50) | **Star의 최종 액션** ⭐ |
| `policy_reason` | Text | 결정 근거 |
| `task_type` | String(50) | 태스크 타입 |
| `ontology_version` | String(20) | 온톨로지 버전 |
| `applied_policy` | JSON | 적용된 정책 상세 |
| `created_at` | DateTime | 생성 시간 |

**주체**: Hub Router (Star)
**역할**: Star가 내린 최종 액션 결정 저장
⚠️ **중요**: 브랜치는 권장만, Star가 최종 결정!

---

## 🔄 DB 저장 흐름 (Hub Router가 관리)

```
1. 사용자 입력
   ↓
2. Gateway 처리
   ↓
3. Hub Router 라우팅 결정
   ↓
4. Branch 실행
   ↓
5. Hub Router 최종 액션 결정
   ↓
6. ⭐ Hub Router가 DB에 모두 저장 (한 번에!)
   ├─> InputText (입력 텍스트)
   ├─> RoutingLog (라우팅 과정)
   ├─> BranchResultRecord (브랜치 결과)
   └─> PolicyDecision (Star의 최종 결정)
```

---

## 💻 사용 예시

### Hub Router에서 DB 저장

```python
from app.database.connection import SessionLocal
from app.services.hub.hub_router import HubRouter
from app.services.gateway.hybrid_gateway import HybridGateway
from app.services.branches.spam_agent import SpamAgent

# 1. DB 세션 생성
db = SessionLocal()

# 2. 컴포넌트 초기화
gateway = HybridGateway()
hub = HubRouter()
spam_agent = SpamAgent()

# 스팸 에이전트 모델 로드
spam_agent.load_model(
    base_model_path="app/models/original/exaone-2.4b",
    adapter_path="./checkpoints/exaone-spam-filter-v2/checkpoint-3000"
)

try:
    # 3. 입력 텍스트
    text = "긴급송금 필요! 계좌번호 알려주세요!"

    # 4. Gateway 처리
    gateway_result = gateway.route(text)

    # 5. Hub Router 라우팅
    routing_decision = hub.route(gateway_result, text)

    # 6. Branch 실행
    branch_result = spam_agent.process(text)

    # 7. Star 최종 액션 결정
    final_action, policy_reason = hub.decide_final_action(
        branch_recommendation=branch_result.recommended_action,
        branch_confidence=branch_result.confidence,
        branch_evidence=branch_result.evidence,
        gateway_result=gateway_result,
        task_name="spam"
    )

    # 8. ⭐ Hub Router가 DB에 모두 저장
    saved = hub.save_to_db(
        db=db,
        text=text,
        gateway_result=gateway_result,
        routing_decision=routing_decision,
        branch_result=branch_result,
        final_action=final_action,
        policy_reason=policy_reason,
        user_id="user_123",
        source="api"
    )

    print(f"✅ DB 저장 완료: {saved}")

finally:
    db.close()
    hub.shutdown()
```

---

## 📚 주요 메서드

### `HubRouter.save_to_db()`

**주체**: Hub Router (Star)
**역할**: 전체 워크플로우를 DB에 한 번에 저장

```python
hub.save_to_db(
    db=db,                          # DB 세션
    text=text,                      # 원본 텍스트
    gateway_result=gateway_result,  # Gateway 결과
    routing_decision=routing_decision,  # Hub Router 라우팅 결정
    branch_result=branch_result,    # Branch 결과
    final_action=final_action,      # Star의 최종 액션
    policy_reason=policy_reason,    # 결정 근거
    user_id="user_123",             # 사용자 ID (Optional)
    source="api"                    # 입력 소스 (Optional)
)
```

---

## ⚠️ 중요 원칙

1. **Hub Router (Star)만 DB 접근 가능!**
   - Branch는 DB 접근 금지
   - Gateway는 DB 접근 금지

2. **Branch는 결과만 반환**
   - `BranchResult` 객체로 반환
   - Hub Router가 DB에 저장

3. **Star가 최종 결정**
   - Branch는 `recommended_action`만 제안
   - Star가 정책 적용하여 `final_action` 결정

---

## 🔗 다음 단계

- [ ] **Phase 5: LangGraph 통합** (워크플로우 자동화)
- [ ] **PGVector 확장** (벡터 임베딩, 유사도 검색)
- [ ] **Alembic 마이그레이션** (스키마 버전 관리)
