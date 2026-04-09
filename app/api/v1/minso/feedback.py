"""
Feedback Domain API Router

피드백 관리 및 생성 API
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domain.v1.minso.spokes.services.feedback_service import FeedbackService, FeedbackGenerator
from app.domain.v1.minso.hub.orchestrators.minso_hub import MinsoHub
from app.domain.v1.minso.models.transfers import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse,
    FeedbackListResponse,
    GenerateFeedbackRequest, GenerateFeedbackResponse,
    FeedbackReportRequest, FeedbackReportResponse,
    FeedbackCorrectionCreate, FeedbackCorrectionResponse,
)


router = APIRouter(prefix="/feedback", tags=["Feedback"])


# ========== Feedback Management Endpoints ==========

@router.post("/feedbacks", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    data: FeedbackCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    피드백 생성

    피드백을 수동으로 생성합니다.
    """
    service = FeedbackService(session)
    return await service.create_feedback(data)


@router.get("/feedbacks", response_model=FeedbackListResponse)
async def get_feedbacks(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """
    피드백 목록 조회

    모든 피드백을 페이지네이션하여 조회합니다.
    """
    service = FeedbackService(session)
    return await service.get_all_feedbacks(skip=skip, limit=limit)


@router.get("/feedbacks/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    피드백 조회

    특정 피드백을 ID로 조회합니다.
    """
    service = FeedbackService(session)
    feedback = await service.get_feedback(feedback_id)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"피드백을 찾을 수 없습니다: {feedback_id}"
        )

    return feedback


@router.get("/answers/{answer_id}/feedbacks", response_model=FeedbackListResponse)
async def get_feedbacks_by_answer(
    answer_id: str,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """
    답안의 피드백 조회

    특정 사용자 답안에 대한 모든 피드백을 조회합니다.
    """
    service = FeedbackService(session)
    return await service.get_feedbacks_by_user_answer(answer_id, skip=skip, limit=limit)


@router.put("/feedbacks/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: str,
    data: FeedbackUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    피드백 수정

    피드백 정보를 수정합니다.
    """
    service = FeedbackService(session)
    feedback = await service.update_feedback(feedback_id, data)

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"피드백을 찾을 수 없습니다: {feedback_id}"
        )

    return feedback


@router.delete("/feedbacks/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    피드백 삭제

    피드백 및 연관된 항목을 삭제합니다.
    """
    service = FeedbackService(session)
    success = await service.delete_feedback(feedback_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"피드백을 찾을 수 없습니다: {feedback_id}"
        )


# ========== 피드백에 대한 사용자 의견 (학습용) ==========

@router.post(
    "/feedbacks/{feedback_id}/corrections",
    response_model=FeedbackCorrectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feedback_correction(
    feedback_id: str,
    data: FeedbackCorrectionCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    피드백에 대한 정정/추가 요청 저장 (학습용)

    - **correction**: "이 부분은 틀렸다, 이렇게 피드백 내려라"
    - **addition**: "이런 포인트를 더 추가/강조해서 피드백 내려라"

    수집된 데이터는 나중에 SFT/RAG 등으로 모델 개선에 활용할 수 있습니다.
    """
    import uuid
    from app.domain.v1.minso.models import FeedbackCorrection
    from app.domain.v1.minso.hub.repositories import FeedbackRepository, FeedbackCorrectionRepository

    feedback_repo = FeedbackRepository(session)
    correction_repo = FeedbackCorrectionRepository(session)

    feedback = await feedback_repo.get_by_id(feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"피드백을 찾을 수 없습니다: {feedback_id}",
        )

    raw = (data.correction_type or "").strip().lower()
    if raw not in ("correction", "addition"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="correction_type은 'correction' 또는 'addition' 이어야 합니다.",
        )

    correction = FeedbackCorrection(
        id=str(uuid.uuid4()),
        feedback_id=feedback_id,
        correction_type=raw,
        content=data.content.strip(),
    )
    await correction_repo.create(correction)
    await session.commit()

    return FeedbackCorrectionResponse.from_orm(correction)


@router.get(
    "/feedbacks/{feedback_id}/corrections",
    response_model=List[FeedbackCorrectionResponse],
)
async def list_feedback_corrections(
    feedback_id: str,
    session: AsyncSession = Depends(get_session),
):
    """특정 피드백에 대한 사용자 정정/추가 요청 목록 조회 (학습용)."""
    from app.domain.v1.minso.hub.repositories import FeedbackRepository, FeedbackCorrectionRepository

    feedback_repo = FeedbackRepository(session)
    correction_repo = FeedbackCorrectionRepository(session)

    feedback = await feedback_repo.get_by_id(feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"피드백을 찾을 수 없습니다: {feedback_id}",
        )

    corrections = await correction_repo.get_by_feedback_id(feedback_id)
    return [FeedbackCorrectionResponse.from_orm(c) for c in corrections]


# ========== Feedback Generation Endpoints ==========

@router.post("/generate", response_model=GenerateFeedbackResponse)
async def generate_feedback(
    request: GenerateFeedbackRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    피드백 생성 ⭐

    추론 결과로부터 구조화된 피드백을 자동 생성합니다.

    - 쟁점 피드백: 식별/누락 쟁점
    - 논리 피드백: 일관성, 논증 강도, 약점
    - 표현 피드백: 명료성, 격식성, 개선안
    - 종합 피드백: 모든 항목 통합

    **Reasoning Task → Feedback 변환**

    ⚠️ 오케스트레이터를 통해 처리됩니다 (정책 기반 - Star 토폴로지).
    """
    from app.domain.v1.minso.hub.orchestrators import MinsoHub

    hub = MinsoHub(session)

    try:
        return await hub.process(
            domain="feedback",
            action="generate",
            request=request
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"피드백 생성 중 오류 발생: {str(e)}"
        )


@router.post("/report", response_model=FeedbackReportResponse)
async def generate_report(
    request: FeedbackReportRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    피드백 리포트 생성 ⭐⭐⭐

    사용자 답안의 모든 피드백을 통합한 리포트를 생성합니다.

    - 전체 피드백 목록
    - 평균 점수
    - 리포트 요약

    ⚠️ 오케스트레이터를 통해 처리됩니다 (정책 기반 - Star 토폴로지).
    """
    from app.domain.v1.minso.hub.orchestrators import MinsoHub

    hub = MinsoHub(session)

    try:
        return await hub.process(
            domain="feedback",
            action="generate_report",
            request=request
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리포트 생성 중 오류 발생: {str(e)}"
        )


# ========== Embedding Migration Endpoints ==========

async def _run_embedding_migration_async(
    domain: str,
    batch_size: int,
    session: AsyncSession
):
    """백그라운드에서 실행할 임베딩 마이그레이션 작업"""
    hub = MinsoHub(session)
    try:
        result = await hub.trigger_embedding_migration(domain, batch_size)
        return result
    except Exception as e:
        # 로깅은 MinsoHub에서 처리됨
        raise


@router.get("/embedding", response_model=Dict[str, Any])
async def trigger_feedback_embedding_migration(
    batch_size: int = 100,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session)
):
    """
    Feedback 임베딩 마이그레이션 트리거

    모든 Feedback 데이터에 대해 임베딩을 생성하고 저장합니다.
    MCP 서버의 KoELECTRA 모델을 사용하여 백그라운드에서 처리됩니다.

    Args:
        batch_size: 배치 크기 (한 번에 처리할 레코드 수, 기본: 100)

    Returns:
        {
            "success": bool,
            "message": str,
            "domain": "feedback"
        }
    """
    # 백그라운드 작업으로 실행
    background_tasks.add_task(
        _run_embedding_migration_async,
        domain="feedback",
        batch_size=batch_size,
        session=session
    )

    return {
        "success": True,
        "message": "Feedback 임베딩 마이그레이션이 백그라운드에서 시작되었습니다.",
        "domain": "feedback",
        "batch_size": batch_size
    }
