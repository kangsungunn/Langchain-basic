# ExaOne 전용 워커 (별도 프로세스). 웹 서버와 같은 프로세스에서 CUDA 멈춤 회피용.
# 사용법: 터미널 1에서 이 스크립트 실행 후, 터미널 2에서 아래처럼 백엔드 실행
#   $env:EXAONE_WORKER_URL = "http://127.0.0.1:8765"
#   .\run_backend.ps1
conda activate torch313
$env:EXAONE_WORKER_PORT = "8765"
python scripts/exaone_worker.py
