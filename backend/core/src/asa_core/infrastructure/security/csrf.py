"""CSRF Token 工具函数。

提供 CSRF Token 的安全生成和恒定时间比较。
"""

import hmac
import secrets


def generate_csrf_token() -> str:
    """生成不可预测的 CSRF Token。

    使用 secrets.token_urlsafe 基于操作系统 CSPRNG 生成。
    32 字节 → 43 字符的 URL 安全 Base64 编码。
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(provided: str, stored: str) -> bool:
    """恒定时间比较 CSRF Token。

    使用 hmac.compare_digest 确保比较时间不随输入差异变化，
    防止时序侧信道攻击。
    """
    return hmac.compare_digest(provided, stored)
