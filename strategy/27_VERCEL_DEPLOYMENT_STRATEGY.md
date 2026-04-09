# Vercel 배포 전략 - 환경 변수 및 자동 배포

## 📋 전략 개요

**목표:**
- Vercel에 Next.js 프론트엔드 배포
- 환경 변수를 안전하게 관리
- GitHub 푸시 시 자동 배포 설정

**핵심 전략:**
1. 환경 변수 관리 전략
2. 자동 배포 파이프라인 구축
3. 개발/프로덕션 환경 분리

---

## 🔐 전략 1: 환경 변수 관리

### 왜 환경 변수를 사용하나요?

**문제 상황:**
```typescript
// 나쁜 예: 하드코딩
const API_URL = 'http://54.180.124.217:8000'
```

**문제점:**
- 환경별로 다른 주소 사용 불가 (개발/프로덕션)
- 코드 수정 없이 설정 변경 불가
- 보안 위험 (민감한 정보 노출)

**해결책: 환경 변수**
```typescript
// 좋은 예: 환경 변수 사용
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

**장점:**
- 환경별로 다른 설정 사용 가능
- 코드 수정 없이 설정 변경 가능
- 보안 강화

### Next.js 환경 변수 규칙

#### 규칙 1: 브라우저에서 사용하려면 `NEXT_PUBLIC_` 접두사 필수

**브라우저에서 사용 가능:**
```typescript
// ✅ 브라우저에서 사용 가능
process.env.NEXT_PUBLIC_API_URL
```

**브라우저에서 사용 불가:**
```typescript
// ❌ 브라우저에서 사용 불가 (서버에서만 사용)
process.env.API_URL
```

**왜 이렇게 하나요?**
- 보안: 민감한 정보(비밀번호 등)를 브라우저에 노출하지 않음
- 명확성: `NEXT_PUBLIC_` 접두사로 브라우저 노출 여부 명확히 표시

#### 규칙 2: 환경 변수는 빌드 시점에 주입됨

**빌드 시점:**
- Vercel이 `npm run build` 실행 시 환경 변수를 주입
- 빌드된 파일에 환경 변수 값이 포함됨

**런타임 시점:**
- 브라우저에서 이미 주입된 값 사용
- 런타임에 환경 변수 변경 불가

**중요:**
- 환경 변수 변경 후 재배포 필요
- 빌드 없이는 환경 변수 변경이 반영되지 않음

### 환경 변수 설정 전략

#### 전략 1: 환경별 변수 분리

**개발 환경 (로컬):**
```bash
# .env.local (로컬 개발용)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**프로덕션 환경 (Vercel):**
```
NEXT_PUBLIC_API_URL=http://YOUR_EC2_IP:8000
```

**Preview 환경 (Vercel):**
```
NEXT_PUBLIC_API_URL=http://YOUR_EC2_IP:8000
```

**왜 분리하나요?**
- 개발: 로컬 백엔드 사용
- 프로덕션: 실제 EC2 백엔드 사용
- Preview: Pull Request 테스트용

#### 전략 2: Vercel에서 환경 변수 설정

**설정 위치:**
1. Vercel 대시보드 접속
2. 프로젝트 선택
3. Settings → Environment Variables

**설정 방법:**
1. Key 입력: `NEXT_PUBLIC_API_URL`
2. Value 입력: `http://YOUR_EC2_IP:8000`
3. Environment 선택:
   - ✅ Production
   - ✅ Preview
   - ✅ Development

**각 환경의 의미:**
- **Production**: `main` 브랜치 배포 시 사용
- **Preview**: Pull Request 배포 시 사용
- **Development**: 로컬 개발 시 사용 (Vercel CLI 사용 시)

#### 전략 3: 기본값 설정

**코드에서 기본값 설정:**
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

**왜 기본값이 필요한가?**
- 로컬 개발 시 환경 변수 없이도 작동
- Vercel 설정 실수 시에도 기본값으로 작동

**주의사항:**
- 프로덕션에서는 항상 Vercel에서 설정한 값 사용
- 기본값은 로컬 개발용으로만 사용

### 환경 변수 설정 체크리스트

배포 전 확인:
- [ ] Vercel에서 `NEXT_PUBLIC_API_URL` 설정 완료
- [ ] Production, Preview, Development 모두 설정
- [ ] 값이 올바른지 확인 (EC2 IP 주소)
- [ ] 코드에서 기본값 설정 확인

