"""认证领域异常。

所有异常继承自 DomainException 基类，由 API 层的全局异常处理器
映射为对应的 HTTP 状态码和业务码。异常只携带业务上下文，
不携带 HTTP Response 或堆栈信息。
"""


class DomainException(Exception):
    """所有领域异常的基类。"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class SystemAlreadyInitialized(DomainException):
    """系统已初始化，拒绝重复的初始化请求。"""

    def __init__(self):
        super().__init__("系统已完成初始化")


class SystemNotInitialized(DomainException):
    """系统尚未初始化，拒绝登录请求。"""

    def __init__(self):
        super().__init__("系统尚未初始化，请先创建管理员账户")


class InvalidCredentials(DomainException):
    """用户名或密码错误。

    不区分"用户不存在"和"密码错误"，
    响应始终使用统一的错误消息防止用户枚举。
    """

    def __init__(self):
        super().__init__("用户名或密码错误")


class AccountDisabled(DomainException):
    """账户已被禁用。"""

    def __init__(self):
        super().__init__("账户已被禁用")


class AuthenticationRequired(DomainException):
    """需要有效的登录态。"""

    def __init__(self):
        super().__init__("请先登录")


class SessionExpired(DomainException):
    """登录会话已过期。"""

    def __init__(self):
        super().__init__("登录已过期，请重新登录")


class CsrfValidationFailed(DomainException):
    """CSRF Token 校验失败。"""

    def __init__(self):
        super().__init__("请求校验失败")


class AdminRequired(DomainException):
    """需要管理员权限。"""

    def __init__(self):
        super().__init__("需要管理员权限")


class UserNotFound(DomainException):
    """用户不存在。"""

    def __init__(self, user_id: str | None = None):
        detail = f"用户不存在: {user_id}" if user_id else "用户不存在"
        super().__init__(detail)


class UsernameAlreadyExists(DomainException):
    """用户名已存在（唯一约束冲突）。"""

    def __init__(self, username: str):
        super().__init__(f"用户名 '{username}' 已被使用")


class PermissionDenied(DomainException):
    """已认证用户无权访问目标资源。"""

    def __init__(self, message: str = "无操作权限"):
        super().__init__(message)


class PasswordValidationError(DomainException):
    """密码不符合强度要求（领域层校验）。"""

    def __init__(self, reason: str):
        super().__init__(f"密码不符合要求: {reason}")
