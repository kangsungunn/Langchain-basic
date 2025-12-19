# 🔧 Midm 모델 연결 문제 해결

## 문제 상황

- **증상**: localhost:3000에서 "Failed to fetch" 오류
- **원인**: 백엔드 서버가 제대로 시작되지 않음

## 🔍 진단 과정

### 1. Docker 컨테이너 상태 확인

```bash
docker-compose ps
```

모든 컨테이너가 `Up` 상태여야 합니다.

### 2. 백엔드 로그 확인

```bash
docker-compose logs langchain-app
```

**정상 로그**:
```
INFO:     Application startup complete.
🚀 FastAPI 서버 시작 중...
🔄 로컬 Midm 모델 로드 중...
✅ Midm 모델 로드 완료!
✅ RAG 시스템 초기화 완료!
✅ 서버 준비 완료!
```

### 3. API 엔드포인트 테스트

```bash
# PowerShell
Invoke-WebRequest -Uri http://localhost:8000/health -Method GET

# CMD or Git Bash
curl http://localhost:8000/health
```

## ✅ 해결 방법

### 수정 사항

1. **`api_server.py` 수정**: Midm 모델 로드 로직 추가
2. **`docker-compose.yaml` 수정**: 환경 변수 및 명령어 수정

### 완전 재시작

```bash
# 1. 모든 컨테이너 중지 및 제거
docker-compose down

# 2. 다시 시작
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f langchain-app
```

## 🧪 테스트 방법

### 1. 헬스 체크

```bash
# PowerShell
Invoke-WebRequest -Uri http://localhost:8000/health

# 예상 응답
{
  "status": "healthy",
  "message": "RAG Chatbot API is running"
}
```

### 2. 채팅 API 테스트

```bash
# PowerShell
$body = @{
    message = "안녕하세요!"
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:8000/api/chat/general `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

### 3. 프론트엔드 테스트

1. http://localhost:3000 접속
2. 메시지 입력: "안녕하세요!"
3. 응답 확인

## 📊 현재 설정

### `docker-compose.yaml`

```yaml
langchain-app:
  environment:
    LLM_PROVIDER: local_llama
    MIDM_MODEL_PATH: app/models/midm
    MIDM_DEVICE: cpu
    OPENAI_API_KEY: ${OPENAI_API_KEY}  # Embeddings용
  command: uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### `api_server.py`

```python
def initialize_rag_system():
    llm_provider = os.getenv("LLM_PROVIDER", "openai")

    if llm_provider == "local_llama":
        # Midm 모델 로드
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        from langchain_huggingface import HuggingFacePipeline

        model = AutoModelForCausalLM.from_pretrained(
            "app/models/midm",
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True
        )
        # ...
```

## ⚠️ 주의사항

### 1. 첫 실행 시간

Midm 모델 로드에 **30초~2분** 소요됩니다.

```bash
# 로그 실시간 확인
docker-compose logs -f langchain-app
```

### 2. 메모리 부족

최소 **8GB RAM** 필요합니다.

```bash
# Docker 메모리 설정 확인
docker stats langchain-app
```

### 3. 필수 패키지

Docker 이미지에 다음 패키지가 설치되어 있어야 합니다:
- `transformers`
- `torch`
- `langchain-huggingface`
- `accelerate`

### 4. 모델 파일 확인

```bash
# 컨테이너 내부 확인
docker exec -it langchain-app ls -lh app/models/midm/

# 필수 파일
# - config.json
# - model.safetensors (4.3GB)
# - tokenizer.json
```

## 🐛 일반적인 오류

### "Failed to fetch"

**원인**: 백엔드 서버가 시작되지 않음

**해결**:
```bash
docker-compose logs langchain-app
# 오류 메시지 확인 후 해당 문제 해결
```

### "ModuleNotFoundError: No module named 'app'"

**원인**: `api_server_refactored.py` 사용 시 발생

**해결**:
```yaml
# docker-compose.yaml
command: uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### "OPENAI_API_KEY가 설정되지 않았습니다"

**원인**: Embeddings용 OpenAI API 키 필요

**해결**:
```bash
# .env 파일 생성
OPENAI_API_KEY=your_key_here
```

### 모델 로드 실패

**원인**: 메모리 부족 또는 패키지 누락

**해결**:
```bash
# 메모리 확인
docker stats

# 패키지 설치 확인
docker exec -it langchain-app pip list | grep transformers
```

## 📝 체크리스트

- [ ] Docker 컨테이너 모두 `Up` 상태
- [ ] `docker-compose.yaml`에 `LLM_PROVIDER=local_llama` 설정
- [ ] `api_server.py`에 Midm 로드 로직 추가
- [ ] 모델 파일 존재 확인 (`app/models/midm/`)
- [ ] 헬스 체크 API 응답 확인
- [ ] 프론트엔드에서 채팅 테스트

## 🎯 다음 단계

1. 로그에서 "✅ Midm 모델 로드 완료!" 확인
2. API 테스트로 응답 확인
3. 프론트엔드에서 실제 채팅 테스트
4. 응답 속도 및 품질 평가

