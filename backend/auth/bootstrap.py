from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.auth.service import AuthenticatedUser


async def ensure_development_identity(
    session_factory: async_sessionmaker[AsyncSession],
    user: AuthenticatedUser,
) -> None:
    """为单用户开发认证准备幂等的租户和用户记录。"""
    async with session_factory() as session, session.begin():
        await session.execute(
            text(
                """
                INSERT INTO tenants (id, name, slug, status, settings)
                VALUES (:tenant_id, '本地开发租户', 'local-development', 'active', '{}')
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"tenant_id": user.tenant_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO users (
                    id, tenant_id, email, name, role, is_first_login,
                    failed_login_count, auth_provider
                )
                VALUES (
                    :user_id, :tenant_id, :email, :name, :role, false, 0, 'local'
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "user_id": user.id,
                "tenant_id": user.tenant_id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
            },
        )
        await session.execute(
            text("UPDATE tenants SET admin_user_id = :user_id WHERE id = :tenant_id"),
            {"user_id": user.id, "tenant_id": user.tenant_id},
        )
