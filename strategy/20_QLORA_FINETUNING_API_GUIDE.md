# 20. QLoRA 파인튜닝 및 대화 API 가이드

## 📋 개요

이 문서는 `chat_service.py`와 `chat_router.py`에 구현된 QLoRA 기반 파인튜닝 및 대화 기능의 사용 가이드입니다.

## 🎯 주요 기능

### 1. QLoRA (Quantized Low-Rank Adaptation)
- **4bit 양자화**: 메모리 효율적인 모델 로딩
- **LoRA 어댑터**: 일부 파라미터만 학습하여 빠른 파인튜닝
- **메모리 절약**: 대형 LLM을 소형 GPU에서도 학습 가능

### 2. API 엔드포인트
- 모델 로드/언로드
- 파인튜닝 실행
- 학습된 모델과 대화
- 모델 상태 관리

## 🛠️ API 엔드포인트 상세

### 1. 모델 로드

#### 새 모델 로드 (학습용)
```bash
POST /api/chat/qlora/load
```

**요청 본문:**
```json
{
  "model_name": "beomi/Llama-3-Open-Ko-8B",
  "lora_r": 8,
  "lora_alpha": 16,
  "lora_dropout": 0.05,
  "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"]
}
```

**파라미터 설명:**
- `model_name`: HuggingFace 모델 이름
- `lora_r`: LoRA rank (낮을수록 파라미터 적음, 기본값: 8)
- `lora_alpha`: LoRA scaling factor (기본값: 16)
- `lora_dropout`: Dropout 비율 (기본값: 0.05)
- `target_modules`: LoRA를 적용할 레이어 (옵션)

**응답:**
```json
{
  "status": "success",
  "message": "QLoRA 모델 로드 완료: beomi/Llama-3-Open-Ko-8B",
  "model_info": {
    "loaded": true,
    "model_name": "beomi/Llama-3-Open-Ko-8B",
    "adapter_path": null,
    "config": {
      "lora_r": 8,
      "lora_alpha": 16,
      "lora_dropout": 0.05
    }
  }
}
```

#### 학습된 모델 로드
```bash
POST /api/chat/qlora/load_trained?base_model_name=beomi/Llama-3-Open-Ko-8B&adapter_path=./checkpoints/qlora/final_model
```

**쿼리 파라미터:**
- `base_model_name`: 베이스 모델 이름
- `adapter_path`: 학습된 어댑터 경로

### 2. 모델 상태 확인

```bash
GET /api/chat/qlora/status
```

**응답:**
```json
{
  "loaded": true,
  "model_name": "beomi/Llama-3-Open-Ko-8B",
  "adapter_path": "./checkpoints/qlora/final_model"
}
```

### 3. QLoRA 모델과 대화

```bash
POST /api/chat/qlora/chat?max_new_tokens=512&temperature=0.7&top_p=0.9
```

**요청 본문:**
```json  
{
  "message": "LangChain에 대해 설명해줘"
}
```

**쿼리 파라미터:**
- `max_new_tokens`: 생성할 최대 토큰 수 (기본값: 512)
- `temperature`: 온도 값 (0.1-1.0, 높을수록 창의적, 기본값: 0.7)
- `top_p`: Top-p 샘플링 (0.1-1.0, 기본값: 0.9)

**응답:**
```json
{
  "answer": "LangChain은 대형 언어 모델을 활용한 애플리케이션 개발을 위한 프레임워크입니다...",
  "sources": ["🤖 출처: QLoRA Fine-tuned Model"],
  "timestamp": "2024-12-18T10:30:00",
  "model_info": {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 512
  }
}
```

### 4. 파인튜닝 실행

```bash
POST /api/chat/qlora/train
```

**요청 본문:**
```json
{
  "conversations": [
    {
      "prompt": "LangChain이 뭐야?",
      "response": "LangChain은 LLM 애플리케이션 개발을 위한 프레임워크입니다."
    },
    {
      "prompt": "RAG는 무엇인가요?",
      "response": "RAG는 검색 증강 생성(Retrieval-Augmented Generation) 기법입니다."
    }
  ],
  "output_dir": "./checkpoints/qlora",
  "num_train_epochs": 3,
  "per_device_train_batch_size": 4,
  "learning_rate": 0.0002
}
```

