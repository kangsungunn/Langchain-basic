"""
LangChain과 Midm 모델 통합 테스트

로컬 Midm 모델을 LangChain으로 래핑하여 사용합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from langchain_huggingface import HuggingFacePipeline
from langchain_core.prompts import PromptTemplate


def create_midm_llm(model_path: str = "app/models/midm"):
    """
    Midm 모델을 LangChain LLM으로 래핑합니다.

    Args:
        model_path: 모델 경로

    Returns:
        LangChain HuggingFacePipeline 인스턴스
    """
    print("=" * 70)
    print("🤖 Midm 모델을 LangChain으로 래핑")
    print("=" * 70)

    try:
        print(f"\n📂 모델 경로: {model_path}")
        print("\n🔄 모델 로드 중...")

        # 모델과 토크나이저 로드
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True
        )

        tokenizer = AutoTokenizer.from_pretrained(model_path)

        print("✅ 모델 로드 완료!")

        # Pipeline 생성
        print("\n🔄 Pipeline 생성 중...")
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=256,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
        )

        # LangChain 래퍼로 변환
        llm = HuggingFacePipeline(pipeline=pipe)

        print("✅ LangChain 래핑 완료!")

        return llm

    except Exception as e:
        print(f"\n❌ 래핑 실패: {e}")
        raise


def test_langchain_prompt(llm):
    """
    LangChain 프롬프트 템플릿 테스트

    Args:
        llm: LangChain LLM 인스턴스
    """
    print("\n" + "=" * 70)
    print("🧪 LangChain 프롬프트 템플릿 테스트")
    print("=" * 70)

    # 프롬프트 템플릿 생성
    template = """질문: {question}

답변:"""

    prompt = PromptTemplate(
        input_variables=["question"],
        template=template
    )

    # 테스트 질문들
    questions = [
        "LangChain이란 무엇인가요?",
        "RAG는 어떻게 작동하나요?",
        "벡터 데이터베이스의 장점은 무엇인가요?",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n[질문 {i}] {question}")
        print("-" * 70)

        try:
            # 프롬프트 생성
            formatted_prompt = prompt.format(question=question)

            # LLM 실행
            response = llm.invoke(formatted_prompt)

            print(f"[답변] {response}")

        except Exception as e:
            print(f"❌ 오류: {e}")


def test_with_custom_llm_wrapper():
    """
    CustomLLM으로 래핑하여 테스트합니다.
    """
    print("\n" + "=" * 70)
    print("🧪 CustomLLM 래퍼 테스트")
    print("=" * 70)

    try:
        from app.models.providers.custom_provider import CustomLLM

        # LangChain LLM 생성
        llm_pipeline = create_midm_llm()

        # CustomLLM으로 래핑
        custom_llm = CustomLLM(
            model=llm_pipeline,
            model_name="midm-2.0-mini"
        )

        print("\n✅ CustomLLM 래핑 완료!")
        print(f"   모델 이름: {custom_llm.get_model_name()}")
        print(f"   설정: {custom_llm.get_model_config()}")

        # 테스트
        test_prompt = "안녕하세요! 자기소개를 해주세요."
        print(f"\n💬 테스트 프롬프트: {test_prompt}")

        model = custom_llm.get_model()
        response = model.invoke(test_prompt)

        print(f"\n📝 응답: {response}")

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    try:
        # 1. LangChain LLM 생성
        llm = create_midm_llm()

        # 2. 프롬프트 템플릿 테스트
        test_langchain_prompt(llm)

        # 3. CustomLLM 래퍼 테스트
        test_with_custom_llm_wrapper()

        print("\n" + "=" * 70)
        print("✅ 모든 테스트 완료!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️  스크립트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

