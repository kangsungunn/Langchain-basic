#!/bin/bash
# 서비스 상태 모니터링 및 자동 복구 스크립트
#
# 사용법:
#   sudo systemctl enable health-monitor.service
#   sudo systemctl start health-monitor.service

SERVICE_NAME="langchain-api.service"
HEALTH_URL="http://localhost:8000/health"
MAX_FAILURES=3
FAILURE_COUNT=0
CHECK_INTERVAL=30
LOG_FILE="/var/log/langchain/health-monitor.log"

# 로그 디렉토리 생성
mkdir -p /var/log/langchain

# 로그 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 서비스 상태 확인
check_service() {
    # 서비스가 실행 중인지 확인
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        log "WARNING: Service $SERVICE_NAME is not active"
        return 1
    fi

    # 포트가 리스닝 상태인지 확인
    if ! ss -tlnp 2>/dev/null | grep -q ":8000"; then
        log "WARNING: Port 8000 is not listening"
        return 1
    fi

    # Health check
    if ! curl -f -s --max-time 5 $HEALTH_URL >/dev/null 2>&1; then
        log "WARNING: Health check failed"
        return 1
    fi

    return 0
}

# 서비스 재시작
restart_service() {
    log "Attempting to restart $SERVICE_NAME..."
    sudo systemctl restart $SERVICE_NAME
    sleep 10

    # 재시작 후 확인
    if systemctl is-active --quiet $SERVICE_NAME; then
        if ss -tlnp 2>/dev/null | grep -q ":8000"; then
            if curl -f -s --max-time 5 $HEALTH_URL >/dev/null 2>&1; then
                log "SUCCESS: Service restarted and healthy"
                return 0
            fi
        fi
    fi

    log "ERROR: Service restart failed or still unhealthy"
    return 1
}

# Nginx 재시작
restart_nginx() {
    log "Attempting to restart nginx..."
    sudo systemctl restart nginx
    sleep 3

    if systemctl is-active --quiet nginx; then
        log "SUCCESS: Nginx restarted"
        return 0
    else
        log "ERROR: Nginx restart failed"
        return 1
    fi
}

# 메인 루프
main() {
    log "Health monitor started"
    log "Service: $SERVICE_NAME"
    log "Health URL: $HEALTH_URL"
    log "Check interval: ${CHECK_INTERVAL}s"

    while true; do
        if ! check_service; then
            FAILURE_COUNT=$((FAILURE_COUNT + 1))
            log "Failure count: $FAILURE_COUNT/$MAX_FAILURES"

            if [ $FAILURE_COUNT -ge $MAX_FAILURES ]; then
                log "Max failures reached, attempting recovery..."

                # 서비스 재시작 시도
                if restart_service; then
                    FAILURE_COUNT=0
                    log "Recovery successful"
                else
                    # Nginx도 재시작 시도
                    restart_nginx

                    # 여전히 실패하면 알림 (선택적)
                    log "CRITICAL: Service recovery failed after $MAX_FAILURES attempts"
                    log "Please check manually:"
                    log "  - sudo systemctl status $SERVICE_NAME"
                    log "  - sudo journalctl -u $SERVICE_NAME -n 50"
                    log "  - tail -50 /var/log/langchain/error.log"

                    # 실패 카운터 리셋 (무한 루프 방지)
                    FAILURE_COUNT=0
                fi
            fi
        else
            if [ $FAILURE_COUNT -gt 0 ]; then
                log "Service recovered, resetting failure count"
                FAILURE_COUNT=0
            fi
        fi

        sleep $CHECK_INTERVAL
    done
}

# 시그널 핸들링
trap 'log "Health monitor stopped"; exit 0' SIGTERM SIGINT

# 메인 실행
main

