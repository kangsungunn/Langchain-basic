"""
파인튜닝된 KoELECTRA 모델 사용 확인 테스트

실제 데이터 기준으로 작성된 코드입니다.
파인튜닝된 모델이 자동으로 사용되는지 확인합니다.
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.ml.koelectra_loader import KoELECTRALoader
from app.domain.v1.minso.hub.decision_maker import DecisionMaker


async def test_finetuned_model():
    """파인튜닝된 모델 사용 확인"""
    print("=" * 80)
    print("파인튜닝된 KoELECTRA 모델 사용 확인")
    print("=" * 80)

    # DecisionMaker 초기화 (자동으로 파인튜닝된 모델 사용)
    decision_maker = DecisionMaker()

    # 모델 경로 확인
    model_path = decision_maker.koelectra.model_path
    is_finetuned = "finetuned" in str(model_path)

    print(f"\n모델 경로: {model_path}")
    print(f"파인튜닝된 모델 사용: {'예' if is_finetuned else '아니오 (베이스 모델)'}")

    if is_finetuned:
        print("[OK] 파인튜닝된 모델이 자동으로 선택되었습니다.")
    else:
        print("[INFO] 베이스 모델을 사용합니다. (파인튜닝된 모델이 없거나 감지되지 않음)")

    # 모델 사용 가능 여부 확인
    is_available = decision_maker.koelectra.is_available()
    print(f"모델 사용 가능: {'예' if is_available else '아니오'}")

    if not is_available:
        print("[ERROR] 모델을 사용할 수 없습니다.")
        return

    # 테스트 요청
    print("\n" + "-" * 80)
    print("테스트 요청")
    print("-" * 80)

    test_cases = [
        ("reasoning", "comprehensive_analysis", {"user_answer_id": "test"}),
        ("training", "create_training_data", {"problem_text": "test"}),
        ("submission", "create_text_answer", {"problem_id": "test", "content": "test"}),
    ]

    for domain, action, request in test_cases:
        try:
            strategy = await decision_maker.determine_strategy(domain, action, request)
            print(f"\n도메인: {domain}, 액션: {action}")
            print(f"판단 결과: {strategy}")
        except Exception as e:
            print(f"\n도메인: {domain}, 액션: {action}")
            print(f"오류: {e}")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_finetuned_model())
