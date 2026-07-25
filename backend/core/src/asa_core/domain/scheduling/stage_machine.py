"""阶段状态机与固定顺序校验。"""

from datetime import datetime

from asa_core.domain.scheduling.entities import ExecutionStatus, RuntimeStage
from asa_core.domain.scheduling.exceptions import (
    InvalidStageTransition,
    ProjectCancellationRequested,
    StagePrerequisiteNotMet,
)


class StageStateMachine:
    """集中维护阶段状态迁移，禁止跨层复制规则。"""

    _TRANSITIONS: dict[ExecutionStatus, frozenset[ExecutionStatus]] = {
        ExecutionStatus.IDLE: frozenset({ExecutionStatus.RUNNING}),
        ExecutionStatus.RUNNING: frozenset({ExecutionStatus.SUCCESS, ExecutionStatus.FAILED}),
        ExecutionStatus.SUCCESS: frozenset(),
        ExecutionStatus.FAILED: frozenset(),
    }

    @classmethod
    def ensure_transition(
        cls,
        current: ExecutionStatus | str,
        target: ExecutionStatus | str,
    ) -> None:
        current_status = ExecutionStatus(current)
        target_status = ExecutionStatus(target)
        if target_status not in cls._TRANSITIONS[current_status]:
            raise InvalidStageTransition(current_status, target_status)

    @classmethod
    def ensure_can_start(
        cls,
        stage: RuntimeStage,
        *,
        previous_stage: RuntimeStage | None,
        stop_requested: bool,
    ) -> None:
        if stop_requested:
            raise ProjectCancellationRequested()
        cls.ensure_transition(stage.stage_status, ExecutionStatus.RUNNING)
        if stage.stage_order == 1:
            return
        if (
            previous_stage is None
            or previous_stage.stage_order != stage.stage_order - 1
            or previous_stage.stage_status != ExecutionStatus.SUCCESS
        ):
            raise StagePrerequisiteNotMet(stage.stage_name)

    @staticmethod
    def validate_terminal_payload(
        target: ExecutionStatus | str,
        *,
        finished_at: datetime,
        error_message: str | None,
    ) -> None:
        target_status = ExecutionStatus(target)
        if finished_at.tzinfo is None:
            raise ValueError("finished_at 必须包含时区")
        if target_status == ExecutionStatus.FAILED and not error_message:
            raise ValueError("失败阶段必须包含错误摘要")
        if target_status == ExecutionStatus.SUCCESS and error_message is not None:
            raise ValueError("成功阶段不能包含错误摘要")
