"""
PDF 파싱 테스트 스크립트

PDF에서 실제로 몇 개의 문제가 추출되는지 확인합니다.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.utils.pdf_parser import PDFParser

def test_pdf_parsing(pdf_path: str):
    """PDF 파싱 테스트"""
    print("=" * 80)
    print("PDF 파싱 테스트")
    print("=" * 80)

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"\n[ERROR] PDF 파일이 없습니다: {pdf_path}")
        return

    print(f"\nPDF 파일: {pdf_path}")

    try:
        parser = PDFParser()
        results = parser.parse_training_pdf(str(pdf_path))

        print(f"\n추출된 문제 수: {len(results)}개")

        if len(results) == 0:
            print("\n[WARN] 문제가 추출되지 않았습니다.")
            print("\n가능한 원인:")
            print("1. PDF가 이미지 기반 PDF일 수 있습니다")
            print("2. 문제/답안 패턴이 인식되지 않았습니다")
            print("3. PDF 구조가 예상과 다릅니다")
            return

        # 각 문제의 길이 확인
        print("\n" + "-" * 80)
        print("추출된 문제 상세 정보")
        print("-" * 80)

        for i, result in enumerate(results[:5]):  # 처음 5개만 출력
            problem_text = result.get("problem_text", "")
            reference_answer_text = result.get("reference_answer_text", "")

            print(f"\n문제 {i+1}:")
            print(f"  문제 길이: {len(problem_text)}자")
            print(f"  답안 길이: {len(reference_answer_text)}자")
            print(f"  문제 미리보기: {problem_text[:100]}...")
            print(f"  답안 미리보기: {reference_answer_text[:100]}...")

        if len(results) > 5:
            print(f"\n... 외 {len(results) - 5}개 더 있음")

        # 문제/답안이 없는 항목 확인
        empty_problems = [i for i, r in enumerate(results) if not r.get("problem_text")]
        empty_answers = [i for i, r in enumerate(results) if not r.get("reference_answer_text")]

        if empty_problems:
            print(f"\n[WARN] 문제 텍스트가 없는 항목: {len(empty_problems)}개")
        if empty_answers:
            print(f"[WARN] 답안 텍스트가 없는 항목: {len(empty_answers)}개")

    except Exception as e:
        print(f"\n[ERROR] PDF 파싱 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python test_pdf_parsing.py <PDF 파일 경로>")
        sys.exit(1)

    test_pdf_parsing(sys.argv[1])
