# 변리사 민사소송법 답안지 첨삭 서비스 - 프론트엔드

## 📋 개요

Next.js 14 기반 프론트엔드 애플리케이션

## 🏗️ 구조

```
frontend/
├── src/
│   └── app/
│       ├── page.tsx              # 홈화면
│       ├── upload/
│       │   └── page.tsx          # 답안지 업로드 화면
│       ├── review/
│       │   └── [id]/
│       │       └── page.tsx      # 첨삭 결과 화면
│       └── api/
│           └── v1/                # 프론트엔드 라우터 (백엔드 프록시)
│               ├── submission/    # 답안지 업로드 API
│               ├── reasoning/     # 추론 분석 API
│               └── feedback/      # 피드백 생성 API
```

## 🚀 실행 방법

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 빌드
npm run build

# 프로덕션 실행
npm start
```

## 🔌 백엔드 연결

프론트엔드는 `app/api/v1/` 라우터를 통해 백엔드와 연결됩니다.

**환경 변수 설정**:
```bash
# .env.local 파일 생성
BACKEND_URL=http://localhost:8000
```

**프론트엔드 API Routes**:
- `/api/v1/submission` → 백엔드 `app/api/v1/submission.py`
- `/api/v1/reasoning/analyze/comprehensive` → 백엔드 `app/api/v1/reasoning.py`
- `/api/v1/feedback/generate` → 백엔드 `app/api/v1/feedback.py`

## 📱 화면 구성

### 1. 홈화면 (`/`)
- 서비스 소개
- 기능 설명 (쟁점 분석, 논리 평가, 표현 검토)
- 사용 방법 안내
- 답안지 첨삭 시작 버튼

### 2. 답안지 업로드 화면 (`/upload`)
- PDF 파일 드래그 앤 드롭
- 파일 선택 버튼
- 문제 파일 업로드 (선택사항)
- 답안지 파일 업로드 (필수)
- 첨삭 시작 버튼

### 3. 첨삭 결과 화면 (`/review/[id]`)
- 종합 점수 카드 (쟁점, 논리, 표현)
- 탭 네비게이션 (종합 평가, 쟁점 분석, 논리 평가, 표현 검토)
- 상세 피드백 표시
- 결과 인쇄 기능

## 🛠️ 기술 스택

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Hooks

## 📝 주요 기능

1. **파일 업로드**
   - PDF 파일 드래그 앤 드롭 지원
   - 파일 크기 표시
   - 업로드 진행 상태 표시

2. **자동 OCR 처리**
   - 이미지/PDF 파일 업로드 시 자동 OCR 처리
   - 텍스트 추출 후 분석 진행

3. **실시간 분석**
   - 업로드 후 자동으로 분석 시작
   - 진행 상황 표시

4. **종합 피드백**
   - 쟁점, 논리, 표현 종합 분석
   - 강점/약점/개선 제안 제공
