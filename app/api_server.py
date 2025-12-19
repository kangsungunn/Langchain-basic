"""
FastAPI 서버 - RAG 챗봇 API

웹 UI와 통신하기 위한 REST API 서버입니다.

FastAPI 기반 RAG 백엔드 서버.

FastAPI 앱의 엔트리 포인트.
하는 일:
FastAPI 인스턴스 생성.
router/ 안의 라우터들 include.
CORS, 미들웨어, 로깅, 예외 핸들러 설정.
앱 시작 시점에:
LLM/벡터스토어/필요한 리소스들을 미리 로드(옵션),
또는 DI 컨테이너 초기화.
역할: 이 프로젝트의 “메인 실행 파일”이자 API 서버의 부팅 스크립트.

이 모듈은 순수하게 API 서버 역할만 수행하며,
Next.js 프론트엔드(`frontend/`)와는 HTTP 요청/응답으로만 통신합니다.

"""

import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv

# .env 파일 로드 (루트 디렉토리에서)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from pydantic import BaseModel


# Pydantic 모델
class ChatRequest(BaseModel):
    """채팅 요청 모델"""

    message: str
    model: str = "openai"  # "openai" 또는 "midm"
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """채팅 응답 모델"""

    answer: str
    sources: List[str]
    timestamp: str


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""

    status: str
    message: str


# FastAPI 앱 초기화
app = FastAPI(
    title="LangChain RAG Chatbot API",
    description="RAG를 사용한 지능형 챗봇 API",
    version="1.0.0",
)

# CORS 설정 (웹 브라우저에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
vector_store = None
openai_model = None
midm_model = None
embeddings = None


def initialize_rag_system():
    """RAG 시스템을 초기화합니다 (OpenAI + Midm 모두 로드)."""
    global vector_store, openai_model, midm_model, embeddings

    # Embeddings 초기화 (OpenAI 사용)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY가 없습니다. Embeddings를 위해 필요합니다.")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)

    # Neon PGVector 초기화
    db_user = os.getenv("POSTGRES_USER", "neondb_owner")
    db_password = os.getenv("POSTGRES_PASSWORD", "npg_VhUdLOR8F7MQ")
    db_host = os.getenv(
        "POSTGRES_HOST", "ep-mute-boat-a1sgw2su-pooler.ap-southeast-1.aws.neon.tech"
    )
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "neondb")
    db_sslmode = os.getenv("POSTGRES_SSLMODE", "require")

    # Neon PostgreSQL은 SSL이 필수입니다
    connection_string = (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}?sslmode={db_sslmode}"
    )

    print("🔗 Neon PostgreSQL에 연결 중...")
    print(f"   호스트: {db_host}")
    print(f"   데이터베이스: {db_name}")

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name="langchain_knowledge_base",
        connection=connection_string,
        use_jsonb=True,
    )

    print("✅ Neon PostgreSQL 연결 완료!")

    # 1. OpenAI 모델 로드 (항상 로드)
    print("\n🔄 [1/2] OpenAI 모델 로드 중...")
    openai_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=api_key)
    print("✅ OpenAI 모델 로드 완료!")

    # 2. Midm 모델 로드 (항상 로드)
    print("\n🔄 [2/2] Midm 모델 로드 중 (GPU + 4bit 양자화)...")
    try:
        import torch
        from langchain_huggingface import HuggingFacePipeline
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            pipeline,
        )

        model_path = os.getenv("MIDM_MODEL_PATH", "models/midm")
        print(f"   모델 경로: {model_path}")

        # GPU 확인
        if torch.cuda.is_available():
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
            print(f"   CUDA 버전: {torch.version.cuda}")
        else:
            print("   ⚠️  GPU를 찾을 수 없습니다. CPU 모드로 실행됩니다.")

        # 4bit 양자화 설정
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        print("   4bit 양자화 설정 완료")

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True,
            low_cpu_mem_usage=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            model_path, trust_remote_code=True, local_files_only=True
        )

        print("✅ 모델과 토크나이저 로드 완료!")

        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=256,
            temperature=0.7,
            do_sample=True,
            repetition_penalty=1.1,
        )

        midm_model = HuggingFacePipeline(pipeline=pipe)
        print("✅ Midm 모델 로드 완료 (4bit 양자화)!")

    except Exception as e:
        print(f"❌ Midm 모델 로드 실패: {e}")
        import traceback

        traceback.print_exc()
        print("⚠️  Midm은 사용할 수 없습니다. OpenAI만 사용 가능합니다.")
        midm_model = None

    print("\n✅ RAG 시스템 초기화 완료!")
    print(f"   - OpenAI: {'✅ 사용 가능' if openai_model else '❌ 사용 불가'}")
    print(f"   - Midm: {'✅ 사용 가능' if midm_model else '❌ 사용 불가'}")


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    print("🚀 FastAPI 서버 시작 중...")
    initialize_rag_system()
    print("✅ 서버 준비 완료!")


