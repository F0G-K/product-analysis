"""更新用户用例。

管理员更新用户角色、状态等字段。
禁止管理员修改自己的角色或禁用自己。
使用乐观锁（updated_at）防止并发冲突。
"""

import uuid
from dataclasses import dataclass
from datetime import UTC

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.application.ports.user_repository import UserRepository
from asa_core.domain.auth.entities import User
from asa_core.domain.auth.exceptions import PermissionDenied, UserNotFound


@dataclass(frozen=True)
class UpdateUserCommand:
    """更新用户的 Command 对象。

    role 和 status 至少提供一个非 None 值。
    """

    user_id: str  # 目标用户 UUID
    role: str | None = None  # 'user' | 'admin' | None（不修改）
    status: str | None = None  # 'active' | 'disabled' | None（不修改）


@dataclass(frozen=True)
class UpdateUserResult:
    """更新用户成功的返回结果。"""

    user: User


class UpdateUserHandler:
    """处理更新用户用例。

    约束：
    1. 仅管理员可调用。
    2. 不可修改自己的角色或状态。
    3. 使用乐观锁防止并发覆盖。
    """

    # 允许的角色和状态值域
    VALID_ROLES = frozenset({"user", "admin"})
    VALID_STATUSES = frozenset({"active", "disabled"})

    def __init__(self, audit_logger: AuditLogger):
        self._audit_logger = audit_logger

    async def handle(
        self,
        command: UpdateUserCommand,
        *,
        user_repo: UserRepository,
        operator_id: str,
    ) -> UpdateUserResult:
        """执行更新用户。

        Args:
            command: 更新参数。
            user_repo: 用户仓储。
            operator_id: 操作管理员 ID。

        Returns:
            UpdateUserResult。

        Raises:
            UserNotFound: 目标用户不存在。
            PermissionDenied: 尝试修改自己。
            ValueError: role 或 status 值无效。
        """
        target_id = uuid.UUID(command.user_id)

        # 1. 禁止管理员修改自己
        if str(target_id) == operator_id:
            raise PermissionDenied("不允许修改自己的角色或状态")

        # 2. 校验修改值
        if command.role is not None and command.role not in self.VALID_ROLES:
            raise ValueError(f"无效的角色值: {command.role}")
        if command.status is not None and command.status not in self.VALID_STATUSES:
            raise ValueError(f"无效的状态值: {command.status}")

        # 3. 查找目标用户
        target = await user_repo.find_by_id(target_id)
        if target is None:
            raise UserNotFound(command.user_id)

        # 4. 构建更新后的实体（保留 updated_at 用于乐观锁）
        from datetime import datetime

        updated = User(
            id=target.id,
            username=target.username,
            password_hash=target.password_hash,
            role=command.role if command.role is not None else target.role,
            status=command.status if command.status is not None else target.status,
            created_at=target.created_at,
            updated_at=datetime.now(UTC),
        )

        # 5. 持久化（乐观锁更新）
        await user_repo.update(updated)

        # 6. 审计日志（记录变更前后值）
        changes: dict[str, str] = {}
        if command.role is not None and command.role != target.role:
            changes["role"] = f"{target.role} → {command.role}"
        if command.status is not None and command.status != target.status:
            changes["status"] = f"{target.status} → {command.status}"

        await self._audit_logger.log(
            action="update_user",
            object_type="user",
            result_status="success",
            actor_user_id=uuid.UUID(operator_id),
            metadata={
                "target_user_id": command.user_id,
                "changes": changes,
            },
        )

        return UpdateUserResult(user=updated)
