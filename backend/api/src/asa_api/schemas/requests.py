"""API 请求 Schema。

定义所有 API 端点的请求体 Pydantic 模型。
所有请求模型默认拒绝未知字段（extra="forbid"）。
"""

from pydantic import BaseModel, ConfigDict, Field


class InitRequest(BaseModel):
    """初始化管理员请求体。

    对应 POST /api/v1/system/init 的请求体。
    """

    model_config = ConfigDict(extra="forbid")

    username: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="管理员登录名，1-64 字符",
        examples=["security_admin"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="管理员密码",
        examples=["Sas-Admin-2026!"],
    )


class LoginRequest(BaseModel):
    """用户登录请求体。

    对应 POST /api/v1/system/login 的请求体。
    """

    model_config = ConfigDict(extra="forbid")

    username: str = Field(
        ...,
        min_length=1,
        description="登录名",
        examples=["security_admin"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="登录密码",
        examples=["Sas-Admin-2026!"],
    )


# ============================================================
# 账号管理相关请求 Schema
# ============================================================


class CreateUserRequest(BaseModel):
    """管理员创建用户请求体。

    对应 POST /api/v1/users 的请求体。
    """

    model_config = ConfigDict(extra="forbid")

    username: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="登录名，1-64 字符，不可与已有用户重复",
        examples=["analyst_zhang"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="初始密码，8-128 字符",
        examples=["Secure-Pass-2026!"],
    )
    role: str = Field(
        ...,
        pattern=r"^(user|admin)$",
        description="角色：user 或 admin",
        examples=["user"],
    )


class UpdateUserRequest(BaseModel):
    """管理员更新用户请求体。

    对应 PUT /api/v1/users/{user_id} 的请求体。
    role 和 status 至少提供一个。
    """

    model_config = ConfigDict(extra="forbid")

    role: str | None = Field(
        default=None,
        pattern=r"^(user|admin)$",
        description="新角色：user 或 admin",
    )
    status: str | None = Field(
        default=None,
        pattern=r"^(active|disabled)$",
        description="新状态：active 或 disabled",
    )


class ResetPasswordRequest(BaseModel):
    """管理员重置用户密码请求体。

    对应 POST /api/v1/users/{user_id}/reset-password 的请求体。
    """

    model_config = ConfigDict(extra="forbid")

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新密码，8-128 字符",
        examples=["New-Secure-Pass-2026!"],
    )


class ChangeOwnPasswordRequest(BaseModel):
    """用户修改自己密码请求体。

    对应 PUT /api/v1/users/me/password 的请求体。
    必须提供旧密码进行身份再确认。
    """

    model_config = ConfigDict(extra="forbid")

    old_password: str = Field(
        ...,
        min_length=1,
        description="当前密码",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="新密码，8-128 字符，不能与旧密码相同",
        examples=["New-Secure-Pass-2026!"],
    )
