"""进入日志、事件和模型上下文前的敏感文本过滤。"""

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?i)(password|passwd|pwd|token|secret|api[_-]?key|authorization)"
        r"\s*[:=]\s*([^\s,;]+)"
    ),
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"),
)


def redact_sensitive_text(value: str | None, *, max_length: int) -> str | None:
    """脱敏并限制不可信文本长度。"""
    if value is None:
        return None
    redacted = _CONTROL_CHARS.sub("", value).strip()
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(
            lambda match: f"{match.group(1)}=[REDACTED]" if match.lastindex else "[REDACTED]",
            redacted,
        )
    return redacted[:max_length] or None
