"""
오케스트레이터 통합 테스트

정책/규칙 기반 라우팅이 올바르게 동작하는지 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.v1.minso.hub.orchestrators import MinsoHub
from app.domain.v1.minso.hub.decision_maker import DecisionMaker
from training.schemas import TrainingDataCreate
from app.domain.v1.minso.models.transfers import ComprehensiveAnalysisRequest


@pytest.mark.asyncio
async def test_rule_based_routing():
    """규칙 기반 라우팅 테스트"""
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock service
    mock_service = AsyncMock()
    mock_service.create = AsyncMock(return_value=MagicMock(id="test-id"))

    # MinsoHub 생성
    hub = MinsoHub(mock_session)

    # TrainingDataCreate 요청
    request = TrainingDataCreate(
        problem_text="테스트 문제",
        reference_answer_text="테스트 모범답안",
        user_answer_text="테스트 사용자 답안"
    )

    # 서비스 매핑을 Mock으로 교체
    with patch.object(hub, '_get_service_map') as mock_map:
        from training.services import TrainingDataService
        mock_map.return_value = {
            'training': TrainingDataService
        }
        # TrainingDataService.create를 Mock으로 교체
        with patch('training.services.TrainingDataService.create', return_value=mock_service.create()):
            # 요청 처리
            result = await hub.process(
                domain="training",
                action="create_training_data",
                request=request
            )

            # 규칙 기반으로 처리되었는지 확인
            assert result is not None


@pytest.mark.asyncio
async def test_policy_based_routing():
    """정책 기반 라우팅 테스트"""
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # MinsoHub 생성
    hub = MinsoHub(mock_session)

    # ComprehensiveAnalysisRequest 요청
    request = ComprehensiveAnalysisRequest(
        user_answer_id="test-answer-id",
        reference_answer_id="test-ref-id",
        problem_id="test-problem-id"
    )

    # DecisionMaker를 Mock하여 정책 기반으로 판단하도록 설정
    mock_decision_maker = AsyncMock()
    mock_decision_maker.decide = AsyncMock(return_value="policy")

    # ReasoningHub.process를 Mock으로 교체
    mock_reasoning_hub = AsyncMock()
    mock_reasoning_hub.process = AsyncMock(return_value={"result": "success"})

    with patch.object(hub, 'decision_maker', mock_decision_maker):
        with patch.object(hub, 'reasoning_hub', mock_reasoning_hub):
            # 요청 처리
            result = await hub.process(
                domain="reasoning",
                action="comprehensive_analysis",
                request=request
            )

            # 정책 기반으로 처리되었는지 확인
            assert result is not None
            mock_reasoning_hub.process.assert_called_once()


@pytest.mark.asyncio
async def test_decision_maker_rule_based():
    """DecisionMaker 규칙 기반 판단 테스트"""
    decision_maker = DecisionMaker()

    # 규칙 기반 액션 테스트
    strategy = await decision_maker.decide(
        domain="training",
        action="create_training_data",
        request=TrainingDataCreate(
            problem_text="테스트",
            reference_answer_text="테스트"
        )
    )

    assert strategy == "rule"


@pytest.mark.asyncio
async def test_decision_maker_policy_based():
    """DecisionMaker 정책 기반 판단 테스트"""
    decision_maker = DecisionMaker()

    # 정책 기반 액션 테스트
    strategy = await decision_maker.decide(
        domain="reasoning",
        action="comprehensive_analysis",
        request=ComprehensiveAnalysisRequest(
            user_answer_id="test-id"
        )
    )

    assert strategy == "policy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
