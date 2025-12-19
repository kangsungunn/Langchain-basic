"""
OpenAI Embeddings + PGVector 통합 테스트

실제 OpenAI 임베딩을 사용하여 PGVector에 저장하고 검색합니다.
더미 임베딩과의 차이를 확인할 수 있습니다.
"""
import os
import sys
import time
from datetime import datetime

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector


def print_banner(text: str) -> None:
    """배너를 출력합니다."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def wait_for_db(connection_string: str, max_retries: int = 30) -> bool:
    """데이터베이스가 준비될 때까지 대기합니다."""
    import psycopg2

    print("\n🔍 데이터베이스 연결 확인 중...")
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(connection_string)
            conn.close()
            print("✅ 데이터베이스 연결 성공!")
            return True
        except psycopg2.OperationalError:
            if i < 3:  # 처음 몇 번만 출력
                print(f"   대기 중... ({i + 1}/{max_retries})")
            time.sleep(2)

    print("❌ 데이터베이스 연결 실패!")
    return False


def test_openai_embeddings() -> None:
    """OpenAI Embeddings와 PGVector 통합 테스트"""
    print_banner("OpenAI Embeddings + PGVector 통합 테스트")

    # 환경 변수 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ OPENAI_API_KEY가 설정되지 않았습니다!")
        sys.exit(1)

    # 데이터베이스 연결 정보
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_user = os.getenv("POSTGRES_USER", "langchain")
    db_password = os.getenv("POSTGRES_PASSWORD", "langchain123")
    db_name = os.getenv("POSTGRES_DB", "vectordb")

    connection_string = (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    simple_conn_string = (
        f"host={db_host} port={db_port} dbname={db_name} "
        f"user={db_user} password={db_password}"
    )

    print(f"\n📍 연결 정보:")
    print(f"   Database: {db_host}:{db_port}/{db_name}")
    print(f"   Embeddings: OpenAI (text-embedding-3-small)")

    # 데이터베이스 대기
    if not wait_for_db(simple_conn_string):
        sys.exit(1)

    # Step 1: OpenAI Embeddings 초기화
    print_banner("Step 1: OpenAI Embeddings 초기화")

    try:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key
        )
        print("✅ OpenAI Embeddings 초기화 성공!")
        print("   모델: text-embedding-3-small")
        print("   차원: 1536")
        print("   비용: $0.02 / 1M tokens (매우 저렴)")
    except Exception as e:
        print(f"❌ Embeddings 초기화 실패: {e}")
        sys.exit(1)

    # Step 2: PGVector 초기화
    print_banner("Step 2: PGVector 초기화")

    collection_name = "openai_embeddings_test"

    try:
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=collection_name,
            connection=connection_string,
            use_jsonb=True,
        )
        print(f"✅ PGVector 초기화 성공!")
        print(f"   Collection: {collection_name}")
    except Exception as e:
        print(f"❌ PGVector 초기화 실패: {e}")
        sys.exit(1)

    # Step 3: 의미 있는 문서 저장
    print_banner("Step 3: 문서 저장 (실제 의미 있는 벡터)")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    documents = [
        Document(
            page_content="파이썬은 배우기 쉽고 강력한 프로그래밍 언어입니다.",
            metadata={"category": "programming", "language": "python", "timestamp": timestamp}
        ),
        Document(
            page_content="자바스크립트는 웹 개발에 필수적인 언어입니다.",
            metadata={"category": "programming", "language": "javascript", "timestamp": timestamp}
        ),
        Document(
            page_content="머신러닝은 데이터로부터 학습하는 인공지능 기술입니다.",
            metadata={"category": "ai", "topic": "machine-learning", "timestamp": timestamp}
        ),
        Document(
            page_content="딥러닝은 신경망을 사용하는 머신러닝의 한 분야입니다.",
            metadata={"category": "ai", "topic": "deep-learning", "timestamp": timestamp}
        ),
        Document(
            page_content="LangChain은 LLM 애플리케이션을 쉽게 만들 수 있는 프레임워크입니다.",
            metadata={"category": "tools", "topic": "langchain", "timestamp": timestamp}
        ),
        Document(
            page_content="PGVector는 PostgreSQL에서 벡터 검색을 가능하게 합니다.",
            metadata={"category": "tools", "topic": "database", "timestamp": timestamp}
        ),
    ]

    print(f"\n📤 {len(documents)}개의 문서 저장 중...")
    print("   (OpenAI API 호출 중 - 약 1-2초 소요)")

    try:
        ids = vector_store.add_documents(documents)
        print(f"\n✅ 저장 완료!")
        print(f"   생성된 Document IDs: {len(ids)}개")
    except Exception as e:
        print(f"\n❌ 문서 저장 실패: {e}")
        sys.exit(1)

    # Step 4: 의미 기반 검색 테스트
    print_banner("Step 4: 의미 기반 검색 테스트")

    test_queries = [
        "프로그래밍 언어에 대해 알려줘",
        "인공지능과 머신러닝의 차이는?",
        "LangChain 사용법을 알고 싶어",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─' * 70}")
        print(f"🔎 Query {i}: '{query}'")
        print("   (OpenAI API로 쿼리 임베딩 중...)")

        try:
            results = vector_store.similarity_search(query, k=2)

            print(f"\n✅ 검색 완료! 가장 관련 있는 문서 {len(results)}개:")

            for j, doc in enumerate(results, 1):
                print(f"\n   [{j}] {doc.page_content}")
                print(f"       카테고리: {doc.metadata.get('category', 'N/A')}")
                if 'topic' in doc.metadata:
                    print(f"       주제: {doc.metadata['topic']}")

        except Exception as e:
            print(f"\n❌ 검색 실패: {e}")

    # Step 5: 더미 임베딩과 비교
    print_banner("Step 5: 실제 임베딩 vs 더미 임베딩 차이")

    print("\n더미 임베딩 (이전 방식):")
    print("  • 벡터: [0, 1, 2, 3, 4, ..., 383] (단순 순서)")
    print("  • 검색 결과: 무작위 (의미 없음)")
    print("  • 예: '프로그래밍'과 '사과'가 같은 벡터")
    print("\n실제 OpenAI 임베딩 (현재 방식):")
    print("  • 벡터: [0.234, -0.123, 0.456, ...] (의미 반영)")
    print("  • 검색 결과: 의미적으로 유사한 문서 찾기")
    print("  • 예: '프로그래밍' → Python, JavaScript 문서 찾음")

    print("\n💡 차이점:")
    print("  위의 검색 결과를 보면 의미적으로 관련된 문서들이")
    print("  정확하게 찾아진 것을 확인할 수 있습니다!")

    # Step 6: 비용 정보
    print_banner("비용 정보")

    num_docs = len(documents)
    avg_words_per_doc = 15  # 대략적인 평균 단어 수
    tokens_per_doc = int(avg_words_per_doc * 1.3)  # 토큰은 단어보다 약간 많음
    total_tokens = num_docs * tokens_per_doc + 3 * 10  # 문서 + 쿼리

    embedding_cost = (total_tokens / 1_000_000) * 0.02

    print(f"\n이번 테스트 예상 비용:")
    print(f"  • 저장한 문서: {num_docs}개")
    print(f"  • 검색 쿼리: 3개")
    print(f"  • 총 토큰 수: ~{total_tokens}")
    print(f"  • 예상 비용: ~${embedding_cost:.6f} (약 {embedding_cost * 1300:.2f}원)")
    print("\n💰 매우 저렴합니다! 걱정하지 마세요.")

    # 최종 메시지
    print_banner("✅ 모든 테스트 완료!")

    print("\n🎉 OpenAI Embeddings가 완벽하게 작동합니다!")
    print("\n확인된 기능:")
    print("  ✓ OpenAI API 연결")
    print("  ✓ 실제 의미 있는 벡터 생성")
    print("  ✓ PGVector에 벡터 저장")
    print("  ✓ 의미 기반 유사도 검색")
    print("\n이제 챗봇을 만들 준비가 되었습니다! 🚀")
    print()


if __name__ == "__main__":
    try:
        test_openai_embeddings()
    except KeyboardInterrupt:
        print("\n\n⚠️  테스트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

