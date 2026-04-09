# DB Layer 설정 및 테스트 가이드

## 📌 개요

**주체**: Hub Router (Star)
**역할**: PostgreSQL 데이터베이스 설정, 테이블 생성, DB 저장 테스트
**접근 권한**: Hub Router (Star)만 DB 접근 가능 (중앙 집권화 원칙)

---

## 🗂️ DB Layer 파일 구조 (주체별)

### 📁 `app/database/` - Hub Router (Star) 전용

```
app/database/
├── __init__.py              # 📦 Database 패키지 초기화
│   주체: Hub Router (Star)
│   역할: DB 관련 모든 모듈 export
│
├── connection.py            # 🔌 DB 연결 관리
│   주체: Hub Router (Star)
│   역할: PostgreSQL 연결, 세션 제공, DB 초기화
│   주요 함수:
│     - get_db(): DB 세션 제공 (FastAPI Dependency)
│     - init_db(): 테이블 생성 (Hub Router만 호출 가능)
│     - check_db_connection(): 연결 상태 체크
│
├── models.py                # 📋 DB 테이블 스키마 (SQLAlchemy ORM)
│   주체: Hub Router (Star)
│   역할: 4개 테이블 정의
│   테이블:
│     - InputText: 입력 텍스트 저장
│       주체: Hub Router (Star)
│       역할: 사용자 입력 원본 저장
│     - RoutingLog: Gateway → Hub Router → Branch 라우팅 기록
│       주체: Hub Router (Star)
│       역할: 전체 라우팅 과정 추적
│     - BranchResultRecord: Branch 실행 결과 저장
│       주체: Hub Router (Star)
│       역할: Branch가 반환한 결과 저장 (Branch는 직접 저장 안함!)
│     - PolicyDecision: Star의 최종 액션 결정 저장
│       주체: Hub Router (Star)
│       역할: Star의 최종 결정 기록
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
        주체: Hub Router (Star)
        역할: 4개 테이블에 한 번에 저장 (원자성 보장)
```

### 📁 `scripts/` - DB 초기화 및 테스트 스크립트

```
scripts/
├── init_db.py               # 🗄️ DB 테이블 생성
│   주체: 개발자/운영자
│   역할: PostgreSQL 테이블 초기화
│   실행: python scripts/init_db.py
│
├── fix_db_tables.py         # 🔧 DB 테이블 문제 해결
│   주체: 개발자/운영자
│   역할: 충돌하는 인덱스/테이블 삭제 후 재생성
│   실행: python scripts/fix_db_tables.py
│
└── test_db.py               # 🧪 DB CRUD 테스트
    주체: 개발자/운영자
    역할: DB 저장/조회 기능 검증
    실행: python scripts/test_db.py
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

**Neon DB (클라우드, 추천)**:
- https://console.neon.tech/ 접속
- 프로젝트 생성
- Connection String 복사 → `.env` 파일에 `DATABASE_URL`로 저장

---

### 2단계: DB 의존성 설치

```bash
# DB Layer 의존성 설치
pip install -r requirements-db.txt
```

**설치 내용**:
- `psycopg2-binary`: PostgreSQL 드라이버
- `sqlalchemy`: ORM
- `python-dotenv`: 환경 변수 로드

---

### 3단계: 환경 변수 설정

`.env` 파일 생성 (프로젝트 루트):

```env
# PostgreSQL 연결 정보
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require

# 예시 (Neon DB):
# DATABASE_URL=postgresql://neondb_owner:npg_xxx@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

**주체**: 개발자/운영자
**역할**: DB 연결 정보 설정

---

### 4단계: DB 테이블 생성

#### 방법 A: 자동 스크립트 (추천)

```bash
# 충돌하는 인덱스/테이블 삭제 후 재생성
python scripts/fix_db_tables.py
```

**주체**: `fix_db_tables.py` 스크립트
**역할**:
1. 충돌하는 인덱스 삭제 (`ix_branch_results_*`)
2. 충돌하는 테이블 삭제 (`branch_results`, `input_texts`, `routing_logs`, `policy_decisions`)
3. 테이블 재생성 (`init_db()` 호출)
4. 생성 확인

