"""
PDF 파싱 유틸리티

PDF 파일에서 문제와 모범답안을 추출하는 서비스
"""

import re
from typing import List, Dict, Optional
from pathlib import Path

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from app.core.utils.logger import get_logger

logger = get_logger()


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    PDF 파일에서 전체 텍스트를 추출합니다.
    문제 PDF 업로드 시 지문 추출용 (텍스트 레이어 있는 PDF만 지원).
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber가 필요합니다. pip install pdfplumber")
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF 파일 없음: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        parts = []
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts).strip() if parts else ""


class PDFParser:
    """PDF 파일 파싱 서비스"""

    def __init__(self):
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError(
                "pdfplumber가 설치되지 않았습니다. "
                "pip install pdfplumber 를 실행해주세요."
            )

    def parse_training_pdf(
        self,
        pdf_path: str,
        problem_pattern: Optional[str] = None,
        reference_answer_pattern: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        PDF 파일에서 학습 데이터 추출

        Args:
            pdf_path: PDF 파일 경로
            problem_pattern: 문제 시작 패턴 (기본: "문제", "Q", "Question" 등)
            reference_answer_pattern: 모범답안 시작 패턴 (기본: "모범답안", "정답", "Answer" 등)

        Returns:
            [
                {
                    "problem_text": "문제 내용...",
                    "reference_answer_text": "모범답안 내용...",
                    "user_answer_text": "",  # 빈 값 (사용자 답안 없음)
                    "labels": {}  # 빈 라벨 (사용자가 나중에 추가)
                },
                ...
            ]
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

        # 기본 패턴 설정
        if problem_pattern is None:
            problem_pattern = r"(문제\s*\d*|Q\d*|Question\s*\d*|^\d+\.\s*문제)"

        if reference_answer_pattern is None:
            reference_answer_pattern = r"(모범답안|정답|Answer|Reference\s*Answer|해설)"

        results = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                # 전체 텍스트 추출
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"

                if not full_text.strip():
                    # 텍스트 레이어가 없는 경우 (이미지 기반 PDF)
                    logger.warning(
                        f"PDF에서 텍스트를 추출할 수 없습니다 (이미지 기반 PDF일 가능성): {pdf_path}\n"
                        f"이 PDF는 스캔본이거나 이미지로만 구성되어 있어 OCR이 필요합니다.\n"
                        f"현재는 텍스트 레이어가 있는 PDF만 지원합니다.\n"
                        f"대안: 1) PDF를 텍스트로 변환하여 JSONL로 수동 입력, 2) OCR 기능 추가 필요"
                    )
                    raise ValueError(
                        "이 PDF는 이미지 기반 PDF입니다. 텍스트 레이어가 없어 자동 추출이 불가능합니다.\n"
                        "해결 방법:\n"
                        "1. PDF를 텍스트로 변환하여 JSONL 파일로 수동 입력 (권장)\n"
                        "2. OCR 기능 추가 필요 (Tesseract 또는 AWS Textract)"
                    )

                # 문제와 모범답안 분리
                training_data = self._extract_problems_and_answers(
                    full_text,
                    problem_pattern,
                    reference_answer_pattern
                )

                for data in training_data:
                    results.append({
                        "problem_text": data.get("problem_text", "").strip(),
                        "reference_answer_text": data.get("reference_answer_text", "").strip(),
                        "user_answer_text": "",  # 사용자 답안 없음
                        "labels": {}  # 빈 라벨 (사용자가 나중에 JSONL로 추가 가능)
                    })

                logger.info(f"PDF에서 {len(results)}개의 학습 데이터를 추출했습니다: {pdf_path}")

        except Exception as e:
            logger.error(f"PDF 파싱 실패: {pdf_path}, 오류: {str(e)}")
            raise

        return results

    def _extract_problems_and_answers(
        self,
        text: str,
        problem_pattern: str,
        reference_answer_pattern: str
    ) -> List[Dict[str, str]]:
        """
        텍스트에서 문제와 모범답안 추출

        전략:
        1. 문제 패턴으로 시작하는 섹션 찾기
        2. 다음 문제 또는 모범답안 패턴까지가 문제 내용
        3. 모범답안 패턴으로 시작하는 섹션 찾기
        4. 다음 문제 패턴까지가 모범답안 내용
        """
        results = []

        # 문제 패턴 찾기
        problem_matches = list(re.finditer(problem_pattern, text, re.IGNORECASE | re.MULTILINE))
        answer_matches = list(re.finditer(reference_answer_pattern, text, re.IGNORECASE | re.MULTILINE))

        if not problem_matches:
            # 패턴이 없으면 전체를 하나의 문제+답안으로 처리
            logger.warning("문제 패턴을 찾을 수 없어 전체 텍스트를 하나의 항목으로 처리합니다.")
            # 텍스트를 반으로 나누어 문제와 답안으로 간주
            mid_point = len(text) // 2
            results.append({
                "problem_text": text[:mid_point].strip(),
                "reference_answer_text": text[mid_point:].strip()
            })
            return results

        # 문제와 답안 매칭
        for i, problem_match in enumerate(problem_matches):
            problem_start = problem_match.start()

            # 다음 문제 또는 답안 패턴 찾기
            next_problem_start = None
            if i + 1 < len(problem_matches):
                next_problem_start = problem_matches[i + 1].start()

            # 해당 문제의 답안 찾기
            answer_start = None
            answer_end = None

            for answer_match in answer_matches:
                if answer_match.start() > problem_start:
                    answer_start = answer_match.start()
                    # 다음 문제나 답안까지가 답안 내용
                    if next_problem_start and next_problem_start < answer_match.start():
                        continue
                    # 다음 문제나 답안까지 찾기
                    for next_match in list(problem_matches) + list(answer_matches):
                        if next_match.start() > answer_match.start():
                            answer_end = next_match.start()
                            break
                    if answer_end is None:
                        answer_end = len(text)
                    break

            # 문제 텍스트 추출
            if answer_start:
                problem_text = text[problem_start:answer_start].strip()
            elif next_problem_start:
                problem_text = text[problem_start:next_problem_start].strip()
            else:
                problem_text = text[problem_start:].strip()

            # 문제 패턴 제거
            problem_text = re.sub(problem_pattern, "", problem_text, count=1, flags=re.IGNORECASE).strip()

            # 모범답안 텍스트 추출
            reference_answer_text = ""
            if answer_start and answer_end:
                answer_text = text[answer_start:answer_end].strip()
                # 답안 패턴 제거
                reference_answer_text = re.sub(
                    reference_answer_pattern,
                    "",
                    answer_text,
                    count=1,
                    flags=re.IGNORECASE
                ).strip()

            if problem_text and reference_answer_text:
                results.append({
                    "problem_text": problem_text,
                    "reference_answer_text": reference_answer_text
                })
            elif problem_text:
                # 답안이 없으면 문제만 저장
                results.append({
                    "problem_text": problem_text,
                    "reference_answer_text": ""
                })

        # 문제와 답안이 쌍으로 없는 경우 처리
        if not results and problem_matches:
            # 첫 번째 문제부터 마지막까지를 하나로 처리
            first_problem_start = problem_matches[0].start()
            results.append({
                "problem_text": text[first_problem_start:].strip(),
                "reference_answer_text": ""
            })

        return results


def parse_pdf(pdf_path: str) -> List[Dict[str, str]]:
    """
    편의 함수: PDF 파일 파싱

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        학습 데이터 리스트
    """
    parser = PDFParser()
    return parser.parse_training_pdf(pdf_path)
