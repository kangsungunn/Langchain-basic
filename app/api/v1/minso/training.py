"""
Training Domain - API Endpoints

학습 데이터 및 작업 관리 API
"""

from typing import List, Optional
from datetime import datetime
import asyncio
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.config import settings
from training.services import TrainingDataService, TrainingOrchestrator
from training.schemas import (
    TrainingDataCreate, TrainingDataResponse,
    TrainingJobCreate, TrainingJobResponse,
    TrainingDataListResponse, TrainingJobListResponse
)
from training.models import TrainingDataStatus
from app.core.utils.pdf_parser import PDFParser

router = APIRouter(prefix="/training", tags=["Training"])


@router.post("/data", response_model=TrainingDataResponse, status_code=status.HTTP_201_CREATED)
async def create_training_data(
    data: TrainingDataCreate,
    session: AsyncSession = Depends(get_session),
    auto_trigger: bool = Query(True, description="자동 학습 트리거 활성화 여부"),
    min_data_count: int = Query(10, ge=1, description="자동 학습 시작 최소 데이터 개수")
):
    """
    학습 데이터 생성

    새로운 학습 데이터를 추가합니다.
    auto_trigger가 True이고 충분한 데이터가 쌓이면 자동으로 학습을 시작합니다.

    ⚠️ 오케스트레이터를 통해 처리됩니다 (정책/규칙 기반 라우팅).
    """
    # 로깅: 받은 데이터 출력
    from app.core.utils.logger import get_logger
    logger = get_logger()

    logger.info("=" * 80)
    logger.info("📥 학습 데이터 수신 (JSONL 업로드)")
    logger.info("=" * 80)
    logger.info(f"📍 엔드포인트: POST /api/v1/training/data")
    logger.info(f"📋 문제 텍스트 (처음 150자): {data.problem_text[:150]}...")
    logger.info(f"📋 모범답안 텍스트 (처음 150자): {data.reference_answer_text[:150]}...")
    logger.info(f"📋 사용자 답안: {'있음' if data.user_answer_text else '없음'}")
    if data.user_answer_text:
        logger.info(f"   └─ 내용 (처음 100자): {data.user_answer_text[:100]}...")
    logger.info(f"🏷️  라벨: {data.labels if data.labels else '(없음)'}")
    logger.info(f"⚙️  설정: auto_trigger={auto_trigger}, min_data_count={min_data_count}")
    logger.info(f"🔗 참조 ID: problem_id={data.problem_id}, reference_answer_id={data.reference_answer_id}, user_answer_id={data.user_answer_id}")
    logger.info("=" * 80)

    # 오케스트레이터를 통해 처리
    from app.domain.v1.minso.hub.orchestrators import MinsoHub

    hub = MinsoHub(session)

    try:
        # 오케스트레이터를 통해 요청 처리 (정책/규칙 기반 라우팅)
        training_data = await hub.process(
            domain="training",
            action="create_training_data",
            request=data
        )

        logger.info(f"✅ 학습 데이터 생성 완료")
        logger.info(f"   └─ ID: {training_data.id}")
        logger.info(f"   └─ 상태: {training_data.status.value}")
        logger.info(f"   └─ 생성 시간: {training_data.created_at}")

        # 자동 트리거 체크 (백그라운드에서 실행)
        if auto_trigger:
            logger.info(f"🔄 자동 학습 트리거 확인 중... (최소 데이터 개수: {min_data_count})")
            training_orchestrator = TrainingOrchestrator(session)
            should_start = await training_orchestrator.check_auto_training_trigger(min_data_count=min_data_count)

            if should_start:
                logger.info(f"🚀 자동 학습 시작 조건 충족! 학습을 시작합니다...")
                # 기본 설정으로 학습 시작
                default_config = {
                    "base_model": "exaone-2.4b",
                    "num_train_epochs": 3,
                    "per_device_train_batch_size": 1,
                    "learning_rate": 2e-5,
                    "lora_r": 8,
                    "lora_alpha": 16
                }

                # 백그라운드에서 학습 시작 (응답은 즉시 반환)
                job_name = f"Auto Training - {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                logger.info(f"   └─ 작업 이름: {job_name}")
                logger.info(f"   └─ 학습 설정: {default_config}")

                asyncio.create_task(
                    training_orchestrator.start_training(
                        job_name=job_name,
                        config=default_config,
                        training_data_ids=None,  # 전체 사용
                        auto_trigger=True
                    )
                )
            else:
                logger.info(f"⏸️  자동 학습 시작 조건 미충족 (현재 데이터 부족, 최소 {min_data_count}개 필요)")

        logger.info("=" * 80)
        return TrainingDataResponse.from_orm(training_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 데이터 생성 실패: {str(e)}"
        )


