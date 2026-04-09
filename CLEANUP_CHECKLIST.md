# 정리 체크리스트 (Cleanup Checklist)

## 📋 목차

1. [즉시 제거 가능 파일](#즉시-제거-가능-파일)
2. [마이그레이션 후 제거](#마이그레이션-후-제거)
3. [레거시 파일 관리](#레거시-파일-관리)
4. [디스크 공간 절약](#디스크-공간-절약)

---

## 즉시 제거 가능 파일

### ✅ 이미 마이그레이션 완료된 폴더

#### 1. `app/services/` → ❌ 제거 대상

**상태**: `app/domain/`으로 이미 마이그레이션됨

**제거 명령**:
```powershell
# 백업 생성
Rename-Item app/services app/services_backup -ErrorAction Stop

# 검증 후 삭제
# Remove-Item app/services_backup -Recurse -Force
```

**이유**:
- ✅ `app/services/spam_classifier/` → `app/domain/spam_filter/services/`
- ✅ `app/services/verdict_agent/` → `app/domain/spam_filter/services/`
- ✅ `app/services/chat_service.py` → `app/domain/chat/services/`
- ✅ `app/services/rag_service.py` → `app/domain/chat/services/`

#### 2. `app/graph.py` → ❌ 제거 대상

**상태**: `app/domain/chat/orchestrators/graph.py`로 대체됨

**제거 명령**:
```powershell
# 백업
Rename-Item app/graph.py app/graph_legacy.py

# 검증 후 삭제
# Remove-Item app/graph_legacy.py
```

#### 3. 중복 스크립트 파일

**제거 대상**:
```powershell
# app/ 루트의 레거시 스크립트
Remove-Item app/api_server.py              # api_server_refactored.py로 대체
Remove-Item app/chatbot_rag.py             # domain/chat/로 대체
Remove-Item app/build_knowledge_base.py    # 사용 안 함
```

---

## 마이그레이션 후 제거

### 🔄 `training/services/` → 재구성 필요

#### 분석 결과

| 파일 | 현재 위치 | 새 위치 | 상태 |
|------|----------|--------|------|
| **Gateway** | | | |
| `gateway/hybrid_gateway.py` | `training/services/gateway/` | `app/domain/shared/gateway/` | 🔄 이동 필요 |
| `gateway/ml_assistant.py` | `training/services/gateway/` | `app/domain/shared/gateway/` | 🔄 이동 필요 |
| `gateway/rule_engine.py` | `training/services/gateway/` | `app/domain/shared/gateway/` | 🔄 이동 필요 |
| `gateway/rules/*.py` | `training/services/gateway/rules/` | `app/domain/shared/gateway/rules/` | 🔄 이동 필요 |
| **Hub** | | | |
| `hub/hub_router.py` | `training/services/hub/` | `app/application/orchestrators/hub/` | 🔄 이동 필요 |
| `hub/branch_registry.py` | `training/services/hub/` | `app/application/orchestrators/hub/` | 🔄 이동 필요 |
| `hub/health_checker.py` | `training/services/hub/` | `app/application/orchestrators/hub/` | 🔄 이동 필요 |
| `hub/ontology_manager.py` | `training/services/hub/` | `app/application/orchestrators/hub/` | 🔄 이동 필요 |
| **Branches** | | | |
| `branches/base_branch.py` | `training/services/branches/` | `app/domain/spam_filter/agents/` | 🔄 이동 필요 |
| `branches/spam_agent.py` | `training/services/branches/` | `app/domain/spam_filter/agents/` | 🔄 이동 필요 |
| **KoELECTRA** | | | |
| `spam_classifier/train.py` | `training/services/spam_classifier/` | `training/koelectra/train.py` | 🔄 통합 필요 |
| `spam_classifier/inference.py` | `training/services/spam_classifier/` | `app/infrastructure/models/koelectra/inference.py` | 🔄 분리 필요 |
| `spam_classifier/pipeline.py` | `training/services/spam_classifier/` | `training/koelectra/train.py` | 🔄 통합 필요 |
| **EXAONE** | | | |
| `verdict_agent/exaone_inference.py` | `training/services/verdict_agent/` | `app/infrastructure/models/exaone/inference.py` | 🔄 이동 필요 |
| `verdict_agent/lora_adapter.py` | `training/services/verdict_agent/` | `training/exaone/train_lora.py` | 🔄 통합 필요 |
| `verdict_agent/load_model.py` | `training/services/verdict_agent/` | `app/infrastructure/models/exaone/loader.py` | 🔄 통합 필요 |
| **기타** | | | |
| `spam_agent_rc/*` | `training/services/spam_agent_rc/` | ❌ 제거 (사용 안 함) | 🗑️ 제거 |
| `langgraph_workflow/*` | `training/services/langgraph_workflow/` | `app/application/orchestrators/` | 🔄 이동 필요 |

#### 마이그레이션 스크립트

**Phase 1: Gateway 이동**

```powershell
# 1. Gateway 폴더 생성
New-Item -ItemType Directory -Path app/domain/shared/gateway -Force
New-Item -ItemType Directory -Path app/domain/shared/gateway/rules -Force

# 2. 파일 이동
Copy-Item training/services/gateway/*.py app/domain/shared/gateway/
Copy-Item training/services/gateway/rules/*.py app/domain/shared/gateway/rules/

# 3. Import 경로 수정 (수동)
# training/services/gateway → app/domain/shared/gateway
```

**Phase 2: Hub 이동**

```powershell
# 1. Hub 폴더 생성
New-Item -ItemType Directory -Path app/application/orchestrators/hub -Force

# 2. 파일 이동
Copy-Item training/services/hub/*.py app/application/orchestrators/hub/

# 3. Import 경로 수정
# training/services/hub → app/application/orchestrators/hub
```

**Phase 3: KoELECTRA 재구성**

```powershell
# 1. training/koelectra/ 생성
New-Item -ItemType Directory -Path training/koelectra -Force

# 2. 훈련 코드 통합
# training/services/spam_classifier/train.py + pipeline.py → training/koelectra/train.py

# 3. 추론 코드 분리
# training/services/spam_classifier/inference.py → app/infrastructure/models/koelectra/inference.py
```

**Phase 4: EXAONE 재구성**

```powershell
# 1. training/exaone/ 생성
New-Item -ItemType Directory -Path training/exaone -Force

# 2. 훈련 코드 통합
# training/services/verdict_agent/lora_adapter.py → training/exaone/train_lora.py

# 3. 추론 코드 분리
# training/services/verdict_agent/exaone_inference.py → app/infrastructure/models/exaone/inference.py
```

**Phase 5: training/services/ 제거**

```powershell
# 마이그레이션 완료 후
Remove-Item training/services -Recurse -Force
```

---

## 레거시 파일 관리

### 📦 보관할 파일 (참고용)

**이유**: 아키텍처 참고, 롤백 가능성

```powershell
# 레거시 백업 폴더 생성
New-Item -ItemType Directory -Path .legacy -Force

# 백업 이동
Move-Item app/services_backup .legacy/app_services
Move-Item app/graph_legacy.py .legacy/
Move-Item training/services .legacy/training_services

# .gitignore 추가
Add-Content .gitignore "`n.legacy/"
```

### 🗑️ 완전 제거할 파일

#### 1. 중복/사용 안 하는 훈련 스크립트

```powershell
# spam_agent_rc (사용 안 함, verdict_agent과 중복)
Remove-Item training/services/spam_agent_rc -Recurse -Force
```

#### 2. 임시 테스트 파일

```powershell
# 루트의 테스트 파일들
Remove-Item test_*.py           # test_api.py 등은 유지
Remove-Item app/test_*.py       # 도메인별 테스트는 유지
Remove-Item check_connection.py
```

#### 3. 중복 데이터 파일

```powershell
# app/data/spam_agent_processed/ - 캐시 파일 정리
Get-ChildItem app/data/spam_agent_processed/*_dataset/cache-*.arrow | Remove-Item
```

---

## 디스크 공간 절약

### 📊 현재 사용량 분석

```powershell
# 폴더별 용량 확인
$folders = @("app", "training", "artifacts")
foreach ($folder in $folders) {
    $size = (Get-ChildItem $folder -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Host "$folder : $([math]::Round($size, 2)) GB"
}

# 상세 분석
Get-ChildItem artifacts/models/ -Recurse -Directory |
    ForEach-Object {
        $size = (Get-ChildItem $_.FullName -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        [PSCustomObject]@{
            Path = $_.FullName
            SizeMB = [math]::Round($size, 2)
        }
    } | Sort-Object SizeMB -Descending | Format-Table -AutoSize
```

### 🧹 정리 대상

#### 1. 모델 체크포인트 (artifacts/models/trained/)

**문제**: 훈련 중 생성된 모든 체크포인트가 보관됨

**해결**:
```powershell
# 최신 체크포인트만 유지, 나머지 삭제
function Keep-LatestCheckpoint {
    param($modelPath)

    $checkpoints = Get-ChildItem "$modelPath/checkpoint-*" -Directory |
        Sort-Object Name -Descending

    # 최신 2개만 유지
    $checkpoints | Select-Object -Skip 2 | ForEach-Object {
        Write-Host "🗑️ 삭제: $($_.Name)"
        Remove-Item $_.FullName -Recurse -Force
    }
}

# KoELECTRA 체크포인트 정리
Keep-LatestCheckpoint "artifacts/models/trained/koelectra/spam_classifier/full/run_20260114_143241"

# EXAONE 체크포인트 정리
# (adapter는 작아서 생략 가능)
```

#### 2. 데이터 캐시 파일

```powershell
# HuggingFace 캐시 정리
Get-ChildItem app/data/ -Recurse -Filter "cache-*.arrow" | Remove-Item
Get-ChildItem app/data/ -Recurse -Filter "*.pyc" | Remove-Item

# 절약 예상: ~500MB
```

#### 3. Python 캐시 파일

```powershell
# __pycache__ 정리
Get-ChildItem -Path . -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force

# .pyc 파일 정리
Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item

# 절약 예상: ~100MB
```

#### 4. 로그 파일 정리

```powershell
# 오래된 로그 제거 (30일 이상)
$cutoffDate = (Get-Date).AddDays(-30)
Get-ChildItem -Path . -Recurse -Filter "*.log" |
    Where-Object { $_.LastWriteTime -lt $cutoffDate } |
    Remove-Item
```

---

## 정리 실행 순서

### 📅 Day 1: 백업 & 레거시 이동

```powershell
# 1. Git 커밋
git add -A
git commit -m "정리 전 백업"
git tag -a "before-cleanup" -m "정리 전 백업"

# 2. 레거시 폴더 생성
New-Item -ItemType Directory -Path .legacy -Force

# 3. 즉시 제거 가능한 파일 백업
Rename-Item app/services app/services_backup
Rename-Item app/graph.py app/graph_legacy.py
Move-Item app/services_backup .legacy/
Move-Item app/graph_legacy.py .legacy/

# 4. 테스트 실행
python -m pytest tests/ -v

# 5. 문제 없으면 커밋
git add -A
git commit -m "정리: 레거시 파일 백업"
```

### 📅 Day 2-3: 마이그레이션

```powershell
# DDD_QUICK_START.md의 Phase 2-3 실행
# - Infrastructure Layer 구축
# - Application Layer 구축
# - training/services/ 마이그레이션

# 검증
python tests/infrastructure/test_models.py
python tests/application/test_use_cases.py
```

### 📅 Day 4: 디스크 정리

```powershell
# 1. 캐시 정리
Get-ChildItem -Path . -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem app/data/ -Recurse -Filter "cache-*.arrow" | Remove-Item

# 2. 체크포인트 정리 (함수 실행)
# Keep-LatestCheckpoint 실행

# 3. 압축 백업
Compress-Archive -Path .legacy/ -DestinationPath "legacy_backup_$(Get-Date -Format 'yyyyMMdd').zip"

# 4. .legacy 폴더 제거 (선택)
# Remove-Item .legacy -Recurse -Force
```

---

## 정리 후 구조

```
langchain/
├── app/                              # EC2 배포 (깔끔)
│   ├── interface/                   # Interface Layer
│   ├── application/                 # Application Layer
│   ├── domain/                      # Domain Layer
│   ├── infrastructure/              # Infrastructure Layer
│   └── main.py
│
├── training/                        # 모델 훈련 (정리됨)
│   ├── koelectra/
│   ├── exaone/
│   └── shared/
│
├── artifacts/                       # 모델 저장소 (최적화됨)
│   └── models/
│       ├── base/
│       └── trained/
│           └── (최신 체크포인트만)
│
├── tests/                           # 테스트
├── scripts/                         # 배포 스크립트
└── .legacy/                         # 레거시 (백업용, .gitignore)
```

---

## 예상 효과

### 📊 정리 전후 비교

| 항목 | 정리 전 | 정리 후 | 절감 |
|------|--------|--------|------|
| **코드 중복** | `app/services/` + `training/services/` | DDD 레이어로 통합 | ~50 파일 |
| **디스크 공간** | ~15 GB | ~10 GB | **~5 GB** |
| **폴더 개수** | 80+ | 50 | **-30** |
| **Import 경로** | 혼란스러움 | 명확함 | ✅ |
| **유지보수성** | 낮음 | 높음 | ✅ |

### 🎯 핵심 개선 사항

1. **역할 명확화**
   - `training/`: 모델 훈련 전용
   - `artifacts/`: 모델 저장소
   - `app/`: 실행 환경 (DDD 레이어 분리)

2. **코드 중복 제거**
   - `inference.py` 통합 → Infrastructure Layer
   - `train.py` 통합 → training/

3. **디스크 공간 최적화**
   - 체크포인트 정리
   - 캐시 파일 제거
   - 레거시 백업

---

## 체크리스트

### ✅ 즉시 실행

- [ ] Git 백업 커밋
- [ ] `app/services/` → `app/services_backup` 이름 변경
- [ ] `app/graph.py` → `app/graph_legacy.py` 이름 변경
- [ ] 테스트 실행 (문제 없는지 확인)

### 🔄 마이그레이션

- [ ] Infrastructure Layer 구축 (DDD_QUICK_START.md 참조)
- [ ] Gateway 이동: `training/services/gateway/` → `app/domain/shared/gateway/`
- [ ] Hub 이동: `training/services/hub/` → `app/application/orchestrators/hub/`
- [ ] KoELECTRA 재구성
- [ ] EXAONE 재구성

### 🧹 정리

- [ ] `training/services/` 제거
- [ ] 캐시 파일 정리
- [ ] 체크포인트 정리
- [ ] 레거시 백업

### 📝 문서화

- [ ] README 업데이트
- [ ] 폴더 구조 문서 생성
- [ ] 배포 가이드 업데이트

---

**정리 우선순위**: 즉시 실행 → 마이그레이션 → 정리 → 문서화

**예상 소요 시간**: 3-4일

**롤백 가능**: `.legacy/` 폴더에 백업 보관
