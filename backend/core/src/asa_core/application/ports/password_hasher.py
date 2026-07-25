"""PasswordHasher Port 接口。

定义密码哈希与验证的标准接口，由基础设施层的 Argon2id 实现。
"""

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """密码哈希器接口（应用层 Port）。

    定义密码哈希和校验的标准操作。
    实现类负责具体的哈希算法细节。
    """

    @abstractmethod
    async def hash(self, password: str) -> str:
        """对明文密码进行哈希。

        Args:
            password: 明文密码。

        Returns:
            Argon2id 哈希字符串。
        """
        ...

    @abstractmethod
    async def verify(self, password: str, hash_value: str) -> bool:
        """验证密码是否与哈希匹配。

        实现必须使用恒定时间比较，防止时序攻击。

        Args:
            password: 待验证的明文密码。
            hash_value: 已存储的密码哈希。

        Returns:
            True 表示密码匹配。
        """
        ...
