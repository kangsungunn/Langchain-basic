# 🎨 프론트엔드 분리 및 아키텍처 개편

## 📋 개요

이 문서는 FastAPI 내장 HTML에서 독립적인 Next.js 프론트엔드로 분리한 이유와 아키텍처적 의사결정에 대해 설명합니다.

---

## 🤔 왜 프론트엔드를 분리했나?

### 기존 구조 (FastAPI 내장 HTML)

```python
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 페이지 - 채팅 UI"""
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>...</head>
        <body>
            <div class="chat-container">...</div>
            <script>
                // 수백 줄의 JavaScript 코드
            </script>
        </body>
    </html>
    """
    return html_content
```

**문제점:**

```
1. 코드 관리의 어려움
   - Python 파일 안에 HTML/CSS/JS 혼재
   - 문자열로 관리되는 프론트엔드 코드
   - 문법 하이라이팅 없음
   - 자동 완성 불가능

2. 개발 경험 저하
   - 수정 시 서버 재시작 필요
   - 핫 리로딩 없음
   - 디버깅 어려움

3. 확장성 제한
   - 복잡한 UI 구현 어려움
   - 컴포넌트 재사용 불가
   - 상태 관리 복잡

4. 배포 비효율
   - 프론트엔드 변경 시 백엔드도 재배포
   - 캐싱 전략 제한적
   - CDN 활용 불가
```

### 분리 후 구조 (Next.js)

```
langchain/
├── app/                    # FastAPI 백엔드
│   └── api_server.py      # API만 제공
│
├── frontend/              # Next.js 프론트엔드
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx   # 메인 페이지
│   │       └── globals.css
│   └── package.json
│
└── docker-compose.yaml    # 두 서비스 orchestration
```

**장점:**

```
1. 관심사의 분리 (Separation of Concerns)
   - 백엔드: 비즈니스 로직, 데이터 처리
   - 프론트엔드: UI/UX, 사용자 인터랙션

2. 독립적 개발 및 배포
   - 백엔드 변경 → 프론트엔드 영향 없음
   - 프론트엔드 변경 → 백엔드 영향 없음
   - 각각 독립적으로 확장 가능

3. 최신 프론트엔드 도구 활용
   - TypeScript 타입 안정성
   - React 컴포넌트 시스템
   - CSS Modules 스코핑
   - 핫 리로딩 개발 경험

4. 성능 최적화
   - 코드 스플리팅
   - 번들 최적화
   - 정적 생성 (Static Generation)
   - 이미지 최적화
```

---

## 🏗️ 아키텍처 구조

### 전체 시스템

```
┌─────────────────────────────────────────────┐
│           사용자 브라우저                    │
│                                              │
│  http://localhost:3000                      │
└────────────┬────────────────────────────────┘
             │
             │ HTTP/HTTPS
             ↓
┌─────────────────────────────────────────────┐
│        Next.js Frontend (Port 3000)         │
│                                              │
│  • React 컴포넌트                            │
│  • UI 렌더링                                 │
│  • 사용자 인터랙션                           │
│  • 상태 관리                                 │
└────────────┬────────────────────────────────┘
             │
             │ API 호출
             │ fetch('/api/chat/rag')
             ↓
┌─────────────────────────────────────────────┐
│      FastAPI Backend (Port 8000)            │
│                                              │
│  • /api/chat/rag                            │
│  • /api/chat/general                        │
│  • 비즈니스 로직                             │
│  • 데이터 처리                               │
└────────────┬────────────────────────────────┘
             │
             ├─────────────────┬──────────────┐
             ↓                 ↓              ↓
      ┌──────────┐      ┌──────────┐  ┌──────────┐
      │ PGVector │      │ OpenAI   │  │   기타   │
      │   DB     │      │   API    │  │ 서비스   │
      └──────────┘      └──────────┘  └──────────┘
```

### 통신 흐름

```
1. 사용자 입력
   사용자 → Next.js Frontend

2. API 요청
   Frontend → Backend (fetch)

3. 데이터 처리
   Backend → PGVector/OpenAI

4. 응답 반환
   Backend → Frontend (JSON)

5. UI 업데이트
   Frontend → 사용자
```

---

## 🎯 Next.js 선택 이유

### React 기반 프레임워크 선택지

| 프레임워크 | 장점 | 단점 | 선택 여부 |
|-----------|------|------|----------|
| **Next.js** | 풀스택, SSR/SSG, 최적화 | 학습 곡선 | ✅ 선택 |
| Create React App | 간단, 가벼움 | 최적화 부족, 더 이상 권장 안 함 | ❌ |
| Vite + React | 매우 빠름, 가벼움 | 수동 설정 필요 | ⚠️ 대안 |
| Remix | 풀스택, 웹 표준 | 상대적으로 신생 | ⚠️ 대안 |

