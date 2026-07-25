"""聊天服务：对话历史管理、任务上下文注入、流式 LLM 调用。"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from backend.ai.llm_providers import LLMProviderFactory
from backend.repositories.task_repository import SQLAlchemyTaskRepositoryFactory

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE_DIR = Path("data")


class ChatService:
    """聊天服务：管理对话上下文并流式调用 LLM。"""

    _DEFAULT_SYSTEM_PROMPT = (
        "你是产品管理智能助手平台的 AI 助手。你可以帮助用户理解分析任务结果、"
        "解释产品数据、提供产品管理建议。回答简洁专业，使用中文。"
        "如果用户提供了任务上下文，请结合任务信息回答。"
    )

    def __init__(
        self,
        provider_factory: LLMProviderFactory,
        default_provider: str = "anthropic",
        default_model: str = "claude-opus-4-8",
        task_repository_factory: SQLAlchemyTaskRepositoryFactory | None = None,
        storage_path: str | None = None,
    ) -> None:
        self._factory = provider_factory
        self._default_provider = default_provider
        self._default_model = default_model
        self._task_repo_factory = task_repository_factory
        self._lock = threading.Lock()

        # 确定存储文件路径
        if storage_path:
            file_path = Path(storage_path)
        else:
            file_path = _DEFAULT_STORAGE_DIR / "conversations.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path = file_path

        self._conversations: dict[str, dict[str, Any]] = self._load()

    # ---- 持久化 ----

    def _load(self) -> dict[str, dict[str, Any]]:
        """从 JSON 文件加载对话数据。"""
        if not self._storage_path.exists():
            return {}
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            logger.warning("chat.invalid_storage_format")
        except (json.JSONDecodeError, OSError):
            logger.exception("chat.load_failed")
        return {}

    def _save(self) -> None:
        """将对话数据写入 JSON 文件（线程安全）。"""
        with self._lock:
            try:
                tmp_path = self._storage_path.with_suffix(".json.tmp")
                tmp_path.write_text(
                    json.dumps(self._conversations, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                tmp_path.replace(self._storage_path)
            except OSError:
                logger.exception("chat.save_failed")

    # ---- CRUD ----

    def create_conversation(self, task_id: str | None = None) -> str:
        """创建新对话，返回 conversation_id。"""
        conv_id = str(uuid4())
        self._conversations[conv_id] = {
            "id": conv_id,
            "task_id": task_id,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()
        return conv_id

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        return self._conversations.get(conversation_id)

    def list_conversations(self) -> list[dict[str, Any]]:
        return sorted(
            self._conversations.values(),
            key=lambda c: c.get("created_at", ""),
            reverse=True,
        )

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            return
        conv["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save()

    async def build_system_prompt(self, task_id: str | None) -> str:
        """构建 system prompt，可选注入任务上下文。"""
        if not task_id or not self._task_repo_factory:
            return self._DEFAULT_SYSTEM_PROMPT

        try:
            async with self._task_repo_factory.create() as repo:
                task = await repo.get(UUID(task_id))
        except Exception:
            logger.warning("chat.load_task_failed", extra={"task_id": task_id})
            return self._DEFAULT_SYSTEM_PROMPT

        if task is None:
            return self._DEFAULT_SYSTEM_PROMPT

        task_type = task.task_type
        if hasattr(task_type, "value"):
            task_type = task_type.value
        task_status = task.status
        if hasattr(task_status, "value"):
            task_status = task_status.value

        context_lines = [
            self._DEFAULT_SYSTEM_PROMPT,
            "",
            "## 当前关联任务上下文",
            f"- 任务 ID: {task.id}",
            f"- 任务标题: {task.title}",
            f"- 任务类型: {task_type}",
            f"- 任务状态: {task_status}",
        ]
        if task.description:
            context_lines.append(f"- 任务描述: {task.description}")
        return "\n".join(context_lines)

    async def chat_stream(
        self,
        *,
        conversation_id: str | None,
        task_id: str | None,
        message: str,
        provider_name: str = "",
        model_name: str = "",
    ) -> AsyncIterator[str]:
        """流式聊天，逐文本块返回。"""
        conv = self._conversations.get(conversation_id) if conversation_id else None
        if conv is None:
            conversation_id = self.create_conversation(task_id)
            conv = self._conversations[conversation_id]

        # 如果传入了 task_id 但对话未绑定，则绑定
        if task_id and not conv.get("task_id"):
            conv["task_id"] = task_id
            self._save()

        # 构建消息列表
        api_messages: list[dict[str, Any]] = []
        for m in conv.get("messages", [])[-20:]:  # 最近 20 条作为上下文
            api_messages.append({"role": m["role"], "content": m["content"]})
        api_messages.append({"role": "user", "content": message})

        # 保存用户消息
        self.add_message(conversation_id, "user", message)

        # 构建 system prompt
        effective_task_id = task_id or conv.get("task_id")
        system_prompt = await self.build_system_prompt(effective_task_id)

        # 选择 provider
        provider_name_effective = provider_name or self._default_provider
        effective_model = model_name or self._default_model

        # 流式输出并收集完整响应
        full_response: list[str] = []
        try:
            provider = self._factory.get(provider_name_effective)
            async for chunk in provider.chat_stream(
                model_name=effective_model,
                system_prompt=system_prompt,
                messages=api_messages,
                max_tokens=4096,
            ):
                full_response.append(chunk)
                yield chunk
        except Exception as exc:
            logger.exception("chat.stream_error")
            err_msg = str(exc)
            # 截取有用信息
            if len(err_msg) > 300:
                err_msg = err_msg[:300] + "..."
            available = self._factory.available_providers
            yield (
                "\n\n> ⚠️ 大模型服务调用失败。\n>\n>"
                f" **Provider:** {provider_name_effective}\n>"
                f" **可用:** {', '.join(available)}\n>"
                f" **错误:** {err_msg}"
            )
            return
        finally:
            # 保存助手响应
            combined = "".join(full_response)
            if combined:
                self.add_message(conversation_id, "assistant", combined)
