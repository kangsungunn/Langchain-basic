# Vercel에 Frontend 배포하기 - 완전 가이드

## 📋 프로젝트 개요

**무엇을 배포하는가?**
- Next.js로 만든 React 프론트엔드 애플리케이션
- EC2에 배포된 FastAPI 백엔드와 통신

**왜 Vercel을 사용하나요?**
- Next.js를 만든 회사가 만든 플랫폼
- 자동 배포 (GitHub 푸시 시 자동 배포)
- 무료 플랜 제공
- 빠른 CDN (전 세계 어디서나 빠른 속도)
- SSL 인증서 자동 설정

**전체 구조:**
```
사용자 브라우저
    ↓
Vercel (Frontend) - https://your-app.vercel.app
    ↓ (API 요청)
EC2 (Backend) - http://EC2_IP:8000
```

---

## 🏗️ 전체 구조 이해하기

### 배포 전 구조

```
로컬 개발 환경
├── frontend/          ← Next.js 앱
│   └── src/
│       └── app/
│           └── page.tsx
└── app/              ← FastAPI 백엔드
    └── api_server_refactored.py
```

### 배포 후 구조

```
Vercel (프론트엔드)
├── Next.js 앱 실행
├── 사용자 요청 처리
└── API 요청을 EC2로 전달
    ↓
EC2 (백엔드)
├── FastAPI 앱 실행
└── 데이터 처리 및 응답
```

### 왜 프론트엔드와 백엔드를 분리하나요?

**장점:**
1. **독립적 배포**: 프론트엔드와 백엔드를 따로 배포 가능
2. **서로 다른 플랫폼**: 프론트엔드는 Vercel, 백엔드는 EC2
3. **확장성**: 프론트엔드만 여러 개 배포 가능 (예: 웹, 모바일)
4. **성능**: Vercel의 글로벌 CDN으로 빠른 속도

---

## 🚀 배포 방법 (2가지)

### 방법 1: Vercel 웹 대시보드 사용 (초보자 추천)

**장점:**
- GUI로 쉽게 설정
- 단계별 가이드 제공
- 실시간 배포 상태 확인

### 방법 2: Vercel CLI 사용 (고급)

**장점:**
- 명령어로 빠르게 배포
- 자동화 스크립트 작성 가능

---

## 📝 방법 1: Vercel 웹 대시보드로 배포

### Step 1: GitHub에 frontend 폴더를 별도 저장소로 푸시

**왜 별도 저장소가 필요한가?**
- Vercel은 GitHub 저장소를 연결하여 배포
- frontend 폴더만 배포하려면 별도 저장소가 편함

**방법 A: frontend를 루트로 하는 새 저장소 생성 (권장)**

```bash
# 1. frontend 폴더로 이동
cd frontend

# 2. Git 초기화 (이미 .git이 있다면 생략)
git init

# 3. 모든 파일 추가
git add .

# 4. 첫 커밋
git commit -m "Initial commit: Next.js frontend"

# 5. GitHub에서 새 저장소 생성 후
# 6. 원격 저장소 연결 및 푸시
git remote add origin https://github.com/YOUR_USERNAME/frontend-repo.git
git branch -M main
git push -u origin main
```

**방법 B: 기존 저장소의 frontend 폴더만 배포**

- Vercel에서 Root Directory를 `frontend`로 설정하면 됨

### Step 2: Vercel에 프로젝트 추가

1. **Vercel 웹사이트 접속**
   - https://vercel.com 접속
   - GitHub 계정으로 로그인

2. **New Project 클릭**
   - 대시보드에서 "Add New..." → "Project" 클릭

3. **GitHub 저장소 선택**
   - 방금 만든 frontend 저장소 선택
   - 또는 기존 저장소에서 frontend 폴더 선택

4. **프로젝트 설정**
   - **Framework Preset**: Next.js (자동 감지됨)
   - **Root Directory**: `frontend` (기존 저장소 사용 시) 또는 `.` (별도 저장소 사용 시)
   - **Build Command**: `npm run build` (자동 설정됨)
   - **Output Directory**: `.next` (자동 설정됨)

