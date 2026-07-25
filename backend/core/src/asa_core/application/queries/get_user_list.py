"""查询用户列表用例。

管理员分页查询用户，支持按角色、状态和关键词筛选。
"""

from dataclasses import dataclass

from asa_core.application.ports.user_repository import UserListResult, UserRepository


@dataclass(frozen=True)
class GetUserListQuery:
    """查询用户列表的 Query 对象。"""

    page: int = 1
    page_size: int = 20
    role: str | None = None  # 'user' | 'admin'
    status: str | None = None  # 'active' | 'disabled'
    keyword: str | None = None  # 按用户名模糊搜索


class GetUserListHandler:
    """处理查询用户列表。

    UserRepository 在 handle() 方法注入（请求级依赖）。
    """

    # 允许的排序白名单（防止 SQL 注入）
    MAX_PAGE_SIZE: int = 100

    async def handle(
        self,
        query: GetUserListQuery,
        *,
        user_repo: UserRepository,
    ) -> UserListResult:
        """执行用户列表查询。

        Args:
            query: 查询筛选条件。
            user_repo: 用户仓储。

        Returns:
            UserListResult 包含分页结果。
        """
        # 分页参数保护
        page = max(1, query.page)
        page_size = min(max(1, query.page_size), self.MAX_PAGE_SIZE)

        return await user_repo.find_all(
            page=page,
            page_size=page_size,
            role=query.role,
            status=query.status,
            keyword=query.keyword,
        )
