from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from redis.asyncio import Redis

from backend.api.tasks import router as tasks_router
from backend.core.celery_app import celery_app
from backend.core.database import create_database
from backend.core.errors import AppError
from backend.core.settings import get_settings
from backend.infrastructure.celery_queue import CeleryTaskQueue
from backend.infrastructure.redis_adapters import (
    RedisAnalysisInputStore,
    RedisEventPublisher,
)
from backend.middleware.errors import (
    app_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from backend.middleware.request_context import RequestIDMiddleware
from backend.repositories.task_repository import SQLAlchemyTaskRepositoryFactory
from backend.scheduling.service import TaskSchedulerService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine, session_factory = create_database(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.task_scheduler_service = TaskSchedulerService(
        SQLAlchemyTaskRepositoryFactory(session_factory),
        CeleryTaskQueue(celery_app),
        RedisEventPublisher(redis),
        RedisAnalysisInputStore(redis),
    )
    try:
        yield
    finally:
        await redis.aclose()
        await engine.dispose()


def create_app(*, actor_resolver: Any | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    @app.get("/health", tags=["系统"])
    async def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    if actor_resolver is not None:
        app.state.task_actor_resolver = actor_resolver
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
    app.include_router(tasks_router, prefix="/api/v1")
    return app


app = create_app()


def main() -> None:
    """本地开发启动入口：python -m backend.main。"""
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=get_settings().environment == "development",
    )


if __name__ == "__main__":
    main()
