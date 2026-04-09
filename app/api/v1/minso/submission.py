"""
Submission Domain API Router

사용자 답안 관리 API
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Body, File, UploadFile, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.config import settings
from app.core.utils.logger import get_logger
from app.domain.v1.minso.spokes.services.submission_service import (
    UserAnswerService,
    AnswerStructureService,
    OCRService,
)
from app.domain.v1.minso.spokes.services.reference_service import ReferenceAnswerService
from app.domain.v1.minso.models.transfers import (
    UserAnswerCreateText, UserAnswerCreateImage, UserAnswerUpdate, UserAnswerResponse,
    UserAnswerListResponse, AnswerStructureResponse,
    StructureAnalysisRequest, StructureAnalysisResponse,
    OCRRequest, OCRResponse,
    AnalyzeAndFeedbackResponse,
    ComprehensiveAnalysisRequest,
    GenerateFeedbackRequest,
)


router = APIRouter(prefix="/submission", tags=["Submission"])


# ========== UserAnswer Endpoints ==========

@router.post("/answers/text", response_model=UserAnswerResponse, status_code=status.HTTP_201_CREATED)
async def create_text_answer(
    data: UserAnswerCreateText,
    session: AsyncSession = Depends(get_session)
):
    """
    텍스트 답안 생성

    사용자가 직접 입력한 텍스트 답안을 생성합니다.

    ⚠️ 오케스트레이터를 통해 처리됩니다 (규칙 기반 - Direct Service).
    """
    from app.domain.v1.minso.hub.orchestrators import MinsoHub

    hub = MinsoHub(session)
    result = await hub.process(
        domain="submission",
        action="create_text_answer",
        request=data
    )
    # Phase 2: 생성된 답안 1건 자동 임베딩 (실패해도 201 반환)
    try:
        await hub.embed_one("submission", result.id)
    except Exception:
        pass
    return result


@router.post("/answers/image", response_model=UserAnswerResponse, status_code=status.HTTP_201_CREATED)
async def create_image_answer(
    file: UploadFile = File(...),
    problem_id: str = Form(""),
    question_label: Optional[str] = Form(None),
    problem_file: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session)
):
    """
    이미지/PDF 답안 생성.

    problem_file이 있으면: 문제 PDF에서 텍스트 추출 → DB에 문제 등록 → 해당 problem_id로 답안 연결.
    없으면: problem_id(또는 빈 값이면 unknown)로 답안만 생성.
    """
    upload_dir = Path(settings.PROJECT_ROOT) / "uploads" / "answers"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix if file.filename else ".pdf"
    file_path = upload_dir / f"{file_id}{file_ext}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    relative_path = f"uploads/answers/{file_id}{file_ext}"

    final_problem_id = problem_id if problem_id and problem_id.strip() else None

    # 문제 PDF가 있으면: 파싱 후 DB에 문제 등록하고 그 id 사용
    if problem_file and problem_file.filename and problem_file.filename.lower().endswith(".pdf"):
        try:
            from app.core.utils.pdf_parser import extract_text_from_pdf
            from app.domain.v1.minso.models.transfers import ProblemCreate
            from app.domain.v1.minso.spokes.services.reference_service import ProblemService

            problem_upload_dir = Path(settings.PROJECT_ROOT) / "uploads" / "problems"
            problem_upload_dir.mkdir(parents=True, exist_ok=True)
            problem_pdf_id = str(uuid.uuid4())
            problem_pdf_path = problem_upload_dir / f"{problem_pdf_id}.pdf"
            problem_content_bytes = await problem_file.read()
            with open(problem_pdf_path, "wb") as f:
                f.write(problem_content_bytes)

            problem_text = extract_text_from_pdf(str(problem_pdf_path))
            if problem_text:
                problem_svc = ProblemService(session)
                title = Path(problem_file.filename or "업로드 문제").stem
                problem_create = ProblemCreate(title=title[:200], content=problem_text, meta={"source": "upload", "filename": problem_file.filename})
                created_problem = await problem_svc.create_problem(problem_create)
                final_problem_id = created_problem.id
        except Exception as e:
            get_logger().warning(f"문제 PDF 처리 실패(답안만 생성): {e}")

    if not final_problem_id:
        final_problem_id = "unknown"

    meta = None
    if question_label and str(question_label).strip():
        meta = {"question_label": str(question_label).strip()}

    data = UserAnswerCreateImage(
        problem_id=final_problem_id,
        submission_type="image",
        image_path=relative_path,
        meta=meta
    )

    from app.domain.v1.minso.hub.orchestrators import MinsoHub

    hub = MinsoHub(session)
    result = await hub.process(
        domain="submission",
        action="create_image_answer",
        request=data
    )
    try:
        await hub.embed_one("submission", result.id)
    except Exception:
        pass
    return result


@router.get("/answers", response_model=UserAnswerListResponse)
async def get_answers(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """
    답안 목록 조회

    모든 사용자 답안을 페이지네이션하여 조회합니다.
    """
    service = UserAnswerService(session)
    return await service.get_all_answers(skip=skip, limit=limit)


@router.get("/answers/{answer_id}", response_model=UserAnswerResponse)
async def get_answer(
    answer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    답안 조회

    특정 사용자 답안을 ID로 조회합니다.
    """
    service = UserAnswerService(session)
    answer = await service.get_answer(answer_id)

    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"답안을 찾을 수 없습니다: {answer_id}"
        )

    return answer


