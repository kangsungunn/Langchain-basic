"""
Reference Spoke - 서비스 (Star 토폴로지 말단)

문제/모범답안/논점 비즈니스 로직.
단일 소스: 이 파일. reference/services.py 는 re-export.
"""

import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.v1.minso.models import Problem, ReferenceAnswer, Issue
from app.domain.v1.minso.hub.repositories import (
    ProblemRepository, ReferenceAnswerRepository, IssueRepository,
)
from app.domain.v1.minso.models.transfers import (
    ProblemCreate, ProblemUpdate, ProblemResponse,
    ReferenceAnswerCreate, ReferenceAnswerUpdate, ReferenceAnswerResponse,
    IssueCreate, IssueUpdate, IssueResponse,
)


class ProblemService:
    """문제 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProblemRepository(session)

    async def create_problem(self, data: ProblemCreate) -> ProblemResponse:
        """문제 생성"""
        problem = Problem(
            id=str(uuid.uuid4()),
            title=data.title,
            content=data.content,
            meta=data.meta
        )

        created = await self.repo.create(problem)
        # reference_answers 관계는 로드하지 않고 빈 리스트로 반환 (async에서 lazy load 방지)
        return ProblemResponse(
            id=created.id,
            title=created.title,
            content=created.content,
            meta=created.meta,
            created_at=created.created_at,
            updated_at=created.updated_at,
            reference_answers=[],
        )

    async def get_problem(self, problem_id: str) -> Optional[ProblemResponse]:
        """문제 조회"""
        problem = await self.repo.get_by_id(problem_id)
        if not problem:
            return None
        return ProblemResponse.from_orm(problem)

    async def get_all_problems(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """문제 목록 조회"""
        problems = await self.repo.get_all(skip=skip, limit=limit)
        total = await self.repo.count()

        return {
            "total": total,
            "items": [ProblemResponse.from_orm(p) for p in problems]
        }

    async def update_problem(self, problem_id: str, data: ProblemUpdate) -> Optional[ProblemResponse]:
        """문제 수정"""
        problem = await self.repo.get_by_id(problem_id)
        if not problem:
            return None

        if data.title is not None:
            problem.title = data.title
        if data.content is not None:
            problem.content = data.content
        if data.meta is not None:
            problem.meta = data.meta

        updated = await self.repo.update(problem)
        return ProblemResponse.from_orm(updated)

    async def delete_problem(self, problem_id: str) -> bool:
        """문제 삭제"""
        problem = await self.repo.get_by_id(problem_id)
        if not problem:
            return False

        await self.repo.delete(problem)
        return True


class ReferenceAnswerService:
    """모범답안 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ReferenceAnswerRepository(session)

    async def create_answer(self, data: ReferenceAnswerCreate) -> ReferenceAnswerResponse:
        """모범답안 생성"""
        answer = ReferenceAnswer(
            id=str(uuid.uuid4()),
            problem_id=data.problem_id,
            content=data.content,
            structure=data.structure
        )

        created = await self.repo.create(answer)
        return ReferenceAnswerResponse.from_orm(created)

    async def get_answer(self, answer_id: str) -> Optional[ReferenceAnswerResponse]:
        """모범답안 조회"""
        answer = await self.repo.get_by_id(answer_id)
        if not answer:
            return None
        return ReferenceAnswerResponse.from_orm(answer)

    async def get_answers_by_problem(self, problem_id: str) -> List[ReferenceAnswerResponse]:
        """문제의 모든 모범답안 조회"""
        answers = await self.repo.get_by_problem_id(problem_id)
        return [ReferenceAnswerResponse.from_orm(a) for a in answers]

    async def update_answer(self, answer_id: str, data: ReferenceAnswerUpdate) -> Optional[ReferenceAnswerResponse]:
        """모범답안 수정"""
        answer = await self.repo.get_by_id(answer_id)
        if not answer:
            return None

        if data.content is not None:
            answer.content = data.content
        if data.structure is not None:
            answer.structure = data.structure

        updated = await self.repo.update(answer)
        return ReferenceAnswerResponse.from_orm(updated)

    async def delete_answer(self, answer_id: str) -> bool:
        """모범답안 삭제"""
        answer = await self.repo.get_by_id(answer_id)
        if not answer:
            return False

        await self.repo.delete(answer)
        return True


