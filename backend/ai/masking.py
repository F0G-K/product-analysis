from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


class SensitiveDataMasker:
    """在数据进入检索索引或大模型前统一脱敏。"""

    _patterns: tuple[tuple[re.Pattern[str], str], ...] = (
        (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "1**********"),
        (
            re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b"),
            "***@***.***",
        ),
        (re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "******************"),
        (
            re.compile(
                r"(?i)\b(sk|api[_-]?key|access[_-]?token|token)\b\s*[:=]\s*[\w.-]+"
            ),
            r"\1=***",
        ),
    )

    def mask_text(self, value: str) -> str:
        masked = value
        for pattern, replacement in self._patterns:
            masked = pattern.sub(replacement, masked)
        return masked

    def mask(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.mask_text(value)
        if isinstance(value, Mapping):
            return {str(key): self.mask(item) for key, item in value.items()}
        if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            return [self.mask(item) for item in value]
        return value

