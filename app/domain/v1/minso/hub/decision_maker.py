"""
정책/규칙 판단기 (Domain Hub)

KoELECTRA 모델을 사용하여 요청이 정책 기반인지 규칙 기반인지 판단.
core/orchestration에서 domain으로 이동.
"""

from typing import Any, Dict, Optional
import json

from app.core.ml.koelectra_loader import KoELECTRALoader
from app.core.utils.logger import get_logger

logger = get_logger()


# 규칙 기반 액션 (사전 필터링용)
RULE_BASED_ACTIONS = {
    "training": ["create_training_data", "get_training_data", "get_training_jobs", "get_training_data_list"],
    "submission": ["create_text_answer", "create_image_answer", "get_answers", "get_answer", "analyze_structure"],
    "reasoning": ["get_tasks", "get_task", "create_task", "update_task", "delete_task"],
    "reference": ["*"],  # 모든 액션
    "feedback": ["get_feedbacks", "get_feedback", "create_feedback", "update_feedback", "delete_feedback"],
}

# 정책 기반 액션 (사전 필터링용)
POLICY_BASED_ACTIONS = {
    "reasoning": ["analyze_issues", "analyze_logic", "analyze_expression", "comprehensive_analysis"],
    "feedback": ["generate", "generate_from_reasoning", "generate_report"],
    "training": ["start_training", "create_training_job"],
}


class DecisionMaker:
    """
    정책/규칙 판단기

    KoELECTRA 모델을 사용하여 요청이 정책 기반인지 규칙 기반인지 판단합니다.
    """

    def __init__(self):
        self.koelectra = KoELECTRALoader.get_instance()

    def _build_prompt(
        self,
        domain: str,
        action: str,
        request_data: Any
    ) -> str:
        """
        KoELECTRA 판단을 위한 프롬프트 구성

        Args:
            domain: 도메인 이름
            action: 액션 이름
            request_data: 요청 데이터

        Returns:
            프롬프트 텍스트
        """
        # 요청 데이터 요약
        request_summary = self._summarize_request(request_data)

        prompt = f"""
다음은 민사소송법 서술형 답안지 첨삭 시스템의 API 요청입니다.

**도메인**: {domain}
**액션**: {action}
**요청 요약**: {request_summary}

이 요청을 처리하기 위해:
1. ML 모델(EXAONE 등) 추론이 필요한가요?
2. 복잡한 비즈니스 로직이나 여러 도메인 간 협업이 필요한가요?
3. Star 토폴로지(Reasoning Hub)를 통한 중앙 집중식 처리가 필요한가요?

위 질문 중 하나라도 "예"라면 → **정책 기반 (policy)**
모두 "아니오"라면 → **규칙 기반 (rule)**

답변: [policy 또는 rule]
"""
        return prompt.strip()

    def _summarize_request(self, request_data: Any) -> str:
        """
        요청 데이터 요약

        Args:
            request_data: 요청 데이터 (Pydantic 모델, dict, 또는 기타)

        Returns:
            요약 텍스트
        """
        try:
            # Pydantic 모델인 경우
            if hasattr(request_data, 'model_dump'):
                data_dict = request_data.model_dump(exclude_none=True)
            # dict인 경우
            elif isinstance(request_data, dict):
                data_dict = request_data
            # 기타 (str, int 등)
            else:
                return str(request_data)[:200]

            # 주요 필드만 추출 (너무 길면 잘라냄)
            summary_parts = []
            for key, value in list(data_dict.items())[:5]:  # 최대 5개 필드만
                if isinstance(value, str):
                    # 텍스트는 처음 50자만
                    summary_parts.append(f"{key}: {value[:50]}...")
                elif isinstance(value, (int, float, bool)):
                    summary_parts.append(f"{key}: {value}")
                elif value is None:
                    summary_parts.append(f"{key}: None")
                else:
                    summary_parts.append(f"{key}: {type(value).__name__}")

            return ", ".join(summary_parts) if summary_parts else "요청 데이터 없음"

        except Exception as e:
            logger.warning(f"요청 데이터 요약 실패: {e}")
            return "요청 데이터 요약 실패"

    async def decide(
        self,
        domain: str,
        action: str,
        request: Any
    ) -> str:
        """
        정책/규칙 판단

        Args:
            domain: 도메인 이름 (예: "training", "reasoning")
            action: 액션 이름 (예: "create_training_data", "comprehensive_analysis")
            request: 요청 데이터

        Returns:
            "policy" 또는 "rule"
        """
        # 1단계: 규칙 기반 사전 필터링 (빠른 판단)
        if self._is_rule_based(domain, action):
            logger.info(f"[OK] 규칙 기반 판단 (사전 필터링): {domain}.{action}")
            return "rule"

        # 2단계: 정책 기반 사전 필터링 (빠른 판단)
        if self._is_policy_based(domain, action):
            logger.info(f"[OK] 정책 기반 판단 (사전 필터링): {domain}.{action}")
            return "policy"

        # 3단계: KoELECTRA 모델 판단 (모호한 경우)
        logger.info(f"[KOELECTRA] KoELECTRA 모델로 판단 중: {domain}.{action}")

        # KoELECTRA 모델 사용 가능 여부 확인
        if not self.koelectra.is_available():
            logger.warning("[WARN] KoELECTRA 모델을 사용할 수 없습니다. 기본값으로 규칙 기반 처리합니다.")
            return "rule"

        # 프롬프트 구성
        prompt = self._build_prompt(domain, action, request)

        # KoELECTRA 추론
        try:
            result = self.koelectra.predict(prompt)
            strategy = result["strategy"]
            confidence = result["confidence"]

            logger.info(
                f"[OK] KoELECTRA 판단 결과: {strategy} (신뢰도: {confidence:.2f}) - {domain}.{action}"
            )

            return strategy

        except Exception as e:
            logger.error(f"[FAIL] KoELECTRA 판단 실패: {e}")
            # 폴백: 기본값으로 규칙 기반 처리
            logger.warning("⚠️  폴백: 규칙 기반으로 처리합니다.")
            return "rule"

    def _is_rule_based(self, domain: str, action: str) -> bool:
        """
        규칙 기반 여부 확인 (사전 필터링)

        Args:
            domain: 도메인 이름
            action: 액션 이름

        Returns:
            규칙 기반이면 True
        """
        # 도메인별 규칙 기반 액션 확인
        rule_actions = RULE_BASED_ACTIONS.get(domain, [])

        # "*"가 있으면 모든 액션이 규칙 기반
        if "*" in rule_actions:
            return True

        # 특정 액션이 규칙 기반 목록에 있는지 확인
        return action in rule_actions

    def _is_policy_based(self, domain: str, action: str) -> bool:
        """
        정책 기반 여부 확인 (사전 필터링)

        Args:
            domain: 도메인 이름
            action: 액션 이름

        Returns:
            정책 기반이면 True
        """
        # 도메인별 정책 기반 액션 확인
        policy_actions = POLICY_BASED_ACTIONS.get(domain, [])

        # 특정 액션이 정책 기반 목록에 있는지 확인
        return action in policy_actions
