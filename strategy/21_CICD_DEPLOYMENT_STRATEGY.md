# 21. FastAPI EC2 CI/CD 배포 전략

## 📋 개요

GitHub Actions를 사용하여 FastAPI 애플리케이션을 AWS EC2에 자동으로 배포하는 CI/CD 파이프라인 구축 가이드입니다.

## 🏗️ 아키텍처

```
GitHub Repository
    ↓ (push to main)
GitHub Actions
    ↓ (SSH 배포)
AWS EC2 (54.180.124.217)
    ↓
FastAPI (Systemd Service)
    ↓
Uvicorn (포트 8000)
```

## 🎯 배포 전략

### 1단계: EC2 환경 준비
### 2단계: GitHub Repository 설정
### 3단계: GitHub Actions 워크플로우 작성
### 4단계: 자동 배포 테스트

---

## 1️⃣ EC2 환경 준비

### 1.1 EC2 접속 및 기본 설정

```bash
# 로컬에서 EC2 접속
ssh -i "kang.pem" ubuntu@ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx
```

### 1.2 애플리케이션 디렉토리 구조 생성

```bash
# 애플리케이션 디렉토리 생성
sudo mkdir -p /var/www/langchain
sudo chown -R ubuntu:ubuntu /var/www/langchain

# 로그 디렉토리 생성
sudo mkdir -p /var/log/langchain
sudo chown -R ubuntu:ubuntu /var/log/langchain
```

### 1.3 Python 가상 환경 설정

```bash
cd /var/www/langchain

# 가상 환경 생성
python3.11 -m venv venv

# 가상 환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip
```

### 1.4 환경 변수 파일 생성

```bash
# .env 파일 생성 (프로덕션 환경)
cat > /var/www/langchain/.env << 'EOF'
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# PostgreSQL (Neon)
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=your_password_here
POSTGRES_HOST=ep-mute-boat-a1sgw2su-pooler.ap-southeast-1.aws.neon.tech
POSTGRES_PORT=5432
POSTGRES_DB=neondb

# Model
LLM_PROVIDER=openai
MIDM_MODEL_PATH=/var/www/langchain/models/midm

# Server
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
EOF

# 보안을 위해 권한 설정
chmod 600 /var/www/langchain/.env
```

### 1.5 Systemd 서비스 생성

