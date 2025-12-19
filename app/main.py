"""
LangChain + PGVector Hello World Example

이 예제는 LangChain과 PostgreSQL의 pgvector 확장을 사용하여
간단한 벡터 저장 및 검색을 수행합니다.
"""
import os
import time
from typing import List

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector


class DummyEmbeddings(Embeddings):
    """테스트용 더미 임베딩 클래스 (실제 환경에서는 OpenAI 등을 사용)"""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """문서들을 임베딩합니다."""
        # 간단한 더미 임베딩 (실제로는 의미 있는 벡터를 생성해야 함)
        return [[float(i) for i in range(384)] for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        """쿼리를 임베딩합니다."""
        return [float(i) for i in range(384)]


def wait_for_db(connection_string: str, max_retries: int = 30):
    """데이터베이스가 준비될 때까지 대기합니다."""
    import psycopg2

    print("Waiting for database to be ready...")
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(connection_string)
            conn.close()
            print("Database is ready!")
            return
        except psycopg2.OperationalError:
            print(f"Attempt {i + 1}/{max_retries}: Database not ready yet...")
            time.sleep(2)

    raise Exception("Database did not become ready in time")


def main():
    """메인 함수: LangChain과 PGVector를 사용한 기본 예제"""

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

    print("=" * 60)
    print("LangChain + PGVector Hello World Example")
    print("=" * 60)
    print(f"\nConnecting to: {db_host}:{db_port}/{db_name}")

    # 데이터베이스 준비 대기
    simple_conn_string = (
        f"host={db_host} port={db_port} dbname={db_name} "
        f"user={db_user} password={db_password}"
    )
    wait_for_db(simple_conn_string)

    # 임베딩 모델 초기화 (더미 임베딩 사용)
    embeddings = DummyEmbeddings()

    # 컬렉션 이름
    collection_name = "langchain_demo"

    print(f"\nInitializing PGVector store with collection: {collection_name}")

    # PGVector 벡터 스토어 초기화
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,
    )

    # 샘플 문서 생성
    documents = [
        Document(
            page_content="LangChain is a framework for developing applications powered by language models.",
            metadata={"source": "documentation", "topic": "introduction"}
        ),
        Document(
            page_content="PGVector is a PostgreSQL extension for vector similarity search.",
            metadata={"source": "documentation", "topic": "database"}
        ),
        Document(
            page_content="Docker makes it easy to create, deploy, and run applications using containers.",
            metadata={"source": "documentation", "topic": "devops"}
        ),
        Document(
            page_content="Python is a high-level programming language known for its simplicity.",
            metadata={"source": "documentation", "topic": "programming"}
        ),
    ]

    print(f"\nAdding {len(documents)} documents to vector store...")

    # 문서를 벡터 스토어에 추가
    ids = vector_store.add_documents(documents)
    print(f"Successfully added documents with IDs: {ids}")

    # 유사도 검색 수행
    query = "Tell me about LangChain"
    print(f"\n{'=' * 60}")
    print(f"Query: {query}")
    print(f"{'=' * 60}")

    results = vector_store.similarity_search(query, k=2)

    print(f"\nTop {len(results)} similar documents:")
    for i, doc in enumerate(results, 1):
        print(f"\n{i}. Content: {doc.page_content}")
        print(f"   Metadata: {doc.metadata}")

    # 메타데이터로 필터링한 검색
    print(f"\n{'=' * 60}")
    print("Filtering by metadata (topic='database')")
    print(f"{'=' * 60}")

    filtered_results = vector_store.similarity_search(
        query,
        k=2,
        filter={"topic": "database"}
    )

    print(f"\nFiltered results:")
    for i, doc in enumerate(filtered_results, 1):
        print(f"\n{i}. Content: {doc.page_content}")
        print(f"   Metadata: {doc.metadata}")

    print(f"\n{'=' * 60}")
    print("✓ LangChain + PGVector integration successful!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()

