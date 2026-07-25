"""UserRepository Port 接口。

定义用户持久化操作的标准接口，由基础设施层实现。
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from asa_core.domain.auth.entities import User


@dataclass(frozen=True)
class UserListResult:
    """用户列表分页查询结果。"""

    items: list[User] = field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total: int = 0

    @property
    def has_next(self) -> bool:
        """是否存在下一页。"""
        return self.page * self.page_size < self.total


class UserRepository(ABC):
    """用户仓储接口（应用层 Port）。

    定义领域层需要的所有用户数据访问操作。
    实现类负责将领域实体与 ORM Model 之间的转换。
    """

    @abstractmethod
    async def exists_any(self) -> bool:
        """检查系统中是否存在任何用户（即系统是否已初始化）。"""
        ...

    @abstractmethod
    async def count(self) -> int:
        """返回用户总数。"""
        ...

    @abstractmethod
    async def find_by_username(self, username: str) -> User | None:
        """按小写用户名查找用户。

        Args:
            username: 已规范化为小写的用户名。

        Returns:
            匹配的 User 实体，未找到返回 None。
        """
        ...

    @abstractmethod
    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        """按用户 ID 查找用户。"""
        ...

    @abstractmethod
    async def add(self, user: User) -> None:
        """新增用户（写入持久化存储，但不提交事务）。"""
        ...

    @abstractmethod
    async def find_all(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> UserListResult:
        """分页查询用户列表，支持按角色、状态和关键词筛选。

        Args:
            page: 页码（从 1 开始）。
            page_size: 每页条数（1-100）。
            role: 按角色精确筛选（'user' / 'admin'）。
            status: 按状态精确筛选（'active' / 'disabled'）。
            keyword: 按用户名模糊匹配（LIKE %keyword%）。

        Returns:
            UserListResult 包含分页数据。
        """
        ...

    @abstractmethod
    async def update(self, user: User) -> None:
        """更新用户字段（乐观锁：以 updated_at 为版本号）。

        仅更新 username、role、status、password_hash、updated_at。
        使用条件 UPDATE ... WHERE id = :id AND updated_at = :old_updated_at。

        Args:
            user: 包含更新后字段的 User 实体（id 不变，updated_at 为新值）。

        Raises:
            UserNotFound: 用户不存在或乐观锁冲突（受影响行数 != 1）。
        """
        ...
