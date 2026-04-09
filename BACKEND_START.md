# 백엔드 서버 실행 가이드

## ✅ 올바른 실행 방법

### 방법 1: 프로젝트 루트에서 실행 (권장)

```powershell
# 프로젝트 루트 (C:\Users\hi\Documents\rag)에서
conda activate torch313
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 방법 2: 스크립트 사용

```powershell
# 프로젝트 루트에서
.\run_backend.ps1
```

### 방법 3: main.py 직접 실행

```powershell
# 프로젝트 루트에서
conda activate torch313
python -m app.main
```

## ❌ 잘못된 실행 방법

```powershell
# ❌ app 디렉토리 안에서 실행하면 안 됩니다!
cd app
python main.py  # ModuleNotFoundError 발생!
```

## 🔍 확인 방법

서버가 정상적으로 실행되면:

1. **터미널에 다음 메시지 표시:**
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8000
   INFO:     Application startup complete.
   ```

2. **브라우저에서 확인:**
   - API 문서: http://localhost:8000/api/v1/docs
   - 헬스 체크: http://localhost:8000/health

## 📝 참고

- `app/main.py`는 `from app.core.config import settings`처럼 절대 경로로 import합니다
- 따라서 프로젝트 루트에서 실행해야 `app` 모듈을 찾을 수 있습니다
- `--reload` 옵션은 개발 중 코드 변경 시 자동 재시작합니다
