"""
(문제, 큰 논점 + 세부논점) 계층형 JSONL 생성

- 문제/설문에 따라 "큰 논점"만 두고, 모범답안과 매칭해 각 큰 논점 안에 "세부논점"을 붙이는 2단계 구조.
- 입력: 문제 JSONL, 모범답안 JSONL (id로 1:1 매칭)
- 모범답안 본문에서:
  - "1. 제목", "2. 제목" → 큰 논점
  - "(1) 세부제목", "(2) 세부제목" → 해당 큰 논점 아래 세부논점
- 출력: problem_id, problem_content, issues: [ { "title": "큰 논점", "sub_issues": ["세부1", "세부2"] }, ... ]

사용 예:
  python scripts/build_problem_issues_hierarchical_jsonl.py
"""

import argparse
import json
import re
import sys
from pathlib import Path


def _clean_title(s: str) -> str:
    """끝에 붙은 점수 제거."""
    return re.sub(r"\s+\d+(?:\.\d+)?\s*$", "", s).strip()


def extract_hierarchical_issues_from_answer_text(answer_text: str) -> list[dict]:
    """
    모범답안 본문에서 큰 논점(상위)과 세부논점(하위)을 계층으로 추출.

    - "1. 제목 점수", "2. 제목 점수" → 큰 논점
    - "(1) 세부제목", "(2) 세부제목" → 직전 큰 논점의 세부논점
    - "1) 제목", "2) 제목" (괄호 없음)은 더 하위이므로 여기서는 같은 세부 수준으로만 수집
      (필요 시 나중에 3단계로 확장 가능)
    """
    if not (answer_text or answer_text.strip()):
        return []
    result: list[dict] = []
    current: dict | None = None

    for line in answer_text.split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 상위: "1. 제목", "2. 제목"
        m_top = re.match(r"^\d+[.,]\s*(.+)$", line_stripped)
        if m_top:
            title = _clean_title(m_top.group(1).strip())
            if title:
                current = {"title": title, "sub_issues": []}
                result.append(current)
            continue

        # 세부: "(1) 제목", "(2) 제목"
        m_sub = re.match(r"^\s*\(\d+\)\s*(.+)$", line_stripped)
        if m_sub and current is not None:
            sub_title = _clean_title(m_sub.group(1).strip())
            if sub_title:
                current["sub_issues"].append(sub_title)
            continue

        # 선택: "1) 제목", "2) 제목" (괄호 없음) → 같은 큰 논점 아래 세부로 넣기 (세세 논점은 생략)
        m_sub_alt = re.match(r"^\s*\d+\)\s*(.+)$", line_stripped)
        if m_sub_alt and current is not None:
            # 이미 (1), (2)가 있는 경우 1), 2)는 더 하위이므로 스킵하거나, 세부로 넣을지 정책에 따라 결정.
            # 여기서는 "세부" 한 단계만 쓰므로, (N) 형태만 세부논점으로 두고 1), 2)는 스킵.
            pass

    return result


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build (problem, issues with sub_issues) hierarchical JSONL from problem + model_answer JSONL"
    )
    parser.add_argument(
        "--problems",
        type=Path,
        default=Path("data/raw/civil_procedure/problems/gy_saeryejip_all.jsonl"),
        help="문제 JSONL 경로",
    )
    parser.add_argument(
        "--answers",
        type=Path,
        default=Path("data/raw/civil_procedure/model_answers/gy_saeryejip_all.jsonl"),
        help="모범답안 JSONL 경로",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/raw/civil_procedure/problem_issues/gy_saeryejip_issues_hierarchical.jsonl"),
        help="출력 계층형 JSONL 경로",
    )
    args = parser.parse_args()

    if not args.problems.exists():
        print(f"문제 파일 없음: {args.problems}", file=sys.stderr)
        sys.exit(1)
    if not args.answers.exists():
        print(f"모범답안 파일 없음: {args.answers}", file=sys.stderr)
        sys.exit(1)

    problems = load_jsonl(args.problems)
    answers = load_jsonl(args.answers)
    by_id_problems = {p["id"]: p for p in problems}
    by_id_answers = {a["id"]: a for a in answers}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    with open(args.out, "w", encoding="utf-8") as out_f:
        for pid, ans in by_id_answers.items():
            prob = by_id_problems.get(pid)
            if not prob:
                skipped += 1
                continue
            answer_text = ""
            if ans.get("answers"):
                answer_text = (ans["answers"][0].get("answer") or "").strip()
            issues = extract_hierarchical_issues_from_answer_text(answer_text)
            content = (prob.get("content") or "").strip()
            record = {
                "problem_id": pid,
                "problem_content": content,
                "issues": issues,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(f"쓰기 완료: {args.out} (총 {written}건, id 불일치 스킵 {skipped}건)")


if __name__ == "__main__":
    main()
