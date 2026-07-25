"""AI 角色领域异常。"""

from asa_core.domain.auth.exceptions import DomainException


class AgentDomainException(DomainException):
    """AI 角色领域异常基类。"""


class RoleNotAllowedForStage(AgentDomainException):
    def __init__(self, role: str, stage: str) -> None:
        super().__init__(f"角色 {role} 不允许在阶段 {stage} 执行")


class ToolNotAllowed(AgentDomainException):
    def __init__(self, role: str, tool_name: str) -> None:
        super().__init__(f"角色 {role} 无权使用工具 {tool_name}")


class ModelOutputInvalid(AgentDomainException):
    def __init__(self) -> None:
        super().__init__("模型输出未通过结构化校验")


class ModelCallFailed(AgentDomainException):
    """统一模型调用错误，可由 Worker 判断是否重试。"""

    def __init__(self, message: str, *, retryable: bool) -> None:
        self.retryable = retryable
        super().__init__(message)
