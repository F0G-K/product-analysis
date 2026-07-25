"""项目领域值对象。"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectName:
    """项目名称，写入前统一去除首尾空白。"""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not 1 <= len(normalized) <= 128:
            raise ValueError("项目名称长度必须在 1-128 字符之间")
        if any(ord(character) < 32 for character in normalized):
            raise ValueError("项目名称不得包含控制字符")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class TaskContent:
    """评估任务说明。"""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise ValueError("评估任务说明不得为空")
        if "\x00" in normalized:
            raise ValueError("评估任务说明不得包含空字符")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class EnvironmentType:
    """隔离环境类型标识。"""

    value: str

    _PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not self._PATTERN.fullmatch(normalized):
            raise ValueError("隔离环境类型格式不合法")
        object.__setattr__(self, "value", normalized)
