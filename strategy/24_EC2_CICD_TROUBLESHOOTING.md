# EC2 CI/CD 배포 트러블슈팅 가이드

## 📋 개요

GitHub Actions를 통한 EC2 배포 시 발생할 수 있는 문제와 해결 방법을 정리한 가이드입니다.

---

## 🔴 주요 에러 및 해결 방법

### 1. "Add EC2 to known hosts" 실패

**증상:**
```
Error: Process completed with exit code 1
getaddrinfo: Name or service not known
```

**원인:**
- `ssh-keyscan` 명령이 호스트명을 해석하지 못함
- EC2 인스턴스가 실행 중이 아니거나 접근 불가
- 네트워크 연결 문제

**해결 방법:**

#### 방법 1: GitHub Secrets 확인

1. **EC2_HOST Secret 확인**
   - GitHub 저장소 → Settings → Secrets and variables → Actions
   - `EC2_HOST` 값 확인:
     ```
     ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com
     ```
   - **주의사항:**
     - 앞뒤 공백 없어야 함
     - 한 줄만 있어야 함
     - 호스트명만 포함 (사용자명, 키 파일명 등 포함하지 않음)

2. **EC2_SSH_KEY Secret 확인**
   - SSH 키 파일 전체 내용이 포함되어 있는지 확인
   - `-----BEGIN RSA PRIVATE KEY-----` 부터 `-----END RSA PRIVATE KEY-----` 까지
   - 개행 문자가 포함되어야 함

3. **EC2_USER Secret 확인**
   - 값: `ubuntu` (한 줄)

#### 방법 2: EC2 인스턴스 상태 확인

```bash
# AWS 콘솔에서 확인
1. EC2 Dashboard → Instances
2. 인스턴스 상태가 "running"인지 확인
3. Public IP 주소 확인
```

#### 방법 3: Security Group 설정 확인

EC2 Security Group에서 다음을 허용해야 합니다:

**Inbound Rules:**
- Type: SSH
- Protocol: TCP
- Port: 22
- Source: `0.0.0.0/0` (또는 GitHub Actions IP 범위)

**GitHub Actions IP 범위 (선택사항):**
```
# GitHub Actions는 동적 IP를 사용하므로
# 보안을 위해 특정 IP로 제한하기 어렵습니다
# 따라서 0.0.0.0/0을 허용하되, SSH 키 인증으로 보안을 유지합니다
```

#### 방법 4: 로컬에서 SSH 연결 테스트

```bash
# 로컬에서 직접 SSH 연결 테스트
ssh -i "kang.pem" ubuntu@ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com

# 연결이 성공하면:
# - EC2 인스턴스는 정상
# - SSH 키는 정상
# - 문제는 GitHub Actions 설정에 있음
```

---

### 2. "Test SSH connection" 실패

**증상:**
```
❌ SSH connection test failed
```

**원인:**
- EC2 인스턴스가 실행 중이 아님
- Security Group이 SSH 접근을 차단
- SSH 키가 잘못됨

**해결 방법:**

1. **EC2 인스턴스 재시작**
   ```bash
   # AWS 콘솔에서
   EC2 Dashboard → Instances → 인스턴스 선택 → Instance state → Reboot
   ```

2. **Security Group 확인**
   - Inbound Rules에 SSH (포트 22) 허용 확인

3. **SSH 키 확인**
   - 로컬에서 SSH 연결 테스트
   - 성공하면 키는 정상

---

### 3. "Deploy to EC2" 단계 실패

**증상:**
```
Permission denied (publickey)
```

**원인:**
- SSH 키가 잘못 설정됨
- EC2 인스턴스의 authorized_keys에 키가 없음

**해결 방법:**

1. **EC2_SSH_KEY Secret 재확인**
   - SSH 키 파일 전체 내용 복사
   - 앞뒤 공백 제거
   - 개행 문자 포함 확인

2. **EC2에서 authorized_keys 확인**
   ```bash
   # EC2에 직접 접속하여 확인
   ssh -i "kang.pem" ubuntu@ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com

   # authorized_keys 확인
   cat ~/.ssh/authorized_keys
   ```

