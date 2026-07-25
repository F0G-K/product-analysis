"""CSRF 防护中间件。

实现 Double-Submit Cookie 模式：
- asa_csrf Cookie 的值（前端可读）必须与 X-CSRF-Token 请求头一致。
- GET/HEAD/OPTIONS 请求跳过 CSRF 校验。
- 使用 hmac.compare_digest 进行恒定时间比较。
"""

import hmac
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# 跳过 CSRF 校验的 HTTP 方法
_SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS"})

# 这两个匿名端点在会话和 CSRF Cookie 创建之前调用，不能要求已有 Token。
_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/system/init",
        "/api/v1/system/login",
    }
)


class CsrfMiddleware(BaseHTTPMiddleware):
    """CSRF 防护中间件。

    对 POST/PUT/PATCH/DELETE 请求校验 X-CSRF-Token 请求头
    与 asa_csrf Cookie 的值是否一致。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 安全方法和匿名认证入口跳过
        if request.method.upper() in _SAFE_METHODS or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # 提取 Cookie 中的 asa_csrf
        cookie_token: str = request.cookies.get("asa_csrf", "")

        # 提取请求头中的 X-CSRF-Token
        header_token: str = request.headers.get("X-CSRF-Token", "")

        # 任一缺失均拒绝
        if not cookie_token or not header_token:
            return self._error_response(request)

        # 恒定时间比较
        if not hmac.compare_digest(cookie_token, header_token):
            return self._error_response(request)

        return await call_next(request)

    @staticmethod
    def _error_response(request: Request) -> JSONResponse:
        """构造 CSRF 校验失败的错误响应。"""
        request_id = getattr(request.state, "request_id", uuid.uuid4())
        return JSONResponse(
            status_code=403,
            content={
                "code": "CSRF_INVALID",
                "message": "请求校验失败",
                "data": None,
                "request_id": str(request_id),
            },
        )
