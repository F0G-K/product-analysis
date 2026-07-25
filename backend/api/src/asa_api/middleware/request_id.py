"""Request-ID 中间件。

为每个 HTTP 请求生成或接受 X-Request-ID，并注入到 request.state
供下游依赖和日志使用。同时将 request_id 写入响应头。
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_ID_HEADER: str = "X-Request-ID"
_REQUEST_ID_STATE_KEY: str = "request_id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Request-ID 中间件。

    - 读取客户端传入的 X-Request-ID（需为合法 UUID 格式），
      无效时生成新的 UUID。
    - 将 request_id 存入 request.state.request_id。
    - 写入响应头 X-Request-ID。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = self._resolve_request_id(request)
        request.state.__setattr__(_REQUEST_ID_STATE_KEY, request_id)

        response = await call_next(request)
        response.headers[_REQUEST_ID_HEADER] = str(request_id)
        return response

    @staticmethod
    def _resolve_request_id(request: Request) -> uuid.UUID:
        """从请求头解析或生成 request_id。"""
        header_value = request.headers.get(_REQUEST_ID_HEADER)
        if header_value:
            try:
                return uuid.UUID(header_value)
            except (ValueError, AttributeError):
                pass
        return uuid.uuid4()


def get_request_id(request: Request) -> uuid.UUID:
    """从 request.state 中获取当前请求的 request_id。

    供异常处理器和依赖函数使用。
    """
    return getattr(request.state, _REQUEST_ID_STATE_KEY, uuid.uuid4())
