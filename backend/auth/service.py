from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from uuid import UUID

from fastapi import Request

from backend.core.errors import AuthenticationError, ErrorCode
from backend.domain.task import TaskActor

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: UUID = DEFAULT_USER_ID
    tenant_id: UUID = DEFAULT_TENANT_ID
    username: str = DEFAULT_USERNAME
    email: str = "admin@local"
    name: str = "管理员"
    role: str = "platform_admin"


class DevelopmentAuthService:
    """单用户开发认证；Token 在服务重启后失效。"""

    def __init__(self) -> None:
        self._tokens: set[str] = set()
        self.user = AuthenticatedUser()

    def login(self, username: str, password: str) -> str:
        username_matches = hmac.compare_digest(username, DEFAULT_USERNAME)
        password_matches = hmac.compare_digest(password, DEFAULT_PASSWORD)
        if not username_matches or not password_matches:
            raise AuthenticationError(
                ErrorCode.INVALID_CREDENTIALS,
                "用户名或密码错误",
            )
        token = secrets.token_urlsafe(32)
        self._tokens.add(token)
        return token

    def authenticate_token(self, token: str | None) -> AuthenticatedUser:
        if token is None or token not in self._tokens:
            raise AuthenticationError(
                ErrorCode.INVALID_CREDENTIALS,
                "登录已失效，请重新登录",
            )
        return self.user

    def logout(self, token: str) -> None:
        self._tokens.discard(token)


auth_service = DevelopmentAuthService()


def get_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator and scheme.lower() == "bearer" and token:
        return token
    return None


async def resolve_task_actor(request: Request) -> TaskActor:
    user = getattr(request.state, "auth_user", None)
    if not isinstance(user, AuthenticatedUser):
        raise AuthenticationError(ErrorCode.INVALID_CREDENTIALS, "请先登录")
    return TaskActor(
        user_id=user.id,
        tenant_id=user.tenant_id,
        is_tenant_admin=True,
    )

