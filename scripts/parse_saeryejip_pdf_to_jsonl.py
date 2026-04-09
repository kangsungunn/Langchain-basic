# -*- coding: utf-8 -*-
"""
곽준형 윤곽 민소법 사례집 PDF → 57_all.jsonl 호환 (2단계)

1단계(정확도용): PDF → 원본 텍스트 1차 정리 (raw .txt)
  python parse_saeryejip_pdf_to_jsonl.py --extract-only "data/raw/civil_procedure/곽준형...상...pdf"
  → gy_saeryejip_sang_raw.txt 생성 (한 번만 실행, 필요 시 수동 보정)

2단계(빠름): raw .txt → 문제/답안 인식 → jsonl
  python parse_saeryejip_pdf_to_jsonl.py "data/raw/civil_procedure/gy_saeryejip_sang_raw.txt"
  → problems/gy_saeryejip_all.jsonl, model_answers/gy_saeryejip_all.jsonl

형식: A-1. ［...］ → 사례 본문 → 설명하시오. (10점) / 논하시오. (N점)
      답안: 1. 문제의 소재 ... 로 시작
"""
from pathlib import Path
import re
import json
import sys
import argparse

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def extract_full_text(
    pdf_path: Path,
    with_page_markers: bool = True,
    show_progress: bool = False,
    max_pages: int | None = None,
) -> str:
    """PDF 전체 텍스트 추출. with_page_markers=True면 '--- PAGE N ---' 삽입."""
    parts = []
    total = 0
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            if max_pages is not None:
                total = min(total, max_pages)
            if show_progress:
                print("총 %d 페이지 추출 예정 (10페이지마다 진행 표시)" % total, flush=True)
            for i, p in enumerate(pdf.pages):
                if max_pages is not None and i >= max_pages:
                    break
                t = p.extract_text() or ""
                if with_page_markers:
                    parts.append("--- PAGE %d ---\n%s" % (i + 1, t))
                else:
                    parts.append(t)
                if show_progress and (i + 1) % 10 == 0:
                    print("  페이지 %d / %d 처리함" % (i + 1, total), flush=True)
    except Exception:
        import pypdf
        r = pypdf.PdfReader(open(pdf_path, "rb"))
        total = len(r.pages)
        if max_pages is not None:
            total = min(total, max_pages)
        if show_progress:
            print("총 %d 페이지 추출 예정 (10페이지마다 진행 표시)" % total, flush=True)
        for i in range(len(r.pages)):
            if max_pages is not None and i >= max_pages:
                break
            t = r.pages[i].extract_text() or ""
            if with_page_markers:
                parts.append("--- PAGE %d ---\n%s" % (i + 1, t))
            else:
                parts.append(t)
            if show_progress and (i + 1) % 10 == 0:
                print("  페이지 %d / %d 처리함" % (i + 1, total), flush=True)
    if show_progress:
        print("추출 완료. 파일 저장 중...", flush=True)
    return "\n\n".join(parts)


# 【문제-N】 마커 (edited.txt 전용: 이걸로 블록 분리하면 누락 없음)
PROBLEM_MARKER_RE = re.compile(r"【문제-(\d+)】", re.MULTILINE)
# 사례집 섹션: A-1. ［...］ 또는 【문제-N】 다음 A-1. ［ (OCR 오류 시 AT. ［ → A-1. ［)
SECTION_HEADER_RE = re.compile(
    r"^(?:--- PAGE \d+ ---\s*\n|【문제-\d+】\s*\n)?"
    r"([A-Z])-(\d+)\.\s*［",
    re.MULTILINE,
)
# 블록 본문 첫 줄에서 섹션 식별 (A-1. ［ ... ］)
SECTION_FROM_FIRST_LINE = re.compile(r"^([A-Z])-(\d+)\.\s*［", re.MULTILINE)
# 답안 시작 (각 설문마다 등장). "1 . 문제의 소재" OCR 허용
ANSWER_START_RE = re.compile(r"^1\s*\.\s*문제의 소재\s", re.MULTILINE)
# 배점
POINTS_RE = re.compile(r"\((\d+)\s*점\s*\)")
# 문제 본문 (1) ... (N점), (2) ... (M점) 추출
QUESTION_PART_RE = re.compile(r"\((\d+)\)\s*(.+?)\s*\((\d+)\s*점\s*\)", re.DOTALL)
def preprocess(text: str) -> str:
    # OCR: AT. ［ → A-1. ［, BT. ［ → B-1. ［ 등
    text = re.sub(r"([A-Z])T\.\s*［", r"\1-1. ［", text)
    return text


