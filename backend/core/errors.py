from __future__ import annotations

from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    INVALID_CREDENTIALS = 40101
    PROJECT_ACCESS_DENIED = 40302
    OPERATION_PERMISSION_DENIED = 40303
    RESOURCE_NOT_FOUND = 40401
    RESOURCE_CONFLICT = 40901
    VALIDATION_FAILED = 42201
    BUSINESS_RULE_VIOLATION = 42202
    INTERNAL_ERROR = 50001
    ANALYSIS_FAILED = 50002
    EXTERNAL_SERVICE_UNAVAILABLE = 50003


class AppError(Exception):
    http_status = 500

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        detail: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail
        self.context = context or {}


class AuthenticationError(AppError):
    http_status = 401


class PermissionDeniedError(AppError):
    http_status = 403


class ResourceNotFoundError(AppError):
    http_status = 404


class ResourceConflictError(AppError):
    http_status = 409


class BusinessError(AppError):
    http_status = 422


class AnalysisError(AppError):
    http_status = 500


class ExternalServiceError(AppError):
    http_status = 502


class TaskAlreadyRunningError(ResourceConflictError):
    def __init__(self, task_id: str) -> None:
        super().__init__(
            ErrorCode.RESOURCE_CONFLICT,
            "任务正在执行，请勿重复提交",
            context={"task_id": task_id},
        )


class TaskCancelledError(BusinessError):
    def __init__(self, task_id: str) -> None:
        super().__init__(
            ErrorCode.BUSINESS_RULE_VIOLATION,
            "任务已取消",
            context={"task_id": task_id},
        )


class TokenBudgetExceededError(AnalysisError):
    def __init__(self, *, limit: int, used: int, requested: int) -> None:
        super().__init__(
            ErrorCode.ANALYSIS_FAILED,
            "任务 token 预算不足",
            detail=f"limit={limit}, used={used}, requested={requested}",
        )

