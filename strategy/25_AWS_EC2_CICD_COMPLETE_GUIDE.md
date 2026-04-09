# AWS EC2 + GitHub Actions CICD 완전 가이드

## 📋 프로젝트 개요

**무엇을 만드는가?**
- FastAPI 기반 RAG 챗봇 API를 AWS EC2에 자동 배포하는 시스템

**왜 만드는가?**
- 코드를 GitHub에 푸시하면 자동으로 서버에 배포되어 즉시 사용 가능
- 수동 배포의 실수와 시간 낭비 방지
- 일관된 배포 프로세스로 안정성 향상

**기술 스택:**
- **GitHub Actions**: CI/CD 자동화
- **AWS EC2**: 서버 인프라
- **FastAPI**: Python 웹 프레임워크
- **Systemd**: 서비스 관리
- **Nginx**: 리버스 프록시

---

## 🏗️ 전체 구조 이해하기

### 1. 전체 흐름도

```
개발자 (로컬)
    ↓
코드 작성 및 수정
    ↓
git push origin main
    ↓
GitHub Repository
    ↓
GitHub Actions (자동 실행)
    ├─ 코드 체크아웃
    ├─ SSH 연결 설정
    ├─ EC2에 파일 전송 (rsync)
    ├─ EC2에서 배포 작업 실행
    │   ├─ Python 가상환경 설정
    │   ├─ 의존성 설치
    │   ├─ Systemd 서비스 설정
    │   └─ Nginx 설정
    └─ Health Check (배포 확인)
    ↓
AWS EC2 서버
    ├─ FastAPI 앱 (포트 8000)
    └─ Nginx (포트 80)
    ↓
외부 사용자 접근
```

### 2. 각 구성 요소의 역할

#### GitHub Actions
- **역할**: 자동화된 배포 파이프라인
- **하는 일**: 코드가 푸시되면 자동으로 EC2에 배포
- **왜 필요한가**: 수동 배포 대신 자동화로 시간 절약 및 실수 방지

#### AWS EC2
- **역할**: 실제 애플리케이션이 실행되는 서버
- **하는 일**: FastAPI 앱을 24/7 실행
- **왜 필요한가**: 클라우드 서버로 언제 어디서나 접근 가능

#### Systemd
- **역할**: 서비스 관리자 (백그라운드에서 앱 실행)
- **하는 일**: 서버 재부팅 시 자동으로 앱 시작, 앱 크래시 시 자동 재시작
- **왜 필요한가**: 수동으로 앱을 실행할 필요 없이 자동 관리

#### Nginx
- **역할**: 리버스 프록시 (중간 다리 역할)
- **하는 일**: 외부 요청(포트 80)을 내부 앱(포트 8000)으로 전달
- **왜 필요한가**:
  - 보안: 앱을 직접 노출하지 않고 Nginx를 통해 접근
  - SSL/HTTPS 설정 용이
  - 로드 밸런싱 가능

---

## 📁 EC2 서버 디렉토리 구조

### 전체 구조

```
/var/www/langchain/              ← 애플리케이션 루트
├── app/                         ← 실제 애플리케이션 코드
│   ├── api_server_refactored.py ← FastAPI 앱 시작점
│   ├── router/                  ← API 엔드포인트들
│   ├── services/                ← 비즈니스 로직
│   ├── models/                  ← AI 모델 관련
│   └── config/                  ← 설정 파일들
├── venv/                        ← Python 가상환경 (의존성 패키지들)
└── .env                         ← 환경 변수 (비밀번호, API 키 등)

/var/log/langchain/              ← 로그 파일들
├── access.log                   ← 앱 접근 로그
└── error.log                    ← 에러 로그

/etc/systemd/system/             ← 시스템 서비스 설정
└── langchain-api.service        ← FastAPI 앱을 서비스로 등록

/etc/nginx/sites-available/      ← Nginx 설정
└── langchain                    ← 리버스 프록시 설정
```

