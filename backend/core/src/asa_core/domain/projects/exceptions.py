"""项目管理领域异常。"""

from typing import Any

from asa_core.domain.auth.exceptions import DomainException


class ProjectDomainException(DomainException):
    """项目领域异常基类，携带可安全返回的上下文。"""

    def __init__(
        self,
        message: str,
        *,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.data = data
        super().__init__(message)


class ProjectNotFound(ProjectDomainException):
    """项目不存在，或当前用户无权获知项目是否存在。"""

    def __init__(self) -> None:
        super().__init__("项目不存在")


class ProjectAccessDenied(ProjectDomainException):
    """当前用户无项目操作权限。"""

    def __init__(self) -> None:
        super().__init__("无项目访问或操作权限")


class ProjectStatusConflict(ProjectDomainException):
    """当前项目状态不允许执行目标操作。"""

    def __init__(self, current_status: str, allowed_statuses: list[str]) -> None:
        super().__init__(
            "当前项目状态不允许执行该操作",
            data={
                "project_status": current_status,
                "allowed_statuses": allowed_statuses,
            },
        )


class ProjectNotRunning(ProjectDomainException):
    """停止目标不是运行状态。"""

    def __init__(self, current_status: str) -> None:
        super().__init__(
            "只有运行中的项目可以停止",
            data={"project_status": current_status},
        )


class ProjectCapacityExceeded(ProjectDomainException):
    """当前运行项目数达到配置上限。"""

    def __init__(self, limit: int) -> None:
        super().__init__(
            "已达到并发项目上限",
            data={"max_concurrent_projects": limit},
        )


class ProjectDeleteForbidden(ProjectDomainException):
    """运行中的项目不可删除。"""

    def __init__(self, current_status: str) -> None:
        super().__init__(
            "运行中的项目不能删除，请先停止项目",
            data={"project_status": current_status},
        )


class ProjectNameConfirmationMismatch(ProjectDomainException):
    """项目删除确认名称不匹配。"""

    def __init__(self) -> None:
        super().__init__("项目名称确认不一致")


class SourcePathInvalid(ProjectDomainException):
    """源码路径或仓库地址格式不合法。"""

    def __init__(self, source_type: str, reason: str) -> None:
        super().__init__(
            "源码地址与源码类型不匹配",
            data={"source_type": source_type, "reason": reason},
        )


class SourceCredentialForbidden(ProjectDomainException):
    """仓库地址包含不得持久化的凭证。"""

    def __init__(self) -> None:
        super().__init__("仓库地址不得包含用户名、密码、Token 或敏感查询参数")


class EnvironmentTypeDisabled(ProjectDomainException):
    """请求的隔离环境类型未启用。"""

    def __init__(self, environment_type: str) -> None:
        super().__init__(
            "隔离环境类型未启用",
            data={"environment_type": environment_type},
        )


class IdempotencyKeyReused(ProjectDomainException):
    """同一幂等键被用于不同请求。"""

    def __init__(self) -> None:
        super().__init__("Idempotency-Key 已用于不同请求")


class DependencyUnavailable(ProjectDomainException):
    """异步任务依赖当前不可用。"""

    def __init__(self) -> None:
        super().__init__("任务依赖暂时不可用，请稍后重试")