### Step 3: 환경 변수 설정

**중요한 환경 변수:**
- `NEXT_PUBLIC_API_URL`: 백엔드 API 주소

**설정 방법:**
1. 프로젝트 설정 페이지에서 "Environment Variables" 클릭
2. 다음 변수 추가:

```
NEXT_PUBLIC_API_URL = http://YOUR_EC2_IP:8000
```

**예시:**
```
NEXT_PUBLIC_API_URL = http://54.180.124.217:8000
```

**왜 `NEXT_PUBLIC_` 접두사가 필요한가?**
- Next.js는 `NEXT_PUBLIC_`로 시작하는 변수만 브라우저에서 사용 가능
- 보안을 위해 서버 전용 변수는 브라우저에 노출되지 않음

### Step 4: 배포 실행

1. **Deploy 버튼 클릭**
2. **배포 진행 상황 확인**
   - 빌드 로그 실시간 확인
   - 에러 발생 시 로그에서 확인

3. **배포 완료 후**
   - Vercel이 자동으로 URL 제공
   - 예: `https://your-app.vercel.app`

### Step 5: 자동 배포 설정 (이미 설정됨)

**GitHub 연동 시:**
- `main` 브랜치에 푸시하면 자동 배포
- Pull Request 생성 시 Preview 배포

---

## 💻 방법 2: Vercel CLI로 배포

### Step 1: Vercel CLI 설치

```bash
npm install -g vercel
```

### Step 2: Vercel 로그인

```bash
vercel login
```

- 브라우저가 열리면 GitHub 계정으로 로그인

### Step 3: frontend 폴더로 이동

```bash
cd frontend
```

### Step 4: 프로젝트 배포

```bash
vercel
```

**첫 배포 시 질문:**
1. "Set up and deploy?": `Y`
2. "Which scope?": 본인 계정 선택
3. "Link to existing project?": `N` (첫 배포)
4. "What's your project's name?": 프로젝트 이름 입력
5. "In which directory is your code located?": `./` (현재 디렉토리)

### Step 5: 환경 변수 설정

```bash
vercel env add NEXT_PUBLIC_API_URL
```

- 프롬프트에 EC2 백엔드 주소 입력
- 예: `http://54.180.124.217:8000`

### Step 6: 프로덕션 배포

```bash
vercel --prod
```

---

## 🔧 환경 변수 설정 상세

### 필수 환경 변수

**NEXT_PUBLIC_API_URL**
- **값**: EC2 백엔드 주소
- **예시**: `http://54.180.124.217:8000`
- **용도**: 프론트엔드에서 백엔드 API 호출 시 사용

### 환경 변수 설정 위치

**Vercel 대시보드:**
1. 프로젝트 선택
2. Settings → Environment Variables
3. 변수 추가:
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `http://YOUR_EC2_IP:8000`
   - Environment: Production, Preview, Development 모두 선택

**CLI로 설정:**
```bash
vercel env add NEXT_PUBLIC_API_URL production
# 프롬프트에 값 입력
```

### 환경 변수 사용 방법

**코드에서 사용:**
```typescript
// next.config.js에서 이미 설정됨
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API 호출 예시
fetch(`${apiUrl}/api/chat/rag`, {
  method: 'POST',
  body: JSON.stringify(data)
})
```

---

## 🔍 CORS 설정 (중요!)

### 문제 상황

**에러 메시지:**
```
Access to fetch at 'http://EC2_IP:8000/api/...' from origin 'https://your-app.vercel.app'
has been blocked by CORS policy
```

**원인:**
- Vercel(HTTPS)에서 EC2(HTTP)로 요청 시 CORS 정책 위반
- 브라우저가 다른 도메인 간 요청을 차단

### 해결 방법: FastAPI 백엔드에 CORS 설정

**EC2의 FastAPI 앱에 이미 설정되어 있어야 함:**

