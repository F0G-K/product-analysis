"""认证相关路由。

提供系统状态查询、管理员初始化、登录、退出四个端点。

路由前缀：/api/v1/system（由 main.py 中的 app.include_router 设置）
"""

from typing import Any

from asa_api.bootstrap import create_user_repo, get_service_container
from asa_api.dependencies import get_session_token
from asa_api.middleware.request_id import get_request_id
from asa_api.schemas.common import (
    ApiResponse,
    InitData,
    LoginData,
    SystemStatusData,
    UserSummaryResponse,
)
from asa_api.schemas.requests import InitRequest, LoginRequest
from asa_core.application.commands.initialize_system import (
    InitializeSystemCommand,
)
from asa_core.application.commands.login import LoginCommand
from asa_core.application.commands.logout import LogoutCommand
from asa_core.application.queries.get_system_status import GetSystemStatusQuery
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

router = APIRouter(tags=["系统与认证"])


# --- 工具函数 ---


def _ok(code: str, message: str, data: Any, request: Request) -> dict[str, Any]:
    """构造成功响应的 JSON 字典。"""
    return ApiResponse[Any](
        code=code,
        message=message,
        data=data,
        request_id=get_request_id(request),
    ).model_dump(mode="json")


def _set_auth_cookies(
    response: Response,
    session_token: str,
    csrf_token: str,
    max_age: int = 7200,
) -> None:
    """设置认证 Cookie。

    asa_session: HttpOnly（JS 不可访问）。
    asa_csrf: 非 HttpOnly（前端需要读取以设置 X-CSRF-Token 头）。
    """
    response.set_cookie(
        key="asa_session",
        value=session_token,
        httponly=True,
        secure=False,  # 开发环境使用 HTTP；生产环境 Nginx 设置 Secure
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    response.set_cookie(
        key="asa_csrf",
        value=csrf_token,
        httponly=False,  # 前端 JS 需要读取
        secure=False,
        samesite="lax",
        path="/",
        max_age=max_age,
    )


def _clear_auth_cookies(response: Response) -> None:
    """清除认证 Cookie（退出登录时调用）。"""
    response.set_cookie(
        key="asa_session",
        value="",
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=0,
    )
    response.set_cookie(
        key="asa_csrf",
        value="",
        httponly=False,
        secure=False,
        samesite="lax",
        path="/",
        max_age=0,
    )


# --- 端点 ---


@router.get("/status")
async def get_system_status(request: Request) -> JSONResponse:
    """查询系统初始化状态。

    无需认证。供前端判断展示初始化页还是登录页。
    """
    container = get_service_container(request.app)

    async with container.session_factory() as session:
        user_repo = create_user_repo(session)
        initialized = await container.get_system_status_handler.handle(
            GetSystemStatusQuery(),
            user_repo=user_repo,
        )

    content = _ok(
        "SYSTEM_STATUS_OK",
        "查询成功",
        SystemStatusData(initialized=initialized),
        request,
    )
    return JSONResponse(status_code=200, content=content)


@router.post("/init", status_code=201)
async def init_system(
    request: Request,
    body: InitRequest,
) -> JSONResponse:
    """初始化管理员账户。

    仅在系统未初始化时可用。
    使用 advisory lock 防止并发创建多个管理员。
    成功不自动建立登录态。
    """
    container = get_service_container(request.app)

    command = InitializeSystemCommand(
        username=body.username,
        password=body.password,
    )

    async with container.session_factory() as session:
        async with session.begin():
            user_repo = create_user_repo(session)
            result = await container.initialize_system_handler.handle(
                command,
                user_repo=user_repo,
                session=session,
            )

    admin_response = UserSummaryResponse(
        id=str(result.admin.id),
        username=result.admin.username,
        role=result.admin.role,
        status=result.admin.status,
    )

    content = _ok(
        "SYSTEM_INITIALIZED",
        "系统初始化成功，请登录",
        InitData(admin=admin_response),
        request,
    )
    return JSONResponse(status_code=201, content=content)


@router.post("/login")
async def login(
    request: Request,
    body: LoginRequest,
) -> JSONResponse:
    """用户登录。

    校验用户名和密码，创建短期会话。
    成功时设置 asa_session（HttpOnly）和 asa_csrf Cookie。
    """
    container = get_service_container(request.app)

    command = LoginCommand(
        username=body.username,
        password=body.password,
    )

    async with container.session_factory() as session:
        user_repo = create_user_repo(session)
        result = await container.login_handler.handle(
            command,
            user_repo=user_repo,
        )

    user_response = UserSummaryResponse(
        id=str(result.user.id),
        username=result.user.username,
        role=result.user.role,
        status=result.user.status,
    )

    content = _ok(
        "LOGIN_SUCCESS",
        "登录成功",
        LoginData(
            user=user_response,
            expires_at=result.expires_at.isoformat(),
        ),
        request,
    )

    response = JSONResponse(status_code=200, content=content)
    _set_auth_cookies(response, result.session_token, result.csrf_token)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    session_token: str = Depends(get_session_token),
) -> JSONResponse:
    """用户退出登录。

    使服务端会话失效（幂等），清除认证 Cookie。
    CSRF 校验由中间件完成。
    """
    container = get_service_container(request.app)

    command = LogoutCommand(session_token=session_token)
    await container.logout_handler.handle(command)

    content = _ok("LOGOUT_SUCCESS", "已安全退出", None, request)
    response = JSONResponse(status_code=200, content=content)
    _clear_auth_cookies(response)
    return response
