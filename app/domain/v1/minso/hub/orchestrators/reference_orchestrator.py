"""
Hub - Reference 오케스트레이터 (스텁)

reference 도메인 정책 기반 요청이 생기면 여기서 처리.
현재는 DecisionMaker에서 reference 액션이 모두 규칙 기반("*")으로 분류되어
서비스로 직접 라우팅되므로, MinsoHub 맵에는 미등록 상태.
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.v1.minso.shared import DomainValidationError
from app.core.utils.logger import get_logger

logger = get_logger()


class ReferenceOrchestrator:
    """
    Reference 전용 오케스트레이터.

    정책 기반 reference 요청이 추가되면 액션 구현 후 MinsoHub 맵에 등록.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def process(
        self,
        domain: str,
        action: str,
        request: Any
    ) -> Any:
        if domain != "reference":
            raise DomainValidationError(
                f"ReferenceOrchestrator는 reference 도메인만 처리합니다: {domain}"
            )
        raise DomainValidationError(
            f"Reference 정책 액션 미구현: {action}. 현재 reference는 규칙 기반으로만 처리됩니다."
        )
