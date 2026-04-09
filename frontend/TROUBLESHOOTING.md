# 프론트엔드 트러블슈팅 가이드

## 🔴 ECONNREFUSED 에러

### 증상
```
Upload error: TypeError: fetch failed
[cause]: AggregateError [ECONNREFUSED]
```

### 원인
백엔드 서버(`http://localhost:8000`)가 실행되지 않았습니다.

### 해결 방법

#### 1. 백엔드 서버 실행 확인

**방법 A: PowerShell에서 실행**
```powershell
# 프로젝트 루트에서
conda activate torch313
cd app
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**방법 B: main.py 직접 실행**
```powershell
conda activate torch313
cd app
python main.py
```

#### 2. 백엔드 서버 확인

브라우저에서 다음 URL 접속:
- API 문서: http://localhost:8000/api/v1/docs
- 헬스 체크: http://localhost:8000/health

#### 3. 환경 변수 확인

프론트엔드 `.env.local` 파일 확인:
```env
BACKEND_URL=http://localhost:8000
```

#### 4. 포트 충돌 확인

다른 프로세스가 8000 포트를 사용 중인지 확인:
```powershell
netstat -ano | findstr :8000
```

## ✅ 정상 작동 확인

### 백엔드 서버 실행 확인
```bash
curl http://localhost:8000/health
```

정상 응답 예시:
```json
{"status": "healthy"}
```

### 프론트엔드 실행 확인
1. 프론트엔드 서버 실행: `npm run dev`
2. 브라우저에서 http://localhost:3000 접속
3. 홈화면이 정상적으로 표시되는지 확인

## 📝 실행 순서

1. **백엔드 서버 먼저 실행**
   ```powershell
   conda activate torch313
   cd app
   python main.py
   ```

2. **프론트엔드 서버 실행** (새 터미널)
   ```powershell
   cd frontend
   npm run dev
   ```

3. **브라우저에서 테스트**
   - http://localhost:3000 접속
   - 파일 업로드 테스트

## ⚠️ 주의사항

- 백엔드 서버가 실행되지 않으면 프론트엔드에서 파일 업로드 시 `ECONNREFUSED` 에러가 발생합니다.
- 두 서버 모두 실행 중이어야 정상 작동합니다.