### 왜 이렇게 구조화했나요?

1. **`/var/www/langchain/`**: Linux에서 웹 애플리케이션의 표준 위치
2. **`app/` 폴더 분리**: 코드와 설정을 분리하여 관리 용이
3. **`venv/` 분리**: Python 패키지들을 독립적으로 관리
4. **`.env` 파일**: 민감한 정보(비밀번호 등)를 코드와 분리

---

## 🔄 배포 프로세스 상세 설명

### Step 1: GitHub에 코드 푸시

**개발자가 하는 일:**
```bash
git add .
git commit -m "새 기능 추가"
git push origin main
```

**무슨 일이 일어나는가?**
- GitHub 저장소에 코드가 업로드됨
- `main` 브랜치에 푸시되면 GitHub Actions가 자동으로 실행됨

### Step 2: GitHub Actions 실행

**자동으로 실행되는 단계들:**

#### 2-1. 코드 체크아웃
- GitHub에서 최신 코드를 가져옴

#### 2-2. SSH 연결 설정
- EC2 서버에 접속하기 위한 인증 설정
- SSH 키를 사용하여 안전하게 연결

#### 2-3. 파일 전송 (rsync)
- 로컬 `app/` 폴더의 내용을 EC2의 `/var/www/langchain/app/`로 전송
- 변경된 파일만 전송하여 효율적

**rsync가 하는 일:**
```
로컬: app/api_server_refactored.py
  ↓ (전송)
EC2: /var/www/langchain/app/api_server_refactored.py
```

### Step 3: EC2에서 배포 작업

**EC2 서버에서 자동으로 실행되는 작업들:**

#### 3-1. Python 가상환경 확인
- `/var/www/langchain/venv/` 폴더 확인
- 없으면 생성, 있으면 기존 것 사용

**가상환경이란?**
- 프로젝트별로 Python 패키지를 독립적으로 관리
- 다른 프로젝트와 패키지 충돌 방지

#### 3-2. 의존성 설치
- `requirements.txt`에 있는 패키지들을 설치
- 예: FastAPI, LangChain, OpenAI 등

#### 3-3. Systemd 서비스 설정
- FastAPI 앱을 시스템 서비스로 등록
- 서버 재부팅 시 자동 시작
- 앱 크래시 시 자동 재시작

**Systemd 서비스 파일 위치:**
```
/etc/systemd/system/langchain-api.service
```

**서비스 파일 내용 (간단히):**
```ini
[Service]
WorkingDirectory=/var/www/langchain
ExecStart=/var/www/langchain/venv/bin/uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000
Restart=always
```

**이것이 하는 일:**
- FastAPI 앱을 포트 8000에서 실행
- 앱이 종료되면 자동으로 재시작

#### 3-4. Nginx 설정
- 외부 요청(포트 80)을 내부 앱(포트 8000)으로 전달

**Nginx 설정 위치:**
```
/etc/nginx/sites-available/langchain
```

**설정 내용 (간단히):**
```nginx
server {
    listen 80;
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

**이것이 하는 일:**
- 외부에서 `http://EC2_IP/`로 접속하면
- 내부의 `http://127.0.0.1:8000/`로 요청을 전달

### Step 4: Health Check

**배포가 성공했는지 확인:**
- `http://EC2_IP/health` 엔드포인트에 요청
- 정상 응답이 오면 배포 성공

---

## 🔍 핵심 개념 이해하기

### 1. 포트(Port)란?

**비유로 이해하기:**
- 서버는 아파트, 포트는 방 번호
- 각 서비스는 다른 방(포트)에서 실행

**우리 프로젝트:**
- **포트 8000**: FastAPI 앱 (내부용)
- **포트 80**: Nginx (외부 접근용)

**왜 이렇게 하나요?**
- 보안: 앱을 직접 노출하지 않음
- 유연성: 나중에 여러 앱을 같은 서버에서 실행 가능

