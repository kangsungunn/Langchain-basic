"""
생성된 데이터 확인 스크립트
"""

import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_data(data_dir: str = "training/data/policy_rule_classification"):
    """생성된 데이터 확인"""
    data_dir = Path(data_dir)

    for split in ["train", "val", "test"]:
        file_path = data_dir / f"{split}.jsonl"
        if not file_path.exists():
            print(f"[ERROR] {split}.jsonl 파일이 없습니다.")
            continue

        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))

        labels = [d['label'] for d in data]
        rule_count = labels.count(0)
        policy_count = labels.count(1)

        print(f"\n[{split}] 데이터:")
        print(f"   - 총 샘플: {len(data)}개")
        print(f"   - 규칙 기반 (0): {rule_count}개")
        print(f"   - 정책 기반 (1): {policy_count}개")

if __name__ == "__main__":
    check_data()