class IssueService:
    """논점 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IssueRepository(session)

    async def create_issue(self, data: IssueCreate) -> IssueResponse:
        """논점 생성"""
        issue = Issue(
            id=str(uuid.uuid4()),
            reference_answer_id=data.reference_answer_id,
            issue_type=data.issue_type,
            title=data.title,
            description=data.description,
            order=data.order,
            keywords=data.keywords,
            related_cases=data.related_cases
        )

        created = await self.repo.create(issue)
        return IssueResponse.from_orm(created)

    async def create_issues_batch(self, issues_data: List[IssueCreate]) -> List[IssueResponse]:
        """여러 논점 생성 (배치)"""
        issues = [
            Issue(
                id=str(uuid.uuid4()),
                reference_answer_id=data.reference_answer_id,
                issue_type=data.issue_type,
                title=data.title,
                description=data.description,
                order=data.order,
                keywords=data.keywords,
                related_cases=data.related_cases
            )
            for data in issues_data
        ]

        created = await self.repo.create_many(issues)
        return [IssueResponse.from_orm(i) for i in created]

    async def get_issue(self, issue_id: str) -> Optional[IssueResponse]:
        """논점 조회"""
        issue = await self.repo.get_by_id(issue_id)
        if not issue:
            return None
        return IssueResponse.from_orm(issue)

    async def get_issues_by_answer(self, answer_id: str) -> List[IssueResponse]:
        """모범답안의 모든 논점 조회"""
        issues = await self.repo.get_by_reference_answer_id(answer_id)
        return [IssueResponse.from_orm(i) for i in issues]

    async def update_issue(self, issue_id: str, data: IssueUpdate) -> Optional[IssueResponse]:
        """논점 수정"""
        issue = await self.repo.get_by_id(issue_id)
        if not issue:
            return None

        if data.issue_type is not None:
            issue.issue_type = data.issue_type
        if data.title is not None:
            issue.title = data.title
        if data.description is not None:
            issue.description = data.description
        if data.order is not None:
            issue.order = data.order
        if data.keywords is not None:
            issue.keywords = data.keywords
        if data.related_cases is not None:
            issue.related_cases = data.related_cases

        updated = await self.repo.update(issue)
        return IssueResponse.from_orm(updated)

    async def delete_issue(self, issue_id: str) -> bool:
        """논점 삭제"""
        issue = await self.repo.get_by_id(issue_id)
        if not issue:
            return False

        await self.repo.delete(issue)
        return True

    async def extract_issues_from_answer(
        self,
        answer_id: str,
        auto_save: bool = True
    ) -> List[IssueResponse]:
        """
        모범답안으로부터 논점 추출

        TODO: 현재는 더미 구현. Phase 3에서 EXAONE 연동 예정.
        """
        dummy_issues = [
            IssueCreate(
                reference_answer_id=answer_id,
                issue_type="main",
                title="소의 이익",
                description="소송의 이익이 있는지 여부",
                order=1,
                keywords=["소의 이익", "권리보호의 이익"],
                related_cases=["대법원 2020다12345"]
            ),
            IssueCreate(
                reference_answer_id=answer_id,
                issue_type="sub",
                title="당사자적격",
                description="원고 및 피고의 당사자적격",
                order=2,
                keywords=["당사자적격", "원고적격"],
                related_cases=["대법원 2019다54321"]
            )
        ]

        if auto_save:
            await self.repo.delete_by_reference_answer_id(answer_id)
            return await self.create_issues_batch(dummy_issues)
        else:
            return [IssueResponse(**issue.dict()) for issue in dummy_issues]
