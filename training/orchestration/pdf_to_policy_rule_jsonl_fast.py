"""
PDF를 정책/규칙 판별 학습 데이터(JSONL)로 변환하는 스크립트 (고속 버전)

PyPDF2를 사용하여 더 빠른 PDF 파싱
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.domain.v1.minso.hub.decision_maker import DecisionMaker
from app.core.utils.logger import get_logger

logger = get_logger()

# pypdf 사용 (PyPDF2의 후속 버전, 빠름)
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    try:
        import PyPDF2 as pypdf  # 폴백: PyPDF2 사용
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False


class FastPDFParser:
    """빠른 PDF 파서 (PyPDF2/pypdf 사용)"""

    def __init__(self):
        if not PYPDF_AVAILABLE:
            raise ImportError(
                "pypdf가 설치되지 않았습니다. "
                "pip install pypdf 를 실행해주세요."
            )

    def extract_text(self, pdf_path: Path) -> str:
        """
        PDF에서 텍스트 추출 (빠른 버전)

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            전체 텍스트
        """
        full_text = ""

        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)

                # 모든 페이지에서 텍스트 추출
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            full_text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"[WARN] 페이지 {page_num+1} 텍스트 추출 실패: {e}")
                        continue

                logger.info(f"[OK] PDF 텍스트 추출 완료: {len(pdf_reader.pages)}페이지")

        except Exception as e:
            logger.error(f"[ERROR] PDF 읽기 실패: {e}")
            raise

        if not full_text.strip():
            raise ValueError(
                "PDF에서 텍스트를 추출할 수 없습니다. "
                "이 PDF는 이미지 기반 PDF일 수 있습니다."
            )

        return full_text

    def parse_training_pdf(
        self,
        pdf_path: str,
        problem_pattern: Optional[str] = None,
        reference_answer_pattern: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        PDF 파일에서 학습 데이터 추출 (빠른 버전)

        Args:
            pdf_path: PDF 파일 경로
            problem_pattern: 문제 시작 패턴
            reference_answer_pattern: 모범답안 시작 패턴

        Returns:
            문제와 답안 리스트
        """
        import re

        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

        # 기본 패턴 설정 (더 많은 패턴 포함)
        if problem_pattern is None:
            # 문제 패턴: "문제", "Q", "점-1", "【문제】", "제1문제" 등
            problem_pattern = r"(문제\s*\d*|Q\d*|Question\s*\d*|^\d+\.\s*문제|【문제|제\d+문제|점\s*[-]?\s*\d+|문제\s*점|^\d+\.|【\s*\d+\s*】)"

        if reference_answer_pattern is None:
            # 답안 패턴: "모범답안", "정답", "해설", "【해설】" 등
            reference_answer_pattern = r"(모범답안|정답|Answer|Reference\s*Answer|해설|【해설|【정답|답안|해답|【답안|【해답)"

        # 텍스트 추출
        full_text = self.extract_text(Path(pdf_path))

        # 문제와 답안 분리 (기존 로직 재사용)
        results = self._extract_problems_and_answers(
            full_text,
            problem_pattern,
            reference_answer_pattern
        )

        return results

    def _extract_problems_and_answers(
        self,
        text: str,
        problem_pattern: str,
        reference_answer_pattern: str
    ) -> List[Dict[str, str]]:
        """텍스트에서 문제와 모범답안 추출"""
        import re

        results = []

        # 문제 패턴 찾기
        problem_matches = list(re.finditer(problem_pattern, text, re.IGNORECASE | re.MULTILINE))
        answer_matches = list(re.finditer(reference_answer_pattern, text, re.IGNORECASE | re.MULTILINE))

        logger.info(f"[PARSE] 문제 패턴 매칭: {len(problem_matches)}개")
        logger.info(f"[PARSE] 답안 패턴 매칭: {len(answer_matches)}개")

        if not problem_matches:
            # 패턴이 없으면 전체를 하나의 문제+답안으로 처리
            logger.warning("[WARN] 문제 패턴을 찾을 수 없어 전체 텍스트를 하나의 항목으로 처리합니다.")
            mid_point = len(text) // 2
            results.append({
                "problem_text": text[:mid_point].strip(),
                "reference_answer_text": text[mid_point:].strip()
            })
            return results

        # 문제와 답안 매칭
        for i, problem_match in enumerate(problem_matches):
            problem_start = problem_match.start()

            # 다음 문제 찾기
            next_problem_start = None
            if i + 1 < len(problem_matches):
                next_problem_start = problem_matches[i + 1].start()

            # 해당 문제의 답안 찾기
            answer_start = None
            answer_end = None

            for answer_match in answer_matches:
                if answer_match.start() > problem_start:
                    answer_start = answer_match.start()
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
            first_problem_start = problem_matches[0].start()
            results.append({
                "problem_text": text[first_problem_start:].strip(),
                "reference_answer_text": ""
            })

        return results