@router.post("/data/pdf", response_model=TrainingDataListResponse, status_code=status.HTTP_201_CREATED)
async def create_training_data_from_pdf(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    auto_trigger: bool = Query(True, description="자동 학습 트리거 활성화 여부"),
    min_data_count: int = Query(10, ge=1, description="자동 학습 시작 최소 데이터 개수")
):
    """
    PDF 파일에서 학습 데이터 생성

    PDF 파일을 업로드하면 자동으로 문제와 모범답안을 추출하여 학습 데이터를 생성합니다.
    사용자 답안은 빈 값으로 설정되며, 라벨은 나중에 JSONL 파일로 추가할 수 있습니다.

    1. PDF 파일 저장
    2. PDF 파싱 (문제/모범답안 추출)
    3. 각 문제별로 TrainingData 생성
    4. 자동 학습 트리거 (옵션)
    """
    # 파일 확장자 확인
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF 파일만 업로드 가능합니다"
        )

    # 업로드 디렉토리 생성
    upload_dir = Path(settings.PROJECT_ROOT) / "uploads" / "training"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 파일 저장
    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}.pdf"

    try:
        # 파일 내용 읽기 및 저장
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # PDF 파싱
        try:
            parser = PDFParser()
            parsed_data = parser.parse_training_pdf(str(file_path))
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF 파싱 라이브러리가 설치되지 않았습니다: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF 파싱 실패: {str(e)}"
            )

        if not parsed_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF에서 학습 데이터를 추출할 수 없습니다. 문제와 모범답안이 포함되어 있는지 확인해주세요."
            )

        # 학습 데이터 생성
        service = TrainingDataService(session)
        created_items = []

        for data in parsed_data:
            try:
                training_data = await service.create(
                    TrainingDataCreate(
                        problem_text=data["problem_text"],
                        reference_answer_text=data["reference_answer_text"],
                        user_answer_text=data.get("user_answer_text", ""),
                        labels=data.get("labels", {}),
                        problem_id=None,
                        reference_answer_id=None,
                        user_answer_id=None,
                        meta={"source": "pdf", "pdf_file": file.filename}
                    )
                )
                created_items.append(training_data)
            except Exception as e:
                # 개별 항목 생성 실패는 로그만 남기고 계속 진행
                from app.core.utils.logger import get_logger
                logger = get_logger()
                logger.warning(f"학습 데이터 생성 실패: {str(e)}")

        if not created_items:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="학습 데이터 생성에 실패했습니다"
            )

        # 자동 트리거 체크 (백그라운드에서 실행)
        if auto_trigger:
            orchestrator = TrainingOrchestrator(session)
            should_start = await orchestrator.check_auto_training_trigger(min_data_count=min_data_count)

            if should_start:
                # 기본 설정으로 학습 시작
                default_config = {
                    "base_model": "exaone-2.4b",
                    "num_train_epochs": 3,
                    "per_device_train_batch_size": 1,
                    "learning_rate": 2e-5,
                    "lora_r": 8,
                    "lora_alpha": 16
                }

                # 백그라운드에서 학습 시작 (응답은 즉시 반환)
                asyncio.create_task(
                    orchestrator.start_training(
                        job_name=f"Auto Training from PDF - {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                        config=default_config,
                        training_data_ids=None,  # 전체 사용
                        auto_trigger=True
                    )
                )

        return TrainingDataListResponse(
            total=len(created_items),
            items=[TrainingDataResponse.from_orm(item) for item in created_items]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF 처리 실패: {str(e)}"
        )
    finally:
        # 임시 파일 삭제 (선택사항)
        # if file_path.exists():
        #     file_path.unlink()
        pass


