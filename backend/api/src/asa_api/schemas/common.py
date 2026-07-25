"""API 统一响应 Schema。

定义所有 API 端点使用的统一响应格式 ApiResponse[T]，
以及各接口的输出数据模型。
"""

import uuid
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")


class ApiResponse[DataT](BaseModel):
    """统一 API 响应格式。

    所有成功和失败响应均使用此结构。
    除文件下载和 WebSocket 外，所有端点必须返回此格式。

    Attributes:
        code: 稳定的业务码，UPPER_SNAKE_CASE 格式。
        message: 面向用户的简洁中文提示。
        data: 响应数据，无数据时为 None（JSON 中为 null）。
        request_id: 请求链路标识 UUID。
    """

    code: str = Field(..., description="稳定业务码")
    message: str = Field(..., description="面向用户的中文提示")
    data: DataT | None = Field(default=None, description="响应数据")
    request_id: uuid.UUID = Field(..., description="请求链路标识")


# --- 账号管理相关输出 Schema ---


class UserSummaryResponse(BaseModel):
    """用户摘要（符合 API 文档 3.1 UserSummary 定义）。

    用于登录、初始化、会话查询等场景返回用户信息。
    不包含 password_hash 等敏感字段。
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="用户 UUID")
    username: str = Field(..., description="登录名")
    role: str = Field(..., description="角色：user 或 admin")
    status: str = Field(..., description="账户状态：active 或 disabled")


class SystemStatusData(BaseModel):
    """系统初始化状态数据。"""

    initialized: bool = Field(..., description="系统是否已完成初始化")


class InitData(BaseModel):
    """初始化管理员接口的响应数据。"""

    admin: UserSummaryResponse = Field(..., description="新建的管理员信息")


class LoginData(BaseModel):
    """登录成功接口的响应数据。"""

    user: UserSummaryResponse = Field(..., description="当前用户信息")
    expires_at: str = Field(..., description="会话过期时间（ISO 8601 UTC）")


# --- 用户管理相关输出 Schema ---


class UserDetailResponse(BaseModel):
    """用户详情（扩展了时间信息）。

    用于管理员查看用户详情，比 UserSummary 多了时间字段。
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="用户 UUID")
    username: str = Field(..., description="登录名")
    role: str = Field(..., description="角色：user 或 admin")
    status: str = Field(..., description="账户状态：active 或 disabled")
    created_at: str = Field(..., description="创建时间（ISO 8601 UTC）")
    updated_at: str = Field(..., description="更新时间（ISO 8601 UTC）")


class UserListData(BaseModel):
    """用户列表分页数据。"""

    items: list[UserDetailResponse] = Field(default_factory=list, description="用户列表")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total: int = Field(..., description="用户总数")
    has_next: bool = Field(..., description="是否有下一页")


# --- 调度与 AI 角色模块输出 Schema ---


class RuntimeStageResponse(BaseModel):
    """项目运行阶段状态。"""

    id: str
    stage_name: str
    stage_order: int
    stage_status: str
    started_at: str | None
    finished_at: str | None
    error_message: str | None


class RuntimeStageListData(BaseModel):
    items: list[RuntimeStageResponse] = Field(default_factory=list)


class WorkerTaskResponse(BaseModel):
    """角色任务只读投影，不返回完整 Prompt 和模型原始响应。"""

    id: str
    stage_id: str
    worker_role: str
    task_content: str
    task_status: str
    result_summary: str | None
    error_message: str | None
    request_id: str
    attempt_count: int
    started_at: str | None
    finished_at: str | None
    created_at: str


class WorkerTaskListData(BaseModel):
    items: list[WorkerTaskResponse] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
    has_next: bool
