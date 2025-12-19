# 🔄 Midm 모델로 전환하기

## 현재 상황

- **기존**: OpenAI GPT-4o-mini 사용 중
- **변경**: 로컬 Midm-2.0-Mini-Instruct 모델로 전환

## 🚀 빠른 전환 방법

### Docker 사용 중인 경우

```bash
# 1. Docker 컨테이너 재시작
docker-compose down
docker-compose up -d

# 2. 로그 확인
docker-compose logs -f langchain-app
```

### 로컬 실행 중인 경우

```bash
# 1. 환경 변수 설정
export LLM_PROVIDER=local_llama
export MIDM_MODEL_PATH=app/models/midm
export MIDM_DEVICE=cpu
export OPENAI_API_KEY=your_key  # Embeddings용

# 2. 필수 패키지 설치
pip install transformers torch langchain-huggingface accelerate

# 3. 서버 실행
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --reload
```

## ✅ 적용 확인

### 1. 서버 시작 로그 확인

```
🚀 FastAPI 서버 시작 중...
🔄 로컬 모델 로드 중: app/models/midm
✅ 모델 로드 완료: midm-2.0-mini-instruct
   디바이스: cpu
✅ LLM 모델: midm-2.0-mini-instruct
```

### 2. API 테스트

```bash
curl -X POST http://localhost:8000/api/chat/general \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요!"}'
```

### 3. 프론트엔드에서 확인

- http://localhost:3000 접속
- 채팅 메시지 전송
- 응답의 출처에 "midm" 또는 로컬 모델 표시 확인

## 📝 변경 내역

### `docker-compose.yaml`

```yaml
environment:
  LLM_PROVIDER: local_llama        # ← OpenAI에서 변경
  MIDM_MODEL_PATH: app/models/midm
  MIDM_DEVICE: cpu
```

### 서버 명령어

```yaml
command: uvicorn api_server_refactored:app --host 0.0.0.0 --port 8000 --reload
# 이전: api_server:app
```

## 🔙 OpenAI로 되돌리기

```bash
# docker-compose.yaml 수정
environment:
  LLM_PROVIDER: openai
  OPENAI_API_KEY: ${OPENAI_API_KEY}

# 재시작
docker-compose restart langchain-app
```

## ⚠️ 주의사항

1. **첫 실행 시간**: Midm 모델 로드에 30초~1분 소요
2. **메모리**: 최소 8GB RAM 필요
3. **속도**: CPU 사용 시 응답이 느릴 수 있음 (GPU 권장)
4. **Embeddings**: 벡터 검색은 여전히 OpenAI Embeddings 사용

## 🐛 문제 해결

### 모델 로드 실패

```bash
# transformers 설치 확인
pip install transformers torch langchain-huggingface

# 모델 파일 확인
ls -lh app/models/midm/
```

### 메모리 부족

```python
# 8-bit 양자화 사용
# app/models/providers/local_llama_provider.py 수정
load_in_8bit=True
```

### 너무 느림

```bash
# GPU 사용
export MIDM_DEVICE=cuda
```

## 📊 성능 비교

| 항목 | OpenAI | Midm (CPU) | Midm (GPU) |
|------|--------|------------|------------|
| 응답 속도 | 빠름 (1-2초) | 느림 (10-30초) | 보통 (3-5초) |
| 비용 | 유료 | 무료 | 무료 |
| 품질 | 매우 높음 | 보통 | 보통 |
| 인터넷 | 필요 | 불필요 | 불필요 |

