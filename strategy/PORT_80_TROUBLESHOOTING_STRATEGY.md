# 포트 80 문제 해결 전략

## 문제 분석

### 증상
- `curl: (7) Failed to connect to localhost port 8000` - FastAPI 서비스가 8000번 포트에서 실행되지 않음
- `502 Bad Gateway` - Nginx가 백엔드(8000)에 연결하지 못함
- Health check 실패

### 원인 분석

1. **FastAPI 서비스 시작 실패**
   - 서비스가 크래시되거나 시작되지 않음
   - 포트 8000이 리스닝 상태가 아님
   - 의존성 문제 (Python, 패키지 등)

2. **Nginx 설정 문제**
   - Nginx가 실행되지 않음
   - Nginx 설정 오류
   - 백엔드 연결 실패 (502)

3. **타이밍 문제**
   - Nginx가 서비스 시작 전에 실행됨
   - 서비스가 완전히 시작되기 전에 health check 실행

4. **방화벽/보안 그룹 문제**
   - 포트 80이 외부에서 접근 불가
   - AWS Security Group 설정 오류

## 해결 전략

### 전략 1: 서비스 시작 순서 개선

**문제**: Nginx가 FastAPI 서비스 시작 전에 실행되어 502 에러 발생

**해결책**:
1. FastAPI 서비스가 완전히 시작될 때까지 대기
2. 포트 8000이 실제로 리스닝 상태인지 확인
3. 그 후 Nginx 설정 및 재시작

**구현**:
```bash
# 1. 서비스 시작
sudo systemctl restart langchain-api.service

# 2. 포트가 열릴 때까지 대기 (최대 30초)
for i in {1..30}; do
  if sudo ss -tlnp | grep -q ":8000"; then
    echo "Port 8000 is listening"
    break
  fi
  sleep 1
done

# 3. 로컬 health check 성공 확인
curl -f http://localhost:8000/health || exit 1

# 4. 그 후 Nginx 설정 및 재시작
sudo nginx -t && sudo systemctl restart nginx
```

### 전략 2: Systemd 의존성 설정

**문제**: 서비스 간 의존성이 명확하지 않음

**해결책**: Systemd 서비스 파일에 의존성 추가

**구현**:
```ini
[Unit]
Description=LangChain FastAPI Application
After=network.target
# Nginx가 먼저 시작되도록 (선택적)
# After=nginx.service

[Service]
Type=simple
# 서비스가 완전히 시작될 때까지 대기
ExecStartPre=/bin/sleep 2
ExecStart=/var/www/langchain/venv/bin/uvicorn api_server_refactored:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10
# 서비스가 시작되었는지 확인
TimeoutStartSec=60

[Install]
WantedBy=multi-user.target
```

### 전략 3: Nginx 백엔드 연결 재시도 설정

**문제**: 백엔드가 일시적으로 응답하지 않을 때 502 발생

**해결책**: Nginx에 백엔드 연결 재시도 및 타임아웃 설정 추가

**구현**:
```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # 백엔드 연결 재시도 설정
        proxy_next_upstream error timeout http_502 http_503;
        proxy_next_upstream_tries 3;
        proxy_next_upstream_timeout 10s;

        # 타임아웃 설정
        proxy_connect_timeout 10s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 헤더 설정
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
        proxy_connect_timeout 5s;
        proxy_read_timeout 5s;
        access_log off;
    }
}
```

### 전략 4: 자동 복구 스크립트

**문제**: 서비스가 크래시되거나 중단될 때 수동 개입 필요

**해결책**: 주기적으로 서비스 상태를 확인하고 자동 재시작하는 스크립트

