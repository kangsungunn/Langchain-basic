"""
Training - Repositories (루트 training/ 폴더)

학습 데이터 및 작업 데이터 접근 계층.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from training.models import (
    TrainingData, TrainingJob, ModelVersion,
    TrainingDataStatus, TrainingJobStatus, ModelVersionStatus
)


class TrainingDataRepository:
    """학습 데이터 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: TrainingData) -> TrainingData:
        self.session.add(data)
        await self.session.commit()
        await self.session.refresh(data)
        return data

    async def get_by_id(self, data_id: str) -> Optional[TrainingData]:
        result = await self.session.execute(
            select(TrainingData).where(TrainingData.id == data_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        status: Optional[TrainingDataStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TrainingData]:
        query = select(TrainingData)
        if status:
            query = query.where(TrainingData.status == status)
        query = query.order_by(TrainingData.created_at.desc())
        if limit:
            query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, status: Optional[TrainingDataStatus] = None) -> int:
        query = select(func.count(TrainingData.id))
        if status:
            query = query.where(TrainingData.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update(self, data: TrainingData) -> TrainingData:
        await self.session.commit()
        await self.session.refresh(data)
        return data

    async def delete(self, data: TrainingData):
        await self.session.delete(data)
        await self.session.commit()


class TrainingJobRepository:
    """학습 작업 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, job: TrainingJob) -> TrainingJob:
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: str) -> Optional[TrainingJob]:
        result = await self.session.execute(
            select(TrainingJob)
            .options(selectinload(TrainingJob.model_versions))
            .where(TrainingJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        status: Optional[TrainingJobStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TrainingJob]:
        query = select(TrainingJob).options(selectinload(TrainingJob.model_versions))
        if status:
            query = query.where(TrainingJob.status == status)
        query = query.order_by(TrainingJob.created_at.desc())
        if limit:
            query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest(self) -> Optional[TrainingJob]:
        result = await self.session.execute(
            select(TrainingJob)
            .options(selectinload(TrainingJob.model_versions))
            .order_by(TrainingJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, job: TrainingJob) -> TrainingJob:
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def delete(self, job: TrainingJob):
        await self.session.delete(job)
        await self.session.commit()


class ModelVersionRepository:
    """모델 버전 리포지토리"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, version: ModelVersion) -> ModelVersion:
        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def get_by_id(self, version_id: str) -> Optional[ModelVersion]:
        result = await self.session.execute(
            select(ModelVersion)
            .options(selectinload(ModelVersion.training_job))
            .where(ModelVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_by_version(self, version: str) -> Optional[ModelVersion]:
        result = await self.session.execute(
            select(ModelVersion)
            .options(selectinload(ModelVersion.training_job))
            .where(ModelVersion.version == version)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> Optional[ModelVersion]:
        result = await self.session.execute(
            select(ModelVersion)
            .options(selectinload(ModelVersion.training_job))
            .where(ModelVersion.is_active == True)
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        status: Optional[ModelVersionStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ModelVersion]:
        query = select(ModelVersion).options(selectinload(ModelVersion.training_job))
        if status:
            query = query.where(ModelVersion.status == status)
        query = query.order_by(ModelVersion.created_at.desc())
        if limit:
            query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, version: ModelVersion) -> ModelVersion:
        await self.session.commit()
        await self.session.refresh(version)
        return version
