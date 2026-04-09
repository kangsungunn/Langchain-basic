"""
Reasoning Domain API Router

추론 및 분석 API
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domain.v1.minso.spokes.services.reasoning_service import ReasoningTaskService, ReasoningEngine
from app.domain.v1.minso.models.transfers import (
    ReasoningTaskCreate, ReasoningTaskUpdate, ReasoningTaskResponse,
    ReasoningTaskListResponse,
    IssueAnalysisRequest, LogicEvaluationRequest, ExpressionReviewRequest,
    ComprehensiveAnalysisRequest, AnalysisResponse,
)


router = APIRouter(prefix="/reasoning", tags=["Reasoning"])


# ========== Task Management Endpoints ==========

@router.post("/tasks", response_model=ReasoningTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: ReasoningTaskCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    추론 작업 생성

    분석 작업을 수동으로 생성합니다.
    """
    service = ReasoningTaskService(session)
    return await service.create_task(data)


@router.get("/tasks", response_model=ReasoningTaskListResponse)
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """
    추론 작업 목록 조회

    모든 추론 작업을 페이지네이션하여 조회합니다.
    """
    service = ReasoningTaskService(session)
    return await service.get_all_tasks(skip=skip, limit=limit)


@router.get("/tasks/{task_id}", response_model=ReasoningTaskResponse)
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    추론 작업 조회

    특정 추론 작업을 ID로 조회합니다.
    """
    service = ReasoningTaskService(session)
    task = await service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"추론 작업을 찾을 수 없습니다: {task_id}"
        )

    return task


@router.get("/answers/{answer_id}/tasks", response_model=ReasoningTaskListResponse)
async def get_tasks_by_answer(
    answer_id: str,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """
    답안의 추론 작업 조회

    특정 사용자 답안에 대한 모든 추론 작업을 조회합니다.
    """
    service = ReasoningTaskService(session)
    return await service.get_tasks_by_user_answer(answer_id, skip=skip, limit=limit)


@router.put("/tasks/{task_id}", response_model=ReasoningTaskResponse)
async def update_task(
    task_id: str,
    data: ReasoningTaskUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    추론 작업 수정

    추론 작업 정보를 수정합니다.
    """
    service = ReasoningTaskService(session)
    task = await service.update_task(task_id, data)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"추론 작업을 찾을 수 없습니다: {task_id}"
        )

    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    추론 작업 삭제

    추론 작업 및 연관된 결과를 삭제합니다.
    """
    service = ReasoningTaskService(session)
    success = await service.delete_task(task_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"추론 작업을 찾을 수 없습니다: {task_id}"
        )


# ========== Analysis Endpoints ==========

@router.post("/analyze/issues", response_model=AnalysisResponse)
async def analyze_issues(
    request: IssueAnalysisRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    쟁점 분석 ⭐

    사용자 답안이 모범 답안의 쟁점을 얼마나 포함하는지 분석합니다.

    - 식별된 쟁점
    - 누락된 쟁점
    - 쟁점 포함률

    ⚠️ 오케스트레이터를 통해 처리됩니다 (정책 기반 - Star 토폴로지).
    """
    from app.domain.v1.minso.hub.orchestrators import MinsoHub

    hub = MinsoHub(session)

    try:
        return await hub.process(
            domain="reasoning",
            action="analyze_issues",
            request=request
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"쟁점 분석 중 오류 발생: {str(e)}"
        )


@router.post("/analyze/logic", response_model=AnalysisResponse)
async def evaluate_logic(
    request: LogicEvaluationRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    논리 평가 ⭐

    사용자 답안의 논리 일관성과 논증 강도를 평가합니다.

    - 논리 일관성 점수
    - 논증 강도
    - 약점 및 개선 제안

    ⚠️ 오케스트레이터를 통해 처리됩니다 (정책 기반 - Star 토폴로지).
    """
    from app.domain.v1.minso.hub.orchestrators import MinsoHub

    hub = MinsoHub(session)

    try:
        return await hub.process(
            domain="reasoning",
            action="analyze_logic",
            request=request
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"논리 평가 중 오류 발생: {str(e)}"
        )


@router.post("/analyze/expression", response_model=AnalysisResponse)
async def review_expression(
    request: ExpressionReviewRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    표현 검토 ⭐

    사용자 답안의 명료성, 격식성, 문법을 검토합니다.

    - 명료성 점수
    - 격식성 점수
    - 표현 문제 및 개선안

    ⚠️ 오케스트레이터를 통해 처리됩니다 (정책 기반 - Star 토폴로지).
    """
    from app.domain.v1.minso.hub.orchestrators import MinsoHub

    hub = MinsoHub(session)

    try:
        return await hub.process(
            domain="reasoning",
            action="analyze_expression",
            request=request
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"표현 검토 중 오류 발생: {str(e)}"
        )


@router.post("/analyze/comprehensive", response_model=AnalysisResponse)
async def comprehensive_analysis(
    request: ComprehensiveAnalysisRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    종합 분석 ⭐⭐⭐

    쟁점, 논리, 표현을 모두 분석하여 종합 피드백을 제공합니다.

    - 쟁점 분석
    - 논리 평가
    - 표현 검토

    ⚠️ 오케스트레이터를 통해 처리됩니다 (정책 기반 - Star 토폴로지).
    """
    from app.domain.v1.minso.hub.orchestrators import MinsoHub

    hub = MinsoHub(session)

    try:
        return await hub.process(
            domain="reasoning",
            action="comprehensive_analysis",
            request=request
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"종합 분석 중 오류 발생: {str(e)}"
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
async def trigger_reasoning_embedding_migration(
    batch_size: int = 100,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session)
):
    """
    Reasoning(추론 작업) 임베딩 마이그레이션 트리거.
    reasoning_tasks 테이블 데이터를 임베딩하여 reasoning_task_embeddings에 저장합니다.
    """
    background_tasks.add_task(
        _run_embedding_migration_async,
        domain="reasoning",
        batch_size=batch_size,
        session=session
    )
    return {
        "success": True,
        "message": "Reasoning 임베딩 마이그레이션이 백그라운드에서 시작되었습니다.",
        "domain": "reasoning",
        "batch_size": batch_size
    }
