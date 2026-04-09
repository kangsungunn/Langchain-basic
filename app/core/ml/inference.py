"""
ML 추론 엔진

모델을 사용한 추론 기능 제공
"""

from typing import Dict, Any, List
import torch


class InferenceEngine:
    """
    추론 엔진

    모델 로더로부터 모델을 받아 추론 수행
    """

    def __init__(self, model_loader):
        """
        Args:
            model_loader: ModelLoader 인스턴스
        """
        self.model_loader = model_loader
        self.model = model_loader.get_model()
        self.tokenizer = model_loader.get_tokenizer()
        self.device = model_loader.get_device()

    def predict(
        self,
        text: str,
        max_length: int = 512
    ) -> Dict[str, Any]:
        """
        텍스트 분류 예측

        Args:
            text: 입력 텍스트
            max_length: 최대 토큰 길이

        Returns:
            {
                "prediction": int,  # 예측 클래스
                "confidence": float,  # 신뢰도
                "probabilities": List[float]  # 각 클래스 확률
            }
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("모델이 로드되지 않았습니다.")

        with torch.no_grad():
            # 토큰화
            inputs = self.tokenizer(
                text,
                truncation=True,
                padding=True,
                max_length=max_length,
                return_tensors="pt"
            ).to(self.device)

            # 추론
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)

            # 예측
            prediction = torch.argmax(probs, dim=-1).item()
            confidence = probs[0][prediction].item()
            probabilities = probs[0].cpu().tolist()

            return {
                "prediction": prediction,
                "confidence": round(confidence, 4),
                "probabilities": [round(p, 4) for p in probabilities]
            }

    def predict_batch(
        self,
        texts: List[str],
        max_length: int = 512
    ) -> List[Dict[str, Any]]:
        """
        배치 예측

        Args:
            texts: 입력 텍스트 리스트
            max_length: 최대 토큰 길이

        Returns:
            예측 결과 리스트
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("모델이 로드되지 않았습니다.")

        with torch.no_grad():
            # 토큰화
            inputs = self.tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=max_length,
                return_tensors="pt"
            ).to(self.device)

            # 추론
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)

            # 배치 예측
            predictions = torch.argmax(probs, dim=-1).cpu().tolist()
            confidences = [probs[i][pred].item() for i, pred in enumerate(predictions)]
            probabilities = probs.cpu().tolist()

            results = []
            for i in range(len(texts)):
                results.append({
                    "prediction": predictions[i],
                    "confidence": round(confidences[i], 4),
                    "probabilities": [round(p, 4) for p in probabilities[i]]
                })

            return results

    def encode_text(
        self,
        text: str,
        max_length: int = 512
    ) -> torch.Tensor:
        """
        텍스트를 임베딩으로 변환

        Args:
            text: 입력 텍스트
            max_length: 최대 토큰 길이

        Returns:
            임베딩 텐서
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("모델이 로드되지 않았습니다.")

        with torch.no_grad():
            inputs = self.tokenizer(
                text,
                truncation=True,
                padding=True,
                max_length=max_length,
                return_tensors="pt"
            ).to(self.device)

            # 마지막 히든 스테이트 추출
            outputs = self.model(**inputs, output_hidden_states=True)
            hidden_states = outputs.hidden_states[-1]

            # [CLS] 토큰의 임베딩 반환
            embeddings = hidden_states[:, 0, :]

            return embeddings
