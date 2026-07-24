from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from backend.scheduling.executor import TaskExecutor


class ExecutorProvider(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[TaskExecutor]: ...


_executor_provider: ExecutorProvider | None = None


def configure_executor_provider(provider: ExecutorProvider) -> None:
    global _executor_provider
    _executor_provider = provider


def get_executor_scope() -> AbstractAsyncContextManager[TaskExecutor]:
    if _executor_provider is not None:
        return _executor_provider()

    from backend.bootstrap import create_executor_scope

    return create_executor_scope()
