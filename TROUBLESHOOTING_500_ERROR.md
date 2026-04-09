# 500 에러 해결 가이드

## 문제 원인

백엔드에서 500 에러가 발생하는 주요 원인:

1. **LLM_PROVIDER 환경 변수 미설정**
   - 기본값이 `"openai"`인데 `OPENAI_API_KEY`가 없으면 실패

2. **OPENAI_API_KEY 미설정**
   - `LLM_PROVIDER=openai`일 때 필수

## 해결 방법

### 방법 1: 로컬 MIDM 모델 사용 (권장)

```bash
# Windows PowerShell
$env:LLM_PROVIDER="local_llama"
$env:MIDM_MODEL_PATH="app/models/midm"

# Linux/Mac
export LLM_PROVIDER=local_llama
export MIDM_MODEL_PATH=app/models/midm
```

### 방법 2: OpenAI 사용

```bash
# Windows PowerShell
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="sk-your-api-key-here"

# Linux/Mac
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-your-api-key-here
```

### 방법 3: .env 파일 사용

프로젝트 루트에 `.env` 파일 생성:

```env
# 로컬 MIDM 모델 사용
LLM_PROVIDER=local_llama
MIDM_MODEL_PATH=app/models/midm

# 또는 OpenAI 사용
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-api-key-here
```

## 확인 방법

서버 재시작 후 로그 확인:

```
✅ LLM 모델: local-llama  ← 정상
✅ Embeddings 모델: ...   ← 정상
```

또는:

```
⚠️ LLM/Embeddings 초기화 실패: OPENAI_API_KEY가 설정되지 않았습니다!  ← 문제
```

## 추가 확인 사항

1. **MIDM 모델 경로 확인**
   - `app/models/midm/` 디렉토리에 모델 파일이 있는지 확인
   - `config.json`, `model.safetensors` 등 필수 파일 확인

2. **서버 재시작**
   - 환경 변수 변경 후 반드시 서버 재시작 필요

3. **에러 로그 확인**
   - 서버 콘솔에서 상세한 에러 메시지 확인
   - `❌ get_llm() 실패:` 메시지 확인
