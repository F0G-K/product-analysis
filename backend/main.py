from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from redis.asyncio import Redis

from backend.analysis_tasks.service import AnalysisTaskCreationService
from backend.ai.llm_providers import create_default_provider_factory
from backend.api.analysis_tasks import router as analysis_tasks_router
from backend.api.auth import router as auth_router
from backend.api.chat import router as chat_router
from backend.api.projects import router as projects_router
from backend.api.tasks import router as tasks_router
from backend.api.uploads import router as uploads_router
from backend.auth.bootstrap import ensure_development_identity
from backend.auth.service import auth_service, resolve_task_actor
from backend.core.celery_app import celery_app
from backend.core.database import create_database
from backend.core.errors import AppError
from backend.core.settings import get_settings
from backend.infrastructure.celery_queue import CeleryTaskQueue
from backend.infrastructure.redis_adapters import (
    RedisAnalysisInputStore,
    RedisEventPublisher,
)
from backend.middleware.authentication import AuthenticationMiddleware
from backend.middleware.errors import (
    app_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from backend.middleware.request_context import RequestIDMiddleware
from backend.models.base import Base
from backend.models.identity import TenantModel, UserModel  # noqa: F401
from backend.models.project import ProjectMemberModel, ProjectModel  # noqa: F401
from backend.models.task import TaskModel  # noqa: F401
from backend.projects.service import ProjectService
from backend.repositories.task_repository import SQLAlchemyTaskRepositoryFactory
from backend.scheduling.service import TaskSchedulerService
from backend.services.chat_service import ChatService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine, session_factory = create_database(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    repository_factory = SQLAlchemyTaskRepositoryFactory(session_factory)
    input_store = RedisAnalysisInputStore(redis)
    project_service = ProjectService(session_factory)
    app.state.project_service = project_service
    app.state.task_scheduler_service = TaskSchedulerService(
        repository_factory,
        CeleryTaskQueue(celery_app),
        RedisEventPublisher(redis),
        input_store,
    )
    app.state.analysis_task_creation_service = AnalysisTaskCreationService(
        repository_factory,
        input_store,
        project_service,
        settings,
    )
    provider_factory = create_default_provider_factory(
        anthropic_api_key=settings.llm_api_key or "",
        anthropic_base_url=settings.llm_api_base_url,
        openai_api_key=settings.llm_openai_api_key,
        openai_base_url=settings.llm_openai_base_url,
        ollama_base_url=settings.llm_ollama_base_url,
    )
    app.state.chat_service = ChatService(
        provider_factory=provider_factory,
        default_provider=settings.llm_default_provider,
        default_model=settings.llm_default_model,
        task_repository_factory=repository_factory,
    )
    if settings.environment == "development":
        async with engine.begin() as connection:
            await connection.run_sync(
                Base.metadata.create_all,
                tables=[
                    TenantModel.__table__,
                    UserModel.__table__,
                    ProjectModel.__table__,
                    ProjectMemberModel.__table__,
                    TaskModel.__table__,
                ],
            )
        await ensure_development_identity(session_factory, auth_service.user)
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

    app.state.task_actor_resolver = actor_resolver or resolve_task_actor
    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(analysis_tasks_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(uploads_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
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