class PDFToPolicyRuleConverterFast:
    """PDF를 정책/규칙 판별 JSONL로 변환하는 클래스 (고속 버전)"""

    def __init__(self):
        self.pdf_parser = FastPDFParser()
        self.decision_maker = DecisionMaker()

    def extract_problems_from_pdf(self, pdf_path: Path) -> List[Dict[str, str]]:
        """PDF에서 문제와 답안 추출"""
        try:
            parsed_data = self.pdf_parser.parse_training_pdf(str(pdf_path))
            logger.info(f"[OK] PDF 파싱 완료: {len(parsed_data)}개 항목 추출")
            return parsed_data
        except Exception as e:
            logger.error(f"[ERROR] PDF 파싱 실패: {e}")
            raise

    async def convert_to_policy_rule_data(
        self,
        problems: List[Dict[str, str]],
        domain: str = "reasoning",
        action: str = "comprehensive_analysis"
    ) -> List[Dict[str, Any]]:
        """문제/답안을 정책/규칙 판별 데이터로 변환"""
        results = []

        for idx, problem_data in enumerate(problems):
            problem_text = problem_data.get("problem_text", "")
            reference_answer_text = problem_data.get("reference_answer_text", "")

            if not problem_text or not reference_answer_text:
                logger.warning(f"[WARN] 문제 {idx+1}: 문제 또는 답안이 없어 건너뜀")
                continue

            # 요청 데이터 구성
            request = {
                "user_answer_id": f"pdf-{idx+1}",
                "problem_text": problem_text,
                "reference_answer_text": reference_answer_text
            }

            try:
                # DecisionMaker로 판단
                strategy = await self.decision_maker.determine_strategy(
                    domain, action, request
                )

                # 프롬프트 생성
                prompt = self.decision_maker._build_prompt(domain, action, request)

                # 라벨 생성 (0: policy, 1: rule)
                label = 0 if strategy == "policy" else 1

                # 데이터 구성
                data = {
                    "text": prompt,
                    "label": label,
                    "metadata": {
                        "source": "pdf",
                        "domain": domain,
                        "action": action,
                        "strategy": strategy,
                        "problem_text_preview": problem_text[:100],
                        "reference_answer_text_preview": reference_answer_text[:100]
                    }
                }

                results.append(data)

                # 진행 상황 출력 (10개마다)
                if (idx + 1) % 10 == 0:
                    logger.info(f"[PROGRESS] 처리 중: {idx+1}/{len(problems)}개 완료")

            except Exception as e:
                logger.error(f"[ERROR] 문제 {idx+1} 처리 실패: {e}")
                continue

        return results

    def save_to_jsonl(
        self,
        data: List[Dict[str, Any]],
        output_file: Path,
        format_type: str = "training"
    ):
        """JSONL 파일로 저장"""
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            for item in data:
                if format_type == "training":
                    training_item = {
                        "text": item.get("text", ""),
                        "label": item.get("label", 0)
                    }
                    f.write(json.dumps(training_item, ensure_ascii=False) + "\n")
                else:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

        logger.info(f"[SAVE] JSONL 저장 완료: {output_file} ({len(data)}개)")