def split_by_problem_markers(full_text: str) -> list[tuple[int, str]]:
    """【문제-N】 기준으로 블록 분리. 반환: [(문제번호, 블록텍스트), ...]. 누락 없음."""
    text = preprocess(full_text)
    matches = list(PROBLEM_MARKER_RE.finditer(text))
    if not matches:
        return []
    out = []
    for i, m in enumerate(matches):
        n = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if not block or not ANSWER_START_RE.search(block):
            continue
        out.append((n, block))
    return out


def block_to_section_id(block_body: str) -> str:
    """블록 본문(【문제-N】 제거 후) 첫 줄에서 A-1. ［ ... ］ → gy_A_1."""
    first = SECTION_FROM_FIRST_LINE.search(block_body)
    if first:
        return "gy_%s_%s" % (first.group(1), first.group(2))
    return None


def split_sections(full_text: str) -> list[tuple[str, str, str]]:
    """(chapter_num, section_num, block_text) 리스트. 본문만 (목차 제외)."""
    text = preprocess(full_text)
    sections = []
    for m in SECTION_HEADER_RE.finditer(text):
        ch, num = m.group(1), m.group(2)
        start = m.start()
        end = len(text)
        next_m = SECTION_HEADER_RE.search(text, m.end())
        if next_m:
            end = next_m.start()
        block = text[start:end]
        # 목차는 "1. 문제의 소재"가 없고 점선/숫자만 있음 → 스킵
        if ANSWER_START_RE.search(block):
            sections.append((ch, num, block))
    return sections


def split_problem_and_answer(block: str) -> tuple[str, str] | None:
    m = ANSWER_START_RE.search(block)
    if not m:
        return None
    problem = block[: m.start()].strip()
    answer = block[m.start() :].strip()
    if not problem or not answer:
        return None
    return problem, answer


def split_answer_into_parts(full_answer: str) -> list[str]:
    """답안을 '1. 문제의 소재' 줄 기준으로 설문별 분리."""
    parts = []
    for m in ANSWER_START_RE.finditer(full_answer):
        start = m.start()
        end = len(full_answer)
        next_m = ANSWER_START_RE.search(full_answer, m.end())
        if next_m:
            end = next_m.start()
        chunk = full_answer[start:end].strip()
        if chunk:
            parts.append(chunk)
    return parts if parts else [full_answer]


def extract_question_parts(problem_text: str) -> list[tuple[int, str]]:
    """(1) ... (N점), (2) ... (M점) 추출. 반환: [(배점, 질문문장), ...]"""
    out = []
    for m in QUESTION_PART_RE.finditer(problem_text):
        body, points_str = m.group(2).strip(), m.group(3)
        points = int(points_str)
        q = (body + " (" + points_str + "점)").strip() if len(body) > 3 else "위 사안에 대하여 설명하시오."
        out.append((points, q))
    return out


def extract_points_and_question(problem_text: str) -> tuple[int, str]:
    """(points, question 문장). (N점) 마지막 매칭으로 배점, 해당 문장으로 질문 추출."""
    points = 0
    question = ""
    # 배점: (N점) 형태 마지막 등장
    for m in POINTS_RE.finditer(problem_text):
        points = int(m.group(1))
    # 질문: (N점) 앞 문장. 해당 점 앞까지에서 마지막 줄 또는 문장
    last_point = list(POINTS_RE.finditer(problem_text))
    if last_point:
        m = last_point[-1]
        end = m.end()
        line_start = problem_text.rfind("\n", 0, end) + 1
        # 줄 시작부터 (N점) 포함까지; 앞쪽 불필요 제거
        raw = problem_text[line_start:end].strip()
        if len(raw) > 15:
            question = raw
        else:
            # 한 줄이 너무 짧으면 앞 줄과 합침
            prev = problem_text.rfind("\n", 0, line_start - 1) + 1
            question = (problem_text[prev:end].replace("\n", " ").strip())
    if not question:
        question = "위 사안에 대하여 설명하시오."
    return points, question


