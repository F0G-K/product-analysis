"""用户登录用例。

验证用户凭据、检查账户状态、创建登录会话。
"""

from dataclasses import dataclass
from datetime import datetime

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.application.ports.password_hasher import PasswordHasher
from asa_core.application.ports.session_store import SessionStore
from asa_core.application.ports.user_repository import UserRepository
from asa_core.domain.auth.entities import User
from asa_core.domain.auth.exceptions import (
    AccountDisabled,
    InvalidCredentials,
    SystemNotInitialized,
)
from asa_core.domain.auth.services import AuthenticationService
from asa_core.infrastructure.security.argon2_hasher import Argon2idHasher


@dataclass(frozen=True)
class LoginCommand:
    """登录 Command 对象。"""

    username: str
    password: str


@dataclass(frozen=True)
class LoginResult:
    """登录成功的返回结果。"""

    user: User
    expires_at: datetime
    session_token: str
    csrf_token: str


class LoginHandler:
    """处理用户登录用例。

    安全要点：
    1. 用户不存在和密码错误统一返回 InvalidCredentials（防枚举）。
    2. 用户不存在时仍执行 Argon2id 哈希验算（时序均衡）。
    3. 禁用账户返回 AccountDisabled。
    """

    def __init__(
        self,
        password_hasher: PasswordHasher,
        session_store: SessionStore,
        audit_logger: AuditLogger,
        auth_service: AuthenticationService,
    ):
        self._password_hasher = password_hasher
        self._session_store = session_store
        self._audit_logger = audit_logger
        self._auth_service = auth_service

    async def handle(
        self,
        command: LoginCommand,
        *,
        user_repo: UserRepository,
    ) -> LoginResult:
        """执行登录。

        Args:
            command: 登录参数。
            user_repo: 用户仓储。

        Returns:
            LoginResult 包含用户信息、过期时间和会话 token。

        Raises:
            SystemNotInitialized: 系统尚未初始化。
            InvalidCredentials: 用户名或密码错误。
            AccountDisabled: 账户已禁用。
        """
        # 1. 系统初始化检查
        if not await user_repo.exists_any():
            raise SystemNotInitialized()

        # 2. 规范化用户名
        normalized_username = command.username.strip().lower()

        # 3. 查找用户
        user = await user_repo.find_by_username(normalized_username)

        # 4. 用户不存在 → 假哈希验算（时序均衡），统一返回错误
        if user is None:
            await self._password_hasher.verify(command.password, Argon2idHasher.DUMMY_HASH)
            raise InvalidCredentials()

        # 5. 密码校验 + 账户状态检查
        try:
            await self._auth_service.authenticate(user, command.password, self._password_hasher)
        except InvalidCredentials:
            await self._audit_logger.log(
                action="login",
                object_type="user",
                result_status="failure",
                actor_user_id=user.id,
                metadata={"username": normalized_username},
            )
            raise
        except AccountDisabled:
            raise

        # 6. 创建会话
        session_token, csrf_token, expires_at = await self._session_store.create_session(user.id)

        # 7. 成功审计
        await self._audit_logger.log(
            action="login",
            object_type="user",
            result_status="success",
            actor_user_id=user.id,
            metadata={"username": normalized_username},
        )

        return LoginResult(
            user=user,
            expires_at=expires_at,
            session_token=session_token,
            csrf_token=csrf_token,
        )
