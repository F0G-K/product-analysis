"""角色任务状态机和阶段任务分发策略。"""

from dataclasses import dataclass

from asa_core.domain.scheduling.entities import ExecutionStatus, StageName
from asa_core.domain.scheduling.exceptions import InvalidTaskTransition


class TaskStateMachine:
    """角色任务只允许 idle → running → success/failed。"""

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
            raise InvalidTaskTransition(current_status, target_status)


@dataclass(frozen=True, slots=True)
class StageTaskSpec:
    """一个阶段内需要创建的角色任务定义。"""

    worker_role: str
    task_content: str
    critical: bool = True
    depends_on: tuple[str, ...] = ()


class TaskDistributionPolicy:
    """MVP 固定阶段任务图；跨阶段仍由调度器串行推进。"""

    _TASKS: dict[StageName, tuple[StageTaskSpec, ...]] = {
        StageName.ENVIRONMENT_SCAN: (
            StageTaskSpec(
                worker_role="environment_inspector",
                task_content="识别项目技术栈、依赖、目录结构和运行条件。",
            ),
            StageTaskSpec(
                worker_role="operations_assistant",
                task_content="准备受控执行环境并采集环境阶段的基础资源信息。",
            ),
        ),
        StageName.CODE_ANALYSIS: (
            StageTaskSpec(
                worker_role="code_analyst",
                task_content="分析源码安全风险，输出候选漏洞、位置和初始证据。",
            ),
            StageTaskSpec(
                worker_role="general",
                task_content="汇总代码分析结果并去除重复候选项。",
                critical=False,
                depends_on=("code_analyst",),
            ),
        ),
        StageName.VULNERABILITY_VERIFY: (
            StageTaskSpec(
                worker_role="vulnerability_verifier",
                task_content="验证候选漏洞的可达性、触发条件、证据和影响。",
            ),
        ),
        StageName.REPORT_GENERATE: (
            StageTaskSpec(
                worker_role="report_editor",
                task_content="汇总漏洞与攻击路径，形成结构化报告内容。",
            ),
        ),
        StageName.DONE: (),
    }

    @classmethod
    def tasks_for(cls, stage_name: StageName | str) -> tuple[StageTaskSpec, ...]:
        return cls._TASKS[StageName(stage_name)]

    @classmethod
    def is_critical(cls, stage_name: StageName | str, worker_role: str) -> bool:
        return any(spec.worker_role == worker_role and spec.critical for spec in cls.tasks_for(stage_name))

    @classmethod
    def ready_roles(
        cls,
        stage_name: StageName | str,
        completed_roles: set[str],
        existing_roles: set[str],
    ) -> tuple[StageTaskSpec, ...]:
        """返回依赖已满足且尚未创建的任务，供受控并行分发。"""
        return tuple(
            spec
            for spec in cls.tasks_for(stage_name)
            if spec.worker_role not in existing_roles and set(spec.depends_on).issubset(completed_roles)
        )