**파라미터 설명:**
- `conversations`: 학습 데이터 (prompt-response 쌍의 배열)
- `output_dir`: 체크포인트 저장 경로
- `num_train_epochs`: 학습 에폭 수
- `per_device_train_batch_size`: 배치 크기
- `learning_rate`: 학습률

**응답:**
```json
{
  "status": "success",
  "message": "QLoRA 학습 완료",
  "result": {
    "status": "completed",
    "output_dir": "./checkpoints/qlora",
    "final_model_path": "./checkpoints/qlora/final_model",
    "train_loss": 0.345,
    "epochs": 3,
    "timestamp": "2024-12-18T11:00:00"
  }
}
```

### 5. 모델 언로드

```bash
POST /api/chat/qlora/unload
```

**응답:**
```json
{
  "status": "success",
  "message": "QLoRA 모델 언로드 완료"
}
```

## 📝 사용 시나리오

### 시나리오 1: 새 모델 학습 및 사용

```bash
# Step 1: 모델 로드
curl -X POST "http://localhost:8000/api/chat/qlora/load" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "beomi/Llama-3-Open-Ko-8B",
    "lora_r": 8,
    "lora_alpha": 16
  }'

# Step 2: 학습 데이터 준비 및 파인튜닝
curl -X POST "http://localhost:8000/api/chat/qlora/train" \
  -H "Content-Type: application/json" \
  -d '{
    "conversations": [
      {"prompt": "질문1", "response": "답변1"},
      {"prompt": "질문2", "response": "답변2"}
    ],
    "num_train_epochs": 3,
    "output_dir": "./checkpoints/my_model"
  }'

# Step 3: 학습된 모델과 대화
curl -X POST "http://localhost:8000/api/chat/qlora/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요!"}'

# Step 4: 메모리 해제 (필요시)
curl -X POST "http://localhost:8000/api/chat/qlora/unload"
```

### 시나리오 2: 기존 학습 모델 사용

```bash
# Step 1: 학습된 어댑터 로드
curl -X POST "http://localhost:8000/api/chat/qlora/load_trained?base_model_name=beomi/Llama-3-Open-Ko-8B&adapter_path=./checkpoints/my_model/final_model"

# Step 2: 상태 확인
curl -X GET "http://localhost:8000/api/chat/qlora/status"

# Step 3: 대화하기
curl -X POST "http://localhost:8000/api/chat/qlora/chat?temperature=0.8" \
  -H "Content-Type: application/json" \
  -d '{"message": "LangChain에 대해 설명해줘"}'
```

## 🔧 Python 코드 예제

### ChatService 직접 사용

```python
from app.services.chat_service import ChatService
from app.services.rag_service import RAGService

# 서비스 초기화
rag_service = RAGService(llm, embeddings, repository)
chat_service = ChatService(rag_service)

# 1. QLoRA 모델 로드
model, tokenizer = chat_service.load_qlora_model(
    model_name="beomi/Llama-3-Open-Ko-8B",
    lora_r=8,
    lora_alpha=16
)

# 2. 대화하기
response = chat_service.chat_with_qlora_model(
    model=model,
    tokenizer=tokenizer,
    message="안녕하세요!",
    temperature=0.7
)
print(response["answer"])

# 3. 학습 데이터 준비
conversations = [
    {"prompt": "질문1", "response": "답변1"},
    {"prompt": "질문2", "response": "답변2"}
]
train_dataset = chat_service.prepare_training_dataset(
    tokenizer=tokenizer,
    conversations=conversations
)

# 4. 파인튜닝
result = chat_service.train_qlora_model(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    num_train_epochs=3,
    output_dir="./checkpoints/my_model"
)
print(f"학습 완료! 모델 위치: {result['final_model_path']}")

# 5. 학습된 모델 로드
trained_model, trained_tokenizer = chat_service.load_trained_qlora_model(
    base_model_name="beomi/Llama-3-Open-Ko-8B",
    adapter_path="./checkpoints/my_model/final_model"
)
```

## ⚙️ 설정 가이드

### LoRA 하이퍼파라미터

#### lora_r (Rank)
- **낮은 값 (4-8)**: 적은 파라미터, 빠른 학습, 작은 메모리
- **높은 값 (16-32)**: 많은 파라미터, 더 나은 성능, 큰 메모리

#### lora_alpha
- 일반적으로 `lora_r`의 2배 사용
- `lora_r=8`이면 `lora_alpha=16` 권장

