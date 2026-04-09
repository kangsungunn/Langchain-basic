#!/usr/bin/env python3
"""
DB 테스트 스크립트

주체: Hub Router (Star)
역할: DB CRUD 작업 테스트

실행 방법:
    python scripts/test_db.py
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.database.connection import SessionLocal
from app.database.repositories import (
    InputTextRepository,
    RoutingLogRepository,
    BranchResultRepository,
    PolicyDecisionRepository,
    StarRepository
)
from app.services.gateway.rule_engine import GatewayResult
from app.services.hub.hub_router import RoutingDecision
from app.services.hub.branch_registry import BranchConfig
from app.services.branches.base_branch import BranchResult


def test_basic_crud():
    """기본 CRUD 테스트"""
    print("=" * 70)
    print("DB CRUD 테스트")
    print("=" * 70)

    db = SessionLocal()

    try:
        # 1. InputText 생성
        print("\n[1/4] InputText 생성...")
        input_text = InputTextRepository.create(
            db,
            text="테스트 이메일 내용입니다. 긴급송금 요청!",
            user_id="test_user_001",
            source="test"
        )
        print(f"✅ 생성됨: ID={input_text.id}, hash={input_text.text_hash[:16]}...")

        # 2. RoutingLog 생성
        print("\n[2/4] RoutingLog 생성...")

        # Gateway 결과 더미
        gateway_result = GatewayResult(
            route="spam_agent",
            confidence=0.9,
            reason="금칙어 2개 감지",
            method="rule_based",
            matched_rules=["spam_keywords_multi"],
            latency_ms=2.5
        )

        # RoutingDecision 더미
        branch_config = BranchConfig(
            name="spam_agent",
            adapter_path="./checkpoints/exaone-spam-filter-v2/checkpoint-3000",
            base_model_path="app/models/original/exaone-2.4b"
        )

        routing_decision = RoutingDecision(
            branch_name="spam_agent",
            branch_config=branch_config,
            reason="게이트웨이 결과: 금칙어 감지",
            gateway_result=gateway_result,
            ontology_version="1.0.0",
            fallback_used=False
        )

        routing_log = RoutingLogRepository.create(
            db, input_text.id, gateway_result, routing_decision
        )
        print(f"✅ 생성됨: ID={routing_log.id}, branch={routing_log.selected_branch}")

        # 3. BranchResult 생성
        print("\n[3/4] BranchResult 생성...")

        branch_result = BranchResult(
            branch_name="spam_agent",
            task_type="spam",
            label="spam",
            confidence=0.85,
            recommended_action="block",
            reasoning="URL_MISMATCH 및 URGENT_MONEY 패턴 감지",
            evidence=["URL_MISMATCH", "URGENT_MONEY"],
            latency_ms=150.5
        )

        branch_result_record = BranchResultRepository.create(
            db, input_text.id, branch_result
        )
        print(f"✅ 생성됨: ID={branch_result_record.id}, label={branch_result_record.label}")

        # 4. PolicyDecision 생성
        print("\n[4/4] PolicyDecision 생성...")

        policy_decision = PolicyDecisionRepository.create(
            db,
            input_text.id,
            branch_result,
            final_action="quarantine",
            policy_reason="증거 2개, Star 판단: block → quarantine"
        )
        print(f"✅ 생성됨: ID={policy_decision.id}, action={policy_decision.final_action}")

        # 조회 테스트
        print("\n" + "=" * 70)
        print("조회 테스트")
        print("=" * 70)

        # InputText 조회
        fetched_input = InputTextRepository.get_by_id(db, input_text.id)
        print(f"\n✅ InputText 조회: {fetched_input.text[:50]}...")

        # 통계 조회
        stats = PolicyDecisionRepository.get_statistics(db)
        print(f"\n✅ PolicyDecision 통계:")
        print(f"   총 결정: {stats['total']}")
        print(f"   액션별: {stats['by_action']}")
        print(f"   브랜치별: {stats['by_branch']}")

        print("\n" + "=" * 70)
        print("✅ 모든 테스트 통과!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_star_repository():
    """StarRepository 통합 테스트"""
    print("\n" + "=" * 70)
    print("StarRepository 통합 테스트")
    print("=" * 70)

    db = SessionLocal()

    try:
        # Gateway 결과
        gateway_result = GatewayResult(
            route="spam_agent",
            confidence=0.95,
            reason="금칙어 3개 감지",
            method="rule_based",
            matched_rules=["spam_keywords_multi"],
            latency_ms=3.0
        )

        # RoutingDecision
        branch_config = BranchConfig(
            name="spam_agent",
            adapter_path="./checkpoints/exaone-spam-filter-v2/checkpoint-3000",
            base_model_path="app/models/original/exaone-2.4b"
        )

        routing_decision = RoutingDecision(
            branch_name="spam_agent",
            branch_config=branch_config,
            reason="게이트웨이 결과: 금칙어 감지",
            gateway_result=gateway_result,
            ontology_version="1.0.0",
            fallback_used=False
        )

        # BranchResult
        branch_result = BranchResult(
            branch_name="spam_agent",
            task_type="spam",
            label="spam",
            confidence=0.90,
            recommended_action="block",
            reasoning="URL_MISMATCH, URGENT_MONEY, SUSPICIOUS_SENDER 패턴 감지",
            evidence=["URL_MISMATCH", "URGENT_MONEY", "SUSPICIOUS_SENDER"],
            latency_ms=160.0
        )

        # StarRepository로 전체 워크플로우 한 번에 저장
        repo = StarRepository(db)

        result = repo.save_complete_workflow(
            text="긴급송금 필요합니다! 계좌번호 알려주세요. 링크 클릭: http://suspicious.com",
            gateway_result=gateway_result,
            routing_decision=routing_decision,
            branch_result=branch_result,
            final_action="block",
            policy_reason="증거 3개 >= 3 (자동 차단 기준)",
            user_id="test_user_002",
            source="test",
            applied_policy={"auto_block_threshold": 3}
        )

        print(f"\n✅ 전체 워크플로우 저장 완료!")
        print(f"   input_text_id: {result['input_text_id']}")
        print(f"   routing_log_id: {result['routing_log_id']}")
        print(f"   branch_result_id: {result['branch_result_id']}")
        print(f"   policy_decision_id: {result['policy_decision_id']}")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_basic_crud()
    test_star_repository()