# ========== Phase 1: 제출 → 추론 → 피드백 한 번에 ==========


@router.get(
    "/answers/{answer_id}/review-result",
    response_model=AnalyzeAndFeedbackResponse,
    status_code=status.HTTP_200_OK,
)
async def get_review_result(
    answer_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    이미 생성된 첨삭 결과 조회 (리뷰 페이지용).

    해당 답안에 대한 종합(comprehensive) 피드백이 있으면 분석 요약과 함께 반환합니다.
    없으면 404 → 프론트는 POST analyze-and-feedback으로 새로 요청하면 됩니다.
    """
    from app.domain.v1.minso.models import FeedbackType
    from app.domain.v1.minso.models.transfers import FeedbackResponse
    from app.domain.v1.minso.hub.repositories import FeedbackRepository, ReasoningResultRepository, UserAnswerRepository, ProblemRepository

    feedback_repo = FeedbackRepository(session)
    result_repo = ReasoningResultRepository(session)
    user_answer_repo = UserAnswerRepository(session)
    problem_repo = ProblemRepository(session)

    user_answer = await user_answer_repo.get_by_id(answer_id)
    problem_id: Optional[str] = None
    problem_title: Optional[str] = None
    question_label: Optional[str] = None
    if user_answer:
        problem_id = getattr(user_answer, "problem_id", None) or None
        meta = getattr(user_answer, "meta", None) or {}
        if isinstance(meta, dict):
            question_label = meta.get("question_label") or meta.get("설문")
        if problem_id:
            problem = await problem_repo.get_by_id(problem_id)
            if problem:
                problem_title = getattr(problem, "title", None) or None

    feedbacks = await feedback_repo.get_by_user_answer(answer_id, limit=50)
    comprehensive = [f for f in feedbacks if getattr(f.feedback_type, "value", f.feedback_type) == "comprehensive"]
    if not comprehensive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 답안에 대한 첨삭 결과가 없습니다. 분석·피드백을 먼저 실행해 주세요.",
        )

    comprehensive.sort(key=lambda f: f.created_at or datetime.min, reverse=True)
    feedback = comprehensive[0]
    task_id = feedback.reasoning_task_id
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="첨삭 결과에 추론 작업이 연결되어 있지 않습니다.",
        )

    results = await result_repo.get_by_task_id(task_id)
    summary: Dict[str, Any] = {}
    for r in results:
        content = getattr(r, "content", None) or {}
        if not isinstance(content, dict):
            continue
        rt = getattr(r, "result_type", None) or ""
        if rt == "issue_analysis":
            summary["issue_coverage"] = content.get("coverage_rate", 0)
        elif rt == "logic_evaluation":
            summary["logic_coherence"] = content.get("coherence_score", 0)
            if content.get("raw_analysis"):
                summary["logic_evaluation_text"] = content.get("raw_analysis")
        elif rt == "expression_review":
            summary["expression_clarity"] = content.get("clarity_score", 0)
            if content.get("raw_analysis"):
                summary["expression_review_text"] = content.get("raw_analysis")
        elif rt == "exaone_analysis":
            summary["exaone_analysis"] = content.get("analysis", "")

    feedback_with_items = await feedback_repo.get_by_id(feedback.id)
    if not feedback_with_items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="피드백을 찾을 수 없습니다.")

    return AnalyzeAndFeedbackResponse(
        user_answer_id=answer_id,
        reasoning_task_id=task_id,
        analysis_summary=summary,
        feedback=FeedbackResponse.model_validate(feedback_with_items),
        message="기존 결과를 불러왔습니다.",
        problem_id=problem_id,
        problem_title=problem_title,
        question_label=question_label,
    )


@router.post(
    "/answers/{answer_id}/analyze-and-feedback",
    response_model=AnalyzeAndFeedbackResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_and_feedback(
    answer_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    답안 분석 및 피드백 생성 (한 번에) ⭐

    사용자 답안에 대해 1) 종합 추론(쟁점/논리/표현) 실행 → 2) 그 결과로 피드백 생성까지 한 번에 실행합니다.
    해당 문제의 모범답안이 있어야 합니다.

    - 404: 답안 없음
    - 400: 해당 문제에 모범답안 없음
    - 500: 추론 또는 피드백 생성 실패
    """
    from app.domain.v1.minso.hub.orchestrators.minso_hub import MinsoHub

    # 1) 사용자 답안 조회
    user_service = UserAnswerService(session)
    user_answer = await user_service.get_answer(answer_id)
    if not user_answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"답안을 찾을 수 없습니다: {answer_id}",
        )

    # 2) 해당 문제의 모범답안 조회 (있으면 사용, 없으면 논점 추출로 대체)
    ref_service = ReferenceAnswerService(session)
    ref_answers = await ref_service.get_answers_by_problem(user_answer.problem_id or "")
    reference_answer_id: Optional[str] = ref_answers[0].id if ref_answers else None
    extracted_issues: Optional[List[str]] = None

    if not ref_answers:
        # 모범답안 없음 → 문제 지문으로 논점 추출 후 그걸 기준으로 분석
        from app.domain.v1.minso.hub.repositories import ProblemRepository
        from app.domain.v1.minso.spokes.services.issue_extraction_service import extract_issues_from_problem

        problem_repo = ProblemRepository(session)
        problem = await problem_repo.get_by_id(user_answer.problem_id) if (user_answer.problem_id and user_answer.problem_id.strip()) else None
        problem_content = (getattr(problem, "content", None) or "").strip() if problem else ""
        if not problem_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"문제({user_answer.problem_id})에 대한 모범답안이 없고, 문제 지문도 없어 분석할 수 없습니다. 모범답안을 등록하거나 문제를 지정해 주세요.",
            )
        try:
            extracted_issues = extract_issues_from_problem(problem_content)
        except Exception as e:
            get_logger().warning("논점 추출 실패 (폴백): %s", e)
        if not extracted_issues:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"문제({user_answer.problem_id})에 대한 모범답안이 없고, 논점 추출 결과도 없습니다. 모범답안을 등록해 주세요.",
            )

    hub = MinsoHub(session)

    # 3) 종합 추론 실행
    analysis_req = ComprehensiveAnalysisRequest(
        user_answer_id=answer_id,
        reference_answer_id=reference_answer_id or "",
        problem_id=user_answer.problem_id or "",
        save_result=True,
        extracted_issues=extracted_issues,
    )
    try:
        analysis_resp = await hub.process(
            domain="reasoning",
            action="comprehensive_analysis",
            request=analysis_req,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"추론 분석 중 오류: {str(e)}",
        ) from e

    # Phase 2: 생성된 추론 작업 1건 자동 임베딩 (실패해도 계속 진행)
    try:
        await hub.embed_one("reasoning", analysis_resp.task_id)
    except Exception:
        pass

    # 4) 추론 결과로 피드백 생성
    feedback_req = GenerateFeedbackRequest(
        user_answer_id=answer_id,
        reasoning_task_id=analysis_resp.task_id,
        feedback_type="comprehensive",
        include_suggestions=True,
    )
    try:
        feedback_resp = await hub.process(
            domain="feedback",
            action="generate",
            request=feedback_req,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"피드백 생성 중 오류: {str(e)} (추론 작업 ID: {analysis_resp.task_id})",
        ) from e

    # Phase 2: 생성된 피드백 1건 자동 임베딩 (실패해도 응답은 반환)
    try:
        embed_result = await hub.embed_one("feedback", feedback_resp.feedback.id)
        if not embed_result.get("success"):
            get_logger().warning("피드백 자동 임베딩 실패: %s", embed_result.get("error"))
    except Exception:
        pass  # 임베딩 실패 시에도 분석·피드백 응답은 그대로 반환

    problem_id_out: Optional[str] = getattr(user_answer, "problem_id", None) or None
    problem_title_out: Optional[str] = None
    question_label_out: Optional[str] = None
    meta = getattr(user_answer, "meta", None) or {}
    if isinstance(meta, dict):
        question_label_out = meta.get("question_label") or meta.get("설문")
    if problem_id_out:
        from app.domain.v1.minso.hub.repositories import ProblemRepository
        problem_repo = ProblemRepository(session)
        problem = await problem_repo.get_by_id(problem_id_out)
        if problem:
            problem_title_out = getattr(problem, "title", None) or None

    return AnalyzeAndFeedbackResponse(
        user_answer_id=answer_id,
        reasoning_task_id=analysis_resp.task_id,
        analysis_summary=analysis_resp.summary,
        feedback=feedback_resp.feedback,
        message="분석 및 피드백 생성이 완료되었습니다.",
        problem_id=problem_id_out,
        problem_title=problem_title_out,
        question_label=question_label_out,
    )


