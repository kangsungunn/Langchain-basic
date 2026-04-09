"""
ExaOne 전용 워커 프로세스

웹 서버(uvicorn)와 같은 프로세스에서 ExaOne 로드/추론 시 CUDA에서 멈추는 문제를 피하기 위해,
이 스크립트를 별도 프로세스로 실행해 모델을 한 번만 로드하고 HTTP로 생성 요청을 처리합니다.

사용법:
  1. 터미널 1: python scripts/exaone_worker.py   (또는 EXAONE_WORKER_PORT=8765 python scripts/exaone_worker.py)
  2. 터미널 2: set EXAONE_WORKER_URL=http://127.0.0.1:8765 && run_backend.ps1

API:
  POST /generate
  Body: {"prompt": "[질문] ...\\n[답변] ", "max_new_tokens": 512}
  Response: {"text": "생성된 텍스트", "error": null} 또는 {"text": null, "error": "메시지"}
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# 프로젝트 루트를 path에 추가 (모델 경로 기본값용)
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 환경 변수
EXAONE_MODEL_PATH = os.getenv(
    "EXAONE_BASE_MODEL_PATH",
    str(REPO_ROOT / "artifacts" / "models" / "base" / "exaone-2.4b"),
)
PORT = int(os.getenv("EXAONE_WORKER_PORT", "8765"))
HOST = os.getenv("EXAONE_WORKER_HOST", "127.0.0.1")

# 전역 모델/토크나이저 (서버 시작 전 한 번만 로드)
_model = None
_tokenizer = None


def load_model():
    """ExaOne 모델·토크나이저 로드 (이 프로세스에서 한 번만)."""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[ExaOne Worker] Loading model from {EXAONE_MODEL_PATH} ...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(
        EXAONE_MODEL_PATH,
        trust_remote_code=True,
        local_files_only=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[ExaOne Worker] Device: {device}", flush=True)

    model = AutoModelForCausalLM.from_pretrained(
        EXAONE_MODEL_PATH,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        trust_remote_code=True,
        local_files_only=True,
        low_cpu_mem_usage=False,
    )
    model = model.to(device)
    print("[ExaOne Worker] Model loaded.", flush=True)

    _model, _tokenizer = model, tokenizer
    return _model, _tokenizer


def generate(prompt: str, max_new_tokens: int = 512) -> str:
    import torch
    model, tokenizer = load_model()
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
    dev = next(model.parameters()).device
    inputs = {k: v.to(dev) for k, v in inputs.items()}
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


class GenerateHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/generate":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
            prompt = data.get("prompt", "")
            max_new_tokens = int(data.get("max_new_tokens", 512))
            if not prompt:
                self._send_json(400, {"text": None, "error": "prompt required"})
                return
            text = generate(prompt, max_new_tokens=max_new_tokens)
            self._send_json(200, {"text": text, "error": None})
        except Exception as e:
            self._send_json(500, {"text": None, "error": str(e)})

    def _send_json(self, status: int, obj: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        print(f"[ExaOne Worker] {args[0]}", flush=True)


def main():
    load_model()
    server = HTTPServer((HOST, PORT), GenerateHandler)
    print(f"[ExaOne Worker] Listening on http://{HOST}:{PORT}/generate", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
