# 🚀 빠른 배포 확인 가이드

## 1️⃣ 커밋 전 확인 (지금 하실 일)

### 현재 상태 확인
```bash
git status
```

**예상 결과:**
- `.github/workflows/deploy.yml` (수정됨)
- `strategy/PORT_80_TROUBLESHOOTING_STRATEGY.md` (새 파일)
- `scripts/health-monitor.sh` (새 파일)
- `scripts/health-monitor.service` (새 파일)
- `scripts/verify-deployment.sh` (새 파일)

## 2️⃣ 커밋 및 푸시 (3단계)

### Step 1: 변경사항 추가
```bash
git add .
```

### Step 2: 커밋
```bash
git commit -m "fix: 포트 80 문제 해결 및 배포 워크플로우 개선

- 서비스 시작 순서 개선
- Health check 재시도 로직 강화
- Nginx 백엔드 연결 재시도 설정
- 자동 모니터링 스크립트 추가"
```

### Step 3: 푸시 (자동 배포 시작!)
```bash
git push origin main
```

**중요:** `main` 브랜치에 푸시하면 자동으로 배포가 시작됩니다! 🎯

## 3️⃣ 배포 진행 상황 확인 (약 5-10분)

### GitHub에서 확인
1. GitHub 저장소로 이동
2. **"Actions"** 탭 클릭
3. 최신 워크플로우 실행 클릭
4. 다음 단계들이 모두 ✅ 되면 성공:
   - ✅ Deploy app to EC2
   - ✅ Health Check

### 실패하면?
- 각 단계를 클릭하여 상세 로그 확인
- 에러 메시지 확인 후 `DEPLOYMENT_VERIFICATION_GUIDE.md` 참고

## 4️⃣ 배포 후 확인 (EC2 서버에서)

### 간단한 확인 (SSH 접속 후)
```bash
# 1. 서비스 상태
sudo systemctl status langchain-api.service
# ✅ "active (running)" 이면 OK!

# 2. Health Check
curl http://localhost:8000/health
# ✅ {"status":"healthy",...} 이면 OK!

# 3. Nginx 확인
curl http://localhost/health
# ✅ {"status":"healthy",...} 이면 OK!
```

### 외부에서 확인
```bash
# EC2 퍼블릭 IP로 접속
curl http://YOUR_EC2_IP/health

# 또는 브라우저에서
# http://YOUR_EC2_IP/health
```

## ✅ 성공 기준

다음 3가지만 확인하면 됩니다:

1. ✅ GitHub Actions가 성공적으로 완료
2. ✅ `sudo systemctl status langchain-api.service` → active (running)
3. ✅ `curl http://YOUR_EC2_IP/health` → {"status":"healthy",...}

## 🆘 문제 발생 시

### 빠른 진단
```bash
# EC2 서버에서 실행
sudo systemctl status langchain-api.service
sudo journalctl -u langchain-api.service -n 50
tail -50 /var/log/langchain/error.log
```

### 자세한 가이드
- `DEPLOYMENT_VERIFICATION_GUIDE.md` 참고
- `strategy/PORT_80_TROUBLESHOOTING_STRATEGY.md` 참고

