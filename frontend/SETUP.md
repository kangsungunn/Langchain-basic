# 프론트엔드 설정 가이드

## ⚠️ 중요: 백엔드 API 수정 필요

현재 백엔드 API (`app/api/v1/submission.py`)는 `image_path` (문자열)를 받는 구조입니다.
프론트엔드에서 파일을 직접 업로드하려면 백엔드 API를 수정해야 합니다.

### 백엔드 수정 필요 사항

**현재 구조**:
```python
@router.post("/answers/image")
async def create_image_answer(
    data: UserAnswerCreateImage,  # image_path: str
    ...
)
```

**수정 필요**:
```python
from fastapi import File, UploadFile

@router.post("/answers/image")
async def create_image_answer(
    file: UploadFile = File(...),
    problem_id: str = Form(""),
    session: AsyncSession = Depends(get_session)
):
    # 파일 저장 후 경로 반환
    ...
```

## 📦 패키지 설치

```bash
cd frontend
npm install
```

## 🔧 환경 변수 설정

`.env.local` 파일 생성:
```bash
BACKEND_URL=http://localhost:8000
```

## 🚀 실행

```bash
npm run dev
```

브라우저에서 `http://localhost:3000` 접속

## 📱 화면 구성

1. **홈화면** (`/`)
   - 서비스 소개 및 시작 버튼

2. **업로드 화면** (`/upload`)
   - PDF 파일 드래그 앤 드롭
   - 파일 선택 및 업로드

3. **첨삭 결과 화면** (`/review/[id]`)
   - 종합 점수 및 상세 피드백
