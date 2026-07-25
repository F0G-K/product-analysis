"""六类固定 AI 执行角色。"""

from dataclasses import dataclass
from enum import StrEnum

from asa_core.domain.agents.exceptions import RoleNotAllowedForStage
from asa_core.domain.scheduling.entities import STAGE_SEQUENCE, StageName


class WorkerRole(StrEnum):
    GENERAL = "general"
    ENVIRONMENT_INSPECTOR = "environment_inspector"
    CODE_ANALYST = "code_analyst"
    VULNERABILITY_VERIFIER = "vulnerability_verifier"
    REPORT_EDITOR = "report_editor"
    OPERATIONS_ASSISTANT = "operations_assistant"


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    role: WorkerRole
    description: str
    allowed_stages: frozenset[StageName]
    rag_enabled: bool = False


class RoleRegistry:
    """角色注册表是固定白名单，不接受模型或请求动态扩展。"""

    _ALL_STAGES = frozenset(STAGE_SEQUENCE)
    _DEFINITIONS: dict[WorkerRole, RoleDefinition] = {
        WorkerRole.GENERAL: RoleDefinition(
            WorkerRole.GENERAL,
            "解析任务、裁剪上下文并汇总角色协作结果",
            _ALL_STAGES,
        ),
        WorkerRole.ENVIRONMENT_INSPECTOR: RoleDefinition(
            WorkerRole.ENVIRONMENT_INSPECTOR,
            "识别技术栈、依赖、目录结构和运行条件",
            frozenset({StageName.ENVIRONMENT_SCAN}),
        ),
        WorkerRole.CODE_ANALYST: RoleDefinition(
            WorkerRole.CODE_ANALYST,
            "分析源码并识别候选安全问题",
            frozenset({StageName.CODE_ANALYSIS}),
            rag_enabled=True,
        ),
        WorkerRole.VULNERABILITY_VERIFIER: RoleDefinition(
            WorkerRole.VULNERABILITY_VERIFIER,
            "验证漏洞可达性、触发条件、证据与影响",
            frozenset({StageName.VULNERABILITY_VERIFY}),
            rag_enabled=True,
        ),
        WorkerRole.REPORT_EDITOR: RoleDefinition(
            WorkerRole.REPORT_EDITOR,
            "汇总漏洞、攻击路径和修复建议",
            frozenset({StageName.REPORT_GENERATE}),
        ),
        WorkerRole.OPERATIONS_ASSISTANT: RoleDefinition(
            WorkerRole.OPERATIONS_ASSISTANT,
            "通过受控工具处理环境、文件、命令和资源采样",
            _ALL_STAGES,
        ),
    }

    @classmethod
    def get(cls, role: WorkerRole | str) -> RoleDefinition:
        return cls._DEFINITIONS[WorkerRole(role)]

    @classmethod
    def ensure_allowed(
        cls,
        role: WorkerRole | str,
        stage_name: StageName | str,
    ) -> RoleDefinition:
        definition = cls.get(role)
        stage = StageName(stage_name)
        if stage not in definition.allowed_stages:
            raise RoleNotAllowedForStage(definition.role, stage)
        return definition
