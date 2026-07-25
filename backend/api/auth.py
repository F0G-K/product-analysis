from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from backend.auth.service import AuthenticatedUser, auth_service
from backend.schemas.common import APIResponse

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    remember_me: bool = False


class UserResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    name: str
    role: str
    is_first_login: bool = False
    mfa_enabled: bool = False
    auth_provider: str = "local"
    memberships: list[dict[str, str]] = []

    @classmethod
    def from_user(cls, user: AuthenticatedUser) -> UserResponse:
        return cls(
            id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=user.email,
            name=user.name,
            role=user.role,
        )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 43_200
    user: UserResponse


def _request_id(request: Request) -> str:
    return str(request.state.request_id)


@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(payload: LoginRequest, request: Request) -> APIResponse[LoginResponse]:
    token = auth_service.login(payload.username, payload.password)
    return APIResponse(
        data=LoginResponse(
            access_token=token,
            user=UserResponse.from_user(auth_service.user),
        ),
        request_id=_request_id(request),
    )


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_current_user(request: Request) -> APIResponse[UserResponse]:
    return APIResponse(
        data=UserResponse.from_user(request.state.auth_user),
        request_id=_request_id(request),
    )


@router.post("/logout", response_model=APIResponse[None])
async def logout(request: Request) -> APIResponse[None]:
    auth_service.logout(request.state.access_token)
    return APIResponse(data=None, request_id=_request_id(request))

