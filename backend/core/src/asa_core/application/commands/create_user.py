"""创建用户用例。

管理员创建新的系统用户，校验用户名唯一性和密码强度，
使用 Argon2id 哈希存储密码。
"""

from dataclasses import dataclass
from datetime import UTC

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.application.ports.password_hasher import PasswordHasher
from asa_core.application.ports.user_repository import UserRepository
from asa_core.domain.auth.entities import User
from asa_core.domain.auth.exceptions import UsernameAlreadyExists
from asa_core.domain.auth.value_objects import PlainPassword, Username


@dataclass(frozen=True)
class CreateUserCommand:
    """创建用户的 Command 对象。

    由管理员调用，username 在 handler 中规范化为小写。
    """

    username: str
    password: str
    role: str  # 'user' | 'admin'


@dataclass(frozen=True)
class CreateUserResult:
    """创建用户成功的返回结果。"""

    user: User


class CreateUserHandler:
    """处理创建用户用例。

    约束：
    1. 仅管理员可调用（由 API 层 enforce）。
    2. 用户名不能与已有用户重复。
    3. 密码长度 8-128 字符。
    4. 密码 Argon2id 哈希后存储，不记录明文。
    """

    def __init__(
        self,
        password_hasher: PasswordHasher,
        audit_logger: AuditLogger,
    ):
        self._password_hasher = password_hasher
        self._audit_logger = audit_logger

    async def handle(
        self,
        command: CreateUserCommand,
        *,
        user_repo: UserRepository,
        operator_id: str,
    ) -> CreateUserResult:
        """执行创建用户。

        Args:
            command: 创建参数。
            user_repo: 用户仓储。
            operator_id: 操作管理员 ID（用于审计）。

        Returns:
            CreateUserResult。

        Raises:
            UsernameAlreadyExists: 用户名已占用。
            ValueError: 密码或角色值不合法。
        """
        # 1. 规范化用户名并校验格式
        normalized = command.username.strip().lower()
        Username(normalized)  # 值对象构造时校验

        # 2. 校验密码强度
        PlainPassword(command.password)

        # 3. 校验角色值域
        if command.role not in ("user", "admin"):
            raise ValueError(f"无效的角色值: {command.role}，仅允许 'user' 或 'admin'")

        # 4. 检查用户名唯一性
        existing = await user_repo.find_by_username(normalized)
        if existing is not None:
            raise UsernameAlreadyExists(normalized)

        # 5. Argon2id 哈希
        password_hash_str = await self._password_hasher.hash(command.password)

        # 6. 创建用户实体
        import uuid
        from datetime import datetime

        now = datetime.now(UTC)
        user = User(
            id=uuid.uuid4(),
            username=normalized,
            password_hash=password_hash_str,
            role=command.role,
            status="active",
            created_at=now,
            updated_at=now,
        )

        # 7. 持久化
        await user_repo.add(user)

        # 8. 审计日志
        await self._audit_logger.log(
            action="create_user",
            object_type="user",
            result_status="success",
            actor_user_id=uuid.UUID(operator_id),
            metadata={
                "created_username": normalized,
                "created_role": command.role,
            },
        )

        return CreateUserResult(user=user)
