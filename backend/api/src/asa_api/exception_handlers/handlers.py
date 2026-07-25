"""API 全局异常处理器。

将领域异常和框架异常映射为统一的 ApiResponse 格式。
"""

from asa_api.middleware.request_id import get_request_id
from asa_core.domain.auth.exceptions import (
    AccountDisabled,
    AdminRequired,
    AuthenticationRequired,
    CsrfValidationFailed,
    InvalidCredentials,
    PasswordValidationError,
    PermissionDenied,
    SessionExpired,
    SystemAlreadyInitialized,
    SystemNotInitialized,
    UsernameAlreadyExists,
    UserNotFound,
)
from asa_core.domain.projects.exceptions import (
    DependencyUnavailable,
    EnvironmentTypeDisabled,
    IdempotencyKeyReused,
    ProjectAccessDenied,
    ProjectCapacityExceeded,
    ProjectDeleteForbidden,
    ProjectDomainException,
    ProjectNameConfirmationMismatch,
    ProjectNotFound,
    ProjectNotRunning,
    ProjectStatusConflict,
    SourceCredentialForbidden,
    SourcePathInvalid,
)
from asa_core.domain.scheduling.exceptions import ProjectRuntimeNotFound
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError


def _build_error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    data: dict | None = None,
) -> JSONResponse:
    """构造统一格式的错误响应。"""
    request_id = get_request_id(request)
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "data": data,
            "request_id": str(request_id),
        },
    )


# --- 领域异常处理器 ---


async def handle_system_already_initialized(
    request: Request,
    exc: SystemAlreadyInitialized,
) -> JSONResponse:
    """系统已初始化 → 409 Conflict。"""
    return _build_error_response(request, 409, "SYSTEM_ALREADY_INITIALIZED", exc.message)


async def handle_system_not_initialized(
    request: Request,
    exc: SystemNotInitialized,
) -> JSONResponse:
    """系统未初始化 → 409 Conflict。"""
    return _build_error_response(request, 409, "SYSTEM_NOT_INITIALIZED", exc.message)


async def handle_invalid_credentials(
    request: Request,
    exc: InvalidCredentials,
) -> JSONResponse:
    """无效凭据 → 401 Unauthorized。"""
    return _build_error_response(request, 401, "INVALID_CREDENTIALS", exc.message)


async def handle_account_disabled(
    request: Request,
    exc: AccountDisabled,
) -> JSONResponse:
    """账户禁用 → 403 Forbidden。"""
    return _build_error_response(request, 403, "ACCOUNT_DISABLED", exc.message)


async def handle_authentication_required(
    request: Request,
    exc: AuthenticationRequired,
) -> JSONResponse:
    """需要认证 → 401 Unauthorized。"""
    return _build_error_response(request, 401, "AUTH_REQUIRED", exc.message)


async def handle_session_expired(
    request: Request,
    exc: SessionExpired,
) -> JSONResponse:
    """会话过期 → 401 Unauthorized。"""
    return _build_error_response(request, 401, "SESSION_EXPIRED", exc.message)


async def handle_csrf_validation_failed(
    request: Request,
    exc: CsrfValidationFailed,
) -> JSONResponse:
    """CSRF 校验失败 → 403 Forbidden。"""
    return _build_error_response(request, 403, "CSRF_INVALID", exc.message)


async def handle_admin_required(
    request: Request,
    exc: AdminRequired,
) -> JSONResponse:
    """需要管理员权限 → 403 Forbidden。"""
    return _build_error_response(request, 403, "ADMIN_REQUIRED", exc.message)


async def handle_user_not_found(
    request: Request,
    exc: UserNotFound,
) -> JSONResponse:
    """用户不存在 → 404 Not Found。"""
    return _build_error_response(request, 404, "USER_NOT_FOUND", exc.message)


async def handle_username_already_exists(
    request: Request,
    exc: UsernameAlreadyExists,
) -> JSONResponse:
    """用户名已存在 → 409 Conflict。"""
    return _build_error_response(request, 409, "USERNAME_ALREADY_EXISTS", exc.message)


async def handle_permission_denied(
    request: Request,
    exc: PermissionDenied,
) -> JSONResponse:
    """权限不足 → 403 Forbidden。"""
    return _build_error_response(request, 403, "PERMISSION_DENIED", exc.message)


async def handle_password_validation_error(
    request: Request,
    exc: PasswordValidationError,
) -> JSONResponse:
    """密码不符合要求 → 422 Unprocessable Entity。"""
    return _build_error_response(request, 422, "PASSWORD_VALIDATION_ERROR", exc.message)


def _project_error_data(exc: ProjectDomainException) -> dict | None:
    """提取项目异常中已脱敏的响应上下文。"""

    return exc.data


async def handle_project_not_found(
    request: Request,
    exc: ProjectNotFound,
) -> JSONResponse:
    return _build_error_response(request, 404, "PROJECT_NOT_FOUND", exc.message)


async def handle_project_access_denied(
    request: Request,
    exc: ProjectAccessDenied,
) -> JSONResponse:
    return _build_error_response(request, 403, "PROJECT_ACCESS_DENIED", exc.message)


async def handle_project_status_conflict(
    request: Request,
    exc: ProjectStatusConflict,
) -> JSONResponse:
    return _build_error_response(
        request,
        409,
        "PROJECT_STATUS_CONFLICT",
        exc.message,
        _project_error_data(exc),
    )


async def handle_project_not_running(
    request: Request,
    exc: ProjectNotRunning,
) -> JSONResponse:
    return _build_error_response(
        request,
        409,
        "PROJECT_NOT_RUNNING",
        exc.message,
        _project_error_data(exc),
    )


