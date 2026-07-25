"""用户管理相关路由（账号管理模块）。

提供管理员专属的用户 CRUD 接口，以及当前用户的个人信息和密码修改。

路由前缀：/api/v1/users（由 main.py 设置）
"""

from typing import Any

from asa_api.bootstrap import create_user_repo, get_service_container
from asa_api.dependencies import CurrentUser, get_current_user
from asa_api.middleware.request_id import get_request_id
from asa_api.schemas.common import (
    ApiResponse,
    UserDetailResponse,
    UserListData,
    UserSummaryResponse,
)
from asa_api.schemas.requests import (
    ChangeOwnPasswordRequest,
    CreateUserRequest,
    ResetPasswordRequest,
    UpdateUserRequest,
)
from asa_core.application.commands.change_password import (
    ChangeOwnPasswordCommand,
    ResetPasswordCommand,
)
from asa_core.application.commands.create_user import CreateUserCommand
from asa_core.application.commands.update_user import UpdateUserCommand
from asa_core.application.queries.get_user_detail import GetUserDetailQuery
from asa_core.application.queries.get_user_list import GetUserListQuery
from asa_core.domain.auth.exceptions import AdminRequired
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["账号管理"])


# --- 工具函数 ---


def _ok(code: str, message: str, data: Any, request: Request) -> dict[str, Any]:
    """构造成功响应的 JSON 字典。"""
    return ApiResponse[Any](
        code=code,
        message=message,
        data=data,
        request_id=get_request_id(request),
    ).model_dump(mode="json")


def _require_admin(current_user: CurrentUser) -> None:
    """断言当前用户为管理员（直接检查 role，避免构造领域实体）。"""
    if not current_user.is_admin:
        raise AdminRequired()


