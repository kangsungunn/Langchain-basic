# FastAPI EC2 CI/CD 배포 가이드

## 📋 프로젝트 개요

이 가이드는 FastAPI 기반 RAG 챗봇 애플리케이션을 AWS EC2에 자동 배포하는 CI/CD 파이프라인 구축 과정을 설명합니다.

### 기술 스택
- **백엔드**: FastAPI (Python 3.11)
- **배포 플랫폼**: AWS EC2 (Ubuntu 24.04)
- **CI/CD**: GitHub Actions
- **웹 서버**: Nginx (리버스 프록시)
- **프로세스 관리**: Systemd
- **벡터 DB**: Neon PostgreSQL (PGVector)

### Table of Contents
1. [사전 준비](#1-사전-준비)
2. [EC2 초기 설정](#2-ec2-초기-설정)
3. [GitHub Secrets 설정](#3-github-secrets-설정)
4. [GitHub Actions 워크플로우 확인](#4-github-actions-워크플로우-확인)
5. [자동 배포 테스트](#5-자동-배포-테스트)
6. [배포 확인 및 모니터링](#6-배포-확인-및-모니터링)
7. [트러블슈팅](#7-트러블슈팅)

---

## 1. 사전 준비

### 1.1 필요한 파일 및 정보

배포를 시작하기 전에 다음 정보를 준비해야 합니다:

1. **EC2 인스턴스 정보**
   - 호스트: `ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com`
   - 사용자: `ubuntu`
   - SSH 키: `kang.pem`

2. **환경 변수**
   - `OPENAI_API_KEY`: OpenAI API 키
   - `POSTGRES_HOST`: Neon PostgreSQL 호스트
   - `POSTGRES_PASSWORD`: Neon PostgreSQL 비밀번호
   - 기타 데이터베이스 설정

3. **GitHub Repository**
   - 저장소 URL
   - GitHub Actions 접근 권한

### 1.2 프로젝트 구조 확인

현재 프로젝트의 주요 파일 구조:

```
langchain/
├── app/
│   ├── api_server_refactored.py  # 메인 FastAPI 엔트리 포인트
│   ├── router/                   # API 라우터
│   ├── services/                 # 비즈니스 로직
│   └── config/                   # 설정 관리
├── .github/
│   └── workflows/
│       └── deploy.yml            # GitHub Actions 워크플로우
├── requirements.txt              # Python 의존성
└── scripts/
    └── deploy.sh                 # 로컬 배포 스크립트
```

---

## 2. EC2 초기 설정

### 2.1 EC2 접속

로컬 터미널에서 EC2에 SSH로 접속합니다:

```bash
ssh -i "kang.pem" ubuntu@ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com
```

### 2.2 시스템 패키지 설치

EC2에서 다음 명령어를 실행하여 필수 패키지를 설치합니다:

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx curl
```

**왜 이렇게 하나요?**
- `python3.11`: Python 3.11 인터프리터
- `python3.11-venv`: 가상 환경 생성 도구
- `python3-pip`: Python 패키지 관리자
- `git`: 코드 저장소 클론을 위해 필요
- `nginx`: 웹 서버 (리버스 프록시 역할)
- `curl`: 헬스 체크 및 테스트용

### 2.3 애플리케이션 디렉토리 생성

```bash
# 애플리케이션 디렉토리 생성
sudo mkdir -p /var/www/langchain
sudo chown -R ubuntu:ubuntu /var/www/langchain

# 로그 디렉토리 생성
sudo mkdir -p /var/log/langchain
sudo chown -R ubuntu:ubuntu /var/log/langchain
```

**디렉토리 구조 설명:**
- `/var/www/langchain`: 애플리케이션 코드가 배포되는 위치
- `/var/log/langchain`: 애플리케이션 로그 저장 위치

### 2.4 Python 가상 환경 설정

```bash
cd /var/www/langchain

# 가상 환경 생성
python3.11 -m venv venv

# 가상 환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip
```

**가상 환경을 사용하는 이유:**
- 프로젝트별 의존성 격리
- 시스템 Python과 충돌 방지
- 배포 환경 일관성 유지

### 2.5 환경 변수 파일 생성

프로덕션 환경 변수를 `.env` 파일로 생성합니다:

```bash
cat > /var/www/langchain/.env << 'EOF'
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# PostgreSQL (Neon)
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=your_password_here
POSTGRES_HOST=ep-mute-boat-a1sgw2su-pooler.ap-southeast-1.aws.neon.tech
POSTGRES_PORT=5432
POSTGRES_DB=neondb
POSTGRES_SSLMODE=require

# Model
LLM_PROVIDER=openai
MIDM_MODEL_PATH=/var/www/langchain/models/midm

# Server
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production

# PGVector Collection
PGVECTOR_COLLECTION=langchain_knowledge_base
EOF

# 보안을 위해 권한 설정 (소유자만 읽기/쓰기 가능)
chmod 600 /var/www/langchain/.env
```

**중요:** 실제 값으로 `.env` 파일을 편집해야 합니다:

```bash
nano /var/www/langchain/.env
```

### 2.6 Systemd 서비스 생성

FastAPI 애플리케이션을 Systemd 서비스로 등록하여 자동 시작 및 재시작을 설정합니다:

```bash
sudo tee /etc/systemd/system/langchain-api.service > /dev/null << 'EOF'
[Unit]
Description=LangChain FastAPI Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/var/www/langchain
Environment="PATH=/var/www/langchain/venv/bin"
EnvironmentFile=/var/www/langchain/.env
ExecStart=/var/www/langchain/venv/bin/uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=append:/var/log/langchain/access.log
StandardError=append:/var/log/langchain/error.log

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable langchain-api.service
```

**설정 설명:**
- `Type=simple`: 단순 실행 서비스
- `User=ubuntu`: ubuntu 사용자로 실행
- `WorkingDirectory`: 작업 디렉토리
- `EnvironmentFile`: 환경 변수 파일 로드
- `ExecStart`: uvicorn으로 FastAPI 앱 실행
- `--workers 2`: 워커 프로세스 수 (CPU 코어에 맞게 조정)
- `Restart=always`: 항상 재시작
- `StandardOutput/StandardError`: 로그 파일로 출력

### 2.7 Nginx 리버스 프록시 설정

Nginx를 리버스 프록시로 설정하여 FastAPI 애플리케이션에 요청을 전달합니다:

```bash
sudo tee /etc/nginx/sites-available/langchain > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# 심볼릭 링크 생성
sudo ln -sf /etc/nginx/sites-available/langchain /etc/nginx/sites-enabled/

# 기본 사이트 비활성화
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
sudo systemctl enable nginx
```

**리버스 프록시를 사용하는 이유:**
- 포트 80(HTTP)에서 외부 접근 가능
- SSL/TLS 종료 가능 (HTTPS 설정 시)
- 로드 밸런싱 및 캐싱 가능
- 보안 강화 (FastAPI는 내부 포트만 사용)

### 2.8 방화벽 설정

UFW(Uncomplicated Firewall)를 설정하여 필요한 포트만 열어둡니다:

```bash
# SSH 허용
sudo ufw allow 22/tcp

# HTTP/HTTPS 허용
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 방화벽 활성화
echo "y" | sudo ufw enable

# 상태 확인
sudo ufw status
```

**보안 고려사항:**
- 포트 8000은 외부에 노출하지 않음 (Nginx가 프록시)
- SSH(22)는 필수이지만, 가능하면 IP 제한 권장

### 2.9 최초 코드 배포

GitHub에서 코드를 클론하고 의존성을 설치합니다:

```bash
cd /var/www/langchain

# GitHub에서 클론 (실제 저장소 URL로 변경)
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .

# 가상 환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 서비스 시작
sudo systemctl start langchain-api.service

# 서비스 상태 확인
sudo systemctl status langchain-api.service

# 헬스 체크
curl http://localhost:8000/health
```

**의존성 설치 시간:**
- `requirements.txt`에 따라 5-10분 소요될 수 있습니다
- 특히 `torch`, `transformers` 같은 대용량 패키지는 시간이 걸립니다

---

## 3. GitHub Secrets 설정

GitHub Actions가 EC2에 배포하기 위해 필요한 시크릿을 설정합니다.

### 3.1 GitHub Repository 접속

1. GitHub 저장소로 이동
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 클릭

### 3.2 필요한 Secrets 추가

다음 시크릿들을 하나씩 추가합니다:

#### 3.2.1 EC2_HOST

```
Name: EC2_HOST
Value: ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com
```

#### 3.2.2 EC2_USER

```
Name: EC2_USER
Value: ubuntu
```

#### 3.2.3 EC2_SSH_KEY

로컬에서 SSH 키 파일의 전체 내용을 복사합니다:

**PowerShell에서:**
```powershell
Get-Content kang.pem | Out-String
```

**Git Bash/Linux에서:**
```bash
cat kang.pem
```

출력된 전체 내용 (-----BEGIN RSA PRIVATE KEY----- 부터 -----END RSA PRIVATE KEY----- 까지)을 복사하여:

```
Name: EC2_SSH_KEY
Value: (복사한 전체 내용)
```

**중요:** 개행 문자(`\n`)가 포함되어야 합니다. 전체 키 내용을 그대로 복사하세요.

#### 3.2.4 OPENAI_API_KEY

```
Name: OPENAI_API_KEY
Value: sk-... (실제 OpenAI API 키)
```

#### 3.2.5 POSTGRES_PASSWORD (선택사항)

환경 변수 업데이트에 사용할 수 있습니다:

```
Name: POSTGRES_PASSWORD
Value: (Neon PostgreSQL 비밀번호)
```

### 3.3 Secrets 확인

모든 Secrets가 추가되었는지 확인:

- ✅ EC2_HOST
- ✅ EC2_USER
- ✅ EC2_SSH_KEY
- ✅ OPENAI_API_KEY
- ✅ POSTGRES_PASSWORD (선택)

---

## 4. GitHub Actions 워크플로우 확인

### 4.1 워크플로우 파일 위치

워크플로우 파일은 `.github/workflows/deploy.yml`에 있습니다.

### 4.2 워크플로우 동작 원리

```yaml
name: Deploy to EC2

on:
  push:
    branches:
      - main  # main 브랜치에 푸시될 때 자동 실행
  workflow_dispatch:  # 수동 실행 가능
```

**트리거 조건:**
- `push` to `main`: main 브랜치에 코드가 푸시되면 자동 실행
- `workflow_dispatch`: GitHub Actions UI에서 수동 실행 가능

### 4.3 배포 단계 설명

워크플로우는 다음 단계로 구성됩니다:

1. **Checkout code**: GitHub에서 코드 체크아웃
2. **Setup SSH**: SSH 키 설정
3. **Add EC2 to known hosts**: SSH 호스트 키 등록
4. **Deploy to EC2**: EC2에 배포
   - Git pull로 최신 코드 가져오기
   - 가상 환경 활성화
   - 의존성 설치
   - Systemd 서비스 재시작
5. **Health Check**: 배포 후 헬스 체크
6. **Notify Deployment Status**: 배포 상태 알림

### 4.4 워크플로우 파일 수정 (필요시)

저장소 URL이 다른 경우 `.github/workflows/deploy.yml` 파일을 수정해야 합니다:

```yaml
# 52번째 줄 근처
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .
```

실제 저장소 URL로 변경하세요.

---

## 5. 자동 배포 테스트

### 5.1 코드 변경 및 푸시

로컬에서 코드를 수정하고 GitHub에 푸시합니다:

```bash
# 변경사항 스테이징
git add .

# 커밋
git commit -m "feat: setup CI/CD deployment"

# 푸시 (main 브랜치에)
git push origin main
```

### 5.2 GitHub Actions 실행 확인

1. GitHub 저장소로 이동
2. **Actions** 탭 클릭
3. **Deploy to EC2** 워크플로우가 실행되는지 확인
4. 실행 중인 워크플로우를 클릭하여 상세 로그 확인

**성공 시:**
- 모든 단계에 ✅ 표시
- "Deployment successful!" 메시지
- Health check 통과

**실패 시:**
- ❌ 표시된 단계 확인
- 로그에서 에러 메시지 확인
- [트러블슈팅](#7-트러블슈팅) 섹션 참고

### 5.3 배포 시간

일반적으로 배포에 소요되는 시간:
- 코드 체크아웃: ~10초
- SSH 설정: ~5초
- Git pull: ~5초
- 의존성 설치: ~5-10분 (변경사항이 있는 경우)
- 서비스 재시작: ~10초
- 헬스 체크: ~5초

**총 소요 시간:** 약 5-15분 (의존성 설치 여부에 따라 다름)

---

## 6. 배포 확인 및 모니터링

### 6.1 API 엔드포인트 확인

배포가 완료되면 다음 엔드포인트로 접근할 수 있습니다:

```bash
# 루트 엔드포인트 (API 정보)
curl http://ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com/

# 헬스 체크
curl http://ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com/health

# API 문서
# 브라우저에서 접근: http://ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com/docs
```

### 6.2 주요 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/` | GET | API 정보 |
| `/health` | GET | 헬스 체크 |
| `/docs` | GET | Swagger UI 문서 |
| `/api/chat/rag` | POST | RAG 채팅 |
| `/api/chat/general` | POST | 일반 채팅 |
| `/api/chat` | POST | 레거시 엔드포인트 |

### 6.3 로그 모니터링

EC2에 SSH 접속하여 로그를 확인합니다:

```bash
# Systemd 서비스 로그 (실시간)
sudo journalctl -u langchain-api.service -f

# 최근 100줄 로그
sudo journalctl -u langchain-api.service -n 100

# 특정 시간 이후 로그
sudo journalctl -u langchain-api.service --since "1 hour ago"

# 애플리케이션 로그 파일
tail -f /var/log/langchain/access.log
tail -f /var/log/langchain/error.log

# Nginx 로그
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 6.4 서비스 상태 확인

```bash
# 서비스 상태
sudo systemctl status langchain-api.service

# 서비스 활성화 여부
sudo systemctl is-enabled langchain-api.service

# 프로세스 확인
ps aux | grep uvicorn

# 포트 리스닝 확인
sudo netstat -tlnp | grep 8000
```

### 6.5 모니터링 스크립트

로컬에서 `scripts/monitor.sh`를 실행하여 원격 모니터링:

```bash
# 스크립트에 실행 권한 부여 (최초 1회)
chmod +x scripts/monitor.sh

# 실행
./scripts/monitor.sh
```

---

## 7. 트러블슈팅

### 7.1 서비스가 시작되지 않는 경우

**증상:**
```bash
sudo systemctl status langchain-api.service
# 상태: failed 또는 inactive
```

**원인 분석:**
1. 의존성 누락
2. 포트 충돌
3. 권한 문제
4. 환경 변수 오류

**해결 방법:**

```bash
# 1. 로그 확인
sudo journalctl -u langchain-api.service -n 50

# 2. 의존성 재설치
cd /var/www/langchain
source venv/bin/activate
pip install -r requirements.txt

# 3. 포트 확인
sudo lsof -i :8000
# 다른 프로세스가 사용 중이면 종료

# 4. 권한 확인
ls -la /var/www/langchain
sudo chown -R ubuntu:ubuntu /var/www/langchain

# 5. 환경 변수 확인
cat /var/www/langchain/.env
# 필수 변수가 모두 설정되어 있는지 확인

# 6. 수동 실행 테스트
cd /var/www/langchain
source venv/bin/activate
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000
# 에러 메시지 확인
```

### 7.2 GitHub Actions 배포 실패

**증상:**
- GitHub Actions에서 ❌ 표시
- SSH 연결 실패 또는 배포 단계 실패

**원인 분석:**
1. SSH 키 형식 오류
2. EC2 호스트 정보 오류
3. Git 저장소 URL 오류
4. 권한 문제

**해결 방법:**

```bash
# 1. SSH 키 확인
# EC2_SSH_KEY에 전체 키 내용이 포함되어 있는지 확인
# 개행 문자가 포함되어야 함

# 2. SSH 연결 테스트 (로컬에서)
ssh -i "kang.pem" ubuntu@ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com "echo 'test'"

# 3. GitHub Secrets 재확인
# - EC2_HOST: 정확한 호스트명
# - EC2_USER: ubuntu
# - EC2_SSH_KEY: 전체 키 내용

# 4. 워크플로우 파일의 저장소 URL 확인
# .github/workflows/deploy.yml의 52번째 줄
```

### 7.3 Nginx 502 Bad Gateway

**증상:**
```bash
curl http://ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com/health
# 502 Bad Gateway
```

**원인 분석:**
1. FastAPI 서비스가 실행되지 않음
2. 포트 불일치
3. Nginx 설정 오류

**해결 방법:**

```bash
# 1. FastAPI 서비스 상태 확인
sudo systemctl status langchain-api.service

# 2. 포트 리스닝 확인
sudo netstat -tlnp | grep 8000
# 127.0.0.1:8000에서 리스닝해야 함

# 3. Nginx 설정 테스트
sudo nginx -t

# 4. Nginx 재시작
sudo systemctl restart nginx

# 5. Nginx 로그 확인
sudo tail -f /var/log/nginx/error.log
```

### 7.4 의존성 설치 실패

**증상:**
```bash
pip install -r requirements.txt
# 에러 발생
```

**원인 분석:**
1. 네트워크 문제
2. 패키지 버전 충돌
3. 시스템 라이브러리 누락

**해결 방법:**

```bash
# 1. pip 업그레이드
pip install --upgrade pip

# 2. 시스템 라이브러리 설치
sudo apt install -y build-essential python3-dev

# 3. 개별 패키지 설치 (에러 발생 패키지)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 4. requirements.txt 수정 (버전 호환성)
# 특정 패키지 버전을 고정
```

### 7.5 환경 변수 오류

**증상:**
- 애플리케이션이 시작되지만 API 호출 시 에러
- 데이터베이스 연결 실패

**원인 분석:**
1. `.env` 파일 누락 또는 오류
2. 환경 변수 값 오류

**해결 방법:**

```bash
# 1. .env 파일 확인
cat /var/www/langchain/.env

# 2. 환경 변수 테스트
cd /var/www/langchain
source venv/bin/activate
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"

# 3. Systemd 서비스의 EnvironmentFile 확인
sudo systemctl cat langchain-api.service | grep EnvironmentFile

# 4. 서비스 재시작
sudo systemctl restart langchain-api.service
```

---

## 8. 배포 프로세스 요약

### 8.1 전체 배포 플로우

```
로컬 개발
    ↓
git commit & push
    ↓
GitHub Repository (main 브랜치)
    ↓
GitHub Actions 트리거
    ↓
SSH로 EC2 접속
    ↓
Git pull (최신 코드)
    ↓
가상 환경 활성화
    ↓
의존성 설치/업데이트
    ↓
Systemd 서비스 재시작
    ↓
헬스 체크
    ↓
배포 완료 ✅
```

### 8.2 배포 체크리스트

**초기 설정 (최초 1회):**
- [ ] EC2 접속 확인
- [ ] 시스템 패키지 설치
- [ ] 디렉토리 구조 생성
- [ ] 가상 환경 설정
- [ ] `.env` 파일 생성
- [ ] Systemd 서비스 생성
- [ ] Nginx 설정
- [ ] 방화벽 설정
- [ ] 최초 코드 배포

**GitHub 설정:**
- [ ] GitHub Secrets 추가
- [ ] 워크플로우 파일 확인
- [ ] 저장소 URL 확인

**배포 테스트:**
- [ ] 코드 푸시
- [ ] GitHub Actions 실행 확인
- [ ] 배포 성공 확인
- [ ] API 엔드포인트 테스트

---

## 9. 학습 정리

### 9.1 배운 기술

1. **CI/CD 파이프라인 구축**
   - GitHub Actions를 사용한 자동 배포
   - SSH를 통한 원격 배포
   - 헬스 체크 및 자동 롤백

2. **서버 관리**
   - Systemd 서비스 관리
   - Nginx 리버스 프록시 설정
   - 로그 관리 및 모니터링

3. **보안**
   - 환경 변수 관리
   - SSH 키 관리
   - 방화벽 설정

### 9.2 비즈니스 인사이트

1. **자동화의 중요성**
   - 수동 배포는 실수와 시간 낭비
   - CI/CD로 배포 시간 단축 및 안정성 향상

2. **모니터링의 필요성**
   - 로그 모니터링으로 문제 조기 발견
   - 헬스 체크로 서비스 상태 확인

3. **인프라 관리**
   - 코드와 인프라 설정의 분리
   - 환경 변수로 설정 관리

---

## 10. 다음 학습 과제

### 10.1 단기 개선 사항

1. **SSL/TLS 설정**
   - Let's Encrypt로 HTTPS 적용
   - 도메인 연결

2. **로깅 개선**
   - 구조화된 로깅 (JSON 형식)
   - 로그 집계 시스템 (ELK Stack 등)

3. **모니터링 강화**
   - Prometheus + Grafana 설정
   - 알림 시스템 구축

### 10.2 중장기 개선 사항

1. **Blue-Green 배포**
   - 무중단 배포 구현
   - 롤백 자동화

2. **Auto Scaling**
   - 트래픽에 따른 자동 스케일링
   - 로드 밸런서 설정

3. **컨테이너화**
   - Docker 컨테이너로 배포
   - Kubernetes 오케스트레이션

4. **데이터베이스 마이그레이션**
   - Alembic으로 자동 마이그레이션
   - 백업 자동화

---

## 11. 참고 자료

### 11.1 공식 문서

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Systemd 서비스 관리](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Nginx 공식 문서](https://nginx.org/en/docs/)

### 11.2 유용한 명령어 모음

```bash
# 서비스 관리
sudo systemctl start langchain-api.service
sudo systemctl stop langchain-api.service
sudo systemctl restart langchain-api.service
sudo systemctl status langchain-api.service

# 로그 확인
sudo journalctl -u langchain-api.service -f
sudo journalctl -u langchain-api.service -n 100

# Nginx 관리
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl reload nginx

# 프로세스 확인
ps aux | grep uvicorn
sudo netstat -tlnp | grep 8000

# 디스크 사용량
df -h
du -sh /var/www/langchain

# 메모리 사용량
free -h
```

---

**작성일:** 2024-12-19
**작성자:** AI Assistant
**버전:** 1.0

