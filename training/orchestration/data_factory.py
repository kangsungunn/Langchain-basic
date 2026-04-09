"""
더미 학습 데이터 생성 스크립트

⚠️ 임시 개발/테스트용입니다.
실제 데이터가 준비되면 이 파일은 제거해도 됩니다.

실제 프로덕션에서는 실제 API 요청 로그를 수집하여 JSONL 형식으로 변환합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.domain.v1.minso.hub.decision_maker import DecisionMaker


def generate_dummy_training_data(
    output_dir: Optional[str] = None,
    num_samples: int = 200
) -> Dict[str, int]:
    """
    더미 학습 데이터 생성 (임시 개발/테스트용)

    ⚠️ 실제 데이터가 준비되면 이 함수는 사용하지 않습니다.

    Args:
        output_dir: 출력 디렉토리 (기본값: training/data/policy_rule_classification)
        num_samples: 생성할 샘플 수 (기본값: 200)

    Returns:
        dict: 생성된 파일별 샘플 수
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "training" / "data" / "policy_rule_classification"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # DecisionMaker 인스턴스 생성 (프롬프트 구성 로직 사용)
    decision_maker = DecisionMaker()

    # 더미 데이터 생성 (실제 데이터 기준으로 작성된 코드 사용)
    samples = _create_dummy_samples(decision_maker, num_samples)

    # 학습/검증/테스트 분할 (80/10/10)
    train_size = int(len(samples) * 0.8)
    val_size = int(len(samples) * 0.1)

    train_data = samples[:train_size]
    val_data = samples[train_size:train_size + val_size]
    test_data = samples[train_size + val_size:]

    # JSONL 파일로 저장
    _save_jsonl(output_dir / "train.jsonl", train_data)
    _save_jsonl(output_dir / "val.jsonl", val_data)
    _save_jsonl(output_dir / "test.jsonl", test_data)

    print(f"✅ 더미 학습 데이터 생성 완료")
    print(f"   └─ 학습 데이터: {len(train_data)}개")
    print(f"   └─ 검증 데이터: {len(val_data)}개")
    print(f"   └─ 테스트 데이터: {len(test_data)}개")
    print(f"   └─ 출력 경로: {output_dir}")

    return {
        "train": len(train_data),
        "val": len(val_data),
        "test": len(test_data)
    }


def _create_dummy_samples(decision_maker: DecisionMaker, num_samples: int) -> List[Dict[str, Any]]:
    """
    더미 샘플 생성

    실제 DecisionMaker의 프롬프트 구성 로직을 사용하여 더미 샘플을 생성합니다.

    Args:
        decision_maker: DecisionMaker 인스턴스
        num_samples: 생성할 샘플 수

    Returns:
        list: 더미 샘플 리스트
    """
    samples = []

    # 규칙 기반 액션 (label: 0)
    rule_based_cases = [
        ("training", "create_training_data", {"problem_text": "민사소송법 문제", "reference_answer_text": "모범답안", "user_answer_text": "사용자 답안"}),
        ("training", "get_training_data", {"training_data_id": "test-id"}),
        ("submission", "create_text_answer", {"problem_id": "test-problem", "content": "답안 내용"}),
        ("submission", "get_answer", {"answer_id": "test-answer"}),
        ("reference", "create_problem", {"title": "문제 제목", "content": "문제 내용"}),
        ("reference", "get_problem", {"problem_id": "test-problem"}),
        ("reasoning", "get_tasks", {}),
        ("reasoning", "get_task", {"task_id": "test-task"}),
        ("feedback", "get_feedbacks", {"user_answer_id": "test-answer"}),
        ("feedback", "get_feedback", {"feedback_id": "test-feedback"}),
    ]

    # 정책 기반 액션 (label: 1)
    policy_based_cases = [
        ("reasoning", "comprehensive_analysis", {"user_answer_id": "test-answer", "reference_answer_id": "test-ref", "problem_id": "test-problem"}),
        ("reasoning", "analyze_issues", {"user_answer_id": "test-answer", "reference_answer_id": "test-ref", "problem_id": "test-problem"}),
        ("reasoning", "analyze_logic", {"user_answer_id": "test-answer", "reference_answer_id": "test-ref", "problem_id": "test-problem"}),
        ("reasoning", "analyze_expression", {"user_answer_id": "test-answer"}),
        ("feedback", "generate", {"user_answer_id": "test-answer", "reasoning_task_id": "test-task"}),
        ("feedback", "generate_from_reasoning", {"reasoning_task_id": "test-task"}),
        ("training", "start_training", {"model_type": "exaone", "training_data_ids": ["test-id"]}),
    ]

    # 규칙 기반 샘플 생성
    rule_samples_per_case = num_samples // 2 // len(rule_based_cases)
    for domain, action, request_data in rule_based_cases:
        for i in range(rule_samples_per_case):
            # 실제 DecisionMaker의 프롬프트 구성 로직 사용
            prompt = decision_maker._build_prompt(domain, action, request_data)
            samples.append({
                "text": prompt,
                "label": 0  # rule (규칙 기반)
            })

    # 정책 기반 샘플 생성
    policy_samples_per_case = num_samples // 2 // len(policy_based_cases)
    for domain, action, request_data in policy_based_cases:
        for i in range(policy_samples_per_case):
            # 실제 DecisionMaker의 프롬프트 구성 로직 사용
            prompt = decision_maker._build_prompt(domain, action, request_data)
            samples.append({
                "text": prompt,
                "label": 1  # policy (정책 기반)
            })

    # 샘플 셔플
    import random
    random.shuffle(samples)

    return samples


def _save_jsonl(file_path: Path, data: List[Dict[str, Any]]):
    """
    JSONL 파일로 저장

    Args:
        file_path: 저장할 파일 경로
        data: 저장할 데이터 리스트
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')




if __name__ == "__main__":
    # 더미 데이터 생성 테스트
    result = generate_dummy_training_data(num_samples=200)
    print(f"\n📊 생성 결과: {result}")
