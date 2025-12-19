#!/bin/bash
# 배포 검증 스크립트
#
# 사용법:
#   ./scripts/verify-deployment.sh

SERVICE_NAME="langchain-api.service"
HEALTH_URL="http://localhost:8000/health"
MAX_WAIT=30
RETRY_COUNT=0
EXIT_CODE=0

echo "🔍 Verifying deployment..."

# 1. 서비스 상태 확인
echo "1. Checking service status..."
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "   ✅ Service is active"
else
    echo "   ❌ Service is not active"
    EXIT_CODE=1
fi

# 2. 포트 리스닝 확인
echo "2. Checking port 8000..."
if ss -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "   ✅ Port 8000 is listening"
else
    echo "   ❌ Port 8000 is not listening"
    EXIT_CODE=1
fi

# 3. Health check (재시도 포함)
echo "3. Checking health endpoint..."
while [ $RETRY_COUNT -lt $MAX_WAIT ]; do
    if curl -f -s --max-time 5 $HEALTH_URL >/dev/null 2>&1; then
        echo "   ✅ Health check passed"
        curl -s $HEALTH_URL | head -3
        break
    fi
    sleep 1
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_WAIT ]; then
    echo "   ❌ Health check failed after $MAX_WAIT seconds"
    EXIT_CODE=1
fi

# 4. Nginx 상태 확인
echo "4. Checking Nginx status..."
if systemctl is-active --quiet nginx; then
    echo "   ✅ Nginx is active"

    # Nginx를 통한 health check
    if curl -f -s --max-time 5 http://localhost/health >/dev/null 2>&1; then
        echo "   ✅ Health check via Nginx passed"
    else
        echo "   ⚠️  Health check via Nginx failed (but service is running)"
    fi
else
    echo "   ⚠️  Nginx is not active (optional)"
fi

# 5. 포트 80 확인
echo "5. Checking port 80..."
if ss -tlnp 2>/dev/null | grep -q ":80 "; then
    echo "   ✅ Port 80 is listening"
else
    echo "   ⚠️  Port 80 is not listening (Nginx may not be configured)"
fi

# 결과 요약
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Deployment verification successful!"
else
    echo "❌ Deployment verification failed!"
    echo ""
    echo "Troubleshooting steps:"
    echo "  1. Check service status: sudo systemctl status $SERVICE_NAME"
    echo "  2. Check service logs: sudo journalctl -u $SERVICE_NAME -n 50"
    echo "  3. Check error logs: tail -50 /var/log/langchain/error.log"
    echo "  4. Check port status: sudo ss -tlnp | grep -E ':(80|8000)'"
fi

exit $EXIT_CODE

