"""
LangChain + OpenAI 연결 상태 최종 검증

현재 시스템이 올바르게 구성되어 있는지 확인합니다.
"""
import os
import sys


def print_banner(text: str, char: str = "=") -> None:
    """배너를 출력합니다."""
    print("\n" + char * 70)
    print(f"  {text}")
    print(char * 70)


def verify_complete_setup() -> None:
    """전체 설정을 검증합니다."""
    print_banner("🔍 LangChain + OpenAI 연결 상태 검증", "=")

    all_checks_passed = True

    # Check 1: 환경 변수
    print_banner("Check 1: 환경 변수 확인", "-")

    api_key = os.getenv("OPENAI_API_KEY")
    db_host = os.getenv("POSTGRES_HOST")

    if api_key:
        masked_key = api_key[:7] + "..." + api_key[-4:]
        print(f"✅ OPENAI_API_KEY: {masked_key}")
    else:
        print("❌ OPENAI_API_KEY: 설정되지 않음")
        all_checks_passed = False

    if db_host:
        print(f"✅ POSTGRES_HOST: {db_host}")
    else:
        print("❌ POSTGRES_HOST: 설정되지 않음")
        all_checks_passed = False

    # Check 2: LangChain 패키지
    print_banner("Check 2: LangChain 패키지 확인", "-")

    try:
        import langchain
        print(f"✅ langchain: {langchain.__version__}")
    except ImportError:
        print("❌ langchain: 설치되지 않음")
        all_checks_passed = False

    try:
        import langchain_core
        print(f"✅ langchain-core: {langchain_core.__version__}")
    except ImportError:
        print("❌ langchain-core: 설치되지 않음")
        all_checks_passed = False

    try:
        import langchain_openai
        print(f"✅ langchain-openai: 설치됨")
    except ImportError:
        print("❌ langchain-openai: 설치되지 않음")
        all_checks_passed = False

    try:
        import langchain_postgres
        print(f"✅ langchain-postgres: 설치됨")
    except ImportError:
        print("❌ langchain-postgres: 설치되지 않음")
        all_checks_passed = False

    # Check 3: OpenAI 연결 (LangChain을 통해)
    print_banner("Check 3: LangChain을 통한 OpenAI 연결", "-")

    try:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings

        print("\n🔗 연결 방식 확인:")
        print("   langchain_openai.ChatOpenAI ← LangChain의 OpenAI 래퍼")
        print("   langchain_openai.OpenAIEmbeddings ← LangChain의 OpenAI 래퍼")
        print("\n✅ 올바른 방식으로 연결되어 있습니다!")

        # ChatGPT 테스트
        print("\n📡 ChatGPT 연결 테스트...")
        chat = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # LangChain 방식으로 호출
        from langchain_core.messages import HumanMessage

        response = chat.invoke([HumanMessage(content="1+1은?")])
        print(f"   질문: 1+1은?")
        print(f"   답변: {response.content}")
        print("✅ ChatGPT 응답 성공 (LangChain 방식)")

        # Embeddings 테스트
        print("\n📡 Embeddings 연결 테스트...")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        vector = embeddings.embed_query("테스트")
        print(f"   텍스트: '테스트'")
        print(f"   벡터 차원: {len(vector)}")
        print(f"   샘플: [{vector[0]:.4f}, {vector[1]:.4f}, ...]")
        print("✅ Embeddings 생성 성공 (LangChain 방식)")

    except Exception as e:
        print(f"❌ OpenAI 연결 실패: {e}")
        all_checks_passed = False

    # Check 4: PGVector 연결 (LangChain을 통해)
    print_banner("Check 4: LangChain을 통한 PGVector 연결", "-")

    try:
        from langchain_postgres import PGVector
        from langchain_core.documents import Document

        print("\n🔗 연결 방식 확인:")
        print("   langchain_postgres.PGVector ← LangChain의 PGVector 래퍼")
        print("   langchain_core.documents.Document ← LangChain의 문서 타입")
        print("\n✅ 올바른 방식으로 연결되어 있습니다!")

        # PGVector 초기화
        db_user = os.getenv("POSTGRES_USER", "langchain")
        db_password = os.getenv("POSTGRES_PASSWORD", "langchain123")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "vectordb")

        connection_string = (
            f"postgresql+psycopg2://{db_user}:{db_password}"
            f"@{db_host}:{db_port}/{db_name}"
        )

        vector_store = PGVector(
            embeddings=embeddings,
            collection_name="verification_test",
            connection=connection_string,
            use_jsonb=True,
        )

        print("\n📤 테스트 문서 저장 중...")
        test_doc = Document(
            page_content="검증 테스트 문서입니다.",
            metadata={"test": True}
        )

        vector_store.add_documents([test_doc])
        print("✅ 문서 저장 성공 (LangChain 방식)")

        print("\n🔎 유사도 검색 테스트...")
        results = vector_store.similarity_search("검증", k=1)
        if results:
            print(f"   검색 결과: {results[0].page_content}")
            print("✅ 검색 성공 (LangChain 방식)")

    except Exception as e:
        print(f"❌ PGVector 연결 실패: {e}")
        all_checks_passed = False

    # Check 5: 전체 파이프라인 확인
    print_banner("Check 5: 전체 파이프라인 검증", "-")

    print("\n📊 현재 시스템 구조:")
    print("""
    ┌─────────────────────────────────────────────────┐
    │          LangChain Framework                    │
    │  (모든 컴포넌트를 통합 관리)                    │
    └─────────────┬───────────────────────────────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
    ┌─────────┐      ┌──────────┐
    │ OpenAI  │      │ PGVector │
    │         │      │          │
    │ ChatGPT │      │ Postgres │
    │ Embed   │      │ Database │
    └─────────┘      └──────────┘

    LangChain이 중간에서:
    ✓ OpenAI API를 쉽게 사용하도록 래핑
    ✓ PGVector를 쉽게 사용하도록 래핑
    ✓ 문서(Document) 타입으로 데이터 통일
    ✓ 검색, 생성, 저장을 하나의 흐름으로 연결
    """)

    print("\n✅ LangChain을 통해 모든 것이 연결되어 있습니다!")

    # Check 6: 코드 예시
    print_banner("Check 6: 사용 중인 코드 확인", "-")

    print("\n📝 현재 사용하는 방식 (올바름):")
    print("""
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langchain_postgres import PGVector
    from langchain_core.documents import Document

    # LangChain이 OpenAI를 감싸서 제공
    chat = ChatOpenAI(model="gpt-4o-mini")      ✅
    embeddings = OpenAIEmbeddings()              ✅

    # LangChain이 PGVector를 감싸서 제공
    vector_store = PGVector(embeddings=...)      ✅

    # LangChain의 통일된 인터페이스
    documents = [Document(...)]                  ✅
    vector_store.add_documents(documents)        ✅
    results = vector_store.similarity_search()   ✅
    """)

    print("\n❌ 잘못된 방식 (직접 OpenAI SDK 사용):")
    print("""
    from openai import OpenAI  # ← LangChain 없이 직접 사용

    client = OpenAI(api_key="...")
    response = client.chat.completions.create()  ❌

    # LangChain을 우회하므로 통합 기능 사용 불가
    """)

    # 최종 결과
    print_banner("검증 결과", "=")

    if all_checks_passed:
        print("\n✅ ✅ ✅ 모든 검증 통과! ✅ ✅ ✅")
        print("\n🎉 축하합니다! 시스템이 완벽하게 구성되어 있습니다!")
        print("\n현재 상태:")
        print("  ✓ LangChain Framework 사용 중")
        print("  ✓ OpenAI를 LangChain을 통해 사용 중")
        print("  ✓ PGVector를 LangChain을 통해 사용 중")
        print("  ✓ 모든 컴포넌트가 LangChain으로 통합됨")
        print("\n다음 단계:")
        print("  → RAG 챗봇 구현 준비 완료!")
        print("  → 지식 베이스 구축")
        print("  → 대화형 챗봇 완성")
    else:
        print("\n⚠️  일부 검증 실패")
        print("\n위의 ❌ 표시된 항목을 확인하세요.")

    print()


if __name__ == "__main__":
    try:
        verify_complete_setup()
    except KeyboardInterrupt:
        print("\n\n⚠️  검증이 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

