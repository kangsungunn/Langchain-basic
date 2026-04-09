# 모델 파일 마이그레이션 요약

## 📋 작업 완료 내역

### 1. 모델 파일 이동 및 분류
모든 훈련된 모델과 베이스 모델을 `app/models/`에서 `artifacts/models/`로 이동하고 종류별로 분류했습니다.

**새로운 구조:**
```
artifacts/models/
├── trained/          # 훈련된 모델
│   ├── exaone/
│   │   ├── adapter/              # Exaone LoRA 어댑터 (최종 모델)
│   │   └── checkpoints/          # Exaone 훈련 체크포인트
│   └── koelectra/
│       └── spam_classifier/      # KoElectra 스팸 분류 모델
└── base/             # 원본 베이스 모델
    ├── exaone-2.4b/
    ├── midm/
    └── koelectra-small-v3-discriminator/
```

### 2. 코드 경로 업데이트

다음 파일들의 모델 경로를 새로운 구조로 업데이트했습니다:

#### 핵심 서비스 파일
- ✅ `app/graph.py` - Exaone, MIDM 모델 경로
- ✅ `app/services/verdict_agent/exaone_inference.py` - Exaone 어댑터/베이스 모델
- ✅ `app/services/spam_classifier/inference.py` - KoElectra 모델
- ✅ `app/services/verdict_agent/load_model.py` - KoElectra 베이스 모델
- ✅ `app/services/spam_agent_rc/load_model.py` - Exaone 베이스 모델

#### 설정 파일
- ✅ `app/config/model_config.py` - MIDM 모델 경로
- ✅ `app/api/dependencies.py` - MIDM 모델 경로 문서

#### API 서버
- ✅ `app/api_server.py` - MIDM 모델 경로

#### 워크플로우 및 라우팅
- ✅ `app/services/langgraph_workflow/nodes.py` - Exaone 모델 경로
- ✅ `app/services/hub/branch_registry.py` - Exaone 모델 경로

#### 학습 및 변환 스크립트
- ✅ `app/services/spam_classifier/train.py` - KoElectra 베이스 모델 경로
- ✅ `app/services/spam_classifier/transform_jsonl.py` - Exaone 토크나이저 경로
- ✅ `app/services/spam_agent_rc/transform_jsonl.py` - Exaone 토크나이저 경로
- ✅ `app/services/spam_agent_rc/lora_adapter.py` - Exaone 모델 경로 및 저장 경로

#### 테스트 및 스크립트
- ✅ `app/services/spam_classifier/test_cli.py` - Exaone 베이스 모델 경로
- ✅ `app/services/spam_classifier/test_gate_cli.py` - Exaone 베이스 모델 경로
- ✅ `app/test_midm_loading.py` - MIDM 모델 경로
- ✅ `app/scripts/load_local_model.py` - MIDM 모델 경로
- ✅ `app/scripts/test_midm_with_langchain.py` - MIDM 모델 경로
- ✅ `app/models/providers/local_llama_provider.py` - MIDM 모델 경로

## 🔄 경로 변경 매핑

### 베이스 모델
| 이전 경로 | 새 경로 |
|---------|---------|
| `app/models/original/exaone-2.4b` | `artifacts/models/base/exaone-2.4b` |
| `app/models/original/midm` | `artifacts/models/base/midm` |
| `app/models/original/models--monologg--koelectra-small-v3-discriminator/...` | `artifacts/models/base/koelectra-small-v3-discriminator/...` |

### 훈련된 모델
| 이전 경로 | 새 경로 |
|---------|---------|
| `app/models/exaone/` (어댑터) | `artifacts/models/trained/exaone/adapter/` |
| `checkpoints/exaone-spam-filter-v2/checkpoint-3000` | `artifacts/models/trained/exaone/checkpoints/exaone-spam-filter-v2/checkpoint-3000` |
| `models/spam/full/` | `artifacts/models/trained/koelectra/spam_classifier/full/` |

### 환경 변수 기본값
| 환경 변수 | 이전 기본값 | 새 기본값 |
|---------|-----------|----------|
| `EXAONE_MODEL_PATH` | `app/models/original/exaone-2.4b` | `artifacts/models/base/exaone-2.4b` |
| `MIDM_MODEL_PATH` | `app/models/midm` | `artifacts/models/base/midm` |

## ⚠️ 주의사항

### 1. 원본 파일 정리
`app/models/` 디렉토리의 원본 파일들은 아직 남아있습니다. 모든 테스트가 완료된 후 다음 디렉토리를 삭제할 수 있습니다:
- `app/models/exaone/`
- `app/models/koelectra/`
- `app/models/original/`

**주의**: `app/models/factory.py`, `app/models/base.py`, `app/models/providers/` 등 코드 파일은 삭제하지 마세요!

### 2. 환경 변수 설정
프로덕션 환경에서 환경 변수를 사용하는 경우, 새로운 경로로 업데이트하세요:
```bash
export EXAONE_MODEL_PATH=artifacts/models/base/exaone-2.4b
export MIDM_MODEL_PATH=artifacts/models/base/midm
```

### 3. 체크포인트 경로
일부 코드에서 `checkpoints/` 경로를 직접 참조하는 경우가 있을 수 있습니다. 이 경우 `artifacts/models/trained/exaone/checkpoints/`로 변경해야 합니다.

## ✅ 다음 단계

1. **테스트 실행**: 모든 모델 로드 기능이 정상 작동하는지 확인
2. **원본 파일 삭제**: 테스트 완료 후 `app/models/exaone/`, `app/models/koelectra/`, `app/models/original/` 삭제
3. **문서 업데이트**: README나 다른 문서에 새로운 경로 반영

## 📝 참고 문서

- `artifacts/models/README.md` - 모델 디렉토리 구조 상세 설명
