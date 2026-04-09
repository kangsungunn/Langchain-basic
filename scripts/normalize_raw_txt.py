# -*- coding: utf-8 -*-
"""
raw txt 정리: 페이지 표시 제거, 【문제-N】 부여, 문제/답안 사이 빈 줄, 줄바꿈/들여쓰기 검사

사용 (직접 실행):
  python scripts/normalize_raw_txt.py "data/raw/civil_procedure/곽준형 윤곽 민소법 사례집(상)(5판)_ocr_raw.txt"

출력: 같은 폴더에 _edited.txt 로 저장. 기존 raw는 덮어쓰지 않음.
"""
from pathlib import Path
import re
import sys

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# parse_saeryejip 와 동일한 패턴
SECTION_HEADER_RE = re.compile(
    r"^(?:--- PAGE \d+ ---\s*\n)?"
    r"([A-Z])-(\d+)\.\s*［",
    re.MULTILINE,
)
ANSWER_START_RE = re.compile(r"^1\s*\.\s*문제의 소재\s", re.MULTILINE)


def preprocess(text: str) -> str:
    text = re.sub(r"([A-Z])T\.\s*［", r"\1-1. ［", text)
    return text


def normalize_brackets_and_i(text: str) -> str:
    """OCR 오류: ［/］ vs 【/】 vs 대문자 I 혼용 정규화. 법조문은 ［ ］, 문제마커는 【문제-N】 유지."""
    # I제 / I第 → ［제 / ［第 (대문자 I가 여는 괄호 ［로 잘못 인식된 경우)
    text = re.sub(r"I제", "［제", text)
    text = re.sub(r"I第", "［第", text)
    # 본문에서 【가 ［로 쓰인 경우: 【문제- 숫자】 제외하고 【 → ［
    text = re.sub(r"【(?!문제-\d)", "［", text)
    # 법조문 닫는 괄호: 】가 ］로 쓰인 경우. 【문제-N】 안의 】는 숫자 뒤이므로 제외
    text = re.sub(r"(?<=\D)】", "］", text)
    return text


def remove_page_markers(text: str) -> str:
    """--- PAGE N --- 줄 제거."""
    return re.sub(r"^--- PAGE \d+ ---\s*$", "", text, flags=re.MULTILINE)


def collapse_blank_lines(text: str, max_blank: int = 2) -> str:
    """연속 빈 줄을 max_blank 개로 축소 (max_blank=2 → 빈 줄 하나 유지). 한 번에 처리."""
    return re.sub(r"\n{3,}", "\n\n", text)


def split_sections(full_text: str) -> list[tuple[str, str, str]]:
    """(ch, num, block) 리스트. 본문만."""
    sections = []
    for m in SECTION_HEADER_RE.finditer(full_text):
        ch, num = m.group(1), m.group(2)
        start = m.start()
        end = len(full_text)
        next_m = SECTION_HEADER_RE.search(full_text, m.end())
        if next_m:
            end = next_m.start()
        block = full_text[start:end]
        if ANSWER_START_RE.search(block):
            sections.append((ch, num, block))
    return sections


def ensure_blank_before_answer(block: str) -> str:
    """문제/설문 끝과 '1. 문제의 소재' 사이에 빈 줄 하나 확보."""
    m = ANSWER_START_RE.search(block)
    if not m:
        return block
    pos = m.start()
    # pos 앞에서 마지막 개행 두 개가 \n\n 이어야 함
    head = block[:pos]
    if not head:
        return block
    head = head.rstrip()
    if head.endswith("\n\n"):
        return block
    if head.endswith("\n"):
        return block[: pos - 1] + "\n" + block[pos:]  # \n → \n\n
    return block[:pos] + "\n\n" + block[pos:]


def strip_block_page_marker(block: str) -> str:
    """블록 맨 앞 '--- PAGE N ---' 제거."""
    return re.sub(r"^--- PAGE \d+ ---\s*\n?", "", block)


