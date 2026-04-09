"""
MCP (Model Context Protocol)

도메인 간 통신 프로토콜
core/mcp에서 domain/hub/mcp_central로 이동.
"""

from enum import Enum
from typing import Any, Dict, Optional


class MessageType(str, Enum):
    """메시지 타입"""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    EVENT = "event"


class DomainType(str, Enum):
    """도메인 타입"""
    REFERENCE = "reference"
    SUBMISSION = "submission"
    REASONING = "reasoning"
    FEEDBACK = "feedback"


class MCPProtocol:
    """
    MCP 프로토콜 정의

    도메인 간 표준화된 통신을 위한 프로토콜
    """

    VERSION = "1.0.0"

    @staticmethod
    def create_request(
        from_domain: DomainType,
        to_domain: DomainType,
        action: str,
        data: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        요청 메시지 생성

        Args:
            from_domain: 요청 도메인
            to_domain: 대상 도메인
            action: 액션 (예: "get_issues", "parse_text")
            data: 요청 데이터
            request_id: 요청 ID (선택, 자동 생성)

        Returns:
            표준 요청 메시지
        """
        if request_id is None:
            import uuid
            request_id = str(uuid.uuid4())

        return {
            "protocol": "MCP",
            "version": MCPProtocol.VERSION,
            "type": MessageType.REQUEST.value,
            "request_id": request_id,
            "from": from_domain.value,
            "to": to_domain.value,
            "action": action,
            "data": data,
            "timestamp": MCPProtocol._get_timestamp()
        }

    @staticmethod
    def create_response(
        request_id: str,
        from_domain: DomainType,
        to_domain: DomainType,
        data: Dict[str, Any],
        success: bool = True
    ) -> Dict[str, Any]:
        """
        응답 메시지 생성

        Args:
            request_id: 요청 ID
            from_domain: 응답 도메인
            to_domain: 대상 도메인
            data: 응답 데이터
            success: 성공 여부

        Returns:
            표준 응답 메시지
        """
        return {
            "protocol": "MCP",
            "version": MCPProtocol.VERSION,
            "type": MessageType.RESPONSE.value,
            "request_id": request_id,
            "from": from_domain.value,
            "to": to_domain.value,
            "success": success,
            "data": data,
            "timestamp": MCPProtocol._get_timestamp()
        }

    @staticmethod
    def create_error(
        request_id: str,
        from_domain: DomainType,
        to_domain: DomainType,
        error_code: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        에러 메시지 생성

        Args:
            request_id: 요청 ID
            from_domain: 에러 발생 도메인
            to_domain: 대상 도메인
            error_code: 에러 코드
            error_message: 에러 메시지
            details: 추가 상세 정보

        Returns:
            표준 에러 메시지
        """
        return {
            "protocol": "MCP",
            "version": MCPProtocol.VERSION,
            "type": MessageType.ERROR.value,
            "request_id": request_id,
            "from": from_domain.value,
            "to": to_domain.value,
            "error": {
                "code": error_code,
                "message": error_message,
                "details": details or {}
            },
            "timestamp": MCPProtocol._get_timestamp()
        }

    @staticmethod
    def create_event(
        from_domain: DomainType,
        event_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        이벤트 메시지 생성

        Args:
            from_domain: 이벤트 발생 도메인
            event_name: 이벤트 이름
            data: 이벤트 데이터

        Returns:
            표준 이벤트 메시지
        """
        import uuid

        return {
            "protocol": "MCP",
            "version": MCPProtocol.VERSION,
            "type": MessageType.EVENT.value,
            "event_id": str(uuid.uuid4()),
            "from": from_domain.value,
            "event": event_name,
            "data": data,
            "timestamp": MCPProtocol._get_timestamp()
        }

    @staticmethod
    def validate_message(message: Dict[str, Any]) -> bool:
        """
        메시지 유효성 검증

        Args:
            message: 검증할 메시지

        Returns:
            bool: 유효 여부
        """
        required_fields = ["protocol", "version", "type", "from"]

        for field in required_fields:
            if field not in message:
                return False

        if message["protocol"] != "MCP":
            return False

        if message["type"] not in [t.value for t in MessageType]:
            return False

        return True

    @staticmethod
    def _get_timestamp() -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# 에러 코드 정의
class MCPErrorCode:
    """MCP 에러 코드"""

    # 일반 에러
    INVALID_MESSAGE = "MCP_001"
    INVALID_DOMAIN = "MCP_002"
    INVALID_ACTION = "MCP_003"

    # 도메인 에러
    DOMAIN_NOT_FOUND = "MCP_101"
    DOMAIN_UNAVAILABLE = "MCP_102"
    DOMAIN_TIMEOUT = "MCP_103"

    # 데이터 에러
    DATA_NOT_FOUND = "MCP_201"
    DATA_INVALID = "MCP_202"
    DATA_CONFLICT = "MCP_203"

    # 권한 에러
    PERMISSION_DENIED = "MCP_301"
    AUTHENTICATION_FAILED = "MCP_302"
