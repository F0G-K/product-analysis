"""项目状态机。"""

from asa_core.domain.projects.entities import ProjectStatus
from asa_core.domain.projects.exceptions import (
    ProjectDeleteForbidden,
    ProjectNotRunning,
    ProjectStatusConflict,
)


class ProjectStatusMachine:
    """集中维护项目状态规则，避免各层重复判断。"""

    _TRANSITIONS: dict[ProjectStatus, frozenset[ProjectStatus]] = {
        ProjectStatus.CREATED: frozenset({ProjectStatus.RUNNING, ProjectStatus.FAILED}),
        ProjectStatus.RUNNING: frozenset(
            {
                ProjectStatus.COMPLETED,
                ProjectStatus.FAILED,
                ProjectStatus.STOPPED,
            }
        ),
        ProjectStatus.COMPLETED: frozenset(),
        ProjectStatus.FAILED: frozenset(),
        ProjectStatus.STOPPED: frozenset(),
    }

    @classmethod
    def ensure_transition(cls, current: str, target: str) -> None:
        current_status = ProjectStatus(current)
        target_status = ProjectStatus(target)
        if target_status not in cls._TRANSITIONS[current_status]:
            raise ProjectStatusConflict(
                current_status,
                sorted(status.value for status in cls._TRANSITIONS[current_status]),
            )

    @staticmethod
    def ensure_can_start(current: str) -> None:
        if current != ProjectStatus.CREATED:
            raise ProjectStatusConflict(current, [ProjectStatus.CREATED])

    @staticmethod
    def ensure_can_stop(current: str) -> None:
        if current != ProjectStatus.RUNNING:
            raise ProjectNotRunning(current)

    @staticmethod
    def ensure_can_delete(current: str) -> None:
        if current == ProjectStatus.RUNNING:
            raise ProjectDeleteForbidden(current)
