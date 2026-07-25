"""SQLAlchemy 实现的 UserRepository。

实现 application/ports/user_repository.py 中定义的 UserRepository 接口。
"""

import uuid

from asa_core.application.ports.user_repository import UserListResult, UserRepository
from asa_core.domain.auth.entities import User
from asa_core.domain.auth.exceptions import UserNotFound
from asa_core.infrastructure.database.models import UserModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyUserRepository(UserRepository):
    """基于 SQLAlchemy 的 UserRepository 实现。

    所有方法接受外部传入的 AsyncSession，不自行管理事务。
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def exists_any(self) -> bool:
        """检查系统中是否存在任何用户记录。"""
        stmt = select(func.count(UserModel.id)).select_from(UserModel)
        result = await self._session.execute(stmt)
        count: int = result.scalar_one()
        return count > 0

    async def count(self) -> int:
        """返回用户总数。"""
        stmt = select(func.count(UserModel.id)).select_from(UserModel)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def find_by_username(self, username: str) -> User | None:
        """按小写用户名查找用户。"""
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        model: UserModel | None = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        """按用户 ID 查找用户。"""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model: UserModel | None = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def add(self, user: User) -> None:
        """新增用户（将领域实体转换为 ORM Model 后持久化）。"""
        model = UserModel(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            role=user.role,
            status=user.status,
        )
        self._session.add(model)

    async def find_all(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> UserListResult:
        """分页查询用户列表，支持按角色、状态和关键词筛选。"""
        # 构建筛选条件列表
        conditions: list = []

        if role is not None:
            conditions.append(UserModel.role == role)
        if status is not None:
            conditions.append(UserModel.status == status)
        if keyword is not None and keyword.strip():
            # 用户名模糊匹配（已规范化为小写，使用 ilike 兼容大小写）
            conditions.append(UserModel.username.ilike(f"%{keyword.strip().lower()}%"))

        # COUNT 查询（总数）
        count_stmt = select(func.count(UserModel.id)).select_from(UserModel)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        count_result = await self._session.execute(count_stmt)
        total: int = count_result.scalar_one()

        # 分页数据查询（按 created_at 降序排列）
        offset = (page - 1) * page_size
        data_stmt = select(UserModel)
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        data_stmt = data_stmt.order_by(UserModel.created_at.desc()).offset(offset).limit(page_size)
        data_result = await self._session.execute(data_stmt)
        models = data_result.scalars().all()

        return UserListResult(
            items=[self._to_entity(m) for m in models],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def update(self, user: User) -> None:
        """更新用户字段。

        注意：乐观锁检查由调用方在应用层完成（比较 updated_at）。
        此方法执行简单的 UPDATE ... WHERE id = :id。

        调用方应先通过 find_by_id 获取当前实体，
        比较 updated_at 确认无并发修改后，再调用此方法。
        """
        stmt = (
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                username=user.username,
                password_hash=user.password_hash,
                role=user.role,
                status=user.status,
                updated_at=user.updated_at,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount != 1:
            raise UserNotFound(str(user.id))

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        """将 ORM Model 转换为领域实体。"""
        return User(
            id=model.id,
            username=model.username,
            password_hash=model.password_hash,
            role=model.role,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
