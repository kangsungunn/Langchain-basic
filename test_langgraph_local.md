# 로컬 테스트 가이드

## 1. 서버 실행

### 방법 1: uvicorn 직접 실행 (권장)
```bash
# 프로젝트 루트에서
cd app
python -m uvicorn api_server_refactored:app --host 0.0.0.0 --port 8000 --reload
```

### 방법 2: Python 스크립트로 실행
```bash
cd app
python api_server_refactored.py
```

### 방법 3: PowerShell (Windows)
```powershell
cd app
python -m uvicorn api_server_refactored:app --host 0.0.0.0 --port 8000 --reload
```

## 2. 환경 변수 설정

서버 실행 전에 필요한 환경 변수를 설정하세요:

```bash
# .env 파일 또는 환경 변수로 설정
export LLM_PROVIDER=local_llama
export MIDM_MODEL_PATH=app/models/midm
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=langchain
export POSTGRES_PASSWORD=langchain123
export POSTGRES_DB=vectordb
```

## 3. API 테스트

### 3.1 LangGraph RAG 모드 테스트
```bash
curl -X POST "http://localhost:8000/api/chat/langgraph/rag" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요! LangGraph에 대해 알려주세요."
  }'
```

### 3.2 LangGraph Tool calling 모드 테스트
```bash
curl -X POST "http://localhost:8000/api/chat/langgraph/tool" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "현재 서버 시간을 알려주세요."
  }'
```

### 3.3 LangGraph 통합 엔드포인트 (RAG 모드)
```bash
curl -X POST "http://localhost:8000/api/chat/langgraph?use_rag=true" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "RAG가 무엇인가요?"
  }'
```

### 3.4 LangGraph 통합 엔드포인트 (Tool 모드)
```bash
curl -X POST "http://localhost:8000/api/chat/langgraph?use_rag=false" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "서버 시간을 알려주세요."
  }'
```

### 3.5 기존 LangChain 엔드포인트 (비교용)
```bash
# RAG 모드
curl -X POST "http://localhost:8000/api/chat/rag" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요!"
  }'

# 일반 대화 모드
curl -X POST "http://localhost:8000/api/chat/general" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요!"
  }'
```

### 3.6 헬스체크
```bash
curl http://localhost:8000/health
```

## 4. Python 스크립트로 직접 테스트

`test_langgraph.py` 파일을 생성하여 테스트:

```python
# test_langgraph.py
import requests
import json

BASE_URL = "http://localhost:8000"

def test_langgraph_rag():
    """LangGraph RAG 모드 테스트"""
    url = f"{BASE_URL}/api/chat/langgraph/rag"
    data = {
        "message": "안녕하세요! LangGraph에 대해 알려주세요."
    }

    response = requests.post(url, json=data)
    print("=" * 60)
    print("LangGraph RAG 모드 테스트")
    print("=" * 60)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_langgraph_tool():
    """LangGraph Tool calling 모드 테스트"""
    url = f"{BASE_URL}/api/chat/langgraph/tool"
    data = {
        "message": "현재 서버 시간을 알려주세요."
    }

    response = requests.post(url, json=data)
    print("=" * 60)
    print("LangGraph Tool calling 모드 테스트")
    print("=" * 60)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_langchain_rag():
    """기존 LangChain RAG 모드 테스트 (비교용)"""
    url = f"{BASE_URL}/api/chat/rag"
    data = {
        "message": "안녕하세요!"
    }

    response = requests.post(url, json=data)
    print("=" * 60)
    print("LangChain RAG 모드 테스트 (비교용)")
    print("=" * 60)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

if __name__ == "__main__":
    print("🚀 LangGraph 테스트 시작\n")

    # 서버가 실행 중인지 확인
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code != 200:
            print("❌ 서버가 실행 중이지 않습니다. 먼저 서버를 시작하세요.")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        print("   실행 명령어: cd app && python -m uvicorn api_server_refactored:app --host 0.0.0.0 --port 8000")
        exit(1)

    # 테스트 실행
    test_langgraph_rag()
    test_langgraph_tool()
    test_langchain_rag()

    print("✅ 모든 테스트 완료!")
```

실행:
```bash
python test_langgraph.py
```

## 5. 브라우저에서 테스트

서버 실행 후 브라우저에서 접속:

- API 문서: http://localhost:8000/docs
- 대화형 API 테스트: http://localhost:8000/redoc

## 6. 예상 응답 형식

```json
{
  "answer": "답변 내용...",
  "sources": [
    "📚 출처: local-llama + Vector DB",
    "관련 문서 내용... (유사도: 0.85)"
  ],
  "timestamp": "2025-01-XX...",
  "model_info": null
}
```

## 7. 문제 해결

### 모델 로드 오류
- `MIDM_MODEL_PATH` 환경 변수가 올바른지 확인
- 모델 파일이 `app/models/midm/` 경로에 있는지 확인

### 데이터베이스 연결 오류
- PostgreSQL이 실행 중인지 확인
- 환경 변수 `POSTGRES_*` 값이 올바른지 확인

### 포트 충돌
- 다른 포트 사용: `--port 8001`
- 실행 중인 프로세스 확인: `netstat -ano | findstr :8000` (Windows)