#### target_modules
- **Llama 계열**: `["q_proj", "k_proj", "v_proj", "o_proj"]`
- **GPT 계열**: `["c_attn", "c_proj"]`
- **모든 Linear 레이어**: 더 많은 레이어 추가 가능

### 학습 하이퍼파라미터

#### num_train_epochs
- **작은 데이터셋 (< 100)**: 5-10 에폭
- **중간 데이터셋 (100-1000)**: 3-5 에폭
- **큰 데이터셋 (> 1000)**: 1-3 에폭

#### learning_rate
- **기본값**: 2e-4 (0.0002)
- **작은 모델**: 3e-4
- **큰 모델**: 1e-4

#### per_device_train_batch_size
- GPU 메모리에 따라 조절
- **8GB GPU**: 1-2
- **16GB GPU**: 2-4
- **24GB GPU**: 4-8

## 🎯 베스트 프랙티스

### 1. 메모리 관리
```python
# 학습 전에 기존 모델 언로드
POST /api/chat/qlora/unload

# 새 모델 로드
POST /api/chat/qlora/load
```

### 2. 학습 데이터 품질
- 최소 50개 이상의 고품질 대화 쌍 준비
- 일관된 형식과 스타일 유지
- 도메인 특화 데이터 사용 권장

### 3. 체크포인트 관리
```bash
# 체크포인트 디렉토리 구조
checkpoints/
├── model_v1/
│   ├── checkpoint-100/
│   ├── checkpoint-200/
│   └── final_model/
└── model_v2/
    └── final_model/
```

### 4. 모델 평가
학습 후 다양한 질문으로 테스트:
```bash
# 테스트 스크립트
for question in "${questions[@]}"; do
  curl -X POST "http://localhost:8000/api/chat/qlora/chat" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$question\"}"
done
```

## ⚠️ 주의사항

### 1. GPU 메모리
- 최소 8GB GPU 권장 (4bit 양자화 사용 시)
- 모델 크기에 따라 요구 사항 다름:
  - 7B 모델: 8GB GPU
  - 13B 모델: 16GB GPU
  - 70B 모델: 24GB+ GPU

### 2. 학습 시간
- 데이터셋 크기와 에폭 수에 비례
- 예상 시간:
  - 100 샘플, 3 에폭: 10-20분
  - 1000 샘플, 3 에폭: 1-2시간

### 3. 오버피팅 방지
- 너무 많은 에폭 피하기
- 다양한 데이터로 학습
- Validation set으로 모니터링

### 4. API 타임아웃
학습 중에는 응답이 오래 걸릴 수 있으므로 클라이언트 타임아웃 설정 증가:
```python
import httpx

async with httpx.AsyncClient(timeout=3600.0) as client:
    response = await client.post("http://localhost:8000/api/chat/qlora/train", ...)
```

## 🔍 트러블슈팅

### 문제: Out of Memory
**해결:**
- `per_device_train_batch_size` 줄이기
- `gradient_accumulation_steps` 늘리기
- 더 작은 `lora_r` 사용

### 문제: 학습 속도가 너무 느림
**해결:**
- `gradient_accumulation_steps` 줄이기
- `per_device_train_batch_size` 늘리기 (메모리 허용 시)
- 더 강력한 GPU 사용

### 문제: 모델 로드 실패
**해결:**
- 모델 이름 확인
- HuggingFace 토큰 설정 (비공개 모델인 경우)
- 디스크 공간 확인

## 📚 참고 자료

- [PEFT Documentation](https://huggingface.co/docs/peft)
- [QLoRA Paper](https://arxiv.org/abs/2305.14314)
- [Llama-3-Open-Ko-8B](https://huggingface.co/beomi/Llama-3-Open-Ko-8B)
- [LoRA: Low-Rank Adaptation](https://arxiv.org/abs/2106.09685)

## 🎓 다음 단계

1. **기존 RAG 시스템과 통합**: QLoRA 모델에 RAG 검색 결과를 컨텍스트로 제공
2. **모델 앙상블**: 여러 파인튜닝 모델 결과 결합
3. **자동 평가**: 학습 후 자동 품질 평가 파이프라인 구축
4. **배포 최적화**: 프로덕션 환경을 위한 추론 최적화

---

**마지막 업데이트:** 2024-12-18
**작성자:** AI Assistant
**버전:** 1.0

