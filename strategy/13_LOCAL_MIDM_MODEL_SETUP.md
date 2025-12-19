# 🤖 Midm-2.0-Mini-Instruct 모델 설정 가이드

## 📋 개요

로컬 Midm-2.0-Mini-Instruct 모델을 LangChain 애플리케이션에서 사용하는 방법을 설명합니다.

## 🔧 필수 패키지 설치

```bash
pip install transformers torch langchain-huggingface accelerate
```

## 📂 모델 파일 확인

모델 파일이 `app/models/midm/` 디렉토리에 있는지 확인:

```
app/models/midm/
├── config.json
├── generation_config.json
├── model.safetensors (4.3GB)
├── tokenizer.json
├── tokenizer_config.json
└── special_tokens_map.json
```

## 🚀 사용 방법

### 방법 1: 환경 변수로 설정 (권장)

```bash
# .env 파일 또는 환경 변수
export LLM_PROVIDER=local_llama
export MIDM_MODEL_PATH=app/models/midm
export MIDM_DEVICE=auto  # 또는 cpu, cuda
export MIDM_MAX_NEW_TOKENS=512
export MIDM_TEMPERATURE=0.7

# 서버 실행
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000
```

### 방법 2: dependencies.py에서 직접 설정

`app/api/dependencies.py` 수정:

```python
from app.models.providers.local_llama_provider import LocalLlamaLLM

@lru_cache()
def get_llm() -> BaseLLM:
    # Midm 모델 로드
    return LocalLlamaLLM(
        model_path="app/models/midm",
        model_name="midm-2.0-mini-instruct",
        device="auto",
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.9,
    )
```

### 방법 3: CustomLLM으로 직접 주입

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from langchain_huggingface import HuggingFacePipeline
from app.models.providers.custom_provider import CustomLLM

@lru_cache()
def get_llm() -> BaseLLM:
    # 모델 로드
    model = AutoModelForCausalLM.from_pretrained(
        "app/models/midm",
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=True  # Mi:dm 필수
    )

    tokenizer = AutoTokenizer.from_pretrained("app/models/midm")

    # Pipeline 생성
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.7,
        do_sample=True,
    )

    # LangChain 래퍼
    hf_pipeline = HuggingFacePipeline(pipeline=pipe)

    # CustomLLM으로 래핑
    return CustomLLM(model=hf_pipeline, model_name="midm-2.0-mini")
```

## 🧪 테스트

### 1. 기본 모델 로드 테스트

```bash
python app/scripts/load_local_model.py
```

### 2. LangChain 통합 테스트

```bash
python app/scripts/test_midm_with_langchain.py
```

### 3. API 테스트

```bash
# 서버 실행
export LLM_PROVIDER=local_llama
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000

# 다른 터미널에서 테스트
curl -X POST http://localhost:8000/api/chat/general \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요!"}'
```

## 📊 모델 정보

- **모델 이름**: Midm-2.0-Mini-Instruct
- **모델 타입**: LlamaForCausalLM
- **모델 크기**: 4.3GB
- **Hidden size**: 1792
- **레이어 수**: 48
- **어텐션 헤드**: 32
- **Vocabulary size**: 131,392

## ⚙️ 환경 변수 설정

| 환경 변수 | 기본값 | 설명 |
|----------|--------|------|
| `LLM_PROVIDER` | `openai` | 모델 제공자 (`openai`, `local_llama`) |
| `MIDM_MODEL_PATH` | `app/models/midm` | Midm 모델 경로 |
| `MIDM_DEVICE` | `auto` | 디바이스 (`auto`, `cpu`, `cuda`) |
| `MIDM_MAX_NEW_TOKENS` | `512` | 최대 생성 토큰 수 |
| `MIDM_TEMPERATURE` | `0.7` | 온도 (0.0 ~ 1.0) |
| `MIDM_TOP_P` | `0.9` | Top-p 샘플링 |

## 🔄 모델 전환

### OpenAI ↔ Midm 전환

```bash
# OpenAI 사용
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Midm 사용
export LLM_PROVIDER=local_llama
export MIDM_MODEL_PATH=app/models/midm

# 서버 재시작
uvicorn app.api_server_refactored:app --reload
```

## 💡 성능 최적화

### GPU 사용

```bash
# CUDA 사용 (NVIDIA GPU)
export MIDM_DEVICE=cuda

# 특정 GPU 선택
export CUDA_VISIBLE_DEVICES=0
```

### 메모리 최적화

```python
# 8-bit 양자화 사용
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    load_in_8bit=True,  # 메모리 절약
    device_map="auto",
    trust_remote_code=True
)
```

## ⚠️ 주의사항

1. **메모리 요구사항**: 최소 8GB RAM (CPU), 4GB VRAM (GPU)
2. **trust_remote_code**: Mi:dm 모델은 반드시 `trust_remote_code=True` 필요
3. **속도**: CPU 사용 시 느릴 수 있음 (GPU 권장)
4. **첫 실행**: 모델 로드에 시간이 걸릴 수 있음 (캐싱됨)

## 📚 관련 파일

- `app/models/providers/local_llama_provider.py` - Midm 모델 로더
- `app/scripts/load_local_model.py` - 기본 로드 테스트
- `app/scripts/test_midm_with_langchain.py` - LangChain 통합 테스트
- `app/config/model_config.py` - 모델 설정 관리

## 🎯 다음 단계

1. 테스트 스크립트 실행하여 모델 로드 확인
2. 환경 변수 설정
3. 서버 실행 및 API 테스트
4. 성능 모니터링 및 최적화

