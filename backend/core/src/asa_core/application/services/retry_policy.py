"""Worker 有限重试分类和退避策略。"""

import random
from dataclasses import dataclass

from asa_core.domain.agents.exceptions import ModelCallFailed
from asa_core.domain.scheduling.exceptions import SchedulingDomainException


@dataclass(frozen=True, slots=True)
class RetryDecision:
    retry: bool
    countdown_seconds: int


class TaskRetryPolicy:
    """业务冲突不重试；仅重试明确的短暂基础设施错误。"""

    def __init__(
        self,
        *,
        max_retries: int,
        backoff_base_seconds: int,
        max_backoff_seconds: int = 300,
        jitter_ratio: float = 0.25,
        random_source: random.Random | None = None,
    ):
        if max_retries < 0 or backoff_base_seconds <= 0:
            raise ValueError("重试配置不合法")
        if not 0 <= jitter_ratio <= 1:
            raise ValueError("jitter_ratio 必须在 0 到 1 之间")
        self.max_retries = max_retries
        self._base = backoff_base_seconds
        self._max_backoff = max_backoff_seconds
        self._jitter_ratio = jitter_ratio
        self._random = random_source or random.Random()

    def decide(self, exc: Exception, *, retries: int) -> RetryDecision:
        if retries >= self.max_retries or not self._is_retryable(exc):
            return RetryDecision(False, 0)
        raw = min(self._base * (2**retries), self._max_backoff)
        jitter = raw * self._jitter_ratio
        countdown = max(1, round(self._random.uniform(raw - jitter, raw + jitter)))
        return RetryDecision(True, countdown)

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, ModelCallFailed):
            return exc.retryable
        if isinstance(exc, SchedulingDomainException):
            return False
        return isinstance(exc, (ConnectionError, TimeoutError))
