"""用户退出登录用例。

使当前会话失效并清除认证 Cookie。
操作为幂等：会话不存在也不报错。
"""

from dataclasses import dataclass

from asa_core.application.ports.session_store import SessionStore


@dataclass(frozen=True)
class LogoutCommand:
    """退出登录 Command 对象。"""

    session_token: str


class LogoutHandler:
    """处理用户退出登录用例。

    只负责使服务端会话失效，不操作 Cookie（Cookie 由 API 层设置）。
    """

    def __init__(self, session_store: SessionStore):
        self._session_store = session_store

    async def handle(self, command: LogoutCommand) -> None:
        """执行退出登录。

        操作为幂等：重复调用不会报错。
        """
        await self._session_store.revoke_session(command.session_token)
