#!/bin/bash

EC2_HOST="ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com"
EC2_USER="ubuntu"
SSH_KEY="kang.pem"

echo "📊 Monitoring EC2 Instance..."
echo ""

ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" << 'ENDSSH'
    echo "=== System Info ==="
    uptime
    echo ""
    free -h
    echo ""
    df -h /var/www/langchain
    echo ""

    echo "=== Service Status ==="
    sudo systemctl status langchain-api.service --no-pager | head -20
    echo ""

    echo "=== Recent Logs (Last 10 lines) ==="
    sudo journalctl -u langchain-api.service -n 10 --no-pager
    echo ""

    echo "=== Process Info ==="
    ps aux | grep uvicorn | grep -v grep
    echo ""

    echo "=== Port Listening ==="
    sudo netstat -tlnp | grep :8000
    echo ""

    echo "=== Nginx Status ==="
    sudo systemctl status nginx --no-pager | head -10
ENDSSH

