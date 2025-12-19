"""
지식 베이스 구축 스크립트

텍스트 파일을 읽어서 청크로 나누고 PGVector에 저장합니다.
"""
import os
import sys
from typing import List

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter


def print_banner(text: str) -> None:
    """배너를 출력합니다."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def load_knowledge_file(file_path: str) -> str:
    """지식 파일을 읽어옵니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {e}")
        sys.exit(1)


def split_text_into_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Document]:
    """텍스트를 청크로 분할합니다."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
        length_function=len,
    )

    chunks = text_splitter.split_text(text)

    # Document 객체로 변환
    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(
            page_content=chunk,
            metadata={
                "chunk_id": i,
                "source": "knowledge_base",
                "total_chunks": len(chunks)
            }
        )
        documents.append(doc)

    return documents


def build_knowledge_base() -> None:
    """지식 베이스를 구축합니다."""
    print_banner("📚 LangChain 지식 베이스 구축")

    # API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ OPENAI_API_KEY가 설정되지 않았습니다!")
        sys.exit(1)

    # Step 1: 지식 파일 읽기
    print_banner("Step 1: 지식 파일 읽기")

    knowledge_file = "/knowledge/sample_knowledge.txt"
    print(f"\n📖 파일 경로: {knowledge_file}")

    content = load_knowledge_file(knowledge_file)
    print(f"✅ 파일 읽기 성공!")
    print(f"   총 문자 수: {len(content):,}")
    print(f"   총 줄 수: {len(content.splitlines())}")

    # Step 2: 텍스트 청크 분할
    print_banner("Step 2: 텍스트 청크 분할")

    print("\n🔪 텍스트를 작은 청크로 분할 중...")
    print("   청크 크기: 500 문자")
    print("   중복 영역: 50 문자")
    print("   (청크 간 문맥 유지를 위해)")

    documents = split_text_into_chunks(content)

    print(f"\n✅ 분할 완료!")
    print(f"   생성된 청크 수: {len(documents)}")

    # 몇 개 샘플 출력
    print("\n📄 샘플 청크 미리보기:")
    for i, doc in enumerate(documents[:3], 1):
        preview = doc.page_content[:100].replace('\n', ' ')
        print(f"   [{i}] {preview}...")

    # Step 3: OpenAI Embeddings 초기화
    print_banner("Step 3: OpenAI Embeddings 초기화")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=api_key
    )
    print("✅ OpenAI Embeddings 초기화 완료")
    print("   모델: text-embedding-3-small")
    print("   벡터 차원: 1536")

    # Step 4: PGVector 초기화
    print_banner("Step 4: PGVector 데이터베이스 연결")

    db_user = os.getenv("POSTGRES_USER", "langchain")
    db_password = os.getenv("POSTGRES_PASSWORD", "langchain123")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "vectordb")

    connection_string = (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    collection_name = "langchain_knowledge_base"

    print(f"\n🔌 데이터베이스 연결 중...")
    print(f"   Host: {db_host}:{db_port}")
    print(f"   Database: {db_name}")
    print(f"   Collection: {collection_name}")

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,
    )

    print("✅ 데이터베이스 연결 완료")

    # Step 5: 벡터 저장
    print_banner("Step 5: 문서를 벡터로 변환하여 저장")

    print(f"\n📤 {len(documents)}개의 청크를 벡터로 변환하여 저장 중...")
    print("   (OpenAI API 호출 중 - 수 초 소요)")
    print("   ⏳ 잠시만 기다려주세요...")

    try:
        ids = vector_store.add_documents(documents)
        print(f"\n✅ 저장 완료!")
        print(f"   저장된 문서 ID: {len(ids)}개")
        print(f"   첫 3개 ID: {ids[:3]}")
    except Exception as e:
        print(f"\n❌ 저장 실패: {e}")
        sys.exit(1)

    # Step 6: 저장 확인 (테스트 검색)
    print_banner("Step 6: 저장 확인 (테스트 검색)")

    test_queries = [
        "LangChain이 뭐야?",
        "RAG는 어떻게 작동해?",
        "PGVector의 장점은?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n🔎 테스트 쿼리 {i}: '{query}'")

        results = vector_store.similarity_search(query, k=1)

        if results:
            preview = results[0].page_content[:150].replace('\n', ' ')
            print(f"   ✅ 관련 문서 찾음:")
            print(f"      {preview}...")
        else:
            print(f"   ⚠️  관련 문서를 찾지 못했습니다.")

    # Step 7: 비용 정보
    print_banner("💰 예상 비용")

    total_chars = sum(len(doc.page_content) for doc in documents)
    estimated_tokens = int(total_chars * 1.3)  # 문자를 토큰으로 대략 변환
    cost = (estimated_tokens / 1_000_000) * 0.02

    print(f"\n📊 처리 정보:")
    print(f"   총 문자 수: {total_chars:,}")
    print(f"   예상 토큰 수: {estimated_tokens:,}")
    print(f"   예상 비용: ${cost:.6f} (약 {cost * 1300:.2f}원)")
    print("\n💡 매우 저렴합니다!")

    # 최종 메시지
    print_banner("✅ 지식 베이스 구축 완료!")

    print(f"\n🎉 성공적으로 지식 베이스를 구축했습니다!")
    print(f"\n📊 구축 결과:")
    print(f"   • Collection: {collection_name}")
    print(f"   • 저장된 청크: {len(documents)}개")
    print(f"   • 벡터 차원: 1536")
    print(f"   • 임베딩 모델: text-embedding-3-small")
    print(f"\n다음 단계:")
    print(f"   → RAG 챗봇으로 질문하기")
    print(f"   → 지식 베이스를 활용한 정확한 답변 생성")
    print()


if __name__ == "__main__":
    try:
        build_knowledge_base()
    except KeyboardInterrupt:
        print("\n\n⚠️  지식 베이스 구축이 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

