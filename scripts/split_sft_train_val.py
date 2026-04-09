"""
SFT JSONL을 train / val 로 분할

- 입력: gy_saeryejip_sft.jsonl (instruction, input, output)
- 출력: training/data/issue_extraction/train.jsonl, val.jsonl
- 비율: 기본 90% train, 10% val (--val-ratio로 변경 가능)

사용 예:
  python scripts/split_sft_train_val.py
  python scripts/split_sft_train_val.py --sft data/raw/civil_procedure/problem_issues/gy_saeryejip_sft.jsonl --out-dir training/data/issue_extraction --val-ratio 0.1
"""

import argparse
import json
import random
import sys
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Split SFT JSONL into train/val")
    parser.add_argument(
        "--sft",
        type=Path,
        default=Path("data/raw/civil_procedure/problem_issues/gy_saeryejip_sft.jsonl"),
        help="SFT JSONL 경로",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("training/data/issue_extraction"),
        help="train.jsonl, val.jsonl 출력 디렉터리",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.1,
        help="검증 비율 (0~1, 기본 0.1)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="랜덤 시드",
    )
    args = parser.parse_args()

    if not args.sft.exists():
        print(f"파일 없음: {args.sft}", file=sys.stderr)
        sys.exit(1)

    rows = load_jsonl(args.sft)
    if not rows:
        print("데이터가 비어 있습니다.", file=sys.stderr)
        sys.exit(1)

    random.seed(args.seed)
    random.shuffle(rows)
    n_val = max(1, int(len(rows) * args.val_ratio))
    n_train = len(rows) - n_val
    train_data = rows[:n_train]
    val_data = rows[n_train:]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    train_path = args.out_dir / "train.jsonl"
    val_path = args.out_dir / "val.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for r in train_data:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(val_path, "w", encoding="utf-8") as f:
        for r in val_data:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"분할 완료: train {len(train_data)}건, val {len(val_data)}건")
    print(f"  - {train_path}")
    print(f"  - {val_path}")


if __name__ == "__main__":
    main()
