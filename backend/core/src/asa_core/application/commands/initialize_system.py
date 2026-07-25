"""初始化管理员用例。

在系统首次使用时创建唯一的初始管理员账户。
使用数据库 advisory lock 防止并发创建多个管理员。
"""

from dataclasses import dataclass

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.application.ports.password_hasher import PasswordHasher
from asa_core.application.ports.user_repository import UserRepository
from asa_core.domain.auth.entities import User
from asa_core.domain.auth.exceptions import SystemAlreadyInitialized
from asa_core.domain.auth.value_objects import Username
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 全局 advisory lock 的键值（确定性的整数）
_ADVISORY_LOCK_KEY: int = 1739274011


@dataclass(frozen=True)
class InitializeSystemCommand:
    """初始化系统的 Command 对象。"""

    username: str
    password: str


@dataclass(frozen=True)
class InitializeSystemResult:
    """初始化成功的返回结果。"""

    admin: User


class InitializeSystemHandler:
    """处理系统管理员初始化用例。

    关键约束：
    1. pg_advisory_xact_lock 事务级锁防止并发初始化。
    2. 锁内双重检查。
    3. 用户名规范化为小写后写入。
    4. 密码 Argon2id 哈希后存储。
    5. 初始化成功不自动创建登录态。

    依赖注入：
    - password_hasher, audit_logger: 构造函数注入（无状态单例）。
    - user_repository, session: handle() 方法注入（请求级）。
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
        command: InitializeSystemCommand,
        *,
        user_repo: UserRepository,
        session: AsyncSession,
    ) -> InitializeSystemResult:
        """执行系统初始化。

        Args:
            command: 初始化参数。
            user_repo: 用户仓储（与 session 绑定）。
            session: 当前数据库事务会话（调用方管理事务边界）。

        Returns:
            InitializeSystemResult。

        Raises:
            SystemAlreadyInitialized: 系统已有管理员。
        """
        # 1. 获取事务级 advisory lock（COMMIT/ROLLBACK 时自动释放）
        await session.execute(text(f"SELECT pg_advisory_xact_lock({_ADVISORY_LOCK_KEY})"))

        # 2. 双重检查：锁内再次确认未初始化
        if await user_repo.exists_any():
            raise SystemAlreadyInitialized()

        # 3. 规范化用户名（去空白 + 小写），值对象构造时校验
        normalized_username = command.username.strip().lower()
        Username(normalized_username)

        # 4. Argon2id 密码哈希
        password_hash_str = await self._password_hasher.hash(command.password)

        # 5. 创建管理员实体
        admin = User.create_admin(
            username=normalized_username,
            password_hash=password_hash_str,
        )

        # 6. 持久化（同一事务内）
        await user_repo.add(admin)

        # 7. 审计日志
        await self._audit_logger.log(
            action="system_init",
            object_type="system",
            result_status="success",
            actor_user_id=admin.id,
            metadata={"username": normalized_username},
        )

        return InitializeSystemResult(admin=admin)
