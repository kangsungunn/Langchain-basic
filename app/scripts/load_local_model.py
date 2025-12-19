"""
로컬 Midm 모델 로드 테스트 스크립트

Midm-2.0-Mini-Instruct 모델을 로드하고 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from transformers import AutoModelForCausalLM, AutoTokenizer


def load_midm_model(model_path: str = "app/models/midm"):
    """
    Midm 모델을 로드합니다.

    Args:
        model_path: 모델 경로

    Returns:
        (model, tokenizer) 튜플
    """
    print("=" * 70)
    print("🤖 Midm-2.0-Mini-Instruct 모델 로드")
    print("=" * 70)
    print(f"\n📂 모델 경로: {model_path}")

    try:
        print("\n🔄 모델 로드 중... (시간이 걸릴 수 있습니다)")

        # 모델 로드
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True  # Mi:dm 필수
        )

        print("✅ 모델 로드 완료!")

        # 토크나이저 로드
        print("\n🔄 토크나이저 로드 중...")
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        print("✅ 토크나이저 로드 완료!")

        # 모델 정보 출력
        print("\n" + "=" * 70)
        print("📊 모델 정보")
        print("=" * 70)
        print(f"모델 타입: {model.config.model_type}")
        print(f"Hidden size: {model.config.hidden_size}")
        print(f"레이어 수: {model.config.num_hidden_layers}")
        print(f"어텐션 헤드: {model.config.num_attention_heads}")
        print(f"Vocabulary size: {model.config.vocab_size}")

        return model, tokenizer

    except Exception as e:
        print(f"\n❌ 모델 로드 실패: {e}")
        raise


def test_generation(model, tokenizer, prompt: str = "안녕하세요! 오늘 날씨가 어때요?"):
    """
    모델로 텍스트를 생성합니다.

    Args:
        model: 로드된 모델
        tokenizer: 로드된 토크나이저
        prompt: 테스트 프롬프트
    """
    print("\n" + "=" * 70)
    print("🧪 텍스트 생성 테스트")
    print("=" * 70)
    print(f"\n💬 프롬프트: {prompt}")

    try:
        # 입력 인코딩
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        print("\n🔄 생성 중...")

        # 텍스트 생성
        outputs = model.generate(
            **inputs,
            max_new_tokens=100,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id
        )

        # 디코딩
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        print("\n✅ 생성 완료!")
        print("\n" + "=" * 70)
        print("📝 생성된 텍스트")
        print("=" * 70)
        print(generated_text)

    except Exception as e:
        print(f"\n❌ 생성 실패: {e}")
        raise


def main():
    """메인 함수"""
    try:
        # 모델 로드
        model, tokenizer = load_midm_model()

        # 텍스트 생성 테스트
        test_prompts = [
            "안녕하세요! 오늘 날씨가 어때요?",
            "LangChain이란 무엇인가요?",
            "파이썬으로 Hello World를 출력하는 코드를 작성해주세요.",
        ]

        for prompt in test_prompts:
            test_generation(model, tokenizer, prompt)
            print("\n")

        print("=" * 70)
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