#### 방법 B: 수동 (Neon DB 콘솔)

1. **Neon DB 콘솔 접속**
   - https://console.neon.tech/
   - 프로젝트 선택 → SQL Editor

2. **충돌하는 인덱스/테이블 삭제**
   ```sql
   -- 충돌하는 인덱스 삭제
   DROP INDEX IF EXISTS ix_branch_results_branch_name CASCADE;
   DROP INDEX IF EXISTS ix_branch_results_task_type CASCADE;
   DROP INDEX IF EXISTS ix_branch_results_label CASCADE;
   DROP INDEX IF EXISTS ix_branch_results_created_at CASCADE;

   -- 충돌하는 테이블 삭제 (데이터 손실 주의!)
   DROP TABLE IF EXISTS branch_results CASCADE;
   DROP TABLE IF EXISTS input_texts CASCADE;
   DROP TABLE IF EXISTS routing_logs CASCADE;
   DROP TABLE IF EXISTS policy_decisions CASCADE;
   ```

3. **테이블 재생성**
   ```bash
   python scripts/init_db.py
   ```

**예상 출력**:
```
[1/3] DB 연결 확인 중...
✅ DB 연결 성공!

[2/3] 기존 테이블 확인 중...
✅ 기존 테이블 발견: 1개
   테이블: login_logs

[3/3] 테이블 생성 중...
✅ 데이터베이스 초기화 완료!

현재 테이블: 5개
  1. branch_results      ← 새로 생성됨!
  2. input_texts         ← 새로 생성됨!
  3. login_logs          (기존)
  4. policy_decisions    ← 새로 생성됨!
  5. routing_logs        ← 새로 생성됨!
```

---

## 🧪 DB 저장 테스트

### 전제 조건
- ✅ DB 테이블 생성 완료 (4개 테이블)
- ✅ FastAPI 서버 실행 중

### 테스트 방법

#### 방법 A: Swagger UI (추천)

**주체**: 개발자/테스터
**역할**: HTTP API를 통한 DB 저장 테스트

1. **브라우저에서 접속**
   - http://localhost:8000/docs

2. **`/api/mcp/workflow` 엔드포인트 선택**

3. **요청 본문 입력**
   ```json
   {
     "text": "긴급송금 필요! 계좌번호 알려주세요!",
     "user_id": "test_user_001",
     "save_to_db": true
   }
   ```

4. **Execute 클릭**

5. **응답 확인**
   ```json
   {
     "final_action": "quarantine",
     "policy_reason": "브랜치 신뢰도 낮음 (0.67 < 0.7)",
     "gateway": {...},
     "hub_router": {...},
     "branch": {...},
     "db": {
       "saved": true,
       "input_text_id": 1,
       "routing_log_id": 1,
       "branch_result_id": 1,
       "policy_decision_id": 1
     },
     "performance": {...}
   }
   ```

**주체**: `db_save_node` (Hub Router)
**역할**: 4개 테이블에 한 번에 저장

#### 방법 B: PowerShell 스크립트

```powershell
# test_api_with_db.ps1 실행
.\test_api_with_db.ps1
```

**주체**: `test_api_with_db.ps1` 스크립트
**역할**: 자동화된 DB 저장 테스트

#### 방법 C: curl (PowerShell)

```powershell
$json = @{
    text = "긴급송금 필요! 계좌번호 알려주세요!"
    user_id = "test_user_001"
    save_to_db = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/mcp/workflow" `
    -Method Post `
    -ContentType "application/json" `
    -Body $json | ConvertTo-Json -Depth 5
```

---

### DB 데이터 확인

**주체**: 개발자/운영자
**역할**: Neon DB 콘솔에서 데이터 확인

**Neon DB 콘솔에서 실행**:

```sql
-- 1. 입력 텍스트 확인
SELECT * FROM input_texts ORDER BY created_at DESC LIMIT 5;

-- 2. 라우팅 로그 확인
SELECT * FROM routing_logs ORDER BY created_at DESC LIMIT 5;

-- 3. 브랜치 결과 확인
SELECT branch_name, label, confidence, recommended_action, evidence
FROM branch_results
ORDER BY created_at DESC LIMIT 5;

