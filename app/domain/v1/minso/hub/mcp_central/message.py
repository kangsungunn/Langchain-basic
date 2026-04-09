"""
MCP 메시지 클래스

타입 안전한 메시지 처리
core/mcp에서 domain/hub/mcp_central로 이동.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime

from .protocol import MessageType, DomainType


@dataclass
class MCPRequest:
    """MCP 요청 메시지"""

    request_id: str
    from_domain: DomainType
    to_domain: DomainType
    action: str
    data: Dict[str, Any]
    timestamp: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPRequest':
        """딕셔너리로부터 생성"""
        return cls(
            request_id=data["request_id"],
            from_domain=DomainType(data["from"]),
            to_domain=DomainType(data["to"]),
            action=data["action"],
            data=data["data"],
            timestamp=data["timestamp"]
        )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "protocol": "MCP",
            "version": "1.0.0",
            "type": MessageType.REQUEST.value,
            "request_id": self.request_id,
            "from": self.from_domain.value,
            "to": self.to_domain.value,
            "action": self.action,
            "data": self.data,
            "timestamp": self.timestamp
        }


@dataclass
class MCPResponse:
    """MCP 응답 메시지"""

    request_id: str
    from_domain: DomainType
    to_domain: DomainType
    success: bool
    data: Dict[str, Any]
    timestamp: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPResponse':
        """딕셔너리로부터 생성"""
        return cls(
            request_id=data["request_id"],
            from_domain=DomainType(data["from"]),
            to_domain=DomainType(data["to"]),
            success=data["success"],
            data=data["data"],
            timestamp=data["timestamp"]
        )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "protocol": "MCP",
            "version": "1.0.0",
            "type": MessageType.RESPONSE.value,
            "request_id": self.request_id,
            "from": self.from_domain.value,
            "to": self.to_domain.value,
            "success": self.success,
            "data": self.data,
            "timestamp": self.timestamp
        }


@dataclass
class MCPError:
    """MCP 에러 메시지"""

    request_id: str
    from_domain: DomainType
    to_domain: DomainType
    error_code: str
    error_message: str
    details: Dict[str, Any]
    timestamp: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPError':
        """딕셔너리로부터 생성"""
        error = data["error"]
        return cls(
            request_id=data["request_id"],
            from_domain=DomainType(data["from"]),
            to_domain=DomainType(data["to"]),
            error_code=error["code"],
            error_message=error["message"],
            details=error.get("details", {}),
            timestamp=data["timestamp"]
        )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "protocol": "MCP",
            "version": "1.0.0",
            "type": MessageType.ERROR.value,
            "request_id": self.request_id,
            "from": self.from_domain.value,
            "to": self.to_domain.value,
            "error": {
                "code": self.error_code,
                "message": self.error_message,
                "details": self.details
            },
            "timestamp": self.timestamp
        }


@dataclass
class MCPEvent:
    """MCP 이벤트 메시지"""

    event_id: str
    from_domain: DomainType
    event_name: str
    data: Dict[str, Any]
    timestamp: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPEvent':
        """딕셔너리로부터 생성"""
        return cls(
            event_id=data["event_id"],
            from_domain=DomainType(data["from"]),
            event_name=data["event"],
            data=data["data"],
            timestamp=data["timestamp"]
        )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "protocol": "MCP",
            "version": "1.0.0",
            "type": MessageType.EVENT.value,
            "event_id": self.event_id,
            "from": self.from_domain.value,
            "event": self.event_name,
            "data": self.data,
            "timestamp": self.timestamp
        }