def create_rag_prompt():
    """RAG용 프롬프트 템플릿을 생성합니다 (PGVector 문서 기반)."""
    template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content="다음 문서 내용을 바탕으로 질문에 답하세요."),
            (
                "human",
                """참고 문서:
{context}

{question}""",
            ),
        ]
    )

    return template


def clean_answer(answer) -> str:
    """답변에서 불필요한 메타 정보를 제거합니다."""
    # 먼저 문자열로 변환
    if not isinstance(answer, str):
        answer = str(answer)

    # 제거할 패턴들 (더 많이 추가)
    patterns = [
        "System:",
        "시스템:",
        "Human:",
        "Answer:",
        "답변:",
        "질문:",
        "질문에 자연스럽게 답변하세요.",
        "질문에 답변하세요.",
        "다음 문서 내용을 바탕으로 질문에 답하세요.",
        "참고 문서:",
        "H:",
        "A:",
    ]

    result = answer.strip()

    # 프롬프트 텍스트가 포함된 경우 제거
    prompt_indicators = [
        "질문에 자연스럽게 답변하세요",
        "질문에 답변하세요",
        "다음 문서 내용을 바탕으로",
        "RAG가 뭐고 어떻게 작동해?",  # 질문 자체도 제거
    ]

    # 프롬프트가 답변에 포함되어 있으면, 실제 답변 부분만 추출
    for indicator in prompt_indicators:
        if indicator in result:
            parts = result.split(indicator, 1)
            if len(parts) > 1:
                result = parts[1].strip()

    # 각 줄에서 패턴을 찾아서 제거 (라인은 유지)
    lines = result.split("\n")
    cleaned_lines = []

    for line in lines:
        cleaned_line = line.strip()

        # 완전히 패턴으로만 이루어진 라인은 건너뛰기
        skip_line = False
        for pattern in patterns:
            if cleaned_line == pattern.rstrip(":").rstrip("?").rstrip("."):
                skip_line = True
                break

        if skip_line:
            continue

        # 라인 시작 부분의 패턴만 제거
        for pattern in patterns:
            if cleaned_line.startswith(pattern):
                cleaned_line = cleaned_line[len(pattern) :].strip()
                break

        # 빈 줄이 아니면 추가
        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    result = "\n".join(cleaned_lines)

    return result


