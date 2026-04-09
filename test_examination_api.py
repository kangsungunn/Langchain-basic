"""
특허 심사 API 테스트 스크립트

사용법:
    1. FastAPI 서버 실행: uvicorn app.main:app --reload
    2. 테스트 실행: python test_examination_api.py
"""

import requests
import json


BASE_URL = "http://localhost:8000"


def test_rule_based_examination():
    """규칙기반 심사 테스트"""
    print("\n" + "=" * 60)
    print("1. 규칙기반 심사 테스트")
    print("=" * 60)

    # 테스트 데이터
    payload = {
        "examination_type": "rule_based",
        "patent_text": """
        본 발명은 인공지능을 이용한 이미지 인식 시스템에 관한 것이다.
        종래의 이미지 인식 시스템은 정확도가 낮았으나,
        본 발명은 딥러닝 모델을 활용하여 95% 이상의 정확도를 달성한다.
        """,
        "article_number": "제29조"
    }

    print(f"요청 데이터:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    response = requests.post(
        f"{BASE_URL}/admin/examination/examine",
        json=payload
    )

    print(f"\n상태 코드: {response.status_code}")
    print(f"응답:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_policy_based_examination():
    """정책기반 심사 테스트"""
    print("\n" + "=" * 60)
    print("2. 정책기반 심사 테스트")
    print("=" * 60)

    # 테스트 데이터
    payload = {
        "examination_type": "policy_based",
        "patent_text": """
        본 발명은 블록체인 기반 전자계약 시스템에 관한 것이다.
        기존 기술은 중앙화된 서버에 의존하여 보안이 취약했으나,
        본 발명은 분산 원장 기술을 활용하여 높은 보안성을 제공한다.
        스마트 계약을 통해 계약 이행을 자동화하고,
        위변조 방지 기능을 통해 신뢰성을 확보한다.
        """,
        "query": "이 발명이 진보성을 갖는가?"
    }

    print(f"요청 데이터:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    response = requests.post(
        f"{BASE_URL}/admin/examination/examine",
        json=payload
    )

    print(f"\n상태 코드: {response.status_code}")
    print(f"응답:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_validation_error():
    """입력 검증 에러 테스트"""
    print("\n" + "=" * 60)
    print("3. 입력 검증 에러 테스트")
    print("=" * 60)

    # 규칙기반인데 article_number가 없는 경우
    payload = {
        "examination_type": "rule_based",
        "patent_text": "테스트 특허 명세서"
        # article_number 누락
    }

    print(f"요청 데이터 (article_number 누락):")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    response = requests.post(
        f"{BASE_URL}/admin/examination/examine",
        json=payload
    )

    print(f"\n상태 코드: {response.status_code}")
    print(f"응답:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("특허 심사 API 테스트 시작")
    print("=" * 60)

    try:
        # 루트 엔드포인트 확인
        response = requests.get(BASE_URL)
        if response.status_code != 200:
            print(f"❌ 서버에 연결할 수 없습니다: {BASE_URL}")
            print("FastAPI 서버를 먼저 실행하세요:")
            print("  uvicorn app.main:app --reload")
            return

        print(f"✅ 서버 연결 성공: {BASE_URL}")

        # 각 테스트 실행
        test_rule_based_examination()
        test_policy_based_examination()
        test_validation_error()

        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print(f"\n❌ 서버에 연결할 수 없습니다: {BASE_URL}")
        print("FastAPI 서버를 먼저 실행하세요:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")


if __name__ == "__main__":
    main()