```python
# app/api_server_refactored.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 또는 특정 도메인만: ["https://your-app.vercel.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**프로덕션에서는 특정 도메인만 허용하는 것이 좋습니다:**
```python
allow_origins=[
    "https://your-app.vercel.app",
    "https://www.your-domain.com"
]
```

---

## 📊 배포 후 확인 사항

### 1. 배포 상태 확인

**Vercel 대시보드:**
- Deployments 탭에서 배포 상태 확인
- 성공 시 초록색 체크 표시

### 2. 사이트 접속 테스트

**브라우저에서:**
```
https://your-app.vercel.app
```

**예상 결과:**
- Next.js 앱이 정상적으로 표시됨

### 3. API 연결 테스트

**브라우저 개발자 도구 (F12):**
- Network 탭에서 API 요청 확인
- 백엔드로 요청이 정상적으로 전달되는지 확인

### 4. 에러 확인

**Vercel 대시보드:**
- Functions 탭에서 에러 로그 확인
- Runtime Logs에서 실시간 로그 확인

---

## 🔄 자동 배포 설정

### GitHub 연동 시 자동 배포

**이미 설정됨:**
- `main` 브랜치에 푸시하면 자동 배포
- Pull Request 생성 시 Preview 배포

**작동 방식:**
```
로컬에서 코드 수정
    ↓
git push origin main
    ↓
GitHub 저장소 업데이트
    ↓
Vercel이 자동으로 감지
    ↓
자동 빌드 및 배포
    ↓
약 1-2분 후 배포 완료
```

### 배포 브랜치 설정

**Vercel 대시보드:**
1. Settings → Git
2. Production Branch: `main` (기본값)
3. Preview Branches: 모든 브랜치 또는 특정 브랜치만

---

## 🛠️ 문제 해결 가이드

### 문제 1: 빌드 실패

**증상:**
- Vercel 배포 시 빌드 에러 발생

**확인 사항:**
1. 로컬에서 빌드 테스트:
   ```bash
   cd frontend
   npm run build
   ```

2. `package.json`의 빌드 스크립트 확인:
   ```json
   "scripts": {
     "build": "next build"
   }
   ```

3. Vercel 빌드 로그 확인:
   - Deployments → 실패한 배포 클릭 → Build Logs

### 문제 2: 환경 변수가 적용되지 않음

**증상:**
- `NEXT_PUBLIC_API_URL`이 `undefined`

**해결 방법:**
1. Vercel 대시보드에서 환경 변수 확인
2. 변수명이 정확한지 확인 (`NEXT_PUBLIC_` 접두사 필수)
3. 배포 후 재배포 (환경 변수 변경 시)

### 문제 3: CORS 에러

**증상:**
```
Access to fetch ... has been blocked by CORS policy
```

**해결 방법:**
1. EC2의 FastAPI 앱에 CORS 미들웨어 추가
2. Vercel 도메인을 `allow_origins`에 추가
3. EC2 서비스 재시작:
   ```bash
   sudo systemctl restart langchain-api.service
   ```

### 문제 4: API 연결 실패

**증상:**
- 프론트엔드는 로드되지만 API 호출 실패

**확인 사항:**
1. EC2 서버가 실행 중인지:
   ```bash
   curl http://EC2_IP:8000/health
   ```

2. Security Group에서 포트 8000이 허용되었는지
3. 환경 변수 `NEXT_PUBLIC_API_URL`이 올바른지

---

## 📁 프로젝트 구조 (배포 후)

### Vercel에 배포되는 구조

```
frontend/                    ← Vercel이 이 폴더를 배포
├── src/
│   └── app/
│       ├── page.tsx        ← 메인 페이지
│       └── layout.tsx      ← 레이아웃
├── public/                  ← 정적 파일 (이미지 등)
├── package.json            ← 의존성 정의
├── next.config.js          ← Next.js 설정
└── tsconfig.json           ← TypeScript 설정
```

### Vercel이 자동으로 하는 일

1. **의존성 설치**: `npm install`
2. **빌드**: `npm run build`
3. **배포**: 빌드된 파일을 CDN에 배포
4. **도메인 할당**: `https://your-app.vercel.app`

---

## 🎯 핵심 포인트 정리

### 1. 왜 Vercel을 사용하나요?