### 2. 리버스 프록시(Reverse Proxy)란?

**일반 프록시:**
```
사용자 → 프록시 → 인터넷
```

**리버스 프록시:**
```
사용자 → Nginx → FastAPI 앱
```

**Nginx의 역할:**
- 사용자의 요청을 받아서
- 내부 앱으로 전달하고
- 응답을 다시 사용자에게 전달

**왜 필요한가?**
- 보안 강화
- SSL/HTTPS 설정 용이
- 로드 밸런싱 가능

### 3. Systemd 서비스란?

**일반 실행:**
```bash
python app.py  # 터미널을 닫으면 앱도 종료됨
```

**Systemd 서비스:**
```bash
sudo systemctl start langchain-api.service  # 백그라운드에서 실행
```

**장점:**
- 터미널을 닫아도 계속 실행
- 서버 재부팅 시 자동 시작
- 크래시 시 자동 재시작

### 4. 가상환경(Virtual Environment)이란?

**문제 상황:**
- 프로젝트 A는 Python 3.10 필요
- 프로젝트 B는 Python 3.12 필요
- 같은 서버에서 충돌 발생

**해결책: 가상환경**
- 각 프로젝트마다 독립적인 Python 환경
- 패키지 충돌 방지

**우리 프로젝트:**
```
/var/www/langchain/venv/  ← 이 프로젝트만의 Python 환경
```

---

## 🛠️ 실제 배포 흐름 (단계별)

### Phase 1: 준비 단계

**1. EC2 인스턴스 생성**
- AWS 콘솔에서 EC2 인스턴스 생성
- Ubuntu 24.04 LTS 사용

**2. 보안 그룹 설정**
- 포트 22 (SSH): GitHub Actions에서 접속용
- 포트 80 (HTTP): 외부 사용자 접속용

**3. SSH 키 생성**
- EC2 접속용 키 페어 생성
- GitHub Secrets에 등록

### Phase 2: 초기 설정 (한 번만)

**EC2 서버에 SSH 접속 후:**

```bash
# 1. 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 2. 필수 패키지 설치
sudo apt install -y python3 python3-venv nginx

# 3. 디렉토리 생성
sudo mkdir -p /var/www/langchain /var/log/langchain
sudo chown -R ubuntu:ubuntu /var/www/langchain /var/log/langchain
```

**왜 이렇게 하나요?**
- `/var/www/`: 웹 애플리케이션 표준 위치
- `/var/log/`: 로그 파일 저장 위치
- `chown`: 파일 소유권 설정 (ubuntu 사용자가 사용 가능하도록)

### Phase 3: GitHub Actions 설정

**GitHub Secrets에 등록해야 할 것들:**

1. **EC2_HOST**: EC2 서버의 IP 주소 또는 도메인
2. **EC2_USER**: EC2 사용자 이름 (보통 `ubuntu`)
3. **EC2_SSH_KEY**: EC2 접속용 SSH 개인 키
4. **OPENAI_API_KEY**: OpenAI API 키
5. **POSTGRES_PASSWORD**: 데이터베이스 비밀번호

**왜 Secrets에 저장하나요?**
- 민감한 정보를 코드에 직접 넣지 않음
- 보안 강화

### Phase 4: 자동 배포 (이후 계속)

**개발자가 하는 일:**
```bash
git push origin main
```

**자동으로 일어나는 일:**

1. **GitHub Actions 실행**
   - 코드 체크아웃
   - SSH 연결
   - 파일 전송

2. **EC2에서 자동 실행**
   - 가상환경 확인/생성
   - 의존성 설치
   - 서비스 재시작

3. **Health Check**
   - 배포 성공 확인

**전체 소요 시간:** 약 5-10분

---

## 🔐 보안 구조 이해하기

### 1. 포트 접근 제어

