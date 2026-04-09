"""
특허법 O/X 판단 테스트

입력: 문장
출력: O/X 판단 + 관련 조문
"""

import json
from pathlib import Path
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# 모델 로드
model_path = "artifacts/models/finetuned/patent/final"
print(f"🔄 모델 로드 중: {model_path}")

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModel.from_pretrained(model_path)
model.eval()

print("✅ 모델 로드 완료\n")

# 조문 데이터 로드 (내용이 충분한 것만)
print("🔄 조문 데이터 로드 중...")
articles = []
with open("data/processed/patent/train.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        content = data["output"].strip()
        # 내용이 너무 짧은 조문 제외 (10자 이상)
        if len(content) > 10:
            articles.append({
                "article": data["input"],
                "content": content,
                "full_text": f"{data['input']} {content}",
                "metadata": data.get("metadata", {})
            })

print(f"✅ {len(articles)}개 조문 로드 완료 (내용 충분한 조문만)\n")


def get_embedding(text):
    """텍스트를 임베딩 벡터로 변환"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        # [CLS] 토큰의 임베딩 사용
        embedding = outputs.last_hidden_state[:, 0, :].numpy()
    return embedding


def find_relevant_article(query_text, top_k=3):
    """입력 문장과 가장 유사한 조문 찾기"""
    query_embedding = get_embedding(query_text)

    similarities = []
    for article in articles:
        # 전체 조문 텍스트로 임베딩
        article_text = article['full_text']
        article_embedding = get_embedding(article_text)

        # 코사인 유사도 계산
        similarity = cosine_similarity(query_embedding, article_embedding)[0][0]
        similarities.append((similarity, article))

    # 유사도 순으로 정렬
    similarities.sort(reverse=True, key=lambda x: x[0])

    return similarities[:top_k]


def judge_statement(statement):
    """문장을 O/X로 판단"""
    print("=" * 60)
    print(f"입력 문장: {statement}")
    print("=" * 60)

    # 관련 조문 찾기
    relevant = find_relevant_article(statement, top_k=3)

    print(f"\n📋 관련 조문 (상위 {len(relevant)}개):\n")

    for i, (similarity, article) in enumerate(relevant, 1):
        print(f"{i}. {article['article']}")
        print(f"   유사도: {similarity:.4f}")
        print(f"   내용: {article['content'][:100]}...")
        print()

    # 가장 유사한 조문 선택
    best_similarity, best_article = relevant[0]

    # 판단 로직 (유사도 기반)
    # 유사도가 높으면 해당 조문과 일치한다고 판단
    threshold = 0.85  # 높은 임계값 사용

    if best_similarity > threshold:
        judgment = "✅ O (맞음)"
        reason = f"입력 문장이 '{best_article['article']}'의 내용과 일치합니다."
    elif best_similarity > 0.75:
        judgment = "⚠️ 부분 일치"
        reason = f"입력 문장이 '{best_article['article']}'과 부분적으로 관련이 있습니다."
    else:
        judgment = "❌ X (틀림 또는 관련 없음)"
        reason = f"입력 문장과 특허법 조문 간 유사도가 낮습니다. (최고 유사도: {best_similarity:.2f})"

    print("=" * 60)
    print(f"판단: {judgment}")
    print(f"근거: {reason}")
    print(f"관련 조문: {best_article['article']}")
    print("=" * 60)

    return {
        "judgment": judgment,
        "reason": reason,
        "article": best_article['article'],
        "article_content": best_article['content'],
        "similarity": float(best_similarity)
    }


# 테스트 실행
if __name__ == "__main__":
    test_statements = [
        "이 법은 발명을 보호하고 장려한다",
        "발명은 자연법칙을 이용한 기술적 사상의 창작이다",
        "특허권의 존속기간은 출원일부터 20년이다",
    ]

    print("🧪 특허법 O/X 판단 테스트\n")

    for statement in test_statements:
        result = judge_statement(statement)
        print("\n")

    # 사용자 입력 받기 (선택적)
    print("\n" + "=" * 60)
    print("💡 직접 테스트하려면 스크립트를 수정하여 문장을 추가하세요")
    print("=" * 60)
