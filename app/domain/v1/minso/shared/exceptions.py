"""
minso 도메인 공통 예외

도메인 서비스·리포지토리에서 사용하는 공통 예외.
API 레이어는 MinsoDomainError 또는 ValueError 로 catch 하여 HTTP 4xx/5xx 로 변환 가능.
EntityNotFoundError, DomainValidationError 는 ValueError 를 상속하여
기존 `except ValueError` 처리와 호환된다.
"""

from typing import Optional


# ---------------------------------------------------------------------------
# 기본 도메인 예외
# ---------------------------------------------------------------------------


class MinsoDomainError(Exception):
    """
    minso 서브도메인 공통 기본 예외.

    모든 도메인 정의 예외는 이 클래스를 상속한다.
    API에서 일괄 처리 시 사용 (예: 4xx 변환).
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
    ):
        self.message = message
        self.code = code
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


# ---------------------------------------------------------------------------
# 엔티티 부재 (404 대응)
# ---------------------------------------------------------------------------


class EntityNotFoundError(MinsoDomainError, ValueError):
    """
    엔티티를 찾을 수 없을 때 사용.

    entity_type: 엔티티 종류 (예: "user_answer", "reasoning_task", "feedback")
    entity_id: 조회에 사용한 ID (없으면 None)
    기존 API의 `except ValueError` 로 그대로 처리 가능.
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.entity_type = entity_type
        self.entity_id = entity_id
        if message:
            msg = message
        elif entity_id is not None:
            msg = f"{entity_type}을(를) 찾을 수 없습니다: {entity_id}"
        else:
            msg = f"{entity_type}을(를) 찾을 수 없습니다."
        super().__init__(msg, code="ENTITY_NOT_FOUND")


# ---------------------------------------------------------------------------
# 도메인 검증/비즈니스 규칙 위반 (400 대응)
# ---------------------------------------------------------------------------


class DomainValidationError(MinsoDomainError, ValueError):
    """
    도메인 검증 실패 또는 지원하지 않는 동작.

    예: 지원하지 않는 피드백 타입, 이미지 답안이 아님, 학습할 데이터 없음,
         필요한 분석 결과 없음, 허브에서 처리할 수 없는 도메인/액션.
    기존 API의 `except ValueError` 로 그대로 처리 가능.
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
    ):
        super().__init__(message, code=code or "VALIDATION_ERROR")