---

## 🔄 전략 2: 자동 배포 파이프라인

### 자동 배포가 작동하는 원리

**전체 흐름:**
```
로컬에서 코드 수정
    ↓
git add .
git commit -m "변경사항"
git push origin main
    ↓
GitHub 저장소 업데이트
    ↓
Vercel이 자동으로 감지 (Webhook)
    ↓
자동 빌드 시작
    ├─ npm install (의존성 설치)
    ├─ npm run build (빌드)
    └─ 환경 변수 주입
    ↓
배포 실행
    ├─ 빌드된 파일을 CDN에 배포
    └─ 도메인 할당
    ↓
배포 완료 (약 1-2분)
```

### 자동 배포 설정 방법

#### Step 1: GitHub 저장소 연결

**Vercel 대시보드에서:**
1. "Add New..." → "Project"
2. "Import Git Repository" 클릭
3. GitHub 저장소 선택
4. "Import" 클릭

**이것이 하는 일:**
- Vercel이 GitHub 저장소에 Webhook 설정
- 저장소 변경 시 Vercel에 알림 전송

#### Step 2: 배포 설정 확인

**프로젝트 설정:**
- **Framework Preset**: Next.js
- **Root Directory**: `frontend` (또는 `.`)
- **Build Command**: `npm run build` (자동 감지)
- **Output Directory**: `.next` (자동 감지)

**Branch 설정:**
- **Production Branch**: `main` (기본값)
- **Preview Branches**: 모든 브랜치 또는 특정 브랜치

#### Step 3: 자동 배포 활성화

**이미 활성화됨:**
- GitHub 저장소 연결 시 자동으로 활성화
- 별도 설정 불필요

### 배포 시나리오별 동작

#### 시나리오 1: main 브랜치에 푸시

**트리거:**
```bash
git push origin main
```

**동작:**
1. Vercel이 자동으로 감지
2. Production 환경으로 빌드
3. Production 환경 변수 사용
4. 배포 완료 후 Production URL 업데이트

**결과:**
- Production 사이트 업데이트
- 기존 URL 유지 (예: `https://your-app.vercel.app`)

#### 시나리오 2: Pull Request 생성

**트리거:**
```bash
git checkout -b feature/new-feature
# 코드 수정
git push origin feature/new-feature
# GitHub에서 Pull Request 생성
```

**동작:**
1. Vercel이 자동으로 감지
2. Preview 환경으로 빌드
3. Preview 환경 변수 사용
4. 고유한 Preview URL 생성

**결과:**
- Preview 사이트 생성
- 새로운 URL 할당 (예: `https://your-app-git-feature-new-feature.vercel.app`)
- Pull Request에 Preview 링크 자동 추가

**장점:**
- 코드 리뷰 전에 실제 배포된 버전 확인 가능
- 변경사항을 실제 환경에서 테스트 가능

#### 시나리오 3: 다른 브랜치에 푸시

**트리거:**
```bash
git push origin develop
```

**동작:**
- Preview 환경으로 배포
- 고유한 Preview URL 생성

**설정 변경:**
- Settings → Git → Preview Branches
- 특정 브랜치만 Preview 배포하도록 설정 가능

### 자동 배포 최적화 전략

#### 전략 1: 빌드 캐시 활용

**Vercel이 자동으로 하는 일:**
- 이전 빌드의 `node_modules` 캐시 사용
- 변경되지 않은 파일은 재빌드하지 않음

**효과:**
- 빌드 시간 단축 (약 30-50% 감소)
- 비용 절감

#### 전략 2: 조건부 배포

**특정 파일만 변경 시 배포 스킵:**

**방법: Vercel 설정 파일 사용**

`vercel.json` 생성:
```json
{
  "git": {
    "deployOnPush": {
      "main": true,
      "branches": ["main", "develop"]
    }
  },
  "ignoreCommand": "git diff HEAD^ HEAD --quiet frontend/"
}
```

**이것이 하는 일:**
- `frontend/` 폴더가 변경되지 않으면 배포 스킵
- 불필요한 배포 방지

#### 전략 3: 배포 알림 설정

**Slack/Discord 연동:**
1. Settings → Integrations
2. Slack 또는 Discord 선택
3. 웹훅 URL 설정

**알림 내용:**
- 배포 시작 알림
- 배포 완료 알림
- 배포 실패 알림

---