async def convert_pdf_to_jsonl_fast(
    pdf_path: Path,
    output_file: Path,
    domain: str = "reasoning",
    action: str = "comprehensive_analysis",
    format_type: str = "training"
):
    """PDF를 JSONL로 변환하는 메인 함수 (고속 버전)"""
    print("=" * 80)
    print("PDF → 정책/규칙 판별 JSONL 변환 (고속 버전)")
    print("=" * 80)

    converter = PDFToPolicyRuleConverterFast()

    # 1. PDF 파싱
    print(f"\n[1단계] PDF 파싱 중... (PyPDF2/pypdf 사용)")
    print(f"입력 파일: {pdf_path}")

    if not pdf_path.exists():
        print(f"\n[ERROR] PDF 파일이 없습니다: {pdf_path}")
        return

    import time
    start_time = time.time()

    problems = converter.extract_problems_from_pdf(pdf_path)

    parse_time = time.time() - start_time
    print(f"파싱 시간: {parse_time:.2f}초")
    print(f"추출된 문제 수: {len(problems)}개")

    if not problems:
        print("\n[ERROR] PDF에서 문제를 추출할 수 없습니다.")
        return

    # 2. 정책/규칙 판별 데이터로 변환
    print(f"\n[2단계] 정책/규칙 판별 데이터로 변환 중...")
    print(f"도메인: {domain}, 액션: {action}")

    convert_start = time.time()
    policy_rule_data = await converter.convert_to_policy_rule_data(
        problems, domain, action
    )
    convert_time = time.time() - convert_start

    print(f"변환 시간: {convert_time:.2f}초")

    if not policy_rule_data:
        print("\n[ERROR] 변환된 데이터가 없습니다.")
        return

    # 라벨 분포 확인
    policy_count = sum(1 for item in policy_rule_data if item.get("label") == 0)
    rule_count = sum(1 for item in policy_rule_data if item.get("label") == 1)

    print(f"\n변환 완료: {len(policy_rule_data)}개")
    print(f"  - 정책 기반 (0): {policy_count}개 ({policy_count/len(policy_rule_data)*100:.1f}%)")
    print(f"  - 규칙 기반 (1): {rule_count}개 ({rule_count/len(policy_rule_data)*100:.1f}%)")

    # 3. JSONL 저장
    print(f"\n[3단계] JSONL 저장 중...")
    print(f"출력 파일: {output_file}")

    converter.save_to_jsonl(policy_rule_data, output_file, format_type)

    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)
    print(f"\n총 소요 시간: {total_time:.2f}초")
    print(f"  - PDF 파싱: {parse_time:.2f}초")
    print(f"  - 데이터 변환: {convert_time:.2f}초")
    print(f"출력 파일: {output_file}")
    print(f"변환된 데이터: {len(policy_rule_data)}개")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="PDF를 정책/규칙 판별 JSONL로 변환 (고속 버전)")
    parser.add_argument(
        "pdf_file",
        type=str,
        help="PDF 파일 경로"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 JSONL 파일 경로"
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="reasoning",
        help="도메인 이름"
    )
    parser.add_argument(
        "--action",
        type=str,
        default="comprehensive_analysis",
        help="액션 이름"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["training", "full"],
        default="training",
        help="저장 형식"
    )

    args = parser.parse_args()

    # 경로 정규화 (PowerShell 백슬래시 문제 해결)
    pdf_path = Path(args.pdf_file).resolve()

    if not pdf_path.exists():
        print(f"\n[ERROR] PDF 파일을 찾을 수 없습니다: {pdf_path}")
        print(f"\n입력된 경로: {args.pdf_file}")
        print(f"절대 경로: {pdf_path}")
        print("\n해결 방법:")
        print("1. 파일 경로가 올바른지 확인하세요")
        print("2. 상대 경로 또는 절대 경로를 사용하세요")
        print("3. PowerShell에서는 따옴표로 경로를 감싸세요")
        return

    if args.output:
        output_file = Path(args.output).resolve()
    else:
        output_file = pdf_path.parent / f"{pdf_path.stem}_policy_rule.jsonl"

    asyncio.run(convert_pdf_to_jsonl_fast(
        pdf_path=pdf_path,
        output_file=output_file,
        domain=args.domain,
        action=args.action,
        format_type=args.format
    ))


if __name__ == "__main__":
    main()