### Next.js를 선택한 구체적 이유

**1. 프로덕션 준비 (Production-Ready)**
```
- 자동 최적화
- 빌드 최적화
- 이미지 최적화
- 번들 최적화
→ 별도 설정 없이 최상의 성능
```

**2. 풀스택 가능성**
```
- API Routes 지원
- 필요시 백엔드 일부 기능 통합 가능
- Middleware 지원
→ 유연한 아키텍처
```

**3. Docker 친화적**
```
- Standalone 빌드 지원
- 작은 Docker 이미지
- 효율적 배포
```

**4. TypeScript 기본 지원**
```
- 타입 안정성
- 자동 완성
- 에러 사전 감지
```

**5. 개발 경험**
```
- Fast Refresh (핫 리로딩)
- 자동 라우팅
- CSS Modules 기본 지원
```

---

## 🐳 Docker 통합

### docker-compose.yaml 구조

```yaml
services:
  pgvector:
    # PostgreSQL + Vector 확장
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]

  langchain-app:
    # FastAPI 백엔드
    build: .
    ports: ["8000:8000"]
    depends_on: [pgvector]
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}

  frontend:
    # Next.js 프론트엔드
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [langchain-app]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 컨테이너 간 통신

**브라우저 → 프론트엔드 → 백엔드:**

```javascript
// frontend/src/app/page.tsx

// 환경 변수로 백엔드 URL 설정
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// API 호출
const response = await fetch(`${API_URL}/api/chat/rag`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: userInput })
})
```

**CORS 설정:**

```python
# app/api_server.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발: 모두 허용
    # 프로덕션: ["https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📦 빌드 전략

### Multi-Stage Docker Build

**frontend/Dockerfile:**

```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: Runner (최종 이미지)
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production

# 최소한의 파일만 복사
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
```

**장점:**
```
1. 작은 최종 이미지
   - node_modules 제외
   - 빌드 도구 제외
   - 소스 코드 제외
   → 100MB 이하

2. 빠른 배포
   - 레이어 캐싱
   - 변경사항만 업데이트

3. 보안
   - 개발 의존성 제외
   - 최소한의 공격 표면
```

---

## 🔌 API 통신

### RESTful API 설계

**엔드포인트 구조:**

```
GET  /health              → 헬스 체크
POST /api/chat/rag        → RAG 모드 채팅
POST /api/chat/general    → 일반 모드 채팅
```

**요청/응답 형식:**

```typescript
// 요청 타입
interface ChatRequest {
  message: string
  session_id?: string
}

// 응답 타입
interface ChatResponse {
  answer: string
  sources: string[]
  timestamp: string
}
```

**프론트엔드에서 타입 안전하게 사용:**

```typescript
// frontend/src/app/page.tsx

const sendMessage = async (mode: 'rag' | 'general') => {
  const endpoint = mode === 'rag'
    ? '/api/chat/rag'
    : '/api/chat/general'

  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: inputValue })
  })

  const data: ChatResponse = await response.json()
  // TypeScript가 data의 구조를 알고 있음
}
```

---

## 🎯 상태 관리

### React Hooks 기반

**현재 구현:**

```typescript
// frontend/src/app/page.tsx

export default function Home() {
  // 메시지 목록
  const [messages, setMessages] = useState<Message[]>([])

  // 입력 값
  const [inputValue, setInputValue] = useState('')

  // 로딩 상태
  const [isLoading, setIsLoading] = useState(false)

  // 채팅 모드
  const [chatMode, setChatMode] = useState<'rag' | 'general'>('rag')

  // 출처 펼침/접힘 상태
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set())

  // ...
}
```

**상태 흐름:**

```
사용자 입력
    ↓
inputValue 업데이트
    ↓
전송 버튼 클릭
    ↓
isLoading = true
    ↓
API 호출
    ↓
응답 받음
    ↓
messages 배열에 추가
    ↓
isLoading = false
    ↓
UI 자동 업데이트
```

### 향후 확장 가능성

**상태 관리 라이브러리 추가 시:**

```
현재: React Hooks (충분)
  ↓
복잡도 증가 시
  ↓
옵션 1: Zustand (가벼움, 추천)
옵션 2: Redux Toolkit (강력, 복잡)
옵션 3: Jotai (원자적 상태)
```

---

## 🔄 개발 워크플로우

### 로컬 개발

**방법 1: Docker Compose (추천)**

```bash
# 모든 서비스 동시 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f frontend
docker-compose logs -f langchain-app

# 변경사항 반영
docker-compose restart frontend
```

**방법 2: 개별 실행 (빠른 개발)**

```bash
# 터미널 1: 백엔드
cd app
uvicorn api_server:app --reload

# 터미널 2: 프론트엔드
cd frontend
npm run dev

# 터미널 3: 데이터베이스
docker-compose up pgvector
```

