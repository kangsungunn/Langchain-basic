"""
Hub - Feedback 오케스트레이터

정책 기반 피드백 요청 처리. generate, generate_report 등.
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.v1.minso.shared import DomainValidationError
from app.core.utils.logger import get_logger

logger = get_logger()


class FeedbackOrchestrator:
    """
    Feedback 전용 오케스트레이터.

    정책 기반 피드백 요청(생성·리포트 등)을 FeedbackGenerator로 처리합니다.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def process(
        self,
        domain: str,
        action: str,
        request: Any
    ) -> Any:
        """Feedback 도메인 요청만 처리."""
        logger.info(f"[FEEDBACK] Feedback Orchestrator 처리: {domain}.{action}")

        if domain != "feedback":
            raise DomainValidationError(
                f"FeedbackOrchestrator는 feedback 도메인만 처리합니다: {domain}"
            )

        try:
            return await self._handle(action, request)
        except Exception as e:
            logger.error(f"[FAIL] Feedback Orchestrator 처리 실패: {action}, 오류: {e}")
            raise

    async def _handle(self, action: str, request: Any) -> Any:
        """액션별 처리 (spokes FeedbackGenerator 사용)."""
        from app.domain.v1.minso.spokes.services.feedback_service import FeedbackGenerator

        generator = FeedbackGenerator(self.session)

        if action == "generate" or action == "generate_from_reasoning":
            reasoning_task_id = getattr(request, "reasoning_task_id", None)
            if not reasoning_task_id:
                raise DomainValidationError("generate_from_reasoning에는 reasoning_task_id가 필요합니다.")
            return await generator.generate_from_reasoning(
                user_answer_id=request.user_answer_id,
                reasoning_task_id=reasoning_task_id,
                feedback_type=getattr(request, "feedback_type", "comprehensive"),
                include_suggestions=getattr(request, "include_suggestions", True),
            )
        elif action == "generate_report":
            return await generator.generate_report(
                user_answer_id=request.user_answer_id,
                include_comprehensive=getattr(request, "include_comprehensive", True),
            )
        else:
            raise DomainValidationError(f"알 수 없는 Feedback 액션: {action}")
