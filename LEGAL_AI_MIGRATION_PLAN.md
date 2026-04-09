# 변리사 AI 에이전트 마이그레이션 계획서

## 🎯 목표

**기존**: 스팸 필터 시스템
**신규**: 변리사 AI 에이전트 (특허/상표 심사 판단, 분쟁 대응, 문서 자동화)

---

## 📊 현재 상태 분석

### 유지할 인프라 (재사용)

✅ **app/domain/shared/** - 공통 오케스트레이션
- `orchestrators/` → `app/core/shared/orchestration/`으로 이동
- LangGraph 워크플로우 구조 재사용
- Star Topology 아키텍처 유지

✅ **app/domain/chat/** - RAG 시스템
- `services/rag_service.py` → `app/core/shared/rag/`로 이동
- 벡터 DB 구조 재사용 (판례 검색에 활용)

✅ **app/graph.py** - LangGraph 구조
- → `app/core/shared/orchestration/star_node.py`로 재구성

✅ **app/database/** - DB 인프라
- `connection.py`, `repositories.py` 유지
- PostgreSQL + PGVector 활용 (판례/법령 저장)

✅ **artifacts/models/base/**
- `koelectra/` - 1차 분류기로 재활용 (법률 도메인 파인튜닝)
- `exaone/` - 중앙 법률 판단 LLM으로 재활용

✅ **training/** 구조
- 훈련 파이프라인 재사용
- 데이터만 법률 도메인으로 교체

---

## 🗑️ 삭제 대상

### 즉시 삭제 (스팸 필터 전용)

❌ **app/domain/spam_filter/** - 스팸 도메인 전체
```
app/domain/spam_filter/
├── agents/
├── models/
├── orchestrators/
├── repositories/
└── services/
```
**이유**: 법률 AI와 무관, 완전히 다른 도메인

❌ **app/domain/admin/** - 이메일 관리
```
app/domain/admin/
```
**이유**: 관리자 기능 불필요

❌ **app/domain/consumer/** - 소비자 도메인
❌ **app/domain/partner/** - 파트너 도메인
❌ **app/domain/community/** - 커뮤니티 도메인

**이유**: 법률 AI와 무관한 비즈니스 도메인

❌ **app/api/v1/spam_filter/** - 스팸 API
❌ **app/api/v1/admin/** - 관리자 API
❌ **app/api/v1/chat/** - 채팅 API (RAG는 core로 이동)

**이유**: 새 API 구조로 재작성

❌ **training/services/** - 레거시 훈련 코드
```
training/services/
├── spam_classifier/
├── spam_agent_rc/
├── verdict_agent/
└── ...
```
**이유**: 이미 중복, 새로운 training/ 구조로 교체

❌ **app/data/** - 스팸 데이터셋
```
app/data/
├── spam_agent_processed/
├── korean-malicious-comments-dataset-master/
└── 한국우편사업진흥원_스팸메일*.jsonl
```
**이유**: 법률 AI와 무관

---

## ⚠️ 보류 (사용자 판단 필요)

### 🤔 app/domain/training/
```
app/domain/training/
├── services/
│   ├── training_service.py
│   ├── lora_service.py
│   └── train_service.py
```
**질문**: 이 훈련 서비스를 유지할까요?
- **옵션 A**: 삭제 (training/ 폴더에서 직접 훈련 스크립트 실행)
- **옵션 B**: 유지 (API로 훈련 트리거 가능)

**추천**: 옵션 A (간결성)

### 🤔 artifacts/models/trained/
```
artifacts/models/trained/
├── koelectra/spam_classifier/  # 스팸 분류 체크포인트
└── exaone/adapter/             # 스팸 LoRA 어댑터
```
**질문**: 기존 훈련된 모델을 삭제할까요?
- **옵션 A**: 삭제 (법률 도메인으로 새로 훈련)
- **옵션 B**: 백업 후 삭제

**추천**: 옵션 B (백업 → S3 또는 .legacy/)

### 🤔 frontend/
```
frontend/  # React 프론트엔드
```
**질문**: 프론트엔드를 유지할까요?
- **옵션 A**: 삭제 (API만 제공)
- **옵션 B**: 유지 (법률 AI용 UI로 재구성)

**추천**: 옵션 A (현재는 API 우선)

---

## 🔄 이동/재구성 대상

### app/ 재구성

| 현재 위치 | 새 위치 | 작업 |
|----------|--------|------|
| `app/domain/shared/orchestrators/` | `app/core/shared/orchestration/` | 이동 + 재구성 |
| `app/domain/chat/services/rag_service.py` | `app/core/shared/rag/retriever.py` | 이동 + 이름 변경 |
| `app/graph.py` | `app/core/shared/orchestration/star_node.py` | 재구성 |
| `app/domain/shared/services/embedding_service.py` | `app/core/shared/rag/embeddings.py` | 이동 |
| `app/database/` | `app/domain/shared/repositories/` | 이동 |

### training/ 재구성

| 현재 위치 | 새 위치 | 작업 |
|----------|--------|------|
| `training/services/spam_classifier/train.py` | `training/shared/base_training.py` | 통합 (재사용 가능 부분만) |
| `training/services/verdict_agent/lora_adapter.py` | `training/shared/lora_utils.py` | 통합 |

---

## 📋 마이그레이션 단계

### Phase 0: 백업 (필수)

```powershell
# Git 커밋
git add -A
git commit -m "백업: 변리사 AI 마이그레이션 전"
git tag -a "before-legal-ai-migration" -m "스팸 필터 최종 버전"

# 중요 파일 압축 백업
Compress-Archive -Path app/domain/, artifacts/models/trained/ -DestinationPath "backup_legal_migration_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
```

### Phase 1: 새 폴더 구조 생성

```powershell
# app/ 새 구조 생성
New-Item -ItemType Directory -Path app/api/examination, app/api/dispute, app/api/document -Force
New-Item -ItemType Directory -Path app/core/examination, app/core/dispute, app/core/document -Force
New-Item -ItemType Directory -Path app/core/shared/models, app/core/shared/rag, app/core/shared/legal, app/core/shared/orchestration -Force
New-Item -ItemType Directory -Path app/domain/examination, app/domain/dispute, app/domain/document, app/domain/shared -Force

# training/ 새 구조 생성
New-Item -ItemType Directory -Path training/examination/patent, training/examination/trademark -Force
New-Item -ItemType Directory -Path training/dispute, training/document, training/shared -Force

# data/ 법률 데이터 폴더
New-Item -ItemType Directory -Path data/raw, data/processed, data/annotations -Force
```

### Phase 2: 재사용 코드 이동

```powershell
# LangGraph 오케스트레이션 이동
Copy-Item app/domain/shared/orchestrators/* app/core/shared/orchestration/ -Recurse

# RAG 시스템 이동
Copy-Item app/domain/chat/services/rag_service.py app/core/shared/rag/retriever.py

# 데이터베이스 이동
Copy-Item app/database/* app/domain/shared/repositories/ -Recurse
```

### Phase 3: 불필요한 파일 삭제

```powershell
# 스팸 도메인 제거
Remove-Item app/domain/spam_filter -Recurse -Force
Remove-Item app/domain/admin -Recurse -Force
Remove-Item app/domain/consumer -Recurse -Force
Remove-Item app/domain/partner -Recurse -Force
Remove-Item app/domain/community -Recurse -Force

# 스팸 API 제거
Remove-Item app/api/v1 -Recurse -Force

# 레거시 훈련 코드 제거
Remove-Item training/services -Recurse -Force

# 스팸 데이터 제거
Remove-Item app/data -Recurse -Force
```

### Phase 4: 새 코드 작성

- `app/api/main.py` - FastAPI 앱
- `app/core/shared/orchestration/star_node.py` - Legal Star Node
- `app/core/examination/patent_analyzer.py` - 특허성 분석
- `app/domain/examination/models.py` - Patent 모델

### Phase 5: 검증

```powershell
# Import 에러 확인
python -c "from app.api.main import app; print('✅ API 로드 성공')"

# 폴더 구조 확인
tree app /F
```

---

## ✅ 최종 폴더 구조

```
legal-ai-agent/
├── app/
│   ├── api/
│   │   ├── main.py
│   │   ├── examination/
│   │   ├── dispute/
│   │   └── document/
│   ├── core/
│   │   ├── examination/
│   │   ├── dispute/
│   │   ├── document/
│   │   └── shared/
│   │       ├── models/
│   │       ├── rag/
│   │       ├── legal/
│   │       └── orchestration/
│   └── domain/
│       ├── examination/
│       ├── dispute/
│       ├── document/
│       └── shared/
│
├── artifacts/
│   ├── models/
│   │   ├── base/
│   │   └── finetuned/
│   ├── vectordb/
│   └── knowledge/
│
├── training/
│   ├── examination/
│   ├── dispute/
│   ├── document/
│   └── shared/
│
└── data/
    ├── raw/
    ├── processed/
    └── annotations/
```

---

## 🚨 안전 장치

### 롤백 방법

```powershell
# Git으로 롤백
git reset --hard before-legal-ai-migration

# 또는 백업 복원
Expand-Archive backup_legal_migration_*.zip -DestinationPath .
```

### 검증 체크리스트

- [ ] Git 백업 완료
- [ ] 압축 백업 완료
- [ ] 새 폴더 구조 생성 완료
- [ ] 재사용 코드 이동 완료
- [ ] Import 에러 없음
- [ ] API 서버 실행 가능

---

## 📝 사용자 확인 필요

### ❓ 질문 1: app/domain/training/ 처리
- [ ] **삭제** (training/ 폴더만 사용)
- [ ] **유지** (API로 훈련 트리거)

### ❓ 질문 2: artifacts/models/trained/ 처리
- [ ] **백업 후 삭제** (S3 또는 .legacy/)
- [ ] **삭제** (새로 훈련)
- [ ] **유지** (참고용)

### ❓ 질문 3: frontend/ 처리
- [ ] **삭제** (API만 제공)
- [ ] **유지** (법률 AI용 UI로 재구성)

### ❓ 질문 4: libs/ (LangChain 소스) 처리
- [ ] **삭제** (pip install langchain 사용)
- [ ] **유지** (커스터마이징 필요시)

---

## 🎯 다음 단계

1. ✅ 이 계획서 검토
2. ⏸️ 사용자 확인 (보류 항목)
3. ⏸️ Phase 0-5 실행
4. ⏸️ 새 코드 작성
5. ⏸️ 테스트 및 검증

---

**결정해주세요:**

1. **app/domain/training/** - 삭제/유지?
2. **artifacts/models/trained/** - 백업 후 삭제/삭제/유지?
3. **frontend/** - 삭제/유지?
4. **libs/** - 삭제/유지?

이 4가지만 결정해주시면 바로 실행하겠습니다! 🚀