-- 4. 정책 결정 확인
SELECT branch_name, branch_recommended_action, final_action, policy_reason
FROM policy_decisions
ORDER BY created_at DESC LIMIT 5;

-- 5. 통계 확인
SELECT
    (SELECT COUNT(*) FROM input_texts) as total_inputs,
    (SELECT COUNT(*) FROM routing_logs) as total_routings,
    (SELECT COUNT(*) FROM branch_results) as total_branch_results,
    (SELECT COUNT(*) FROM policy_decisions) as total_decisions;
```

---

## 🔄 DB 저장 흐름 (주체별)

```
사용자 요청 (FastAPI)
   ↓
POST /api/mcp/workflow (save_to_db=true)
   ↓
┌─────────────────────────────────────────────────────────────────┐
│ [Node 5/5] db_save_node                                         │
│ 주체: Hub Router (Star)                                         │
│ 역할: 전체 워크플로우를 DB에 저장                               │
│                                                                    │
│ 저장 순서:                                                       │
│   1. InputText 저장 (입력 텍스트)                                │
│      주체: InputTextRepository                                   │
│      역할: 사용자 입력 원본 저장                                │
│                                                                    │
│   2. RoutingLog 저장 (라우팅 과정)                              │
│      주체: RoutingLogRepository                                  │
│      역할: Gateway → Hub Router → Branch 라우팅 기록            │
│                                                                    │
│   3. BranchResultRecord 저장 (Branch 결과)                      │
│      주체: BranchResultRepository                                │
│      역할: Branch가 반환한 결과 저장 (Branch는 직접 저장 안함!) │
│                                                                    │
│   4. PolicyDecision 저장 (Star의 최종 결정)                    │
│      주체: PolicyDecisionRepository                              │
│      역할: Star의 최종 액션 결정 기록                           │
│                                                                    │
│ ⚠️ 중요: Star만 DB 접근 가능!                                   │
│ ⚠️ 중요: Branch는 직접 DB 저장 안함!                           │
└─────────────────────────────────────────────────────────────────┘
   ↓
응답 반환 (db.saved: true)
```

---

## ⚠️ 문제 해결

### 문제 1: 인덱스 충돌

**에러 메시지**:
```
(psycopg2.errors.DuplicateTable) relation "ix_branch_results_branch_name" already exists
```

**원인**: 이전에 생성된 인덱스가 남아있음

**해결 방법**:
```bash
# 자동 해결
python scripts/fix_db_tables.py

# 또는 수동 해결 (Neon DB 콘솔)
DROP INDEX IF EXISTS ix_branch_results_branch_name CASCADE;
DROP TABLE IF EXISTS branch_results CASCADE;
python scripts/init_db.py
```

**주체**: `fix_db_tables.py` 또는 개발자
**역할**: 충돌하는 인덱스/테이블 삭제

---

### 문제 2: DB 연결 실패

**에러 메시지**:
```
[DB] 연결 실패: Textual SQL expression 'SELECT 1' should be explicitly declared as text('SELECT 1')
```

**원인**: SQLAlchemy 2.0 문법 변경

**해결 방법**: `app/database/connection.py`에서 수정됨
```python
# 수정 전
db.execute("SELECT 1")