# 문제/설문/답안과 무관한 줄 제거 (페이지 푸터, 챕터 헤더 등) — 한 번에 매칭
FOOTER_CHAPTER_RE = re.compile(
    r"^(?:"
    r"[\d\s]*[•·]\s*윤곽\s*민사소송법\s*사례\s*집\s*上?편\s*|"
    r"[\d\s]*[•·]\s*윤곽민사소송법사례집\s*上?편\s*|"
    r"Chapter\s+[A-Z]\.\s*민사소송법\s*총론\s*[•·\s,\d]*|"
    r"Chapter\s+[A-Z]\.\s*소송의\s*주체\s*[-－]\s*법원\s*[•·\s\d]*|"
    r"Chapter\s+[A-Z]\.\s*소송의\s*주체[-－]법원\s*[•·\s\d]*|"
    r"Chapter\s+[A-Z]\s*\.?\s*소송의.*|"
    r"Chapter\s+[A-Z]\s*\.?\s*민사소송법.*|"
    r"윤곽\s*민사소송법\s*(?:사례|사레)\s*집\s*|"
    r"윤곽\s*민사소송법\s*참조\)\s*|"
    r"Chapter\s*|"
    r"[IVX]+[\s•·]*"
    r")$",
    re.IGNORECASE,
)


def drop_footer_chapter_lines(block: str) -> str:
    """블록에서 푸터/챕터 헤더 줄 제거. 줄당 정규식 1회만 사용."""
    lines = block.split("\n")
    kept = [line for line in lines if not line.strip() or not FOOTER_CHAPTER_RE.match(line.strip())]
    return "\n".join(kept)


def check_issues(text: str) -> list[str]:
    """줄바꿈/들여쓰기/밀림 검사. 발견된 이슈 설명 리스트."""
    issues = []
    lines = text.split("\n")
    # 연속 빈 줄 3개 이상
    blank_run = 0
    for i, line in enumerate(lines):
        if not line.strip():
            blank_run += 1
        else:
            if blank_run >= 3:
                issues.append("연속 빈 줄 %d개 (라인 %d 근처)" % (blank_run, i))
            blank_run = 0
    # 선두 공백(들여쓰기) 있는 줄 수
    leading_space = sum(1 for L in lines if L and L[0] in " \t")
    if leading_space:
        issues.append("선두 공백 있는 줄 %d개" % leading_space)
    # 한 글자만 있는 줄 (OCR 밀림 가능성)
    very_short = [i + 1 for i, L in enumerate(lines) if len(L.strip()) == 1 and L.strip()]
    if very_short and len(very_short) <= 20:
        issues.append("한 글자만 있는 줄 (라인: %s)" % (very_short[:15],))
    elif len(very_short) > 20:
        issues.append("한 글자만 있는 줄 %d개" % len(very_short))
    return issues


def main():
    if len(sys.argv) < 2:
        raw_path = project_root / "data" / "raw" / "civil_procedure" / "곽준형 윤곽 민소법 사례집(상)(5판)_ocr_raw.txt"
    else:
        raw_path = Path(sys.argv[1]).resolve()
        if not raw_path.is_absolute():
            raw_path = (project_root / raw_path).resolve()
    if not raw_path.exists():
        print("파일 없음:", raw_path)
        sys.exit(1)

    text = raw_path.read_text(encoding="utf-8")
    # 1) 페이지 표시 제거
    text = remove_page_markers(text)
    # 2) 연속 빈 줄 축소
    text = collapse_blank_lines(text)
    # 3) OCR 전처리
    text = preprocess(text)
    # 4) 섹션 분리 (문제+답 있는 블록만)
    sections = split_sections(text)
    # 5) 각 블록: 【문제-N】 부여, 문제/답 사이 빈 줄, 블록 내 페이지 표시 제거
    out_blocks = []
    for idx, (ch, num, block) in enumerate(sections):
        block = strip_block_page_marker(block)
        block = drop_footer_chapter_lines(block)
        block = ensure_blank_before_answer(block)
        out_blocks.append("【문제-%d】\n%s" % (idx + 1, block.strip()))
    out_text = "\n\n".join(out_blocks)
    # 6) 괄호/I 정규화 (［/］/】/I제)
    out_text = normalize_brackets_and_i(out_text)

    # 7) 검사
    issues = check_issues(out_text)
    if issues:
        print("검사 결과:")
        for s in issues:
            print("  -", s)
    else:
        print("검사: 특이사항 없음.")

    out_path = raw_path.parent / (raw_path.stem + "_edited.txt")
    out_path.write_text(out_text, encoding="utf-8")
    print("섹션(문제+답) %d개 → %s" % (len(sections), out_path))
    print("2단계(jsonl) 실행 시 이 파일 경로 사용: %s" % out_path.name)


if __name__ == "__main__":
    main()
