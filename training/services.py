"""
Training - 서비스 (루트 training/ 폴더)

학습 데이터·작업·모델 버전 관리 및 학습 실행 오케스트레이션.
모델/리포/스키마는 동일 패키지(training), 학습 스크립트는 training.examination.civil_law.train_simple.
"""

import uuid
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from training.models import (
    TrainingData, TrainingJob, ModelVersion,
    TrainingDataStatus, TrainingJobStatus, ModelVersionStatus,
)
from training.repositories import (
    TrainingDataRepository, TrainingJobRepository, ModelVersionRepository,
)
from training.schemas import (
    TrainingDataCreate, TrainingJobCreate, ModelVersionCreate,
)
from app.core.utils.logger import get_logger

# 루트 training/ 폴더 기준
PROJECT_ROOT = Path(__file__).resolve().parent

logger = get_logger()


class TrainingDataService:
    """학습 데이터 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TrainingDataRepository(session)

    async def create(self, data: TrainingDataCreate) -> TrainingData:
        training_data = TrainingData(
            id=str(uuid.uuid4()),
            problem_id=data.problem_id,
            reference_answer_id=data.reference_answer_id,
            user_answer_id=data.user_answer_id,
            problem_text=data.problem_text,
            reference_answer_text=data.reference_answer_text,
            user_answer_text=data.user_answer_text,
            labels=data.labels,
            status=TrainingDataStatus.PENDING,
            meta=data.meta
        )
        return await self.repo.create(training_data)

    async def get_by_id(self, data_id: str) -> Optional[TrainingData]:
        return await self.repo.get_by_id(data_id)

    async def get_all(
        self,
        status: Optional[TrainingDataStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> tuple[List[TrainingData], int]:
        items = await self.repo.get_all(status=status, limit=limit, offset=offset)
        total = await self.repo.count(status=status)
        return items, total

    async def mark_as_used(self, data_ids: List[str]):
        for data_id in data_ids:
            data = await self.repo.get_by_id(data_id)
            if data:
                data.status = TrainingDataStatus.USED
                await self.repo.update(data)


class TrainingOrchestrator:
    """
    학습 오케스트레이터.
    학습 작업 생성·모니터링·모델 버전 관리. 실제 학습은 training.examination.civil_law.train_simple 호출.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.data_repo = TrainingDataRepository(session)
        self.job_repo = TrainingJobRepository(session)
        self.version_repo = ModelVersionRepository(session)

    async def check_auto_training_trigger(self, min_data_count: int = 10) -> bool:
        pending_count = await self.data_repo.count(status=TrainingDataStatus.PENDING)
        return pending_count >= min_data_count

    async def start_training(
        self,
        job_name: str,
        config: Dict[str, Any],
        training_data_ids: Optional[List[str]] = None,
        auto_trigger: bool = False
    ) -> TrainingJob:
        if training_data_ids:
            training_data_list = []
            for data_id in training_data_ids:
                data = await self.data_repo.get_by_id(data_id)
                if data and data.status == TrainingDataStatus.PENDING:
                    training_data_list.append(data)
        else:
            training_data_list = await self.data_repo.get_all(status=TrainingDataStatus.PENDING)

        if not training_data_list:
            raise ValueError("학습할 데이터가 없습니다.")

        job = TrainingJob(
            id=str(uuid.uuid4()),
            job_name=job_name,
            status=TrainingJobStatus.PENDING,
            config=config,
            training_data_ids=[d.id for d in training_data_list],
            train_size=len(training_data_list),
            total_epochs=config.get("num_train_epochs", 3),
            started_at=datetime.utcnow()
        )
        job = await self.job_repo.create(job)
        asyncio.create_task(self._run_training(job, training_data_list))
        logger.info(f"학습 작업 시작: job_id={job.id}, data_count={len(training_data_list)}")
        return job

    async def _run_training(self, job: TrainingJob, training_data_list: List[TrainingData]):
        try:
            job.status = TrainingJobStatus.RUNNING
            await self.job_repo.update(job)

            data_dir = PROJECT_ROOT / "data" / "processed" / "civil_law"
            data_dir.mkdir(parents=True, exist_ok=True)

            train_samples = []
            for idx, data in enumerate(training_data_list, start=1001):
                train_samples.append({
                    "id": idx,
                    "problem": data.problem_text,
                    "reference_answer": data.reference_answer_text,
                    "user_answer": data.user_answer_text,
                    "labels": data.labels
                })

            train_path = data_dir / f"train_{job.id}.jsonl"
            with open(train_path, 'w', encoding='utf-8') as f:
                for sample in train_samples:
                    f.write(json.dumps(sample, ensure_ascii=False) + '\n')

            val_size = max(1, len(train_samples) // 5)
            val_samples = train_samples[:val_size]
            train_samples = train_samples[val_size:]
            for idx, sample in enumerate(val_samples, start=2001):
                sample["id"] = idx

            val_path = data_dir / f"val_{job.id}.jsonl"
            with open(val_path, 'w', encoding='utf-8') as f:
                for sample in val_samples:
                    f.write(json.dumps(sample, ensure_ascii=False) + '\n')

            job.train_size = len(train_samples)
            job.val_size = len(val_samples)
            await self.job_repo.update(job)

            from training.examination.civil_law.train_simple import train_model

            output_dir = PROJECT_ROOT / "artifacts" / "models" / "finetuned" / "legal" / f"checkpoint_{job.id}"
            output_dir.mkdir(parents=True, exist_ok=True)
            num_epochs = job.config.get("num_train_epochs", 2)
            batch_size = job.config.get("per_device_train_batch_size", 1)
            learning_rate = job.config.get("learning_rate", 2e-5)
            base_model_path = job.config.get("base_model_path", None)
            progress_file = output_dir / "progress.json"

            monitor_task = asyncio.create_task(self._monitor_training_progress(job, progress_file))
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                train_model,
                str(train_path),
                str(val_path),
                str(output_dir),
                base_model_path,
                num_epochs,
                batch_size,
                learning_rate,
                str(progress_file)
            )

            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

            if result and result.get("success"):
                job.status = TrainingJobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.progress = 1.0
                job.metrics = result.get("metrics", {})
                final_model_path = output_dir / "final"
                job.model_path = str(final_model_path)
                version = await self._create_model_version(job, final_model_path)
                data_service = TrainingDataService(self.session)
                await data_service.mark_as_used([d.id for d in training_data_list])
                logger.info(f"학습 완료: job_id={job.id}, model_version={version.version}")
                auto_feedback = job.config.get("auto_feedback", False)
                if auto_feedback:
                    asyncio.create_task(self._run_auto_feedback(job, training_data_list))
            else:
                job.status = TrainingJobStatus.FAILED
                error_msg = result.get("error", "알 수 없는 오류") if result else "학습 결과를 받지 못함"
                job.error_message = str(error_msg)[:1000]
                if result and "traceback" in result:
                    job.error_traceback = result["traceback"][:5000]
                logger.error(f"학습 실패: job_id={job.id}, error={job.error_message}")

            await self.job_repo.update(job)
        except Exception as e:
            job.status = TrainingJobStatus.FAILED
            job.error_message = str(e)
            import traceback
            job.error_traceback = traceback.format_exc()
            await self.job_repo.update(job)
            logger.error(f"학습 중 예외 발생: job_id={job.id}, error={e}")

    async def _monitor_training_progress(self, job: TrainingJob, progress_file: Path):
        while True:
            try:
                await asyncio.sleep(5)
                if not progress_file.exists():
                    continue
                try:
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)
                    job.current_epoch = progress_data.get("current_epoch", 0)
                    job.progress = progress_data.get("progress", 0.0)
                    if "loss" in progress_data:
                        if job.loss_history is None:
                            job.loss_history = []
                        job.loss_history.append({
                            "epoch": progress_data.get("current_epoch", 0),
                            "loss": progress_data.get("loss", 0.0)
                        })
                    await self.job_repo.update(job)
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"진행률 파일 읽기 실패: {e}")
                    continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"진행률 모니터링 중 오류: {e}")
                await asyncio.sleep(5)

    async def _create_model_version(self, job: TrainingJob, model_path: Path) -> ModelVersion:
        latest_version = await self.version_repo.get_all(limit=1)
        if latest_version:
            last_version_str = latest_version[0].version
            try:
                version_num = int(last_version_str.split('.')[-1]) + 1
                new_version = f"v1.0.{version_num}"
            except Exception:
                new_version = f"v1.0.{len(latest_version) + 1}"
        else:
            new_version = "v1.0.0"

        active_version = await self.version_repo.get_active()
        if active_version:
            active_version.is_active = False
            active_version.status = ModelVersionStatus.ARCHIVED
            await self.version_repo.update(active_version)

        version = ModelVersion(
            id=str(uuid.uuid4()),
            training_job_id=job.id,
            version=new_version,
            model_path=str(model_path),
            base_model=job.config.get("base_model", "exaone-2.4b"),
            status=ModelVersionStatus.ACTIVE,
            is_active=True,
            metrics=job.metrics,
            training_config=job.config,
            data_info={
                "train_size": job.train_size,
                "val_size": job.val_size,
                "training_data_ids": job.training_data_ids
            }
        )
        version = await self.version_repo.create(version)
        try:
            from app.core.ml.model_loader import ModelLoader
            loader = ModelLoader.get_instance()
            base_model_path = job.config.get("base_model_path") or "artifacts/models/base/exaone-2.4b"
            reload_success = loader.reload(model_path=str(model_path), base_model_path=base_model_path)
            if reload_success:
                logger.info(f"ModelLoader 리로드 완료: model_path={model_path}")
            else:
                logger.warning(f"ModelLoader 리로드 실패: model_path={model_path}")
        except Exception as e:
            logger.warning(f"ModelLoader 리로드 중 오류: {e}")
        return version

    async def get_job_status(self, job_id: str) -> Optional[TrainingJob]:
        return await self.job_repo.get_by_id(job_id)

    async def get_latest_job(self) -> Optional[TrainingJob]:
        return await self.job_repo.get_latest()

    async def _run_auto_feedback(self, job: TrainingJob, training_data_list: List[TrainingData]):
        try:
            logger.info(f"자동 첨삭 시작: job_id={job.id}, data_count={len(training_data_list)}")
            valid_data = [
                d for d in training_data_list
                if d.problem_id and d.reference_answer_id and d.user_answer_id
            ]
            if not valid_data:
                logger.info(f"자동 첨삭 스킵: ID 참조가 있는 데이터가 없음 (job_id={job.id})")
                return
            sample_size = min(5, len(valid_data))
            sample_data = valid_data[:sample_size]
            logger.info(f"자동 첨삭 실행: {sample_size}개 데이터로 새 모델 검증")

            from app.domain.v1.minso.spokes.services.reasoning_service import ReasoningEngine
            from app.domain.v1.minso.spokes.services.feedback_service import FeedbackGenerator

            reasoning_engine = ReasoningEngine(self.session)
            feedback_generator = FeedbackGenerator(self.session)
            feedback_count = 0
            for data in sample_data:
                try:
                    analysis_result = await reasoning_engine.analyze_issues(
                        user_answer_id=data.user_answer_id,
                        reference_answer_id=data.reference_answer_id,
                        problem_id=data.problem_id,
                        save_result=True
                    )
                    reasoning_task_id = analysis_result.task_id
                    if reasoning_task_id:
                        await feedback_generator.generate_from_reasoning(
                            user_answer_id=data.user_answer_id,
                            reasoning_task_id=reasoning_task_id,
                            feedback_type="comprehensive",
                            include_suggestions=True
                        )
                        feedback_count += 1
                        logger.info(f"피드백 생성 완료: user_answer_id={data.user_answer_id}")
                    else:
                        logger.warning(f"추론 작업 ID를 찾을 수 없음: user_answer_id={data.user_answer_id}")
                except Exception as e:
                    logger.warning(f"자동 첨삭 실패 (데이터 ID: {data.id}): {e}")
                    continue
            logger.info(f"자동 첨삭 완료: job_id={job.id}, 생성된 피드백={feedback_count}개")
        except Exception as e:
            logger.warning(f"자동 첨삭 중 오류 발생 (job_id={job.id}): {e}")
