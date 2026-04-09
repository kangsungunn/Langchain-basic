"""
(문제/설문, 논점) 학습용 JSONL 생성

- 입력: 문제 JSONL, 모범답안 JSONL (id로 1:1 매칭)
- 모범답안 본문에서 "1. 제목 점수", "2. 제목 점수" 형태의 대목을 파싱해 논점(쟁점) 목록 추출
- 출력: problem_id, problem_content, issues(논점 문자열 리스트) 한 줄씩 JSONL

사용 예:
  python scripts/build_problem_issues_jsonl.py
  python scripts/build_problem_issues_jsonl.py --problems data/raw/civil_procedure/problems/gy_saeryejip_all.jsonl --answers data/raw/civil_procedure/model_answers/gy_saeryejip_all.jsonl --out data/raw/civil_procedure/problem_issues/gy_saeryejip_issues.jsonl
"""

import argparse
import json
import re
import sys
from pathlib import Path


def extract_issues_from_answer_text(answer_text: str) -> list[str]:
    """
    모범답안 본문에서 상위 논점만 추출.
    "1. 문제의 소재 0.5", "2. 표시정정신청의 부적법성 1" 같은 줄만 인식하고,
    "(1) 당사자 확정" 같은 하위 항목은 제외.
    """
    if not (answer_text or answer_text.strip()):
        return []
    issues = []
    for line in answer_text.split("\n"):
        line = line.strip()
        # 상위 번호: 줄 맨 앞이 "숫자. " 또는 "숫자, " (오타 대비)
        m = re.match(r"^\d+[.,]\s*(.+)$", line)
        if not m:
            continue
        title = m.group(1).strip()
        # 끝에 붙은 점수 제거 (예: "0.5", "1", "4.5")
        title = re.sub(r"\s+\d+(?:\.\d+)?\s*$", "", title).strip()
        if title:
            issues.append(title)
    return issues


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
    parser = argparse.ArgumentParser(description="Build (problem, issues) JSONL from problem + model_answer JSONL")
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
        default=Path("data/raw/civil_procedure/problem_issues/gy_saeryejip_issues.jsonl"),
        help="출력 (problem_issues) JSONL 경로",
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
            issues = extract_issues_from_answer_text(answer_text)
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
