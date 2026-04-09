"""
Hub - Submission 리포지토리 (단일 소스)

데이터 접근 계층. 모델은 minso.models 기준.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.v1.minso.models import UserAnswer, AnswerStructure


class UserAnswerRepository:
    """사용자 답안 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, answer: UserAnswer) -> UserAnswer:
        """사용자 답안 생성"""
        self.session.add(answer)
        await self.session.flush()
        await self.session.refresh(answer)
        return answer

    async def get_by_id(self, answer_id: str) -> Optional[UserAnswer]:
        """ID로 사용자 답안 조회"""
        result = await self.session.execute(
            select(UserAnswer)
            .options(selectinload(UserAnswer.structure))
            .where(UserAnswer.id == answer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_problem_id(self, problem_id: str, skip: int = 0, limit: int = 100) -> List[UserAnswer]:
        """문제 ID로 사용자 답안 조회"""
        result = await self.session.execute(
            select(UserAnswer)
            .options(selectinload(UserAnswer.structure))
            .where(UserAnswer.problem_id == problem_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[UserAnswer]:
        """모든 사용자 답안 조회"""
        result = await self.session.execute(
            select(UserAnswer)
            .options(selectinload(UserAnswer.structure))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """사용자 답안 총 개수"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(UserAnswer)
        )
        return result.scalar()

    async def count_by_problem(self, problem_id: str) -> int:
        """문제별 사용자 답안 개수"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(UserAnswer).where(UserAnswer.problem_id == problem_id)
        )
        return result.scalar()

    async def update(self, answer: UserAnswer) -> UserAnswer:
        """사용자 답안 수정"""
        await self.session.flush()
        await self.session.refresh(answer)
        return answer

    async def delete(self, answer: UserAnswer):
        """사용자 답안 삭제"""
        await self.session.delete(answer)
        await self.session.flush()


class AnswerStructureRepository:
    """답안 구조 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, structure: AnswerStructure) -> AnswerStructure:
        """답안 구조 생성"""
        self.session.add(structure)
        await self.session.flush()
        await self.session.refresh(structure)
        return structure

    async def get_by_id(self, structure_id: str) -> Optional[AnswerStructure]:
        """ID로 답안 구조 조회"""
        result = await self.session.execute(
            select(AnswerStructure).where(AnswerStructure.id == structure_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_answer_id(self, user_answer_id: str) -> Optional[AnswerStructure]:
        """사용자 답안 ID로 구조 조회"""
        result = await self.session.execute(
            select(AnswerStructure).where(AnswerStructure.user_answer_id == user_answer_id)
        )
        return result.scalar_one_or_none()

    async def update(self, structure: AnswerStructure) -> AnswerStructure:
        """답안 구조 수정"""
        await self.session.flush()
        await self.session.refresh(structure)
        return structure

    async def delete(self, structure: AnswerStructure):
        """답안 구조 삭제"""
        await self.session.delete(structure)
        await self.session.flush()

    async def delete_by_user_answer_id(self, user_answer_id: str):
        """사용자 답안의 구조 삭제"""
        from sqlalchemy import delete as sql_delete
        await self.session.execute(
            sql_delete(AnswerStructure).where(AnswerStructure.user_answer_id == user_answer_id)
        )
        await self.session.flush()
