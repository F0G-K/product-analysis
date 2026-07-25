"""认证与授权领域服务。

AuthenticationService: 负责密码校验和账户状态检查。
AuthorizationPolicy: 负责基于角色的权限判断。

这些服务是纯领域逻辑，不依赖框架、数据库或外部系统。
"""

from asa_core.application.ports.password_hasher import PasswordHasher
from asa_core.domain.auth.entities import User
from asa_core.domain.auth.exceptions import (
    AccountDisabled,
    AdminRequired,
    InvalidCredentials,
)


class AuthenticationService:
    """认证服务：统一处理密码校验和账户状态检查。"""

    async def authenticate(
        self,
        user: User,
        plain_password: str,
        password_hasher: PasswordHasher,
    ) -> None:
        """校验用户凭据。

        1. 验证密码是否匹配
        2. 检查账户是否已禁用

        Raises:
            InvalidCredentials: 密码不匹配（不泄露是否存在用户）。
            AccountDisabled: 账户已被禁用。
        """
        # 校验密码
        password_valid = await password_hasher.verify(plain_password, user.password_hash)
        if not password_valid:
            raise InvalidCredentials()

        # 检查账户状态
        if not user.is_active:
            raise AccountDisabled()


class AuthorizationPolicy:
    """授权策略：基于角色的权限判断。"""

    @staticmethod
    def require_admin(user: User) -> None:
        """断言当前用户是管理员。

        Raises:
            AdminRequired: 用户不是管理员。
        """
        if not user.is_admin:
            raise AdminRequired()

    @staticmethod
    def ensure_active(user: User) -> None:
        """断言账户处于激活状态。

        Raises:
            AccountDisabled: 账户已被禁用。
        """
        if not user.is_active:
            raise AccountDisabled()
