"""
MCP 전송 계층

도메인 간 메시지 전송 관리
core/mcp에서 domain/hub/mcp_central로 이동.
"""

from typing import Dict, Any, Optional, Callable, Awaitable
import asyncio

from .protocol import DomainType, MCPProtocol
from .message import MCPRequest, MCPResponse, MCPError


class MCPTransport:
    """
    MCP 전송 계층

    도메인 간 비동기 메시지 전송
    """

    def __init__(self):
        # 도메인 핸들러 레지스트리
        self._handlers: Dict[DomainType, Callable] = {}

        # 응답 대기 큐
        self._pending_responses: Dict[str, asyncio.Future] = {}

    def register_handler(
        self,
        domain: DomainType,
        handler: Callable[[MCPRequest], Awaitable[Dict[str, Any]]]
    ):
        """
        도메인 핸들러 등록

        Args:
            domain: 도메인 타입
            handler: 비동기 핸들러 함수
        """
        self._handlers[domain] = handler
        print(f"✅ MCP 핸들러 등록: {domain.value}")

    async def send_request(
        self,
        from_domain: DomainType,
        to_domain: DomainType,
        action: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        요청 전송 및 응답 대기

        Args:
            from_domain: 요청 도메인
            to_domain: 대상 도메인
            action: 액션
            data: 요청 데이터
            timeout: 타임아웃 (초)

        Returns:
            응답 데이터

        Raises:
            TimeoutError: 타임아웃 발생
            RuntimeError: 핸들러 없음
        """
        # 요청 메시지 생성
        request_dict = MCPProtocol.create_request(
            from_domain=from_domain,
            to_domain=to_domain,
            action=action,
            data=data
        )
        request = MCPRequest.from_dict(request_dict)

        # 핸들러 확인
        if to_domain not in self._handlers:
            raise RuntimeError(f"핸들러가 등록되지 않음: {to_domain.value}")

        # Future 생성 (응답 대기)
        future = asyncio.Future()
        self._pending_responses[request.request_id] = future

        try:
            # 핸들러 호출
            handler = self._handlers[to_domain]
            response_data = await asyncio.wait_for(
                handler(request),
                timeout=timeout
            )

            # 응답 생성
            response_dict = MCPProtocol.create_response(
                request_id=request.request_id,
                from_domain=to_domain,
                to_domain=from_domain,
                data=response_data,
                success=True
            )
            response = MCPResponse.from_dict(response_dict)

            return response.data

        except asyncio.TimeoutError:
            raise TimeoutError(
                f"MCP 요청 타임아웃: {from_domain.value} → {to_domain.value} ({action})"
            )
        except Exception as e:
            # 에러 응답 생성
            error_dict = MCPProtocol.create_error(
                request_id=request.request_id,
                from_domain=to_domain,
                to_domain=from_domain,
                error_code="MCP_500",
                error_message=str(e)
            )
            error = MCPError.from_dict(error_dict)
            raise RuntimeError(f"MCP 요청 실패: {error.error_message}")
        finally:
            # Future 정리
            if request.request_id in self._pending_responses:
                del self._pending_responses[request.request_id]

    def send_event(
        self,
        from_domain: DomainType,
        event_name: str,
        data: Dict[str, Any]
    ):
        """
        이벤트 브로드캐스트 (비동기, 응답 없음)

        Args:
            from_domain: 이벤트 발생 도메인
            event_name: 이벤트 이름
            data: 이벤트 데이터
        """
        event_dict = MCPProtocol.create_event(
            from_domain=from_domain,
            event_name=event_name,
            data=data
        )
        # 이벤트는 단순 로깅 (추후 이벤트 버스 연결 가능)
        print(f"📡 MCP 이벤트: {from_domain.value} → {event_name}")

    def get_registered_domains(self) -> list[DomainType]:
        """
        등록된 도메인 목록 반환

        Returns:
            도메인 타입 리스트
        """
        return list(self._handlers.keys())


# 전역 인스턴스 (싱글톤)
_transport: Optional[MCPTransport] = None


def get_mcp_transport() -> MCPTransport:
    """
    전역 MCP Transport 인스턴스 반환

    Returns:
        MCPTransport 인스턴스
    """
    global _transport
    if _transport is None:
        _transport = MCPTransport()
    return _transport
