# 🖥️ 로컬 환경 설정 가이드

## 개요

Docker를 제거하고 로컬 환경에서 직접 실행하도록 전환했습니다.

## 📋 사전 요구사항

### 1. Python 3.11 이상

```bash
python --version
# Python 3.11.0 이상이어야 함
```

### 2. Node.js 18 이상

```bash
node --version
# v18.0.0 이상이어야 함
```

### 3. 필수 Python 패키지

```bash
pip install -r requirements.txt
```

## 🚀 빠른 시작

### 방법 1: 자동 시작 (권장)

**모든 서버를 한 번에 시작:**

```bash
start_all.bat
```

이 스크립트는 백엔드와 프론트엔드를 각각 별도의 터미널 창에서 자동으로 시작합니다.

### 방법 2: 수동 시작

**터미널 1 - 백엔드:**

```bash
start_backend.bat
```

**터미널 2 - 프론트엔드:**

```bash
start_frontend.bat
```

## 📁 디렉토리 구조

```
langchain/
├── app/                          # 백엔드 (FastAPI)
│   ├── api_server.py             # 메인 서버 파일
│   ├── models/
│   │   └── midm/                 # Midm 로컬 모델
│   ├── services/
│   ├── repository/
│   └── router/
├── frontend/                     # 프론트엔드 (Next.js)
│   ├── src/
│   │   └── app/
│   │       └── page.tsx
│   └── .env.local                # 프론트엔드 환경 변수
├── .env                          # 백엔드 환경 변수
├── .env.example                  # 환경 변수 예시
├── requirements.txt              # Python 의존성
├── start_backend.bat             # 백엔드 시작 스크립트
├── start_frontend.bat            # 프론트엔드 시작 스크립트
└── start_all.bat                 # 전체 시작 스크립트
```

## ⚙️ 환경 변수 설정

### `.env` (백엔드)

```env
# Neon PostgreSQL 설정
POSTGRES_HOST=ep-mute-boat-a1sgw2su-pooler.ap-southeast-1.aws.neon.tech
POSTGRES_PORT=5432
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=XXX
POSTGRES_DB=neondb
POSTGRES_SSLMODE=require

# LLM 제공자 설정
LLM_PROVIDER=local_llama
MIDM_MODEL_PATH=app/models/midm
MIDM_DEVICE=cpu

# OpenAI API 설정 (Embeddings용)
OPENAI_API_KEY=your_openai_api_key_here

# Embeddings 제공자
EMBEDDINGS_PROVIDER=openai
```

### `frontend/.env.local` (프론트엔드)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🔧 상세 실행 방법

### 백엔드 (FastAPI + Midm)

1. **app 디렉토리로 이동:**

```bash
cd app
```

2. **환경 변수 확인:**

`.env` 파일이 프로젝트 루트에 있어야 합니다.

3. **서버 시작:**

```bash
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

4. **확인:**

- API: http://localhost:8000
- API 문서: http://localhost:8000/docs
- 헬스 체크: http://localhost:8000/health

### 프론트엔드 (Next.js)

1. **frontend 디렉토리로 이동:**

```bash
cd frontend
```

2. **패키지 설치 (최초 1회):**

```bash
npm install
```

3. **개발 서버 시작:**

```bash
npm run dev
```

4. **확인:**

http://localhost:3000

## 🧪 테스트

### API 테스트

```bash
# 헬스 체크
curl http://localhost:8000/health

# 일반 채팅 (Midm 모델)
curl -X POST http://localhost:8000/api/chat/general \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"안녕하세요!\"}"
```

### 프론트엔드 테스트

1. 브라우저에서 http://localhost:3000 접속
2. "General" 모드 선택
3. "안녕하세요!" 입력
4. Midm 모델 응답 확인 (1~2분 소요)

## ⚠️ 주의사항

### 1. Midm 모델 응답 시간

- **첫 번째 응답**: 30초 ~ 2분
- **이후 응답**: 30초 ~ 1분
- CPU에서 실행되므로 느립니다

### 2. 메모리 사용량

- Midm 모델: 약 4~8GB RAM
- 최소 권장 RAM: 8GB

### 3. 포트 충돌

기본 포트가 이미 사용 중이라면:

**백엔드 (8000 → 8001):**

```bash
cd app
python -m uvicorn api_server:app --host 0.0.0.0 --port 8001 --reload
```

**프론트엔드 환경 변수 업데이트:**

```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
```

### 4. 환경 변수 로드

Python이 `.env` 파일을 자동으로 로드하려면 `python-dotenv`가 설치되어 있어야 합니다:

```bash
pip install python-dotenv
```

## 🐛 문제 해결

### "ModuleNotFoundError" 발생 시

```bash
# 프로젝트 루트에서 실행
pip install -r requirements.txt
```

### "Port already in use" 발생 시

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# 또는 다른 포트 사용
python -m uvicorn api_server:app --port 8001
```

### Midm 모델 로드 실패 시

```bash
# 모델 파일 확인
dir app\models\midm

# 필수 파일:
# - config.json
# - model.safetensors (4.3GB)
# - tokenizer.json
# - generation_config.json
```

### 프론트엔드 빌드 오류 시

```bash
cd frontend

# node_modules 삭제 및 재설치
rmdir /s /q node_modules
npm install

# 캐시 정리
npm cache clean --force
npm install
```

## 📊 성능 모니터링

### 백엔드 로그 확인

터미널에서 실시간으로 로그를 확인할 수 있습니다:

```
🚀 FastAPI 서버 시작 중...
🔗 Neon PostgreSQL에 연결 중...
   호스트: ep-mute-boat-a1sgw2su-pooler.ap-southeast-1.aws.neon.tech
   데이터베이스: neondb
✅ Neon PostgreSQL 연결 완료!
🔄 로컬 Midm 모델 로드 중...
   모델 경로: app/models/midm
✅ 모델과 토크나이저 로드 완료!
✅ Midm 모델 로드 완료!
✅ RAG 시스템 초기화 완료!
✅ 서버 준비 완료!
```

### 메모리 사용량 확인

```bash
# Windows 작업 관리자
Ctrl + Shift + Esc

# Python 프로세스 확인
```

## 🎯 다음 단계

1. **지식 베이스 구축:**

```bash
cd app
python build_knowledge_base.py
```

2. **RAG 모드 테스트:**

프론트엔드에서 "Knowledge Base" 모드를 선택하여 문서 기반 질문 테스트

3. **성능 최적화:**

- GPU 사용 고려 (CUDA 설치 필요)
- 양자화된 모델 사용
- 더 작은 모델로 교체

## 🔄 Docker로 되돌리기

Docker 환경으로 되돌리려면:

1. `docker-compose.yaml` 복원
2. `Dockerfile` 복원
3. `docker-compose up -d` 실행

## 📞 도움말

문제가 계속되면:

1. 로그 확인 (터미널 출력)
2. 환경 변수 확인 (`.env` 파일)
3. 패키지 버전 확인 (`pip list`)
4. Python/Node.js 버전 확인

---

**로컬 환경 설정 완료!** 🎉

이제 `start_all.bat`을 실행하여 챗봇을 시작하세요.