## 🎯 전략 3: 개발/프로덕션 환경 분리

### 환경 분리 전략

#### 전략 1: 환경 변수로 분리

**로컬 개발:**
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Vercel Production:**
```
NEXT_PUBLIC_API_URL=http://YOUR_EC2_IP:8000
```

**Vercel Preview:**
```
NEXT_PUBLIC_API_URL=http://YOUR_EC2_IP:8000
```

#### 전략 2: 코드에서 환경 감지

```typescript
const isDevelopment = process.env.NODE_ENV === 'development'
const isProduction = process.env.NODE_ENV === 'production'

const API_URL = isDevelopment
  ? 'http://localhost:8000'
  : process.env.NEXT_PUBLIC_API_URL
```

**왜 이렇게 하나요?**
- 개발 환경: 항상 로컬 백엔드 사용
- 프로덕션 환경: Vercel 설정 값 사용

#### 전략 3: 환경별 기능 분기

```typescript
// 개발 환경에서만 디버그 로그 출력
if (process.env.NODE_ENV === 'development') {
  console.log('API Request:', endpoint, data)
}

// 프로덕션에서만 Analytics 활성화
if (process.env.NODE_ENV === 'production') {
  // Analytics 코드
}
```

---

## 🔧 실제 설정 가이드

### Step 1: Vercel 프로젝트 생성

1. **Vercel 대시보드 접속**
   - https://vercel.com
   - GitHub 계정으로 로그인

2. **프로젝트 추가**
   - "Add New..." → "Project"
   - GitHub 저장소 선택

3. **프로젝트 설정**
   - Framework Preset: Next.js
   - Root Directory: `frontend` (기존 저장소 사용 시)
   - Build Command: `npm run build` (자동)
   - Output Directory: `.next` (자동)

### Step 2: 환경 변수 설정

1. **Settings → Environment Variables 이동**

2. **환경 변수 추가:**
   ```
   Key: NEXT_PUBLIC_API_URL
   Value: http://YOUR_EC2_IP:8000
   ```

3. **Environment 선택:**
   - ✅ Production
   - ✅ Preview
   - ✅ Development

4. **Save 클릭**

### Step 3: 첫 배포

1. **Deploy 버튼 클릭**
2. **빌드 로그 확인**
3. **배포 완료 대기 (약 1-2분)**
4. **배포된 URL 확인**

### Step 4: 자동 배포 테스트

1. **로컬에서 코드 수정**
   ```bash
   cd frontend
   # 코드 수정
   ```

2. **GitHub에 푸시**
   ```bash
   git add .
   git commit -m "테스트: 자동 배포 확인"
   git push origin main
   ```

3. **Vercel 대시보드 확인**
   - Deployments 탭에서 자동 배포 진행 상황 확인
   - 약 1-2분 후 배포 완료

---

## 🔍 환경 변수 확인 방법

### 방법 1: Vercel 대시보드에서 확인

1. 프로젝트 → Settings → Environment Variables
2. 설정된 환경 변수 목록 확인

### 방법 2: 배포된 사이트에서 확인

**브라우저 개발자 도구 (F12):**
```javascript
// Console 탭에서 실행
console.log(process.env.NEXT_PUBLIC_API_URL)
```

**주의:**
- `NEXT_PUBLIC_` 접두사가 없는 변수는 `undefined`로 표시됨
- 이는 정상 동작 (보안을 위해)

### 방법 3: 빌드 로그에서 확인

**Vercel 빌드 로그:**
- Deployments → 배포 클릭 → Build Logs
- 환경 변수 주입 과정 확인 가능

---

## 🚨 주의사항 및 모범 사례

### 주의사항 1: 환경 변수 이름 규칙

**✅ 올바른 예:**
```
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_APP_NAME
```

**❌ 잘못된 예:**
```
API_URL              # 브라우저에서 사용 불가
NEXT_PUBLIC_api_url  # 대소문자 구분 (권장하지 않음)
```

### 주의사항 2: 환경 변수 변경 후 재배포

**중요:**
- 환경 변수 변경 후 자동으로 재배포되지 않음
- 수동으로 재배포하거나 코드 푸시 필요

**재배포 방법:**
1. Deployments → "Redeploy" 클릭
2. 또는 코드를 약간 수정 후 푸시

### 주의사항 3: 민감한 정보 관리

