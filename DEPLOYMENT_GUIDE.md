# 🚀 배포 실행 가이드

## Step 1: GitHub Secrets 설정 (필수)

GitHub Repository → Settings → Secrets and variables → Actions

다음 시크릿들을 추가하세요:

### 1. EC2_HOST
```
ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com
```

### 2. EC2_USER
```
ubuntu
```

### 3. EC2_SSH_KEY
kang.pem 파일의 전체 내용을 복사:
```bash
# PowerShell에서
Get-Content kang.pem | Out-String
```
출력된 전체 내용 (-----BEGIN RSA PRIVATE KEY----- 부터 -----END RSA PRIVATE KEY----- 까지)을 복사하여 추가

### 4. OPENAI_API_KEY
```
sk-...  # 실제 OpenAI API 키
```

### 5. POSTGRES_PASSWORD
```
# Neon PostgreSQL 비밀번호
```

---

## Step 2: EC2 초기 설정 (최초 1회만)

### 2.1 EC2 접속
```bash
ssh -i "kang.pem" ubuntu@ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com
```

### 2.2 설정 스크립트 실행

EC2에서 다음 명령어를 실행:

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx curl

# 애플리케이션 디렉토리 생성
sudo mkdir -p /var/www/langchain
sudo chown -R ubuntu:ubuntu /var/www/langchain
sudo mkdir -p /var/log/langchain
sudo chown -R ubuntu:ubuntu /var/log/langchain

# Python 가상 환경 설정
cd /var/www/langchain
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 2.3 환경 변수 파일 생성

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

# Model
LLM_PROVIDER=openai
MIDM_MODEL_PATH=/var/www/langchain/models/midm

# Server
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
EOF

chmod 600 /var/www/langchain/.env

# 실제 값으로 편집
nano /var/www/langchain/.env
```

### 2.4 Systemd 서비스 생성

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
ExecStart=/var/www/langchain/venv/bin/uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
StandardOutput=append:/var/log/langchain/access.log
StandardError=append:/var/log/langchain/error.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable langchain-api.service
```

### 2.5 Nginx 설정

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

sudo ln -sf /etc/nginx/sites-available/langchain /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 2.6 방화벽 설정

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
echo "y" | sudo ufw enable
```

### 2.7 최초 코드 배포

```bash
cd /var/www/langchain

# GitHub에서 클론 (실제 저장소 URL로 변경)
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .

# 의존성 설치
source venv/bin/activate
pip install -r requirements.txt

# 서비스 시작
sudo systemctl start langchain-api.service
sudo systemctl status langchain-api.service

# 헬스 체크
curl http://localhost:8000/health
```

---

## Step 3: 자동 배포 테스트

로컬에서:

```bash
# 변경사항 커밋 및 푸시
git add .
git commit -m "feat: setup CI/CD pipeline"
git push origin main
```

GitHub Actions 탭에서 배포 상태 확인:
- https://github.com/YOUR_USERNAME/YOUR_REPO/actions

---

## Step 4: 배포 확인

```bash
# 헬스 체크
curl http://ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com/health

# 로그 확인 (EC2에서)
sudo journalctl -u langchain-api.service -f
```

---

## 트러블슈팅

### 서비스가 시작되지 않는 경우

```bash
# 로그 확인
sudo journalctl -u langchain-api.service -n 50

# 권한 확인
ls -la /var/www/langchain

# 포트 확인
sudo netstat -tlnp | grep 8000
```

### 배포가 실패하는 경우

```bash
# GitHub Actions 로그 확인
# SSH 연결 테스트
ssh -i "kang.pem" ubuntu@ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com "echo 'test'"
```

---

## 롤백

문제가 발생하면:

```bash
# 로컬에서 (Git Bash 사용)
./scripts/rollback.sh
```

또는 EC2에서 직접:

```bash
cd /var/www/langchain
git reset --hard HEAD~1
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart langchain-api.service
```

