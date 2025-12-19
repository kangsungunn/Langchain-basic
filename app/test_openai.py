"""
OpenAI API 연결 테스트 스크립트

OpenAI API 키가 올바르게 설정되었는지 확인하고
기본적인 API 호출을 테스트합니다.
"""
import os
import sys


def print_banner(text: str) -> None:
    """배너를 출력합니다."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def test_openai_setup() -> None:
    """OpenAI 설정을 테스트합니다."""
    print_banner("OpenAI API 연결 테스트")

    # Step 1: API 키 확인
    print("\n[Step 1] API 키 확인")
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다!")
        print("\n해결 방법:")
        print("1. .env 파일에 OPENAI_API_KEY를 추가하세요")
        print("2. docker-compose.yaml에 환경 변수가 설정되어 있는지 확인하세요")
        sys.exit(1)

    # API 키 일부만 표시 (보안)
    masked_key = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 11 else "***"
    print(f"✅ API 키 발견: {masked_key}")

    # Step 2: OpenAI 패키지 확인
    print("\n[Step 2] OpenAI 패키지 확인")
    try:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        print("✅ langchain-openai 패키지 설치됨")
    except ImportError as e:
        print(f"❌ langchain-openai 패키지를 찾을 수 없습니다: {e}")
        print("\n해결 방법:")
        print("pip install langchain-openai")
        sys.exit(1)

    # Step 3: ChatGPT 연결 테스트
    print("\n[Step 3] ChatGPT API 연결 테스트")
    print("📡 GPT-4o-mini 모델에 연결 중...")

    try:
        chat = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=api_key
        )

        # 간단한 질문
        test_message = "안녕! 간단히 인사만 해줘."
        print(f"\n💬 테스트 메시지: '{test_message}'")

        response = chat.invoke(test_message)
        print(f"\n🤖 ChatGPT 응답:")
        print(f"   {response.content}")
        print("\n✅ ChatGPT 연결 성공!")

    except Exception as e:
        print(f"\n❌ ChatGPT 연결 실패: {e}")
        print("\n가능한 원인:")
        print("1. API 키가 올바르지 않음")
        print("2. 결제 수단이 등록되지 않음")
        print("3. 크레딧 또는 한도 초과")
        print("4. 네트워크 연결 문제")
        print("\nhttps://platform.openai.com/account/billing 에서 확인하세요")
        sys.exit(1)

    # Step 4: Embeddings 연결 테스트
    print("\n[Step 4] Embeddings API 연결 테스트")
    print("📡 text-embedding-3-small 모델에 연결 중...")

    try:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key
        )

        # 간단한 텍스트 임베딩
        test_text = "테스트 문장입니다."
        print(f"\n📝 테스트 텍스트: '{test_text}'")

        vector = embeddings.embed_query(test_text)

        print(f"\n🔢 생성된 벡터 정보:")
        print(f"   차원: {len(vector)}")
        print(f"   샘플 값: [{vector[0]:.4f}, {vector[1]:.4f}, {vector[2]:.4f}, ...]")
        print("\n✅ Embeddings 연결 성공!")

    except Exception as e:
        print(f"\n❌ Embeddings 연결 실패: {e}")
        print("\n가능한 원인:")
        print("1. API 키가 올바르지 않음")
        print("2. 결제 수단이 등록되지 않음")
        print("3. 네트워크 연결 문제")
        sys.exit(1)

    # Step 5: 비용 정보 안내
    print_banner("비용 정보")
    print("\n방금 테스트에서 사용한 비용:")
    print("  • ChatGPT (1회 대화): ~$0.0001 (약 0.1원)")
    print("  • Embeddings (1개): ~$0.000001 (약 0.001원)")
    print("  • 총 예상 비용: ~$0.0002 (약 0.3원)")
    print("\n안심하세요! 테스트는 거의 무료입니다. 😊")

    # 최종 성공 메시지
    print_banner("✅ 모든 테스트 통과!")
    print("\n🎉 OpenAI API 연결이 완벽하게 설정되었습니다!")
    print("\n다음 단계:")
    print("  1. 실제 임베딩으로 벡터 저장 테스트")
    print("  2. RAG 챗봇 구현")
    print("  3. 웹 인터페이스 추가")
    print()


if __name__ == "__main__":
    try:
        test_openai_setup()
    except KeyboardInterrupt:
        print("\n\n⚠️  테스트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

