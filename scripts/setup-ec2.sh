#!/bin/bash
# EC2 초기 설정 스크립트
# 이 스크립트는 EC2 인스턴스에서 실행됩니다

set -e

echo "🚀 EC2 초기 설정 시작..."

# 시스템 업데이트
echo "📦 시스템 업데이트 중..."
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
echo "📦 필수 패키지 설치 중..."
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    nginx \
    curl \
    htop

# 애플리케이션 디렉토리 생성
echo "📁 애플리케이션 디렉토리 생성..."
sudo mkdir -p /var/www/langchain
sudo chown -R ubuntu:ubuntu /var/www/langchain

# 로그 디렉토리 생성
sudo mkdir -p /var/log/langchain
sudo chown -R ubuntu:ubuntu /var/log/langchain

# Python 가상 환경 설정
echo "🐍 Python 가상 환경 설정..."
cd /var/www/langchain
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# .env 파일 생성 (수동으로 편집 필요)
if [ ! -f /var/www/langchain/.env ]; then
    echo "📝 .env 파일 템플릿 생성..."
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
    echo "⚠️  .env 파일을 수동으로 편집하여 실제 값을 입력하세요!"
fi

# Systemd 서비스 파일 생성
echo "⚙️  Systemd 서비스 생성..."
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

# Nginx 설정
echo "🌐 Nginx 설정..."
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

        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range' always;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# Nginx 심볼릭 링크
sudo ln -sf /etc/nginx/sites-available/langchain /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 테스트 및 재시작
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# Systemd 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable langchain-api.service

# 방화벽 설정
echo "🔒 방화벽 설정..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
echo "y" | sudo ufw enable

echo "✅ EC2 초기 설정 완료!"
echo ""
echo "다음 단계:"
echo "1. /var/www/langchain/.env 파일 편집"
echo "2. GitHub에서 코드 클론: cd /var/www/langchain && git clone <repo-url> ."
echo "3. 의존성 설치: source venv/bin/activate && pip install -r requirements.txt"
echo "4. 서비스 시작: sudo systemctl start langchain-api.service"
echo "5. 상태 확인: sudo systemctl status langchain-api.service"

