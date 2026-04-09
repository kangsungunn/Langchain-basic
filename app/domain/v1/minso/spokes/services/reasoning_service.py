"""
Reasoning Spoke - 서비스 (Star 토폴로지 말단)

추론 엔진 비즈니스 로직.
단일 소스: 이 파일. reasoning/services.py 는 re-export.
"""

import asyncio
import uuid
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.v1.minso.models import ReasoningTask, ReasoningResult, TaskType, TaskStatus
from app.domain.v1.minso.hub.repositories import ReasoningTaskRepository, ReasoningResultRepository
from app.domain.v1.minso.models.transfers import (
    ReasoningTaskCreate, ReasoningTaskUpdate, ReasoningTaskResponse,
    ReasoningResultResponse, AnalysisResponse,
    IssueAnalysisResult, LogicEvaluationResult, ExpressionReviewResult,
)
from app.domain.v1.minso.shared import EntityNotFoundError
from app.domain.v1.minso.shared.value_objects import ENTITY_USER_ANSWER
from app.core.config import settings
from app.core.database.session import get_session_factory
from app.core.ml.model_loader import ModelLoader
from app.core.ml.inference import InferenceEngine
from app.core.utils.logger import Logger

logger = Logger.get_instance()


def _build_reference_data_for_exaone(ref_answer, problem=None) -> Dict[str, Any]:
    """ExaOne 분석용 모범답안 dict (필요 최소 필드)."""
    data = {"id": getattr(ref_answer, "id", ""), "content": getattr(ref_answer, "content", "") or ""}
    if problem:
        data["problem_context"] = (getattr(problem, "content", "") or "")[:500]
    return data


def _build_submission_data_for_exaone(user_answer, problem=None) -> Dict[str, Any]:
    """ExaOne 분석용 제출답안 dict."""
    data = {
        "id": getattr(user_answer, "id", ""),
        "content": getattr(user_answer, "processed_content", None) or getattr(user_answer, "raw_content", "") or "",
        "raw_content": getattr(user_answer, "raw_content", "") or "",
    }
    if problem:
        data["problem_context"] = (getattr(problem, "content", "") or "")[:500]
    return data


