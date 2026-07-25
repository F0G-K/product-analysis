from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.auth.service import auth_service, get_bearer_token
from backend.core.errors import AuthenticationError, ErrorCode


class AuthenticationMiddleware:
    PUBLIC_API_PATHS = frozenset({"/api/v1/auth/login"})

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/api/v1/") or path in self.PUBLIC_API_PATHS:
            await self._app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        authorization = headers.get(b"authorization")
        token = get_bearer_token(
            authorization.decode("utf-8", errors="ignore") if authorization else None
        )
        try:
            user = auth_service.authenticate_token(token)
        except AuthenticationError:
            request_id = str(scope.get("state", {}).get("request_id", ""))
            response = JSONResponse(
                status_code=401,
                content=jsonable_encoder({
                    "code": int(ErrorCode.INVALID_CREDENTIALS),
                    "message": "请先登录或重新登录",
                    "detail": None,
                    "request_id": request_id,
                }),
            )
            await response(scope, receive, send)
            return

        scope.setdefault("state", {})["auth_user"] = user
        scope["state"]["access_token"] = token
        await self._app(scope, receive, send)

