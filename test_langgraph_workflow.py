#!/usr/bin/env python3
"""
LangGraph Workflow 통합 테스트

주체: LangGraph Orchestrator
역할: 전체 워크플로우 테스트 (Gateway → Hub Router → Branch → Star → DB)

실행 방법:
    python test_langgraph_workflow.py
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from app.services.langgraph_workflow import run_workflow


def test_spam_detection():
    """스팸 감지 테스트"""
    print("\n" + "=" * 70)
    print("테스트 1: 스팸 이메일 감지")
    print("=" * 70)

    text = "긴급송금 필요! 계좌번호 알려주세요! 당첨되셨습니다!"

    final_state = run_workflow(
        text=text,
        user_id="test_user_001",
        source="test",
        db=None  # DB 저장 스킵
    )

    print("\n" + "-" * 70)
    print("테스트 결과 검증")
    print("-" * 70)

    # 검증
    assert final_state.get("gateway_route") in ["spam_agent", "reject"], \
        f"Gateway가 스팸을 감지해야 함: {final_state.get('gateway_route')}"

    assert final_state.get("selected_branch") in ["spam_agent", "default_agent"], \
        f"Hub Router가 브랜치를 선택해야 함: {final_state.get('selected_branch')}"

    assert final_state.get("label") in ["spam", "suspicious"], \
        f"Branch가 스팸/의심으로 판정해야 함: {final_state.get('label')}"

    assert final_state.get("final_action") in ["block", "quarantine"], \
        f"Star가 block/quarantine 결정해야 함: {final_state.get('final_action')}"

    print("✅ 모든 검증 통과!")
    print(f"   Gateway: {final_state.get('gateway_route')} ({final_state.get('gateway_method')})")
    print(f"   Branch: {final_state.get('label')} (신뢰도: {final_state.get('branch_confidence'):.2f})")
    print(f"   Star: {final_state.get('final_action')} - {final_state.get('policy_reason')}")


def test_normal_email():
    """정상 이메일 테스트"""
    print("\n" + "=" * 70)
    print("테스트 2: 정상 이메일")
    print("=" * 70)

    text = "회의 일정을 조율하고 싶습니다. 다음 주 화요일 오후 2시는 어떠신가요?"

    final_state = run_workflow(
        text=text,
        user_id="test_user_002",
        source="test",
        db=None
    )

    print("\n" + "-" * 70)
    print("테스트 결과 검증")
    print("-" * 70)

    # 검증 (정상 메일은 default_agent로 가거나 spam_agent에서 ham 판정)
    print(f"   Gateway: {final_state.get('gateway_route')} ({final_state.get('gateway_method')})")
    print(f"   Branch: {final_state.get('label')} (신뢰도: {final_state.get('branch_confidence'):.2f})")
    print(f"   Star: {final_state.get('final_action')} - {final_state.get('policy_reason')}")

    print("✅ 정상 처리 완료!")


def test_performance():
    """성능 테스트"""
    print("\n" + "=" * 70)
    print("테스트 3: 성능 테스트")
    print("=" * 70)

    text = "환불 요청합니다. 제품이 불량입니다."

    final_state = run_workflow(
        text=text,
        user_id="test_user_003",
        source="test",
        db=None
    )

    print("\n" + "-" * 70)
    print("성능 메트릭")
    print("-" * 70)

    total_latency = final_state.get("total_latency_ms", 0)
    gateway_latency = final_state.get("gateway_latency_ms", 0)
    branch_latency = final_state.get("branch_latency_ms", 0)

    print(f"   전체 지연 시간: {total_latency:.2f}ms")
    print(f"   Gateway 지연 시간: {gateway_latency:.2f}ms")
    print(f"   Branch 지연 시간: {branch_latency:.2f}ms")

    # 성능 목표 확인
    assert total_latency < 5000, \
        f"전체 지연 시간이 5초를 초과했습니다: {total_latency:.2f}ms"

    print("✅ 성능 목표 달성!")


def test_workflow_stats():
    """워크플로우 통계"""
    print("\n" + "=" * 70)
    print("테스트 4: 워크플로우 통계")
    print("=" * 70)

    from app.services.gateway.hybrid_gateway import HybridGateway
    from app.services.hub.hub_router import HubRouter

    gateway = HybridGateway()
    hub = HubRouter()

    # Gateway 통계
    gateway_stats = gateway.get_stats()
    print("\n[Gateway 통계]")
    gateway_data = gateway_stats.get("gateway", {})
    print(f"   총 요청: {gateway_data.get('total_requests', 0)}")
    print(f"   규칙 기반: {gateway_data.get('rule_based', 0)} ({gateway_data.get('rule_based_ratio', 0.0):.1%})")
    print(f"   ML 보조: {gateway_data.get('ml_assisted', 0)} ({gateway_data.get('ml_assisted_ratio', 0.0):.1%})")
    print(f"   평균 지연: {gateway_data.get('avg_latency_ms', 0.0):.2f}ms")

    # Hub Router 통계
    router_stats = hub.get_router_stats()
    print("\n[Hub Router 통계]")
    print(f"   총 라우팅: {router_stats['total_routings']}")
    print(f"   성공: {router_stats['successful_routings']} ({router_stats['success_rate']:.1%})")
    print(f"   폴백: {router_stats['fallback_routings']} ({router_stats['fallback_rate']:.1%})")
    print(f"   거부: {router_stats['rejected_routings']}")

    # 브랜치 통계
    branch_stats = hub.get_branch_stats()
    print("\n[브랜치 통계]")
    for branch_name, stats in branch_stats.items():
        if stats['metrics']['total_requests'] > 0:
            print(f"   {branch_name}:")
            print(f"      - 요청 수: {stats['metrics']['total_requests']}")
            print(f"      - 성공률: {1 - stats['metrics']['error_rate']:.1%}")
            print(f"      - 평균 지연: {stats['metrics']['avg_latency_ms']:.2f}ms")

    # 헬스 리포트
    health_report = hub.get_health_report()
    print("\n[헬스 리포트]")
    print(f"   총 브랜치: {health_report['total_branches']}")
    print(f"   건강: {health_report['healthy_count']}")
    print(f"   불건강: {health_report['unhealthy_count']}")

    hub.shutdown()

    print("\n✅ 통계 조회 완료!")


def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 70)
    print("LangGraph Workflow 통합 테스트")
    print("=" * 70)

    try:
        # 테스트 실행
        test_spam_detection()
        test_normal_email()
        test_performance()
        test_workflow_stats()

        print("\n" + "=" * 70)
        print("✅ 모든 테스트 통과!")
        print("=" * 70)

        print("\n다음 단계:")
        print("  1. FastAPI 서버 실행: uvicorn app.main:app --reload")
        print("  2. API 테스트: POST http://localhost:8000/api/mcp/workflow")
        print("  3. DB 저장 테스트: save_to_db=true로 요청")

    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예기치 않은 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
