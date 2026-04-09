"""
Feedback Spoke - 서비스 (Star 토폴로지 말단)

피드백 생성 및 관리 비즈니스 로직.
단일 소스: 이 파일. feedback/services.py 는 re-export.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.v1.minso.models import Feedback, FeedbackItem, FeedbackType, FeedbackSeverity
from app.domain.v1.minso.hub.repositories import (
    FeedbackRepository,
    FeedbackItemRepository,
    ReasoningTaskRepository,
    ReasoningResultRepository,
)
from app.domain.v1.minso.models.transfers import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse,
    FeedbackItemCreate, GenerateFeedbackResponse, FeedbackReportResponse,
)
from app.domain.v1.minso.shared import EntityNotFoundError, DomainValidationError
from app.domain.v1.minso.shared.value_objects import ENTITY_REASONING_TASK
from app.core.config import settings
from app.core.utils.logger import Logger

logger = Logger.get_instance()


class FeedbackService:
    """피드백 관리 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FeedbackRepository(session)

    async def create_feedback(self, data: FeedbackCreate) -> FeedbackResponse:
        """피드백 생성"""
        feedback = Feedback(
            id=str(uuid.uuid4()),
            user_answer_id=data.user_answer_id,
            reasoning_task_id=data.reasoning_task_id,
            feedback_type=FeedbackType(data.feedback_type),
            overall_score=data.overall_score,
            scores=data.scores,
            summary=data.summary,
            strengths=data.strengths,
            weaknesses=data.weaknesses,
            meta=data.meta
        )

        created = await self.repo.create(feedback)
        feedback_with_items = await self.repo.get_by_id(created.id)
        return FeedbackResponse.from_orm(feedback_with_items)

    async def get_feedback(self, feedback_id: str) -> Optional[FeedbackResponse]:
        """피드백 조회"""
        feedback = await self.repo.get_by_id(feedback_id)
        if not feedback:
            return None
        return FeedbackResponse.from_orm(feedback)

    async def get_feedbacks_by_user_answer(
        self,
        user_answer_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """사용자 답안의 피드백 조회"""
        feedbacks = await self.repo.get_by_user_answer(user_answer_id, skip=skip, limit=limit)
        total = await self.repo.count_by_user_answer(user_answer_id)

        return {
            "total": total,
            "items": [FeedbackResponse.from_orm(f) for f in feedbacks]
        }

    async def get_all_feedbacks(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """모든 피드백 조회"""
        feedbacks = await self.repo.get_all(skip=skip, limit=limit)
        total = await self.repo.count()

        return {
            "total": total,
            "items": [FeedbackResponse.from_orm(f) for f in feedbacks]
        }

    async def update_feedback(self, feedback_id: str, data: FeedbackUpdate) -> Optional[FeedbackResponse]:
        """피드백 수정"""
        feedback = await self.repo.get_by_id(feedback_id)
        if not feedback:
            return None

        if data.overall_score is not None:
            feedback.overall_score = data.overall_score
        if data.scores is not None:
            feedback.scores = data.scores
        if data.summary is not None:
            feedback.summary = data.summary
        if data.strengths is not None:
            feedback.strengths = data.strengths
        if data.weaknesses is not None:
            feedback.weaknesses = data.weaknesses
        if data.meta is not None:
            feedback.meta = data.meta

        updated = await self.repo.update(feedback)
        return FeedbackResponse.from_orm(updated)

    async def delete_feedback(self, feedback_id: str) -> bool:
        """피드백 삭제"""
        feedback = await self.repo.get_by_id(feedback_id)
        if not feedback:
            return False

        await self.repo.delete(feedback)
        return True


class FeedbackGenerator:
    """
    피드백 생성 엔진

    Reasoning 결과를 사용자 친화적인 피드백으로 변환
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.feedback_repo = FeedbackRepository(session)
        self.item_repo = FeedbackItemRepository(session)
        self.reasoning_task_repo = ReasoningTaskRepository(session)
        self.reasoning_result_repo = ReasoningResultRepository(session)

    async def _call_exaone_for_feedback(self, task, results: List) -> Optional[str]:
        """
        ExaOne으로 추론 데이터 분석 (Phase 4). 실패 시 None, 기존 파이프라인 유지.
        """
        try:
            from app.domain.v1.minso.hub.mcp import get_minso_central_mcp_server

            task_type_val = getattr(task, "task_type", None)
            if task_type_val is not None and hasattr(task_type_val, "value"):
                task_type_val = task_type_val.value
            reasoning_data = {
                "task_id": task.id,
                "task_type": task_type_val,
                "results": [
                    {"result_type": getattr(r, "result_type", ""), "content": getattr(r, "content", {})}
                    for r in results
                ],
            }
            mcp = get_minso_central_mcp_server()
            res = await mcp.call_tool("exaone_analyze_reasoning_data", reasoning_data=reasoning_data)
            if res.get("success") and res.get("analysis"):
                return res["analysis"]
        except Exception as e:
            logger.warning(f"ExaOne 피드백 보조 분석 실패 (폴백): {e}")
        return None

    async def generate_from_reasoning(
        self,
        user_answer_id: str,
        reasoning_task_id: str,
        feedback_type: str,
        include_suggestions: bool = True
    ) -> GenerateFeedbackResponse:
        """
        추론 결과로부터 피드백 생성

        Reasoning 결과를 분석하여 구조화된 피드백 생성
        """
        logger.info(f"피드백 생성 시작: task={reasoning_task_id}, type={feedback_type}")

        task = await self.reasoning_task_repo.get_by_id(reasoning_task_id)
        if not task:
            raise EntityNotFoundError(ENTITY_REASONING_TASK, reasoning_task_id)

        results = await self.reasoning_result_repo.get_by_task_id(reasoning_task_id)
        if not results:
            raise DomainValidationError(f"추론 결과가 없습니다: {reasoning_task_id}")

        if feedback_type == "issue":
            response = await self._generate_issue_feedback(
                user_answer_id, reasoning_task_id, results, include_suggestions
            )
        elif feedback_type == "logic":
            response = await self._generate_logic_feedback(
                user_answer_id, reasoning_task_id, results, include_suggestions
            )
        elif feedback_type == "expression":
            response = await self._generate_expression_feedback(
                user_answer_id, reasoning_task_id, results, include_suggestions
            )
        elif feedback_type == "comprehensive":
            response = await self._generate_comprehensive_feedback(
                user_answer_id, reasoning_task_id, results, include_suggestions
            )
        else:
            raise DomainValidationError(f"지원하지 않는 피드백 타입: {feedback_type}")

        # Phase 4: ExaOne 보조 분석 (실패 시 폴백, 기존 응답 유지). SKIP_EXAONE이면 호출 안 함
        if not settings.SKIP_EXAONE:
            try:
                exaone_analysis = await self._call_exaone_for_feedback(task, results)
                if exaone_analysis:
                    feedback_entity = await self.feedback_repo.get_by_id(response.feedback.id)
                    if feedback_entity is not None:
                        feedback_entity.meta = dict(feedback_entity.meta or {})
                        feedback_entity.meta["exaone_analysis"] = exaone_analysis
                        await self.feedback_repo.update(feedback_entity)
                        response = GenerateFeedbackResponse(
                            feedback=FeedbackResponse.from_orm(feedback_entity),
                            generation_summary=response.generation_summary,
                        )
            except Exception as e:
                logger.warning(f"ExaOne 피드백 메타 반영 실패 (무시): {e}")

        return response

    async def _generate_issue_feedback(
        self,
        user_answer_id: str,
        reasoning_task_id: str,
        results: List,
        include_suggestions: bool
    ) -> GenerateFeedbackResponse:
        """쟁점 피드백 생성"""

        issue_result = next((r for r in results if r.result_type == "issue_analysis"), None)
        if not issue_result:
            raise DomainValidationError("쟁점 분석 결과가 없습니다")

        content = issue_result.content
        coverage = content.get("coverage_rate", 0)
        identified = content.get("identified_issues", [])
        missing = content.get("missing_issues", [])

        feedback = Feedback(
            id=str(uuid.uuid4()),
            user_answer_id=user_answer_id,
            reasoning_task_id=reasoning_task_id,
            feedback_type=FeedbackType.ISSUE,
            overall_score=coverage * 100,
            scores={"coverage": coverage * 100},
            summary=f"총 {len(identified) + len(missing)}개 쟁점 중 {len(identified)}개를 다루었습니다.",
            strengths=[f"'{issue}' 쟁점을 잘 파악했습니다" for issue in identified[:3]],
            weaknesses=[f"'{issue}' 쟁점이 누락되었습니다" for issue in missing]
        )
        await self.feedback_repo.create(feedback)

        items = []
        for issue in identified:
            item = FeedbackItem(
                id=str(uuid.uuid4()),
                feedback_id=feedback.id,
                item_type="identified_issue",
                severity=FeedbackSeverity.INFO,
                title=f"✓ {issue}",
                description="이 쟁점을 정확히 파악하고 다루었습니다.",
                suggestion="계속해서 명확한 쟁점 분석을 유지하세요." if include_suggestions else None
            )
            items.append(item)
        for issue in missing:
            item = FeedbackItem(
                id=str(uuid.uuid4()),
                feedback_id=feedback.id,
                item_type="missing_issue",
                severity=FeedbackSeverity.CRITICAL,
                title=f"✗ {issue} (누락)",
                description="이 쟁점이 답안에서 다루어지지 않았습니다.",
                suggestion=f"'{issue}' 쟁점에 대한 분석을 추가하세요." if include_suggestions else None
            )
            items.append(item)

        if items:
            await self.item_repo.create_many(items)

        logger.info(f"쟁점 피드백 생성 완료: {len(items)}개 항목")
        feedback = await self.feedback_repo.get_by_id(feedback.id)

        return GenerateFeedbackResponse(
            feedback=FeedbackResponse.from_orm(feedback),
            generation_summary={
                "total_issues": len(identified) + len(missing),
                "identified": len(identified),
                "missing": len(missing),
                "coverage_rate": coverage
            }
        )

    async def _generate_logic_feedback(
        self,
        user_answer_id: str,
        reasoning_task_id: str,
        results: List,
        include_suggestions: bool
    ) -> GenerateFeedbackResponse:
        """논리 피드백 생성"""

        logic_result = next((r for r in results if r.result_type == "logic_evaluation"), None)
        if not logic_result:
            raise DomainValidationError("논리 평가 결과가 없습니다")

        content = logic_result.content
        coherence = content.get("coherence_score", 0)
        argument = content.get("argument_strength", 0)
        weak_points = content.get("weak_points", [])
        suggestions = content.get("suggestions", [])

        overall_score = (coherence + argument) / 2 * 100

        feedback = Feedback(
            id=str(uuid.uuid4()),
            user_answer_id=user_answer_id,
            reasoning_task_id=reasoning_task_id,
            feedback_type=FeedbackType.LOGIC,
            overall_score=overall_score,
            scores={
                "coherence": coherence * 100,
                "argument_strength": argument * 100
            },
            summary=f"논리 일관성 {coherence * 100:.1f}점, 논증 강도 {argument * 100:.1f}점입니다.",
            strengths=["전반적인 논리 흐름이 양호합니다"] if coherence > 0.7 else [],
            weaknesses=weak_points
        )
        await self.feedback_repo.create(feedback)

        items = []
        for i, weak in enumerate(weak_points):
            item = FeedbackItem(
                id=str(uuid.uuid4()),
                feedback_id=feedback.id,
                item_type="logic_weakness",
                severity=FeedbackSeverity.WARNING,
                title=f"논리적 약점 {i+1}",
                description=weak,
                suggestion=suggestions[i] if i < len(suggestions) and include_suggestions else None
            )
            items.append(item)

        if items:
            await self.item_repo.create_many(items)

        logger.info(f"논리 피드백 생성 완료: {len(items)}개 항목")
        feedback = await self.feedback_repo.get_by_id(feedback.id)

        return GenerateFeedbackResponse(
            feedback=FeedbackResponse.from_orm(feedback),
            generation_summary={
                "coherence_score": coherence,
                "argument_strength": argument,
                "weak_points_count": len(weak_points)
            }
        )

    async def _generate_expression_feedback(
        self,
        user_answer_id: str,
        reasoning_task_id: str,
        results: List,
        include_suggestions: bool
    ) -> GenerateFeedbackResponse:
        """표현 피드백 생성"""

        expression_result = next((r for r in results if r.result_type == "expression_review"), None)
        if not expression_result:
            raise DomainValidationError("표현 검토 결과가 없습니다")

        content = expression_result.content
        clarity = content.get("clarity_score", 0)
        formality = content.get("formality_score", 0)
        issues = content.get("issues", [])
        improvements = content.get("improvements", [])

        overall_score = (clarity + formality) / 2 * 100

        feedback = Feedback(
            id=str(uuid.uuid4()),
            user_answer_id=user_answer_id,
            reasoning_task_id=reasoning_task_id,
            feedback_type=FeedbackType.EXPRESSION,
            overall_score=overall_score,
            scores={
                "clarity": clarity * 100,
                "formality": formality * 100
            },
            summary=f"명료성 {clarity * 100:.1f}점, 격식성 {formality * 100:.1f}점입니다.",
            strengths=["적절한 법률 용어 사용"] if formality > 0.8 else [],
            weaknesses=[f"{issue['type']}: {issue['content']}" for issue in issues]
        )
        await self.feedback_repo.create(feedback)

        items = []
        for i, issue in enumerate(issues):
            improvement = improvements[i] if i < len(improvements) else None
            suggestion_text = None
            if improvement and include_suggestions:
                suggestion_text = f"'{improvement['original']}' → '{improvement['suggestion']}' ({improvement['reason']})"

            item = FeedbackItem(
                id=str(uuid.uuid4()),
                feedback_id=feedback.id,
                item_type="expression_issue",
                severity=FeedbackSeverity.SUGGESTION,
                location={"location": issue.get("location", "")},
                title=f"{issue['type']} 문제",
                description=f"'{issue['content']}'",
                suggestion=suggestion_text
            )
            items.append(item)

        if items:
            await self.item_repo.create_many(items)

        logger.info(f"표현 피드백 생성 완료: {len(items)}개 항목")
        feedback = await self.feedback_repo.get_by_id(feedback.id)

        return GenerateFeedbackResponse(
            feedback=FeedbackResponse.from_orm(feedback),
            generation_summary={
                "clarity_score": clarity,
                "formality_score": formality,
                "issues_count": len(issues)
            }
        )

    async def _generate_comprehensive_feedback(
        self,
        user_answer_id: str,
        reasoning_task_id: str,
        results: List,
        include_suggestions: bool
    ) -> GenerateFeedbackResponse:
        """종합 피드백 생성 — 쟁점/논리/표현 결과를 묶어 상세 항목(items)·강점·약점까지 채움."""

        issue_result = next((r for r in results if r.result_type == "issue_analysis"), None)
        logic_result = next((r for r in results if r.result_type == "logic_evaluation"), None)
        expression_result = next((r for r in results if r.result_type == "expression_review"), None)

        issue_content = issue_result.content if issue_result else {}
        logic_content = logic_result.content if logic_result else {}
        expression_content = expression_result.content if expression_result else {}

        issue_score = issue_content.get("coverage_rate", 0) * 100
        logic_score = (
            (logic_content.get("coherence_score", 0) + logic_content.get("argument_strength", 0)) / 2 * 100
        )
        expression_score = (
            (expression_content.get("clarity_score", 0) + expression_content.get("formality_score", 0)) / 2 * 100
        )

        overall_score = (issue_score + logic_score + expression_score) / 3

        identified = issue_content.get("identified_issues", [])
        missing = issue_content.get("missing_issues", [])
        weak_points = logic_content.get("weak_points", [])
        logic_suggestions = logic_content.get("suggestions", [])
        expr_issues = expression_content.get("issues", [])
        expr_improvements = expression_content.get("improvements", [])
        coherence = logic_content.get("coherence_score", 0)
        formality = expression_content.get("formality_score", 0)

        strengths = []
        if identified:
            strengths.extend([f"'{issue}' 쟁점을 잘 파악했습니다" for issue in identified[:3]])
        if coherence > 0.7:
            strengths.append("전반적인 논리 흐름이 양호합니다")
        if formality > 0.8:
            strengths.append("적절한 법률 용어 사용")

        weaknesses = []
        if missing:
            weaknesses.extend([f"'{issue}' 쟁점이 누락되었습니다" for issue in missing])
        weaknesses.extend(weak_points)
        if expr_issues:
            weaknesses.extend([f"{issue.get('type', '표현')}: {issue.get('content', '')}" for issue in expr_issues])

        feedback = Feedback(
            id=str(uuid.uuid4()),
            user_answer_id=user_answer_id,
            reasoning_task_id=reasoning_task_id,
            feedback_type=FeedbackType.COMPREHENSIVE,
            overall_score=overall_score,
            scores={
                "issue": issue_score,
                "logic": logic_score,
                "expression": expression_score
            },
            summary=f"종합 점수 {overall_score:.1f}점 (쟁점 {issue_score:.1f}, 논리 {logic_score:.1f}, 표현 {expression_score:.1f})",
            strengths=strengths if strengths else None,
            weaknesses=weaknesses if weaknesses else None
        )
        await self.feedback_repo.create(feedback)

        items = []
        for issue in identified:
            items.append(FeedbackItem(
                id=str(uuid.uuid4()),
                feedback_id=feedback.id,
                item_type="identified_issue",
                severity=FeedbackSeverity.INFO,
                title=f"✓ {issue}",
                description="이 쟁점을 정확히 파악하고 다루었습니다.",
                suggestion="계속해서 명확한 쟁점 분석을 유지하세요." if include_suggestions else None
            ))
        for issue in missing:
            items.append(FeedbackItem(
                id=str(uuid.uuid4()),
                feedback_id=feedback.id,
                item_type="missing_issue",
                severity=FeedbackSeverity.CRITICAL,
                title=f"✗ {issue} (누락)",
                description="이 쟁점이 답안에서 다루어지지 않았습니다.",
                suggestion=f"'{issue}' 쟁점에 대한 분석을 추가하세요." if include_suggestions else None
            ))
        for i, weak in enumerate(weak_points):
            items.append(FeedbackItem(
                id=str(uuid.uuid4()),
                feedback_id=feedback.id,
                item_type="logic_weakness",
                severity=FeedbackSeverity.WARNING,
                title=f"논리적 약점 {i + 1}",
                description=weak,
                suggestion=logic_suggestions[i] if i < len(logic_suggestions) and include_suggestions else None
            ))
        for i, issue in enumerate(expr_issues):
            improvement = expr_improvements[i] if i < len(expr_improvements) else None
            suggestion_text = None
            if improvement and include_suggestions:
                suggestion_text = f"'{improvement.get('original')}' → '{improvement.get('suggestion')}' ({improvement.get('reason', '')})"
            items.append(FeedbackItem(
                id=str(uuid.uuid4()),
                feedback_id=feedback.id,
                item_type="expression_issue",
                severity=FeedbackSeverity.SUGGESTION,
                location={"location": issue.get("location", "")},
                title=f"{issue.get('type', '표현')} 문제",
                description=f"'{issue.get('content', '')}'",
                suggestion=suggestion_text
            ))

        if items:
            await self.item_repo.create_many(items)

        logger.info(f"종합 피드백 생성 완료: 종합 {overall_score:.1f}점, 항목 {len(items)}개")
        feedback = await self.feedback_repo.get_by_id(feedback.id)

        return GenerateFeedbackResponse(
            feedback=FeedbackResponse.from_orm(feedback),
            generation_summary={
                "overall_score": overall_score,
                "issue_score": issue_score,
                "logic_score": logic_score,
                "expression_score": expression_score,
                "items_count": len(items)
            }
        )

    async def generate_report(
        self,
        user_answer_id: str,
        include_comprehensive: bool = True
    ) -> FeedbackReportResponse:
        """사용자 답안의 전체 피드백 리포트 생성"""
        logger.info(f"피드백 리포트 생성: answer={user_answer_id}")

        feedbacks = await self.feedback_repo.get_by_user_answer(user_answer_id)

        if include_comprehensive:
            filtered = feedbacks
        else:
            filtered = [f for f in feedbacks if f.feedback_type != FeedbackType.COMPREHENSIVE]

        avg_score = sum(f.overall_score or 0 for f in filtered) / len(filtered) if filtered else 0

        return FeedbackReportResponse(
            user_answer_id=user_answer_id,
            feedbacks=[FeedbackResponse.from_orm(f) for f in filtered],
            report_summary={
                "total_feedbacks": len(filtered),
                "average_score": round(avg_score, 2),
                "feedback_types": list(set(f.feedback_type.value for f in filtered))
            },
            generated_at=datetime.utcnow()
        )
