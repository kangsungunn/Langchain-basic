# ⚠️ DB 테이블 생성 미완료 (나중에 해결 필요!)

## 📌 현재 상황

**날짜**: Phase 5 진행 전
**문제**: DB 테이블이 제대로 생성되지 않음

### 현재 테이블 상태
```
✅ login_logs (기존 테이블, 유지됨)
❌ input_texts (생성 안됨)
❌ routing_logs (생성 안됨)
❌ branch_results (생성 안됨)
❌ policy_decisions (생성 안됨)
```

### 오류 원인
```
인덱스 충돌: ix_branch_results_branch_name already exists
```

---

## ✅ 해결 방법 (Phase 5 완료 후 실행)

### 1단계: Neon DB 콘솔 또는 psql 접속

**Neon DB 콘솔**: https://console.neon.tech/

또는

```bash
psql postgresql://neondb_owner:npg_...@ep-silent-salad-a1yx5hde-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

### 2단계: 충돌하는 인덱스 삭제

```sql
-- 충돌하는 인덱스/테이블 모두 삭제 (CASCADE로 안전하게)
DROP INDEX IF EXISTS ix_branch_results_branch_name CASCADE;
DROP INDEX IF EXISTS ix_branch_results_task_type CASCADE;
DROP INDEX IF EXISTS ix_branch_results_label CASCADE;
DROP INDEX IF EXISTS ix_branch_results_created_at CASCADE;

-- 또는 테이블 자체를 삭제하고 다시 만들기 (데이터 손실 주의!)
DROP TABLE IF EXISTS branch_results CASCADE;
```

### 3단계: 테이블 재생성

```bash
python scripts/init_db.py
```

**예상 출력**:
```
[2/3] 기존 테이블 확인 중...
✅ 기존 테이블 발견: 1개
   테이블: login_logs

[3/3] 테이블 생성 중...
✅ 데이터베이스 초기화 완료!

현재 테이블: 5개
  1. branch_results      ← 새로 생성됨!
  2. input_texts         ← 새로 생성됨!
  3. login_logs
  4. policy_decisions    ← 새로 생성됨!
  5. routing_logs        ← 새로 생성됨!
```

---

## 🧪 테스트 (테이블 생성 후)

```bash
# DB CRUD 테스트
python scripts/test_db.py
```

---

## 📝 참고

- **DB URL**: `.env` 파일에 저장되어 있음
- **주체**: Hub Router (Star)만 DB 접근 가능
- **테이블**: 총 4개 (input_texts, routing_logs, branch_results, policy_decisions)
- **인덱스**: 각 테이블당 3-5개

---

**Phase 5 완료 후 이 파일을 다시 확인하세요!** ⚠️
