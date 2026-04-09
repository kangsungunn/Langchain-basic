# Vercel 500 에러 트러블슈팅 체크리스트

## 🔍 단계별 확인 방법

### 1단계: Vercel 함수 로그 확인 (가장 중요!)

1. **Vercel 대시보드 접속**
   - https://vercel.com/dashboard
   - 프로젝트 선택: `Langchain-basic`

2. **Deployments 페이지에서 최신 배포 클릭**
   - 목록에서 최상단 배포 (Current, Ready 상태) 클릭
   - 예: `Ed4C9gUXo`

3. **Functions 탭 또는 Runtime Logs 탭 클릭**
   - Functions 탭: API 라우트 실행 로그
   - Runtime Logs: 전체 런타임 로그

4. **에러 메시지 확인**
   - ✅ 찾아야 할 메시지: `⚠️ API_URL 환경 변수가 설정되지 않았습니다`
   - ✅ 다른 에러 메시지도 모두 확인

### 2단계: 환경 변수 확인 및 설정

1. **Vercel 대시보드 → Settings → Environment Variables**
   - 프로젝트 선택 → Settings 탭 → Environment Variables 섹션

2. **`API_URL` 변수 확인**
   - Key: `API_URL`
   - Value: `http://43.201.10.181:8000` (문서 기준)
   - Environment: Production, Preview, Development 모두 체크

3. **변수가 없거나 잘못된 경우**
   - Add New 버튼 클릭
   - Key: `API_URL`
   - Value: `http://43.201.10.181:8000`
   - Environment: 모두 선택
   - Save 클릭

4. **재배포**
   - Deployments → 최신 배포 → ... 메뉴 → Redeploy
   - 또는 코드 수정 후 새로 푸시

### 3단계: EC2 백엔드 서버 상태 확인

#### 방법 A: 브라우저에서 확인
```
http://43.201.10.181:8000/health
```
- 정상: JSON 응답 (`{"status":"healthy",...}`)
- 에러: 연결 실패, 타임아웃, 502/503 에러

#### 방법 B: 터미널에서 확인 (SSH 접속 가능한 경우)
```bash
# Health check
curl http://43.201.10.181:8000/health

# 서비스 상태
sudo systemctl status langchain-api.service

# 서비스 재시작 (필요시)
sudo systemctl restart langchain-api.service

# 최근 로그
sudo journalctl -u langchain-api.service -n 50
```

### 4단계: 네트워크 연결 확인

#### EC2 보안 그룹 확인
1. AWS 콘솔 → EC2 → Security Groups
2. 인바운드 규칙 확인
   - 포트: `8000`
   - 프로토콜: `TCP`
   - 소스: `0.0.0.0/0` (모든 IP 허용) 또는 특정 IP 범위

#### EC2 방화벽 확인 (SSH 접속 가능한 경우)
```bash
# 방화벽 상태
sudo ufw status

# 포트 8000 허용 (필요시)
sudo ufw allow 8000/tcp
```

### 5단계: 타임아웃 확인

- 코드에 60초 타임아웃 설정됨
- Vercel 로그에서 `⏱️ Request timeout` 메시지 확인
- 백엔드 응답이 60초 이상 걸리면 504 에러 발생

## 🎯 우선순위별 체크리스트

### 즉시 확인 (가장 가능성 높음)
- [ ] Vercel 함수 로그에서 에러 메시지 확인
- [ ] Vercel 환경 변수 `API_URL` 설정 확인
- [ ] 환경 변수 설정 후 재배포

### 다음 확인
- [ ] EC2 Health check: `http://43.201.10.181:8000/health`
- [ ] EC2 서비스 상태 확인
- [ ] EC2 보안 그룹 포트 8000 허용 확인

### 추가 확인
- [ ] 네트워크 타임아웃 확인
- [ ] CORS 설정 확인 (필요시)

## 📝 예상되는 에러 메시지와 해결 방법

### 에러 1: "API_URL 환경 변수가 설정되지 않았습니다"
**해결**: Vercel 환경 변수에 `API_URL` 추가 후 재배포

### 에러 2: "Failed to connect to backend server"
**해결**:
- EC2 서버가 실행 중인지 확인
- EC2 보안 그룹 포트 8000 허용 확인
- 네트워크 연결 확인

### 에러 3: "Request timeout"
**해결**:
- 백엔드 응답 시간 확인
- 필요시 타임아웃 시간 증가 (route.ts 수정)

### 에러 4: "Backend error: 502/503"
**해결**:
- EC2 서비스 재시작
- EC2 로그 확인

## 🔗 유용한 링크

- Vercel 대시보드: https://vercel.com/dashboard
- Vercel 환경 변수 설정: Settings → Environment Variables
- Vercel 함수 로그: Deployments → 배포 선택 → Functions 탭

