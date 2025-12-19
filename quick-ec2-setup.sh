#!/bin/bash
# Quick EC2 Setup Script
# EC2에 접속한 후 이 스크립트를 실행하세요

set -e

echo "🚀 LangChain FastAPI EC2 Setup Starting..."

# 시스템 업데이트
echo "📦 Updating system..."
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
echo "📦 Installing packages..."
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx curl htop

# 디렉토리 생성
echo "📁 Creating directories..."
sudo mkdir -p /var/www/langchain /var/log/langchain
sudo chown -R ubuntu:ubuntu /var/www/langchain /var/log/langchain

# Python 가상 환경
echo "🐍 Setting up Python environment..."
cd /var/www/langchain
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# .env 파일 (템플릿)
if [ ! -f /var/www/langchain/.env ]; then
    echo "📝 Creating .env template..."
    cat > /var/www/langchain/.env << 'EOF'
OPENAI_API_KEY=your_key_here
POSTGRES_USER=neondb_owner
POSTGRES_PASSWORD=your_password_here
POSTGRES_HOST=ep-mute-boat-a1sgw2su-pooler.ap-southeast-1.aws.neon.tech
POSTGRES_PORT=5432
POSTGRES_DB=neondb
LLM_PROVIDER=openai
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
EOF
    chmod 600 /var/www/langchain/.env
fi

# Systemd 서비스
echo "⚙️  Creating systemd service..."
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
echo "🌐 Configuring Nginx..."
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

# Systemd 활성화
sudo systemctl daemon-reload
sudo systemctl enable langchain-api.service

# 방화벽
echo "🔒 Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
echo "y" | sudo ufw enable || true

echo ""
echo "✅ Setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Clone your repository: cd /var/www/langchain && git clone https://github.com/YOUR_USER/YOUR_REPO.git ."
echo "2. Edit .env file: nano /var/www/langchain/.env"
echo "3. Install dependencies: source venv/bin/activate && pip install -r requirements.txt"
echo "4. Start service: sudo systemctl start langchain-api.service"
echo "5. Check status: sudo systemctl status langchain-api.service"
echo "6. Test health: curl http://localhost:8000/health"

