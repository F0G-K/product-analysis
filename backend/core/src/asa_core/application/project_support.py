"""项目应用用例共享工具。"""

import hashlib
import json
import re
import uuid
from typing import Any

from asa_core.application.services.sensitive_text import redact_sensitive_text
from asa_core.domain.projects.exceptions import IdempotencyKeyReused

_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


def parse_uuid(value: str, *, field_name: str) -> uuid.UUID:
    """解析 UUID，失败时抛出可由 Pydantic/Router 映射的 ValueError。"""

    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{field_name} 必须是有效 UUID") from exc


def validate_idempotency_key(value: str) -> str:
    """校验 Idempotency-Key 格式和长度。"""

    normalized = value.strip()
    if not _IDEMPOTENCY_KEY_PATTERN.fullmatch(normalized):
        raise ValueError("Idempotency-Key 必须为 8-128 位安全字符")
    return normalized


def build_request_fingerprint(
    *,
    actor_user_id: uuid.UUID,
    project_id: uuid.UUID,
    operation: str,
    payload: dict[str, Any],
) -> str:
    """生成稳定请求指纹，不持久化原始敏感输入。"""

    encoded = json.dumps(
        {
            "actor_user_id": str(actor_user_id),
            "project_id": str(project_id),
            "operation": operation,
            "payload": payload,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def ensure_idempotent_match(
    *,
    existing_operation: str,
    existing_fingerprint: str,
    expected_operation: str,
    expected_fingerprint: str,
) -> None:
    """确认幂等重放与首次请求完全一致。"""

    if existing_operation != expected_operation or existing_fingerprint != expected_fingerprint:
        raise IdempotencyKeyReused()


def redact_user_text(value: str | None, *, max_length: int) -> str | None:
    """最小化用户说明，去除控制字符并限制长度。"""

    return redact_sensitive_text(value, max_length=max_length)
