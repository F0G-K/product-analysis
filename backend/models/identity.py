from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class TenantModel(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    admin_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    max_users: Mapped[int | None] = mapped_column(Integer)
    max_projects: Mapped[int | None] = mapped_column(Integer)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(256))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="project_member")
    is_first_login: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(INET)
    auth_provider: Mapped[str] = mapped_column(String(16), nullable=False, default="local")
    sso_external_id: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