@router.get("/data", response_model=TrainingDataListResponse)
async def get_training_data_list(
    status: Optional[str] = Query(None, description="상태 필터 (pending, processed, used)"),
    limit: Optional[int] = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session)
):
    """
    학습 데이터 목록 조회
    """
    service = TrainingDataService(session)

    status_filter = None
    if status:
        try:
            status_filter = TrainingDataStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"잘못된 상태 값: {status}"
            )

    items, total = await service.get_all(status=status_filter, limit=limit, offset=offset)

    return TrainingDataListResponse(
        total=total,
        items=[TrainingDataResponse.from_orm(item) for item in items]
    )


@router.get("/data/{data_id}", response_model=TrainingDataResponse)
async def get_training_data(
    data_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    학습 데이터 조회
    """
    service = TrainingDataService(session)
    data = await service.get_by_id(data_id)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"학습 데이터를 찾을 수 없습니다: {data_id}"
        )

    return TrainingDataResponse.from_orm(data)


@router.post("/jobs", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_training_job(
    job: TrainingJobCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    학습 작업 생성 및 시작

    새로운 학습 작업을 생성하고 자동으로 시작합니다.
    """
    orchestrator = TrainingOrchestrator(session)
    try:
        training_job = await orchestrator.start_training(
            job_name=job.job_name,
            config=job.config,
            training_data_ids=job.training_data_ids
        )
        return TrainingJobResponse.from_orm(training_job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 작업 생성 실패: {str(e)}"
        )


@router.get("/jobs", response_model=TrainingJobListResponse)
async def get_training_job_list(
    status: Optional[str] = Query(None, description="상태 필터"),
    limit: Optional[int] = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session)
):
    """
    학습 작업 목록 조회
    """
    orchestrator = TrainingOrchestrator(session)
    from training.models import TrainingJobStatus

    status_filter = None
    if status:
        try:
            status_filter = TrainingJobStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"잘못된 상태 값: {status}"
            )

    jobs = await orchestrator.job_repo.get_all(status=status_filter, limit=limit, offset=offset)
    total = len(jobs)  # 간단하게, 실제로는 count 쿼리 필요

    return TrainingJobListResponse(
        total=total,
        items=[TrainingJobResponse.from_orm(job) for job in jobs]
    )


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(
    job_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    학습 작업 조회
    """
    orchestrator = TrainingOrchestrator(session)
    job = await orchestrator.get_job_status(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"학습 작업을 찾을 수 없습니다: {job_id}"
        )

    return TrainingJobResponse.from_orm(job)


@router.post("/auto-trigger", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
async def trigger_auto_training(
    min_data_count: int = Query(10, ge=1, description="최소 학습 데이터 개수"),
    session: AsyncSession = Depends(get_session)
):
    """
    자동 학습 트리거

    충분한 학습 데이터가 쌓이면 자동으로 학습을 시작합니다.
    """
    orchestrator = TrainingOrchestrator(session)

    # 트리거 조건 확인
    should_start = await orchestrator.check_auto_training_trigger(min_data_count=min_data_count)

    if not should_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"학습 데이터가 부족합니다. 최소 {min_data_count}개 필요"
        )

    # 기본 설정으로 학습 시작
    default_config = {
        "base_model": "exaone-2.4b",
        "num_train_epochs": 3,
        "per_device_train_batch_size": 1,
        "learning_rate": 2e-5,
        "lora_r": 8,
        "lora_alpha": 16
    }

    try:
        job = await orchestrator.start_training(
            job_name=f"Auto Training - {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            config=default_config,
            training_data_ids=None,  # 전체 사용
            auto_trigger=True
        )
        return TrainingJobResponse.from_orm(job)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"자동 학습 시작 실패: {str(e)}"
        )
