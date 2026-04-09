"""
특허 모델 간단 테스트

사용법: python test_patent_model.py
"""

from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

# 모델 로드
model_path = "artifacts/models/finetuned/patent/final"
print(f"🔄 모델 로드 중: {model_path}")

model = AutoModelForSequenceClassification.from_pretrained(model_path)
tokenizer = AutoTokenizer.from_pretrained(model_path)

print("✅ 모델 로드 완료\n")

# 테스트 입력
test_inputs = [
    "제1조(목적)",
    "제29조(특허요건)",
    "제112조",
]

print("=" * 50)
print("테스트 결과")
print("=" * 50)

for text in test_inputs:
    # 토큰화
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)

    # 추론
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=1)

    print(f"\n입력: {text}")
    print(f"  레이블 0 확률: {probs[0][0]:.4f}")
    print(f"  레이블 1 확률: {probs[0][1]:.4f}")
    print(f"  예측 레이블: {torch.argmax(probs, dim=1).item()}")

print("\n" + "=" * 50)
print("✅ 테스트 완료!")
print("=" * 50)