def _user_to_detail(user) -> UserDetailResponse:
    """将领域实体转换为用户详情响应。"""
    return UserDetailResponse(
        id=str(user.id),
        username=user.username,
        role=user.role,
        status=user.status,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


def _user_to_summary(user) -> UserSummaryResponse:
    """将领域实体转换为用户摘要响应。"""
    return UserSummaryResponse(
        id=str(user.id),
        username=user.username,
        role=user.role,
        status=user.status,
    )


# --- 端点：当前用户 ---


@router.get("/me")
async def get_current_user_info(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """获取当前登录用户的信息。

    用于页面刷新后恢复用户角色和状态。
    所有已认证用户均可访问。
    """
    # 重新从数据库获取最新状态（防止会话期间状态变更）
    container = get_service_container(request.app)
    async with container.session_factory() as session:
        user_repo = create_user_repo(session)
        result = await container.get_user_detail_handler.handle(
            GetUserDetailQuery(user_id=str(current_user.id)),
            user_repo=user_repo,
        )

    content = _ok(
        "USER_DETAIL_OK",
        "查询成功",
        _user_to_detail(result.user),
        request,
    )
    return JSONResponse(status_code=200, content=content)


@router.put("/me/password")
async def change_own_password(
    request: Request,
    body: ChangeOwnPasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """当前用户修改自己的密码。

    必须提供旧密码进行身份再确认。
    新旧密码不能相同。
    """
    container = get_service_container(request.app)

    command = ChangeOwnPasswordCommand(
        old_password=body.old_password,
        new_password=body.new_password,
    )

    async with container.session_factory() as session:
        async with session.begin():
            user_repo = create_user_repo(session)
            await container.change_own_password_handler.handle(
                command,
                user_repo=user_repo,
                current_user_id=str(current_user.id),
            )

    content = _ok("PASSWORD_CHANGED", "密码修改成功", None, request)
    return JSONResponse(status_code=200, content=content)


# --- 端点：管理员用户管理 ---


@router.get("")
async def list_users(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    role: str | None = Query(default=None, pattern=r"^(user|admin)$", description="按角色筛选"),
    status: str | None = Query(default=None, pattern=r"^(active|disabled)$", description="按状态筛选"),
    keyword: str | None = Query(default=None, max_length=64, description="按用户名关键词搜索"),
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """管理员分页查询用户列表。

    支持按角色、状态筛选，以及用户名关键词模糊搜索。
    """
    _require_admin(current_user)

    container = get_service_container(request.app)

    query = GetUserListQuery(
        page=page,
        page_size=page_size,
        role=role,
        status=status,
        keyword=keyword,
    )

    async with container.session_factory() as session:
        user_repo = create_user_repo(session)
        result = await container.get_user_list_handler.handle(
            query,
            user_repo=user_repo,
        )

    content = _ok(
        "USER_LIST_OK",
        "查询成功",
        UserListData(
            items=[_user_to_detail(u) for u in result.items],
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            has_next=result.has_next,
        ),
        request,
    )
    return JSONResponse(status_code=200, content=content)


@router.post("", status_code=201)
async def create_user(
    request: Request,
    body: CreateUserRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """管理员创建新用户。

    用户名必须唯一（大小写不敏感），密码须满足 8-128 字符。
    """
    _require_admin(current_user)

    container = get_service_container(request.app)

    command = CreateUserCommand(
        username=body.username,
        password=body.password,
        role=body.role,
    )

    async with container.session_factory() as session:
        async with session.begin():
            user_repo = create_user_repo(session)
            result = await container.create_user_handler.handle(
                command,
                user_repo=user_repo,
                operator_id=str(current_user.id),
            )

    content = _ok(
        "USER_CREATED",
        "用户创建成功",
        _user_to_detail(result.user),
        request,
    )
    return JSONResponse(status_code=201, content=content)


@router.get("/{user_id}")
async def get_user(
    request: Request,
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """管理员查看用户详情。

    Args:
        user_id: 目标用户 UUID。
    """
    _require_admin(current_user)

    container = get_service_container(request.app)

    async with container.session_factory() as session:
        user_repo = create_user_repo(session)
        result = await container.get_user_detail_handler.handle(
            GetUserDetailQuery(user_id=user_id),
            user_repo=user_repo,
        )

    content = _ok(
        "USER_DETAIL_OK",
        "查询成功",
        _user_to_detail(result.user),
        request,
    )
    return JSONResponse(status_code=200, content=content)


@router.put("/{user_id}")
async def update_user(
    request: Request,
    user_id: str,
    body: UpdateUserRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """管理员更新用户角色或状态。

    不允许修改自己的角色或状态。
    role 和 status 至少提供一个非空值。

    Args:
        user_id: 目标用户 UUID。
    """
    _require_admin(current_user)

    # 至少提供一个修改字段
    if body.role is None and body.status is None:
        content = ApiResponse[Any](
            code="VALIDATION_ERROR",
            message="role 和 status 至少需要提供一个",
            data=None,
            request_id=get_request_id(request),
        ).model_dump(mode="json")
        return JSONResponse(status_code=422, content=content)

    container = get_service_container(request.app)

    command = UpdateUserCommand(
        user_id=user_id,
        role=body.role,
        status=body.status,
    )

    async with container.session_factory() as session:
        async with session.begin():
            user_repo = create_user_repo(session)
            result = await container.update_user_handler.handle(
                command,
                user_repo=user_repo,
                operator_id=str(current_user.id),
            )

    content = _ok(
        "USER_UPDATED",
        "用户信息已更新",
        _user_to_detail(result.user),
        request,
    )
    return JSONResponse(status_code=200, content=content)


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    request: Request,
    user_id: str,
    body: ResetPasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """管理员重置任意用户密码。

    无需提供旧密码，直接设置新密码。

    Args:
        user_id: 目标用户 UUID。
    """
    _require_admin(current_user)

    container = get_service_container(request.app)

    command = ResetPasswordCommand(
        user_id=user_id,
        new_password=body.new_password,
    )

    async with container.session_factory() as session:
        async with session.begin():
            user_repo = create_user_repo(session)
            result = await container.reset_password_handler.handle(
                command,
                user_repo=user_repo,
                operator_id=str(current_user.id),
            )

    content = _ok(
        "PASSWORD_RESET",
        "密码已重置",
        {"user_id": result.user_id},
        request,
    )
    return JSONResponse(status_code=200, content=content)
