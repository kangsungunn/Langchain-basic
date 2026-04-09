"""
Hub - Reference 리포지토리 (단일 소스)

데이터 접근 계층. 모델은 minso.models 기준.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.v1.minso.models import Problem, ReferenceAnswer, Issue


class ProblemRepository:
    """문제 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, problem: Problem) -> Problem:
        """문제 생성"""
        self.session.add(problem)
        await self.session.flush()
        await self.session.refresh(problem)
        return problem

    async def get_by_id(self, problem_id: str) -> Optional[Problem]:
        """ID로 문제 조회"""
        result = await self.session.execute(
            select(Problem)
            .options(
                selectinload(Problem.reference_answers).selectinload(ReferenceAnswer.issues)
            )
            .where(Problem.id == problem_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Problem]:
        """모든 문제 조회"""
        result = await self.session.execute(
            select(Problem)
            .options(
                selectinload(Problem.reference_answers).selectinload(ReferenceAnswer.issues)
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        """문제 총 개수"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).select_from(Problem)
        )
        return result.scalar()

    async def update(self, problem: Problem) -> Problem:
        """문제 수정"""
        await self.session.flush()
        await self.session.refresh(problem)
        return problem

    async def delete(self, problem: Problem):
        """문제 삭제"""
        await self.session.delete(problem)
        await self.session.flush()


class ReferenceAnswerRepository:
    """모범답안 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, answer: ReferenceAnswer) -> ReferenceAnswer:
        """모범답안 생성"""
        self.session.add(answer)
        await self.session.flush()
        await self.session.refresh(answer)
        return answer

    async def get_by_id(self, answer_id: str) -> Optional[ReferenceAnswer]:
        """ID로 모범답안 조회"""
        result = await self.session.execute(
            select(ReferenceAnswer)
            .options(selectinload(ReferenceAnswer.issues))
            .where(ReferenceAnswer.id == answer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_problem_id(self, problem_id: str) -> List[ReferenceAnswer]:
        """문제 ID로 모범답안 조회"""
        result = await self.session.execute(
            select(ReferenceAnswer)
            .options(selectinload(ReferenceAnswer.issues))
            .where(ReferenceAnswer.problem_id == problem_id)
        )
        return result.scalars().all()

    async def update(self, answer: ReferenceAnswer) -> ReferenceAnswer:
        """모범답안 수정"""
        await self.session.flush()
        await self.session.refresh(answer)
        return answer

    async def delete(self, answer: ReferenceAnswer):
        """모범답안 삭제"""
        await self.session.delete(answer)
        await self.session.flush()


class IssueRepository:
    """논점 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, issue: Issue) -> Issue:
        """논점 생성"""
        self.session.add(issue)
        await self.session.flush()
        await self.session.refresh(issue)
        return issue

    async def create_many(self, issues: List[Issue]) -> List[Issue]:
        """여러 논점 생성"""
        self.session.add_all(issues)
        await self.session.flush()
        for issue in issues:
            await self.session.refresh(issue)
        return issues

    async def get_by_id(self, issue_id: str) -> Optional[Issue]:
        """ID로 논점 조회"""
        result = await self.session.execute(
            select(Issue).where(Issue.id == issue_id)
        )
        return result.scalar_one_or_none()

    async def get_by_reference_answer_id(self, answer_id: str) -> List[Issue]:
        """모범답안 ID로 논점 조회"""
        result = await self.session.execute(
            select(Issue)
            .where(Issue.reference_answer_id == answer_id)
            .order_by(Issue.order)
        )
        return result.scalars().all()

    async def update(self, issue: Issue) -> Issue:
        """논점 수정"""
        await self.session.flush()
        await self.session.refresh(issue)
        return issue

    async def delete(self, issue: Issue):
        """논점 삭제"""
        await self.session.delete(issue)
        await self.session.flush()

    async def delete_by_reference_answer_id(self, answer_id: str):
        """모범답안의 모든 논점 삭제"""
        from sqlalchemy import delete as sql_delete
        await self.session.execute(
            sql_delete(Issue).where(Issue.reference_answer_id == answer_id)
        )
        await self.session.flush()
