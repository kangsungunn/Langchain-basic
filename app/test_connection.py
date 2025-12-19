"""
LangChain과 PGVector 연결 테스트 스크립트

더미 데이터를 전송하고 조회하여 연결 상태를 확인합니다.
"""
import os
import sys
import time
from typing import List
from datetime import datetime

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector


class DummyEmbeddings(Embeddings):
    """테스트용 더미 임베딩 클래스"""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """문서들을 임베딩합니다."""
        return [[float(i) for i in range(384)] for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        """쿼리를 임베딩합니다."""
        return [float(i) for i in range(384)]


def print_banner(text: str) -> None:
    """배너를 출력합니다."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def wait_for_db(connection_string: str, max_retries: int = 30) -> bool:
    """데이터베이스가 준비될 때까지 대기합니다."""
    import psycopg2

    print("\n🔍 Checking database connection...")
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(connection_string)
            conn.close()
            print("✅ Database is ready!")
            return True
        except psycopg2.OperationalError:
            print(f"   Attempt {i + 1}/{max_retries}: Waiting for database...")
            time.sleep(2)

    print("❌ Database connection failed!")
    return False


def test_connection() -> None:
    """연결 테스트를 수행합니다."""
    print_banner("LangChain ↔ PGVector 연결 테스트")

    # 환경 변수에서 데이터베이스 연결 정보 가져오기
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_user = os.getenv("POSTGRES_USER", "langchain")
    db_password = os.getenv("POSTGRES_PASSWORD", "langchain123")
    db_name = os.getenv("POSTGRES_DB", "vectordb")

    # PostgreSQL 연결 문자열 생성
    connection_string = (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    simple_conn_string = (
        f"host={db_host} port={db_port} dbname={db_name} "
        f"user={db_user} password={db_password}"
    )

    print(f"\n📍 Connection Info:")
    print(f"   Host: {db_host}")
    print(f"   Port: {db_port}")
    print(f"   Database: {db_name}")
    print(f"   User: {db_user}")

    # 데이터베이스 준비 대기
    if not wait_for_db(simple_conn_string):
        sys.exit(1)

    # 임베딩 모델 초기화
    embeddings = DummyEmbeddings()

    # 컬렉션 이름
    collection_name = "test_connection"

    print_banner("STEP 1: PGVector 초기화")
    try:
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=collection_name,
            connection=connection_string,
            use_jsonb=True,
        )
        print("✅ PGVector 초기화 성공!")
    except Exception as e:
        print(f"❌ PGVector 초기화 실패: {e}")
        sys.exit(1)

    print_banner("STEP 2: 더미 데이터 전송 테스트")

    # 현재 시간을 포함한 더미 데이터 생성
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    test_documents = [
        Document(
            page_content=f"[TEST {timestamp}] 첫 번째 테스트 문서입니다.",
            metadata={"test_id": 1, "timestamp": timestamp, "type": "korean"}
        ),
        Document(
            page_content=f"[TEST {timestamp}] This is the second test document.",
            metadata={"test_id": 2, "timestamp": timestamp, "type": "english"}
        ),
        Document(
            page_content=f"[TEST {timestamp}] LangChain과 PGVector 연결 테스트 중입니다.",
            metadata={"test_id": 3, "timestamp": timestamp, "type": "korean"}
        ),
    ]

    print(f"\n📤 Sending {len(test_documents)} test documents to PGVector...")
    for i, doc in enumerate(test_documents, 1):
        print(f"   {i}. {doc.page_content[:50]}...")

    try:
        # 문서를 벡터 스토어에 추가
        ids = vector_store.add_documents(test_documents)
        print(f"\n✅ 데이터 전송 성공!")
        print(f"   생성된 Document IDs:")
        for i, doc_id in enumerate(ids, 1):
            print(f"   {i}. {doc_id}")
    except Exception as e:
        print(f"\n❌ 데이터 전송 실패: {e}")
        sys.exit(1)

    print_banner("STEP 3: 데이터 조회 테스트")

    # 테스트 1: 유사도 검색
    query = "테스트 문서"
    print(f"\n🔎 Query: '{query}'")
    print("   Searching for similar documents...")

    try:
        results = vector_store.similarity_search(query, k=3)
        print(f"\n✅ 조회 성공! {len(results)}개의 문서를 찾았습니다:")

        for i, doc in enumerate(results, 1):
            print(f"\n   [{i}] {doc.page_content}")
            print(f"       Metadata: {doc.metadata}")
    except Exception as e:
        print(f"\n❌ 조회 실패: {e}")
        sys.exit(1)

    # 테스트 2: 메타데이터 필터링
    print_banner("STEP 4: 메타데이터 필터링 테스트")

    print("\n🔎 Filtering by type='korean'")
    try:
        filtered_results = vector_store.similarity_search(
            query,
            k=5,
            filter={"type": "korean"}
        )
        print(f"\n✅ 필터링 성공! {len(filtered_results)}개의 한국어 문서를 찾았습니다:")

        for i, doc in enumerate(filtered_results, 1):
            print(f"\n   [{i}] {doc.page_content}")
            print(f"       Metadata: {doc.metadata}")
    except Exception as e:
        print(f"\n❌ 필터링 실패: {e}")
        sys.exit(1)

    print_banner("STEP 5: 데이터베이스 직접 확인")

    # PostgreSQL에 직접 쿼리하여 데이터 확인
    try:
        import psycopg2

        conn = psycopg2.connect(simple_conn_string)
        cursor = conn.cursor()

        # 총 문서 수 확인
        cursor.execute("""
            SELECT COUNT(*)
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = %s
        """, (collection_name,))

        count = cursor.fetchone()[0]
        print(f"\n📊 Collection '{collection_name}'의 총 문서 수: {count}")

        # 최근 추가된 문서 확인
        cursor.execute("""
            SELECT document, cmetadata
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = %s
            ORDER BY e.id DESC
            LIMIT 3
        """, (collection_name,))

        print(f"\n📄 최근 추가된 문서 3개:")
        for i, (document, metadata) in enumerate(cursor.fetchall(), 1):
            print(f"\n   [{i}] {document}")
            print(f"       Metadata: {metadata}")

        cursor.close()
        conn.close()

        print("\n✅ 데이터베이스 직접 확인 완료!")
    except Exception as e:
        print(f"\n⚠️  데이터베이스 직접 확인 실패: {e}")

    print_banner("✅ 모든 연결 테스트 완료!")
    print("\n🎉 LangChain과 PGVector가 정상적으로 연결되어 있습니다!")
    print("\n연결 흐름:")
    print("   LangChain (Python) → PGVector Extension → PostgreSQL Database")
    print("   ✓ 데이터 쓰기 성공")
    print("   ✓ 데이터 읽기 성공")
    print("   ✓ 유사도 검색 성공")
    print("   ✓ 메타데이터 필터링 성공")
    print()


if __name__ == "__main__":
    try:
        test_connection()
    except KeyboardInterrupt:
        print("\n\n⚠️  테스트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

