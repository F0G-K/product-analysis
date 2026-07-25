"""项目停止协同策略。"""

from asa_core.domain.scheduling.entities import ProjectExecution
from asa_core.domain.scheduling.exceptions import ProjectCancellationRequested


class CancelPolicy:
    """数据库停止标记是权威取消信号，Redis 仅用于加速。"""

    @staticmethod
    def is_cancellation_requested(project: ProjectExecution) -> bool:
        return project.stop_requested_at is not None

    @classmethod
    def ensure_not_cancelled(cls, project: ProjectExecution) -> None:
        if cls.is_cancellation_requested(project):
            raise ProjectCancellationRequested()
