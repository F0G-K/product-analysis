"""FastAPI 依赖注入。

提供 get_current_user、get_session_token 等 Dependency 函数。
"""

import uuid
from dataclasses import dataclass

from asa_api.bootstrap import create_user_repo, get_service_container
from asa_core.application.ports.session_store import SessionStore
from asa_core.domain.auth.exceptions import (
    AccountDisabled,
    AuthenticationRequired,
    SessionExpired,
)
from fastapi import Cookie, Request


@dataclass(frozen=True)
class CurrentUser:
    """当前认证用户的上下文对象。"""

    id: uuid.UUID
    username: str
    role: str
    status: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


async def get_session_token(
    asa_session: str | None = Cookie(default=None),
) -> str:
    """提取 asa_session Cookie（用于 logout 端点）。

    Raises:
        AuthenticationRequired: Cookie 缺失。
    """
    if not asa_session:
        raise AuthenticationRequired()
    return asa_session


async def get_current_user(
    request: Request,
    asa_session: str | None = Cookie(default=None),
) -> CurrentUser:
    """解析当前认证用户（受保护接口的 FastAPI Dependency）。

    流程：
    1. 提取 asa_session Cookie
    2. SessionStore 验证会话有效性
    3. 查找关联用户
    4. 检查账户状态

    Raises:
        AuthenticationRequired: 无 Cookie。
        SessionExpired: 会话无效或过期。
        AccountDisabled: 账户已禁用。
    """
    if not asa_session:
        raise AuthenticationRequired()

    container = get_service_container(request.app)
    session_store: SessionStore = container.session_store

    # 1. 验证会话
    user_id = await session_store.validate_session(asa_session)
    if user_id is None:
        raise SessionExpired()

    # 2. 查找用户（独立短生命周期 session）
    async with container.session_factory() as db_session:
        user_repo = create_user_repo(db_session)
        user = await user_repo.find_by_id(user_id)

    if user is None:
        raise SessionExpired()

    if not user.is_active:
        raise AccountDisabled()

    return CurrentUser(
        id=user.id,
        username=user.username,
        role=user.role,
        status=user.status,
    )