**구현** (`scripts/health-monitor.sh`):
```bash
#!/bin/bash
# 서비스 상태 모니터링 및 자동 복구 스크립트

SERVICE_NAME="langchain-api.service"
HEALTH_URL="http://localhost:8000/health"
MAX_FAILURES=3
FAILURE_COUNT=0

check_service() {
    # 서비스가 실행 중인지 확인
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        echo "Service is not active, attempting restart..."
        sudo systemctl restart $SERVICE_NAME
        sleep 5
        return 1
    fi

    # 포트가 리스닝 상태인지 확인
    if ! ss -tlnp | grep -q ":8000"; then
        echo "Port 8000 is not listening, restarting service..."
        sudo systemctl restart $SERVICE_NAME
        sleep 5
        return 1
    fi

    # Health check
    if ! curl -f $HEALTH_URL >/dev/null 2>&1; then
        echo "Health check failed"
        return 1
    fi

    return 0
}

# 메인 루프
while true; do
    if ! check_service; then
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        echo "Failure count: $FAILURE_COUNT"

        if [ $FAILURE_COUNT -ge $MAX_FAILURES ]; then
            echo "Max failures reached, sending alert..."
            # 여기에 알림 로직 추가 (이메일, Slack 등)
            FAILURE_COUNT=0
        fi
    else
        FAILURE_COUNT=0
    fi

    sleep 30
done
```

### 전략 5: 배포 워크플로우 개선

**문제**: 배포 중 서비스 시작 타이밍 문제

**해결책**: 단계별 검증 및 재시도 로직

**구현 단계**:
1. 서비스 시작
2. 포트 리스닝 확인 (최대 30초 대기)
3. 로컬 health check (최대 5회 재시도)
4. Nginx 설정 및 재시작
5. 외부 health check (최대 5회 재시도)

### 전략 6: 방화벽 및 보안 그룹 확인

**문제**: 포트 80이 외부에서 접근 불가

**해결책**: 체계적인 확인 절차

**확인 사항**:
1. **UFW 방화벽**:
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

2. **AWS Security Group**:
   - 인바운드 규칙에 HTTP (포트 80) 추가
   - 소스: 0.0.0.0/0 (또는 특정 IP)
   - HTTPS (포트 443)도 추가 권장

3. **포트 리스닝 확인**:
   ```bash
   sudo ss -tlnp | grep 80
   sudo ss -tlnp | grep 8000
   ```

### 전략 7: 로깅 및 모니터링 강화

**문제**: 문제 발생 시 원인 파악이 어려움

**해결책**: 상세한 로깅 및 모니터링

**구현**:
1. **서비스 로그 확인**:
   ```bash
   sudo journalctl -u langchain-api.service -f
   tail -f /var/log/langchain/error.log
   ```

2. **Nginx 로그 확인**:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   sudo tail -f /var/log/nginx/access.log
   ```

3. **포트 모니터링**:
   ```bash
   watch -n 1 'sudo ss -tlnp | grep -E ":(80|8000)"'
   ```

## 단계별 해결 절차

### 1단계: 즉시 확인 사항

```bash
# 서비스 상태 확인
sudo systemctl status langchain-api.service

# 포트 리스닝 확인
sudo ss -tlnp | grep -E ':(80|8000)'

# Nginx 상태 확인
sudo systemctl status nginx

# 로컬 health check
curl http://localhost:8000/health
curl http://localhost/health
```

### 2단계: 서비스 재시작

```bash
# 서비스 재시작
sudo systemctl restart langchain-api.service

# 포트가 열릴 때까지 대기
for i in {1..30}; do
  if sudo ss -tlnp | grep -q ":8000"; then
    echo "Port 8000 is listening"
    break
  fi
  sleep 1
done

# Health check
curl -f http://localhost:8000/health || echo "Health check failed"
```

### 3단계: Nginx 재시작

```bash
# Nginx 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx

# 상태 확인
sudo systemctl status nginx
```

### 4단계: 방화벽 확인

```bash
# UFW 상태
sudo ufw status

# 포트 열기 (필요시)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### 5단계: 외부 접근 테스트