### 개발 사이클

```
1. 코드 수정
   ↓
2. 자동 핫 리로딩
   ↓
3. 브라우저 자동 새로고침
   ↓
4. 변경사항 즉시 확인
   ↓
5. 반복
```

**핫 리로딩 작동:**

```
프론트엔드:
- Next.js Fast Refresh
- 상태 유지하며 컴포넌트만 업데이트
- 매우 빠름 (< 1초)

백엔드:
- Uvicorn --reload
- 파일 변경 감지
- 서버 자동 재시작
- 빠름 (1-2초)
```

---

## 🚀 배포 전략

### 개발 환경

```
docker-compose.yaml (개발용)
- 핫 리로딩 활성화
- 소스 코드 볼륨 마운트
- 디버그 모드
```

### 프로덕션 환경

**권장 구조:**

```
┌─────────────────────────────────────────┐
│          Nginx (Reverse Proxy)          │
│                                          │
│  /          → Next.js (3000)            │
│  /api/*     → FastAPI (8000)            │
│  /static/*  → Static Files              │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        ↓                 ↓
┌──────────────┐  ┌──────────────┐
│   Next.js    │  │   FastAPI    │
│  (Container) │  │  (Container) │
└──────────────┘  └──────────────┘
        ↓                 ↓
┌─────────────────────────────────┐
│         PostgreSQL + PGVector    │
└─────────────────────────────────┘
```

**docker-compose.prod.yaml:**

```yaml
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on: [frontend, langchain-app]

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=https://api.yourdomain.com

  langchain-app:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - POSTGRES_HOST=pgvector
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

### 스케일링

**수평 확장 (Horizontal Scaling):**

```yaml
services:
  frontend:
    deploy:
      replicas: 3  # 3개 인스턴스

  langchain-app:
    deploy:
      replicas: 2  # 2개 인스턴스

  pgvector:
    deploy:
      replicas: 1  # 데이터베이스는 단일 또는 클러스터
```

---

## 💡 아키텍처 결정 기록 (ADR)

### ADR-001: 프론트엔드 분리

**결정:**
```
FastAPI 내장 HTML → Next.js 분리
```

**이유:**
```
1. 관심사의 분리
2. 개발 경험 향상
3. 확장성 확보
4. 성능 최적화
```

**트레이드오프:**
```
장점:
+ 더 나은 개발 경험
+ 독립적 배포
+ 최신 도구 활용

단점:
- 초기 설정 복잡도
- Docker 이미지 증가
- 배포 복잡도 증가
```

**결론:**
```
장기적 이점이 단기적 복잡도를 상회
→ 프론트엔드 분리 진행
```

### ADR-002: Next.js vs 다른 프레임워크

**결정:**
```
Next.js 선택
```

**고려한 대안:**
```
1. Create React App: 더 이상 권장 안 됨
2. Vite + React: 좋지만 수동 설정 필요
3. Remix: 신생 프레임워크
```

**선택 이유:**
```
- 프로덕션 준비 완료
- 풍부한 생태계
- 자동 최적화
- TypeScript 지원
- Docker 친화적
```

### ADR-003: 모노레포 vs 분리 저장소

**결정:**
```
모노레포 유지 (단일 저장소에 frontend/ 폴더)
```

**이유:**
```
1. 간단한 프로젝트 구조
2. 버전 동기화 용이
3. docker-compose로 통합 관리
4. 배포 파이프라인 단순화
```

---

## ✅ 결론

### 달성한 것

1. **깔끔한 코드 분리**
   - 백엔드: Python/FastAPI
   - 프론트엔드: TypeScript/Next.js
   - 각자의 책임과 역할 명확

2. **개발 경험 향상**
   - 핫 리로딩
   - 타입 안정성
   - 컴포넌트 재사용
   - 빠른 피드백 루프

3. **프로덕션 준비**
   - Docker 컨테이너화
   - 최적화된 빌드
   - 확장 가능한 구조
   - 독립적 배포

4. **유지보수성**
   - 모듈화된 코드
   - 명확한 API 계약
   - 쉬운 디버깅
   - 테스트 용이

### 핵심 원칙

**"각자가 잘하는 것에 집중"**

```
FastAPI: 비즈니스 로직, 데이터 처리
Next.js: UI/UX, 사용자 경험
PGVector: 벡터 검색
OpenAI: 언어 모델

→ 각 도구를 최적의 용도로 사용
```

이 원칙을 따라 확장 가능하고
유지보수 가능한 시스템을 구축했습니다.

---

## 📚 참고

- **Next.js 공식 문서**: https://nextjs.org/docs
- **FastAPI CORS**: https://fastapi.tiangolo.com/tutorial/cors/
- **Docker Multi-Stage Build**: https://docs.docker.com/build/building/multi-stage/
- **TypeScript**: https://www.typescriptlang.org/


