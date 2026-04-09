"""
Reference Domain API Router

문제, 모범답안, 논점 관리 API
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domain.v1.minso.spokes.services.reference_service import (
    ProblemService,
    ReferenceAnswerService,
    IssueService,
)
from app.domain.v1.minso.models.transfers import (
    ProblemCreate, ProblemUpdate, ProblemResponse, ProblemListResponse,
    ReferenceAnswerCreate, ReferenceAnswerUpdate, ReferenceAnswerResponse,
    IssueCreate, IssueUpdate, IssueResponse,
    IssueExtractionRequest, IssueExtractionResponse,
)


router = APIRouter(prefix="/reference", tags=["Reference"])


# ========== Problem Endpoints ==========

@router.post("/problems", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def create_problem(
    data: ProblemCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    문제 생성

    민사소송법 서술형 문제를 생성합니다.
    """
    service = ProblemService(session)
    return await service.create_problem(data)


@router.get("/problems", response_model=ProblemListResponse)
async def get_problems(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """
    문제 목록 조회

    모든 문제를 페이지네이션하여 조회합니다.
    """
    service = ProblemService(session)
    return await service.get_all_problems(skip=skip, limit=limit)


@router.get("/problems/{problem_id}", response_model=ProblemResponse)
async def get_problem(
    problem_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    문제 조회

    특정 문제를 ID로 조회합니다.
    """
    service = ProblemService(session)
    problem = await service.get_problem(problem_id)

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문제를 찾을 수 없습니다: {problem_id}"
        )

    return problem


@router.put("/problems/{problem_id}", response_model=ProblemResponse)
async def update_problem(
    problem_id: str,
    data: ProblemUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    문제 수정

    문제 내용을 수정합니다.
    """
    service = ProblemService(session)
    problem = await service.update_problem(problem_id, data)

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문제를 찾을 수 없습니다: {problem_id}"
        )

    return problem


@router.delete("/problems/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_problem(
    problem_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    문제 삭제

    문제 및 연관된 모범답안, 논점을 삭제합니다.
    """
    service = ProblemService(session)
    success = await service.delete_problem(problem_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문제를 찾을 수 없습니다: {problem_id}"
        )


# ========== ReferenceAnswer Endpoints ==========

@router.post("/answers", response_model=ReferenceAnswerResponse, status_code=status.HTTP_201_CREATED)
async def create_answer(
    data: ReferenceAnswerCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    모범답안 생성

    문제에 대한 모범답안을 생성합니다.
    Phase 2: 생성 후 해당 1건 자동 임베딩 (실패해도 201 반환).
    """
    service = ReferenceAnswerService(session)
    created = await service.create_answer(data)
    try:
        from app.domain.v1.minso.hub.orchestrators.minso_hub import MinsoHub
        hub = MinsoHub(session)
        await hub.embed_one("reference", created.id)
    except Exception:
        pass
    return created


@router.get("/answers/{answer_id}", response_model=ReferenceAnswerResponse)
async def get_answer(
    answer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    모범답안 조회

    특정 모범답안을 ID로 조회합니다.
    """
    service = ReferenceAnswerService(session)
    answer = await service.get_answer(answer_id)

    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"모범답안을 찾을 수 없습니다: {answer_id}"
        )

    return answer


@router.get("/problems/{problem_id}/answers", response_model=List[ReferenceAnswerResponse])
async def get_answers_by_problem(
    problem_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    문제의 모범답안 조회

    특정 문제에 대한 모든 모범답안을 조회합니다.
    """
    service = ReferenceAnswerService(session)
    return await service.get_answers_by_problem(problem_id)


@router.put("/answers/{answer_id}", response_model=ReferenceAnswerResponse)
async def update_answer(
    answer_id: str,
    data: ReferenceAnswerUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    모범답안 수정

    모범답안 내용을 수정합니다.
    """
    service = ReferenceAnswerService(session)
    answer = await service.update_answer(answer_id, data)

    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"모범답안을 찾을 수 없습니다: {answer_id}"
        )

    return answer


@router.delete("/answers/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_answer(
    answer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    모범답안 삭제

    모범답안 및 연관된 논점을 삭제합니다.
    """
    service = ReferenceAnswerService(session)
    success = await service.delete_answer(answer_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"모범답안을 찾을 수 없습니다: {answer_id}"
        )


# ========== Issue Endpoints ==========

@router.post("/issues", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    data: IssueCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    논점 생성

    모범답안에 논점을 추가합니다.
    """
    service = IssueService(session)
    return await service.create_issue(data)


@router.get("/issues/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    논점 조회

    특정 논점을 ID로 조회합니다.
    """
    service = IssueService(session)
    issue = await service.get_issue(issue_id)

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"논점을 찾을 수 없습니다: {issue_id}"
        )

    return issue


@router.get("/answers/{answer_id}/issues", response_model=List[IssueResponse])
async def get_issues_by_answer(
    answer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    모범답안의 논점 조회

    특정 모범답안의 모든 논점을 조회합니다.
    """
    service = IssueService(session)
    return await service.get_issues_by_answer(answer_id)


@router.put("/issues/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: str,
    data: IssueUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    논점 수정

    논점 내용을 수정합니다.
    """
    service = IssueService(session)
    issue = await service.update_issue(issue_id, data)

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"논점을 찾을 수 없습니다: {issue_id}"
        )

    return issue


@router.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(
    issue_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    논점 삭제

    논점을 삭제합니다.
    """
    service = IssueService(session)
    success = await service.delete_issue(issue_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"논점을 찾을 수 없습니다: {issue_id}"
        )


# ========== Issue Extraction Endpoint ==========

@router.post("/answers/{answer_id}/extract-issues", response_model=IssueExtractionResponse)
async def extract_issues(
    answer_id: str,
    request: IssueExtractionRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    논점 추출

    모범답안으로부터 자동으로 논점을 추출합니다.

    ⚠️ Phase 3에서 EXAONE 연동 예정 (현재는 더미 데이터)
    """
    service = IssueService(session)

    # 모범답안 존재 확인
    answer_service = ReferenceAnswerService(session)
    answer = await answer_service.get_answer(answer_id)
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"모범답안을 찾을 수 없습니다: {answer_id}"
        )

    # 논점 추출
    extracted = await service.extract_issues_from_answer(
        answer_id=answer_id,
        auto_save=request.auto_save
    )

    return IssueExtractionResponse(
        reference_answer_id=answer_id,
        extracted_issues=extracted,
        total_extracted=len(extracted)
    )


# ========== Embedding Migration Endpoint ==========

async def _run_embedding_migration_async(
    domain: str,
    batch_size: int,
    session: AsyncSession
):
    """백그라운드에서 실행할 임베딩 마이그레이션"""
    from app.domain.v1.minso.hub.orchestrators.minso_hub import MinsoHub
    hub = MinsoHub(session)
    return await hub.trigger_embedding_migration(domain, batch_size)


@router.get("/embedding", response_model=Dict[str, Any])
async def trigger_reference_embedding_migration(
    batch_size: int = 100,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session)
):
    """
    Reference(모범답안) 임베딩 마이그레이션 트리거.
    reference_answers 테이블 데이터를 임베딩하여 reference_answer_embeddings에 저장합니다.
    """
    background_tasks.add_task(
        _run_embedding_migration_async,
        domain="reference",
        batch_size=batch_size,
        session=session
    )
    return {
        "success": True,
        "message": "Reference 임베딩 마이그레이션이 백그라운드에서 시작되었습니다.",
        "domain": "reference",
        "batch_size": batch_size
    }
