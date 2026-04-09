# 특허 심사 API 가이드

## 개요

특허 심사 시스템은 **규칙기반**과 **정책기반** 두 가지 방식의 심사를 제공합니다.

- **규칙기반 심사**: 특정 특허법 조문을 기준으로 명세서를 검토
- **정책기반 심사**: LangGraph 에이전트를 사용한 복잡한 정책 분석

## 아키텍처

```
┌─────────────────────────────────────────────┐
│   examination_router.py                     │  ← 요청 수신
│   (FastAPI Router)                          │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│   examination_flow.py                       │  ← 모델 로드 & 분기
│   (Orchestrator)                            │
│   - 모델: artifacts/models/finetuned/patent │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌────────────────┐   ┌────────────────┐
│ 규칙기반       │   │ 정책기반       │
│ (Rule-based)   │   │ (Policy-based) │
│                │   │                │
│ examination_   │   │ examination_   │
│ service.py     │   │ agent.py       │
│                │   │                │
│ - 조문 검토    │   │ - LangGraph    │
│ - 규칙 판단    │   │ - 정책 추론    │
└────────────────┘   └────────────────┘
```

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r app/requirements.txt
```

### 2. 모델 학습 (최초 1회)

```bash
# 특허 모델 학습
python training/examination/patent/train.py

# 출력: artifacts/models/finetuned/patent/final/
```

### 3. FastAPI 서버 실행

```bash
uvicorn app.main:app --reload
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 4. API 문서 확인

브라우저에서 다음 URL로 접속:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 엔드포인트

### 특허 심사 실행

```bash
POST /admin/examination/examine
```

## 사용 예시

### 규칙기반 심사

특정 특허법 조문을 기준으로 명세서를 검토합니다.

**요청:**
```bash
curl -X POST "http://localhost:8000/admin/examination/examine" \
  -H "Content-Type: application/json" \
  -d '{
    "examination_type": "rule_based",
    "patent_text": "본 발명은 인공지능을 이용한 이미지 인식 시스템에 관한 것이다. 종래의 이미지 인식 시스템은 정확도가 낮았으나, 본 발명은 딥러닝 모델을 활용하여 95% 이상의 정확도를 달성한다.",
    "article_number": "제29조"
  }'
```

**응답 예시:**
```json
{
  "success": true,
  "examination_type": "rule_based",
  "result": {
    "method": "rule_based",
    "article_number": "제29조",
    "article_content": "특허를 받을 수 있는 발명 (신규성)",
    "decision": "등록 가능",
    "prediction": 1,
    "confidence": 0.8945,
    "analysis": "본 특허 출원은 제29조 (특허를 받을 수 있는 발명 (신규성))의 요건을 충족하는 것으로 판단됩니다. (신뢰도: 89.45%)",
    "patent_excerpt": "본 발명은 인공지능을 이용한 이미지 인식 시스템..."
  },
  "message": "심사가 성공적으로 완료되었습니다."
}
```

### 정책기반 심사

LangGraph 에이전트를 사용하여 복잡한 정책 분석을 수행합니다.

**요청:**
```bash
curl -X POST "http://localhost:8000/admin/examination/examine" \
  -H "Content-Type: application/json" \
  -d '{
    "examination_type": "policy_based",
    "patent_text": "본 발명은 블록체인 기반 전자계약 시스템에 관한 것이다. 기존 기술은 중앙화된 서버에 의존하여 보안이 취약했으나, 본 발명은 분산 원장 기술을 활용하여 높은 보안성을 제공한다.",
    "query": "이 발명이 진보성을 갖는가?"
  }'
```

**응답 예시:**
```json
{
  "success": true,
  "examination_type": "policy_based",
  "result": {
    "method": "policy_based",
    "query": "이 발명이 진보성을 갖는가?",
    "decision": "등록 가능",
    "prediction": 1,
    "confidence": 0.9124,
    "reasoning": "질의: '이 발명이 진보성을 갖는가?' 에 대한 분석 결과, 긍정적 판단 (신뢰도: 91.24%)",
    "decision_detail": "특허 요건을 충족하는 것으로 판단됩니다.",
    "patent_excerpt": "본 발명은 블록체인 기반 전자계약 시스템...",
    "workflow_steps": [
      "특허 분석 완료",
      "정책 추론 완료",
      "최종 결정: 등록 가능"
    ]
  },
  "message": "심사가 성공적으로 완료되었습니다."
}
```

