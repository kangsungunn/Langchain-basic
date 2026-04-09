@echo off
call conda activate torch313
REM 프로젝트 루트에서 실행 (app 디렉토리로 이동하지 않음)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

