"""修改密码用例。

支持两种场景：
1. 管理员重置任意用户密码（无需旧密码）。
2. 用户修改自己的密码（需校验旧密码）。

所有场景使用 Argon2id 哈希，旧密码不记录日志。
"""

import uuid
from dataclasses import dataclass
from datetime import UTC

from asa_core.application.ports.audit_logger import AuditLogger
from asa_core.application.ports.password_hasher import PasswordHasher
from asa_core.application.ports.user_repository import UserRepository
from asa_core.domain.auth.entities import User
from asa_core.domain.auth.exceptions import (
    InvalidCredentials,
    UserNotFound,
)
from asa_core.domain.auth.value_objects import PlainPassword

# ============================================================
# 管理员重置用户密码
# ============================================================


@dataclass(frozen=True)
class ResetPasswordCommand:
    """管理员重置用户密码的 Command 对象。

    不需要旧密码，直接设置新密码。
    """

    user_id: str  # 目标用户 UUID
    new_password: str


@dataclass(frozen=True)
class ResetPasswordResult:
    """密码重置成功的返回结果。"""

    user_id: str


class ResetPasswordHandler:
    """处理管理员重置用户密码用例。

    约束：
    1. 仅管理员可调用。
    2. 新密码须满足强度要求（8-128 字符）。
    3. 密码哈希后存储，旧密码不入日志。
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
        command: ResetPasswordCommand,
        *,
        user_repo: UserRepository,
        operator_id: str,
    ) -> ResetPasswordResult:
        """执行管理员重置密码。

        Args:
            command: 重置参数。
            user_repo: 用户仓储。
            operator_id: 操作管理员 ID。

        Returns:
            ResetPasswordResult。

        Raises:
            UserNotFound: 目标用户不存在。
        """
        target_id = uuid.UUID(command.user_id)

        # 1. 校验新密码强度
        PlainPassword(command.new_password)

        # 2. 查找目标用户
        target = await user_repo.find_by_id(target_id)
        if target is None:
            raise UserNotFound(command.user_id)

        # 3. Argon2id 哈希新密码
        new_hash = await self._password_hasher.hash(command.new_password)

        # 4. 更新用户实体（保留 updated_at 用于乐观锁）
        from datetime import datetime

        updated = User(
            id=target.id,
            username=target.username,
            password_hash=new_hash,
            role=target.role,
            status=target.status,
            created_at=target.created_at,
            updated_at=datetime.now(UTC),
        )
        await user_repo.update(updated)

        # 5. 审计日志（不记录密码）
        await self._audit_logger.log(
            action="reset_password",
            object_type="user",
            result_status="success",
            actor_user_id=uuid.UUID(operator_id),
            metadata={"target_user_id": command.user_id},
        )

        return ResetPasswordResult(user_id=command.user_id)


# ============================================================
# 用户修改自己的密码
# ============================================================


@dataclass(frozen=True)
class ChangeOwnPasswordCommand:
    """用户修改自己密码的 Command 对象。

    必须提供旧密码进行身份再确认。
    """

    old_password: str
    new_password: str


@dataclass(frozen=True)
class ChangeOwnPasswordResult:
    """密码修改成功的返回结果。"""

    user_id: str


class ChangeOwnPasswordHandler:
    """处理用户修改自己密码用例。

    约束：
    1. 必须验证旧密码正确。
    2. 新旧密码不能相同。
    3. 新密码须满足强度要求（8-128 字符）。
    4. 旧密码无效时统一返回 InvalidCredentials。
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
        command: ChangeOwnPasswordCommand,
        *,
        user_repo: UserRepository,
        current_user_id: str,
    ) -> ChangeOwnPasswordResult:
        """执行修改自己密码。

        Args:
            command: 新旧密码。
            user_repo: 用户仓储。
            current_user_id: 当前认证用户 ID。

        Returns:
            ChangeOwnPasswordResult。

        Raises:
            UserNotFound: 当前用户不存在（极端情况）。
            InvalidCredentials: 旧密码不正确。
            ValueError: 新旧密码相同或新密码强度不足。
        """
        uid = uuid.UUID(current_user_id)

        # 1. 查找当前用户
        user = await user_repo.find_by_id(uid)
        if user is None:
            raise UserNotFound(current_user_id)

        # 2. 校验旧密码
        is_valid = await self._password_hasher.verify(command.old_password, user.password_hash)
        if not is_valid:
            raise InvalidCredentials()

        # 3. 新旧密码不能相同
        if command.old_password == command.new_password:
            raise ValueError("新密码不能与旧密码相同")

        # 4. 校验新密码强度
        PlainPassword(command.new_password)

        # 5. Argon2id 哈希新密码
        new_hash = await self._password_hasher.hash(command.new_password)

        # 6. 更新用户实体
        from datetime import datetime

        updated = User(
            id=user.id,
            username=user.username,
            password_hash=new_hash,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
            updated_at=datetime.now(UTC),
        )
        await user_repo.update(updated)

        # 7. 审计日志
        await self._audit_logger.log(
            action="change_password",
            object_type="user",
            result_status="success",
            actor_user_id=uid,
            metadata={"target_user_id": current_user_id},
        )

        return ChangeOwnPasswordResult(user_id=current_user_id)
