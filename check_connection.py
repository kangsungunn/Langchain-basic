"""
LangChain과 LangGraph 연결 상태 확인 스크립트
"""
import requests
import json
import sys
import io

# Windows 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

def check_endpoints():
    """등록된 엔드포인트 확인"""
    print("=" * 60)
    print("🔍 엔드포인트 확인")
    print("=" * 60)

    try:
        # OpenAPI 스펙 가져오기
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if response.status_code == 200:
            spec = response.json()
            paths = spec.get("paths", {})

            # LangChain 엔드포인트
            print("\n📚 LangChain 엔드포인트:")
            langchain_endpoints = [
                "/api/chat/rag",
                "/api/chat/general",
                "/api/chat"
            ]
            for endpoint in langchain_endpoints:
                if endpoint in paths:
                    methods = list(paths[endpoint].keys())
                    print(f"  ✅ {endpoint} - {methods}")
                else:
                    print(f"  ❌ {endpoint} - 없음")

            # LangGraph 엔드포인트
            print("\n🔄 LangGraph 엔드포인트:")
            langgraph_endpoints = [
                "/api/chat/langgraph/rag",
                "/api/chat/langgraph/tool",
                "/api/chat/langgraph"
            ]
            for endpoint in langgraph_endpoints:
                if endpoint in paths:
                    methods = list(paths[endpoint].keys())
                    print(f"  ✅ {endpoint} - {methods}")
                else:
                    print(f"  ❌ {endpoint} - 없음")

            return True
        else:
            print(f"❌ OpenAPI 스펙을 가져올 수 없습니다: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def test_langchain_endpoint():
    """LangChain 엔드포인트 테스트"""
    print("\n" + "=" * 60)
    print("🧪 LangChain 엔드포인트 테스트")
    print("=" * 60)

    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/general",
            json={"message": "안녕하세요"},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ LangChain 엔드포인트 작동 중")
            print(f"   답변: {result.get('answer', 'N/A')[:50]}...")
            return True
        else:
            print(f"❌ LangChain 엔드포인트 오류: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def test_langgraph_endpoint():
    """LangGraph 엔드포인트 테스트"""
    print("\n" + "=" * 60)
    print("🧪 LangGraph 엔드포인트 테스트")
    print("=" * 60)

    try:
        # Tool calling 모드 테스트 (RAG 없이)
        response = requests.post(
            f"{BASE_URL}/api/chat/langgraph/tool",
            json={"message": "안녕하세요"},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ LangGraph 엔드포인트 작동 중")
            print(f"   답변: {result.get('answer', 'N/A')[:50]}...")
            print(f"   출처: {result.get('sources', [])}")
            return True
        else:
            print(f"❌ LangGraph 엔드포인트 오류: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    print("🚀 LangChain & LangGraph 연결 상태 확인\n")

    # 서버 확인
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print("❌ 서버가 실행 중이지 않습니다.")
            return
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("   서버를 먼저 실행하세요:")
        print("   python -m uvicorn app.api_server_refactored:app --host 0.0.0.0 --port 8000")
        return

    print("✅ 서버 연결 확인됨\n")

    # 엔드포인트 확인
    endpoints_ok = check_endpoints()

    # 실제 테스트
    langchain_ok = test_langchain_endpoint()
    langgraph_ok = test_langgraph_endpoint()

    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 연결 상태 요약")
    print("=" * 60)
    print(f"엔드포인트 등록: {'✅' if endpoints_ok else '❌'}")
    print(f"LangChain 작동: {'✅' if langchain_ok else '❌'}")
    print(f"LangGraph 작동: {'✅' if langgraph_ok else '❌'}")

    if endpoints_ok and langchain_ok and langgraph_ok:
        print("\n✅ LangChain과 LangGraph가 모두 정상적으로 연결되어 있습니다!")
    else:
        print("\n⚠️ 일부 기능이 정상 작동하지 않을 수 있습니다.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n확인이 중단되었습니다.")
