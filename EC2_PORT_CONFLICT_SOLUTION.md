# EC2 포트 충돌 해결 가이드

## 🔴 "Address already in use" 에러

### 증상
```
ERROR: [Errno 98] Address already in use
```

### 원인
- systemd 서비스(`langchain-api.service`)가 이미 포트 8000에서 실행 중
- 수동으로 `uvicorn`을 실행하려고 시도하여 포트 충돌 발생

---

## ✅ 해결 방법

### 방법 1: systemd 서비스 사용 (권장)

**프로덕션 환경에서는 systemd 서비스를 사용하는 것이 좋습니다.**

#### 1. 서비스 상태 확인
```bash
# 서비스 상태 확인
sudo systemctl status langchain-api.service

# 실행 중인 프로세스 확인
sudo netstat -tlnp | grep 8000
# 또는
sudo ss -tlnp | grep 8000
```

#### 2. 서비스 로그 확인
```bash
# 최근 로그 확인
sudo journalctl -u langchain-api.service -n 50

# 실시간 로그 확인
sudo journalctl -u langchain-api.service -f

# 또는 애플리케이션 로그 확인
tail -f /var/log/langchain/error.log
tail -f /var/log/langchain/access.log
```

#### 3. 서비스 재시작
```bash
# 서비스 재시작
sudo systemctl restart langchain-api.service

# 상태 확인
sudo systemctl status langchain-api.service
```

#### 4. 서비스 중지 (수동 실행이 필요한 경우)
```bash
# 서비스 중지
sudo systemctl stop langchain-api.service

# 수동으로 실행 (개발/디버깅용)
cd /var/www/langchain
source venv/bin/activate
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --reload
```

---

### 방법 2: 다른 포트 사용 (개발/테스트용)

수동 실행이 필요한 경우 다른 포트를 사용:

```bash
# 포트 8001 사용
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 또는 포트 8080 사용
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

**주의:** 다른 포트를 사용하면 Nginx 설정도 변경해야 할 수 있습니다.

---

### 방법 3: 실행 중인 프로세스 종료

#### 포트를 사용하는 프로세스 찾기
```bash
# 포트 8000을 사용하는 프로세스 확인
sudo lsof -i :8000
# 또는
sudo fuser -k 8000/tcp
```

#### 프로세스 종료
```bash
# PID 확인 후 종료
sudo kill -9 <PID>

# 또는 강제 종료 (주의: 모든 uvicorn 프로세스 종료)
sudo pkill -f uvicorn
```

---

## 🔍 문제 진단 명령어

### 1. 포트 사용 확인
```bash
# 포트 8000 사용 확인
sudo netstat -tlnp | grep 8000
sudo ss -tlnp | grep 8000
sudo lsof -i :8000
```

### 2. systemd 서비스 확인
```bash
# 서비스 상태
sudo systemctl status langchain-api.service

# 서비스 활성화 여부
sudo systemctl is-enabled langchain-api.service

# 서비스 실행 여부
sudo systemctl is-active langchain-api.service
```

### 3. 프로세스 확인
```bash
# uvicorn 프로세스 확인
ps aux | grep uvicorn

# python 프로세스 확인
ps aux | grep python
```

---

## 📝 권장 워크플로우

### 프로덕션 환경
```bash
# 1. 코드 수정 후
cd /var/www/langchain
git pull  # 또는 파일 수정

# 2. 서비스 재시작
sudo systemctl restart langchain-api.service

# 3. 상태 확인
sudo systemctl status langchain-api.service
```

### 개발/디버깅 환경
```bash
# 1. 서비스 중지
sudo systemctl stop langchain-api.service

# 2. 수동 실행 (reload 모드)
cd /var/www/langchain
source venv/bin/activate
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --reload

# 3. 디버깅 완료 후 서비스 재시작
sudo systemctl start langchain-api.service
```

---

## ⚠️ 주의사항

1. **프로덕션에서는 systemd 서비스 사용 권장**
   - 자동 재시작
   - 로그 관리
   - 시스템 부팅 시 자동 시작

2. **수동 실행은 개발/디버깅용으로만 사용**
   - `--reload` 옵션은 개발용
   - 프로세스가 종료되면 서비스 중단

3. **포트 충돌 시**
   - 먼저 systemd 서비스 상태 확인
   - 필요시 서비스 중지 후 수동 실행

---

## 🚀 빠른 해결

```bash
# 1. 서비스 상태 확인
sudo systemctl status langchain-api.service

# 2. 서비스가 실행 중이면 그대로 사용
# 3. 수동 실행이 필요하면:
sudo systemctl stop langchain-api.service
cd /var/www/langchain
source venv/bin/activate
uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000 --reload
```