---

### 4. "Health Check" 실패

**증상:**
```
❌ Health check failed with status 000
```

**원인:**
- FastAPI 서비스가 실행되지 않음
- Nginx가 실행되지 않음
- 포트 80이 열려있지 않음

**해결 방법:**

1. **EC2에서 서비스 상태 확인**
   ```bash
   # FastAPI 서비스 상태
   sudo systemctl status langchain-api.service

   # Nginx 상태
   sudo systemctl status nginx

   # 포트 리스닝 확인
   sudo netstat -tlnp | grep 8000
   sudo netstat -tlnp | grep 80
   ```

2. **서비스 재시작**
   ```bash
   sudo systemctl restart langchain-api.service
   sudo systemctl restart nginx
   ```

3. **Security Group 확인**
   - HTTP (포트 80) 허용 확인
   - HTTPS (포트 443) 허용 확인

---

## 🔧 워크플로우 개선 사항

### 현재 적용된 개선 사항

1. **에러 핸들링 강화**
   - Secret 값 검증
   - 명확한 에러 메시지
   - 단계별 디버깅 정보

2. **SSH 연결 개선**
   - `StrictHostKeyChecking=no` 사용
   - `ConnectTimeout=10` 설정
   - `ServerAliveInterval=60` 설정

3. **연결 테스트 단계 추가**
   - 배포 전 SSH 연결 테스트
   - 실패 시 명확한 안내 메시지

---

## 📝 체크리스트

배포 전 확인 사항:

### GitHub Secrets
- [ ] `EC2_HOST`: 정확한 호스트명 (공백 없음)
- [ ] `EC2_USER`: `ubuntu`
- [ ] `EC2_SSH_KEY`: SSH 키 전체 내용 (개행 포함)
- [ ] `OPENAI_API_KEY`: OpenAI API 키

### EC2 인스턴스
- [ ] 인스턴스 상태: `running`
- [ ] Public IP 주소 확인
- [ ] Security Group: SSH (22), HTTP (80) 허용

### EC2 서비스
- [ ] `/var/www/langchain` 디렉토리 존재
- [ ] Systemd 서비스 파일 존재
- [ ] Nginx 설정 파일 존재

---

## 🧪 로컬 테스트

배포 전 로컬에서 테스트:

```bash
# 1. SSH 연결 테스트
ssh -i "kang.pem" ubuntu@ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com "echo 'test'"

# 2. EC2에서 서비스 확인
ssh -i "kang.pem" ubuntu@ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com \
  "sudo systemctl status langchain-api.service"

# 3. 헬스 체크
curl http://ec2-43-201-10-181.ap-northeast-2.compute.amazonaws.com/health
```

---

## 🚀 빠른 해결 가이드

### 문제: ssh-keyscan 실패

**즉시 해결:**
1. GitHub Secrets의 `EC2_HOST` 값 확인
2. EC2 인스턴스가 실행 중인지 확인
3. Security Group에서 SSH 허용 확인

### 문제: SSH 연결 실패

**즉시 해결:**
1. 로컬에서 SSH 연결 테스트
2. `EC2_SSH_KEY` Secret 재확인
3. EC2 인스턴스 재시작

### 문제: 배포 후 헬스 체크 실패

**즉시 해결:**
1. EC2에서 서비스 상태 확인
2. 로그 확인: `sudo journalctl -u langchain-api.service -n 50`
3. Nginx 재시작: `sudo systemctl restart nginx`

---

## 📞 추가 도움말

### GitHub Actions 로그 확인

1. GitHub 저장소 → Actions 탭
2. 실패한 워크플로우 클릭
3. 실패한 단계 클릭하여 상세 로그 확인

### EC2 로그 확인

```bash
# Systemd 서비스 로그
sudo journalctl -u langchain-api.service -f

# Nginx 로그
sudo tail -f /var/log/nginx/error.log

# 애플리케이션 로그
tail -f /var/log/langchain/error.log
```

---

**작성일:** 2024-12-19
**버전:** 1.0

