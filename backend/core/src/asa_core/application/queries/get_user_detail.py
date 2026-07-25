"""查询用户详情用例。

管理员按用户 ID 获取单个用户的完整信息。
"""

import uuid
from dataclasses import dataclass

from asa_core.application.ports.user_repository import UserRepository
from asa_core.domain.auth.entities import User
from asa_core.domain.auth.exceptions import UserNotFound


@dataclass(frozen=True)
class GetUserDetailQuery:
    """查询用户详情的 Query 对象。"""

    user_id: str


@dataclass(frozen=True)
class GetUserDetailResult:
    """查询用户详情的返回结果。"""

    user: User


class GetUserDetailHandler:
    """处理查询用户详情。

    UserRepository 在 handle() 方法注入（请求级依赖）。
    """

    async def handle(
        self,
        query: GetUserDetailQuery,
        *,
        user_repo: UserRepository,
    ) -> GetUserDetailResult:
        """执行用户详情查询。

        Args:
            query: 用户 ID。
            user_repo: 用户仓储。

        Returns:
            GetUserDetailResult。

        Raises:
            UserNotFound: 用户不存在。
        """
        uid = uuid.UUID(query.user_id)
        user = await user_repo.find_by_id(uid)
        if user is None:
            raise UserNotFound(query.user_id)

        return GetUserDetailResult(user=user)