**❌ 절대 하지 말아야 할 것:**
```typescript
// 절대 이렇게 하지 마세요!
const API_KEY = process.env.NEXT_PUBLIC_API_KEY  // 브라우저에 노출됨!
```

**✅ 올바른 방법:**
```typescript
// 서버에서만 사용 (API Routes)
// 브라우저에서 사용하지 않음
const API_KEY = process.env.API_KEY  // NEXT_PUBLIC_ 없음
```

**규칙:**
- 비밀번호, API 키 등은 `NEXT_PUBLIC_` 접두사 사용 금지
- 공개되어도 괜찮은 정보만 `NEXT_PUBLIC_` 사용

### 모범 사례 1: 환경 변수 문서화

**README.md에 기록:**
```markdown
## 환경 변수

### 필수 환경 변수
- `NEXT_PUBLIC_API_URL`: 백엔드 API 주소

### 설정 방법
1. Vercel 대시보드 → Settings → Environment Variables
2. 변수 추가 및 값 설정
```

### 모범 사례 2: 환경별 설정 파일

**.env.example 파일 생성:**
```bash
# .env.example
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**용도:**
- 다른 개발자가 참고할 수 있는 템플릿
- 실제 값은 포함하지 않음

---

## 📊 배포 상태 모니터링

### 배포 상태 확인

**Vercel 대시보드:**
1. Deployments 탭
2. 각 배포의 상태 확인:
   - ✅ Ready: 배포 성공
   - ⏳ Building: 빌드 중
   - ❌ Error: 배포 실패

### 배포 로그 확인

**빌드 로그:**
- Deployments → 배포 클릭 → Build Logs
- 빌드 과정 상세 확인

**런타임 로그:**
- Functions 탭
- 서버리스 함수 실행 로그

### 배포 알림 설정

**이메일 알림:**
- Settings → Notifications
- 배포 성공/실패 시 이메일 수신

**Slack/Discord 연동:**
- Settings → Integrations
- 실시간 배포 알림 수신

---

## 🔄 자동 배포 워크플로우 최적화

### 최적화 전략 1: 배포 브랜치 제한

**설정:**
- Settings → Git → Production Branch: `main`만
- Preview Branches: 특정 브랜치만

**효과:**
- 불필요한 배포 방지
- 비용 절감

### 최적화 전략 2: 빌드 시간 단축

**방법:**
1. 불필요한 의존성 제거
2. 이미지 최적화
3. 코드 스플리팅

**효과:**
- 배포 시간 단축
- 사용자 경험 향상

### 최적화 전략 3: 배포 롤백 전략

**자동 롤백:**
- 배포 실패 시 이전 버전으로 자동 롤백
- Settings → Git → Automatic Rollbacks

**수동 롤백:**
- Deployments → 이전 배포 선택 → "Promote to Production"

---

## 🎓 학습 체크리스트

이 전략을 이해한 후 확인:

- [ ] `NEXT_PUBLIC_` 접두사가 왜 필요한지 이해
- [ ] 환경 변수 설정 방법 이해
- [ ] 자동 배포가 어떻게 작동하는지 이해
- [ ] Production과 Preview의 차이 이해
- [ ] 환경 변수 변경 후 재배포가 필요한 이유 이해

---

## 💡 실무 팁

### 팁 1: 환경 변수 변경 시

1. Vercel에서 환경 변수 수정
2. Deployments → "Redeploy" 클릭
3. 또는 코드를 약간 수정 후 푸시

### 팁 2: 배포 실패 시

1. Build Logs 확인
2. 에러 메시지 확인
3. 로컬에서 `npm run build` 테스트
4. 문제 해결 후 재배포

### 팁 3: Preview 배포 활용

- Pull Request 생성 시 자동 Preview 배포
- 실제 배포 전에 테스트 가능
- 코드 리뷰 시 실제 동작 확인

---

## 📝 요약

**환경 변수 전략:**
- `NEXT_PUBLIC_` 접두사 필수 (브라우저 사용 시)
- Vercel에서 환경별로 설정
- 변경 후 재배포 필요

**자동 배포 전략:**
- GitHub 저장소 연결 시 자동 활성화
- `main` 브랜치 푸시 → Production 배포
- Pull Request → Preview 배포

**환경 분리 전략:**
- 환경 변수로 개발/프로덕션 분리
- 코드에서 환경 감지하여 분기 처리

이제 Vercel 배포 전략을 완벽하게 이해하셨습니다! 🎉