def clean_footer(line: str) -> bool:
    """페이지 푸터/챕터 표시 라인 제거 여부"""
    if re.match(r"^Chapter\s+[A-Z]\s*\.", line):
        return True
    if re.match(r"^[\dIVX]+\s*$", line.strip()):
        return True
    if re.search(r"윤곽\s*민사소송법\s*사례\s*집\s*上?편\s*$", line):
        return True
    return False


def clean_text(s: str) -> str:
    lines = []
    for line in s.split("\n"):
        line = line.strip()
        if not line or clean_footer(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def build_problem_entry(section_id: str, title: str, content: str, questions: list[dict]) -> dict:
    return {"id": section_id, "title": title, "content": content, "questions": questions}


def build_answer_entry(section_id: str, answers_list: list[dict]) -> dict:
    return {"id": section_id, "answers": answers_list}


def _process_one_block(
    block: str,
    section_id: str,
    title_fallback: str,
) -> tuple[dict, dict, int] | None:
    """블록 하나에서 (problem_entry, answer_entry, n_questions) 생성. 실패 시 None."""
    pair = split_problem_and_answer(block)
    if not pair:
        return None
    problem_text, answer_text = pair
    answer_parts = split_answer_into_parts(answer_text)
    question_parts = extract_question_parts(problem_text)

    if question_parts and answer_parts:
        n = min(len(question_parts), len(answer_parts))
    else:
        n = 1
        points, question = extract_points_and_question(problem_text)
        question_parts = [(points, question)]
    if len(question_parts) < n:
        points, question = extract_points_and_question(problem_text)
        question_parts = [(points, question)] * n
    if len(answer_parts) < n:
        answer_parts = [answer_text] * n

    title_line = problem_text.split("\n")[0].strip()
    if not title_line or len(title_line) > 200:
        title_line = title_fallback
    content = clean_text(problem_text)

    questions_list = [
        {"number": i + 1, "points": question_parts[i][0], "question": question_parts[i][1]}
        for i in range(n)
    ]
    answers_list = [
        {"question_number": i + 1, "points": question_parts[i][0], "answer": clean_text(answer_parts[i])}
        for i in range(n)
    ]
    return (
        build_problem_entry(section_id, title_line, content, questions_list),
        build_answer_entry(section_id, answers_list),
        n,
    )


def run_txt_to_jsonl(raw_text: str, base_out: Path) -> tuple[int, int]:
    """raw 텍스트에서 문제/답안 파싱 후 jsonl 저장. 반환: (섹션 수, 총 설문 수).
    【문제-N】 마커가 있으면 그걸로 블록 분리(누락 없음), 없으면 A-1. ［ ... ］ 섹션 헤더로 분리.
    """
    problems = []
    answers = []
    total_questions = 0

    if "【문제-" in raw_text:
        # _edited.txt: 【문제-N】 기준으로만 분리
        blocks = split_by_problem_markers(raw_text)
        for problem_idx, block in blocks:
            # 첫 줄 "【문제-N】" 제거한 본문
            first_newline = block.find("\n")
            if first_newline >= 0:
                block_body = block[first_newline:].lstrip("\n")
            else:
                block_body = block
            section_id = block_to_section_id(block_body) or ("gy_problem_%d" % problem_idx)
            title_fallback = "【문제-%d】" % problem_idx
            one = _process_one_block(block_body, section_id, title_fallback)
            if one:
                p_entry, a_entry, n = one
                problems.append(p_entry)
                answers.append(a_entry)
                total_questions += n
    else:
        sections = split_sections(raw_text)
        for ch, num, block in sections:
            section_id = f"gy_{ch}_{num}"
            title_fallback = f"{ch}-{num}. 사례"
            one = _process_one_block(block, section_id, title_fallback)
            if one:
                p_entry, a_entry, n = one
                problems.append(p_entry)
                answers.append(a_entry)
                total_questions += n

    out_problems = base_out / "problems" / "gy_saeryejip_all.jsonl"
    out_answers = base_out / "model_answers" / "gy_saeryejip_all.jsonl"
    out_problems.parent.mkdir(parents=True, exist_ok=True)
    out_answers.parent.mkdir(parents=True, exist_ok=True)
    with open(out_problems, "w", encoding="utf-8") as f:
        for p in problems:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    with open(out_answers, "w", encoding="utf-8") as f:
        for a in answers:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    return len(problems), total_questions


def main():
    base = project_root / "data" / "raw" / "civil_procedure"
    p = argparse.ArgumentParser(
        description="1단계: PDF→raw txt (--extract-only) / 2단계: raw txt→jsonl"
    )
    p.add_argument(
        "input",
        nargs="?",
        default=None,
        help="PDF 또는 raw .txt 경로. 생략 시 civil_procedure 폴더에서 첫 PDF 사용",
    )
    p.add_argument(
        "--extract-only",
        action="store_true",
        help="1단계: PDF에서 전체 텍스트만 추출하여 raw .txt로 저장",
    )
    p.add_argument(
        "-o", "--output-txt",
        default=None,
        help="--extract-only 시 저장할 raw .txt 경로 (기본: 입력과 같은 폴더, 파일명_raw.txt)",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="추출할 최대 페이지 수 (테스트용. 생략 시 전체)",
    )
    args = p.parse_args()

    if args.input:
        path = Path(args.input)
        if not path.is_absolute():
            path = (project_root / path).resolve()
        else:
            path = path.resolve()
    else:
        pdfs = sorted(base.glob("*.pdf"))
        if not pdfs:
            print("입력 없음. input에 PDF 또는 .txt 경로를 지정하세요.")
            sys.exit(1)
        # 상(上) 권 우선
        sang = [p for p in pdfs if "상" in p.stem]
        path = sang[0] if sang else pdfs[0]

    if not path.exists():
        print("경로 없음:", path)
        sys.exit(1)

    # 1단계: PDF → raw .txt (raw_sample_gy.txt 형식: --- PAGE N --- + 전체 페이지 텍스트)
    if args.extract_only:
        if path.suffix.lower() != ".pdf":
            print("--extract-only 는 PDF 입력만 가능합니다.")
            sys.exit(1)
        print("PDF 추출 중 (전체 페이지):", path.name)
        raw = extract_full_text(
            path,
            with_page_markers=True,
            show_progress=True,
            max_pages=args.max_pages,
        )
        if not raw.strip():
            print("텍스트 추출 실패")
            sys.exit(1)
        out_txt = args.output_txt
        if not out_txt:
            out_txt = path.parent / (path.stem + "_raw.txt")
        else:
            out_txt = Path(out_txt).resolve()
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(raw, encoding="utf-8")
        print("저장:", out_txt, "(chars=%d)" % len(raw))
        return

    # 2단계: 입력이 .txt면 파일에서 읽기, .pdf면 메모리에서 추출 후 파싱
    if path.suffix.lower() == ".txt":
        print("raw .txt 읽는 중:", path.name)
        raw = path.read_text(encoding="utf-8")
    else:
        if path.suffix.lower() != ".pdf":
            print("입력은 .pdf 또는 .txt 여야 합니다.")
            sys.exit(1)
        print("PDF 추출 후 파싱:", path.name)
        raw = extract_full_text(path, with_page_markers=True)

    if not raw.strip():
        print("텍스트가 비어 있습니다.")
        sys.exit(1)

    n_p, n_a = run_txt_to_jsonl(raw, base)
    out_p = base / "problems" / "gy_saeryejip_all.jsonl"
    out_a = base / "model_answers" / "gy_saeryejip_all.jsonl"
    print("섹션 %d개, 총 설문 %d개" % (n_p, n_a))
    print("문제 %d건 → %s" % (n_p, out_p))
    print("답안 %d건 → %s" % (n_p, out_a))


if __name__ == "__main__":
    main()
