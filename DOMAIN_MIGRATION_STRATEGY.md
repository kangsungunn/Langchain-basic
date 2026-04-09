# 도메인 중심 구조(Structure A) 전환 전략

## 📊 현재 상황 분석

### 기존 구조 (Structure B - 계층형)
```
app/
├─ services/          # 비즈니스 로직
│   ├─ spam_classifier/
│   ├─ verdict_agent/
│   ├─ spam_agent_rc/
│   ├─ chat_service.py
│   ├─ rag_service.py
│   ├─ training_service.py
│   ├─ hub/
│   ├─ gateway/
│   └─ branches/
├─ router/            # API 라우터
├─ repository/        # 데이터 접근
└─ models/            # 공통 모델
```

### 새로운 도메인 구조 (이미 생성됨)
```
app/
├─ domain/
│   ├─ admin/        # 관리자 도메인
│   ├─ consumer/     # 소비자 도메인
│   ├─ partner/      # 파트너 도메인
│   ├─ community/    # 커뮤니티 도메인
│   └─ shared/       # 공통 도메인
└─ api/v1/          # API 엔드포인트
    ├─ admin/
    ├─ consumer/
    ├─ partner/
    └─ community/
```

## 🎯 마이그레이션 매핑 전략

### 1. 새 도메인 생성 필요
기존 `services/`의 코드를 다음 도메인으로 매핑:

```
domain/
├─ spam_filter/          # 🆕 새로 생성
│   ├─ agents/          # verdict_agent, spam_classifier
│   ├─ services/        # inference, pipeline
│   ├─ models/          # base_model, state_model
│   ├─ repositories/    # 스팸 DB 접근
│   └─ orchestrators/   # gate_graph
│
├─ chat/                # 🆕 새로 생성
│   ├─ agents/          # chat agent
│   ├─ services/        # chat_service, rag_service
│   ├─ models/          # chat request/response
│   ├─ repositories/    # chat history
│   └─ orchestrators/   # langgraph_workflow
│
├─ training/            # 🆕 새로 생성
│   ├─ agents/          # training agent
│   ├─ services/        # training_service, lora_adapter
│   ├─ models/          # training config
│   └─ repositories/    # checkpoint 관리
│
└─ shared/
    ├─ orchestrators/   # hub, gateway, branches (기존 것 이동)
    ├─ services/        # embedding_ingest_service
    └─ models/          # 공통 모델
```

### 2. API 라우터 매핑

```
api/v1/
├─ spam_filter/        # 🆕 새로 생성
│   └─ filter_router.py    # POST /filter, /analyze
│
├─ chat/               # 🆕 새로 생성
│   └─ chat_router.py      # POST /chat, /rag
│
├─ training/           # 🆕 새로 생성
│   └─ training_router.py  # POST /train, /checkpoint
│
└─ admin/              # 기존 유지
    └─ mail_router.py
```

## 📋 상세 마이그레이션 계획

### Phase 1: 새 도메인 구조 생성 (1일)

#### 1-1. spam_filter 도메인 생성
```bash
domain/spam_filter/
├─ __init__.py
├─ agents/
│   ├─ __init__.py
│   ├─ spam_classifier_agent.py    # services/spam_classifier/ 이동
│   └─ verdict_agent.py            # services/verdict_agent/ 이동
├─ services/
│   ├─ __init__.py
│   ├─ inference_service.py        # spam_classifier/inference.py
│   ├─ pipeline_service.py         # spam_classifier/pipeline.py
│   ├─ training_service.py         # spam_classifier/train.py
│   └─ exaone_service.py           # verdict_agent/exaone_inference.py
├─ models/
│   ├─ __init__.py
│   ├─ request.py                  # verdict_agent/base_model.py
│   ├─ response.py                 # verdict_agent/state_model.py
│   └─ schemas.py
├─ repositories/
│   ├─ __init__.py
│   └─ spam_repository.py
└─ orchestrators/
    ├─ __init__.py
    └─ spam_filter_graph.py        # spam_classifier/gate_graph.py
```

#### 1-2. chat 도메인 생성
```bash
domain/chat/
├─ __init__.py
├─ agents/
│   ├─ __init__.py
│   └─ chat_agent.py
├─ services/
│   ├─ __init__.py
│   ├─ chat_service.py             # services/chat_service.py
│   └─ rag_service.py              # services/rag_service.py
├─ models/
│   ├─ __init__.py
│   ├─ chat_request.py
│   └─ chat_response.py
├─ repositories/
│   ├─ __init__.py
│   └─ chat_history_repository.py
└─ orchestrators/
    ├─ __init__.py
    ├─ chat_graph.py               # services/langgraph_workflow/graph.py
    └─ nodes.py                    # services/langgraph_workflow/nodes.py
```

#### 1-3. training 도메인 생성
```bash
domain/training/
├─ __init__.py
├─ agents/
│   ├─ __init__.py
│   └─ training_agent.py
├─ services/
│   ├─ __init__.py
│   ├─ training_service.py         # services/training_service.py
│   ├─ lora_service.py             # spam_agent_rc/lora_adapter.py
│   └─ transform_service.py        # spam_classifier/transform_jsonl.py
├─ models/
│   ├─ __init__.py
│   └─ training_config.py
└─ repositories/
    ├─ __init__.py
    └─ checkpoint_repository.py
```

