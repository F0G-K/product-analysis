"""同步 Celery Task 与异步应用服务之间的桥接。"""

import asyncio
from collections.abc import Coroutine
from typing import Any


def run_async[ResultT](coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    """Celery prefork 子进程内为单次任务创建明确事件循环边界。"""
    return asyncio.run(coroutine)
