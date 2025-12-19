# 배포 검증 가이드

## 📋 변경사항 확인

### 변경된 파일 목록

1. **`.github/workflows/deploy.yml`** (주요 변경)
   - 서비스 시작 순서 개선
   - 포트 리스닝 확인 로직 추가
   - Health check 재시도 로직 강화
   - Nginx 설정 개선 (백엔드 재시도 설정)

2. **새로 추가된 파일들**
   - `strategy/PORT_80_TROUBLESHOOTING_STRATEGY.md` - 문제 해결 전략 문서
   - `scripts/health-monitor.sh` - 자동 모니터링 스크립트
   - `scripts/health-monitor.service` - 모니터링 서비스 파일
   - `scripts/verify-deployment.sh` - 배포 검증 스크립트

## ✅ 커밋 전 확인 사항

### 1단계: 변경사항 검토

```bash
# 변경된 내용 확인
git diff .github/workflows/deploy.yml

# 새로 추가된 파일 확인
git status
```

### 2단계: 주요 변경사항 확인

**워크플로우 개선 사항:**
- ✅ 서비스 시작 후 포트 8000 리스닝 확인 (최대 30초 대기)
- ✅ 로컬 health check 재시도 (최대 5회)
- ✅ Nginx 설정을 서비스 시작 후로 이동
- ✅ Nginx 백엔드 연결 재시도 설정 추가
- ✅ Systemd 타임아웃 설정 추가
- ✅ 외부 health check 개선 (최대 5회 재시도)

## 🚀 커밋 및 푸시 절차

### 1단계: 변경사항 스테이징

```bash
# 모든 변경사항 추가
git add .

# 또는 개별적으로 추가
git add .github/workflows/deploy.yml
git add strategy/PORT_80_TROUBLESHOOTING_STRATEGY.md
git add scripts/health-monitor.sh
git add scripts/health-monitor.service
git add scripts/verify-deployment.sh
```

### 2단계: 커밋 메시지 작성

```bash
git commit -m "fix: 포트 80 문제 해결 및 배포 워크플로우 개선

- 서비스 시작 순서 개선 (포트 리스닝 확인 후 Nginx 설정)
- Health check 재시도 로직 강화 (로컬/외부 각 5회)
- Nginx 백엔드 연결 재시도 및 타임아웃 설정 추가
- Systemd 타임아웃 설정 추가
- 자동 모니터링 및 배포 검증 스크립트 추가
- 포트 80 문제 해결 전략 문서 추가"
```

### 3단계: 푸시

```bash
git push origin main
```

**참고:** `main` 브랜치에 푸시하면 자동으로 GitHub Actions가 배포를 시작합니다.

## 📊 배포 후 확인 절차

### 1단계: GitHub Actions 확인 (약 5-10분 소요)

1. **GitHub 저장소로 이동**
   - https://github.com/YOUR_USERNAME/YOUR_REPO 로 이동
   - "Actions" 탭 클릭

2. **배포 워크플로우 확인**
   - 최신 워크플로우 실행 클릭
   - 각 단계가 성공적으로 완료되는지 확인:
     - ✅ Checkout code
     - ✅ Setup SSH
     - ✅ Test SSH connection
     - ✅ Deploy app to EC2
     - ✅ Health Check

3. **로그 확인**
   - "Deploy app to EC2" 단계 클릭하여 상세 로그 확인
   - "Health Check" 단계 클릭하여 health check 결과 확인

### 2단계: EC2 서버에서 직접 확인 (SSH 접속)

```bash
# EC2 서버에 SSH 접속
ssh ubuntu@YOUR_EC2_IP

# 1. 서비스 상태 확인
sudo systemctl status langchain-api.service

# 예상 결과:
# - Active: active (running)
# - 포트 8000이 리스닝 상태
```

```bash
# 2. 포트 리스닝 확인
sudo ss -tlnp | grep -E ':(80|8000)'

# 예상 결과:
# - :8000 포트가 리스닝 중
# - :80 포트가 리스닝 중 (Nginx)
```

```bash
# 3. 로컬 Health Check
curl http://localhost:8000/health

# 예상 결과:
# {"status":"healthy","message":"RAG Chatbot API is running"}
```

```bash
# 4. Nginx를 통한 Health Check
curl http://localhost/health

# 예상 결과:
# {"status":"healthy","message":"RAG Chatbot API is running"}
```

```bash
# 5. 서비스 로그 확인 (에러가 있는지)
sudo journalctl -u langchain-api.service -n 50 --no-pager

# 에러가 있다면:
tail -50 /var/log/langchain/error.log
```

```bash
# 6. Nginx 상태 확인
sudo systemctl status nginx

# Nginx 에러 로그 확인 (필요시)
sudo tail -50 /var/log/nginx/error.log
```

