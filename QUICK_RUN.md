# 🚀 LangChain RAG Chatbot - Quick Start Guide

이 프로젝트는 **OpenAI + Midm** 두 모델을 모두 지원하는 RAG 챗봇입니다.

---

## 📋 목차

1. [실행 방법](#-실행-방법)
2. [모델 선택](#-모델-선택)
3. [파일 구조](#-파일-구조)
4. [문제 해결](#-문제-해결)

---

## ⚡ 실행 방법

### 터미널 1: 백엔드 (Midm GPU + OpenAI)

**가장 간단한 방법:**

```bash
run_backend.bat  # CMD
# 또는
run_backend.ps1  # PowerShell
```

**수동 실행:**

```powershell
conda activate torch313
cd app
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000
```

> 💡 **팁**: 환경 변수는 `.env` 파일에 설정되어 있어 별도로 입력할 필요가 없습니다.

### 터미널 2: 프론트엔드

**가장 간단한 방법:**

```bash
run_frontend.bat  # CMD
# 또는
run_frontend.ps1  # PowerShell
```

**수동 실행:**

```bash
cd frontend
npm run dev
```

---

## 🤖 모델 선택

UI에서 두 모델을 선택할 수 있습니다:

### 1. 모드 선택
- **📚 Knowledge Base (RAG Mode)**: Neon PGVector DB 사용
- **💬 General (Free Chat)**: DB 없이 일반 대화

### 2. 모델 선택
- **🤖 OpenAI**: GPT-4o-mini (빠른 응답)
- **🦙 Midm**: Midm-2.0-Mini-Instruct (GPU + 4bit 양자화)

### 조합 예시
- ✅ RAG + OpenAI: 빠른 지식 베이스 검색
- ✅ RAG + Midm: GPU 로컬 모델로 지식 베이스 검색
- ✅ General + OpenAI: 빠른 일반 대화
- ✅ General + Midm: GPU 로컬 모델로 일반 대화

---

## 📁 파일 구조

```
langchain/
├── app/                    # 백엔드 (FastAPI)
│   ├── api_server.py       # 메인 서버 (OpenAI + Midm)
│   ├── models/midm/        # Midm 로컬 모델
│   └── ...
├── frontend/               # 프론트엔드 (Next.js)
│   └── src/app/page.tsx    # UI (모델 선택 버튼)
├── scripts/                # 유틸리티 스크립트
│   └── setup_pgvector_simple.py
├── strategy/               # 아키텍처 문서
├── .env                    # 환경 변수 (여기에 설정 저장) ⭐
├── run_backend.bat         # 백엔드 실행 (CMD)
├── run_backend.ps1         # 백엔드 실행 (PowerShell)
├── run_frontend.bat        # 프론트엔드 실행 (CMD)
├── run_frontend.ps1        # 프론트엔드 실행 (PowerShell)
└── requirements.txt        # Python 패키지
```

---

## 🔧 문제 해결

### 백엔드가 시작되지 않는 경우

1. **`.env` 파일 확인**:

   프로젝트 루트에 `.env` 파일이 있고 다음 항목이 포함되어 있는지 확인:
   ```env
   KMP_DUPLICATE_LIB_OK=TRUE
   MIDM_MODEL_PATH=models/midm
   OPENAI_API_KEY=your_key_here
   POSTGRES_HOST=...
   ```

2. **torch313 환경 확인**:
   ```powershell
   conda activate torch313
   python -c "import torch; print(torch.__version__)"
   ```

3. **패키지 재설치**:
   ```powershell
   pip install -r requirements.txt
   ```

### 프론트엔드 에러

```powershell
cd frontend
npm install
npm run dev
```

### 백엔드 로그 확인

시작 시 다음 메시지가 나와야 합니다:

```
🔄 [1/2] OpenAI 모델 로드 중...
✅ OpenAI 모델 로드 완료!

🔄 [2/2] Midm 모델 로드 중 (GPU + 4bit 양자화)...
   GPU: NVIDIA GeForce RTX 3050
✅ Midm 모델 로드 완료 (4bit 양자화)!

✅ RAG 시스템 초기화 완료!
   - OpenAI: ✅ 사용 가능
   - Midm: ✅ 사용 가능
```

---

## 🌐 접속

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

---

## 📝 주요 기능

### 1. 이중 모델 시스템
- OpenAI (GPT-4o-mini)
- Midm (로컬 LLM, GPU 4bit 양자화)

### 2. RAG (Retrieval-Augmented Generation)
- Neon PostgreSQL (PGVector)
- OpenAI Embeddings

### 3. 실시간 모델 전환
- UI에서 버튼 클릭으로 모델 전환
- 각 요청마다 다른 모델 사용 가능

---

## ⚙️ 환경 설정

### `.env` 파일 필수 항목

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 포함해야 합니다:

```env
# Neon PostgreSQL
POSTGRES_HOST=ep-mute-boat-a1sgw2su-pooler.ap-southeast-1.aws.neon.tech
POSTGRES_PORT=5432
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=your_password_here
POSTGRES_DB=neondb
POSTGRES_SSLMODE=require

# OpenAI (Embeddings용)
OPENAI_API_KEY=your_openai_api_key_here

# Midm 모델 설정
KMP_DUPLICATE_LIB_OK=TRUE
MIDM_MODEL_PATH=models/midm
```

> 💡 이 설정들은 한 번만 하면 됩니다. 이후로는 `run_backend.bat`만 실행하면 자동으로 로드됩니다.

---

## 🛠️ 개발 정보

- **백엔드**: FastAPI + LangChain
- **프론트엔드**: Next.js + TypeScript
- **데이터베이스**: Neon PostgreSQL (PGVector)
- **LLM 모델**: OpenAI GPT-4o-mini, Midm-2.0-Mini-Instruct
- **GPU 최적화**: 4bit 양자화 (bitsandbytes)
- **환경 관리**: python-dotenv (`.env` 파일 자동 로드)

---

생성 날짜: 2025-12-17
최종 업데이트: 2025-12-17
