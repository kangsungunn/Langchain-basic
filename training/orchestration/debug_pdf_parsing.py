"""
PDF 파싱 디버깅 스크립트

PDF에서 문제와 답안이 제대로 추출되는지 확인합니다.
"""

import sys
from pathlib import Path
import re

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        import PyPDF2 as pypdf
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False
        print("[ERROR] pypdf가 설치되지 않았습니다.")
        sys.exit(1)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """PDF에서 텍스트 추출"""
    full_text = ""

    with open(pdf_path, 'rb') as file:
        pdf_reader = pypdf.PdfReader(file)
        print(f"총 페이지 수: {len(pdf_reader.pages)}")

        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
                    print(f"페이지 {page_num+1}: {len(page_text)}자 추출")
            except Exception as e:
                print(f"[WARN] 페이지 {page_num+1} 추출 실패: {e}")

    print(f"\n전체 텍스트 길이: {len(full_text)}자")
    return full_text


def analyze_patterns(text: str):
    """패턴 분석"""
    print("\n" + "=" * 80)
    print("패턴 분석")
    print("=" * 80)

    # 문제 패턴들
    problem_patterns = [
        r"문제\s*\d*",
        r"Q\d*",
        r"Question\s*\d*",
        r"^\d+\.\s*문제",
        r"【문제",
        r"제\d+문제",
        r"문제\s*\d+",
        r"문제\s*[0-9]+",
    ]

    # 답안 패턴들
    answer_patterns = [
        r"모범답안",
        r"정답",
        r"Answer",
        r"Reference\s*Answer",
        r"해설",
        r"【해설",
        r"【정답",
        r"답안",
        r"해답",
    ]

    print("\n[문제 패턴 검색]")
    problem_matches = []
    for pattern in problem_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
        if matches:
            print(f"  '{pattern}': {len(matches)}개 발견")
            problem_matches.extend(matches)
            # 처음 3개 위치 표시
            for i, match in enumerate(matches[:3]):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ')
                print(f"    위치 {i+1}: ...{context}...")

    print(f"\n총 문제 패턴 매칭: {len(problem_matches)}개")

    print("\n[답안 패턴 검색]")
    answer_matches = []
    for pattern in answer_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
        if matches:
            print(f"  '{pattern}': {len(matches)}개 발견")
            answer_matches.extend(matches)
            # 처음 3개 위치 표시
            for i, match in enumerate(matches[:3]):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ')
                print(f"    위치 {i+1}: ...{context}...")

    print(f"\n총 답안 패턴 매칭: {len(answer_matches)}개")

    # 텍스트 샘플 출력
    print("\n[텍스트 샘플 (처음 1000자)]")
    print("-" * 80)
    print(text[:1000])
    print("-" * 80)

    # 텍스트 샘플 출력 (중간 부분)
    if len(text) > 2000:
        print("\n[텍스트 샘플 (중간 부분, 1000자)]")
        print("-" * 80)
        mid_point = len(text) // 2
        print(text[mid_point:mid_point+1000])
        print("-" * 80)

    return problem_matches, answer_matches


def test_parsing(pdf_path: Path):
    """파싱 테스트"""
    print("=" * 80)
    print("PDF 파싱 디버깅")
    print("=" * 80)
    print(f"\nPDF 파일: {pdf_path}")

    if not pdf_path.exists():
        print(f"\n[ERROR] 파일이 없습니다: {pdf_path}")
        return

    # 1. 텍스트 추출
    print("\n[1단계] 텍스트 추출 중...")
    text = extract_text_from_pdf(pdf_path)

    if not text.strip():
        print("\n[ERROR] 텍스트를 추출할 수 없습니다.")
        print("이 PDF는 이미지 기반 PDF일 수 있습니다.")
        return

    # 2. 패턴 분석
    print("\n[2단계] 패턴 분석 중...")
    problem_matches, answer_matches = analyze_patterns(text)

    # 3. 추출 시도
    print("\n[3단계] 문제/답안 추출 시도...")
    from training.orchestration.pdf_to_policy_rule_jsonl_fast import FastPDFParser

    parser = FastPDFParser()
    try:
        results = parser.parse_training_pdf(str(pdf_path))
        print(f"\n추출된 항목 수: {len(results)}개")

        for i, result in enumerate(results[:5]):  # 처음 5개만 표시
            print(f"\n항목 {i+1}:")
            print(f"  문제 길이: {len(result.get('problem_text', ''))}자")
            print(f"  답안 길이: {len(result.get('reference_answer_text', ''))}자")
            print(f"  문제 미리보기: {result.get('problem_text', '')[:100]}...")
            print(f"  답안 미리보기: {result.get('reference_answer_text', '')[:100]}...")

        if len(results) < 5:
            print(f"\n[WARN] 추출된 항목이 적습니다 ({len(results)}개)")
            print("\n가능한 원인:")
            print("1. 문제/답안 패턴이 인식되지 않음")
            print("2. PDF 구조가 예상과 다름")
            print("3. 문제와 답안이 분리되어 있지 않음")

    except Exception as e:
        print(f"\n[ERROR] 파싱 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="PDF 파싱 디버깅")
    parser.add_argument(
        "pdf_file",
        type=str,
        help="PDF 파일 경로"
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf_file).resolve()
    test_parsing(pdf_path)


if __name__ == "__main__":
    main()
