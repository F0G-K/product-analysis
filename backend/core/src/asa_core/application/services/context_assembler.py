"""按项目、阶段和角色最小化组装模型上下文。"""

from dataclasses import dataclass
from typing import Any

from asa_core.application.ports.context_source import AgentContextSource
from asa_core.application.ports.model_port import ModelPort, ModelTool
from asa_core.application.ports.rag_retriever import KnowledgeMatch, RagRetriever
from asa_core.application.services.sensitive_text import redact_sensitive_text
from asa_core.domain.agents.role import RoleRegistry
from asa_core.domain.agents.tool_permissions import ToolName, ToolPermissionPolicy
from asa_core.domain.scheduling.entities import RuntimeStage, WorkerTask


@dataclass(frozen=True, slots=True)
class AssembledContext:
    system_prompt: str
    user_prompt: str
    context: dict[str, Any]
    tools: tuple[ModelTool, ...]


class ContextAssembler:
    """上下文按预算裁剪；RAG 失败时不阻断角色执行。"""

    def __init__(
        self,
        *,
        context_source: AgentContextSource,
        rag_retriever: RagRetriever,
        model: ModelPort,
        max_tokens: int,
        rag_max_tokens: int,
    ):
        if max_tokens <= 0 or rag_max_tokens < 0 or rag_max_tokens > max_tokens:
            raise ValueError("上下文 token 配置不合法")
        self._context_source = context_source
        self._rag_retriever = rag_retriever
        self._model = model
        self._max_tokens = max_tokens
        self._rag_max_tokens = rag_max_tokens

    async def assemble(
        self,
        *,
        task: WorkerTask,
        stage: RuntimeStage,
    ) -> AssembledContext:
        role = RoleRegistry.ensure_allowed(task.worker_role, stage.stage_name)
        project = await self._context_source.get_project_context(task.project_id)
        previous_results = await self._context_source.get_previous_results(
            task.project_id,
            stage,
        )
        source_snippets = await self._context_source.get_source_snippets(task)

        # 检索查询只使用脱敏摘要，不把完整源码或凭证发送给 Embedding 服务。
        query_text = (
            redact_sensitive_text(
                " ".join(
                    [
                        project.environment_type,
                        task.task_content,
                        *(str(item.get("summary", "")) for item in previous_results),
                    ]
                ),
                max_length=2000,
            )
            or task.task_content[:2000]
        )
        knowledge: list[KnowledgeMatch] = []
        if role.rag_enabled:
            try:
                knowledge = await self._rag_retriever.retrieve_for_task(
                    task=task,
                    stage=stage,
                    query_text=query_text,
                )
            except Exception:
                # RAG 是增强能力，异常只降级，不改变任务业务结果。
                knowledge = []

        context: dict[str, Any] = {
            "project": {
                "name": redact_sensitive_text(project.project_name, max_length=128),
                "task_content": redact_sensitive_text(project.task_content, max_length=4000),
                "environment_type": project.environment_type,
            },
            "stage": stage.stage_name.value,
            "previous_results": self._sanitize_items(previous_results, item_limit=20),
            "knowledge": self._format_knowledge(knowledge),
            "source_snippets": self._sanitize_items(source_snippets, item_limit=20),
        }
        self._trim_context(context)

        tools = tuple(
            self._tool_definition(tool)
            for tool in sorted(
                ToolPermissionPolicy.allowed_tools(task.worker_role),
                key=str,
            )
        )
        return AssembledContext(
            system_prompt=(
                f"你是 {role.role.value}。仅处理 {stage.stage_name.value} 阶段，"
                "只能使用声明的工具，输出必须符合给定 JSON Schema。"
            ),
            user_prompt=redact_sensitive_text(task.task_content, max_length=4000) or "执行当前角色任务。",
            context=context,
            tools=tools,
        )

    def _trim_context(self, context: dict[str, Any]) -> None:
        """优先裁剪 RAG，再裁剪源码片段，保留项目与前序结果。"""
        while self._model.estimate_tokens(str(context)) > self._max_tokens:
            knowledge = context["knowledge"]
            snippets = context["source_snippets"]
            if knowledge:
                knowledge.pop()
            elif snippets:
                snippets.pop()
            else:
                break
        while self._model.estimate_tokens(str(context["knowledge"])) > self._rag_max_tokens and context["knowledge"]:
            context["knowledge"].pop()

    @staticmethod
    def _sanitize_items(
        items: list[dict[str, Any]],
        *,
        item_limit: int,
    ) -> list[dict[str, Any]]:
        sanitized: list[dict[str, Any]] = []
        for item in items[:item_limit]:
            sanitized.append(
                {
                    str(key): (redact_sensitive_text(value, max_length=4000) if isinstance(value, str) else value)
                    for key, value in item.items()
                }
            )
        return sanitized

    @staticmethod
    def _format_knowledge(matches: list[KnowledgeMatch]) -> list[dict[str, Any]]:
        return [
            {
                "title": redact_sensitive_text(match.title, max_length=255),
                "content_summary": redact_sensitive_text(
                    match.content_summary,
                    max_length=2000,
                ),
                "knowledge_type": match.knowledge_type,
                "similarity": round(match.similarity, 4),
            }
            for match in matches
            if 0 <= match.similarity <= 1
        ]

    @staticmethod
    def _tool_definition(tool: ToolName) -> ModelTool:
        return ModelTool(
            name=tool.value,
            description=f"受控工具: {tool.value}",
            input_schema={"type": "object", "additionalProperties": False},
        )