```bash
# 서비스 파일 생성
sudo tee /etc/systemd/system/langchain-api.service > /dev/null << 'EOF'
[Unit]
Description=LangChain FastAPI Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/var/www/langchain
Environment="PATH=/var/www/langchain/venv/bin"
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

### 1.6 Nginx 리버스 프록시 설정

```bash
# Nginx 설정 파일 생성
sudo tee /etc/nginx/sites-available/langchain > /dev/null << 'EOF'
server {
    listen 80;
    server_name 54.180.124.217;  # 또는 도메인 이름

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

        # CORS 헤더 (필요한 경우)
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range' always;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/langchain /etc/nginx/sites-enabled/

# 기본 사이트 비활성화 (선택사항)
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 2️⃣ GitHub Repository 설정

### 2.1 Repository Secrets 추가

GitHub Repository → Settings → Secrets and variables → Actions → New repository secret

다음 시크릿들을 추가:

```
EC2_HOST = ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com
EC2_USER = ubuntu
EC2_SSH_KEY = (kang.pem 파일의 전체 내용을 복사)
OPENAI_API_KEY = sk-...
POSTGRES_PASSWORD = your_password
```

**EC2_SSH_KEY 추가 방법:**
```bash
# 로컬에서 SSH 키 내용 출력
cat kang.pem

# 출력된 전체 내용을 복사하여 GitHub Secret에 추가
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...전체 내용...
-----END RSA PRIVATE KEY-----
```

### 2.2 `.gitignore` 업데이트

```bash
# .gitignore에 추가
cat >> .gitignore << 'EOF'

# Environment
.env
.env.local
.env.production

# SSH Keys
*.pem
*.key

# Models
models/midm/*
!models/midm/README.md

# Logs
*.log
logs/

# Cache
__pycache__/
*.pyc
.pytest_cache/

# IDE
.vscode/
.idea/
EOF
```

---

## 3️⃣ GitHub Actions 워크플로우

### 3.1 워크플로우 파일 생성

`.github/workflows/deploy.yml` 생성:

```yaml
name: Deploy to EC2

on:
  push:
    branches:
      - main  # main 브랜치에 푸시될 때 실행
  workflow_dispatch:  # 수동 실행 가능

jobs:
  deploy:
    name: Deploy FastAPI to EC2
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.8.0
        with:
          ssh-private-key: ${{ secrets.EC2_SSH_KEY }}

      - name: Add EC2 to known hosts
        run: |
          mkdir -p ~/.ssh
          ssh-keyscan -H ${{ secrets.EC2_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy to EC2
        env:
          EC2_HOST: ${{ secrets.EC2_HOST }}
          EC2_USER: ${{ secrets.EC2_USER }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
        run: |
          ssh $EC2_USER@$EC2_HOST << 'ENDSSH'
            set -e

            echo "🚀 Starting deployment..."

            # 애플리케이션 디렉토리로 이동
            cd /var/www/langchain

            # Git pull (최초에는 clone 필요)
            if [ -d ".git" ]; then
              echo "📥 Pulling latest changes..."
              git pull origin main
            else
              echo "📥 Cloning repository..."
              git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .
            fi

            # 가상 환경 활성화
            source venv/bin/activate

            # 의존성 설치
            echo "📦 Installing dependencies..."
            pip install -r requirements.txt

            # 환경 변수 업데이트 (선택적)
            echo "⚙️  Updating environment variables..."
            # 필요한 경우 .env 파일 업데이트

            # 서비스 재시작
            echo "🔄 Restarting service..."
            sudo systemctl restart langchain-api.service

            # 서비스 상태 확인
            sleep 3
            if sudo systemctl is-active --quiet langchain-api.service; then
              echo "✅ Deployment successful!"
              sudo systemctl status langchain-api.service --no-pager
            else
              echo "❌ Deployment failed!"
              sudo journalctl -u langchain-api.service -n 50 --no-pager
              exit 1
            fi
          ENDSSH

      - name: Health Check
        run: |
          sleep 5
          response=$(curl -s -o /dev/null -w "%{http_code}" http://${{ secrets.EC2_HOST }}/health)
          if [ $response -eq 200 ]; then
            echo "✅ Health check passed!"
          else
            echo "❌ Health check failed with status $response"
            exit 1
          fi

      - name: Notify Deployment Status
        if: always()
        run: |
          if [ ${{ job.status }} == 'success' ]; then
            echo "🎉 Deployment completed successfully!"
          else
            echo "❌ Deployment failed!"
          fi
```

### 3.2 고급 워크플로우 (Blue-Green 배포)

`.github/workflows/deploy-blue-green.yml`:

```yaml
name: Blue-Green Deploy to EC2

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  deploy:
    name: Blue-Green Deployment
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.8.0
        with:
          ssh-private-key: ${{ secrets.EC2_SSH_KEY }}

      - name: Add EC2 to known hosts
        run: |
          mkdir -p ~/.ssh
          ssh-keyscan -H ${{ secrets.EC2_HOST }} >> ~/.ssh/known_hosts

      - name: Blue-Green Deployment
        env:
          EC2_HOST: ${{ secrets.EC2_HOST }}
          EC2_USER: ${{ secrets.EC2_USER }}
        run: |
          ssh $EC2_USER@$EC2_HOST << 'ENDSSH'
            set -e

            echo "🔵 Starting Blue-Green deployment..."

            # 현재 활성 포트 확인
            if sudo systemctl is-active --quiet langchain-api-8000; then
              CURRENT_PORT=8000
              NEW_PORT=8001
              CURRENT_SERVICE="langchain-api-8000"
              NEW_SERVICE="langchain-api-8001"
            else
              CURRENT_PORT=8001
              NEW_PORT=8000
              CURRENT_SERVICE="langchain-api-8001"
              NEW_SERVICE="langchain-api-8000"
            fi

            echo "Current: $CURRENT_PORT, New: $NEW_PORT"

            # 새 버전 배포
            cd /var/www/langchain
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt

            # 새 포트에서 서비스 시작
            sudo systemctl start $NEW_SERVICE
            sleep 5

            # 헬스 체크
            if curl -f http://localhost:$NEW_PORT/health; then
              echo "✅ New version health check passed"

              # Nginx 전환
              sudo sed -i "s/proxy_pass http:\/\/127.0.0.1:$CURRENT_PORT/proxy_pass http:\/\/127.0.0.1:$NEW_PORT/" /etc/nginx/sites-available/langchain
              sudo nginx -t && sudo systemctl reload nginx

              # 이전 버전 종료
              sudo systemctl stop $CURRENT_SERVICE

              echo "🎉 Blue-Green deployment completed!"
            else
              echo "❌ Health check failed, rolling back"
              sudo systemctl stop $NEW_SERVICE
              exit 1
            fi
          ENDSSH
```

---

## 4️⃣ 배포 스크립트 (로컬)

### 4.1 `scripts/deploy.sh` 생성

```bash
#!/bin/bash
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 환경 변수
EC2_HOST="ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com"
EC2_USER="ubuntu"
SSH_KEY="kang.pem"

echo -e "${GREEN}🚀 Starting deployment to EC2...${NC}"

# SSH 연결 테스트
echo -e "${YELLOW}📡 Testing SSH connection...${NC}"
ssh -i "$SSH_KEY" -o ConnectTimeout=5 "$EC2_USER@$EC2_HOST" "echo 'SSH connection successful!'" || {
    echo -e "${RED}❌ SSH connection failed!${NC}"
    exit 1
}

# 코드 배포
echo -e "${YELLOW}📦 Deploying code...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" << 'ENDSSH'
    set -e
    cd /var/www/langchain

    # Git pull
    echo "Pulling latest changes..."
    git pull origin main || {
        echo "Git pull failed!"
        exit 1
    }

    # 가상 환경 활성화 및 의존성 설치
    source venv/bin/activate
    pip install -r requirements.txt

    # 서비스 재시작
    sudo systemctl restart langchain-api.service

    # 상태 확인
    sleep 3
    sudo systemctl status langchain-api.service --no-pager
ENDSSH

# 헬스 체크
echo -e "${YELLOW}🏥 Performing health check...${NC}"
sleep 5
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "http://$EC2_HOST/health")

if [ "$HEALTH_CHECK" -eq 200 ]; then
    echo -e "${GREEN}✅ Deployment successful! Health check passed.${NC}"
else
    echo -e "${RED}❌ Deployment failed! Health check returned: $HEALTH_CHECK${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Deployment completed!${NC}"
```

실행 권한 부여:
```bash
chmod +x scripts/deploy.sh
```

### 4.2 `scripts/rollback.sh` 생성

```bash
#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

EC2_HOST="ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com"
EC2_USER="ubuntu"
SSH_KEY="kang.pem"

echo -e "${YELLOW}⏮️  Rolling back to previous version...${NC}"

ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" << 'ENDSSH'
    set -e
    cd /var/www/langchain

    # Git 이전 커밋으로 롤백
    echo "Rolling back to previous commit..."
    git reset --hard HEAD~1

    # 의존성 재설치
    source venv/bin/activate
    pip install -r requirements.txt

    # 서비스 재시작
    sudo systemctl restart langchain-api.service

    sleep 3
    sudo systemctl status langchain-api.service --no-pager
ENDSSH

echo -e "${GREEN}✅ Rollback completed!${NC}"
```

---

## 5️⃣ 모니터링 및 로그

### 5.1 로그 확인 명령어

```bash
# 실시간 로그 모니터링
sudo journalctl -u langchain-api.service -f

# 최근 100줄 로그
sudo journalctl -u langchain-api.service -n 100

# 특정 시간 이후 로그
sudo journalctl -u langchain-api.service --since "1 hour ago"

# 애플리케이션 로그
tail -f /var/log/langchain/access.log
tail -f /var/log/langchain/error.log

# Nginx 로그
sudo tail -f /var/nginx/access.log
sudo tail -f /var/nginx/error.log
```

### 5.2 모니터링 스크립트

`scripts/monitor.sh`:
```bash
#!/bin/bash

EC2_HOST="ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com"
EC2_USER="ubuntu"
SSH_KEY="kang.pem"

ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" << 'ENDSSH'
    echo "=== System Info ==="
    uptime
    free -h
    df -h /var/www/langchain

    echo -e "\n=== Service Status ==="
    sudo systemctl status langchain-api.service --no-pager | head -20

    echo -e "\n=== Recent Logs ==="
    sudo journalctl -u langchain-api.service -n 10 --no-pager

    echo -e "\n=== Process Info ==="
    ps aux | grep uvicorn
ENDSSH
```

---

## 6️⃣ 보안 설정

### 6.1 방화벽 설정 (UFW)

```bash
# UFW 활성화
sudo ufw enable

# SSH 허용
sudo ufw allow 22/tcp

# HTTP/HTTPS 허용
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 애플리케이션 포트는 localhost만 허용 (Nginx가 프록시)
# 8000번 포트는 외부 접근 차단

# 상태 확인
sudo ufw status
```

### 6.2 환경 변수 암호화

GitHub Actions에서 환경 변수를 안전하게 사용:

```yaml
- name: Deploy with encrypted secrets
  env:
    ENCRYPTED_ENV: ${{ secrets.ENCRYPTED_ENV_FILE }}
  run: |
    echo "$ENCRYPTED_ENV" | base64 -d > .env
    scp .env $EC2_USER@$EC2_HOST:/var/www/langchain/.env
    rm .env
```

### 6.3 SSL/TLS 설정 (Let's Encrypt)

```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx -y

# SSL 인증서 발급 (도메인이 있는 경우)
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo certbot renew --dry-run
```

---

## 7️⃣ 최초 배포 체크리스트

### Step 1: EC2 준비
- [ ] EC2 접속 확인
- [ ] Python 3.11 설치
- [ ] 디렉토리 구조 생성
- [ ] 가상 환경 설정
- [ ] `.env` 파일 생성
- [ ] Systemd 서비스 생성
- [ ] Nginx 설정

### Step 2: GitHub 설정
- [ ] Repository Secrets 추가
- [ ] `.gitignore` 업데이트
- [ ] 워크플로우 파일 추가

### Step 3: 최초 배포
```bash
# 1. EC2에서 직접 클론 (최초 1회)
cd /var/www/langchain
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .

# 2. 의존성 설치
source venv/bin/activate
pip install -r requirements.txt

# 3. 서비스 시작
sudo systemctl start langchain-api.service
sudo systemctl status langchain-api.service

# 4. 헬스 체크
curl http://localhost:8000/health
```

### Step 4: 자동 배포 테스트
```bash
# 로컬에서 변경 사항 푸시
git add .
git commit -m "test: deploy workflow"
git push origin main

# GitHub Actions 확인
# Repository → Actions 탭에서 워크플로우 실행 확인
```

---

## 8️⃣ 트러블슈팅

### 문제 1: 서비스가 시작되지 않음
```bash
# 로그 확인
sudo journalctl -u langchain-api.service -n 50

# 일반적인 원인:
# 1. 의존성 누락 -> pip install -r requirements.txt
# 2. 포트 충돌 -> sudo lsof -i :8000
# 3. 권한 문제 -> sudo chown -R ubuntu:ubuntu /var/www/langchain
```

### 문제 2: GitHub Actions 배포 실패
```bash
# SSH 키 확인
# - EC2_SSH_KEY에 전체 키 내용이 있는지 확인
# - 개행 문자가 제대로 포함되어 있는지 확인

# known_hosts 문제
# - 워크플로우에 ssh-keyscan 단계가 있는지 확인
```

### 문제 3: Nginx 502 Bad Gateway
```bash
# FastAPI 서비스 상태 확인
sudo systemctl status langchain-api.service

# Nginx 설정 테스트
sudo nginx -t

# 포트 리스닝 확인
sudo netstat -tlnp | grep 8000
```

---

## 9️⃣ 성능 최적화

### 9.1 Uvicorn Workers 설정

`systemd` 서비스에서:
```ini
ExecStart=/var/www/langchain/venv/bin/uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --workers 4
```

워커 수 계산: `(2 x CPU 코어 수) + 1`

### 9.2 Gunicorn 사용 (선택사항)

```bash
# Gunicorn 설치
pip install gunicorn

# systemd 서비스 수정
ExecStart=/var/www/langchain/venv/bin/gunicorn app.api_server_refactored:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 9.3 로그 로테이션

`/etc/logrotate.d/langchain`:
```
/var/log/langchain/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 ubuntu ubuntu
    sharedscripts
    postrotate
        systemctl reload langchain-api.service > /dev/null 2>&1 || true
    endscript
}
```

---

## 🎓 다음 단계

1. **도메인 연결**: Route 53으로 도메인 설정
2. **SSL 인증서**: Let's Encrypt로 HTTPS 적용
3. **모니터링**: CloudWatch, Prometheus, Grafana 설정
4. **백업**: 자동 백업 스크립트 작성
5. **Auto Scaling**: AWS Auto Scaling Group 설정
6. **DB 마이그레이션**: Alembic으로 자동 마이그레이션

---

**마지막 업데이트:** 2024-12-18
**작성자:** AI Assistant
**버전:** 1.0

