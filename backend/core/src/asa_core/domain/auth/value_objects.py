"""认证领域值对象。

包含 Username 和 PasswordHash 等不可变值对象，
封装格式校验规则，确保只有合法值能进入领域层。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Username:
    """用户名字段的值对象。

    约束（与数据库 CHECK 约束一致）：
    - 小写，已去除首尾空白
    - 长度 3-64 字符
    - 不含空白字符
    """

    value: str

    def __post_init__(self) -> None:
        """校验并规范化用户名。"""
        # 规范化：去首尾空白 + 小写
        normalized = self.value.strip().lower()

        # 长度校验
        if len(normalized) < 3 or len(normalized) > 64:
            raise ValueError(f"用户名长度必须在 3-64 字符之间，当前长度: {len(normalized)}")

        # 空白字符校验
        if any(c.isspace() for c in normalized):
            raise ValueError("用户名不得包含空白字符")

        # 使用 object.__setattr__ 绕过 frozen=True 限制进行规范化
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PasswordHash:
    """Argon2id 密码哈希的值对象。

    仅存储哈希字符串，不参与密码校验逻辑。
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value.strip()) < 20:
            raise ValueError("密码哈希不得为空或过短")

    def __str__(self) -> str:
        # 不完整暴露哈希值
        return "<password_hash>"


@dataclass(frozen=True)
class PlainPassword:
    """明文密码的值对象。

    在密码进入哈希流程前校验其强度。
    约束：
    - 长度 8-128 字符
    - MVP 阶段仅做长度校验，复杂度策略由安全评审确认后补充
    """

    value: str

    # 密码最小/最大长度
    MIN_LENGTH: int = 8
    MAX_LENGTH: int = 128

    def __post_init__(self) -> None:
        # 长度校验
        if len(self.value) < self.MIN_LENGTH:
            raise ValueError(f"密码长度至少 {self.MIN_LENGTH} 个字符，当前: {len(self.value)}")
        if len(self.value) > self.MAX_LENGTH:
            raise ValueError(f"密码长度不得超过 {self.MAX_LENGTH} 个字符")

    def __str__(self) -> str:
        # 不暴露明文密码
        return "<plain_password>"


@dataclass(frozen=True)
class SessionToken:
    """会话 Token 的值对象。"""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) < 16:
            raise ValueError("会话 Token 不得为空或过短")
