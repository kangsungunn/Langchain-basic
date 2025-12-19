"""
RAG (Retrieval-Augmented Generation) 챗봇

지식 베이스를 검색하여 정확한 답변을 생성하는 챗봇입니다.
"""
import os
import sys

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector


def print_banner(text: str) -> None:
    """배너를 출력합니다."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def setup_rag_system():
    """RAG 시스템을 설정합니다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ OPENAI_API_KEY가 설정되지 않았습니다!")
        sys.exit(1)

    # Embeddings 초기화
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=api_key
    )

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
        collection_name="langchain_knowledge_base",
        connection=connection_string,
        use_jsonb=True,
    )

    # ChatGPT 초기화
    chat_model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=api_key
    )

    return vector_store, chat_model


def create_rag_prompt():
    """RAG용 프롬프트 템플릿을 생성합니다."""
    template = ChatPromptTemplate.from_messages([
        SystemMessage(content="""당신은 LangChain, RAG, 벡터 데이터베이스 전문가입니다.
사용자의 질문에 답변할 때 제공된 참고 문서를 기반으로 정확하고 친절하게 답변해주세요.

답변 규칙:
1. 참고 문서에 있는 정보를 우선적으로 사용하세요.
2. 참고 문서에 없는 내용은 "제공된 문서에는 해당 정보가 없습니다"라고 말하세요.
3. 한국어로 답변하세요.
4. 친절하고 이해하기 쉽게 설명하세요.
5. 필요하면 예시를 들어주세요."""),
        ("human", """참고 문서:
{context}

질문: {question}

답변:""")
    ])

    return template


def rag_answer(question: str, vector_store, chat_model, k: int = 3):
    """RAG를 사용하여 질문에 답변합니다."""

    # 1. 관련 문서 검색
    print(f"\n🔍 관련 문서 검색 중...")
    docs = vector_store.similarity_search(question, k=k)

    if not docs:
        return "죄송합니다. 관련 정보를 찾을 수 없습니다."

    print(f"✅ {len(docs)}개의 관련 문서를 찾았습니다.")

    # 2. 문서 내용을 컨텍스트로 결합
    context = "\n\n---\n\n".join([doc.page_content for doc in docs])

    # 3. 프롬프트 생성
    prompt_template = create_rag_prompt()
    prompt = prompt_template.format_messages(
        context=context,
        question=question
    )

    # 4. ChatGPT로 답변 생성
    print(f"🤖 답변 생성 중...")
    response = chat_model.invoke(prompt)

    return response.content, docs


def run_demo():
    """데모 질문들을 실행합니다."""
    print_banner("🤖 RAG 챗봇 데모")

    print("\n🔧 RAG 시스템 초기화 중...")
    vector_store, chat_model = setup_rag_system()
    print("✅ 초기화 완료!")

    # 데모 질문들
    demo_questions = [
        "LangChain이 뭐야?",
        "RAG가 뭐고 어떻게 작동하는지 설명해줘",
        "PGVector를 사용하는 이유가 뭐야?",
        "벡터 유사도 검색은 어떻게 작동해?",
    ]

    for i, question in enumerate(demo_questions, 1):
        print_banner(f"질문 {i}/{len(demo_questions)}")
        print(f"\n💬 사용자: {question}")

        try:
            answer, docs = rag_answer(question, vector_store, chat_model)

            print(f"\n🤖 챗봇:")
            print(f"{answer}")

            print(f"\n📚 참고한 문서:")
            for j, doc in enumerate(docs, 1):
                preview = doc.page_content[:100].replace('\n', ' ')
                print(f"   [{j}] {preview}...")

        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")

    # 최종 메시지
    print_banner("✅ 데모 완료!")
    print("\n🎉 RAG 챗봇이 정상적으로 작동합니다!")
    print("\n💡 작동 원리:")
    print("   1. 사용자 질문을 벡터로 변환")
    print("   2. PGVector에서 유사한 문서 검색")
    print("   3. 검색된 문서 + 질문을 ChatGPT에 전달")
    print("   4. ChatGPT가 문서 기반으로 정확한 답변 생성")
    print("\n다음 단계:")
    print("   → 대화형 인터페이스 추가")
    print("   → 대화 히스토리 관리")
    print("   → FastAPI 서버 구축")
    print()


if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\n\n⚠️  챗봇이 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

