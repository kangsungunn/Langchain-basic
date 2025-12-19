# 🚀 CI/CD 배포 시작하기

## ⚡ 빠른 시작 (30분)

### 1단계: GitHub Secrets 설정 (5분) ⭐ 먼저 하세요!

GitHub Repository → Settings → Secrets and variables → Actions

**추가할 5개 Secrets:**

| Name | Value |
|------|-------|
| `EC2_HOST` | `ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com` |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | kang.pem 파일 전체 내용 |
| `OPENAI_API_KEY` | 실제 OpenAI API 키 |
| `POSTGRES_PASSWORD` | Neon PostgreSQL 비밀번호 |

**EC2_SSH_KEY 가져오기:**
```powershell
# PowerShell에서
Get-Content kang.pem
# 출력된 전체 내용을 복사 (-----BEGIN RSA PRIVATE KEY----- 포함)
```

---

### 2단계: EC2 초기 설정 (10분)

#### Option A: 스크립트 사용 (권장)

```bash
# 1. EC2 접속
ssh -i "kang.pem" ubuntu@ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com

# 2. 스크립트 다운로드 및 실행
wget https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/quick-ec2-setup.sh
chmod +x quick-ec2-setup.sh
./quick-ec2-setup.sh
```

#### Option B: 수동 설정

`ec2-setup-commands.txt` 파일의 명령어들을 순서대로 복사하여 실행

---

### 3단계: 코드 배포 (EC2에서)

```bash
# 1. 저장소 클론 (YOUR_USERNAME/YOUR_REPO를 실제 값으로 변경)
cd /var/www/langchain
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git .

# 2. .env 파일 편집 (실제 값 입력)
nano /var/www/langchain/.env
# Ctrl+X, Y, Enter로 저장

# 3. 의존성 설치
source venv/bin/activate
pip install -r requirements.txt

# 4. 서비스 시작
sudo systemctl start langchain-api.service

# 5. 상태 확인
sudo systemctl status langchain-api.service

# 6. 헬스 체크
curl http://localhost:8000/health
```

---

### 4단계: 자동 배포 테스트 (로컬에서)

```bash
# 변경사항 푸시
git add .
git commit -m "feat: setup CI/CD"
git push origin main
```

GitHub Actions 확인: `https://github.com/YOUR_USERNAME/YOUR_REPO/actions`

---

## ✅ 배포 확인

```bash
# 외부 접속 테스트
curl http://ec2-54-180-124-217.ap-northeast-2.compute.amazonaws.com/health

# 응답 예시: {"status":"healthy","message":"RAG Chatbot API is running"}
```

---

## 🔧 유용한 명령어 (EC2에서)

```bash
# 로그 실시간 확인
sudo journalctl -u langchain-api.service -f

# 서비스 재시작
sudo systemctl restart langchain-api.service

# 서비스 상태 확인
sudo systemctl status langchain-api.service

# 최근 50줄 로그
sudo journalctl -u langchain-api.service -n 50

# Nginx 로그
sudo tail -f /var/log/nginx/access.log

# 포트 확인
sudo netstat -tlnp | grep 8000
```

---

## 🆘 트러블슈팅

### 문제: 서비스가 시작되지 않음

```bash
# 로그 확인
sudo journalctl -u langchain-api.service -n 100

# 권한 확인
sudo chown -R ubuntu:ubuntu /var/www/langchain
```

### 문제: Nginx 502 Bad Gateway

```bash
# FastAPI 서비스 확인
sudo systemctl status langchain-api.service

# 포트 확인
sudo netstat -tlnp | grep 8000
```

### 문제: GitHub Actions 배포 실패

1. GitHub Secrets 확인 (특히 EC2_SSH_KEY)
2. EC2에서 Git pull이 되는지 확인
3. Actions 탭의 로그 확인

---

## 🎉 성공하면...

이제 `main` 브랜치에 푸시할 때마다 자동으로 EC2에 배포됩니다!

1. 코드 수정
2. `git push origin main`
3. GitHub Actions가 자동 배포
4. 헬스 체크로 확인

---

## 📚 추가 문서

- 상세 가이드: `strategy/21_CICD_DEPLOYMENT_STRATEGY.md`
- 배포 가이드: `DEPLOYMENT_GUIDE.md`
- EC2 설정: `ec2-setup-commands.txt`

---

**문제가 발생하면:** `scripts/rollback.sh` 실행