## Python 테스트 스크립트

```bash
# 테스트 스크립트 실행
python test_examination_api.py
```

또는 Python 코드로 직접 호출:

```python
import requests
import json

# 규칙기반 심사
response = requests.post(
    "http://localhost:8000/admin/examination/examine",
    json={
        "examination_type": "rule_based",
        "patent_text": "특허 명세서 내용...",
        "article_number": "제29조"
    }
)

result = response.json()
print(json.dumps(result, indent=2, ensure_ascii=False))
```

## 에러 처리

### 400 Bad Request - 입력 검증 오류

**규칙기반 심사에 article_number가 없는 경우:**
```json
{
  "detail": "규칙기반 심사에는 article_number가 필요합니다."
}
```

**정책기반 심사에 query가 없는 경우:**
```json
{
  "detail": "정책기반 심사에는 query가 필요합니다."
}
```

### 500 Internal Server Error - 모델 로드 실패

```json
{
  "detail": "심사 중 오류가 발생했습니다: 모델이 로드되지 않았습니다."
}
```

**해결 방법:**
1. 모델을 먼저 학습하세요: `python training/examination/patent/train.py`
2. 모델 경로를 확인하세요: `artifacts/models/finetuned/patent/final/`

## 주요 파일

```
app/
├── main.py                                   # FastAPI 앱
├── api/
│   └── admin/
│       └── examination_router.py             # 라우터 (요청 수신)
└── domain/
    └── admin/
        ├── orchestrators/
        │   └── examination_flow.py           # 오케스트레이터 (모델 로드 & 분기)
        ├── services/
        │   └── examination_service.py        # 규칙기반 서비스
        └── agents/
            └── examination_agent.py          # 정책기반 에이전트

training/
└── examination/
    └── patent/
        └── train.py                          # 모델 학습

test_examination_api.py                       # API 테스트 스크립트
```

## 확장 가이드

### 1. 새로운 조문 추가

`examination_service.py`의 `_get_article_content()` 메서드를 수정:

```python
article_db = {
    "제29조": "특허를 받을 수 있는 발명 (신규성)",
    "제30조": "공지예외 (신규성 상실의 예외)",
    "제42조": "특허출원서의 기재사항 (명세서 작성 요건)",
    "새조문": "새로운 조문 내용",  # 추가
}
```

### 2. 정책기반 워크플로우 커스터마이징

`examination_agent.py`의 `_build_graph()` 메서드에서 노드 추가/수정:

```python
workflow.add_node("새노드", self._new_node)
workflow.add_edge("analyze", "새노드")
workflow.add_edge("새노드", "reason")
```

### 3. 데이터베이스 연동

현재는 메모리 기반 조문 데이터를 사용하지만, 실제 환경에서는 데이터베이스 연동:

```python
from sqlalchemy import text

def _get_article_content(self, article_number: str) -> str:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT content FROM patent_law WHERE article_number = :num"),
            {"num": article_number}
        )
        row = result.fetchone()
        return row[0] if row else "조문을 찾을 수 없습니다."
```

## 트러블슈팅

### 문제: 모델이 로드되지 않음

```
⚠️ 모델 경로가 존재하지 않습니다: artifacts/models/finetuned/patent/final
```

**해결:**
```bash
python training/examination/patent/train.py
```

### 문제: CUDA out of memory

**해결:** CPU로 전환하거나 배치 크기 줄이기
```python
# examination_flow.py에서
self.device = "cpu"  # 강제 CPU 사용
```

### 문제: ImportError

**해결:** 의존성 재설치
```bash
pip install -r app/requirements.txt
```

## 성능 최적화

1. **모델 양자화**: 4bit/8bit quantization으로 메모리 사용량 감소
2. **배치 처리**: 여러 특허를 한 번에 처리
3. **캐싱**: 자주 사용되는 조문 내용 캐싱
4. **비동기 처리**: asyncio를 활용한 동시 처리

## 라이선스

이 프로젝트는 특허 심사 목적으로만 사용되어야 합니다.