@app.get("/")
async def root():
    """API 루트 엔드포인트 - API 정보 반환"""
    return {
        "name": "LangChain RAG Chatbot API",
        "version": "1.0.0",
        "description": "RAG를 사용한 지능형 챗봇 API",
        "endpoints": {
            "health": "/health",
            "chat_rag": "/api/chat/rag",
            "chat_general": "/api/chat/general",
            "chat_legacy": "/api/chat",
        },
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    return HealthResponse(status="healthy", message="RAG Chatbot API is running")


@app.post("/api/chat/rag", response_model=ChatResponse)
async def chat_rag(request: ChatRequest):
    """RAG 채팅 엔드포인트 (PGVector + OpenAI/Midm)"""
    try:
        # 모델 선택
        if request.model == "midm":
            if midm_model is None:
                raise HTTPException(
                    status_code=503, detail="Midm 모델을 사용할 수 없습니다."
                )
            selected_model = midm_model
            model_name = "Midm-2.0-Mini-Instruct"
        else:  # "openai"
            if openai_model is None:
                raise HTTPException(
                    status_code=503, detail="OpenAI 모델을 사용할 수 없습니다."
                )
            selected_model = openai_model
            model_name = "OpenAI GPT-4o-mini"

        print(f"🤖 사용 모델: {model_name}")

        # 관련 문서 검색 (유사도 점수 포함)
        docs_with_scores = vector_store.similarity_search_with_score(
            request.message, k=3
        )

        # 유사도 임계값 (0.0 ~ 1.0, 낮을수록 유사함 - cosine distance 기준)
        # pgvector는 cosine distance를 사용하므로 낮을수록 관련성이 높음
        SIMILARITY_THRESHOLD = 0.5  # 0.5 이하면 관련성 있다고 판단

        # 관련성 있는 문서만 필터링
        relevant_docs = [
            (doc, score)
            for doc, score in docs_with_scores
            if score <= SIMILARITY_THRESHOLD
        ]

        if not relevant_docs:
            # PGVector에 관련 문서가 없으면 일반 대화 모드
            general_prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content="질문에 자연스럽게 답변하세요."),
                    ("human", "{question}"),
                ]
            )

            prompt = general_prompt.format_messages(question=request.message)
            response = selected_model.invoke(prompt)

            # HuggingFacePipeline은 문자열을 반환하고, ChatOpenAI는 객체를 반환
            if isinstance(response, str):
                answer = response
            else:
                answer = response.content

            # 불필요한 메타 정보 제거
            answer = clean_answer(answer)

            return ChatResponse(
                answer=answer,
                sources=[f"💬 출처: {model_name} (지식 베이스에 관련 문서 없음)"],
                timestamp=datetime.now().isoformat(),
            )

        # PGVector에서 관련 문서를 찾았으면 RAG 사용
        docs = [doc for doc, score in relevant_docs]

        # 문서 내용을 컨텍스트로 결합
        context = "\n\n---\n\n".join([doc.page_content for doc in docs])

        # 프롬프트 생성
        prompt_template = create_rag_prompt()
        prompt = prompt_template.format_messages(
            context=context, question=request.message
        )

        # LLM으로 답변 생성
        response = selected_model.invoke(prompt)

        # HuggingFacePipeline은 문자열을 반환하고, ChatOpenAI는 객체를 반환
        if isinstance(response, str):
            answer = response
        else:
            answer = response.content

        # 불필요한 메타 정보 제거
        answer = clean_answer(answer)

        # 진짜 출처 표시: PGVector에서 문서를 찾았으므로 둘 다 사용
        sources = [f"📚 출처: Neon PGVector DB + {model_name}"]
        for doc, score in relevant_docs:
            preview = doc.page_content[:80].replace("\n", " ").strip()
            if len(doc.page_content) > 80:
                preview += "..."
            sources.append(f"{preview} (유사도: {1 - score:.2f})")

        return ChatResponse(
            answer=answer, sources=sources, timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/general", response_model=ChatResponse)
async def chat_general(request: ChatRequest):
    """일반 대화 엔드포인트 (OpenAI/Midm 선택, DB 검색 없음)"""
    try:
        # 모델 선택
        if request.model == "midm":
            if midm_model is None:
                raise HTTPException(
                    status_code=503, detail="Midm 모델을 사용할 수 없습니다."
                )
            selected_model = midm_model
            model_name = "Midm-2.0-Mini-Instruct"
        else:  # "openai"
            if openai_model is None:
                raise HTTPException(
                    status_code=503, detail="OpenAI 모델을 사용할 수 없습니다."
                )
            selected_model = openai_model
            model_name = "OpenAI GPT-4o-mini"

        print(f"🤖 사용 모델: {model_name}")

        # 일반 대화용 프롬프트
        general_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content="질문에 자연스럽게 답변하세요."),
                ("human", "{question}"),
            ]
        )

        prompt = general_prompt.format_messages(question=request.message)

        # LLM으로 답변 생성 (DB 검색 없이)
        response = selected_model.invoke(prompt)

        # HuggingFacePipeline은 문자열을 반환하고, ChatOpenAI는 객체를 반환
        if isinstance(response, str):
            answer = response
        else:
            answer = response.content

        # 불필요한 메타 정보 제거
        answer = clean_answer(answer)

        return ChatResponse(
            answer=answer,
            sources=[f"💬 출처: {model_name} (일반 대화 모드)"],
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat_legacy(request: ChatRequest):
    """기존 호환성을 위한 엔드포인트 (RAG로 리다이렉트)"""
    return await chat_rag(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
