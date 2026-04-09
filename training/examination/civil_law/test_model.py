"""
학습된 모델 테스트 스크립트

학습된 민사소송법 답안 분석 모델을 직접 테스트합니다.
"""

import sys
from pathlib import Path

import torch  # pyright: ignore[reportMissingImports]
from transformers import AutoTokenizer, AutoModelForSequenceClassification  # pyright: ignore[reportMissingImports]
from peft import PeftModel  # pyright: ignore[reportMissingImports]

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def load_model(model_path: str, base_model_path: str = None):  # pyright: ignore[reportArgumentType]
    """LoRA 모델 로드"""
    print(f"📂 LoRA 모델 로드 중: {model_path}")

    # Base 모델 경로 (LoRA가 저장된 경우)
    if base_model_path is None:
        base_model_path = str(Path(__file__).parent.parent.parent.parent / "artifacts" / "models" / "base" / "exaone-2.4b")

    tokenizer = AutoTokenizer.from_pretrained(model_path)

    # Base 모델 먼저 로드
    print(f"  📂 Base 모델 로드: {base_model_path}")
    base_model = AutoModelForSequenceClassification.from_pretrained(
        base_model_path,
        num_labels=3,
        trust_remote_code=True
    )

    # LoRA 가중치 로드
    try:
        model = PeftModel.from_pretrained(base_model, model_path)
        print(f"  ✅ LoRA 가중치 로드 완료")
    except Exception as e:
        print(f"  ⚠️ LoRA 로드 실패, Base 모델 사용: {e}")
        model = base_model

    # GPU 사용 가능하면 GPU로
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    print(f"✅ 모델 로드 완료 (Device: {device})")

    return tokenizer, model, device


def predict(tokenizer, model, device, problem: str, reference: str, user_answer: str):
    """답안 분석 예측"""

    # 입력 텍스트 구성
    input_text = f"""[문제] {problem}
[모범답안] {reference}
[사용자답안] {user_answer}"""

    print("\n" + "=" * 80)
    print("📝 입력 텍스트:")
    print("-" * 80)
    print(input_text)
    print("=" * 80)

    # 토큰화 (학습 시와 동일한 max_length)
    encoding = tokenizer(
        input_text,
        max_length=256,  # 학습 시와 동일
        padding='max_length',
        truncation=True,
        return_tensors='pt'
    ).to(device)

    # 추론
    with torch.no_grad():
        outputs = model(**encoding)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)
        prediction = torch.argmax(probs, dim=-1).item()
        confidence = probs[0][prediction].item()

    # 결과 해석
    labels = {
        0: "낮음 (< 40%)",
        1: "중간 (40-70%)",
        2: "높음 (> 70%)"
    }

    print("\n🎯 예측 결과:")
    print(f"  - 쟁점 포함률: {labels[prediction]}")
    print(f"  - 신뢰도: {confidence:.2%}")
    print(f"  - 확률 분포:")
    for i, prob in enumerate(probs[0].cpu().numpy()):
        print(f"    • {labels[i]}: {prob:.2%}")

    return prediction, confidence, probs[0].cpu().numpy()


def main():
    print("=" * 80)
    print("민사소송법 답안 분석 모델 - 테스트")
    print("=" * 80)

    # 모델 경로
    model_path = project_root / "artifacts" / "models" / "finetuned" / "legal" / "final_simple"

    if not model_path.exists():
        print(f"\n❌ 모델을 찾을 수 없습니다: {model_path}")
        print(f"\n먼저 학습을 실행하세요:")
        print(f"  python train_simple.py")
        return

    # 모델 로드
    tokenizer, model, device = load_model(str(model_path))

    # 테스트 케이스
    test_cases = [
        {
            "name": "테스트 1: 낮은 품질 답안",
            "problem": "갑은 을에게 금전을 대여하였으나 변제기가 도과하였다. 갑이 을을 상대로 취할 수 있는 조치를 논하시오.",
            "reference": "I. 서론\n본 사안은 대여금 청구가 문제된다.\n\nII. 소비대차계약\n갑과 을 사이에 금전소비대차계약이 체결되었다.\n\nIII. 변제기 도과\n변제기가 도과하였으므로 이행지체 상태이다.\n\nIV. 청구\n갑은 대여금 및 지연손해금을 청구할 수 있다.",
            "user_answer": "돈을 빌려줬으니 돌려받으면 된다."
        },
        {
            "name": "테스트 2: 중간 품질 답안",
            "problem": "갑은 을에게 금전을 대여하였으나 변제기가 도과하였다. 갑이 을을 상대로 취할 수 있는 조치를 논하시오.",
            "reference": "I. 서론\n본 사안은 대여금 청구가 문제된다.\n\nII. 소비대차계약\n갑과 을 사이에 금전소비대차계약이 체결되었다.\n\nIII. 변제기 도과\n변제기가 도과하였으므로 이행지체 상태이다.\n\nIV. 청구\n갑은 대여금 및 지연손해금을 청구할 수 있다.",
            "user_answer": "갑과 을 사이에 소비대차계약이 성립하였고, 변제기가 도과하였으므로 갑은 을에게 대여금을 청구할 수 있다."
        },
        {
            "name": "테스트 3: 높은 품질 답안",
            "problem": "갑은 을에게 금전을 대여하였으나 변제기가 도과하였다. 갑이 을을 상대로 취할 수 있는 조치를 논하시오.",
            "reference": "I. 서론\n본 사안은 대여금 청구가 문제된다.\n\nII. 소비대차계약\n갑과 을 사이에 금전소비대차계약이 체결되었다.\n\nIII. 변제기 도과\n변제기가 도과하였으므로 이행지체 상태이다.\n\nIV. 청구\n갑은 대여금 및 지연손해금을 청구할 수 있다.",
            "user_answer": "I. 서론\n본 사안은 갑의 을에 대한 대여금 청구가 문제된다.\n\nII. 소비대차계약의 성립\n갑과 을 사이에 금전소비대차계약이 체결되었다(민법 제598조).\n\nIII. 변제기의 도과\n변제기가 도과하였으므로 을은 이행지체 책임을 진다(민법 제387조).\n\nIV. 청구권의 행사\n갑은 을에게 대여금 원금 및 변제기 경과 후의 지연손해금을 청구할 수 있다(민법 제603조, 제397조).\n\nV. 결론\n따라서 갑은 대여금청구의 소를 제기할 수 있다."
        }
    ]

    # 각 테스트 케이스 실행
    for i, case in enumerate(test_cases, 1):
        print(f"\n\n{'=' * 80}")
        print(f"{case['name']}")
        print('=' * 80)

        predict(
            tokenizer, model, device,
            case['problem'],
            case['reference'],
            case['user_answer']
        )

    print("\n\n" + "=" * 80)
    print("테스트 완료! ✅")
    print("=" * 80)

    # 대화형 모드
    print("\n\n💡 직접 테스트해보고 싶으시면:")
    print("  - 문제, 모범답안, 사용자답안을 직접 입력하여 테스트할 수 있습니다.")
    print("  - 코드를 수정하거나, API 서버를 통해 테스트하세요.")


if __name__ == "__main__":
    main()
