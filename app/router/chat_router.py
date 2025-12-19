"""
채팅 라우터

채팅 관련 엔드포인트를 정의합니다.


😎😎 FastAPI 기준의 API 엔드포인트 계층입니다.

chat_router.py
POST /api/chat
세션 ID, 메시지 리스트 등을 받아 대화형 응답 반환.

QLoRA 파인튜닝 및 대화 엔드포인트 포함.

"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import get_chat_service
from app.services.chat_service import ChatService

# QLoRA 모델을 저장하는 전역 변수
_qlora_model = None
_qlora_tokenizer = None
_qlora_model_info = {"loaded": False, "model_name": None, "adapter_path": None}


class ChatRequest(BaseModel):
    """채팅 요청 모델"""

    message: str
    model: Optional[str] = None  # 프론트엔드 호환성을 위한 필드 (현재 미사용)


class ChatResponse(BaseModel):
    """채팅 응답 모델"""

    answer: str
    sources: List[str]
    timestamp: str
    model_info: Optional[Dict[str, Any]] = None


class QLoRALoadRequest(BaseModel):
    """QLoRA 모델 로드 요청"""

    model_name: str = "beomi/Llama-3-Open-Ko-8B"
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    target_modules: Optional[List[str]] = None


class QLoRATrainRequest(BaseModel):
    """QLoRA 학습 요청"""

    conversations: List[Dict[str, str]]
    output_dir: str = "./checkpoints/qlora"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    learning_rate: float = 2e-4


class QLoRAStatusResponse(BaseModel):
    """QLoRA 모델 상태 응답"""

    loaded: bool
    model_name: Optional[str] = None
    adapter_path: Optional[str] = None


chat_router = APIRouter(prefix="/api/chat", tags=["chat"])


@chat_router.post("/rag", response_model=ChatResponse)
async def chat_rag(
    request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)
):
    """
    RAG 채팅 엔드포인트 (Vector DB + LLM)

    지식 베이스를 검색하여 관련 문서를 찾고, LLM으로 답변을 생성합니다.
    """
    try:
        result = chat_service.chat_rag(request.message)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.post("/general", response_model=ChatResponse)
async def chat_general(
    request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)
):
    """
    일반 대화 엔드포인트 (LLM만 사용)

    지식 베이스 검색 없이 LLM만 사용하여 답변을 생성합니다.
    """
    try:
        result = chat_service.chat_general(request.message)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.post("", response_model=ChatResponse)
async def chat_legacy(
    request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)
):
    """
    레거시 엔드포인트 (RAG로 리다이렉트)

    기존 호환성을 위한 엔드포인트입니다.
    """
    return await chat_rag(request, chat_service)


# ==================== QLoRA 관련 엔드포인트 ====================


@chat_router.post("/qlora/load")
async def load_qlora_model(
    request: QLoRALoadRequest, chat_service: ChatService = Depends(get_chat_service)
):
    """
    QLoRA 모델을 로드합니다.

    새로운 모델을 학습하기 위해 베이스 모델에 LoRA 어댑터를 추가합니다.
    """
    global _qlora_model, _qlora_tokenizer, _qlora_model_info

    try:
        print(f"🔄 QLoRA 모델 로드 중: {request.model_name}")

        model, tokenizer = chat_service.load_qlora_model(
            model_name=request.model_name,
            lora_r=request.lora_r,
            lora_alpha=request.lora_alpha,
            lora_dropout=request.lora_dropout,
            target_modules=request.target_modules,
        )

        _qlora_model = model
        _qlora_tokenizer = tokenizer
        _qlora_model_info = {
            "loaded": True,
            "model_name": request.model_name,
            "adapter_path": None,
            "config": {
                "lora_r": request.lora_r,
                "lora_alpha": request.lora_alpha,
                "lora_dropout": request.lora_dropout,
            },
        }

        return {
            "status": "success",
            "message": f"QLoRA 모델 로드 완료: {request.model_name}",
            "model_info": _qlora_model_info,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 로드 실패: {str(e)}")


@chat_router.post("/qlora/load_trained")
async def load_trained_qlora_model(
    base_model_name: str,
    adapter_path: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    학습된 QLoRA 어댑터를 로드합니다.

    이미 파인튜닝이 완료된 어댑터를 베이스 모델에 로드합니다.
    """
    global _qlora_model, _qlora_tokenizer, _qlora_model_info

    try:
        print(f"🔄 학습된 QLoRA 모델 로드 중: {adapter_path}")

        model, tokenizer = chat_service.load_trained_qlora_model(
            base_model_name=base_model_name, adapter_path=adapter_path
        )

        _qlora_model = model
        _qlora_tokenizer = tokenizer
        _qlora_model_info = {
            "loaded": True,
            "model_name": base_model_name,
            "adapter_path": adapter_path,
        }

        return {
            "status": "success",
            "message": f"학습된 QLoRA 모델 로드 완료: {adapter_path}",
            "model_info": _qlora_model_info,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 로드 실패: {str(e)}")


@chat_router.get("/qlora/status", response_model=QLoRAStatusResponse)
async def get_qlora_status():
    """
    현재 로드된 QLoRA 모델의 상태를 확인합니다.
    """
    return QLoRAStatusResponse(**_qlora_model_info)


@chat_router.post("/qlora/chat", response_model=ChatResponse)
async def chat_with_qlora(
    request: ChatRequest,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.9,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    로드된 QLoRA 모델과 대화합니다.

    먼저 /qlora/load 또는 /qlora/load_trained로 모델을 로드해야 합니다.
    """
    global _qlora_model, _qlora_tokenizer

    if _qlora_model is None or _qlora_tokenizer is None:
        raise HTTPException(
            status_code=400,
            detail="QLoRA 모델이 로드되지 않았습니다. 먼저 /qlora/load를 호출하세요.",
        )

    try:
        result = chat_service.chat_with_qlora_model(
            model=_qlora_model,
            tokenizer=_qlora_tokenizer,
            message=request.message,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        return ChatResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대화 생성 실패: {str(e)}")


@chat_router.post("/qlora/train")
async def train_qlora_model(
    request: QLoRATrainRequest, chat_service: ChatService = Depends(get_chat_service)
):
    """
    QLoRA 모델을 학습합니다.

    먼저 /qlora/load로 모델을 로드한 후, 이 엔드포인트로 학습을 시작합니다.
    학습 데이터는 [{"prompt": "질문", "response": "답변"}] 형식이어야 합니다.
    """
    global _qlora_model, _qlora_tokenizer

    if _qlora_model is None or _qlora_tokenizer is None:
        raise HTTPException(
            status_code=400,
            detail="QLoRA 모델이 로드되지 않았습니다. 먼저 /qlora/load를 호출하세요.",
        )

    try:
        # 학습 데이터셋 준비
        train_dataset = chat_service.prepare_training_dataset(
            tokenizer=_qlora_tokenizer, conversations=request.conversations
        )

        # 학습 시작
        result = chat_service.train_qlora_model(
            model=_qlora_model,
            tokenizer=_qlora_tokenizer,
            train_dataset=train_dataset,
            output_dir=request.output_dir,
            num_train_epochs=request.num_train_epochs,
            per_device_train_batch_size=request.per_device_train_batch_size,
            learning_rate=request.learning_rate,
        )

        # 학습 후 모델 정보 업데이트
        _qlora_model_info["adapter_path"] = result["final_model_path"]

        return {"status": "success", "message": "QLoRA 학습 완료", "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"학습 실패: {str(e)}")


@chat_router.post("/qlora/unload")
async def unload_qlora_model():
    """
    로드된 QLoRA 모델을 언로드하여 메모리를 해제합니다.
    """
    global _qlora_model, _qlora_tokenizer, _qlora_model_info

    if _qlora_model is None:
        return {"status": "success", "message": "로드된 모델이 없습니다."}

    try:
        # 모델 메모리 해제
        del _qlora_model
        del _qlora_tokenizer
        _qlora_model = None
        _qlora_tokenizer = None
        _qlora_model_info = {"loaded": False, "model_name": None, "adapter_path": None}

        # GPU 캐시 정리
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return {"status": "success", "message": "QLoRA 모델 언로드 완료"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 언로드 실패: {str(e)}")
