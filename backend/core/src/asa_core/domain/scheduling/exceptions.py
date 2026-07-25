"""调度领域异常。"""

from asa_core.domain.auth.exceptions import DomainException


class SchedulingDomainException(DomainException):
    """调度领域异常基类。"""


class InvalidStageTransition(SchedulingDomainException):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"阶段状态不能从 {current} 迁移到 {target}")


class StagePrerequisiteNotMet(SchedulingDomainException):
    def __init__(self, stage_name: str) -> None:
        super().__init__(f"阶段 {stage_name} 的前置阶段尚未成功")


class InvalidTaskTransition(SchedulingDomainException):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"角色任务状态不能从 {current} 迁移到 {target}")


class SchedulingConflict(SchedulingDomainException):
    def __init__(self, message: str = "调度状态已被其他任务更新") -> None:
        super().__init__(message)


class ProjectCancellationRequested(SchedulingDomainException):
    def __init__(self) -> None:
        super().__init__("项目已请求停止")


class ProjectRuntimeNotFound(SchedulingDomainException):
    def __init__(self) -> None:
        super().__init__("项目尚未启动")


class RuntimeStageNotFound(SchedulingDomainException):
    def __init__(self) -> None:
        super().__init__("运行阶段不存在")


class WorkerTaskNotFound(SchedulingDomainException):
    def __init__(self) -> None:
        super().__init__("角色任务不存在")


class InvalidTaskMessage(SchedulingDomainException):
    def __init__(self, reason: str) -> None:
        super().__init__(f"任务消息不合法: {reason}")
