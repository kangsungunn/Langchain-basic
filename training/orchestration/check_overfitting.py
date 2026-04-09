"""
오버피팅 확인 스크립트

학습 로그를 분석하여 오버피팅 여부를 확인합니다.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.utils.logger import get_logger

logger = get_logger(__name__)


def parse_training_logs(log_dir: Path) -> Dict[str, List[float]]:
    """
    학습 로그 파싱

    Args:
        log_dir: 로그 디렉토리 경로

    Returns:
        학습 메트릭 딕셔너리
    """
    metrics = {
        "train_loss": [],
        "eval_loss": [],
        "eval_accuracy": [],
        "eval_f1": [],
        "epoch": []
    }

    # 로그 파일 찾기
    log_files = list(log_dir.glob("**/trainer_state.json"))

    if not log_files:
        logger.warning(f"[WARN] 학습 로그 파일을 찾을 수 없습니다: {log_dir}")
        return metrics

    # 가장 최근 로그 파일 사용
    log_file = log_files[0]

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        # 로그 기록 추출
        log_history = log_data.get("log_history", [])

        for entry in log_history:
            epoch = entry.get("epoch")
            if epoch is not None:
                metrics["epoch"].append(epoch)

            # 학습 손실
            if "loss" in entry:
                metrics["train_loss"].append(entry["loss"])

            # 검증 손실
            if "eval_loss" in entry:
                metrics["eval_loss"].append(entry["eval_loss"])

            # 검증 정확도
            if "eval_accuracy" in entry:
                metrics["eval_accuracy"].append(entry["eval_accuracy"])

            # 검증 F1
            if "eval_f1" in entry:
                metrics["eval_f1"].append(entry["eval_f1"])

        logger.info(f"[OK] 로그 파싱 완료: {len(log_history)}개 기록")

    except Exception as e:
        logger.error(f"[ERROR] 로그 파싱 실패: {e}")

    return metrics


def check_overfitting(metrics: Dict[str, List[float]]) -> Dict[str, Any]:
    """
    오버피팅 확인

    Args:
        metrics: 학습 메트릭

    Returns:
        오버피팅 분석 결과
    """
    result = {
        "has_overfitting": False,
        "overfitting_indicators": [],
        "train_final_loss": None,
        "eval_final_loss": None,
        "train_final_accuracy": None,
        "eval_final_accuracy": None,
        "loss_gap": None,
        "accuracy_gap": None,
        "recommendations": []
    }

    train_loss = metrics.get("train_loss", [])
    eval_loss = metrics.get("eval_loss", [])
    eval_accuracy = metrics.get("eval_accuracy", [])

    if not train_loss or not eval_loss:
        result["recommendations"].append("학습 로그가 충분하지 않습니다. 학습을 다시 실행하세요.")
        return result

    # 최종 값
    result["train_final_loss"] = train_loss[-1] if train_loss else None
    result["eval_final_loss"] = eval_loss[-1] if eval_loss else None
    result["eval_final_accuracy"] = eval_accuracy[-1] if eval_accuracy else None

    # 손실 차이
    if result["train_final_loss"] and result["eval_final_loss"]:
        result["loss_gap"] = result["eval_final_loss"] - result["train_final_loss"]

    # 정확도 차이 (검증 정확도만 있으므로 학습 정확도는 추정 불가)

    # 오버피팅 지표 확인
    # 1. 검증 손실이 학습 손실보다 크고, 그 차이가 증가하는 경우
    if len(eval_loss) >= 2 and len(train_loss) >= 2:
        eval_loss_trend = eval_loss[-1] - eval_loss[-2]
        train_loss_trend = train_loss[-1] - train_loss[-2]

        if eval_loss_trend > 0 and train_loss_trend < 0:
            result["has_overfitting"] = True
            result["overfitting_indicators"].append(
                "검증 손실이 증가하는 동안 학습 손실이 감소함 (오버피팅 징후)"
            )

    # 2. 검증 손실이 학습 손실보다 훨씬 큰 경우
    if result["loss_gap"] and result["loss_gap"] > 0.3:
        result["has_overfitting"] = True
        result["overfitting_indicators"].append(
            f"검증 손실이 학습 손실보다 {result['loss_gap']:.3f}만큼 큼 (오버피팅 징후)"
        )

    # 3. 검증 손실이 증가하는 추세
    if len(eval_loss) >= 3:
        recent_eval_loss = eval_loss[-3:]
        if recent_eval_loss[0] < recent_eval_loss[1] < recent_eval_loss[2]:
            result["has_overfitting"] = True
            result["overfitting_indicators"].append(
                "검증 손실이 지속적으로 증가하는 추세 (오버피팅 징후)"
            )

    # 권장 사항
    if result["has_overfitting"]:
        result["recommendations"].extend([
            "에폭 수를 줄이세요 (예: 3 → 2)",
            "학습률을 낮추세요 (예: 2e-5 → 1e-5)",
            "정규화를 강화하세요 (weight_decay 증가)",
            "드롭아웃을 추가하세요",
            "더 많은 학습 데이터를 수집하세요",
            "Early stopping을 사용하세요"
        ])
    else:
        result["recommendations"].append("현재 오버피팅 징후가 없습니다. 모델이 일반화되고 있습니다.")

    return result


def print_analysis(metrics: Dict[str, List[float]], analysis: Dict[str, Any]):
    """분석 결과 출력"""
    print("\n" + "=" * 80)
    print("오버피팅 분석 결과")
    print("=" * 80)

    # 메트릭 요약
    print("\n[메트릭 요약]")
    if metrics.get("epoch"):
        print(f"  총 에폭 수: {len(set(metrics['epoch']))}")

    if analysis.get("train_final_loss") is not None:
        print(f"  최종 학습 손실: {analysis['train_final_loss']:.4f}")

    if analysis.get("eval_final_loss") is not None:
        print(f"  최종 검증 손실: {analysis['eval_final_loss']:.4f}")

    if analysis.get("loss_gap") is not None:
        gap = analysis['loss_gap']
        status = "[주의]" if gap > 0.3 else "[정상]"
        print(f"  손실 차이 (검증 - 학습): {gap:.4f} {status}")

    if analysis.get("eval_final_accuracy") is not None:
        print(f"  최종 검증 정확도: {analysis['eval_final_accuracy']:.4f}")

    # 오버피팅 여부
    print("\n[오버피팅 여부]")
    if analysis["has_overfitting"]:
        print("  상태: [주의] 오버피팅 징후가 있습니다")
        print("\n  오버피팅 지표:")
        for indicator in analysis["overfitting_indicators"]:
            print(f"    - {indicator}")
    else:
        print("  상태: [정상] 오버피팅 징후가 없습니다")

    # 권장 사항
    print("\n[권장 사항]")
    for recommendation in analysis["recommendations"]:
        print(f"  - {recommendation}")

    print("\n" + "=" * 80)


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="오버피팅 확인 스크립트")
    parser.add_argument(
        "--model-dir",
        type=str,
        default="artifacts/models/finetuned/koelectra-policy-rule",
        help="모델 디렉토리 (로그 포함)"
    )

    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    log_dir = model_dir / "logs"

    print("=" * 80)
    print("오버피팅 확인 스크립트")
    print("=" * 80)
    print(f"\n모델 디렉토리: {model_dir}")
    print(f"로그 디렉토리: {log_dir}")

    if not log_dir.exists():
        print(f"\n[ERROR] 로그 디렉토리가 없습니다: {log_dir}")
        print("\n해결 방법:")
        print("1. 학습을 다시 실행하여 로그를 생성하세요")
        print("2. 또는 다른 모델 디렉토리를 지정하세요: --model-dir <경로>")
        return

    # 로그 파싱
    print("\n[1단계] 학습 로그 파싱 중...")
    metrics = parse_training_logs(log_dir)

    if not metrics.get("train_loss"):
        print("\n[ERROR] 학습 로그를 찾을 수 없습니다.")
        return

    # 오버피팅 확인
    print("\n[2단계] 오버피팅 확인 중...")
    analysis = check_overfitting(metrics)

    # 결과 출력
    print_analysis(metrics, analysis)


if __name__ == "__main__":
    main()
