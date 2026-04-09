"""
MCP (Model Context Protocol)

도메인 간 통신 프로토콜
core/mcp에서 domain/hub/mcp_central로 이동.
"""

from .protocol import MCPProtocol, DomainType, MessageType, MCPErrorCode
from .message import MCPRequest, MCPResponse, MCPError, MCPEvent
from .transport import MCPTransport, get_mcp_transport

__all__ = [
    # Protocol
    "MCPProtocol",
    "DomainType",
    "MessageType",
    "MCPErrorCode",
    # Messages
    "MCPRequest",
    "MCPResponse",
    "MCPError",
    "MCPEvent",
    # Transport
    "MCPTransport",
    "get_mcp_transport",
]