async def handle_project_capacity_exceeded(
    request: Request,
    exc: ProjectCapacityExceeded,
) -> JSONResponse:
    return _build_error_response(
        request,
        409,
        "PROJECT_CAPACITY_EXCEEDED",
        exc.message,
        _project_error_data(exc),
    )


async def handle_project_delete_forbidden(
    request: Request,
    exc: ProjectDeleteForbidden,
) -> JSONResponse:
    return _build_error_response(
        request,
        409,
        "PROJECT_DELETE_FORBIDDEN",
        exc.message,
        _project_error_data(exc),
    )


async def handle_project_name_confirmation_mismatch(
    request: Request,
    exc: ProjectNameConfirmationMismatch,
) -> JSONResponse:
    return _build_error_response(
        request,
        409,
        "PROJECT_NAME_CONFIRMATION_MISMATCH",
        exc.message,
    )


async def handle_source_path_invalid(
    request: Request,
    exc: SourcePathInvalid,
) -> JSONResponse:
    return _build_error_response(
        request,
        422,
        "SOURCE_PATH_INVALID",
        exc.message,
        _project_error_data(exc),
    )


async def handle_source_credential_forbidden(
    request: Request,
    exc: SourceCredentialForbidden,
) -> JSONResponse:
    return _build_error_response(
        request,
        422,
        "SOURCE_CREDENTIAL_FORBIDDEN",
        exc.message,
    )


async def handle_environment_type_disabled(
    request: Request,
    exc: EnvironmentTypeDisabled,
) -> JSONResponse:
    return _build_error_response(
        request,
        409,
        "ENVIRONMENT_TYPE_DISABLED",
        exc.message,
        _project_error_data(exc),
    )


async def handle_idempotency_key_reused(
    request: Request,
    exc: IdempotencyKeyReused,
) -> JSONResponse:
    return _build_error_response(request, 409, "IDEMPOTENCY_KEY_REUSED", exc.message)


async def handle_dependency_unavailable(
    request: Request,
    exc: DependencyUnavailable,
) -> JSONResponse:
    return _build_error_response(request, 503, "DEPENDENCY_UNAVAILABLE", exc.message)


async def handle_project_runtime_not_found(
    request: Request,
    exc: ProjectRuntimeNotFound,
) -> JSONResponse:
    return _build_error_response(
        request,
        404,
        "PROJECT_RUNTIME_NOT_FOUND",
        exc.message,
    )


# --- 框架异常处理器 ---


async def handle_validation_error(
    request: Request,
    exc: RequestValidationError | PydanticValidationError,
) -> JSONResponse:
    """请求参数校验失败 → 422 Unprocessable Entity。

    将 Pydantic/Starlette 的校验错误转换为 API 文档规定的 fields 格式。
    """
    errors: list[dict[str, str]] = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        errors.append(
            {
                "field": field_path,
                "reason": error["msg"],
            }
        )

    return _build_error_response(
        request,
        422,
        "VALIDATION_ERROR",
        "请求参数校验失败",
        data={"errors": errors},
    )


async def handle_internal_error(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """未预期错误 → 500 Internal Server Error。

    注意：生产环境不返回堆栈信息。
    """
    return _build_error_response(request, 500, "INTERNAL_ERROR", "服务器内部错误")


def register_exception_handlers(app):
    """在 FastAPI 应用上注册所有异常处理器。"""
    app.add_exception_handler(SystemAlreadyInitialized, handle_system_already_initialized)
    app.add_exception_handler(SystemNotInitialized, handle_system_not_initialized)
    app.add_exception_handler(InvalidCredentials, handle_invalid_credentials)
    app.add_exception_handler(AccountDisabled, handle_account_disabled)
    app.add_exception_handler(AuthenticationRequired, handle_authentication_required)
    app.add_exception_handler(SessionExpired, handle_session_expired)
    app.add_exception_handler(CsrfValidationFailed, handle_csrf_validation_failed)
    app.add_exception_handler(AdminRequired, handle_admin_required)
    app.add_exception_handler(UserNotFound, handle_user_not_found)
    app.add_exception_handler(UsernameAlreadyExists, handle_username_already_exists)
    app.add_exception_handler(PermissionDenied, handle_permission_denied)
    app.add_exception_handler(PasswordValidationError, handle_password_validation_error)
    app.add_exception_handler(ProjectNotFound, handle_project_not_found)
    app.add_exception_handler(ProjectAccessDenied, handle_project_access_denied)
    app.add_exception_handler(ProjectStatusConflict, handle_project_status_conflict)
    app.add_exception_handler(ProjectNotRunning, handle_project_not_running)
    app.add_exception_handler(
        ProjectCapacityExceeded,
        handle_project_capacity_exceeded,
    )
    app.add_exception_handler(ProjectDeleteForbidden, handle_project_delete_forbidden)
    app.add_exception_handler(
        ProjectNameConfirmationMismatch,
        handle_project_name_confirmation_mismatch,
    )
    app.add_exception_handler(SourcePathInvalid, handle_source_path_invalid)
    app.add_exception_handler(
        SourceCredentialForbidden,
        handle_source_credential_forbidden,
    )
    app.add_exception_handler(
        EnvironmentTypeDisabled,
        handle_environment_type_disabled,
    )
    app.add_exception_handler(IdempotencyKeyReused, handle_idempotency_key_reused)
    app.add_exception_handler(DependencyUnavailable, handle_dependency_unavailable)
    app.add_exception_handler(ProjectRuntimeNotFound, handle_project_runtime_not_found)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(PydanticValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_internal_error)
