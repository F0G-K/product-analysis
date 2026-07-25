"""Alembic 迁移环境配置。

同时支持同步（psycopg，DDL 迁移）和异步（asyncpg，运行时访问）两种引擎。
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from asa_core.infrastructure.database.base import Base

# Alembic Config 对象
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 所有模型的 MetaData
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """以离线模式运行迁移（生成 SQL 脚本）。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """在已有连接上执行迁移。"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """以异步方式运行在线迁移。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """以在线模式运行迁移（直接操作数据库）。"""
    # 处理 async 方言配置：将 async 协议替换为 sync 协议以便 Alembic 使用
    url = config.get_main_option("sqlalchemy.url")
    # 使用同步 psycopg 驱动进行 DDL 操作（Alembic 内部是同步的）
    from sqlalchemy import create_engine, engine_from_config

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