### 3단계: 외부에서 접근 테스트

```bash
# EC2 퍼블릭 IP로 Health Check
curl http://YOUR_EC2_IP/health

# 예상 결과:
# {"status":"healthy","message":"RAG Chatbot API is running"}

# 또는 브라우저에서 접속
# http://YOUR_EC2_IP/health
```

### 4단계: 배포 검증 스크립트 실행 (선택사항)

```bash
# EC2 서버에서 실행
cd /var/www/langchain
./scripts/verify-deployment.sh

# 또는 GitHub에서 배포된 스크립트 실행
bash scripts/verify-deployment.sh
```

## 🔍 문제 발생 시 확인 사항

### 문제 1: 서비스가 시작되지 않음

```bash
# 서비스 상태 확인
sudo systemctl status langchain-api.service

# 서비스 로그 확인
sudo journalctl -u langchain-api.service -n 100 --no-pager

# 에러 로그 확인
tail -100 /var/log/langchain/error.log

# 수동으로 서비스 시작 시도
sudo systemctl restart langchain-api.service
```

### 문제 2: 포트 8000이 리스닝되지 않음

```bash
# 포트 확인
sudo ss -tlnp | grep 8000

# 프로세스 확인
ps aux | grep uvicorn

# 서비스 재시작
sudo systemctl restart langchain-api.service

# 10초 후 다시 확인
sleep 10
sudo ss -tlnp | grep 8000
```

### 문제 3: Nginx가 502 에러 반환

```bash
# Nginx 상태 확인
sudo systemctl status nginx

# Nginx 에러 로그 확인
sudo tail -50 /var/log/nginx/error.log

# 백엔드 연결 테스트
curl http://127.0.0.1:8000/health

# Nginx 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
```

### 문제 4: 외부에서 접근 불가

```bash
# 방화벽 확인
sudo ufw status

# 포트 80 허용 확인
sudo ufw allow 80/tcp

# AWS Security Group 확인 필요
# - EC2 콘솔에서 Security Group 확인
# - 인바운드 규칙에 HTTP (포트 80) 추가
```

## 📝 체크리스트

배포 전:
- [ ] 변경사항 검토 완료
- [ ] 커밋 메시지 작성
- [ ] 로컬에서 git status 확인

배포 중:
- [ ] GitHub Actions 워크플로우 실행 확인
- [ ] 각 단계 성공 여부 확인
- [ ] Health Check 단계 성공 확인

배포 후:
- [ ] 서비스 상태 확인 (active)
- [ ] 포트 8000 리스닝 확인
- [ ] 로컬 health check 성공
- [ ] Nginx 상태 확인
- [ ] 외부 health check 성공
- [ ] 에러 로그 확인 (에러 없음)

## 🎯 성공 기준

다음 조건을 모두 만족하면 성공:

1. ✅ GitHub Actions 워크플로우가 성공적으로 완료
2. ✅ 서비스가 `active (running)` 상태
3. ✅ 포트 8000이 리스닝 중
4. ✅ 로컬 health check 성공 (`http://localhost:8000/health`)
5. ✅ Nginx를 통한 health check 성공 (`http://localhost/health`)
6. ✅ 외부 health check 성공 (`http://EC2_IP/health`)
7. ✅ 에러 로그에 심각한 에러 없음

## 💡 추가 팁

### 자동 모니터링 활성화 (선택사항)

서비스가 자동으로 모니터링되고 문제 발생 시 재시작되도록 설정:

```bash
# EC2 서버에서 실행
sudo cp /var/www/langchain/app/scripts/health-monitor.sh /usr/local/bin/
sudo cp /var/www/langchain/app/scripts/health-monitor.service /etc/systemd/system/
sudo chmod +x /usr/local/bin/health-monitor.sh
sudo systemctl daemon-reload
sudo systemctl enable health-monitor.service
sudo systemctl start health-monitor.service

# 모니터링 로그 확인
tail -f /var/log/langchain/health-monitor.log
```

### 로그 실시간 모니터링

```bash
# 서비스 로그 실시간 확인
sudo journalctl -u langchain-api.service -f

# 에러 로그 실시간 확인
tail -f /var/log/langchain/error.log

# Nginx 에러 로그 실시간 확인
sudo tail -f /var/log/nginx/error.log
```

## 📞 문제 해결이 안 될 때

1. **전략 문서 참고**: `strategy/PORT_80_TROUBLESHOOTING_STRATEGY.md`
2. **GitHub Actions 로그 확인**: 상세한 에러 메시지 확인
3. **서비스 로그 확인**: `sudo journalctl -u langchain-api.service -n 200`
4. **에러 로그 확인**: `tail -100 /var/log/langchain/error.log`

