# 🔑 OpenAI API 키 발급 완벽 가이드

## 📋 목차
1. [OpenAI 계정 생성](#1-openai-계정-생성)
2. [API 키 발급](#2-api-키-발급)
3. [결제 수단 등록](#3-결제-수단-등록)
4. [API 키 프로젝트에 적용](#4-api-키-프로젝트에-적용)
5. [테스트 및 확인](#5-테스트-및-확인)
6. [문제 해결](#6-문제-해결)

---

## 1. OpenAI 계정 생성

### Step 1-1: OpenAI 웹사이트 접속

🌐 **URL**: https://platform.openai.com/signup

### Step 1-2: 회원가입 방법 선택

다음 중 하나를 선택하여 가입:

- ✅ **이메일 주소로 가입** (추천)
- ✅ Google 계정으로 가입
- ✅ Microsoft 계정으로 가입
- ✅ Apple 계정으로 가입

### Step 1-3: 이메일 인증

1. 가입한 이메일로 인증 메일이 전송됩니다
2. "Verify email address" 버튼 클릭
3. 브라우저에서 자동으로 인증 완료

### Step 1-4: 프로필 정보 입력

- **이름** 입력
- **조직 이름** 입력 (선택사항, 개인용이면 본인 이름)
- 사용 목적 선택 (개인 프로젝트, 회사 업무 등)

---

## 2. API 키 발급

### Step 2-1: API 키 페이지 접속

로그인 후 다음 URL로 이동:

🌐 **URL**: https://platform.openai.com/api-keys

또는:

```
1. 로그인 후 우측 상단 프로필 아이콘 클릭
2. "API keys" 메뉴 선택
3. 또는 좌측 메뉴에서 "API keys" 클릭
```

### Step 2-2: 새 API 키 생성

```
┌─────────────────────────────────────────┐
│  API keys 페이지                        │
│                                         │
│  [+ Create new secret key] 버튼 클릭   │
└─────────────────────────────────────────┘
```

1. **"Create new secret key"** 버튼 클릭
2. API 키 이름 입력 (예: "langchain-chatbot-project")
3. **권한 설정** (선택사항):
   - `All` - 모든 권한 (기본값, 추천)
   - `Restricted` - 제한된 권한

4. **"Create secret key"** 버튼 클릭

### Step 2-3: API 키 복사 및 저장 ⚠️ 중요!

```
┌─────────────────────────────────────────────────────────┐
│  API key generated                                      │
│                                                         │
│  sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx          │
│                                                         │
│  [Copy] 버튼 클릭하여 복사                             │
│                                                         │
│  ⚠️  이 키는 다시 표시되지 않습니다!                   │
│     반드시 지금 안전한 곳에 저장하세요!                │
└─────────────────────────────────────────────────────────┘
```

**🔴 매우 중요**:
- API 키는 **한 번만** 표시됩니다
- 다시 볼 수 없으므로 **반드시 복사**해서 저장하세요
- 잃어버리면 새로 생성해야 합니다

**저장 위치 추천**:
- 메모장이나 텍스트 파일 (임시)
- 비밀번호 관리자 (추천)
- `.env` 파일 (프로젝트에 적용 시)

---

## 3. 결제 수단 등록

### ⚠️ 중요 사항

OpenAI API를 사용하려면 **결제 수단 등록이 필수**입니다.

- 무료 크레딧이 있어도 결제 수단 필요
- 신규 가입자: $5 무료 크레딧 제공 (3개월 유효)
- 기존 사용자: 유료 사용만 가능

### Step 3-1: 결제 페이지 접속

🌐 **URL**: https://platform.openai.com/settings/organization/billing/overview

또는:

```
1. 좌측 메뉴에서 "Settings" 클릭
2. "Billing" 탭 선택
3. "Payment methods" 메뉴 선택
```

### Step 3-2: 결제 수단 추가

```
┌─────────────────────────────────────────┐
│  Payment methods                        │
│                                         │
│  [+ Add payment method] 버튼 클릭      │
└─────────────────────────────────────────┘
```

**지원하는 결제 수단**:
- ✅ 신용카드 (Visa, Mastercard, Amex)
- ✅ 체크카드 (해외 결제 가능한 카드)

**필요한 정보**:
- 카드 번호
- 만료일 (MM/YY)
- CVC/CVV (카드 뒷면 3자리)
- 카드 소유자 이름
- 청구지 주소 (해외 주소 입력)

### Step 3-3: 사용 한도 설정 (선택사항)

```
Settings → Billing → Usage limits
```

**추천 설정** (과금 방지):
- **Hard limit**: $10 (월 최대 사용 금액)
- **Soft limit**: $5 (알림 금액)
- 이메일 알림 활성화

이렇게 설정하면:
- $5 사용 시 이메일 알림
- $10 도달 시 자동으로 API 차단
- 예상치 못한 과금 방지

---

## 4. API 키 프로젝트에 적용

### Step 4-1: .env 파일 생성

프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다:

```bash
# Windows (PowerShell)
New-Item -Path .env -ItemType File

# 또는 직접 생성:
# 1. 프로젝트 폴더에서 마우스 우클릭
# 2. "새로 만들기" → "텍스트 문서"
# 3. 파일명을 ".env"로 변경
```

### Step 4-2: API 키 입력

`.env` 파일을 열고 다음 내용을 입력:

```env
# OpenAI API 설정
OPENAI_API_KEY=sk-proj-여기에발급받은API키를붙여넣기

# PostgreSQL 설정 (기존)
POSTGRES_HOST=pgvector
POSTGRES_PORT=5432
POSTGRES_USER=langchain
POSTGRES_PASSWORD=langchain123
POSTGRES_DB=vectordb
```

**⚠️ 주의사항**:
- `=` 앞뒤에 공백 없이 입력
- API 키에 따옴표 없이 그대로 입력
- 실제 키로 교체: `sk-proj-xxxx...`

### Step 4-3: .gitignore 설정

`.env` 파일이 Git에 업로드되지 않도록 설정:

**`.gitignore` 파일에 추가** (이미 있을 수 있음):

```gitignore
# Environment variables
.env
.env.local
.env.*.local

# API Keys
*.key
secrets/
```

**🔴 매우 중요**:
- `.env` 파일을 절대로 Git에 커밋하지 마세요!
- GitHub에 업로드하면 API 키가 노출됩니다!
- 노출되면 즉시 키를 삭제하고 새로 발급받으세요!

---

## 5. 테스트 및 확인

### Step 5-1: API 키 유효성 간단 테스트

터미널에서 다음 명령어로 테스트 (선택사항):

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-proj-여기에키입력"
docker-compose run --rm langchain-app python -c "from openai import OpenAI; print('API Key OK!' if OpenAI().models.list() else 'Failed')"
```

### Step 5-2: 프로젝트에서 테스트

다음 단계에서 제공할 테스트 스크립트로 확인합니다.

---

## 6. 문제 해결

### ❌ "Incorrect API key provided"

**원인**:
- API 키를 잘못 복사함
- 공백이나 줄바꿈이 포함됨

**해결**:
1. API 키를 다시 확인
2. 공백 없이 정확히 복사
3. 안 되면 새 키 발급

### ❌ "You exceeded your current quota"

**원인**:
- 무료 크레딧 소진
- 결제 수단 미등록
- 사용 한도 초과

**해결**:
1. https://platform.openai.com/settings/organization/billing/overview 접속
2. 크레딧 잔액 확인
3. 결제 수단 등록 확인
4. 필요시 크레딧 충전 ($5~$50)

### ❌ "Rate limit exceeded"

**원인**:
- 너무 많은 요청을 빠르게 보냄
- 무료 티어의 제한

**해결**:
1. 요청 사이에 시간 간격 추가
2. 유료 플랜 업그레이드 고려
3. 잠시 기다렸다가 재시도

### ❌ 한국 카드가 거부됨

**원인**:
- 일부 카드사는 OpenAI 결제를 차단

**해결**:
1. 해외 결제 가능한 카드 사용
2. 카드사에 해외 결제 승인 요청
3. PayPal 연동 (일부 지역)
4. 다른 카드 시도

---

## 📊 크레딧 및 가격 정보

### 무료 크레딧

- **신규 가입자**: $5 무료 크레딧 (3개월 유효)
- **사용 후**: 유료로 전환 필요

### 권장 초기 충전 금액

- **테스트용**: $5 (충분함)
- **소규모 프로젝트**: $10~$20
- **정기 사용**: $50 이상

### 월 예상 비용 (참고)

**이 프로젝트의 예상 사용량**:

| 활동 | 월 사용 | 예상 비용 |
|------|---------|-----------|
| 테스트/개발 | 1,000회 대화 | $1~$2 |
| 소규모 사용 | 5,000회 대화 | $5~$10 |
| 중규모 사용 | 20,000회 대화 | $20~$40 |

**실제 비용은 사용량에 따라 다릅니다!**

---

## ✅ 발급 완료 체크리스트

다음 항목을 모두 완료했는지 확인하세요:

- [ ] OpenAI 계정 생성 완료
- [ ] 이메일 인증 완료
- [ ] API 키 발급 완료
- [ ] API 키를 안전한 곳에 저장
- [ ] 결제 수단 등록 완료
- [ ] 사용 한도 설정 (선택사항)
- [ ] `.env` 파일 생성
- [ ] `.env` 파일에 API 키 입력
- [ ] `.gitignore`에 `.env` 추가 확인

---

## 🎯 다음 단계

API 키 발급이 완료되었다면:

1. ✅ **Phase 1 시작**: OpenAI 연동 구현
2. ✅ **기본 챗봇 테스트**
3. ✅ **RAG 시스템 구축**

준비되셨으면 다음 단계로 진행하겠습니다! 🚀

---

## 🔗 유용한 링크

- 🌐 **OpenAI Platform**: https://platform.openai.com
- 🔑 **API Keys 관리**: https://platform.openai.com/api-keys
- 💳 **결제 설정**: https://platform.openai.com/settings/organization/billing
- 📊 **사용량 확인**: https://platform.openai.com/usage
- 📖 **가격 정보**: https://openai.com/api/pricing
- 📚 **API 문서**: https://platform.openai.com/docs

---

## 💡 보안 팁

1. **API 키 노출 방지**:
   - `.env` 파일을 Git에 커밋하지 마세요
   - 코드에 직접 하드코딩하지 마세요
   - 스크린샷이나 영상에 키가 보이지 않도록 주의

2. **키 관리**:
   - 주기적으로 키를 재발급하세요 (3~6개월)
   - 사용하지 않는 키는 삭제하세요
   - 프로젝트별로 다른 키를 사용하세요

3. **과금 방지**:
   - 사용 한도를 설정하세요
   - 이메일 알림을 활성화하세요
   - 정기적으로 사용량을 확인하세요

4. **키 노출 시 대응**:
   - 즉시 해당 키를 삭제하세요
   - 새 키를 발급받으세요
   - 비정상적인 사용이 있는지 확인하세요

---

문제가 있거나 추가 도움이 필요하면 언제든지 말씀해주세요! 😊

