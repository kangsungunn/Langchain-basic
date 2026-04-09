"""
데이터 분할 스크립트

수집된 데이터를 학습/검증/테스트로 분할합니다.
"""

import sys
import json
import random
from pathlib import Path
from typing import List, Dict, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.utils.logger import get_logger

logger = get_logger(__name__)


def load_collected_data(input_file: Path) -> List[Dict[str, Any]]:
    """수집된 데이터 로드"""
    data = []

    if not input_file.exists():
        logger.error(f"[ERROR] 데이터 파일이 없습니다: {input_file}")
        return data

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"[WARN] JSON 파싱 실패: {e}")

    logger.info(f"[OK] 데이터 로드 완료: {len(data)}개")
    return data


def split_data(
    data: List[Dict[str, Any]],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    shuffle: bool = True,
    seed: int = 42
) -> tuple:
    """
    데이터 분할

    Args:
        data: 전체 데이터
        train_ratio: 학습 데이터 비율
        val_ratio: 검증 데이터 비율
        test_ratio: 테스트 데이터 비율
        shuffle: 셔플 여부
        seed: 랜덤 시드

    Returns:
        (train_data, val_data, test_data)
    """
    # 비율 검증
    total_ratio = train_ratio + val_ratio + test_ratio
    if abs(total_ratio - 1.0) > 0.01:
        raise ValueError(f"비율의 합이 1.0이어야 합니다. 현재: {total_ratio}")

    # 셔플
    if shuffle:
        random.seed(seed)
        data = data.copy()
        random.shuffle(data)

    # 분할
    total = len(data)
    train_size = int(total * train_ratio)
    val_size = int(total * val_ratio)

    train_data = data[:train_size]
    val_data = data[train_size:train_size+val_size]
    test_data = data[train_size+val_size:]

    logger.info(f"[SPLIT] 데이터 분할 완료:")
    logger.info(f"   - 학습: {len(train_data)}개 ({len(train_data)/total*100:.1f}%)")
    logger.info(f"   - 검증: {len(val_data)}개 ({len(val_data)/total*100:.1f}%)")
    logger.info(f"   - 테스트: {len(test_data)}개 ({len(test_data)/total*100:.1f}%)")

    return train_data, val_data, test_data


def save_data(data: List[Dict[str, Any]], output_file: Path, format_type: str = "training"):
    """
    데이터 저장

    Args:
        data: 저장할 데이터
        output_file: 출력 파일 경로
        format_type: 저장 형식 ("training" 또는 "raw")
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        for item in data:
            if format_type == "training":
                # 학습 형식으로 변환 (text, label만)
                training_item = {
                    "text": item.get("text", ""),
                    "label": item.get("label", 0)
                }
                f.write(json.dumps(training_item, ensure_ascii=False) + "\n")
            else:
                # 원본 형식으로 저장
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    logger.info(f"[SAVE] 데이터 저장 완료: {output_file} ({len(data)}개)")


def analyze_label_distribution(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """라벨 분포 분석"""
    distribution = {"policy": 0, "rule": 0, "unknown": 0}

    for item in data:
        label = item.get("label")
        if label == 0:
            distribution["policy"] += 1
        elif label == 1:
            distribution["rule"] += 1
        else:
            distribution["unknown"] += 1

    total = len(data)
    logger.info(f"[ANALYZE] 라벨 분포:")
    logger.info(f"   - 정책 기반 (0): {distribution['policy']}개 ({distribution['policy']/total*100:.1f}%)")
    logger.info(f"   - 규칙 기반 (1): {distribution['rule']}개 ({distribution['rule']/total*100:.1f}%)")
    if distribution['unknown'] > 0:
        logger.info(f"   - 알 수 없음: {distribution['unknown']}개")

    return distribution


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="데이터 분할 스크립트")
    parser.add_argument(
        "--input-file",
        type=str,
        default="training/data/collected_logs/collected_logs.jsonl",
        help="입력 파일 경로 (수집된 데이터)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="training/data/policy_rule_classification",
        help="출력 디렉토리"
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="학습 데이터 비율"
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.15,
        help="검증 데이터 비율"
    )
    parser.add_argument(
        "--test-ratio",
        type=float,
        default=0.15,
        help="테스트 데이터 비율"
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="셔플하지 않음"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="랜덤 시드"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("데이터 분할 스크립트")
    print("=" * 80)

    # 입력 파일 확인
    input_file = Path(args.input_file)
    if not input_file.exists():
        print(f"\n[ERROR] 입력 파일이 없습니다: {input_file}")
        print("\n해결 방법:")
        print("1. 데이터를 먼저 수집하세요: python training/orchestration/collect_real_data.py")
        print("2. 또는 다른 입력 파일을 지정하세요: --input-file <경로>")
        return

    # 데이터 로드
    print(f"\n[1단계] 데이터 로드 중...")
    print(f"입력 파일: {input_file}")
    data = load_collected_data(input_file)

    if not data:
        print("\n[ERROR] 데이터가 없습니다.")
        return

    # 라벨 분포 분석
    print(f"\n[2단계] 라벨 분포 분석 중...")
    distribution = analyze_label_distribution(data)

    # 데이터 분할
    print(f"\n[3단계] 데이터 분할 중...")
    train_data, val_data, test_data = split_data(
        data,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        shuffle=not args.no_shuffle,
        seed=args.seed
    )

    # 데이터 저장
    print(f"\n[4단계] 데이터 저장 중...")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    save_data(train_data, output_dir / "train.jsonl", format_type="training")
    save_data(val_data, output_dir / "val.jsonl", format_type="training")
    save_data(test_data, output_dir / "test.jsonl", format_type="training")

    print("\n" + "=" * 80)
    print("완료!")
    print("=" * 80)
    print(f"\n출력 디렉토리: {output_dir}")
    print(f"  - train.jsonl: {len(train_data)}개")
    print(f"  - val.jsonl: {len(val_data)}개")
    print(f"  - test.jsonl: {len(test_data)}개")
    print("\n다음 단계:")
    print("  python training/orchestration/train_koelectra_policy_rule.py \\")
    print(f"    --data-dir {output_dir}")


if __name__ == "__main__":
    main()