# 수정 후
db.execute(text("SELECT 1"))
```

**주체**: `connection.py` (Hub Router)
**역할**: SQLAlchemy 2.0 호환성 유지

---

### 문제 3: 환경 변수 누락

**에러 메시지**:
```
DATABASE_URL 환경 변수가 올바른지 확인하세요. 현재: (없음)
```

**원인**: `.env` 파일이 없거나 `DATABASE_URL`이 설정되지 않음

**해결 방법**:
1. `.env` 파일 생성 (프로젝트 루트)
2. `DATABASE_URL` 설정
3. `python-dotenv` 설치 확인

**주체**: 개발자/운영자
**역할**: 환경 변수 설정

---

### 문제 4: 인코딩 오류

**에러 메시지**:
```
'utf-8' codec can't decode byte 0xb8 in position 63: invalid start byte
```

**원인**: Windows 환경에서 `.env` 파일 인코딩 문제

**해결 방법**: `app/database/connection.py`에서 다중 인코딩 지원
```python
# utf-8, cp949, euc-kr 순서로 시도
```

**주체**: `connection.py` (Hub Router)
**역할**: 다중 인코딩 지원

---

## 📊 테이블 스키마 (주체별)

### 1. `input_texts` - 입력 텍스트 저장

**주체**: Hub Router (Star)
**역할**: 사용자 입력 원본 저장

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER | PK |
| `text` | TEXT | 입력 텍스트 원본 |
| `user_id` | VARCHAR(255) | 사용자 ID |
| `source` | VARCHAR(50) | 입력 소스 (api, web, etc.) |
| `created_at` | TIMESTAMP | 생성 시간 |

---

### 2. `routing_logs` - 라우팅 로그

**주체**: Hub Router (Star)
**역할**: Gateway → Hub Router → Branch 라우팅 과정 추적

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER | PK |
| `input_text_id` | INTEGER | FK → input_texts |
| `gateway_route` | VARCHAR(100) | Gateway가 선택한 라우트 |
| `gateway_confidence` | FLOAT | Gateway 신뢰도 |
| `gateway_method` | VARCHAR(50) | Gateway 처리 방식 (rule_based, ml_assisted) |
| `selected_branch` | VARCHAR(100) | Hub Router가 선택한 브랜치 |
| `fallback_used` | BOOLEAN | 폴백 사용 여부 |
| `created_at` | TIMESTAMP | 생성 시간 |

---

### 3. `branch_results` - 브랜치 결과

**주체**: Hub Router (Star)
**역할**: Branch가 반환한 결과 저장 (Branch는 직접 저장 안함!)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER | PK |
| `routing_log_id` | INTEGER | FK → routing_logs |
| `branch_name` | VARCHAR(100) | 브랜치 이름 |
| `task_type` | VARCHAR(50) | 태스크 타입 (spam, refund, etc.) |
| `label` | VARCHAR(50) | 분류 라벨 (spam, ham, etc.) |
| `confidence` | FLOAT | 신뢰도 |
| `recommended_action` | VARCHAR(50) | 권장 액션 (block, quarantine, deliver) |
| `reasoning` | TEXT | 분석 근거 |
| `evidence` | JSONB | 증거 배열 |
| `latency_ms` | FLOAT | 처리 시간 (ms) |
| `extra_metadata` | JSONB | 추가 메타데이터 |
| `created_at` | TIMESTAMP | 생성 시간 |

---

### 4. `policy_decisions` - 정책 결정

**주체**: Hub Router (Star)
**역할**: Star의 최종 액션 결정 기록

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER | PK |
| `branch_result_id` | INTEGER | FK → branch_results |
| `branch_name` | VARCHAR(100) | 브랜치 이름 |
| `branch_recommended_action` | VARCHAR(50) | 브랜치 권장 액션 |
| `final_action` | VARCHAR(50) | Star의 최종 액션 |
| `policy_reason` | TEXT | 정책 적용 근거 |
| `ontology_version` | VARCHAR(20) | 온톨로지 버전 |
| `created_at` | TIMESTAMP | 생성 시간 |

---

## 🎯 다음 단계

### 완료 후 체크리스트

- [ ] DB 테이블 생성 완료 (4개 테이블)
- [ ] `save_to_db=true` 요청 성공
- [ ] `db.saved: true` 응답 확인
- [ ] DB에서 데이터 확인 (4개 테이블)
- [ ] 통합 시나리오 테스트 (`strategy/41_TESTING_CHECKLIST.md` 참고)

---

## 📝 참고 문서

- `strategy/36_STAR_TOPOLOGY_HYBRID_ARCHITECTURE.md`: 전체 아키텍처
- `strategy/37.ARCHITECTURE_MAP.md`: 파일 구조 및 역할
- `strategy/41_TESTING_CHECKLIST.md`: 테스트 체크리스트
- `strategy/PHASE5_COMPLETE_SUMMARY.md`: Phase 5 완료 요약

---

**마지막 업데이트**: Phase 5 완료 시점