**Next.js 최적화:**
- Next.js를 만든 회사가 만든 플랫폼
- Next.js에 최적화된 빌드 및 배포

**편의성:**
- GitHub 연동으로 자동 배포
- SSL 인증서 자동 설정
- 글로벌 CDN으로 빠른 속도

**무료 플랜:**
- 개인 프로젝트에 충분한 무료 플랜 제공

### 2. 환경 변수 설정이 중요한 이유

**보안:**
- API 주소를 코드에 하드코딩하지 않음
- 환경별로 다른 설정 사용 가능

**유연성:**
- 개발/프로덕션 환경 분리
- 설정 변경 시 코드 수정 불필요

### 3. CORS가 필요한 이유

**브라우저 보안 정책:**
- 다른 도메인 간 요청을 기본적으로 차단
- 백엔드에서 명시적으로 허용해야 함

**해결 방법:**
- FastAPI에 CORS 미들웨어 추가
- Vercel 도메인을 허용 목록에 추가

---

## 🚀 실제 배포 시나리오

### 시나리오 1: 첫 배포

**1. GitHub에 frontend 저장소 생성**
```bash
cd frontend
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/frontend.git
git push -u origin main
```

**2. Vercel에서 프로젝트 추가**
- GitHub 저장소 선택
- 환경 변수 설정
- Deploy 클릭

**3. 배포 완료 확인**
- Vercel URL로 접속
- 정상 작동 확인

### 시나리오 2: 코드 수정 후 재배포

**1. 로컬에서 코드 수정**
```bash
cd frontend
# 코드 수정
vim src/app/page.tsx
```

**2. GitHub에 푸시**
```bash
git add .
git commit -m "UI 개선"
git push origin main
```

**3. 자동 배포**
- Vercel이 자동으로 감지
- 약 1-2분 후 배포 완료

---

## 📚 학습 체크리스트

이 가이드를 읽은 후 다음을 이해했는지 확인하세요:

- [ ] Vercel이 무엇인지 이해
- [ ] 왜 프론트엔드와 백엔드를 분리하는지 이해
- [ ] 환경 변수 설정 방법 이해
- [ ] CORS가 왜 필요한지 이해
- [ ] 자동 배포가 어떻게 작동하는지 이해
- [ ] 배포 후 확인 방법 이해

---

## 🎓 다음 단계 학습 과제

1. **커스텀 도메인 연결**: Vercel 앱에 자신의 도메인 연결
2. **환경별 설정**: 개발/프로덕션 환경 분리
3. **성능 최적화**: 이미지 최적화, 코드 스플리팅
4. **모니터링**: Vercel Analytics로 사용자 분석
5. **에러 추적**: Sentry 등으로 에러 모니터링

---

## 💡 실무 팁

### 1. 배포 전 확인사항

- 로컬에서 `npm run build` 성공 확인
- 환경 변수 값 확인
- API 연결 테스트

### 2. 배포 후 확인사항

- 사이트 접속 테스트
- API 연결 테스트
- 브라우저 콘솔에서 에러 확인

### 3. 문제 발생 시

- Vercel 빌드 로그 확인
- 브라우저 개발자 도구 확인
- EC2 백엔드 상태 확인

---

## 📝 요약

**전체 구조:**
```
Vercel (Frontend)
  → Next.js 앱 실행
  → 사용자 요청 처리
  → API 요청을 EC2로 전달
    ↓
EC2 (Backend)
  → FastAPI 앱 실행
  → 데이터 처리 및 응답
```

**핵심 개념:**
- **Vercel**: Next.js 최적화된 배포 플랫폼
- **환경 변수**: `NEXT_PUBLIC_` 접두사 필수
- **CORS**: 백엔드에서 프론트엔드 도메인 허용 필요
- **자동 배포**: GitHub 푸시 시 자동 배포

**왜 이렇게 설계했나요?**
- 프론트엔드와 백엔드 독립적 배포
- Vercel의 글로벌 CDN으로 빠른 속도
- 자동 배포로 개발 효율성 향상

이제 Vercel에 프론트엔드를 배포할 준비가 되었습니다! 🎉

