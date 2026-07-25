"""Argon2id 密码哈希实现。

实现 application/ports/password_hasher.py 中定义的 PasswordHasher 接口。
使用 argon2-cffi 库，通过 asyncio.to_thread 在线程池中执行（argon2-cffi 为同步库）。
"""

import asyncio

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2 import exceptions as argon2_exceptions
from asa_core.application.ports.password_hasher import PasswordHasher

# 预先计算的 Argon2id 哈希，用于登录失败时做假校验（防止用户枚举时序攻击）
# 这是对固定字符串 "DUMMY_PASSWORD_FOR_TIMING_EQUALIZATION" 的哈希
_DUMMY_HASH: str = "$argon2id$v=19$m=65536,t=3,p=4$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class Argon2idHasher(PasswordHasher):
    """Argon2id 密码哈希器。

    Argon2 参数（符合 OWASP 推荐）：
    - time_cost=3：迭代次数
    - memory_cost=65536：内存开销（64 MiB）
    - parallelism=4：并行度
    - hash_len=32：输出哈希长度（字节）
    """

    DUMMY_HASH: str = _DUMMY_HASH

    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
        hash_len: int = 32,
    ):
        self._hasher = Argon2PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
        )

    async def hash(self, password: str) -> str:
        """对明文密码执行 Argon2id 哈希。

        argon2-cffi 为同步操作，在线程池中执行以避免阻塞事件循环。
        """
        return await asyncio.to_thread(self._hasher.hash, password)

    async def verify(self, password: str, hash_value: str) -> bool:
        """校验明文密码是否与 Argon2id 哈希匹配。

        使用恒定时间比较，防止时序侧信道攻击。
        """
        try:
            verified: bool = await asyncio.to_thread(self._hasher.verify, hash_value, password)
            # 如果密码哈希参数需要更新（如 time_cost 变化），
            # 应在验证成功后异步重哈希，MVP 阶段暂不实现自动 rehash。
            # if verified and self._hasher.check_needs_rehash(hash_value):
            #     ...
            return verified
        except argon2_exceptions.VerifyMismatchError:
            return False
        except argon2_exceptions.VerificationError:
            # 哈希格式无效等情况
            return False