#### 1-4. shared 도메인 확장
```bash
domain/shared/
├─ orchestrators/
│   ├─ __init__.py
│   ├─ hub_orchestrator.py         # services/hub/hub_router.py
│   ├─ gateway.py                  # services/gateway/hybrid_gateway.py
│   └─ branch_registry.py          # services/hub/branch_registry.py
├─ services/
│   ├─ __init__.py
│   └─ embedding_service.py        # services/embedding_ingest_service.py
└─ models/
    ├─ __init__.py
    └─ factory.py                  # app/models/factory.py (참조)
```

### Phase 2: API 라우터 생성 (1일)

#### 2-1. spam_filter API
```python
# api/v1/spam_filter/filter_router.py
from fastapi import APIRouter
from app.domain.spam_filter.orchestrators import spam_filter_graph

filter_router = APIRouter(prefix="/api/v1/spam-filter", tags=["spam-filter"])

@filter_router.post("/filter")
async def filter_email(request: EmailFilterRequest):
    """이메일 스팸 필터링"""
    return spam_filter_graph.run(request)
```

#### 2-2. chat API
```python
# api/v1/chat/chat_router.py
from fastapi import APIRouter
from app.domain.chat.orchestrators import chat_graph

chat_router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

@chat_router.post("/chat")
async def chat(request: ChatRequest):
    """채팅"""
    return chat_graph.run(request)
```

#### 2-3. training API
```python
# api/v1/training/training_router.py
from fastapi import APIRouter
from app.domain.training.services import training_service

training_router = APIRouter(prefix="/api/v1/training", tags=["training"])

@training_router.post("/train")
async def train_model(config: TrainingConfig):
    """모델 훈련"""
    return training_service.train(config)
```

### Phase 3: 코드 마이그레이션 (3-5일)

#### 우선순위 순서:
1. **spam_filter** (가장 독립적) - 2일
2. **training** (타 도메인 의존도 낮음) - 1일
3. **chat** (여러 도메인 참조 가능성) - 2일
4. **shared** (공통 기능) - 1일

### Phase 4: 의존성 제거 및 정리 (2일)

1. `app/services/` 디렉토리 삭제
2. `app/router/` 디렉토리 삭제
3. `app/repository/` → `domain/shared/repositories/`로 통합
4. import 문 정리

## 🔄 마이그레이션 체크리스트

### spam_filter 도메인
- [ ] 디렉토리 구조 생성
- [ ] spam_classifier 코드 이동
- [ ] verdict_agent 코드 이동
- [ ] spam_agent_rc 코드 이동
- [ ] 모델 파일 통합
- [ ] API 라우터 생성
- [ ] 테스트 실행
- [ ] 기존 코드 삭제

### chat 도메인
- [ ] 디렉토리 구조 생성
- [ ] chat_service 코드 이동
- [ ] rag_service 코드 이동
- [ ] langgraph_workflow 코드 이동
- [ ] 모델 파일 통합
- [ ] API 라우터 생성
- [ ] 테스트 실행
- [ ] 기존 코드 삭제

### training 도메인
- [ ] 디렉토리 구조 생성
- [ ] training_service 코드 이동
- [ ] lora_adapter 코드 이동
- [ ] transform 코드 이동
- [ ] 모델 파일 통합
- [ ] API 라우터 생성
- [ ] 테스트 실행
- [ ] 기존 코드 삭제

### shared 도메인
- [ ] hub 코드 이동
- [ ] gateway 코드 이동
- [ ] branches 코드 이동
- [ ] embedding_service 코드 이동
- [ ] 공통 유틸 정리
- [ ] 테스트 실행

## ⚠️ 주의사항

1. **기존 API 엔드포인트 호환성 유지**
   - 기존 `/api/mcp/filter` 등을 `/api/v1/spam-filter/filter`로 redirect 또는 병행 유지

2. **import 경로 일괄 변경**
   - `from app.services.spam_classifier import ...`
   - → `from app.domain.spam_filter.services import ...`

3. **테스트 파일 위치**
   - `domain/spam_filter/tests/` 각 도메인에 tests 폴더 생성

4. **환경 변수 및 설정**
   - 도메인별 설정 파일 분리 검토

## 📝 예상 소요 시간

| Phase | 작업 | 예상 기간 |
|-------|------|-----------|
| 1 | 새 도메인 구조 생성 | 1일 |
| 2 | API 라우터 생성 | 1일 |
| 3 | 코드 마이그레이션 | 3-5일 |
| 4 | 의존성 제거 및 정리 | 2일 |

**총 예상 기간**: 7-9일

## 🚀 시작 준비 완료

지금 바로 시작하시겠습니까?
- Phase 1부터 단계별로 진행
- 또는 특정 도메인부터 시작 (추천: spam_filter)