@router.get("/problems/{problem_id}/answers", response_model=UserAnswerListResponse)
async def get_answers_by_problem(
    problem_id: str,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    """
    문제의 답안 조회

    특정 문제에 대한 모든 사용자 답안을 조회합니다.
    """
    service = UserAnswerService(session)
    return await service.get_answers_by_problem(problem_id, skip=skip, limit=limit)


@router.put("/answers/{answer_id}", response_model=UserAnswerResponse)
async def update_answer(
    answer_id: str,
    data: UserAnswerUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    답안 수정

    사용자 답안 내용을 수정합니다.
    """
    service = UserAnswerService(session)
    answer = await service.update_answer(answer_id, data)

    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"답안을 찾을 수 없습니다: {answer_id}"
        )

    return answer


@router.delete("/answers/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_answer(
    answer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    답안 삭제

    사용자 답안 및 연관된 구조를 삭제합니다.
    """
    service = UserAnswerService(session)
    success = await service.delete_answer(answer_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"답안을 찾을 수 없습니다: {answer_id}"
        )


# ========== Structure Analysis Endpoint ==========

@router.post("/answers/{answer_id}/analyze", response_model=StructureAnalysisResponse)
async def analyze_structure(
    answer_id: str,
    request: Optional[StructureAnalysisRequest] = Body(None),
    session: AsyncSession = Depends(get_session)
):
    """
    답안 구조 분석

    사용자 답안을 문단과 문장으로 분리하고 통계를 생성합니다.

    - 문단 분리: 빈 줄 기준
    - 문장 분리: ., ?, ! 기준
    - 통계: 문단 수, 문장 수, 단어 수
    """
    service = AnswerStructureService(session)

    # body가 없으면 기본값 사용
    auto_save = request.auto_save if request else True

    try:
        return await service.analyze_structure(
            user_answer_id=answer_id,
            auto_save=auto_save
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/answers/{answer_id}/structure", response_model=AnswerStructureResponse)
async def get_structure(
    answer_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    답안 구조 조회

    사용자 답안의 구조화된 정보를 조회합니다.
    """
    service = AnswerStructureService(session)
    structure = await service.get_structure(answer_id)

    if not structure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"답안 구조를 찾을 수 없습니다: {answer_id}"
        )

    return structure


# ========== OCR Endpoint ==========

@router.post("/answers/{answer_id}/ocr", response_model=OCRResponse)
async def process_ocr(
    answer_id: str,
    request: OCRRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    OCR 처리

    이미지 답안을 텍스트로 변환합니다.

    ⚠️ Phase 4에서 실제 OCR 엔진 연동 예정 (현재는 더미 데이터)
    """
    service = OCRService(session)

    try:
        return await service.process_ocr(
            user_answer_id=answer_id,
            confidence_threshold=request.confidence_threshold
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
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
async def trigger_submission_embedding_migration(
    batch_size: int = 100,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: AsyncSession = Depends(get_session)
):
    """
    Submission(사용자 답안) 임베딩 마이그레이션 트리거.
    user_answers 테이블 데이터를 임베딩하여 user_answer_embeddings에 저장합니다.
    """
    background_tasks.add_task(
        _run_embedding_migration_async,
        domain="submission",
        batch_size=batch_size,
        session=session
    )
    return {
        "success": True,
        "message": "Submission 임베딩 마이그레이션이 백그라운드에서 시작되었습니다.",
        "domain": "submission",
        "batch_size": batch_size
    }