class ReasoningTaskService:
    """추론 작업 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ReasoningTaskRepository(session)

    async def create_task(self, data: ReasoningTaskCreate) -> ReasoningTaskResponse:
        """추론 작업 생성"""
        task = ReasoningTask(
            id=str(uuid.uuid4()),
            task_type=TaskType(data.task_type),
            status=TaskStatus.PENDING,
            user_answer_id=data.user_answer_id,
            reference_answer_id=data.reference_answer_id,
            problem_id=data.problem_id,
            config=data.config
        )

        created = await self.repo.create(task)
        return ReasoningTaskResponse.from_orm(created)

    async def get_task(self, task_id: str) -> Optional[ReasoningTaskResponse]:
        """추론 작업 조회"""
        task = await self.repo.get_by_id(task_id)
        if not task:
            return None
        return ReasoningTaskResponse.from_orm(task)

    async def get_tasks_by_user_answer(
        self,
        user_answer_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """사용자 답안의 추론 작업 조회"""
        tasks = await self.repo.get_by_user_answer(user_answer_id, skip=skip, limit=limit)
        total = await self.repo.count_by_user_answer(user_answer_id)

        return {
            "total": total,
            "items": [ReasoningTaskResponse.from_orm(t) for t in tasks]
        }

    async def get_all_tasks(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """모든 추론 작업 조회"""
        tasks = await self.repo.get_all(skip=skip, limit=limit)
        total = await self.repo.count()

        return {
            "total": total,
            "items": [ReasoningTaskResponse.from_orm(t) for t in tasks]
        }

    async def update_task(self, task_id: str, data: ReasoningTaskUpdate) -> Optional[ReasoningTaskResponse]:
        """추론 작업 수정"""
        task = await self.repo.get_by_id(task_id)
        if not task:
            return None

        if data.status is not None:
            task.status = TaskStatus(data.status)
        if data.config is not None:
            task.config = data.config

        updated = await self.repo.update(task)
        return ReasoningTaskResponse.from_orm(updated)

    async def delete_task(self, task_id: str) -> bool:
        """추론 작업 삭제"""
        task = await self.repo.get_by_id(task_id)
        if not task:
            return False

        await self.repo.delete(task)
        return True


class ReasoningEngine:
    """
    추론 엔진 서비스

    EXAONE 모델을 활용한 답안 분석
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_repo = ReasoningTaskRepository(session)
        self.result_repo = ReasoningResultRepository(session)
        # 지연 로딩: 모범답안+문제가 있을 때만 쟁점 포함률 분류 모델 로드 (extracted_issues만 쓰는 경우 불필요)
        self._model_loader = None
        self._inference_engine = None
        self._model_available = False
        self._model_load_failed = False

    def _ensure_classification_model(self) -> bool:
        """쟁점 포함률 분류 모델이 필요할 때만 로드 (모범답안 있는 경로)."""
        if self._model_available and self._inference_engine is not None:
            return True
        if getattr(self, "_model_load_failed", False):
            return False
        try:
            self._model_loader = ModelLoader.get_instance()
            self._inference_engine = InferenceEngine(self._model_loader)
            self._model_available = True
            logger.info("ML 모델(쟁점 포함률 분류) 로드 완료")
            return True
        except Exception as e:
            logger.warning(f"ML 모델 초기화 실패, 더미 데이터 사용: {e}")
            self._model_loader = None
            self._inference_engine = None
            self._model_available = False
            self._model_load_failed = True
            return False

    async def analyze_issues(
        self,
        user_answer_id: str,
        reference_answer_id: str,
        problem_id: str,
        save_result: bool = True,
        extracted_issues: Optional[List[str]] = None,
    ) -> AnalysisResponse:
        """쟁점 분석. extracted_issues가 있으면 모범답안 없이 해당 논점 목록으로 분석."""
        logger.info(f"쟁점 분석 시작: user_answer={user_answer_id}, reference={reference_answer_id}")

        task = ReasoningTask(
            id=str(uuid.uuid4()),
            task_type=TaskType.ISSUE_ANALYSIS,
            status=TaskStatus.RUNNING,
            user_answer_id=user_answer_id,
            reference_answer_id=reference_answer_id or "",
            problem_id=problem_id or ""
        )
        await self.task_repo.create(task)

        try:
            start_time = time.time()

            from app.domain.v1.minso.hub.repositories import (
                UserAnswerRepository,
                ProblemRepository,
                ReferenceAnswerRepository,
            )

            user_answer_repo = UserAnswerRepository(self.session)
            problem_repo = ProblemRepository(self.session)
            ref_answer_repo = ReferenceAnswerRepository(self.session)

            user_answer = await user_answer_repo.get_by_id(user_answer_id)
            if not user_answer:
                raise EntityNotFoundError(ENTITY_USER_ANSWER, user_answer_id)

            problem = None
            ref_answer = None
            if problem_id and problem_id.strip():
                problem = await problem_repo.get_by_id(problem_id)
            if reference_answer_id and reference_answer_id.strip():
                ref_answer = await ref_answer_repo.get_by_id(reference_answer_id)

            reference_issues: List[str] = []
            if ref_answer:
                reference_issues = self._extract_issues_from_reference(ref_answer)
            elif extracted_issues:
                reference_issues = extracted_issues

            predicted_class = None
            confidence = 0.85

            if problem and ref_answer and self._ensure_classification_model() and self._inference_engine:
                try:
                    input_text = f"""[문제] {problem.content}
[모범답안] {ref_answer.content}
[사용자답안] {user_answer.processed_content or user_answer.raw_content}"""

                    prediction_result = self._inference_engine.predict(input_text, max_length=256)
                    predicted_class = prediction_result["prediction"]
                    confidence = prediction_result["confidence"]

                    coverage_map = {0: 0.3, 1: 0.6, 2: 0.9}
                    coverage_rate = coverage_map.get(predicted_class, 0.5)

                    identified_count = int(len(reference_issues) * coverage_rate)
                    identified_issues = reference_issues[:identified_count]
                    missing_issues = reference_issues[identified_count:]

                    analysis_result = IssueAnalysisResult(
                        identified_issues=identified_issues,
                        missing_issues=missing_issues,
                        coverage_rate=coverage_rate,
                        details={
                            "reference_issues": reference_issues,
                            "user_issues": identified_issues,
                            "model_prediction": predicted_class,
                            "model_confidence": confidence
                        }
                    )

                    logger.info(f"실제 모델 예측: class={predicted_class}, confidence={confidence}, coverage={coverage_rate}")

                except Exception as e:
                    logger.warning(f"모델 추론 실패, 더미 데이터 사용: {e}")
                    analysis_result = IssueAnalysisResult(
                        identified_issues=["계약의 성립", "채무불이행"],
                        missing_issues=["손해배상의 범위"],
                        coverage_rate=0.67,
                        details={
                            "reference_issues": ["계약의 성립", "채무불이행", "손해배상의 범위"],
                            "user_issues": ["계약의 성립", "채무불이행"],
                            "error": str(e)
                        }
                    )
                    self._model_available = False
                    self._model_load_failed = True

            elif reference_issues:
                # 모범답안 없이 논점 추출 결과만 있는 경우 (extracted_issues)
                coverage_rate = 0.6
                identified_count = int(len(reference_issues) * coverage_rate)
                identified_issues = reference_issues[:identified_count]
                missing_issues = reference_issues[identified_count:]
                analysis_result = IssueAnalysisResult(
                    identified_issues=identified_issues,
                    missing_issues=missing_issues,
                    coverage_rate=coverage_rate,
                    details={
                        "reference_issues": reference_issues,
                        "user_issues": identified_issues,
                        "source": "extracted_issues",
                    }
                )
                logger.info("논점 추출 결과로 쟁점 분석 (모범답안 없음)")
            else:
                analysis_result = IssueAnalysisResult(
                    identified_issues=["계약의 성립", "채무불이행"],
                    missing_issues=["손해배상의 범위"],
                    coverage_rate=0.67,
                    details={
                        "reference_issues": ["계약의 성립", "채무불이행", "손해배상의 범위"],
                        "user_issues": ["계약의 성립", "채무불이행"]
                    }
                )
                logger.info("더미 데이터 사용 (모델 없음)")

            elapsed_time = time.time() - start_time

            meta_info = {
                "model": "exaone-3.5-7.8b-lora" if self._model_available and predicted_class is not None else "dummy",
                "dummy": not (self._model_available and predicted_class is not None),
                "processing_time": elapsed_time
            }
            if self._model_available and predicted_class is not None:
                meta_info["model_confidence"] = confidence
                meta_info["predicted_class"] = predicted_class

            result = ReasoningResult(
                id=str(uuid.uuid4()),
                task_id=task.id,
                result_type="issue_analysis",
                content=analysis_result.dict(),
                confidence=confidence,
                metrics={"processing_time": elapsed_time},
                meta=meta_info,
                created_at=datetime.utcnow()
            )

            if save_result:
                await self.result_repo.create(result)
                saved_result = await self.result_repo.get_by_id(result.id)
                result = saved_result if saved_result else result

            task.status = TaskStatus.COMPLETED
            await self.task_repo.update(task)

            logger.info(f"쟁점 분석 완료: task_id={task.id}, coverage={analysis_result.coverage_rate}")

            return AnalysisResponse(
                task_id=task.id,
                task_type=TaskType.ISSUE_ANALYSIS.value,
                status=TaskStatus.COMPLETED.value,
                results=[ReasoningResultResponse.from_orm(result)],
                summary={
                    "coverage_rate": analysis_result.coverage_rate,
                    "identified_count": len(analysis_result.identified_issues),
                    "missing_count": len(analysis_result.missing_issues)
                }
            )

        except Exception as e:
            logger.error(f"쟁점 분석 실패: {str(e)}")
            task.status = TaskStatus.FAILED
            await self.task_repo.update(task)
            raise

    async def evaluate_logic(
        self,
        user_answer_id: str,
        reference_answer_id: str,
        problem_id: str,
        save_result: bool = True
    ) -> AnalysisResponse:
        """논리 평가"""
        logger.info(f"논리 평가 시작: user_answer={user_answer_id}")

        task = ReasoningTask(
            id=str(uuid.uuid4()),
            task_type=TaskType.LOGIC_EVALUATION,
            status=TaskStatus.RUNNING,
            user_answer_id=user_answer_id,
            reference_answer_id=reference_answer_id,
            problem_id=problem_id
        )
        await self.task_repo.create(task)

        try:
            start_time = time.time()
            use_exaone = False
            logic_raw_analysis = None
            evaluation_result = LogicEvaluationResult(
                coherence_score=0.78,
                argument_strength=0.72,
                weak_points=[
                    "단락 2에서 전제와 결론 간의 논리적 비약이 있습니다.",
                    "반대 주장에 대한 검토가 부족합니다."
                ],
                suggestions=[
                    "각 논증 단계를 더 명확히 연결하세요.",
                    "법적 근거를 추가하여 논증을 강화하세요."
                ]
            )

            if not settings.SKIP_EXAONE:
                try:
                    from app.domain.v1.minso.hub.repositories import (
                        UserAnswerRepository,
                        ProblemRepository,
                        ReferenceAnswerRepository,
                    )
                    from app.domain.v1.minso.hub.mcp import get_minso_central_mcp_server
                    user_answer_repo = UserAnswerRepository(self.session)
                    problem_repo = ProblemRepository(self.session)
                    ref_answer_repo = ReferenceAnswerRepository(self.session)
                    user_answer = await user_answer_repo.get_by_id(user_answer_id)
                    if user_answer:
                        problem_text = ""
                        reference_text = ""
                        if problem_id and problem_id.strip():
                            problem = await problem_repo.get_by_id(problem_id)
                            problem_text = (problem.content or "") if problem else ""
                        if reference_answer_id and reference_answer_id.strip():
                            ref_answer = await ref_answer_repo.get_by_id(reference_answer_id)
                            reference_text = (ref_answer.content or "") if ref_answer else ""
                        user_answer_text = (user_answer.processed_content or user_answer.raw_content or "") or ""
                        mcp = get_minso_central_mcp_server()
                        tool_res = await mcp.call_tool(
                            "exaone_evaluate_logic",
                            problem_text=problem_text,
                            reference_text=reference_text,
                            user_answer_text=user_answer_text,
                        )
                        if tool_res.get("success") and "coherence_score" in tool_res:
                            evaluation_result = LogicEvaluationResult(
                                coherence_score=float(tool_res.get("coherence_score", 0.5)),
                                argument_strength=float(tool_res.get("argument_strength", 0.5)),
                                weak_points=tool_res.get("weak_points") or [],
                                suggestions=tool_res.get("suggestions") or [],
                            )
                            use_exaone = True
                            logic_raw_analysis = tool_res.get("raw_analysis")
                            logger.info("논리 평가 ExaOne 결과 반영")
                    else:
                        logger.warning("논리 평가: user_answer 없음, 더미 사용")
                except Exception as e:
                    logger.warning(f"논리 평가 ExaOne 호출 실패(폴백): {e}")

            elapsed_time = time.time() - start_time

            logic_content = evaluation_result.dict()
            if logic_raw_analysis:
                logic_content["raw_analysis"] = logic_raw_analysis
            result = ReasoningResult(
                id=str(uuid.uuid4()),
                task_id=task.id,
                result_type="logic_evaluation",
                content=logic_content,
                confidence=0.82,
                metrics={"processing_time": elapsed_time},
                meta={"model": "exaone-legal-v1", "dummy": not use_exaone},
                created_at=datetime.utcnow()
            )

            if save_result:
                await self.result_repo.create(result)
                saved_result = await self.result_repo.get_by_id(result.id)
                result = saved_result if saved_result else result

            task.status = TaskStatus.COMPLETED
            await self.task_repo.update(task)

            logger.info(f"논리 평가 완료: task_id={task.id}")

            return AnalysisResponse(
                task_id=task.id,
                task_type=TaskType.LOGIC_EVALUATION.value,
                status=TaskStatus.COMPLETED.value,
                results=[ReasoningResultResponse.from_orm(result)],
                summary={
                    "coherence_score": evaluation_result.coherence_score,
                    "argument_strength": evaluation_result.argument_strength,
                    "weak_points_count": len(evaluation_result.weak_points)
                }
            )

        except Exception as e:
            logger.error(f"논리 평가 실패: {str(e)}")
            task.status = TaskStatus.FAILED
            await self.task_repo.update(task)
            raise

    async def review_expression(
        self,
        user_answer_id: str,
        save_result: bool = True
    ) -> AnalysisResponse:
        """표현 검토"""
        logger.info(f"표현 검토 시작: user_answer={user_answer_id}")

        task = ReasoningTask(
            id=str(uuid.uuid4()),
            task_type=TaskType.EXPRESSION_REVIEW,
            status=TaskStatus.RUNNING,
            user_answer_id=user_answer_id,
            reference_answer_id="",
            problem_id=""
        )
        await self.task_repo.create(task)

        try:
            start_time = time.time()
            use_exaone = False
            review_result = ExpressionReviewResult(
                clarity_score=0.75,
                formality_score=0.88,
                issues=[
                    {"type": "구어체", "location": "2번 문단", "content": "그런데"},
                    {"type": "중복", "location": "3번 문단", "content": "따라서... 따라서"}
                ],
                improvements=[
                    {"original": "그런데", "suggestion": "그러나", "reason": "법률 문서의 격식성"},
                    {"original": "따라서... 따라서", "suggestion": "따라서... 그러므로", "reason": "반복 회피"}
                ]
            )

            if not settings.SKIP_EXAONE:
                try:
                    from app.domain.v1.minso.hub.repositories import UserAnswerRepository
                    from app.domain.v1.minso.hub.mcp import get_minso_central_mcp_server
                    user_answer_repo = UserAnswerRepository(self.session)
                    user_answer = await user_answer_repo.get_by_id(user_answer_id)
                    if user_answer:
                        user_answer_text = (user_answer.processed_content or user_answer.raw_content or "") or ""
                        mcp = get_minso_central_mcp_server()
                        tool_res = await mcp.call_tool(
                            "exaone_review_expression",
                            user_answer_text=user_answer_text,
                        )
                        if tool_res.get("success") and "clarity_score" in tool_res:
                            review_result = ExpressionReviewResult(
                                clarity_score=float(tool_res.get("clarity_score", 0.5)),
                                formality_score=float(tool_res.get("formality_score", 0.5)),
                                issues=tool_res.get("issues") or [],
                                improvements=tool_res.get("improvements") or [],
                            )
                            use_exaone = True
                            logger.info("표현 검토 ExaOne 결과 반영")
                    else:
                        logger.warning("표현 검토: user_answer 없음, 더미 사용")
                except Exception as e:
                    logger.warning(f"표현 검토 ExaOne 호출 실패(폴백): {e}")

            elapsed_time = time.time() - start_time

            result = ReasoningResult(
                id=str(uuid.uuid4()),
                task_id=task.id,
                result_type="expression_review",
                content=review_result.dict(),
                confidence=0.90,
                metrics={"processing_time": elapsed_time},
                meta={"model": "exaone-legal-v1", "dummy": not use_exaone},
                created_at=datetime.utcnow()
            )

            if save_result:
                await self.result_repo.create(result)
                saved_result = await self.result_repo.get_by_id(result.id)
                result = saved_result if saved_result else result

            task.status = TaskStatus.COMPLETED
            await self.task_repo.update(task)

            logger.info(f"표현 검토 완료: task_id={task.id}")

            return AnalysisResponse(
                task_id=task.id,
                task_type=TaskType.EXPRESSION_REVIEW.value,
                status=TaskStatus.COMPLETED.value,
                results=[ReasoningResultResponse.from_orm(result)],
                summary={
                    "clarity_score": review_result.clarity_score,
                    "formality_score": review_result.formality_score,
                    "issues_count": len(review_result.issues)
                }
            )

        except Exception as e:
            logger.error(f"표현 검토 실패: {str(e)}")
            task.status = TaskStatus.FAILED
            await self.task_repo.update(task)
            raise

    async def _call_exaone_for_analysis(
        self,
        user_answer_id: str,
        reference_answer_id: str,
        problem_id: str,
    ) -> Optional[str]:
        """
        ExaOne으로 모범답안·제출답안 분석 (Phase 4).
        실패 시 None 반환, 기존 파이프라인으로 폴백.
        """
        from app.domain.v1.minso.hub.repositories import (
            UserAnswerRepository,
            ProblemRepository,
            ReferenceAnswerRepository,
        )
        from app.domain.v1.minso.hub.mcp import get_minso_central_mcp_server

        try:
            user_answer_repo = UserAnswerRepository(self.session)
            problem_repo = ProblemRepository(self.session)
            ref_answer_repo = ReferenceAnswerRepository(self.session)

            user_answer = await user_answer_repo.get_by_id(user_answer_id)
            if not user_answer:
                return None
            problem = await problem_repo.get_by_id(problem_id) if (problem_id and problem_id.strip()) else None
            ref_answer = await ref_answer_repo.get_by_id(reference_answer_id) if (reference_answer_id and reference_answer_id.strip()) else None

            reference_data = _build_reference_data_for_exaone(ref_answer, problem) if ref_answer else None
            submission_data = _build_submission_data_for_exaone(user_answer, problem)

            mcp = get_minso_central_mcp_server()
            parts = []

            if reference_data:
                ref_res = await mcp.call_tool("exaone_analyze_reference_data", reference_data=reference_data)
                if ref_res.get("success") and ref_res.get("analysis"):
                    parts.append(f"[모범답안 분석]\n{ref_res['analysis']}")

            sub_res = await mcp.call_tool("exaone_analyze_submission_data", submission_data=submission_data)
            if sub_res.get("success") and sub_res.get("analysis"):
                parts.append(f"[제출답안 분석]\n{sub_res['analysis']}")

            if not parts:
                return None
            return "\n\n".join(parts)
        except Exception as e:
            logger.warning(f"ExaOne 분석 호출 실패 (폴백): {e}")
            return None

    async def comprehensive_analysis(
        self,
        user_answer_id: str,
        reference_answer_id: Optional[str] = None,
        problem_id: Optional[str] = None,
        save_result: bool = True,
        extracted_issues: Optional[List[str]] = None,
    ) -> AnalysisResponse:
        """종합 분석 (Phase 4: ExaOne 보조 분석 포함, 실패 시 기존 파이프라인 폴백). extracted_issues 있으면 모범답안 없이 논점 추출 결과로 쟁점 분석."""
        logger.info(f"종합 분석 시작: user_answer={user_answer_id}")

        ref_answer_id = reference_answer_id or ""
        prob_id = problem_id or ""

        task = ReasoningTask(
            id=str(uuid.uuid4()),
            task_type=TaskType.COMPREHENSIVE,
            status=TaskStatus.RUNNING,
            user_answer_id=user_answer_id,
            reference_answer_id=ref_answer_id,
            problem_id=prob_id
        )
        await self.task_repo.create(task)
        await self.session.commit()  # 트랜잭션 종료 후 연결을 풀에 반환 (ExaOne 장시간 실행 중 연결 끊김 방지)

        exaone_analysis: Optional[str] = None
        if settings.SKIP_EXAONE:
            logger.info("SKIP_EXAONE: ExaOne 비활성화, 보조 분석 생략 (PDF/나머지 파이프라인만 검증)")
        else:
            try:
                exaone_analysis = await asyncio.wait_for(
                    self._call_exaone_for_analysis(user_answer_id, ref_answer_id, prob_id),
                    timeout=600.0,  # 10분 (첫 요청 시 로드+워밍업으로 6~10분 걸릴 수 있음)
                )
                if exaone_analysis:
                    logger.info("ExaOne 보조 분석 반영")
            except asyncio.TimeoutError:
                logger.warning("ExaOne 분석 타임아웃(10분), 폴백")
            except Exception as e:
                logger.warning(f"ExaOne 분석 스킵 (폴백): {e}")

        # 한 세션을 10분 이상 잡고 있으면 DB 서버가 연결을 끊음 → 단계별로 세션 분리
        factory = get_session_factory()
        issue_analysis = None
        logic_evaluation = None
        expression_review = None

        async def _run_with_session(coro):
            old_s = self.session
            old_t = self.task_repo
            old_r = self.result_repo
            async with factory() as sess:
                self.session = sess
                self.task_repo = ReasoningTaskRepository(sess)
                self.result_repo = ReasoningResultRepository(sess)
                try:
                    return await coro
                finally:
                    self.session = old_s
                    self.task_repo = old_t
                    self.result_repo = old_r

        issue_analysis = await _run_with_session(
            self.analyze_issues(
                user_answer_id, ref_answer_id, prob_id, save_result=False,
                extracted_issues=extracted_issues,
            )
        )
        logic_evaluation = await _run_with_session(
            self.evaluate_logic(
                user_answer_id, ref_answer_id, prob_id, save_result=False
            )
        )
        expression_review = await _run_with_session(
            self.review_expression(user_answer_id, save_result=False)
        )

        async with factory() as new_session:
            old_session = self.session
            old_task_repo = self.task_repo
            old_result_repo = self.result_repo
            self.session = new_session
            self.task_repo = ReasoningTaskRepository(new_session)
            self.result_repo = ReasoningResultRepository(new_session)
            try:
                all_results = []
                if save_result:
                    for analysis in [issue_analysis, logic_evaluation, expression_review]:
                        for result_response in analysis.results:
                            now = datetime.utcnow()
                            result = ReasoningResult(
                                id=str(uuid.uuid4()),
                                task_id=task.id,
                                result_type=result_response.result_type,
                                content=result_response.content,
                                confidence=result_response.confidence,
                                metrics=result_response.metrics,
                                meta=result_response.meta,
                                created_at=now,
                                updated_at=now
                            )
                            all_results.append(result)
                    if exaone_analysis:
                        now = datetime.utcnow()
                        exaone_result = ReasoningResult(
                            id=str(uuid.uuid4()),
                            task_id=task.id,
                            result_type="exaone_analysis",
                            content={"analysis": exaone_analysis},
                            confidence=None,
                            metrics=None,
                            meta={"source": "exaone_analyze_reference_data/submission_data"},
                            created_at=now,
                            updated_at=now,
                        )
                        all_results.append(exaone_result)

                    await self.result_repo.create_many(all_results)
                    saved_results = await self.result_repo.get_by_task_id(task.id)
                    result_responses = [ReasoningResultResponse.from_orm(r) for r in saved_results]
                else:
                    result_responses = []
                    for analysis in [issue_analysis, logic_evaluation, expression_review]:
                        result_responses.extend(analysis.results)
                    if exaone_analysis:
                        result_responses.append(
                            ReasoningResultResponse(
                                id="",
                                task_id=task.id,
                                result_type="exaone_analysis",
                                content={"analysis": exaone_analysis},
                                confidence=None,
                                metrics=None,
                                meta={"source": "exaone"},
                                created_at=datetime.utcnow(),
                            )
                        )

                task_to_update = await self.task_repo.get_by_id(task.id)
                if task_to_update:
                    task_to_update.status = TaskStatus.COMPLETED
                    await self.task_repo.update(task_to_update)

                await new_session.commit()
                logger.info(f"종합 분석 완료: task_id={task.id}")

                summary_dict = {
                    "issue_coverage": issue_analysis.summary.get("coverage_rate", 0),
                    "logic_coherence": logic_evaluation.summary.get("coherence_score", 0),
                    "expression_clarity": expression_review.summary.get("clarity_score", 0),
                }
                if exaone_analysis:
                    summary_dict["exaone_analysis"] = exaone_analysis
                for r in result_responses:
                    c = getattr(r, "content", None) or {}
                    if not isinstance(c, dict):
                        continue
                    rt = getattr(r, "result_type", None)
                    if rt == "logic_evaluation" and c.get("raw_analysis"):
                        summary_dict["logic_evaluation_text"] = c.get("raw_analysis")
                    elif rt == "expression_review" and c.get("raw_analysis"):
                        summary_dict["expression_review_text"] = c.get("raw_analysis")

                return AnalysisResponse(
                    task_id=task.id,
                    task_type=TaskType.COMPREHENSIVE.value,
                    status=TaskStatus.COMPLETED.value,
                    results=result_responses,
                    summary=summary_dict,
                )

            except Exception as e:
                logger.error(f"종합 분석 실패: {str(e)}")
                try:
                    await self.session.rollback()
                except Exception:
                    pass
                try:
                    task_to_update = await self.task_repo.get_by_id(task.id)
                    if task_to_update:
                        task_to_update.status = TaskStatus.FAILED
                        await self.task_repo.update(task_to_update)
                except Exception as update_e:
                    logger.warning(f"종합 분석 실패 시 task FAILED 갱신 스킵: {update_e}")
                raise
            finally:
                self.session = old_session
                self.task_repo = old_task_repo
                self.result_repo = old_result_repo

    def _extract_issues_from_reference(self, ref_answer) -> List[str]:
        """모범 답안에서 쟁점 추출 (간단한 규칙 기반)"""
        if hasattr(ref_answer, 'issues') and ref_answer.issues:
            return [issue.title for issue in ref_answer.issues]
        return ["주요 쟁점 1", "주요 쟁점 2", "주요 쟁점 3"]
