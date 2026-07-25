"""角色工具最小权限矩阵。"""

from enum import StrEnum

from asa_core.domain.agents.exceptions import ToolNotAllowed
from asa_core.domain.agents.role import WorkerRole


class ToolName(StrEnum):
    FILE_READ = "file_read"
    DIRECTORY_LIST = "directory_list"
    KEYWORD_SEARCH = "keyword_search"
    CONTROLLED_COMMAND = "controlled_command"
    VULNERABILITY_DATABASE = "vulnerability_database"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    SECURITY_KNOWLEDGE = "search_security_knowledge"


class ToolPermissionPolicy:
    """工具权限由 Worker 端白名单控制，模型不能自行扩权。"""

    _PERMISSIONS: dict[WorkerRole, frozenset[ToolName]] = {
        WorkerRole.GENERAL: frozenset(),
        WorkerRole.ENVIRONMENT_INSPECTOR: frozenset(
            {
                ToolName.FILE_READ,
                ToolName.DIRECTORY_LIST,
                ToolName.KEYWORD_SEARCH,
                ToolName.DEPENDENCY_ANALYSIS,
            }
        ),
        WorkerRole.CODE_ANALYST: frozenset(
            {
                ToolName.FILE_READ,
                ToolName.DIRECTORY_LIST,
                ToolName.KEYWORD_SEARCH,
                ToolName.VULNERABILITY_DATABASE,
                ToolName.SECURITY_KNOWLEDGE,
            }
        ),
        WorkerRole.VULNERABILITY_VERIFIER: frozenset(
            {
                ToolName.FILE_READ,
                ToolName.DIRECTORY_LIST,
                ToolName.KEYWORD_SEARCH,
                ToolName.CONTROLLED_COMMAND,
                ToolName.VULNERABILITY_DATABASE,
                ToolName.SECURITY_KNOWLEDGE,
            }
        ),
        WorkerRole.REPORT_EDITOR: frozenset({ToolName.FILE_READ}),
        WorkerRole.OPERATIONS_ASSISTANT: frozenset(
            {
                ToolName.FILE_READ,
                ToolName.DIRECTORY_LIST,
                ToolName.KEYWORD_SEARCH,
                ToolName.CONTROLLED_COMMAND,
            }
        ),
    }

    @classmethod
    def allowed_tools(cls, role: WorkerRole | str) -> frozenset[ToolName]:
        return cls._PERMISSIONS[WorkerRole(role)]

    @classmethod
    def ensure_allowed(
        cls,
        role: WorkerRole | str,
        tool_name: ToolName | str,
    ) -> None:
        worker_role = WorkerRole(role)
        tool = ToolName(tool_name)
        if tool not in cls.allowed_tools(worker_role):
            raise ToolNotAllowed(worker_role, tool)
