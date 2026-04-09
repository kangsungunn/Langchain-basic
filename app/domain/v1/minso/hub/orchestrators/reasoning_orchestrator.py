"""
Hub - Reasoning 오케스트레이터 (단일 소스)

정책 기반 요청 처리. 서비스는 spokes 기준으로만 참조.
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.v1.minso.spokes.services.reasoning_service import ReasoningEngine
from app.domain.v1.minso.shared import DomainValidationError
from app.core.utils.logger import get_logger

logger = get_logger()


class ReasoningHub:
    """
    Reasoning Hub (Star 토폴로지 중앙 허브)

    정책 기반 요청을 받아 Reasoning Engine으로 처리합니다.
    서비스는 spokes에서만 가져옵니다.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.engine = ReasoningEngine(session)

    async def process(
        self,
        domain: str,
        action: str,
        request: Any
    ) -> Any:
        """요청 처리."""
        logger.info(f"[REASONING] Reasoning Hub 처리 시작: {domain}.{action}")

        try:
            if domain != "reasoning":
                raise DomainValidationError(f"Reasoning Hub는 reasoning 도메인만 처리합니다: {domain}")
            return await self._handle_reasoning(action, request)
        except Exception as e:
            logger.error(f"[FAIL] Reasoning Hub 처리 실패: {domain}.{action}, 오류: {e}")
            raise

    async def _handle_reasoning(self, action: str, request: Any) -> Any:
        """Reasoning 도메인 요청 처리"""
        if action == "analyze_issues":
            return await self.engine.analyze_issues(
                user_answer_id=request.user_answer_id,
                reference_answer_id=request.reference_answer_id,
                problem_id=request.problem_id,
                save_result=getattr(request, 'save_result', True)
            )
        elif action == "analyze_logic":
            return await self.engine.evaluate_logic(
                user_answer_id=request.user_answer_id,
                reference_answer_id=request.reference_answer_id,
                problem_id=request.problem_id,
                save_result=getattr(request, 'save_result', True)
            )
        elif action == "analyze_expression":
            return await self.engine.review_expression(
                user_answer_id=request.user_answer_id,
                save_result=getattr(request, 'save_result', True)
            )
        elif action == "comprehensive_analysis":
            return await self.engine.comprehensive_analysis(
                user_answer_id=request.user_answer_id,
                reference_answer_id=getattr(request, 'reference_answer_id', None),
                problem_id=getattr(request, 'problem_id', None),
                save_result=getattr(request, 'save_result', True),
                extracted_issues=getattr(request, 'extracted_issues', None),
            )
        else:
            raise DomainValidationError(f"알 수 없는 Reasoning 액션: {action}")
