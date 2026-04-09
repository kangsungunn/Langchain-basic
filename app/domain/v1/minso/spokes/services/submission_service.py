"""
Submission Spoke - 서비스 (Star 토폴로지 말단)

사용자 답안·구조 분석·OCR 비즈니스 로직.
단일 소스: 이 파일. submission/services.py 는 re-export.
"""

import uuid
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.v1.minso.models import UserAnswer, AnswerStructure, SubmissionType, SubmissionStatus
from app.domain.v1.minso.hub.repositories import UserAnswerRepository, AnswerStructureRepository
from app.domain.v1.minso.models.transfers import (
    UserAnswerCreateText, UserAnswerCreateImage, UserAnswerUpdate, UserAnswerResponse,
    AnswerStructureResponse, StructureAnalysisResponse, OCRResponse,
    ParagraphInfo, SentenceInfo,
)
from app.domain.v1.minso.shared import EntityNotFoundError, DomainValidationError
from app.domain.v1.minso.shared.value_objects import ENTITY_USER_ANSWER


class UserAnswerService:
    """사용자 답안 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserAnswerRepository(session)

    async def create_text_answer(self, data: UserAnswerCreateText) -> UserAnswerResponse:
        """텍스트 답안 생성"""
        answer = UserAnswer(
            id=str(uuid.uuid4()),
            problem_id=data.problem_id,
            submission_type=SubmissionType.TEXT,
            status=SubmissionStatus.COMPLETED,
            raw_content=data.content,
            processed_content=data.content
        )

        created = await self.repo.create(answer)
        return UserAnswerResponse(
            id=created.id,
            problem_id=created.problem_id,
            submission_type=created.submission_type.value,
            status=created.status.value,
            raw_content=created.raw_content,
            processed_content=created.processed_content,
            meta=created.meta,
            created_at=created.created_at,
            updated_at=created.updated_at,
            structure=None
        )

    async def create_image_answer(self, data: UserAnswerCreateImage) -> UserAnswerResponse:
        """이미지 답안 생성"""
        answer = UserAnswer(
            id=str(uuid.uuid4()),
            problem_id=data.problem_id,
            submission_type=SubmissionType.IMAGE,
            status=SubmissionStatus.PENDING,
            raw_content=data.image_path,
            processed_content=None,
            meta=data.meta
        )

        created = await self.repo.create(answer)
        await self.session.refresh(created)

        now = datetime.utcnow()
        created_at = created.created_at if created.created_at else now
        updated_at = created.updated_at if created.updated_at else now

        return UserAnswerResponse(
            id=created.id,
            problem_id=created.problem_id,
            submission_type=created.submission_type.value,
            status=created.status.value,
            raw_content=created.raw_content,
            processed_content=created.processed_content,
            meta=created.meta,
            created_at=created_at,
            updated_at=updated_at,
            structure=None
        )

    async def get_answer(self, answer_id: str) -> Optional[UserAnswerResponse]:
        """사용자 답안 조회"""
        answer = await self.repo.get_by_id(answer_id)
        if not answer:
            return None
        return UserAnswerResponse.from_orm(answer)

    async def get_answers_by_problem(self, problem_id: str, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """문제의 모든 사용자 답안 조회"""
        answers = await self.repo.get_by_problem_id(problem_id, skip=skip, limit=limit)
        total = await self.repo.count_by_problem(problem_id)

        return {
            "total": total,
            "items": [UserAnswerResponse.from_orm(a) for a in answers]
        }

    async def get_all_answers(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """모든 사용자 답안 조회"""
        answers = await self.repo.get_all(skip=skip, limit=limit)
        total = await self.repo.count()

        return {
            "total": total,
            "items": [UserAnswerResponse.from_orm(a) for a in answers]
        }

    async def update_answer(self, answer_id: str, data: UserAnswerUpdate) -> Optional[UserAnswerResponse]:
        """사용자 답안 수정"""
        answer = await self.repo.get_by_id(answer_id)
        if not answer:
            return None

        if data.processed_content is not None:
            answer.processed_content = data.processed_content
        if data.status is not None:
            answer.status = SubmissionStatus(data.status)
        if data.meta is not None:
            answer.meta = data.meta

        updated = await self.repo.update(answer)
        return UserAnswerResponse.from_orm(updated)

    async def delete_answer(self, answer_id: str) -> bool:
        """사용자 답안 삭제"""
        answer = await self.repo.get_by_id(answer_id)
        if not answer:
            return False

        await self.repo.delete(answer)
        return True


class AnswerStructureService:
    """답안 구조 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AnswerStructureRepository(session)
        self.answer_repo = UserAnswerRepository(session)

    async def analyze_structure(
        self,
        user_answer_id: str,
        auto_save: bool = True
    ) -> StructureAnalysisResponse:
        """답안 구조 분석"""
        answer = await self.answer_repo.get_by_id(user_answer_id)
        if not answer:
            raise EntityNotFoundError(ENTITY_USER_ANSWER, user_answer_id)

        if not answer.processed_content:
            raise DomainValidationError(f"처리된 텍스트가 없습니다: {user_answer_id}")

        text = answer.processed_content
        paragraphs = self._split_paragraphs(text)
        sentences = self._split_sentences(paragraphs)

        paragraph_count = {"total": len(paragraphs)}
        sentence_count = {
            "total": sum(len(p["sentences"]) for p in paragraphs),
            "per_paragraph": [len(p["sentences"]) for p in paragraphs]
        }
        word_count = {"total": len(text.split())}

        if auto_save:
            await self.repo.delete_by_user_answer_id(user_answer_id)

            structure = AnswerStructure(
                id=str(uuid.uuid4()),
                user_answer_id=user_answer_id,
                paragraphs=[
                    {"order": p["order"], "content": p["content"]}
                    for p in paragraphs
                ],
                sentences=sentences,
                paragraph_count=paragraph_count,
                sentence_count=sentence_count,
                word_count=word_count
            )

            created = await self.repo.create(structure)
            structure_response = AnswerStructureResponse.from_orm(created)
        else:
            structure_response = AnswerStructureResponse(
                id=str(uuid.uuid4()),
                user_answer_id=user_answer_id,
                paragraphs=[
                    ParagraphInfo(order=p["order"], content=p["content"])
                    for p in paragraphs
                ],
                sentences=[SentenceInfo(**s) for s in sentences],
                paragraph_count=paragraph_count,
                sentence_count=sentence_count,
                word_count=word_count,
                created_at=answer.created_at,
                updated_at=answer.updated_at
            )

        return StructureAnalysisResponse(
            user_answer_id=user_answer_id,
            structure=structure_response,
            analysis_summary={
                "total_paragraphs": paragraph_count["total"],
                "total_sentences": sentence_count["total"],
                "total_words": word_count["total"],
                "avg_sentences_per_paragraph": round(sentence_count["total"] / max(paragraph_count["total"], 1), 2)
            }
        )

    def _split_paragraphs(self, text: str) -> List[Dict[str, Any]]:
        """텍스트를 문단으로 분리"""
        raw_paragraphs = text.split('\n\n')
        paragraphs = []

        for i, para in enumerate(raw_paragraphs, start=1):
            para = para.strip()
            if para:
                sentences = re.split(r'(?<=[.?!])\s+', para)
                sentences = [s.strip() for s in sentences if s.strip()]

                paragraphs.append({
                    "order": i,
                    "content": para,
                    "sentences": sentences
                })

        return paragraphs

    def _split_sentences(self, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """문단에서 문장 추출"""
        all_sentences = []
        sentence_order = 1

        for para in paragraphs:
            for sent in para["sentences"]:
                all_sentences.append({
                    "paragraph": para["order"],
                    "order": sentence_order,
                    "content": sent
                })
                sentence_order += 1

        return all_sentences

    async def get_structure(self, user_answer_id: str) -> Optional[AnswerStructureResponse]:
        """답안 구조 조회"""
        structure = await self.repo.get_by_user_answer_id(user_answer_id)
        if not structure:
            return None
        return AnswerStructureResponse.from_orm(structure)


class OCRService:
    """OCR 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.answer_repo = UserAnswerRepository(session)

    async def process_ocr(
        self,
        user_answer_id: str,
        confidence_threshold: float = 0.6
    ) -> OCRResponse:
        """이미지 OCR 처리 (더미 구현)"""
        answer = await self.answer_repo.get_by_id(user_answer_id)
        if not answer:
            raise EntityNotFoundError(ENTITY_USER_ANSWER, user_answer_id)

        if answer.submission_type != SubmissionType.IMAGE:
            raise DomainValidationError(f"이미지 답안이 아닙니다: {user_answer_id}")

        dummy_text = """갑은 을에게 금전을 대여하였으나 변제기가 도과하였음에도 을이 변제하지 않고 있다.

이에 갑은 을을 상대로 대여금 청구의 소를 제기하고자 한다.

이 사건에서 문제되는 법률관계를 검토하시오."""

        dummy_confidence = 0.85

        answer.processed_content = dummy_text
        answer.status = SubmissionStatus.COMPLETED
        answer.meta = {
            "ocr_confidence": dummy_confidence,
            "ocr_engine": "dummy",
            "image_path": answer.raw_content
        }

        await self.answer_repo.update(answer)

        return OCRResponse(
            user_answer_id=user_answer_id,
            extracted_text=dummy_text,
            confidence=dummy_confidence,
            status=SubmissionStatus.COMPLETED.value,
            meta=answer.meta
        )
