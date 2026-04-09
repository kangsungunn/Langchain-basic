"""
PDF를 정책/규칙 판별 학습 데이터(JSONL)로 변환하는 스크립트

PDF 파일에서 문제와 답안을 추출하여 DecisionMaker 프롬프트를 생성하고,
정책/규칙 판별 학습 데이터 형식으로 변환합니다.
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.utils.pdf_parser import PDFParser
from app.domain.v1.minso.hub.decision_maker import DecisionMaker
from app.core.utils.logger import get_logger

logger = get_logger()


class PDFToPolicyRuleConverter:
    """PDF를 정책/규칙 판별 JSONL로 변환하는 클래스"""

    def __init__(self):
        self.pdf_parser = PDFParser()
        self.decision_maker = DecisionMaker()

    def extract_problems_from_pdf(self, pdf_path: Path) -> List[Dict[str, str]]:
        """
        PDF에서 문제와 답안 추출

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            문제와 답안 리스트
        """
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
        """
        문제/답안을 정책/규칙 판별 데이터로 변환

        Args:
            problems: 문제와 답안 리스트
            domain: 도메인 이름 (기본값: "reasoning")
            action: 액션 이름 (기본값: "comprehensive_analysis")

        Returns:
            정책/규칙 판별 데이터 리스트
        """
        results = []

        for idx, problem_data in enumerate(problems):
            problem_text = problem_data.get("problem_text", "")
            reference_answer_text = problem_data.get("reference_answer_text", "")

            if not problem_text or not reference_answer_text:
                logger.warning(f"[WARN] 문제 {idx+1}: 문제 또는 답안이 없어 건너뜀")
                continue

            # 요청 데이터 구성 (실제 API 요청과 유사하게)
            request = {
                "user_answer_id": f"pdf-{idx+1}",  # 임시 ID
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
                        "problem_text_preview": problem_text[:100],  # 미리보기
                        "reference_answer_text_preview": reference_answer_text[:100]
                    }
                }

                results.append(data)
                logger.info(f"[OK] 문제 {idx+1}: {strategy} 기반 (라벨: {label})")

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
        """
        JSONL 파일로 저장

        Args:
            data: 저장할 데이터
            output_file: 출력 파일 경로
            format_type: 저장 형식 ("training" 또는 "full")
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            for item in data:
                if format_type == "training":
                    # 학습 형식으로 변환 (text, label만)
                    training_item = {
                        "text": item.get("text", ""),
                        "label": item.get("label", 0)
                    }
                    f.write(json.dumps(training_item, ensure_ascii=False) + "\n")
                else:
                    # 전체 메타데이터 포함
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

        logger.info(f"[SAVE] JSONL 저장 완료: {output_file} ({len(data)}개)")


async def convert_pdf_to_jsonl(
    pdf_path: Path,
    output_file: Path,
    domain: str = "reasoning",
    action: str = "comprehensive_analysis",
    format_type: str = "training"
):
    """
    PDF를 JSONL로 변환하는 메인 함수

    Args:
        pdf_path: PDF 파일 경로
        output_file: 출력 JSONL 파일 경로
        domain: 도메인 이름
        action: 액션 이름
        format_type: 저장 형식 ("training" 또는 "full")
    """
    print("=" * 80)
    print("PDF → 정책/규칙 판별 JSONL 변환")
    print("=" * 80)

    converter = PDFToPolicyRuleConverter()

    # 1. PDF 파싱
    print(f"\n[1단계] PDF 파싱 중...")
    print(f"입력 파일: {pdf_path}")

    if not pdf_path.exists():
        print(f"\n[ERROR] PDF 파일이 없습니다: {pdf_path}")
        return

    problems = converter.extract_problems_from_pdf(pdf_path)

    if not problems:
        print("\n[ERROR] PDF에서 문제를 추출할 수 없습니다.")
        print("\n가능한 원인:")
        print("1. PDF가 이미지 기반 PDF일 수 있습니다 (OCR 필요)")
        print("2. 문제/답안 패턴이 인식되지 않았습니다")
        print("3. PDF 구조가 예상과 다릅니다")
        return

    print(f"추출된 문제 수: {len(problems)}개")

    # 2. 정책/규칙 판별 데이터로 변환
    print(f"\n[2단계] 정책/규칙 판별 데이터로 변환 중...")
    print(f"도메인: {domain}, 액션: {action}")

    policy_rule_data = await converter.convert_to_policy_rule_data(
        problems, domain, action
    )

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

    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)
    print(f"\n출력 파일: {output_file}")
    print(f"변환된 데이터: {len(policy_rule_data)}개")
    print("\n다음 단계:")
    print("1. 데이터 검증: python training/orchestration/check_data.py")
    print("2. 데이터 분할: python training/orchestration/split_data.py")
    print("3. 학습 실행: python training/orchestration/train_koelectra_policy_rule.py")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="PDF를 정책/규칙 판별 JSONL로 변환")
    parser.add_argument(
        "pdf_file",
        type=str,
        help="PDF 파일 경로"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 JSONL 파일 경로 (기본값: 입력 파일명과 동일한 위치)"
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="reasoning",
        help="도메인 이름 (기본값: reasoning)"
    )
    parser.add_argument(
        "--action",
        type=str,
        default="comprehensive_analysis",
        help="액션 이름 (기본값: comprehensive_analysis)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["training", "full"],
        default="training",
        help="저장 형식 (기본값: training)"
    )

    args = parser.parse_args()

    # 경로 설정
    pdf_path = Path(args.pdf_file)

    if args.output:
        output_file = Path(args.output)
    else:
        # 기본값: 입력 파일과 같은 디렉토리에 .jsonl 확장자로 저장
        output_file = pdf_path.parent / f"{pdf_path.stem}_policy_rule.jsonl"

    # 변환 실행
    asyncio.run(convert_pdf_to_jsonl(
        pdf_path=pdf_path,
        output_file=output_file,
        domain=args.domain,
        action=args.action,
        format_type=args.format
    ))


if __name__ == "__main__":
    main()
