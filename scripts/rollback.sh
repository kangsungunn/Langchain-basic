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

