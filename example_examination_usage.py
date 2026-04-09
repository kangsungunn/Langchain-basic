"""
특허 심사 시스템 간단 사용 예제

이 스크립트는 FastAPI 서버가 실행 중일 때 사용할 수 있습니다.
"""

import requests
import json


def example_rule_based():
    """규칙기반 심사 예제"""
    print("=" * 60)
    print("규칙기반 심사 예제")
    print("=" * 60)

    # API 호출
    response = requests.post(
        "http://localhost:8000/admin/examination/examine",
        json={
            "examination_type": "rule_based",
            "patent_text": """
            본 발명은 자율주행 자동차의 경로 계획 시스템에 관한 것이다.
            종래의 경로 계획 시스템은 고정된 알고리즘을 사용하여
            돌발 상황에 대한 대응이 느렸으나,
            본 발명은 강화학습 기반 동적 경로 계획을 통해
            실시간으로 최적 경로를 선택할 수 있다.
            """,
            "article_number": "제29조"
        }
    )

    # 결과 출력
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 심사 결과: {result['result']['decision']}")
        print(f"📊 신뢰도: {result['result']['confidence']:.2%}")
        print(f"📝 분석: {result['result']['analysis']}")
    else:
        print(f"❌ 오류 발생: {response.status_code}")
        print(response.text)


def example_policy_based():
    """정책기반 심사 예제"""
    print("\n" + "=" * 60)
    print("정책기반 심사 예제")
    print("=" * 60)

    # API 호출
    response = requests.post(
        "http://localhost:8000/admin/examination/examine",
        json={
            "examination_type": "policy_based",
            "patent_text": """
            본 발명은 양자 컴퓨팅을 활용한 암호화 시스템에 관한 것이다.
            기존의 RSA 암호화 방식은 양자 컴퓨터에 취약하다는 문제가 있었으나,
            본 발명은 격자 기반 암호화(Lattice-based Cryptography)를 사용하여
            양자 컴퓨터 공격에도 안전한 암호화를 제공한다.
            특히, Ring-LWE 알고리즘을 개선하여 기존 대비 30% 빠른 처리 속도를 달성하였다.
            """,
            "query": "이 발명의 진보성과 산업상 이용가능성을 평가하라"
        }
    )

    # 결과 출력
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 최종 결정: {result['result']['decision']}")
        print(f"📊 신뢰도: {result['result']['confidence']:.2%}")
        print(f"🧠 추론: {result['result']['reasoning']}")
        print(f"📝 상세: {result['result']['decision_detail']}")
        print(f"\n워크플로우 단계:")
        for i, step in enumerate(result['result']['workflow_steps'], 1):
            print(f"  {i}. {step}")
    else:
        print(f"❌ 오류 발생: {response.status_code}")
        print(response.text)


def main():
    """메인 실행"""
    print("\n🚀 특허 심사 시스템 사용 예제\n")

    # 서버 연결 확인
    try:
        response = requests.get("http://localhost:8000/", timeout=2)
        if response.status_code != 200:
            print("❌ 서버에 연결할 수 없습니다.")
            print("FastAPI 서버를 먼저 실행하세요:")
            print("  uvicorn app.main:app --reload")
            return
        print("✅ 서버 연결 성공\n")
    except requests.exceptions.RequestException:
        print("❌ 서버에 연결할 수 없습니다.")
        print("FastAPI 서버를 먼저 실행하세요:")
        print("  uvicorn app.main:app --reload")
        return

    # 예제 실행
    example_rule_based()
    example_policy_based()

    print("\n" + "=" * 60)
    print("✅ 모든 예제 실행 완료!")
    print("=" * 60)
    print("\n더 자세한 정보는 EXAMINATION_API_GUIDE.md를 참고하세요.")


if __name__ == "__main__":
    main()
