"""
Minso Hub - 단순 라우터

모든 요청을 받아서 정책/규칙을 자동 판단하고 적절히 라우팅합니다.
- 정책: 도메인별 오케스트레이터로 위임
- 규칙: 서비스로 직접 라우팅
"""

import inspect
from typing import Any, Dict, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.v1.minso.hub.decision_maker import DecisionMaker
from app.domain.v1.minso.shared import DomainValidationError
from app.domain.v1.minso.hub.mcp import get_minso_central_mcp_server
from app.core.utils.logger import get_logger

logger = get_logger()


class MinsoHub:
    """
    Minso 도메인 Hub (단순 라우터)

    모든 요청을 받아서 정책/규칙을 자동 판단하고 적절히 라우팅합니다.
    - 정책: 도메인별 오케스트레이터로 처리
    - 규칙: 서비스로 직접 라우팅
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.decision_maker = DecisionMaker()
        self._orchestrator_map: Dict[str, Any] = {}
        self._service_map: Dict[str, Type] = {}

    def _get_orchestrator_map(self) -> Dict[str, Any]:
        """
        오케스트레이터 매핑 가져오기 (lazy import)

        정책 기반 요청을 처리할 오케스트레이터 인스턴스를 매핑합니다.
        """
        if not self._orchestrator_map:
            # Lazy import로 순환 참조 방지
            from app.domain.v1.minso.hub.orchestrators.reasoning_orchestrator import ReasoningHub
            from app.domain.v1.minso.hub.orchestrators.feedback_orchestrator import FeedbackOrchestrator

            self._orchestrator_map = {
                "reasoning": ReasoningHub(self.session),
                "feedback": FeedbackOrchestrator(self.session),
            }
        return self._orchestrator_map

    def _get_service_map(self) -> Dict[str, Type]:
        """
        서비스 매핑 가져오기 (lazy import)

        규칙 기반 요청을 처리할 서비스 클래스를 매핑합니다.
        """
        if not self._service_map:
            # Lazy import로 순환 참조 방지
            from training.services import TrainingDataService
            from app.domain.v1.minso.spokes.services.submission_service import UserAnswerService
            from app.domain.v1.minso.spokes.services.reasoning_service import ReasoningTaskService
            from app.domain.v1.minso.spokes.services.feedback_service import FeedbackService

            self._service_map = {
                "training": TrainingDataService,
                "submission": UserAnswerService,
                "reasoning": ReasoningTaskService,
                "feedback": FeedbackService,
            }
        return self._service_map

    async def process(
        self,
        domain: str,
        action: str,
        request: Any
    ) -> Any:
        """
        요청 처리 (정책/규칙 자동 판단 후 라우팅)

        Args:
            domain: 도메인 이름 (예: "training", "reasoning")
            action: 액션 이름 (예: "create_training_data", "comprehensive_analysis")
            request: 요청 데이터

        Returns:
            처리 결과
        """
        logger.info("=" * 80)
        logger.info(f"[MINSO HUB] 요청 처리 시작")
        logger.info(f"   └─ 도메인: {domain}")
        logger.info(f"   └─ 액션: {action}")
        logger.info("=" * 80)

        try:
            # 1. 정책/규칙 판단 (DecisionMaker)
            strategy = await self.decision_maker.decide(domain, action, request)

            logger.info(f"[MINSO HUB] 판단 결과: {strategy}")

            # 2. 정책이면 → 오케스트레이터로 처리
            if strategy == "policy":
                return await self._handle_policy(domain, action, request)

            # 3. 규칙이면 → 서비스로 직접 라우팅
            else:
                return await self._handle_rule(domain, action, request)

        except Exception as e:
            logger.error("=" * 80)
            logger.error("[FAIL] Minso Hub 처리 실패")
            logger.error(f"   └─ 도메인: {domain}")
            logger.error(f"   └─ 액션: {action}")
            logger.error(f"   └─ 오류: {e}")
            logger.error("=" * 80)
            raise

    async def _handle_policy(
        self,
        domain: str,
        action: str,
        request: Any
    ) -> Any:
        """정책 기반 요청 처리 (도메인별 오케스트레이터로 라우팅)"""
        logger.info(f"[POLICY] 정책 기반 처리: {domain}.{action}")

        # 도메인별 오케스트레이터 매핑에서 가져오기
        orchestrator_map = self._get_orchestrator_map()
        orchestrator = orchestrator_map.get(domain)

        if not orchestrator:
            raise DomainValidationError(
                f"정책 기반 요청을 처리할 오케스트레이터가 없습니다: {domain}"
            )

        # 오케스트레이터로 위임
        return await orchestrator.process(domain, action, request)

    async def _handle_rule(
        self,
        domain: str,
        action: str,
        request: Any
    ) -> Any:
        """규칙 기반 요청 처리 (서비스 직접 호출)"""
        logger.info(f"[RULE] 규칙 기반 처리: {domain}.{action}")

        # 서비스 매핑에서 서비스 클래스 가져오기
        service_map = self._get_service_map()
        service_class = service_map.get(domain)

        if not service_class:
            raise DomainValidationError(f"알 수 없는 도메인: {domain}")

        # 서비스 인스턴스 생성
        service = service_class(self.session)

        # 액션 이름 매핑 (API 액션 → 서비스 메서드)
        # 매핑이 없으면 액션 이름을 그대로 서비스 메서드 이름으로 사용합니다.
        action_mapping = {
            "training": {
                "create_training_data": "create",
            },
            "submission": {
                "create_text_answer": "create_text_answer",
                "create_image_answer": "create_image_answer",
            },
            "reasoning": {
                "create_task": "create_task",
            },
        }

        # 액션 이름 매핑 확인
        service_method_name = action_mapping.get(domain, {}).get(action, action)

        # 액션에 해당하는 메서드 가져오기
        method = getattr(service, service_method_name, None)

        if not method:
            raise DomainValidationError(
                f"알 수 없는 액션: {domain}.{action} (서비스: {service_class.__name__}, 메서드: {service_method_name})"
            )

        if not callable(method):
            raise DomainValidationError(
                f"호출 가능한 메서드가 아닙니다: {domain}.{action} (서비스: {service_class.__name__}, 속성: {service_method_name})"
            )

        # 메서드 호출 (async/sync 자동 판단)
        if inspect.iscoroutinefunction(method):
            result = await method(request)
        else:
            result = method(request)

        logger.info(f"[OK] 규칙 기반 처리 완료: {domain}.{action}")
        return result

    async def trigger_embedding_migration(
        self,
        domain: str,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        임베딩 마이그레이션 트리거

        지정된 도메인의 모든 데이터에 대해 임베딩을 생성하고 저장합니다.
        MCP 서버의 koelectra_embed_text 툴을 사용합니다.

        Args:
            domain: 도메인 이름 ("feedback", "reference", "submission", "reasoning")
            batch_size: 배치 크기 (한 번에 처리할 레코드 수)

        Returns:
            {
                "success": bool,
                "domain": str,
                "total_processed": int,
                "total_saved": int,
                "errors": List[str]
            }
        """
        logger.info("=" * 80)
        logger.info(f"[EMBEDDING MIGRATION] 시작")
        logger.info(f"   └─ 도메인: {domain}")
        logger.info(f"   └─ 배치 크기: {batch_size}")
        logger.info("=" * 80)

        try:
            # 중앙 MCP 서버 가져오기
            mcp_server = get_minso_central_mcp_server()

            # 도메인별 처리 로직
            if domain == "feedback":
                return await self._migrate_feedback_embeddings(mcp_server, batch_size)
            elif domain == "reference":
                return await self._migrate_reference_embeddings(mcp_server, batch_size)
            elif domain == "submission":
                return await self._migrate_submission_embeddings(mcp_server, batch_size)
            elif domain == "reasoning":
                return await self._migrate_reasoning_embeddings(mcp_server, batch_size)
            else:
                raise DomainValidationError(f"지원하지 않는 도메인: {domain}")

        except Exception as e:
            logger.error("=" * 80)
            logger.error("[FAIL] 임베딩 마이그레이션 실패")
            logger.error(f"   └─ 도메인: {domain}")
            logger.error(f"   └─ 오류: {e}")
            logger.error("=" * 80)
            raise

    async def embed_one(self, domain: str, entity_id: str) -> Dict[str, Any]:
        """
        단일 엔티티에 대해 임베딩 1건 생성 후 저장 (Phase 2: 자동 임베딩).

        Args:
            domain: "feedback" | "reference" | "submission" | "reasoning"
            entity_id: 해당 도메인 엔티티 ID (feedback_id, reference_answer_id, user_answer_id, reasoning_task_id)

        Returns:
            {"success": bool, "domain": str, "entity_id": str, "error": str | None}
        """
        mcp_server = get_minso_central_mcp_server()
        try:
            if domain == "feedback":
                return await self._embed_one_feedback(mcp_server, entity_id)
            elif domain == "reference":
                return await self._embed_one_reference(mcp_server, entity_id)
            elif domain == "submission":
                return await self._embed_one_submission(mcp_server, entity_id)
            elif domain == "reasoning":
                return await self._embed_one_reasoning(mcp_server, entity_id)
            else:
                raise DomainValidationError(f"지원하지 않는 도메인: {domain}")
        except Exception as e:
            logger.error(f"[embed_one] {domain} {entity_id}: {e}")
            return {"success": False, "domain": domain, "entity_id": entity_id, "error": str(e)}

    async def _embed_one_feedback(self, mcp_server, feedback_id: str) -> Dict[str, Any]:
        from app.domain.v1.minso.models import Feedback, FeedbackEmbedding

        result = await self.session.execute(
            select(Feedback).where(Feedback.id == feedback_id).options(selectinload(Feedback.items))
        )
        feedback = result.scalar_one_or_none()
        if not feedback:
            return {"success": False, "domain": "feedback", "entity_id": feedback_id, "error": "Feedback not found"}
        content = self._build_feedback_text(feedback)
        tool_result = await mcp_server.call_tool("koelectra_embed_text", text=content)
        if not tool_result.get("success") or not tool_result.get("embedding"):
            return {"success": False, "domain": "feedback", "entity_id": feedback_id, "error": tool_result.get("error", "embedding failed")}
        self.session.add(FeedbackEmbedding(feedback_id=feedback_id, content=content, embedding=tool_result["embedding"]))
        await self.session.commit()
        logger.info(f"[embed_one] Feedback {feedback_id} 임베딩 저장 완료")
        return {"success": True, "domain": "feedback", "entity_id": feedback_id, "error": None}

    async def _embed_one_reference(self, mcp_server, reference_answer_id: str) -> Dict[str, Any]:
        from app.domain.v1.minso.models import ReferenceAnswer, ReferenceAnswerEmbedding

        result = await self.session.execute(select(ReferenceAnswer).where(ReferenceAnswer.id == reference_answer_id))
        ra = result.scalar_one_or_none()
        if not ra:
            return {"success": False, "domain": "reference", "entity_id": reference_answer_id, "error": "ReferenceAnswer not found"}
        content = self._build_reference_text(ra)
        tool_result = await mcp_server.call_tool("koelectra_embed_text", text=content)
        if not tool_result.get("success") or not tool_result.get("embedding"):
            return {"success": False, "domain": "reference", "entity_id": reference_answer_id, "error": tool_result.get("error", "embedding failed")}
        self.session.add(ReferenceAnswerEmbedding(reference_answer_id=reference_answer_id, content=content, embedding=tool_result["embedding"]))
        await self.session.commit()
        logger.info(f"[embed_one] ReferenceAnswer {reference_answer_id} 임베딩 저장 완료")
        return {"success": True, "domain": "reference", "entity_id": reference_answer_id, "error": None}

    async def _embed_one_submission(self, mcp_server, user_answer_id: str) -> Dict[str, Any]:
        from app.domain.v1.minso.models import UserAnswer, UserAnswerEmbedding

        result = await self.session.execute(select(UserAnswer).where(UserAnswer.id == user_answer_id))
        ua = result.scalar_one_or_none()
        if not ua:
            return {"success": False, "domain": "submission", "entity_id": user_answer_id, "error": "UserAnswer not found"}
        content = self._build_submission_text(ua)
        tool_result = await mcp_server.call_tool("koelectra_embed_text", text=content)
        if not tool_result.get("success") or not tool_result.get("embedding"):
            return {"success": False, "domain": "submission", "entity_id": user_answer_id, "error": tool_result.get("error", "embedding failed")}
        self.session.add(UserAnswerEmbedding(user_answer_id=user_answer_id, content=content, embedding=tool_result["embedding"]))
        await self.session.commit()
        logger.info(f"[embed_one] UserAnswer {user_answer_id} 임베딩 저장 완료")
        return {"success": True, "domain": "submission", "entity_id": user_answer_id, "error": None}

    async def _embed_one_reasoning(self, mcp_server, reasoning_task_id: str) -> Dict[str, Any]:
        from app.domain.v1.minso.models import ReasoningTask, ReasoningTaskEmbedding

        result = await self.session.execute(select(ReasoningTask).where(ReasoningTask.id == reasoning_task_id))
        rt = result.scalar_one_or_none()
        if not rt:
            return {"success": False, "domain": "reasoning", "entity_id": reasoning_task_id, "error": "ReasoningTask not found"}
        content = self._build_reasoning_text(rt)
        tool_result = await mcp_server.call_tool("koelectra_embed_text", text=content)
        if not tool_result.get("success") or not tool_result.get("embedding"):
            return {"success": False, "domain": "reasoning", "entity_id": reasoning_task_id, "error": tool_result.get("error", "embedding failed")}
        self.session.add(ReasoningTaskEmbedding(reasoning_task_id=reasoning_task_id, content=content, embedding=tool_result["embedding"]))
        await self.session.commit()
        logger.info(f"[embed_one] ReasoningTask {reasoning_task_id} 임베딩 저장 완료")
        return {"success": True, "domain": "reasoning", "entity_id": reasoning_task_id, "error": None}

    async def _migrate_feedback_embeddings(
        self,
        mcp_server,
        batch_size: int
    ) -> Dict[str, Any]:
        """Feedback 도메인 임베딩 마이그레이션"""
        from app.domain.v1.minso.models import Feedback, FeedbackEmbedding

        total_processed = 0
        total_saved = 0
        errors = []

        try:
            offset = 0
            while True:
                result = await self.session.execute(
                    select(Feedback).offset(offset).limit(batch_size)
                )
                feedbacks = result.scalars().all()
                if not feedbacks:
                    break
                for feedback in feedbacks:
                    try:
                        content = self._build_feedback_text(feedback)
                        tool_result = await mcp_server.call_tool(
                            "koelectra_embed_text",
                            text=content
                        )
                        if not tool_result.get("success", False):
                            errors.append(f"Feedback {feedback.id}: 임베딩 생성 실패 - {tool_result.get('error', 'Unknown error')}")
                            continue
                        embedding = tool_result.get("embedding")
                        if not embedding:
                            errors.append(f"Feedback {feedback.id}: embedding 없음")
                            continue
                        self.session.add(FeedbackEmbedding(
                            feedback_id=feedback.id,
                            content=content,
                            embedding=embedding
                        ))
                        total_saved += 1
                        total_processed += 1
                    except Exception as e:
                        errors.append(f"Feedback {feedback.id}: {str(e)}")
                        logger.error(f"[ERROR] Feedback {feedback.id} 임베딩 실패: {e}")
                offset += batch_size
                await self.session.commit()

            logger.info(f"[OK] Feedback 임베딩 마이그레이션 완료: {total_processed}개 처리, {total_saved}개 저장")

            return {
                "success": True,
                "domain": "feedback",
                "total_processed": total_processed,
                "total_saved": total_saved,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"[ERROR] Feedback 임베딩 마이그레이션 실패: {e}")
            raise

    def _build_feedback_text(self, feedback) -> str:
        """Feedback 엔티티를 임베딩할 텍스트로 변환"""
        parts = []

        if feedback.summary:
            parts.append(f"요약: {feedback.summary}")

        if feedback.strengths:
            strengths_text = ", ".join(feedback.strengths) if isinstance(feedback.strengths, list) else str(feedback.strengths)
            parts.append(f"강점: {strengths_text}")

        if feedback.weaknesses:
            weaknesses_text = ", ".join(feedback.weaknesses) if isinstance(feedback.weaknesses, list) else str(feedback.weaknesses)
            parts.append(f"약점: {weaknesses_text}")

        # FeedbackItem이 있으면 추가
        if hasattr(feedback, 'items') and feedback.items:
            item_texts = []
            for item in feedback.items:
                item_parts = []
                if item.title:
                    item_parts.append(item.title)
                if item.description:
                    item_parts.append(item.description)
                if item.suggestion:
                    item_parts.append(f"제안: {item.suggestion}")
                if item_parts:
                    item_texts.append(" | ".join(item_parts))
            if item_texts:
                parts.append("피드백 항목: " + " / ".join(item_texts))

        return "\n".join(parts) if parts else f"피드백 ID: {feedback.id}"

    def _build_reference_text(self, reference_answer) -> str:
        """ReferenceAnswer 엔티티를 임베딩할 텍스트로 변환"""
        parts = []
        if reference_answer.content:
            parts.append(reference_answer.content)
        if reference_answer.structure:
            if isinstance(reference_answer.structure, dict):
                parts.append("구조: " + str(reference_answer.structure))
            else:
                parts.append(f"구조: {reference_answer.structure}")
        return "\n".join(parts) if parts else f"모범답안 ID: {reference_answer.id}"

    async def _migrate_reference_embeddings(
        self,
        mcp_server,
        batch_size: int
    ) -> Dict[str, Any]:
        """Reference 도메인 임베딩 마이그레이션"""
        from app.domain.v1.minso.models import ReferenceAnswer, ReferenceAnswerEmbedding

        total_processed = 0
        total_saved = 0
        errors = []
        try:
            offset = 0
            while True:
                result = await self.session.execute(
                    select(ReferenceAnswer).offset(offset).limit(batch_size)
                )
                rows = result.scalars().all()
                if not rows:
                    break
                for ra in rows:
                    try:
                        content = self._build_reference_text(ra)
                        tool_result = await mcp_server.call_tool(
                            "koelectra_embed_text",
                            text=content
                        )
                        if not tool_result.get("success", False):
                            errors.append(f"ReferenceAnswer {ra.id}: 임베딩 생성 실패")
                            continue
                        embedding = tool_result.get("embedding")
                        if not embedding:
                            errors.append(f"ReferenceAnswer {ra.id}: embedding 없음")
                            continue
                        self.session.add(ReferenceAnswerEmbedding(
                            reference_answer_id=ra.id,
                            content=content,
                            embedding=embedding
                        ))
                        total_saved += 1
                        total_processed += 1
                    except Exception as e:
                        errors.append(f"ReferenceAnswer {ra.id}: {str(e)}")
                        logger.error(f"[ERROR] ReferenceAnswer {ra.id} 임베딩 실패: {e}")
                offset += batch_size
                await self.session.commit()
            logger.info(f"[OK] Reference 임베딩 마이그레이션 완료: {total_processed}개 처리, {total_saved}개 저장")
            return {"success": True, "domain": "reference", "total_processed": total_processed, "total_saved": total_saved, "errors": errors}
        except Exception as e:
            logger.error(f"[ERROR] Reference 임베딩 마이그레이션 실패: {e}")
            raise

    def _build_submission_text(self, user_answer) -> str:
        """UserAnswer 엔티티를 임베딩할 텍스트로 변환"""
        text = user_answer.processed_content or user_answer.raw_content
        if text:
            return text
        return f"사용자 답안 ID: {user_answer.id}"

    async def _migrate_submission_embeddings(
        self,
        mcp_server,
        batch_size: int
    ) -> Dict[str, Any]:
        """Submission 도메인 임베딩 마이그레이션"""
        from app.domain.v1.minso.models import UserAnswer, UserAnswerEmbedding

        total_processed = 0
        total_saved = 0
        errors = []
        try:
            offset = 0
            while True:
                result = await self.session.execute(
                    select(UserAnswer).offset(offset).limit(batch_size)
                )
                rows = result.scalars().all()
                if not rows:
                    break
                for ua in rows:
                    try:
                        content = self._build_submission_text(ua)
                        tool_result = await mcp_server.call_tool(
                            "koelectra_embed_text",
                            text=content
                        )
                        if not tool_result.get("success", False):
                            errors.append(f"UserAnswer {ua.id}: 임베딩 생성 실패")
                            continue
                        embedding = tool_result.get("embedding")
                        if not embedding:
                            errors.append(f"UserAnswer {ua.id}: embedding 없음")
                            continue
                        self.session.add(UserAnswerEmbedding(
                            user_answer_id=ua.id,
                            content=content,
                            embedding=embedding
                        ))
                        total_saved += 1
                        total_processed += 1
                    except Exception as e:
                        errors.append(f"UserAnswer {ua.id}: {str(e)}")
                        logger.error(f"[ERROR] UserAnswer {ua.id} 임베딩 실패: {e}")
                offset += batch_size
                await self.session.commit()
            logger.info(f"[OK] Submission 임베딩 마이그레이션 완료: {total_processed}개 처리, {total_saved}개 저장")
            return {"success": True, "domain": "submission", "total_processed": total_processed, "total_saved": total_saved, "errors": errors}
        except Exception as e:
            logger.error(f"[ERROR] Submission 임베딩 마이그레이션 실패: {e}")
            raise

    def _build_reasoning_text(self, reasoning_task) -> str:
        """ReasoningTask 엔티티를 임베딩할 텍스트로 변환"""
        parts = [
            f"작업유형: {reasoning_task.task_type.value}",
            f"상태: {reasoning_task.status.value}",
            f"문제ID: {reasoning_task.problem_id}",
            f"사용자답안ID: {reasoning_task.user_answer_id}",
            f"모범답안ID: {reasoning_task.reference_answer_id}",
        ]
        if reasoning_task.config:
            parts.append(f"설정: {reasoning_task.config}")
        return "\n".join(parts)

    async def _migrate_reasoning_embeddings(
        self,
        mcp_server,
        batch_size: int
    ) -> Dict[str, Any]:
        """Reasoning 도메인 임베딩 마이그레이션"""
        from app.domain.v1.minso.models import ReasoningTask, ReasoningTaskEmbedding

        total_processed = 0
        total_saved = 0
        errors = []
        try:
            offset = 0
            while True:
                result = await self.session.execute(
                    select(ReasoningTask).offset(offset).limit(batch_size)
                )
                rows = result.scalars().all()
                if not rows:
                    break
                for rt in rows:
                    try:
                        content = self._build_reasoning_text(rt)
                        tool_result = await mcp_server.call_tool(
                            "koelectra_embed_text",
                            text=content
                        )
                        if not tool_result.get("success", False):
                            errors.append(f"ReasoningTask {rt.id}: 임베딩 생성 실패")
                            continue
                        embedding = tool_result.get("embedding")
                        if not embedding:
                            errors.append(f"ReasoningTask {rt.id}: embedding 없음")
                            continue
                        self.session.add(ReasoningTaskEmbedding(
                            reasoning_task_id=rt.id,
                            content=content,
                            embedding=embedding
                        ))
                        total_saved += 1
                        total_processed += 1
                    except Exception as e:
                        errors.append(f"ReasoningTask {rt.id}: {str(e)}")
                        logger.error(f"[ERROR] ReasoningTask {rt.id} 임베딩 실패: {e}")
                offset += batch_size
                await self.session.commit()
            logger.info(f"[OK] Reasoning 임베딩 마이그레이션 완료: {total_processed}개 처리, {total_saved}개 저장")
            return {"success": True, "domain": "reasoning", "total_processed": total_processed, "total_saved": total_saved, "errors": errors}
        except Exception as e:
            logger.error(f"[ERROR] Reasoning 임베딩 마이그레이션 실패: {e}")
            raise
