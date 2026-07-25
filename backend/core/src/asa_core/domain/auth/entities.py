"""用户领域实体。

User 是认证上下文的聚合根，表示系统中的注册用户。
实体不依赖任何框架或 ORM，是纯粹的领域对象。
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class User:
    """系统用户实体（聚合根）。

    字段对应 users 表结构，包含用户标识、认证信息、
    角色和状态等核心属性。
    """

    id: uuid.UUID
    username: str  # 小写规范化登录名
    password_hash: str  # Argon2id 哈希字符串
    role: str  # 'user' | 'admin'
    status: str  # 'active' | 'disabled'
    created_at: datetime
    updated_at: datetime

    @property
    def is_admin(self) -> bool:
        """是否为管理员。"""
        return self.role == "admin"

    @property
    def is_active(self) -> bool:
        """账户是否处于激活状态。"""
        return self.status == "active"

    @classmethod
    def create_admin(
        cls,
        username: str,
        password_hash: str,
    ) -> "User":
        """创建管理员用户的工厂方法。

        Args:
            username: 已规范化为小写的用户名。
            password_hash: Argon2id 哈希后的密码。

        Returns:
            新建的 User 实体（尚未持久化）。
        """
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            username=username,
            password_hash=password_hash,
            role="admin",
            status="active",
            created_at=now,
            updated_at=now,
        )
