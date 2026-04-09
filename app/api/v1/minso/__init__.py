"""
API v1 minso (민사소송법 서브도메인)

domain/v1/minso 구조와 맞춤. reference, submission, reasoning, feedback, training 라우터.
"""

from . import reference, submission, reasoning, feedback, training

__all__ = ["reference", "submission", "reasoning", "feedback", "training"]
