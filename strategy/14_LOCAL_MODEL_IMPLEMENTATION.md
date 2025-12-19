# 🛠️ 로컬 Llama 모델 구현 가이드

## 📋 목차

1. [환경 설정](#환경-설정)
2. [방법 1: HuggingFace Transformers 사용](#방법-1-huggingface-transformers-사용)
3. [방법 2: llama.cpp 사용 (권장)](#방법-2-llamacpp-사용-권장)
4. [의존성 주입](#의존성-주입)
5. [환경 변수 설정](#환경-변수-설정)

---

## 환경 설정

### 필수 패키지 설치

```bash
# HuggingFace Transformers 사용 시
pip install transformers torch langchain-huggingface accelerate

# llama.cpp 사용 시 (더 빠름, 메모리 효율적)
pip install llama-cpp-python langchain-community
```

---

## 방법 1: HuggingFace Transformers 사용

### Step 1: `app/api/dependencies.py` 수정

```python
from functools import lru_cache
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from langchain_huggingface import HuggingFacePipeline

from app.models.providers.custom_provider import CustomLLM
from app.models.base import BaseLLM

@lru_cache()
def get_llm() -> BaseLLM:
    """로컬 Llama 모델을 로드합니다."""

    # 1. 모델과 토크나이저 로드
    model_path = "app/models/midm"

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",  # GPU 자동 할당
        torch_dtype="auto",  # 자동 타입 선택
        low_cpu_mem_usage=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_path)

    # 2. Pipeline 생성
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.7,
        do_sample=True,
    )

    # 3. LangChain 래퍼로 변환
    hf_pipeline = HuggingFacePipeline(pipeline=pipe)

    # 4. CustomLLM으로 래핑하여 반환
    return CustomLLM(
        model=hf_pipeline,
        model_name="local-llama-1.2b"
    )
```

### Step 2: 서버 실행

```bash
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --reload
```

---

## 방법 2: llama.cpp 사용 (권장)

### Step 1: 모델을 GGUF 형식으로 변환 (필요 시)

```bash
# safetensors → GGUF 변환
pip install llama-cpp-python

# 변환 스크립트 (HuggingFace에서 제공)
python convert-hf-to-gguf.py --outfile model.gguf app/models/midm/
```

### Step 2: `app/api/dependencies.py` 수정

```python
from functools import lru_cache
from langchain_community.llms import LlamaCpp
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler

from app.models.providers.custom_provider import CustomLLM
from app.models.base import BaseLLM

@lru_cache()
def get_llm() -> BaseLLM:
    """로컬 Llama 모델을 llama.cpp로 로드합니다."""

    # Callback 설정 (스트리밍 출력)
    callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])

    # llama.cpp로 모델 로드
    llm = LlamaCpp(
        model_path="app/models/midm/model.gguf",  # GGUF 형식
        temperature=0.7,
        max_tokens=512,
        n_ctx=2048,  # 컨텍스트 길이
        callback_manager=callback_manager,
        verbose=False,
        n_gpu_layers=0,  # CPU 사용 (GPU 사용 시 값 증가)
    )

    return CustomLLM(
        model=llm,
        model_name="local-llama-cpp"
    )
```

---

## 의존성 주입

### 환경 변수로 모델 전환

```python
# app/api/dependencies.py
import os
from functools import lru_cache

@lru_cache()
def get_llm() -> BaseLLM:
    provider = os.getenv("LLM_PROVIDER", "openai")

    if provider == "local_llama":
        # 로컬 Llama 모델 로드
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        from langchain_huggingface import HuggingFacePipeline

        model_path = os.getenv("LOCAL_MODEL_PATH", "app/models/midm")

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype="auto",
        )
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
        )

        hf_pipeline = HuggingFacePipeline(pipeline=pipe)

        return CustomLLM(model=hf_pipeline, model_name="local-llama")

    elif provider == "openai":
        # OpenAI 모델 사용
        from app.models.factory import ModelFactory
        return ModelFactory.create_llm()

    else:
        raise ValueError(f"지원하지 않는 LLM 제공자: {provider}")
```

---

## 환경 변수 설정

### `.env` 파일

```bash
# OpenAI 사용 (기본)
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_api_key_here

# 로컬 Llama 모델 사용
LLM_PROVIDER=local_llama
LOCAL_MODEL_PATH=app/models/midm
LOCAL_MODEL_DEVICE=cpu  # 또는 cuda

# Embeddings (OpenAI 사용)
EMBEDDINGS_PROVIDER=openai
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small
```

---

## 🚀 실행 예시

### OpenAI 사용

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000
```

### 로컬 Llama 모델 사용

```bash
export LLM_PROVIDER=local_llama
export LOCAL_MODEL_PATH=app/models/midm

uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000
```

---

## 📝 테스트

```python
# test_local_model.py
import requests

response = requests.post(
    "http://localhost:8000/api/chat/general",
    json={"message": "안녕하세요!"}
)

print(response.json())
```

---

## ⚠️ 주의사항

1. **메모리**: Llama 모델은 최소 8GB RAM 필요 (1.2B 모델 기준)
2. **속도**: CPU 사용 시 느릴 수 있음. GPU 권장
3. **GGUF 변환**: llama.cpp 사용 시 모델을 GGUF 형식으로 변환해야 함
4. **의존성**: `transformers`, `torch`, `langchain-huggingface` 설치 필요

---

## 🎯 권장 사항

- **개발/테스트**: OpenAI 사용 (빠르고 안정적)
- **프로덕션 (비용 절감)**: 로컬 Llama 모델 + llama.cpp
- **프로덕션 (성능 중요)**: OpenAI 또는 GPU 서버에 로컬 모델