**포트 8000 (FastAPI 앱):**
- 외부에서 직접 접근 불가
- 오직 서버 내부(127.0.0.1)에서만 접근 가능
- Nginx를 통해서만 접근 가능

**포트 80 (Nginx):**
- 외부에서 접근 가능
- 사용자가 웹 브라우저로 접속

**왜 이렇게 하나요?**
- FastAPI 앱을 직접 노출하지 않아 보안 강화
- Nginx에서 추가 보안 설정 가능 (Rate Limiting 등)

### 2. 환경 변수 관리

**`.env` 파일:**
```
OPENAI_API_KEY=sk-...
POSTGRES_PASSWORD=비밀번호
```

**위치:**
```
/var/www/langchain/.env
```

**권한:**
```bash
chmod 600 .env  # 소유자만 읽기/쓰기 가능
```

**왜 이렇게 하나요?**
- 민감한 정보를 코드와 분리
- 환경별로 다른 설정 사용 가능 (개발/프로덕션)

### 3. SSH 키 인증

**일반 비밀번호 인증:**
- 비밀번호 탈취 위험

**SSH 키 인증:**
- 공개키/개인키 쌍 사용
- 더 안전한 인증 방식

---

## 📊 데이터 흐름 이해하기

### 사용자 요청 처리 과정

```
1. 사용자가 브라우저에서 접속
   http://EC2_IP/health
   ↓
2. AWS Security Group
   포트 80 허용 확인
   ↓
3. Nginx (포트 80)
   요청을 받아서 내부로 전달
   ↓
4. FastAPI 앱 (포트 8000)
   요청 처리 및 응답 생성
   ↓
5. Nginx
   응답을 사용자에게 전달
   ↓
6. 사용자 브라우저
   결과 표시
```

### 왜 이렇게 복잡하게 하나요?

**단순한 방법:**
```
사용자 → FastAPI 앱 (포트 8000 직접 노출)
```

**문제점:**
- 보안 취약
- SSL 설정 어려움
- 여러 앱 실행 어려움

**우리의 방법:**
```
사용자 → Nginx (포트 80) → FastAPI 앱 (포트 8000)
```

**장점:**
- 보안 강화
- SSL 설정 용이
- 여러 앱 실행 가능
- 로드 밸런싱 가능

---

## 🎯 핵심 포인트 정리

### 1. 왜 GitHub Actions를 사용하나요?

**수동 배포의 문제:**
- 매번 SSH 접속 필요
- 명령어 실수 가능
- 시간 소모

**자동 배포의 장점:**
- 코드 푸시만 하면 자동 배포
- 일관된 배포 프로세스
- 시간 절약

### 2. 왜 Systemd를 사용하나요?

**일반 실행의 문제:**
- 터미널을 닫으면 앱 종료
- 서버 재부팅 시 수동 시작 필요

**Systemd의 장점:**
- 백그라운드에서 자동 실행
- 서버 재부팅 시 자동 시작
- 크래시 시 자동 재시작

### 3. 왜 Nginx를 사용하나요?

**직접 노출의 문제:**
- 보안 취약
- SSL 설정 어려움

**Nginx의 장점:**
- 보안 강화
- SSL 설정 용이
- 여러 앱 실행 가능

### 4. 왜 가상환경을 사용하나요?

**전역 설치의 문제:**
- 패키지 충돌
- 버전 관리 어려움

**가상환경의 장점:**
- 프로젝트별 독립 환경
- 패키지 충돌 방지
- 버전 관리 용이

---

## 🚀 실제 사용 시나리오

### 시나리오 1: 새 기능 추가 후 배포

**1. 로컬에서 개발**
```bash
# 코드 수정
vim app/router/chat_router.py
```

**2. 테스트**
```bash
# 로컬에서 테스트
python -m uvicorn app.api_server_refactored:app --reload
```

**3. GitHub에 푸시**
```bash
git add .
git commit -m "새 기능 추가"
git push origin main
```

