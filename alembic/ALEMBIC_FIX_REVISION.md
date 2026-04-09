# Alembic "Can't locate revision" 해결

DB에만 있고 코드에는 없는 리비전(예: `ec4a26b7f4c9`)을 가리킬 때 발생합니다.

## 해결 절차

**1. DB를 현재 코드 기준 “마지막 적용된 리비전”으로 맞춤 (마이그레이션은 실행하지 않음)**

```powershell
alembic stamp a637b9e3a950
```

**2. 그 다음 head까지 적용**

```powershell
alembic upgrade head
```

- `a637b9e3a950`: feedback_items의 updated_at 추가 등
- `f8a1b2c3d4e5`: pgvector + 임베딩 테이블 4개

DB 스키마가 이미 `a637b9e3a950`와 다르다면(예: 아직 초기만 적용됐다면) `stamp a637b9e3a950` 대신 실제 적용된 리비전으로 stamp한 뒤 `upgrade head` 하세요.
