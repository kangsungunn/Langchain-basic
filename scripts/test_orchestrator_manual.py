"""
오케스트레이터 수동 테스트 스크립트

실제 API 서버가 실행 중일 때 테스트할 수 있는 스크립트
"""

import asyncio
import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000/api/v1"


def test_rule_based_request():
    """규칙 기반 요청 테스트 (학습 데이터 생성)"""
    print("\n" + "="*80)
    print("📋 규칙 기반 요청 테스트: 학습 데이터 생성")
    print("="*80)

    url = f"{BASE_URL}/training/data"
    data = {
        "problem_text": "민사소송법에서 소송요건의 의미를 설명하시오.",
        "reference_answer_text": "소송요건은 소송을 제기하기 위해 필요한 요건으로...",
        "user_answer_text": "소송요건은 소송을 제기하기 위한 조건입니다.",
        "labels": {}
    }

    try:
        response = requests.post(url, json=data)
        print(f"✅ 상태 코드: {response.status_code}")
        print(f"📊 응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        if response.status_code == 201:
            print("✅ 규칙 기반 요청 성공!")
        else:
            print(f"❌ 요청 실패: {response.text}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def create_test_data():
    """테스트용 데이터 생성"""
    print("\n" + "="*80)
    print("📝 테스트용 데이터 생성")
    print("="*80)

    # 1. 텍스트 답안 생성
    answer_url = f"{BASE_URL}/submission/answers/text"
    answer_data = {
        "problem_id": "test-problem-001",
        "content": "민사소송법에서 소송요건은 소송을 제기하기 위해 필요한 요건입니다. 소송요건이 충족되지 않으면 소송이 각하됩니다.",
        "submission_type": "text"
    }

    try:
        answer_response = requests.post(answer_url, json=answer_data)
        if answer_response.status_code == 201:
            user_answer = answer_response.json()
            user_answer_id = user_answer.get("id")
            print(f"✅ 사용자 답안 생성 완료: {user_answer_id}")
            return user_answer_id
        else:
            print(f"⚠️  사용자 답안 생성 실패: {answer_response.text}")
            return None
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None


def test_policy_based_request():
    """정책 기반 요청 테스트 (종합 분석)"""
    print("\n" + "="*80)
    print("🎯 정책 기반 요청 테스트: 종합 분석")
    print("="*80)

    # 테스트용 데이터 생성
    user_answer_id = create_test_data()
    if not user_answer_id:
        print("⚠️  테스트 데이터 생성 실패. 테스트를 건너뜁니다.")
        return

    url = f"{BASE_URL}/reasoning/analyze/comprehensive"
    data = {
        "user_answer_id": user_answer_id,
        "reference_answer_id": None,  # 선택 사항
        "problem_id": None,  # 선택 사항
        "save_result": True
    }

    try:
        response = requests.post(url, json=data)
        print(f"✅ 상태 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"📊 응답 키: {list(result.keys())}")
            if "task_id" in result:
                print(f"📋 작업 ID: {result['task_id']}")
            print("✅ 정책 기반 요청 성공!")
        else:
            print(f"❌ 요청 실패: {response.text}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def test_feedback_generation():
    """피드백 생성 테스트 (정책 기반)"""
    print("\n" + "="*80)
    print("💬 정책 기반 요청 테스트: 피드백 생성")
    print("="*80)

    # 테스트용 데이터 생성
    user_answer_id = create_test_data()
    if not user_answer_id:
        print("⚠️  테스트 데이터 생성 실패. 테스트를 건너뜁니다.")
        return

    # 먼저 종합 분석을 실행하여 reasoning_task_id 얻기
    analysis_url = f"{BASE_URL}/reasoning/analyze/comprehensive"
    analysis_data = {
        "user_answer_id": user_answer_id,
        "save_result": True
    }

    try:
        analysis_response = requests.post(analysis_url, json=analysis_data)
        if analysis_response.status_code != 200:
            print(f"⚠️  종합 분석 실패: {analysis_response.text}")
            print("⚠️  피드백 생성을 위해 종합 분석이 필요합니다. 테스트를 건너뜁니다.")
            return

        analysis_result = analysis_response.json()
        reasoning_task_id = analysis_result.get("task_id")

        if not reasoning_task_id:
            print("⚠️  reasoning_task_id를 찾을 수 없습니다. 테스트를 건너뜁니다.")
            return

        # 피드백 생성
        feedback_url = f"{BASE_URL}/feedback/generate"
        feedback_data = {
            "user_answer_id": user_answer_id,
            "reasoning_task_id": reasoning_task_id,
            "feedback_type": "comprehensive",
            "include_suggestions": True
        }

        response = requests.post(feedback_url, json=feedback_data)
        print(f"✅ 상태 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"📊 응답 키: {list(result.keys())}")
            print("✅ 피드백 생성 성공!")
        else:
            print(f"❌ 요청 실패: {response.text}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("🧪 오케스트레이터 통합 테스트")
    print("="*80)
    print("\n⚠️  주의: 백엔드 서버가 실행 중이어야 합니다.")
    print("   실행 방법: python -m uvicorn app.main:app --reload")
    print("\n" + "="*80)

    # 규칙 기반 테스트
    test_rule_based_request()

    # 정책 기반 테스트 (테스트 데이터 자동 생성)
    test_policy_based_request()

    # 피드백 생성 테스트 (테스트 데이터 자동 생성)
    test_feedback_generation()

    print("\n" + "="*80)
    print("✅ 테스트 완료!")
    print("="*80)
    print("\n💡 백엔드 로그를 확인하여 오케스트레이터 동작을 확인하세요:")
    print("   - 규칙 기반: '📋 규칙 기반 전략: 일반 서비스로 직접 라우팅'")
    print("   - 정책 기반: '🎯 정책 기반 전략: Star 토폴로지로 라우팅'")


if __name__ == "__main__":
    main()
