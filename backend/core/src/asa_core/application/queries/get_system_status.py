"""查询系统初始化状态用例。"""

from dataclasses import dataclass

from asa_core.application.ports.user_repository import UserRepository


@dataclass(frozen=True)
class GetSystemStatusQuery:
    """查询系统状态的 Query（当前无参数）。"""

    pass


class GetSystemStatusHandler:
    """处理查询系统初始化状态。

    UserRepository 在 handle() 方法注入（请求级依赖）。
    """

    async def handle(
        self,
        _query: GetSystemStatusQuery,
        *,
        user_repo: UserRepository,
    ) -> bool:
        """执行查询。

        Returns:
            True 表示系统已初始化。
        """
        return await user_repo.exists_any()
