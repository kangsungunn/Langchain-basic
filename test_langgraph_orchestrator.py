"""
LangGraph 오케스트레이터 테스트 스크립트

LangGraph 전환 후 오케스트레이터 동작 확인
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session, get_database
from app.domain.v1.minso.hub.orchestrators import MinsoHub
from app.domain.v1.minso.models.transfers import ComprehensiveAnalysisRequest
from training.schemas import TrainingDataCreate
from app.core.utils.test_data_factory import (
    create_test_data_for_analysis,
    create_test_training_data
)
import os


async def test_rule_based_request():
    """규칙 기반 요청 테스트"""
    print("\n" + "="*80)
    print("📋 규칙 기반 요청 테스트: 학습 데이터 생성")
    print("="*80)

    result = False
    try:
        async for session in get_session():
            try:
                hub = MinsoHub(session)

                # 규칙 기반 요청 (create_training_data)
                request = TrainingDataCreate(
                    problem_text="민사소송법에서 소송요건의 의미를 설명하시오.",
                    reference_answer_text="소송요건은 소송을 제기하기 위해 필요한 요건으로...",
                    user_answer_text="소송요건은 소송을 제기하기 위한 조건입니다.",
                    labels={}
                )

                result = await hub.process(
                    domain="training",
                    action="create_training_data",
                    request=request
                )

                print(f"✅ 규칙 기반 요청 성공!")
                print(f"📊 결과 타입: {type(result)}")
                if hasattr(result, 'id'):
                    print(f"📋 생성된 ID: {result.id}")

                result = True
                break  # 성공 시 루프 종료

            except Exception as e:
                print(f"❌ 규칙 기반 요청 실패: {e}")
                import traceback
                traceback.print_exc()
                result = False
                break  # 실패 시 루프 종료
    except Exception as e:
        print(f"❌ 세션 획득 실패: {e}")
        import traceback
        traceback.print_exc()
        result = False

    return result




async def test_policy_based_request():
    """정책 기반 요청 테스트"""
    print("\n" + "="*80)
    print("🎯 정책 기반 요청 테스트: 종합 분석")
    print("="*80)

    result = False
    try:
        async for session in get_session():
            try:
                # 더미 데이터 생성 (실제 데이터 기준 코드 사용)
                print("\n📝 테스트용 더미 데이터 생성 중...")
                try:
                    user_answer_id, reference_answer_id, problem_id = await create_test_data_for_analysis(session)
                    print(f"✅ 더미 데이터 생성 완료")
                    print(f"   └─ Problem ID: {problem_id}")
                    print(f"   └─ Reference Answer ID: {reference_answer_id}")
                    print(f"   └─ User Answer ID: {user_answer_id}")
                except Exception as e:
                    print(f"❌ 더미 데이터 생성 실패: {e}")
                    import traceback
                    traceback.print_exc()
                    result = False
                    break  # 실패 시 루프 종료

                hub = MinsoHub(session)

                # 정책 기반 요청 (comprehensive_analysis)
                # 실제 데이터 기준으로 작성된 코드 사용
                request = ComprehensiveAnalysisRequest(
                    user_answer_id=user_answer_id,  # 실제 DB에 생성된 ID 사용
                    reference_answer_id=reference_answer_id,  # 실제 DB에 생성된 ID 사용
                    problem_id=problem_id,  # 실제 DB에 생성된 ID 사용
                    save_result=False
                )

                analysis_result = await hub.process(
                    domain="reasoning",
                    action="comprehensive_analysis",
                    request=request
                )

                print(f"✅ 정책 기반 요청 성공!")
                print(f"📊 결과 타입: {type(analysis_result)}")
                if isinstance(analysis_result, dict):
                    print(f"📋 결과 키: {list(analysis_result.keys())}")

                result = True
                break  # 성공 시 루프 종료

            except Exception as e:
                print(f"❌ 정책 기반 요청 실패: {e}")
                import traceback
                traceback.print_exc()
                result = False
                break  # 실패 시 루프 종료
    except Exception as e:
        print(f"❌ 세션 획득 실패: {e}")
        import traceback
        traceback.print_exc()
        result = False

    return result


async def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("🧪 LangGraph 오케스트레이터 테스트")
    print("="*80)
    print("\n⚠️  주의: 데이터베이스 연결이 필요합니다.")
    print("="*80)

    # 데이터베이스 초기화
    print("\n🔄 데이터베이스 초기화 중...")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL 환경 변수가 설정되지 않았습니다.")
        print("💡 .env 파일에 DATABASE_URL을 설정하세요.")
        return

    db = get_database()
    engine = db.connect(database_url)
    if not engine:
        print("❌ 데이터베이스 연결 실패")
        return

    print("✅ 데이터베이스 연결 완료\n")

    results = []

    # 규칙 기반 테스트
    rule_result = await test_rule_based_request()
    results.append(("규칙 기반 요청", rule_result))

    # 정책 기반 테스트
    policy_result = await test_policy_based_request()
    results.append(("정책 기반 요청", policy_result))

    # 결과 요약
    print("\n" + "="*80)
    print("📊 테스트 결과 요약")
    print("="*80)
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)
    print("="*80)
    if all_passed:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("="*80)

    # 데이터베이스 연결 해제
    print("\n🔄 데이터베이스 연결 해제 중...")
    await db.disconnect()
    print("✅ 데이터베이스 연결 해제 완료")


if __name__ == "__main__":
    asyncio.run(main())
