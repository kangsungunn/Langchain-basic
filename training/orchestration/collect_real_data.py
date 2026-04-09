"""
실제 API 요청 로그 수집 스크립트

목적: 실제 운영 환경에서 DecisionMaker 호출 로그를 수집하여
      정책/규칙 판별 학습 데이터를 생성합니다.

사용 방법:
1. 이 스크립트를 백그라운드에서 실행
2. 실제 API 요청이 들어오면 자동으로 로그 수집
3. 수집된 로그를 JSONL 형식으로 변환
4. 학습 데이터로 사용

주의: 실제 데이터 수집이므로 프로덕션 환경에서 주의해서 사용하세요.
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.domain.v1.minso.hub.decision_maker import DecisionMaker
from app.core.utils.logger import get_logger

logger = get_logger(__name__)


class DataCollector:
    """실제 API 요청 로그 수집기"""

    def __init__(self, output_dir: Path):
        """
        Args:
            output_dir: 수집된 데이터를 저장할 디렉토리
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 로그 파일 경로
        self.log_file = self.output_dir / "collected_logs.jsonl"

        # DecisionMaker 인스턴스
        self.decision_maker = DecisionMaker()

        # 수집된 데이터 카운터
        self.collected_count = 0

    async def collect_request(
        self,
        domain: str,
        action: str,
        request: Dict[str, Any],
        actual_strategy: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        API 요청 로그 수집

        Args:
            domain: 도메인 이름
            action: 액션 이름
            request: 요청 데이터
            actual_strategy: 실제로 사용된 전략 (policy 또는 rule)
                           None이면 DecisionMaker로 판단

        Returns:
            수집된 데이터 (JSONL 형식) 또는 None
        """
        try:
            # DecisionMaker로 판단 (실제 전략)
            predicted_strategy = await self.decision_maker.determine_strategy(
                domain, action, request
            )

            # 실제 전략이 제공되지 않으면 예측 전략 사용
            if actual_strategy is None:
                actual_strategy = predicted_strategy

            # 프롬프트 생성 (DecisionMaker 내부 메서드 사용)
            prompt = self.decision_maker._build_prompt(domain, action, request)

            # 라벨 생성 (0: policy, 1: rule)
            label = 0 if actual_strategy == "policy" else 1

            # 수집 데이터 구성
            collected_data = {
                "text": prompt,
                "label": label,
                "metadata": {
                    "domain": domain,
                    "action": action,
                    "predicted_strategy": predicted_strategy,
                    "actual_strategy": actual_strategy,
                    "timestamp": datetime.now().isoformat(),
                    "request_summary": str(request)[:200]  # 요청 요약 (200자 제한)
                }
            }

            # JSONL 파일에 추가
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(collected_data, ensure_ascii=False) + "\n")

            self.collected_count += 1

            logger.info(
                f"[COLLECT] 데이터 수집 완료: {domain}.{action} "
                f"(예측: {predicted_strategy}, 실제: {actual_strategy}, 라벨: {label})"
            )

            return collected_data

        except Exception as e:
            logger.error(f"[ERROR] 데이터 수집 실패: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """수집 통계 반환"""
        policy_count = 0
        rule_count = 0

        if self.log_file.exists():
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if data.get("label") == 0:
                            policy_count += 1
                        else:
                            rule_count += 1

        return {
            "total": self.collected_count,
            "policy": policy_count,
            "rule": rule_count,
            "log_file": str(self.log_file)
        }

    def convert_to_training_format(
        self,
        output_file: Path,
        filter_by_agreement: bool = True
    ) -> int:
        """
        수집된 로그를 학습 형식으로 변환

        Args:
            output_file: 출력 파일 경로
            filter_by_agreement: 예측과 실제가 일치하는 경우만 포함 (기본값: True)

        Returns:
            변환된 데이터 개수
        """
        if not self.log_file.exists():
            logger.warning(f"[WARN] 로그 파일이 없습니다: {self.log_file}")
            return 0

        converted_count = 0

        with open(self.log_file, "r", encoding="utf-8") as f_in, \
             open(output_file, "w", encoding="utf-8") as f_out:

            for line in f_in:
                if not line.strip():
                    continue

                data = json.loads(line)
                metadata = data.get("metadata", {})

                # 예측과 실제가 일치하는 경우만 포함 (옵션)
                if filter_by_agreement:
                    predicted = metadata.get("predicted_strategy")
                    actual = metadata.get("actual_strategy")
                    if predicted != actual:
                        continue

                # 학습 형식으로 변환
                training_data = {
                    "text": data["text"],
                    "label": data["label"]
                }

                f_out.write(json.dumps(training_data, ensure_ascii=False) + "\n")
                converted_count += 1

        logger.info(f"[CONVERT] 학습 형식 변환 완료: {converted_count}개")
        return converted_count


async def main():
    """메인 함수 (예시)"""
    print("=" * 80)
    print("실제 API 요청 로그 수집 스크립트")
    print("=" * 80)

    # 출력 디렉토리 설정
    output_dir = project_root / "training" / "data" / "collected_logs"
    collector = DataCollector(output_dir)

    print(f"\n출력 디렉토리: {output_dir}")
    print(f"로그 파일: {collector.log_file}")

    # 예시: 테스트 요청 수집
    print("\n" + "-" * 80)
    print("테스트 요청 수집 (예시)")
    print("-" * 80)

    test_cases = [
        ("reasoning", "comprehensive_analysis", {"user_answer_id": "test-1"}, "policy"),
        ("training", "create_training_data", {"problem_text": "test"}, "rule"),
        ("submission", "create_text_answer", {"problem_id": "test", "content": "test"}, "rule"),
    ]

    for domain, action, request, actual_strategy in test_cases:
        await collector.collect_request(domain, action, request, actual_strategy)

    # 통계 출력
    stats = collector.get_statistics()
    print("\n" + "=" * 80)
    print("수집 통계")
    print("=" * 80)
    print(f"총 수집 개수: {stats['total']}")
    print(f"정책 기반: {stats['policy']}")
    print(f"규칙 기반: {stats['rule']}")
    print(f"로그 파일: {stats['log_file']}")

    # 학습 형식으로 변환
    print("\n" + "-" * 80)
    print("학습 형식으로 변환")
    print("-" * 80)

    training_file = output_dir / "train_collected.jsonl"
    converted_count = collector.convert_to_training_format(training_file)
    print(f"변환 완료: {converted_count}개 → {training_file}")

    print("\n" + "=" * 80)
    print("완료")
    print("=" * 80)
    print("\n사용 방법:")
    print("1. 실제 API 요청이 들어올 때 이 스크립트를 백그라운드에서 실행")
    print("2. 수집된 로그를 학습 형식으로 변환")
    print("3. 학습 데이터로 사용")


if __name__ == "__main__":
    asyncio.run(main())
