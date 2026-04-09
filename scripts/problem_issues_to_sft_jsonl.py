"""
(문제, 논점) JSONL → ExaOne SFT용 JSONL 변환

- 입력: gy_saeryejip_issues.jsonl (problem_id, problem_content, issues)
- 출력: instruction + input + output 한 줄씩 (Alpaca 스타일)
- ExaOne 등 SFT/채팅 학습에 바로 넣을 수 있는 형식으로 저장.

사용 예:
  python scripts/problem_issues_to_sft_jsonl.py
  python scripts/problem_issues_to_sft_jsonl.py --issues data/raw/civil_procedure/problem_issues/gy_saeryejip_issues.jsonl --out data/raw/civil_procedure/problem_issues/gy_saeryejip_sft.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

DEFAULT_INSTRUCTION = (
    "다음 민사소송법 사례 문제에서, 답안에 반드시 다뤄야 할 논점(쟁점)을 나열하세요. "
    "논점 제목만 한 줄에 하나씩 출력하세요."
)


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
    parser = argparse.ArgumentParser(description="Convert problem_issues JSONL to SFT (instruction/input/output) JSONL")
    parser.add_argument(
        "--issues",
        type=Path,
        default=Path("data/raw/civil_procedure/problem_issues/gy_saeryejip_issues.jsonl"),
        help="(문제, 논점) JSONL 경로",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/raw/civil_procedure/problem_issues/gy_saeryejip_sft.jsonl"),
        help="출력 SFT JSONL 경로",
    )
    parser.add_argument(
        "--instruction",
        type=str,
        default=DEFAULT_INSTRUCTION,
        help="고정 instruction 문구",
    )
    args = parser.parse_args()

    if not args.issues.exists():
        print(f"파일 없음: {args.issues}", file=sys.stderr)
        sys.exit(1)

    rows = load_jsonl(args.issues)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as out_f:
        for r in rows:
            content = (r.get("problem_content") or "").strip()
            issues = r.get("issues") or []
            output_text = "\n".join(issues) if issues else ""
            record = {
                "instruction": args.instruction,
                "input": content,
                "output": output_text,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"SFT JSONL 쓰기 완료: {args.out} (총 {len(rows)}건)")


if __name__ == "__main__":
    main()