```bash
# EC2 퍼블릭 IP로 테스트
curl http://YOUR_EC2_IP/health

# 또는 도메인으로 테스트
curl http://your-domain.com/health
```

## 예방 조치

### 1. 서비스 시작 검증 스크립트

배포 후 자동으로 검증하는 스크립트 추가:

```bash
#!/bin/bash
# scripts/verify-deployment.sh

SERVICE_NAME="langchain-api.service"
MAX_WAIT=30
RETRY_COUNT=0

echo "Verifying deployment..."

# 서비스가 active인지 확인
while [ $RETRY_COUNT -lt $MAX_WAIT ]; do
  if systemctl is-active --quiet $SERVICE_NAME; then
    if ss -tlnp | grep -q ":8000"; then
      if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ Deployment verified successfully"
        exit 0
      fi
    fi
  fi
  sleep 1
  RETRY_COUNT=$((RETRY_COUNT + 1))
done

echo "❌ Deployment verification failed"
exit 1
```

### 2. Health Check 엔드포인트 강화

더 상세한 정보를 반환하는 health check:

```python
@health_router.get("/health")
async def health_check():
    """상세한 헬스 체크 엔드포인트"""
    import psutil
    import os

    return {
        "status": "healthy",
        "message": "RAG Chatbot API is running",
        "version": "1.0.0",
        "uptime": get_uptime(),
        "memory": {
            "used": psutil.virtual_memory().used,
            "available": psutil.virtual_memory().available
        },
        "port": 8000,
        "workers": os.environ.get("WORKERS", "2")
    }
```

### 3. 모니터링 대시보드

Prometheus + Grafana를 사용한 모니터링 설정 (선택사항)

## 체크리스트

배포 전 확인 사항:

- [ ] 서비스 파일이 올바른 경로와 포트를 사용하는가?
- [ ] .env 파일이 존재하고 올바른 설정을 포함하는가?
- [ ] Python 가상 환경이 올바르게 설정되었는가?
- [ ] 의존성 패키지가 모두 설치되었는가?
- [ ] Nginx 설정 파일이 올바른가?
- [ ] 방화벽이 포트 80을 허용하는가?
- [ ] AWS Security Group이 포트 80을 허용하는가?
- [ ] 서비스가 자동 시작되도록 enable되었는가?

배포 후 확인 사항:

- [ ] 서비스가 active 상태인가?
- [ ] 포트 8000이 리스닝 상태인가?
- [ ] 로컬 health check가 성공하는가?
- [ ] Nginx가 실행 중인가?
- [ ] 포트 80이 리스닝 상태인가?
- [ ] 외부 health check가 성공하는가?

## 문제 해결 플로우차트

```
문제 발생
    ↓
서비스 상태 확인
    ↓
[서비스가 실행 중?]
    ├─ NO → 서비스 재시작 → 포트 확인 → Health check
    └─ YES → 포트 8000 확인
              ↓
         [포트가 열려있나?]
              ├─ NO → 로그 확인 → 의존성 확인 → 재시작
              └─ YES → 로컬 Health check
                          ↓
                     [성공?]
                          ├─ NO → 로그 확인 → 코드 문제 확인
                          └─ YES → Nginx 확인
                                      ↓
                                 [Nginx 실행 중?]
                                      ├─ NO → Nginx 시작
                                      └─ YES → Nginx 설정 확인
                                                  ↓
                                             [설정 올바른가?]
                                                  ├─ NO → 설정 수정
                                                  └─ YES → 외부 Health check
                                                              ↓
                                                         [성공?]
                                                              ├─ NO → 방화벽/Security Group 확인
                                                              └─ YES → 완료
```

## 참고 자료

- [Systemd 서비스 관리](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Nginx 리버스 프록시 설정](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [UFW 방화벽 설정](https://help.ubuntu.com/community/UFW)
- [AWS Security Group 설정](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-security-groups.html)

