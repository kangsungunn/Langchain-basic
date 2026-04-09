"""
다량 PDF 일괄 처리: 전체 텍스트 추출 후 문제/답안 마커로 분할

- PDF 하나당 전체 텍스트만 추출 (복잡한 구조 추론 없음)
- 【문제-1】, 【문제-2】, ... 로 문제 블록 분할
- I. 설문 (1)에 대하여, II. 설문 (2)에 대하여, ... 로 답안 블록 분할
- 결과: problems/{회차}_{n}.md, model_answers/{회차}_{n}.md

사용 예:
  python training/orchestration/batch_pdf_to_structured.py "data/raw/civil_procedure/pdfs"
  python training/orchestration/batch_pdf_to_structured.py "data/raw/civil_procedure/pdfs/57회.pdf"
"""

import re
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pdfplumber
except ImportError:
    try:
        import pypdf
    except ImportError:
        pypdf = None
    pdfplumber = None

if not pdfplumber and not pypdf:
    print("[ERROR] pdfplumber 또는 pypdf 설치 필요: pip install pdfplumber pypdf")
    sys.exit(1)


def extract_full_text(pdf_path: Path) -> str:
    """PDF 전체 텍스트 추출. pdfplumber 우선, 없으면 pypdf."""
    full_text = ""
    if pdfplumber:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    else:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    return full_text


# 문제 블록: 【문제-1】, 【문제-2】 ...
PROBLEM_HEADER_RE = re.compile(r"【문제-(\d+)】\s*[\(（]?\s*(\d+)\s*점\s*[\)）]?")
# 답안 블록: I. 설문 (1)에 대하여(5점) / II. 설문 (2)에 대하여(10점)
ANSWER_HEADER_RE = re.compile(r"^[IVX]+\.\s*설문\s*[\(（]\s*(\d+)\s*[\)）].*?[\(（](\d+)\s*점\s*[\)）]", re.MULTILINE)


def split_problems(full_text: str) -> list[tuple[str, str]]:
    """전체 텍스트에서 【문제-n】 기준으로 블록 추출. 반환: [(번호, 본문), ...]"""
    blocks = []
    for m in PROBLEM_HEADER_RE.finditer(full_text):
        num = m.group(1)
        start = m.start()
        end = len(full_text)
        next_m = PROBLEM_HEADER_RE.search(full_text, m.end())
        if next_m:
            end = next_m.start()
        body = full_text[start:end].strip()
        blocks.append((num, body))
    return blocks


def split_answers(full_text: str) -> list[tuple[str, str]]:
    """전체 텍스트에서 I. 설문 (1) ... 기준으로 답안 블록 추출."""
    blocks = []
    for m in ANSWER_HEADER_RE.finditer(full_text):
        num = m.group(1)
        start = m.start()
        end = len(full_text)
        next_m = ANSWER_HEADER_RE.search(full_text, m.end())
        if next_m:
            end = next_m.start()
        body = full_text[start:end].strip()
        blocks.append((num, body))
    return blocks


def save_problem_md(out_dir: Path, exam_id: str, num: str, body: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{exam_id}_{num}.md"
    path.write_text(body.strip(), encoding="utf-8")
    return path


def save_answer_md(out_dir: Path, exam_id: str, num: str, body: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{exam_id}_{num}.md"
    path.write_text(body.strip(), encoding="utf-8")
    return path


def process_one_pdf(
    pdf_path: Path,
    base_out: Path,
    save_raw: bool = False,
) -> tuple[int, int]:
    """PDF 하나 처리. 반환: (문제 개수, 답안 개수)."""
    stem = pdf_path.stem
    exam_id = re.sub(r"[^\w\-]", "_", stem)
    if not exam_id:
        exam_id = "pdf"

    raw_text = extract_full_text(pdf_path)
    if not raw_text.strip():
        print(f"  [WARN] 텍스트 없음: {pdf_path.name}")
        return 0, 0

    if save_raw:
        raw_dir = base_out / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{stem}.txt").write_text(raw_text, encoding="utf-8")

    problems_dir = base_out / "problems"
    answers_dir = base_out / "model_answers"
    n_problem = 0
    n_answer = 0

    problem_blocks = split_problems(raw_text)
    for num, body in problem_blocks:
        save_problem_md(problems_dir, exam_id, num, body)
        n_problem += 1

    answer_blocks = split_answers(raw_text)
    for num, body in answer_blocks:
        save_answer_md(answers_dir, exam_id, num, body)
        n_answer += 1

    return n_problem, n_answer


def main():
    import argparse
    p = argparse.ArgumentParser(description="다량 PDF → 문제/답안 MD 분할")
    p.add_argument("path", help="PDF 파일 또는 PDF가 들어 있는 폴더")
    p.add_argument("-o", "--output", default=None, help="출력 기준 폴더 (기본: data/raw/civil_procedure)")
    p.add_argument("--save-raw", action="store_true", help="추출한 원문 텍스트를 raw/*.txt 로 저장")
    args = p.parse_args()

    base_out = Path(args.output) if args.output else project_root / "data" / "raw" / "civil_procedure"
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"[ERROR] 경로 없음: {path}")
        sys.exit(1)

    if path.is_file():
        if path.suffix.lower() != ".pdf":
            print("[ERROR] PDF 파일만 처리 가능합니다.")
            sys.exit(1)
        pdfs = [path]
    else:
        pdfs = sorted(path.glob("*.pdf"))

    if not pdfs:
        print(f"[ERROR] PDF 파일이 없습니다: {path}")
        sys.exit(1)

    print(f"처리할 PDF: {len(pdfs)}개")
    total_p, total_a = 0, 0
    for pdf_path in pdfs:
        print(f"  {pdf_path.name} ... ", end="", flush=True)
        try:
            n_p, n_a = process_one_pdf(pdf_path, base_out, save_raw=args.save_raw)
            total_p += n_p
            total_a += n_a
            print(f"문제 {n_p}개, 답안 {n_a}개")
        except Exception as e:
            print(f"실패: {e}")
    print(f"총 문제 {total_p}개, 답안 {total_a}개 → {base_out}")


if __name__ == "__main__":
    main()
