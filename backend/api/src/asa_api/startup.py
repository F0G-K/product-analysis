"""ASA API 进程启动入口。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import NoReturn

import uvicorn


def _parse_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _parse_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class ApiStartupSettings:
    """Uvicorn 启动参数，统一从 ``ASA_API_*`` 环境变量读取。"""

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    log_level: str = "info"

    @classmethod
    def from_env(cls) -> ApiStartupSettings:
        host = os.getenv("ASA_API_HOST", "127.0.0.1").strip()
        if not host:
            raise ValueError("ASA_API_HOST must not be empty")

        log_level = os.getenv("ASA_API_LOG_LEVEL", "info").strip().lower()
        allowed_log_levels = {"critical", "error", "warning", "info", "debug", "trace"}
        if log_level not in allowed_log_levels:
            raise ValueError(
                "ASA_API_LOG_LEVEL must be one of: " + ", ".join(sorted(allowed_log_levels))
            )

        reload_enabled = _parse_bool("ASA_API_RELOAD")
        workers = _parse_int("ASA_API_WORKERS", 1, minimum=1, maximum=64)
        if reload_enabled and workers != 1:
            raise ValueError("ASA_API_WORKERS must be 1 when ASA_API_RELOAD is enabled")

        return cls(
            host=host,
            port=_parse_int("ASA_API_PORT", 8000, minimum=1, maximum=65535),
            reload=reload_enabled,
            workers=workers,
            log_level=log_level,
        )


class ApiApplication:
    """负责校验配置并启动 Uvicorn 的应用启动类。"""

    def __init__(self, settings: ApiStartupSettings | None = None) -> None:
        self.settings = settings or ApiStartupSettings.from_env()

    def run(self) -> NoReturn:
        uvicorn.run(
            "asa_api.main:app",
            host=self.settings.host,
            port=self.settings.port,
            reload=self.settings.reload,
            workers=self.settings.workers,
            log_level=self.settings.log_level,
        )
        raise SystemExit(0)


def main() -> NoReturn:
    """控制台脚本入口。"""

    ApiApplication().run()
