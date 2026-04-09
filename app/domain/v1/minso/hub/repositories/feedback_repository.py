"""
Hub - Feedback 리포지토리 (단일 소스)

데이터 접근 계층. 모델은 minso.models 기준.
"""

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.v1.minso.models import Feedback, FeedbackItem, FeedbackCorrection


class FeedbackRepository:
    """피드백 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, feedback: Feedback) -> Feedback:
        """피드백 생성"""
        self.session.add(feedback)
        await self.session.flush()
        await self.session.refresh(feedback)
        return feedback

    async def get_by_id(self, feedback_id: str) -> Optional[Feedback]:
        """ID로 피드백 조회"""
        result = await self.session.execute(
            select(Feedback)
            .options(selectinload(Feedback.items), selectinload(Feedback.corrections))
            .where(Feedback.id == feedback_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_answer(
        self,
        user_answer_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Feedback]:
        """사용자 답안으로 피드백 조회"""
        result = await self.session.execute(
            select(Feedback)
            .options(selectinload(Feedback.items))
            .where(Feedback.user_answer_id == user_answer_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_reasoning_task(self, reasoning_task_id: str) -> Optional[Feedback]:
        """추론 작업으로 피드백 조회"""
        result = await self.session.execute(
            select(Feedback)
            .options(selectinload(Feedback.items))
            .where(Feedback.reasoning_task_id == reasoning_task_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Feedback]:
        """모든 피드백 조회"""
        result = await self.session.execute(
            select(Feedback)
            .options(selectinload(Feedback.items))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """피드백 총 개수"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(Feedback)
        )
        return result.scalar()

    async def count_by_user_answer(self, user_answer_id: str) -> int:
        """사용자 답안별 피드백 개수"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(Feedback).where(
                Feedback.user_answer_id == user_answer_id
            )
        )
        return result.scalar()

    async def update(self, feedback: Feedback) -> Feedback:
        """피드백 수정"""
        await self.session.flush()
        await self.session.refresh(feedback)
        return feedback

    async def delete(self, feedback: Feedback):
        """피드백 삭제"""
        await self.session.delete(feedback)
        await self.session.flush()


class FeedbackItemRepository:
    """피드백 항목 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, item: FeedbackItem) -> FeedbackItem:
        """피드백 항목 생성"""
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def create_many(self, items: List[FeedbackItem]) -> List[FeedbackItem]:
        """피드백 항목 일괄 생성"""
        self.session.add_all(items)
        await self.session.flush()
        for item in items:
            await self.session.refresh(item)
        return items

    async def get_by_id(self, item_id: str) -> Optional[FeedbackItem]:
        """ID로 피드백 항목 조회"""
        result = await self.session.execute(
            select(FeedbackItem).where(FeedbackItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_by_feedback_id(self, feedback_id: str) -> List[FeedbackItem]:
        """피드백 ID로 항목 조회"""
        result = await self.session.execute(
            select(FeedbackItem).where(FeedbackItem.feedback_id == feedback_id)
        )
        return result.scalars().all()

    async def get_by_type(
        self,
        feedback_id: str,
        item_type: str
    ) -> List[FeedbackItem]:
        """타입으로 피드백 항목 조회"""
        result = await self.session.execute(
            select(FeedbackItem).where(
                and_(
                    FeedbackItem.feedback_id == feedback_id,
                    FeedbackItem.item_type == item_type
                )
            )
        )
        return result.scalars().all()

    async def delete(self, item: FeedbackItem):
        """피드백 항목 삭제"""
        await self.session.delete(item)
        await self.session.flush()

    async def delete_by_feedback_id(self, feedback_id: str):
        """피드백의 모든 항목 삭제"""
        from sqlalchemy import delete as sql_delete
        await self.session.execute(
            sql_delete(FeedbackItem).where(FeedbackItem.feedback_id == feedback_id)
        )
        await self.session.flush()


class FeedbackCorrectionRepository:
    """피드백 정정(학습용) 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, correction: FeedbackCorrection) -> FeedbackCorrection:
        self.session.add(correction)
        await self.session.flush()
        await self.session.refresh(correction)
        return correction

    async def get_by_id(self, correction_id: str) -> Optional[FeedbackCorrection]:
        result = await self.session.execute(
            select(FeedbackCorrection).where(FeedbackCorrection.id == correction_id)
        )
        return result.scalar_one_or_none()

    async def get_by_feedback_id(self, feedback_id: str) -> List[FeedbackCorrection]:
        result = await self.session.execute(
            select(FeedbackCorrection)
            .where(FeedbackCorrection.feedback_id == feedback_id)
            .order_by(FeedbackCorrection.created_at.desc())
        )
        return list(result.scalars().all())
