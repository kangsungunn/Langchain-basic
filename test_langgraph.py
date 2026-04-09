"""
LangGraph 로컬 테스트 스크립트

서버가 실행 중일 때 API를 테스트합니다.
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"


def test_langgraph_rag():
    """LangGraph RAG 모드 테스트"""
    url = f"{BASE_URL}/api/chat/langgraph/rag"
    data = {
        "message": "안녕하세요! LangGraph에 대해 알려주세요."
    }

    try:
        response = requests.post(url, json=data, timeout=60)
        print("=" * 60)
        print("LangGraph RAG 모드 테스트")
        print("=" * 60)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"답변: {result.get('answer', 'N/A')}")
            print(f"출처: {result.get('sources', [])}")
        else:
            print(f"Error: {response.text}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print()
        return False


def test_langgraph_tool():
    """LangGraph Tool calling 모드 테스트"""
    url = f"{BASE_URL}/api/chat/langgraph/tool"
    data = {
        "message": "현재 서버 시간을 알려주세요."
    }

    try:
        response = requests.post(url, json=data, timeout=60)
        print("=" * 60)
        print("LangGraph Tool calling 모드 테스트")
        print("=" * 60)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"답변: {result.get('answer', 'N/A')}")
            print(f"출처: {result.get('sources', [])}")
        else:
            print(f"Error: {response.text}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print()
        return False


def test_langgraph_integrated(use_rag: bool = True):
    """LangGraph 통합 엔드포인트 테스트"""
    url = f"{BASE_URL}/api/chat/langgraph"
    params = {"use_rag": str(use_rag).lower()}
    data = {
        "message": "RAG가 무엇인가요?" if use_rag else "서버 시간을 알려주세요."
    }

    try:
        response = requests.post(url, json=data, params=params, timeout=60)
        mode = "RAG" if use_rag else "Tool calling"
        print("=" * 60)
        print(f"LangGraph 통합 엔드포인트 테스트 ({mode} 모드)")
        print("=" * 60)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"답변: {result.get('answer', 'N/A')}")
            print(f"출처: {result.get('sources', [])}")
        else:
            print(f"Error: {response.text}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print()
        return False


def test_langchain_rag():
    """기존 LangChain RAG 모드 테스트 (비교용)"""
    url = f"{BASE_URL}/api/chat/rag"
    data = {
        "message": "안녕하세요!"
    }

    try:
        response = requests.post(url, json=data, timeout=60)
        print("=" * 60)
        print("LangChain RAG 모드 테스트 (비교용)")
        print("=" * 60)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"답변: {result.get('answer', 'N/A')}")
            print(f"출처: {result.get('sources', [])}")
        else:
            print(f"Error: {response.text}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print()
        return False


def check_server():
    """서버가 실행 중인지 확인"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 서버가 실행 중입니다.\n")
            return True
        else:
            print("❌ 서버가 정상적으로 응답하지 않습니다.")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("   서버가 실행 중인지 확인하세요.")
        print("   실행 명령어:")
        print("   cd app && python -m uvicorn api_server_refactored:app --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 LangGraph 로컬 테스트 시작\n")

    # 서버 확인
    if not check_server():
        sys.exit(1)

    # 테스트 실행
    results = []

    print("테스트를 시작합니다...\n")

    results.append(("LangGraph RAG", test_langgraph_rag()))
    results.append(("LangGraph Tool", test_langgraph_tool()))
    results.append(("LangGraph 통합 (RAG)", test_langgraph_integrated(use_rag=True)))
    results.append(("LangGraph 통합 (Tool)", test_langgraph_integrated(use_rag=False)))
    results.append(("LangChain RAG (비교)", test_langchain_rag()))

    # 결과 요약
    print("=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    for name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{name}: {status}")

    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    print(f"\n총 {total_count}개 테스트 중 {success_count}개 성공")

    if success_count == total_count:
        print("✅ 모든 테스트 통과!")
        return 0
    else:
        print("⚠️  일부 테스트 실패")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
        sys.exit(1)