**4. 자동 배포**
- GitHub Actions가 자동으로 실행
- 약 5-10분 후 배포 완료

**5. 확인**
```bash
curl http://EC2_IP/health
```

### 시나리오 2: 서버 재부팅 후

**자동으로 일어나는 일:**
1. EC2 서버 재부팅
2. Systemd가 자동으로 FastAPI 앱 시작
3. Nginx도 자동으로 시작
4. 서비스 정상 작동

**개발자가 할 일:**
- 없음! (자동으로 처리됨)

---

## 🔧 문제 해결 가이드

### 문제 1: 배포가 실패해요

**확인 사항:**
1. GitHub Secrets가 올바르게 설정되었는가?
2. EC2 서버가 실행 중인가?
3. Security Group에서 포트 22가 허용되었는가?

**해결 방법:**
- GitHub Actions 로그 확인
- EC2 서버에 직접 SSH 접속하여 확인

### 문제 2: 서비스가 시작되지 않아요

**확인 사항:**
```bash
# EC2 서버에서 실행
sudo systemctl status langchain-api.service
```

**일반적인 원인:**
- Python 가상환경 문제
- 의존성 설치 실패
- 환경 변수 누락

### 문제 3: 외부에서 접속이 안 돼요

**확인 사항:**
1. Security Group에서 포트 80이 허용되었는가?
2. Nginx가 실행 중인가?
3. FastAPI 앱이 실행 중인가?

**확인 명령어:**
```bash
# EC2 서버에서 실행
sudo systemctl status nginx
sudo systemctl status langchain-api.service
curl http://localhost:8000/health
```

---

## 📚 학습 체크리스트

이 가이드를 읽은 후 다음을 이해했는지 확인하세요:

- [ ] GitHub Actions가 자동 배포를 어떻게 하는지 이해
- [ ] EC2 서버의 디렉토리 구조를 이해
- [ ] Systemd가 왜 필요한지 이해
- [ ] Nginx가 왜 필요한지 이해
- [ ] 포트 80과 8000의 차이를 이해
- [ ] 가상환경이 왜 필요한지 이해
- [ ] 전체 배포 흐름을 이해

---

## 🎓 다음 단계 학습 과제

1. **SSL/HTTPS 설정**: Let's Encrypt로 무료 SSL 인증서 설정
2. **도메인 연결**: EC2 IP 대신 도메인 사용
3. **모니터링**: 서비스 상태 모니터링 도구 추가
4. **백업 전략**: 데이터베이스 및 파일 백업 자동화
5. **로드 밸런싱**: 여러 EC2 인스턴스로 트래픽 분산

---

## 💡 실무 팁

### 1. 배포 전 확인사항

- 로컬에서 테스트 완료
- 환경 변수 확인
- 의존성 변경사항 확인

### 2. 배포 후 확인사항

- Health Check 성공 여부
- 서비스 로그 확인
- 에러 로그 확인

### 3. 문제 발생 시

- GitHub Actions 로그 먼저 확인
- EC2 서버 로그 확인
- 단계별로 차근차근 확인

---

## 📝 요약

**전체 구조:**
```
GitHub (코드 저장)
  → GitHub Actions (자동 배포)
    → EC2 서버
      → Systemd (서비스 관리)
        → FastAPI 앱 (포트 8000)
      → Nginx (리버스 프록시, 포트 80)
        → 외부 사용자
```

**핵심 개념:**
- **CI/CD**: 코드 푸시 → 자동 배포
- **Systemd**: 백그라운드 서비스 관리
- **Nginx**: 리버스 프록시 (보안 + 유연성)
- **가상환경**: 프로젝트별 독립 환경

**왜 이렇게 설계했나요?**
- 자동화로 시간 절약
- 보안 강화
- 안정성 향상
- 확장성 확보

이제 AWS에 앱을 배포하는 전체 과정을 이해하셨습니다! 🎉

