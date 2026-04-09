# Legal AI Agent - 변리사 업무 지원 AI 에이전트

## 📋 개요

특허·상표 업무를 지원하는 전문 AI 에이전트 시스템

### 핵심 기능

1. **Examination (심사 판단)**
   - 특허성 분석 (신규성/진보성)
   - 상표성 분석 (식별력/유사도)
   - 거절 가능성 예측

2. **Dispute (분쟁 대응)**
   - 무효심판/이의신청 분석
   - 대응 전략 생성
   - 판례 기반 논리 구성

3. **Document (문서 자동화)**
   - 의견서 초안 생성
   - 보정서 초안 생성
   - 법률 문서 템플릿

---

## 🏗️ 프로젝트 구조

```
legal-ai-agent/
├── app/                      # EC2 배포 (실행 환경)
│   ├── api/                 # FastAPI 엔드포인트
│   │   ├── main.py         # FastAPI 앱
│   │   ├── examination/    # 심사 판단 API
│   │   ├── dispute/        # 분쟁 대응 API
│   │   └── document/       # 문서 자동화 API
│   │
│   ├── core/                # 비즈니스 로직 (데이터 분석)
│   │   ├── examination/    # 특허/상표 분석 엔진
│   │   ├── dispute/        # 분쟁 대응 엔진
│   │   ├── document/       # 문서 생성 엔진
│   │   └── shared/         # 공통 로직
│   │       ├── models/     # ML 모델 관리
│   │       ├── rag/        # RAG 검색 엔진
│   │       ├── legal/      # 법률 유틸
│   │       └── orchestration/  # LangGraph 오케스트레이션
│   │
│   └── domain/              # 도메인 모델
│       ├── examination/    # Patent, Trademark 모델
│       ├── dispute/        # Dispute 모델
│       ├── document/       # Document 모델
│       └── shared/         # 공통 모델
│
├── artifacts/                # S3 배포 (모델 저장소)
│   ├── models/
│   │   ├── base/           # 베이스 LLM
│   │   └── finetuned/      # 법률 LoRA
│   ├── vectordb/           # 판례 벡터 DB
│   └── knowledge/          # 법령 지식베이스
│
├── training/                 # 모델 훈련
│   ├── examination/        # 특허/상표 모델 훈련
│   ├── dispute/            # 분쟁 대응 모델
│   ├── document/           # 문서 생성 모델
│   └── shared/             # 공통 훈련 유틸
│
└── data/                     # 학습 데이터
    ├── raw/                # 법령, 판례 원본
    ├── processed/          # 전처리 완료
    └── annotations/        # 레이블링
```

---

## 🚀 시작하기

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd legal-ai-agent

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r app/requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```bash
# 모델 경로
KOELECTRA_BASE_PATH=artifacts/models/base/koelectra-small-v3-discriminator
EXAONE_BASE_PATH=artifacts/models/base/exaone-2.4b

# 데이터베이스
DATABASE_URL=postgresql://user:pass@localhost:5432/legal_ai

# S3 (옵션)
MODEL_STORAGE=local  # 또는 s3
S3_BUCKET=legal-ai-models
```

### 3. API 서버 실행

```bash
# 개발 모드
cd app
uvicorn api.main:app --reload --port 8000

# 프로덕션 모드
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 4. API 문서 확인

브라우저에서 접속:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🌟 스타 토폴로지 아키텍처

```
[User Request]
    ↓
[Gateway] (1차 분류)
    ↓
[Legal Star Node] (중앙 허브)
    ↙      ↓      ↘
[Patent] [Trademark] [Dispute]
 Branch    Branch      Branch
    ↘      ↓      ↙
[Final Decision]
    ↓
[Response]
```

### 흐름 설명

1. **Gateway**: 요청 분류 (특허/상표/분쟁/문서)
2. **Legal Star Node**: 중앙 의사결정 허브
3. **Branch**: 전문 분석 에이전트
4. **Final Decision**: 법률 정책 적용 + 최종 판단

---

## 📚 API 사용 예시

### 특허성 분석

```python
import requests

response = requests.post(
    "http://localhost:8000/api/examination/patent",
    json={
        "title": "인공지능 기반 특허 분석 시스템",
        "invention_description": "본 발명은 인공지능을 활용하여...",
        "claims": [
            "청구항 1: 인공지능 기반 특허 분석 시스템...",
        ]
    }
)

result = response.json()
print(f"신규성: {result['novelty']}")
print(f"진보성: {result['inventiveness']}")
print(f"거절 위험도: {result['rejection_risk']}")
```

---

## 🔧 개발 가이드

### 새 도메인 추가

1. 폴더 생성
```bash
mkdir -p app/api/new_domain
mkdir -p app/core/new_domain
mkdir -p app/domain/new_domain
```

2. API 라우터 작성
```python
# app/api/new_domain/router.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/analyze")
async def analyze(request: dict):
    # 로직 구현
    return {"result": "success"}
```

3. `app/api/main.py`에 등록
```python
from app.api.new_domain import router as new_domain_router
app.include_router(new_domain_router, prefix="/api/new_domain")
```

---

## 🧪 테스트

```bash
# 단위 테스트
pytest tests/unit/

# 통합 테스트
pytest tests/integration/

# 전체 테스트
pytest tests/
```

---

## 📦 배포

### 1. artifacts를 S3에 업로드

```bash
aws s3 sync artifacts/ s3://legal-ai-models/artifacts/
```

### 2. EC2에서 실행

```bash
# artifacts 다운로드
aws s3 sync s3://legal-ai-models/artifacts/ /opt/app/artifacts/

# API 서버 실행
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

---

## 📝 법적 고지

**중요**: 본 AI 에이전트는 **변리사의 업무를 보조하는 도구**이며, 법률 자문을 대체하지 않습니다.

- ✅ 판단 근거 제공
- ✅ 위험 시나리오 제시
- ✅ 대응 옵션 제안
- ❌ 최종 법률 자문 제공 (전문 변리사와 상의 필수)

---

## 📄 라이선스

MIT License

---

## 📧 문의

- 이메일: contact@legal-ai.com
- 이슈: [GitHub Issues](https://github.com/your-repo/issues)

---

**버전**: 1.0.0
**최종 업데이트**: 2026-01-20
