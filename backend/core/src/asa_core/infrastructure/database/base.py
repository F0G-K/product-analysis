"""SQLAlchemy 基础配置和异步会话工厂。

提供 DeclarativeBase 基类、异步引擎和会话工厂，
所有 ORM Model 和 Repository 通过此模块访问数据库。
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# 命名约定：确保 Alembic 自动迁移能正确命名约束
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s__%(column_0_name)s",
    "ck": "ck_%(table_name)s__%(constraint_name)s",
    "fk": "fk_%(table_name)s__%(column_0_name)s__%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """SQLAlchemy DeclarativeBase，所有 ORM Model 的基类。"""

    metadata = MetaData(naming_convention=convention)


# 数据库 URL 从环境变量读取，默认连接本地开发 PostgreSQL
DATABASE_URL: str = os.getenv(
    "ASA_DATABASE_URL",
    "postgresql+asyncpg://root:kkkcm520@127.0.0.1:5433/asa_system",
)

# 异步引擎（echo=False 生产环境；开发调试可设置 ASA_DB_ECHO=true）
_echo: bool = os.getenv("ASA_DB_ECHO", "").lower() == "true"
async_engine = create_async_engine(DATABASE_URL, echo=_echo, pool_size=10, max_overflow=20)

# 异步会话工厂
async_session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供异步数据库会话。

    使用方式：
        @router.get("/example")
        async def example(session: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
