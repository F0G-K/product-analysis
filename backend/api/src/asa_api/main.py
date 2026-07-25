"""FastAPI 应用入口。

创建 FastAPI 实例，挂载中间件、路由和异常处理器。
"""

from contextlib import asynccontextmanager

from asa_api.bootstrap import create_service_container
from asa_api.exception_handlers.handlers import register_exception_handlers
from asa_api.middleware.csrf import CsrfMiddleware
from asa_api.middleware.request_id import RequestIdMiddleware
from asa_api.routers.v1.auth import router as auth_router
from asa_api.routers.v1.projects import router as projects_router
from asa_api.routers.v1.scheduling import router as scheduling_router
from asa_api.routers.v1.users import router as users_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    启动：创建并注入 ServiceContainer。
    关闭：关闭 Redis 等外部连接。
    """
    # 启动
    app.state.container = await create_service_container()
    yield
    # 关闭
    container = app.state.container
    if container and container.redis:
        await container.redis.aclose()


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例的工厂函数。"""
    app = FastAPI(
        title="ASA System API",
        description="自动化安全评估系统（ASA System）REST API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- 中间件（顺序敏感：RequestID → CSRF → CORS） ---
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(CsrfMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # 前端 Vite 开发服务器
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- 异常处理器 ---
    register_exception_handlers(app)

    # --- 路由 ---
    app.include_router(auth_router, prefix="/api/v1/system")
    app.include_router(users_router, prefix="/api/v1/users")
    app.include_router(projects_router, prefix="/api/v1/projects")
    app.include_router(scheduling_router, prefix="/api/v1/projects")

    return app


# uvicorn 入口
app = create_app()
