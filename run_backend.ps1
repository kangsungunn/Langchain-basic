conda activate torch313
Write-Host "Backend starting (uvicorn loading...) - wait a few seconds" -ForegroundColor Cyan
# 프로젝트 루트에서 실행 (app 디렉토리로 이동하지 않음)
# --workers 1: ExaOne은 프로세스당 1개만 로드. 여러 워커 시 GPU/메모리 충돌·500 에러 가능
# -u: unbuffered 출력 (로그가 바로 보이도록)
python -u -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --workers 1
