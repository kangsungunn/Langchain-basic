"""
Hub - Reasoning 리포지토리 (단일 소스)

데이터 접근 계층. 모델은 minso.models 기준.
"""

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.v1.minso.models import ReasoningTask, ReasoningResult
from app.domain.v1.minso.shared import EntityNotFoundError
from app.domain.v1.minso.shared.value_objects import ENTITY_REASONING_TASK


class ReasoningTaskRepository:
    """추론 작업 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: ReasoningTask) -> ReasoningTask:
        """추론 작업 생성"""
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: str) -> Optional[ReasoningTask]:
        """ID로 추론 작업 조회"""
        result = await self.session.execute(
            select(ReasoningTask)
            .options(selectinload(ReasoningTask.results))
            .where(ReasoningTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_answer(
        self,
        user_answer_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ReasoningTask]:
        """사용자 답안으로 추론 작업 조회"""
        result = await self.session.execute(
            select(ReasoningTask)
            .options(selectinload(ReasoningTask.results))
            .where(ReasoningTask.user_answer_id == user_answer_id)
            .order_by(ReasoningTask.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_latest_by_user_answer(self, user_answer_id: str) -> Optional[ReasoningTask]:
        """사용자 답안의 최신 추론 작업 조회"""
        result = await self.session.execute(
            select(ReasoningTask)
            .options(selectinload(ReasoningTask.results))
            .where(ReasoningTask.user_answer_id == user_answer_id)
            .order_by(ReasoningTask.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ReasoningTask]:
        """모든 추론 작업 조회"""
        result = await self.session.execute(
            select(ReasoningTask)
            .options(selectinload(ReasoningTask.results))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """추론 작업 총 개수"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(ReasoningTask)
        )
        return result.scalar()

    async def count_by_user_answer(self, user_answer_id: str) -> int:
        """사용자 답안별 추론 작업 개수"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(ReasoningTask).where(
                ReasoningTask.user_answer_id == user_answer_id
            )
        )
        return result.scalar()

    async def update(self, task: ReasoningTask) -> ReasoningTask:
        """추론 작업 수정"""
        task_id = task.id
        self.session.add(task)
        await self.session.flush()
        try:
            await self.session.refresh(task)
        except Exception:
            task = await self.get_by_id(task_id)
            if not task:
                raise EntityNotFoundError(ENTITY_REASONING_TASK, task_id)
        return task

    async def delete(self, task: ReasoningTask):
        """추론 작업 삭제"""
        await self.session.delete(task)
        await self.session.flush()


class ReasoningResultRepository:
    """추론 결과 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, result: ReasoningResult) -> ReasoningResult:
        """추론 결과 생성"""
        self.session.add(result)
        await self.session.flush()
        await self.session.refresh(result)
        return result

    async def create_many(self, results: List[ReasoningResult]) -> List[ReasoningResult]:
        """추론 결과 일괄 생성"""
        self.session.add_all(results)
        await self.session.flush()
        for result in results:
            await self.session.refresh(result)
        return results

    async def get_by_id(self, result_id: str) -> Optional[ReasoningResult]:
        """ID로 추론 결과 조회"""
        result = await self.session.execute(
            select(ReasoningResult).where(ReasoningResult.id == result_id)
        )
        return result.scalar_one_or_none()

    async def get_by_task_id(self, task_id: str) -> List[ReasoningResult]:
        """작업 ID로 추론 결과 조회"""
        result = await self.session.execute(
            select(ReasoningResult).where(ReasoningResult.task_id == task_id)
        )
        return result.scalars().all()

    async def get_by_task_and_type(
        self,
        task_id: str,
        result_type: str
    ) -> Optional[ReasoningResult]:
        """작업 ID와 타입으로 추론 결과 조회"""
        result = await self.session.execute(
            select(ReasoningResult).where(
                and_(
                    ReasoningResult.task_id == task_id,
                    ReasoningResult.result_type == result_type
                )
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, result: ReasoningResult):
        """추론 결과 삭제"""
        await self.session.delete(result)
        await self.session.flush()

    async def delete_by_task_id(self, task_id: str):
        """작업의 모든 결과 삭제"""
        from sqlalchemy import delete as sql_delete
        await self.session.execute(
            sql_delete(ReasoningResult).where(ReasoningResult.task_id == task_id)
        )
        await self.session.flush()
