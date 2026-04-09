"""
KoELECTRA 모델 성능 비교 테스트

베이스 모델 vs 파인튜닝된 모델의 성능을 비교합니다.
- 판단 정확도
- 추론 속도
- 일관성
"""

import sys
import asyncio
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any
import statistics

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.ml.koelectra_loader import KoELECTRALoader
from app.domain.v1.minso.hub.decision_maker import DecisionMaker


class PerformanceComparator:
    """성능 비교 클래스"""

    def __init__(self):
        self.test_cases = [
            # (domain, action, request, expected_strategy)
            ("reasoning", "comprehensive_analysis", {"user_answer_id": "test-1"}, "policy"),
            ("training", "create_training_data", {"problem_text": "test"}, "rule"),
            ("submission", "create_text_answer", {"problem_id": "test", "content": "test"}, "rule"),
            ("reasoning", "create_task", {"problem_id": "test"}, "rule"),
            ("feedback", "generate_feedback", {"reasoning_result_id": "test"}, "policy"),
        ]

    async def test_model(
        self,
        model_path: Path = None,
        model_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        모델 성능 테스트

        Args:
            model_path: 모델 경로 (None이면 자동 선택)
            model_name: 모델 이름 (로깅용)

        Returns:
            성능 결과 딕셔너리
        """
        print(f"\n{'=' * 80}")
        print(f"모델 테스트: {model_name}")
        print(f"{'=' * 80}")

        # 싱글톤 인스턴스 리셋 (이전 모델 언로드)
        KoELECTRALoader.reset_instance()

        # 특정 모델 경로로 인스턴스 생성 (DecisionMaker 생성 전에)
        if model_path:
            koelectra = KoELECTRALoader.get_instance(model_path=str(model_path))
        else:
            koelectra = KoELECTRALoader.get_instance()  # 자동 선택

        # DecisionMaker 초기화 (이미 생성된 인스턴스 사용)
        decision_maker = DecisionMaker()
        # DecisionMaker가 자동으로 get_instance()를 호출하지만, 이미 생성된 인스턴스를 사용
        decision_maker.koelectra = koelectra  # 명시적으로 교체

        # 모델 경로 확인
        actual_path = decision_maker.koelectra.model_path
        is_finetuned = "finetuned" in str(actual_path)

        print(f"사용된 모델 경로: {actual_path}")
        print(f"파인튜닝된 모델: {'예' if is_finetuned else '아니오'}")

        # 모델 사용 가능 여부 확인
        if not decision_maker.koelectra.is_available():
            print("[ERROR] 모델을 사용할 수 없습니다.")
            return {
                "model_name": model_name,
                "model_path": str(actual_path),
                "is_finetuned": is_finetuned,
                "available": False,
                "results": None
            }

        # 테스트 실행
        results = []
        inference_times = []

        for domain, action, request, expected_strategy in self.test_cases:
            try:
                # 추론 시간 측정
                start_time = time.time()
                predicted_strategy = await decision_maker.determine_strategy(
                    domain, action, request
                )
                inference_time = (time.time() - start_time) * 1000  # ms

                # 결과 저장
                is_correct = predicted_strategy == expected_strategy
                results.append({
                    "domain": domain,
                    "action": action,
                    "expected": expected_strategy,
                    "predicted": predicted_strategy,
                    "correct": is_correct,
                    "inference_time_ms": inference_time
                })

                inference_times.append(inference_time)

                status = "[OK]" if is_correct else "[FAIL]"
                print(
                    f"{status} {domain}.{action}: "
                    f"예상={expected_strategy}, 예측={predicted_strategy}, "
                    f"시간={inference_time:.2f}ms"
                )

            except Exception as e:
                print(f"[ERROR] {domain}.{action}: {e}")
                results.append({
                    "domain": domain,
                    "action": action,
                    "expected": expected_strategy,
                    "predicted": None,
                    "correct": False,
                    "error": str(e),
                    "inference_time_ms": None
                })

        # 통계 계산
        correct_count = sum(1 for r in results if r.get("correct", False))
        total_count = len(results)
        accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

        valid_times = [t for t in inference_times if t is not None]
        avg_inference_time = statistics.mean(valid_times) if valid_times else 0
        median_inference_time = statistics.median(valid_times) if valid_times else 0

        return {
            "model_name": model_name,
            "model_path": str(actual_path),
            "is_finetuned": is_finetuned,
            "available": True,
            "accuracy": accuracy,
            "correct_count": correct_count,
            "total_count": total_count,
            "avg_inference_time_ms": avg_inference_time,
            "median_inference_time_ms": median_inference_time,
            "results": results
        }

    def compare_results(
        self,
        base_results: Dict[str, Any],
        finetuned_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """두 모델 결과 비교"""
        comparison = {
            "base_model": {
                "name": base_results["model_name"],
                "accuracy": base_results.get("accuracy", 0),
                "avg_inference_time_ms": base_results.get("avg_inference_time_ms", 0),
                "available": base_results.get("available", False)
            },
            "finetuned_model": {
                "name": finetuned_results["model_name"],
                "accuracy": finetuned_results.get("accuracy", 0),
                "avg_inference_time_ms": finetuned_results.get("avg_inference_time_ms", 0),
                "available": finetuned_results.get("available", False)
            },
            "improvement": {
                "accuracy_delta": finetuned_results.get("accuracy", 0) - base_results.get("accuracy", 0),
                "speed_delta_ms": finetuned_results.get("avg_inference_time_ms", 0) - base_results.get("avg_inference_time_ms", 0),
                "speed_ratio": (
                    base_results.get("avg_inference_time_ms", 1) /
                    finetuned_results.get("avg_inference_time_ms", 1)
                    if finetuned_results.get("avg_inference_time_ms", 0) > 0 else 0
                )
            }
        }

        return comparison

    def print_comparison(self, comparison: Dict[str, Any]):
        """비교 결과 출력"""
        print("\n" + "=" * 80)
        print("성능 비교 결과")
        print("=" * 80)

        base = comparison["base_model"]
        finetuned = comparison["finetuned_model"]
        improvement = comparison["improvement"]

        print(f"\n베이스 모델 ({base['name']}):")
        print(f"  정확도: {base['accuracy']:.2f}%")
        print(f"  평균 추론 시간: {base['avg_inference_time_ms']:.2f}ms")
        print(f"  사용 가능: {'예' if base['available'] else '아니오'}")

        print(f"\n파인튜닝된 모델 ({finetuned['name']}):")
        print(f"  정확도: {finetuned['accuracy']:.2f}%")
        print(f"  평균 추론 시간: {finetuned['avg_inference_time_ms']:.2f}ms")
        print(f"  사용 가능: {'예' if finetuned['available'] else '아니오'}")

        print(f"\n개선 사항:")
        accuracy_delta = improvement["accuracy_delta"]
        speed_delta = improvement["speed_delta_ms"]
        speed_ratio = improvement["speed_ratio"]

        if accuracy_delta > 0:
            print(f"  정확도 향상: +{accuracy_delta:.2f}%p")
        elif accuracy_delta < 0:
            print(f"  정확도 감소: {accuracy_delta:.2f}%p")
        else:
            print(f"  정확도 변화 없음")

        if speed_delta < 0:
            print(f"  속도 향상: {abs(speed_delta):.2f}ms 빠름 ({speed_ratio:.2f}x)")
        elif speed_delta > 0:
            print(f"  속도 감소: {speed_delta:.2f}ms 느림 ({1/speed_ratio:.2f}x)")
        else:
            print(f"  속도 변화 없음")

        print("\n" + "=" * 80)


async def main():
    """메인 함수"""
    print("=" * 80)
    print("KoELECTRA 모델 성능 비교 테스트")
    print("=" * 80)

    comparator = PerformanceComparator()

    # 베이스 모델 경로
    base_model_path = project_root / "artifacts" / "models" / "base" / "koelectra-small-v3-discriminator"
    finetuned_model_path = project_root / "artifacts" / "models" / "finetuned" / "koelectra-policy-rule"

    # 1. 베이스 모델 테스트
    print("\n[1단계] 베이스 모델 테스트")
    base_results = await comparator.test_model(
        model_path=base_model_path,
        model_name="베이스 모델"
    )

    # 2. 파인튜닝된 모델 테스트
    print("\n[2단계] 파인튜닝된 모델 테스트")
    finetuned_results = await comparator.test_model(
        model_path=finetuned_model_path if finetuned_model_path.exists() else None,
        model_name="파인튜닝된 모델"
    )

    # 3. 결과 비교
    if base_results.get("available") and finetuned_results.get("available"):
        comparison = comparator.compare_results(base_results, finetuned_results)
        comparator.print_comparison(comparison)
    else:
        print("\n[WARN] 일부 모델을 사용할 수 없어 비교를 수행할 수 없습니다.")
        if not base_results.get("available"):
            print(f"  베이스 모델 사용 불가: {base_results.get('model_path')}")
        if not finetuned_results.get("available"):
            print(f"  파인튜닝된 모델 사용 불가: {finetuned_results.get('model_path')}")

    print("\n테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
