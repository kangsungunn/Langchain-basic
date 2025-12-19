#!/bin/bash
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 환경 변수
EC2_HOST="ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com"
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

