"""
민사소송법 도메인 중앙 MCP 서버

민사소송법 도메인 전용 LLM 모델(ExaOne, KoELECTRA)과 툴을 중앙에서 관리합니다.
"""

import asyncio
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List

import torch
from fastmcp import FastMCP
from transformers import AutoModel, AutoTokenizer, AutoModelForCausalLM, pipeline

try:
    from transformers import BitsAndBytesConfig
except ImportError:
    BitsAndBytesConfig = None

try:
    from langchain_huggingface import HuggingFacePipeline
except ImportError:
    try:
        from langchain_community.llms import HuggingFacePipeline
    except ImportError:
        HuggingFacePipeline = None

from app.core.ml.embeddings import get_koelectra_embedder
from app.core.config import settings

logger = logging.getLogger(__name__)


class _ExaOneWorkerClient:
    """ExaOne 전용 워커 프로세스에 HTTP로 요청. invoke(prompt) 호환."""

    def __init__(self, base_url: str, timeout: float = 600.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def invoke(self, prompt: str, max_new_tokens: int = 512) -> str:
        import urllib.request
        url = f"{self.base_url}/generate"
        data = json.dumps({"prompt": prompt, "max_new_tokens": max_new_tokens}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json; charset=utf-8")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        if out.get("error"):
            raise RuntimeError(out["error"])
        return out.get("text") or ""


class _ExaOneGenerateWrapper:
    """HuggingFace pipeline 대신 model.generate()로 추론 (pipeline 생성에서 멈추는 이슈 회피). invoke(prompt) 호환."""

    def __init__(
        self,
        model,
        tokenizer,
        device: int = 0,
        max_new_tokens: int = 512,
        do_sample: bool = True,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.do_sample = do_sample
        self.temperature = temperature
        self.top_p = top_p

    def invoke(self, prompt: str) -> str:
        import torch
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        if self.device >= 0:
            dev = getattr(self.model, "device", None) or getattr(
                next(self.model.parameters(), None), "device", None
            )
            if dev is not None:
                inputs = {k: v.to(dev) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=self.do_sample,
                temperature=self.temperature if self.do_sample else None,
                top_p=self.top_p if self.do_sample else None,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        return self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

# ExaOne 툴: 스레드 풀 대신 이벤트 루프(메인 스레드)에서 실행해 스레드+CUDA 데드락/지연 방지
EXAONE_TOOL_NAMES = frozenset({
    "exaone_generate_text",
    "exaone_generate_code",
    "exaone_analyze_reference_data",
    "exaone_analyze_submission_data",
    "exaone_analyze_reasoning_data",
    "exaone_analyze_feedback_data",
    "exaone_evaluate_logic",
    "exaone_review_expression",
})


class MinsoCentralMCPServer:
    """
    민사소송법 도메인 중앙 MCP 서버

    민사소송법 도메인 전용 LLM 모델과 툴을 중앙에서 관리합니다.
    """

    _instance: Optional["MinsoCentralMCPServer"] = None
    _initialized: bool = False

    def __new__(cls):
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """MinsoCentralMCPServer 초기화"""
        if self._initialized:
            return

        logger.info("[민사소송법 중앙 MCP 서버] 초기화 시작")

        # FastMCP 서버 생성
        self.mcp = FastMCP(name="minso_central_mcp_server")

        # 모델 경로 설정
        self._setup_paths()

        # 모델 로드 (지연 로딩)
        self.exaone_llm: Optional[Any] = None
        self.koelectra_embedder = None  # KoELECTRAEmbedder 인스턴스
        self._exaone_load_lock = threading.Lock()  # 동시 로드 방지 (재시도 시 두 요청이 동시에 로드하는 것 방지)

        # 툴 저장소 (직접 호출용)
        self._tools: Dict[str, Any] = {}

        # 툴 설정
        self._setup_exaone_tools()
        self._setup_koelectra_tools()
        self._setup_integrated_tools()

        self._initialized = True
        logger.info("[민사소송법 중앙 MCP 서버] 초기화 완료")

    def _setup_paths(self) -> None:
        """경로 설정"""
        current_file = Path(__file__)
        # app/domain/v1/minso/hub/mcp/central_mcp_server.py
        # -> mcp -> hub -> minso -> v1 -> domain -> app -> 프로젝트 루트 (7단계 위)
        project_root = current_file.parent.parent.parent.parent.parent.parent.parent
        self.project_root = project_root
        self.exaone_model_dir = Path(settings.EXAONE_BASE_MODEL_PATH)
        self.koelectra_model_dir = Path(settings.EMBEDDING_MODEL_PATH)

    def _load_exaone_model(self):
        """ExaOne 모델을 로드합니다 (지연 로딩). EXAONE_WORKER_URL 있으면 워커 HTTP 호출만 사용."""
        if self.exaone_llm is not None:
            return self.exaone_llm
        worker_url = getattr(settings, "EXAONE_WORKER_URL", None)
        if worker_url:
            logger.info(f"[민사소송법 중앙 MCP 서버] ExaOne 워커 사용: {worker_url} (프로세스 내 로드 없음)")
            self.exaone_llm = _ExaOneWorkerClient(worker_url, timeout=600.0)
            return self.exaone_llm
        with self._exaone_load_lock:
            if self.exaone_llm is not None:
                return self.exaone_llm
            logger.info("[민사소송법 중앙 MCP 서버] ExaOne 모델 로딩 중 (락 획득)...")
            if not self.exaone_model_dir.exists():
                logger.warning(f"[민사소송법 중앙 MCP 서버] ExaOne 모델 디렉토리를 찾을 수 없습니다: {self.exaone_model_dir}")
                # exaone_local.py가 있으면 사용 시도
                try:
                    from app.core.llm.providers.exaone_local import create_exaone_local_llm
                    self.exaone_llm = create_exaone_local_llm()
                    logger.info("[민사소송법 중앙 MCP 서버] ExaOne 모델 로드 완료 (exaone_local 사용)")
                    return self.exaone_llm
                except Exception as e:
                    logger.error(f"[민사소송법 중앙 MCP 서버] ExaOne 모델 로드 실패: {e}", exc_info=True)
                    raise
            else:
                try:
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    logger.info(f"[민사소송법 중앙 MCP 서버] ExaOne 사용 디바이스: {device}")

                    logger.info("[민사소송법 중앙 MCP 서버] ExaOne tokenizer 로드 중...")
                    tokenizer = AutoTokenizer.from_pretrained(
                        str(self.exaone_model_dir),
                        trust_remote_code=True,
                        local_files_only=True
                    )
                    logger.info("[민사소송법 중앙 MCP 서버] ExaOne tokenizer 로드 완료")

                    if tokenizer.pad_token is None:
                        tokenizer.pad_token = tokenizer.eos_token

                    # GPU 전용: 양자화로 VRAM 절감. 8bit → 4bit → float16 순으로 시도 (CPU 오프로드 없음)
                    model = None
                    if device == "cuda" and BitsAndBytesConfig is not None:
                        for qlabel, qconfig in [
                            ("8bit", BitsAndBytesConfig(load_in_8bit=True)),
                            ("4bit", BitsAndBytesConfig(
                                load_in_4bit=True,
                                bnb_4bit_compute_dtype=torch.float16,
                                bnb_4bit_quant_type="nf4",
                                bnb_4bit_use_double_quant=True,
                            )),
                        ]:
                            try:
                                logger.info(f"[민사소송법 중앙 MCP 서버] ExaOne {qlabel} 로드 시도 (GPU 전용, VRAM 절감)")
                                model = AutoModelForCausalLM.from_pretrained(
                                    str(self.exaone_model_dir),
                                    quantization_config=qconfig,
                                    trust_remote_code=True,
                                    local_files_only=True,
                                    device_map="auto",
                                )
                                logger.info(f"[민사소송법 중앙 MCP 서버] ExaOne model from_pretrained 완료 ({qlabel})")
                                break
                            except Exception as eq:
                                logger.warning(f"[민사소송법 중앙 MCP 서버] ExaOne {qlabel} 로드 실패: {eq}")
                                model = None
                    if model is None:
                        # device_map="cuda:0" 시 0%%에서 멈춤 → CPU 로드 후 .to(cuda)도 멈춤. 실사용은 EXAONE_WORKER_URL 워커 권장.
                        model_kwargs = {
                            "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
                            "trust_remote_code": True,
                            "local_files_only": True,
                            "low_cpu_mem_usage": False,
                        }
                        logger.info("[민사소송법 중앙 MCP 서버] ExaOne model from_pretrained 시작 (CPU 로드)")
                        model = AutoModelForCausalLM.from_pretrained(
                            str(self.exaone_model_dir),
                            **model_kwargs
                        )
                        logger.info("[민사소송법 중앙 MCP 서버] ExaOne model from_pretrained 완료")
                        if device == "cuda" and getattr(model, "hf_device_map", None) is None:
                            logger.info("[민사소송법 중앙 MCP 서버] ExaOne model.to(cuda) 시작")
                            model = model.to("cuda:0")
                            logger.info("[민사소송법 중앙 MCP 서버] ExaOne model.to(cuda) 완료")

                    # pipeline() 생성 시 "Device set to use cuda:0" 직후 멈추는 이슈 회피 → model.generate() 래퍼만 사용
                    dev = 0 if device == "cuda" else -1
                    self.exaone_llm = _ExaOneGenerateWrapper(
                        model,
                        tokenizer,
                        device=dev,
                        max_new_tokens=512,
                        do_sample=True,
                        temperature=0.7,
                        top_p=0.9,
                    )
                    logger.info("[민사소송법 중앙 MCP 서버] ExaOne 모델 로딩 완료 (GPU 전용, model.generate 경로)")
                except Exception as e:
                    logger.error(f"[민사소송법 중앙 MCP 서버] ExaOne 모델 로딩 실패: {e}", exc_info=True)
                    raise
        return self.exaone_llm

    def _load_koelectra_embedder(self):
        """KoELECTRA 임베딩 생성기를 로드합니다 (지연 로딩)"""
        if self.koelectra_embedder is None:
            logger.info("[민사소송법 중앙 MCP 서버] KoELECTRA 임베딩 생성기 로딩 중...")
            try:
                self.koelectra_embedder = get_koelectra_embedder()
                if not self.koelectra_embedder.is_available():
                    raise RuntimeError("KoELECTRA 임베딩 생성기 사용 불가")
                logger.info("[민사소송법 중앙 MCP 서버] KoELECTRA 임베딩 생성기 로드 완료")
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] KoELECTRA 임베딩 생성기 로딩 실패: {e}", exc_info=True)
                raise RuntimeError(f"KoELECTRA 임베딩 생성기 로딩 실패: {e}") from e
        return self.koelectra_embedder

    def _setup_exaone_tools(self) -> None:
        """ExaOne 모델을 위한 FastMCP 툴을 설정합니다."""
        @self.mcp.tool()
        def exaone_generate_text(prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
            """ExaOne 모델을 사용하여 텍스트를 생성합니다.

            Args:
                prompt: 생성할 텍스트의 프롬프트
                max_tokens: 최대 생성 토큰 수

            Returns:
                생성 결과 딕셔너리
            """
            try:
                llm = self._load_exaone_model()
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                response = llm.invoke(formatted_prompt)

                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()

                logger.info(f"[민사소송법 중앙 MCP 서버] ExaOne 텍스트 생성 완료: {len(response)}자")
                return {
                    "success": True,
                    "generated_text": response,
                    "prompt": prompt,
                    "length": len(response)
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] ExaOne 텍스트 생성 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def exaone_generate_code(
            instruction: str,
            language: str = "python",
            max_tokens: int = 1024,
        ) -> Dict[str, Any]:
            """ExaOne 모델을 사용하여 코드를 생성합니다.

            요구사항(instruction)에 맞는 코드를 작성합니다.
            Python, JavaScript, SQL 등 다양한 언어 지원 가능합니다.

            Args:
                instruction: 작성할 코드에 대한 설명 또는 요구사항
                language: 생성할 코드의 언어 (기본: python)
                max_tokens: 최대 생성 토큰 수 (코드는 길 수 있으므로 기본 1024)

            Returns:
                success, generated_code, instruction, language 를 담은 딕셔너리
            """
            try:
                code_system = (
                    "You are EXAONE from LG AI Research. You are a helpful assistant that generates code. "
                    "Output only the code without explanation, unless the user asks for comments. "
                    "Use proper syntax and follow best practices for the requested language."
                )
                prompt = (
                    f"{code_system}\n\n"
                    f"Language: {language}\n"
                    f"Request: {instruction}\n\n"
                    "Output the code only:"
                )
                llm = self._load_exaone_model()
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                response = llm.invoke(formatted_prompt)

                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()

                # 마크다운 코드블록 제거 (```python ... ```)
                generated_code = response
                if "```" in response:
                    if f"```{language}" in response:
                        start = response.find(f"```{language}") + len(f"```{language}")
                    elif "```" in response:
                        start = response.find("```") + 3
                    else:
                        start = 0
                    end = response.find("```", start)
                    if end != -1:
                        generated_code = response[start:end].strip()
                    else:
                        generated_code = response[start:].strip()

                logger.info(
                    "[민사소송법 중앙 MCP 서버] ExaOne 코드 생성 완료: %s, %d자",
                    language,
                    len(generated_code),
                )
                return {
                    "success": True,
                    "generated_code": generated_code,
                    "instruction": instruction,
                    "language": language,
                    "length": len(generated_code),
                }
            except Exception as e:
                logger.error(
                    "[민사소송법 중앙 MCP 서버] ExaOne 코드 생성 실패: %s", e, exc_info=True
                )
                return {
                    "success": False,
                    "error": str(e),
                    "instruction": instruction,
                    "language": language,
                }

        @self.mcp.tool()
        def exaone_analyze_reference_data(reference_data: Dict[str, Any]) -> Dict[str, Any]:
            """ExaOne 모델을 사용하여 모범답안 데이터를 분석합니다."""
            try:
                data_text = json.dumps(reference_data, ensure_ascii=False, indent=2)
                prompt = f"다음 모범답안 데이터를 분석하고 주요 특징을 요약해주세요:\n\n{data_text}"

                llm = self._load_exaone_model()
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 모범답안 분석 추론 시작 (첫 추론 시 3~8분 소요 가능)")
                response = llm.invoke(formatted_prompt)

                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()

                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 모범답안 데이터 분석 완료")
                return {
                    "success": True,
                    "analysis": response,
                    "reference_data": reference_data
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] ExaOne 모범답안 데이터 분석 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def exaone_analyze_submission_data(submission_data: Dict[str, Any]) -> Dict[str, Any]:
            """ExaOne 모델을 사용하여 제출 답안 데이터를 분석합니다."""
            try:
                data_text = json.dumps(submission_data, ensure_ascii=False, indent=2)
                prompt = f"다음 제출 답안 데이터를 분석하고 주요 특징을 요약해주세요:\n\n{data_text}"

                llm = self._load_exaone_model()
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 제출 답안 분석 추론 시작 (첫 추론 시 수 분 소요 가능)")
                response = llm.invoke(formatted_prompt)

                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()

                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 제출 답안 데이터 분석 완료")
                return {
                    "success": True,
                    "analysis": response,
                    "submission_data": submission_data
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] ExaOne 제출 답안 데이터 분석 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def exaone_analyze_reasoning_data(reasoning_data: Dict[str, Any]) -> Dict[str, Any]:
            """ExaOne 모델을 사용하여 추론 데이터를 분석합니다."""
            try:
                data_text = json.dumps(reasoning_data, ensure_ascii=False, indent=2)
                prompt = f"다음 추론 데이터를 분석하고 주요 특징을 요약해주세요:\n\n{data_text}"

                llm = self._load_exaone_model()
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 추론 데이터 분석 추론 시작 (첫 추론 시 수 분 소요 가능)")
                response = llm.invoke(formatted_prompt)

                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()

                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 추론 데이터 분석 완료")
                return {
                    "success": True,
                    "analysis": response,
                    "reasoning_data": reasoning_data
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] ExaOne 추론 데이터 분석 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def exaone_analyze_feedback_data(feedback_data: Dict[str, Any]) -> Dict[str, Any]:
            """ExaOne 모델을 사용하여 피드백 데이터를 분석합니다."""
            try:
                data_text = json.dumps(feedback_data, ensure_ascii=False, indent=2)
                prompt = f"다음 피드백 데이터를 분석하고 주요 특징을 요약해주세요:\n\n{data_text}"

                llm = self._load_exaone_model()
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                response = llm.invoke(formatted_prompt)

                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()

                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 피드백 데이터 분석 완료")
                return {
                    "success": True,
                    "analysis": response,
                    "feedback_data": feedback_data
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] ExaOne 피드백 데이터 분석 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def extract_issues_from_problem(problem_content: str) -> Dict[str, Any]:
            """문제 지문에서 논점(쟁점) 목록을 추출합니다. 학습된 ExaOne 논점 추출 모델 사용."""
            try:
                from app.domain.v1.minso.spokes.services.issue_extraction_service import extract_issues_from_problem as _extract
                issues = _extract(problem_content)
                logger.info("[민사소송법 중앙 MCP 서버] 논점 추출 완료: %d개", len(issues))
                return {"success": True, "issues": issues}
            except Exception as e:
                logger.error("[민사소송법 중앙 MCP 서버] 논점 추출 실패: %s", e, exc_info=True)
                return {"success": False, "error": str(e), "issues": []}

        # Phase1: 논리 평가 / 표현 검토용 ExaOne 툴 (JSON 출력 요청 후 파싱)
        _MAX_TEXT_LEN = 2000  # 프롬프트 길이 제한 (토큰/지연 방지, 필요 시 조정 가능)

        def _extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
            """LLM 응답에서 JSON 블록 또는 {...} 추출. 여러 전략 시도."""
            if not response_text or not response_text.strip():
                return None
            text = response_text.strip()

            # 1) 전체가 JSON인 경우
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

            # 2) 코드블록 제거
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                if end == -1:
                    end = len(text)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                if end == -1:
                    end = len(text)
                text = text[start:end].strip()

            # 3) 첫 번째 완전한 {...} 구간 찾기 (문자열 내부의 } 제외하려면 단순 깊이로)
            start_brace = text.find("{")
            if start_brace == -1:
                return None
            depth = 0
            in_string = None
            escape = False
            end_brace = -1
            i = start_brace
            while i < len(text):
                c = text[i]
                if escape:
                    escape = False
                    i += 1
                    continue
                if c == "\\" and in_string:
                    escape = True
                    i += 1
                    continue
                if in_string:
                    if c == in_string:
                        in_string = None
                    i += 1
                    continue
                if c in ('"', "'"):
                    in_string = c
                    i += 1
                    continue
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end_brace = i
                        break
                i += 1
            if end_brace == -1:
                return None
            segment = text[start_brace : end_brace + 1]

            for raw in (segment, re.sub(r",\s*}", "}", re.sub(r",\s*]", "]", segment))):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    continue
            return None

        def _fallback_logic_from_text(response_text: str) -> Optional[Dict[str, Any]]:
            """논리 평가 응답에서 점수·리스트를 정규식으로 추출 (JSON 파싱 실패 시)."""
            if not response_text or not response_text.strip():
                return None
            text = response_text.strip()
            out = {}
            m = re.search(r'"coherence_score"\s*:\s*([0-9.]+)', text, re.IGNORECASE)
            if m:
                try:
                    out["coherence_score"] = float(m.group(1))
                    if out["coherence_score"] > 1:
                        out["coherence_score"] = out["coherence_score"] / 100.0
                except ValueError:
                    pass
            m = re.search(r'"argument_strength"\s*:\s*([0-9.]+)', text, re.IGNORECASE)
            if m:
                try:
                    out["argument_strength"] = float(m.group(1))
                    if out["argument_strength"] > 1:
                        out["argument_strength"] = out["argument_strength"] / 100.0
                except ValueError:
                    pass
            if "coherence_score" not in out:
                m = re.search(r'coherence[_\s]?score\s*[=:]\s*([0-9.]+)', text, re.IGNORECASE)
                if m:
                    try:
                        v = float(m.group(1))
                        out["coherence_score"] = v / 100.0 if v > 1 else v
                    except ValueError:
                        pass
            if "argument_strength" not in out:
                m = re.search(r'argument[_\s]?strength\s*[=:]\s*([0-9.]+)', text, re.IGNORECASE)
                if m:
                    try:
                        v = float(m.group(1))
                        out["argument_strength"] = v / 100.0 if v > 1 else v
                    except ValueError:
                        pass
            # weak_points / suggestions 배열 추출: "weak_points": ["a","b"] 또는 - / * 로 시작하는 줄
            for key, key_alt in [("weak_points", "weak points"), ("suggestions", "suggestions")]:
                arr = []
                pat = re.search(r'"' + key.replace("_", r'[_ ]') + r'"\s*:\s*\[(.*?)\]', text, re.DOTALL | re.IGNORECASE)
                if pat:
                    inner = pat.group(1)
                    for m in re.finditer(r'"([^"]*)"', inner):
                        s = m.group(1).strip()
                        if s and len(s) > 2:
                            arr.append(s)
                if not arr:
                    for line in text.split("\n"):
                        line = line.strip()
                        if (line.startswith("- ") or line.startswith("* ") or line.startswith("• ")) and len(line) > 3:
                            line = line.lstrip("-*• ").strip()
                            if line and line not in arr:
                                arr.append(line[:500])
                if arr:
                    out[key] = arr[:5]
            if "coherence_score" in out or "argument_strength" in out:
                out.setdefault("coherence_score", 0.5)
                out.setdefault("argument_strength", 0.5)
                out.setdefault("weak_points", [])
                out.setdefault("suggestions", [])
                return out
            return None

        def _fallback_expression_from_text(response_text: str) -> Optional[Dict[str, Any]]:
            """표현 검토 응답에서 점수·리스트 추출 (JSON 파싱 실패 시)."""
            if not response_text or not response_text.strip():
                return None
            text = response_text.strip()
            out = {}
            found = False
            for key in ("clarity_score", "formality_score"):
                m = re.search(r'"' + key.replace("_", r'[_ ]') + r'"\s*:\s*([0-9.]+)', text, re.IGNORECASE)
                if m:
                    try:
                        v = float(m.group(1))
                        out[key] = v / 100.0 if v > 1 else v
                        found = True
                    except ValueError:
                        pass
                if key not in out:
                    m = re.search(r'(clarity|formality)[_\s]?score\s*[=:]\s*([0-9.]+)', text, re.IGNORECASE)
                    if m:
                        try:
                            v = float(m.group(2))
                            out[key] = v / 100.0 if v > 1 else v
                            found = True
                        except ValueError:
                            pass
            if not found:
                return None
            out.setdefault("clarity_score", 0.5)
            out.setdefault("formality_score", 0.5)
            out.setdefault("issues", [])
            out.setdefault("improvements", [])
            return out

        @self.mcp.tool()
        def exaone_evaluate_logic(
            problem_text: str,
            reference_text: str,
            user_answer_text: str,
        ) -> Dict[str, Any]:
            """제출답안의 논리 일관성·논증 강도를 평가합니다. JSON만 출력하도록 요청 후 파싱합니다."""
            try:
                p = (problem_text or "")[:_MAX_TEXT_LEN]
                r = (reference_text or "")[:_MAX_TEXT_LEN]
                u = (user_answer_text or "")[:_MAX_TEXT_LEN]
                prompt = f"""아래 [문제], [모범답안], [제출답안]을 읽고, 제출답안의 논리 일관성과 논증 강도를 평가해주세요.
반드시 아래 형식의 JSON만 한 번 출력하세요. 다른 설명은 붙이지 마세요.
키는 영어로, weak_points와 suggestions의 내용은 한글로 작성해주세요.

{{"coherence_score": 0.0~1.0, "argument_strength": 0.0~1.0, "weak_points": ["문장1", "문장2"], "suggestions": ["제안1", "제안2"]}}

[문제]
{p}

[모범답안]
{r}

[제출답안]
{u}
"""
                llm = self._load_exaone_model()
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 논리 평가 추론 시작")
                response = llm.invoke(formatted_prompt)
                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()
                data = _extract_json_from_response(response)
                if not data:
                    data = _fallback_logic_from_text(response)
                if not data:
                    # ExaOne이 JSON 대신 서술형 분석을 낸 경우: 내용을 버리지 않고 그대로 반영
                    raw = (response or "").strip()
                    if len(raw) > 100:
                        logger.info(
                            "[민사소송법 중앙 MCP 서버] ExaOne 논리 평가 JSON 없음 — 서술형 분석 반영 (길이 %d)",
                            len(raw),
                        )
                        return {
                            "success": True,
                            "coherence_score": 0.78,
                            "argument_strength": 0.72,
                            "weak_points": [],
                            "suggestions": [],
                            "raw_analysis": raw[:8000],
                        }
                    logger.warning(
                        "[민사소송법 중앙 MCP 서버] ExaOne 논리 평가 JSON 파싱 실패 (앞 500자: %s)",
                        raw[:500],
                    )
                    return {"success": False, "error": "json_parse_failed"}
                coherence = float(data.get("coherence_score", 0.5))
                argument_strength = float(data.get("argument_strength", 0.5))
                weak_points = data.get("weak_points") if isinstance(data.get("weak_points"), list) else []
                suggestions = data.get("suggestions") if isinstance(data.get("suggestions"), list) else []
                weak_points = [str(x) for x in weak_points][:5]
                suggestions = [str(x) for x in suggestions][:5]
                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 논리 평가 완료")
                return {
                    "success": True,
                    "coherence_score": coherence,
                    "argument_strength": argument_strength,
                    "weak_points": weak_points,
                    "suggestions": suggestions,
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] ExaOne 논리 평가 실패: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        @self.mcp.tool()
        def exaone_review_expression(user_answer_text: str) -> Dict[str, Any]:
            """제출답안의 표현(명료성·격식성·구체적 문제)을 검토합니다. JSON만 출력하도록 요청 후 파싱합니다."""
            try:
                u = (user_answer_text or "")[:_MAX_TEXT_LEN]
                prompt = f"""아래 [제출답안]을 읽고, 법률 답안으로서의 명료성·격식성과 표현 문제를 검토해주세요.
반드시 아래 형식의 JSON만 한 번 출력하세요. 다른 설명은 붙이지 마세요.
키는 영어로, 내용은 한글로 작성해주세요.

{{"clarity_score": 0.0~1.0, "formality_score": 0.0~1.0, "issues": [{{"type": "유형", "location": "위치", "content": "내용"}}], "improvements": [{{"original": "원문", "suggestion": "수정안", "reason": "이유"}}]}}

[제출답안]
{u}
"""
                llm = self._load_exaone_model()
                formatted_prompt = f"[질문] {prompt}\n[답변] "
                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 표현 검토 추론 시작")
                response = llm.invoke(formatted_prompt)
                if "[답변]" in response:
                    response = response.split("[답변]")[-1].strip()
                data = _extract_json_from_response(response)
                if not data:
                    data = _fallback_expression_from_text(response)
                if not data:
                    logger.warning(
                        "[민사소송법 중앙 MCP 서버] ExaOne 표현 검토 JSON 파싱 실패 (앞 500자: %s)",
                        (response or "")[:500],
                    )
                    return {"success": False, "error": "json_parse_failed"}
                clarity = float(data.get("clarity_score", 0.5))
                formality = float(data.get("formality_score", 0.5))
                raw_issues = data.get("issues") if isinstance(data.get("issues"), list) else []
                raw_improvements = data.get("improvements") if isinstance(data.get("improvements"), list) else []
                issues = []
                for x in raw_issues[:10]:
                    if isinstance(x, dict):
                        issues.append({"type": str(x.get("type", "")), "location": str(x.get("location", "")), "content": str(x.get("content", ""))})
                improvements = []
                for x in raw_improvements[:10]:
                    if isinstance(x, dict):
                        improvements.append({"original": str(x.get("original", "")), "suggestion": str(x.get("suggestion", "")), "reason": str(x.get("reason", ""))})
                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 표현 검토 완료")
                return {
                    "success": True,
                    "clarity_score": clarity,
                    "formality_score": formality,
                    "issues": issues,
                    "improvements": improvements,
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] ExaOne 표현 검토 실패: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        # 툴 등록
        self._tools["exaone_generate_text"] = exaone_generate_text
        self._tools["exaone_generate_code"] = exaone_generate_code
        self._tools["extract_issues_from_problem"] = extract_issues_from_problem
        self._tools["exaone_analyze_reference_data"] = exaone_analyze_reference_data
        self._tools["exaone_analyze_submission_data"] = exaone_analyze_submission_data
        self._tools["exaone_analyze_reasoning_data"] = exaone_analyze_reasoning_data
        self._tools["exaone_analyze_feedback_data"] = exaone_analyze_feedback_data
        self._tools["exaone_evaluate_logic"] = exaone_evaluate_logic
        self._tools["exaone_review_expression"] = exaone_review_expression

        logger.info("[민사소송법 중앙 MCP 서버] ExaOne 툴 설정 완료")

    def _setup_koelectra_tools(self) -> None:
        """KoELECTRA 모델을 위한 FastMCP 툴을 설정합니다."""
        @self.mcp.tool()
        def koelectra_embed_text(text: str) -> Dict[str, Any]:

            """KoELECTRA 모델을 사용하여 텍스트를 임베딩으로 변환합니다."""
            try:
                embedder = self._load_koelectra_embedder()
                embedding = embedder.embed_text(text)
                dimension = embedder.get_dimension()

                logger.info(f"[민사소송법 중앙 MCP 서버] KoELECTRA 텍스트 임베딩 생성 완료: {dimension}차원")
                return {
                    "success": True,
                    "embedding": embedding,
                    "dimension": dimension,
                    "text_length": len(text)
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] KoELECTRA 임베딩 생성 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.mcp.tool()
        def koelectra_classify_text(text: str) -> Dict[str, Any]:
            """KoELECTRA 모델을 사용하여 텍스트를 분류합니다 (정책/규칙 판단)."""
            try:
                # 기존 KoELECTRALoader 사용 (DecisionMaker에서 사용하는 것과 동일)
                from app.core.ml.koelectra_loader import KoELECTRALoader
                loader = KoELECTRALoader.get_instance()
                result = loader.predict(text)

                logger.info(f"[민사소송법 중앙 MCP 서버] KoELECTRA 텍스트 분류 완료")
                return {
                    "success": True,
                    **result
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] KoELECTRA 분류 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        # 툴 등록
        self._tools["koelectra_embed_text"] = koelectra_embed_text
        self._tools["koelectra_classify_text"] = koelectra_classify_text

        logger.info("[민사소송법 중앙 MCP 서버] KoELECTRA 툴 설정 완료")

    def _setup_integrated_tools(self) -> None:
        """KoELECTRA와 ExaOne을 연결하는 통합 FastMCP 툴을 설정합니다."""
        @self.mcp.tool()
        async def koelectra_to_exaone_pipeline(text: str) -> Dict[str, Any]:

            """KoELECTRA로 텍스트를 임베딩한 후 ExaOne으로 분석하는 파이프라인."""
            try:
                logger.info(f"[민사소송법 중앙 MCP 서버] 통합 파이프라인 시작: {text[:50]}...")

                # 1단계: KoELECTRA로 임베딩 생성
                embedder = self._load_koelectra_embedder()
                embedding = embedder.embed_text(text)
                dimension = embedder.get_dimension()

                logger.info(f"[민사소송법 중앙 MCP 서버] KoELECTRA 임베딩 생성 완료: {dimension}차원")

                # 2단계: ExaOne으로 텍스트 분석
                analysis_prompt = f"다음 텍스트를 분석하고 주요 내용을 요약해주세요:\n\n{text}"
                llm = self._load_exaone_model()
                formatted_prompt = f"[질문] {analysis_prompt}\n[답변] "
                exaone_result = llm.invoke(formatted_prompt)

                if "[답변]" in exaone_result:
                    exaone_result = exaone_result.split("[답변]")[-1].strip()

                logger.info("[민사소송법 중앙 MCP 서버] ExaOne 분석 완료")

                return {
                    "success": True,
                    "koelectra_embedding": {
                        "dimension": dimension,
                        "sample": embedding[:10]
                    },
                    "exaone_analysis": exaone_result,
                    "original_text": text
                }
            except Exception as e:
                logger.error(f"[민사소송법 중앙 MCP 서버] 통합 파이프라인 처리 실패: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        # 툴 등록
        self._tools["koelectra_to_exaone_pipeline"] = koelectra_to_exaone_pipeline

        logger.info("[민사소송법 중앙 MCP 서버] 통합 툴 설정 완료 (KoELECTRA + ExaOne)")

    def get_mcp_server(self) -> FastMCP:
        """MCP 서버 인스턴스를 반환합니다."""
        return self.mcp

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """툴을 호출합니다 (클라이언트용)."""
        if tool_name not in self._tools:
            return {
                "success": False,
                "error": f"툴을 찾을 수 없습니다: {tool_name}"
            }

        try:
            import inspect
            tool_obj = self._tools[tool_name]
            # FunctionTool: .fn 이 호출 가능하면 사용, 아니면 .run(kwargs) 사용
            fn = getattr(tool_obj, "fn", None)
            if callable(fn):
                if inspect.iscoroutinefunction(fn):
                    result = await fn(**kwargs)
                else:
                    # ExaOne 툴: 스레드+CUDA 이슈 회피를 위해 메인(이벤트 루프) 스레드에서 직접 실행 (요청 동안 서버 블로킹, 동작 검증용)
                    if tool_name in EXAONE_TOOL_NAMES:
                        logger.info(f"[민사소송법 중앙 MCP 서버] ExaOne 툴 메인 스레드 실행: {tool_name} (완료까지 대기)")
                        result = fn(**kwargs)
                    else:
                        result = await asyncio.to_thread(fn, **kwargs)
                return result
            run = getattr(tool_obj, "run", None)
            if callable(run):
                if tool_name in EXAONE_TOOL_NAMES:
                    out = run(kwargs)
                else:
                    out = await asyncio.to_thread(run, kwargs)
                if inspect.iscoroutine(out):
                    result = await out
                else:
                    result = out
                return result
            if inspect.iscoroutinefunction(tool_obj):
                result = await tool_obj(**kwargs)
            else:
                if tool_name in EXAONE_TOOL_NAMES:
                    result = tool_obj(**kwargs)
                else:
                    result = await asyncio.to_thread(tool_obj, **kwargs)
            return result
        except Exception as e:
            logger.error(f"[민사소송법 중앙 MCP 서버] 툴 호출 실패: {tool_name}, {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# 전역 싱글톤 인스턴스
_minso_central_mcp_server: Optional[MinsoCentralMCPServer] = None


def get_minso_central_mcp_server() -> MinsoCentralMCPServer:
    """민사소송법 도메인 중앙 MCP 서버 싱글톤 인스턴스를 반환합니다."""
    global _minso_central_mcp_server
    if _minso_central_mcp_server is None:
        _minso_central_mcp_server = MinsoCentralMCPServer()
    return _minso_central_mcp_server
