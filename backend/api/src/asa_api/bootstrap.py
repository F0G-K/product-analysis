"""应用启动组装（Bootstrap）。

创建并组装所有应用级依赖。
会话级依赖（UserRepository）在 router 层按请求创建。
"""

import os
from dataclasses import dataclass

from asa_api.project_dispatcher import ApiProjectTaskDispatcher
from asa_core.application.commands.change_password import (
    ChangeOwnPasswordHandler,
    ResetPasswordHandler,
)
from asa_core.application.commands.create_project import CreateProjectHandler
from asa_core.application.commands.create_user import CreateUserHandler
from asa_core.application.commands.delete_project import DeleteProjectHandler
from asa_core.application.commands.initialize_system import InitializeSystemHandler
from asa_core.application.commands.login import LoginHandler
from asa_core.application.commands.logout import LogoutHandler
from asa_core.application.commands.start_project import StartProjectHandler
from asa_core.application.commands.stop_project import StopProjectHandler
from asa_core.application.commands.update_user import UpdateUserHandler
from asa_core.application.ports.audit_logger import NoOpAuditLogger
from asa_core.application.ports.project_repository import ProjectRepository
from asa_core.application.ports.project_task_dispatcher import (
    ProjectTaskDispatcher,
)
from asa_core.application.ports.user_repository import UserRepository
from asa_core.application.queries.get_project_detail import GetProjectDetailHandler
from asa_core.application.queries.get_system_status import GetSystemStatusHandler
from asa_core.application.queries.get_user_detail import GetUserDetailHandler
from asa_core.application.queries.get_user_list import GetUserListHandler
from asa_core.application.queries.list_projects import ListProjectsHandler
from asa_core.application.queries.list_runtime_stages import ListRuntimeStagesHandler
from asa_core.application.queries.list_worker_tasks import ListWorkerTasksHandler
from asa_core.domain.auth.services import AuthenticationService
from asa_core.infrastructure.database.audit_logger import SqlAlchemyAuditLogger
from asa_core.infrastructure.database.base import async_session_factory
from asa_core.infrastructure.database.project_repository import (
    SqlAlchemyProjectRepository,
)
from asa_core.infrastructure.database.scheduling_repository import (
    SqlAlchemySchedulingRepository,
)
from asa_core.infrastructure.database.user_repository import SqlAlchemyUserRepository
from asa_core.infrastructure.security.argon2_hasher import Argon2idHasher
from asa_core.infrastructure.security.redis_session_store import RedisSessionStore
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# 会话默认有效期（秒）
_DEFAULT_SESSION_TTL: int = int(os.getenv("ASA_SESSION_TTL_SECONDS", "7200"))

# Redis URL
_REDIS_URL: str = os.getenv("ASA_REDIS_URL", "redis://root:kkkcm520@127.0.0.1:6380/0")


@dataclass
class ServiceContainer:
    """服务容器：持有所有应用级单例和工厂方法。"""

    # --- 基础设施客户端 ---
    redis: Redis
    session_factory: async_sessionmaker[AsyncSession]

    # --- 安全组件 ---
    password_hasher: Argon2idHasher
    session_store: RedisSessionStore
    audit_logger: NoOpAuditLogger

    # --- 领域服务 ---
    auth_service: AuthenticationService

    # --- 应用处理器（无会话依赖的构造函数注入） ---
    get_system_status_handler: GetSystemStatusHandler
    initialize_system_handler: InitializeSystemHandler
    login_handler: LoginHandler
    logout_handler: LogoutHandler

    # --- 账号管理处理器 ---
    create_user_handler: CreateUserHandler
    update_user_handler: UpdateUserHandler
    reset_password_handler: ResetPasswordHandler
    change_own_password_handler: ChangeOwnPasswordHandler
    get_user_list_handler: GetUserListHandler
    get_user_detail_handler: GetUserDetailHandler

    # --- 项目管理 ---
    list_projects_handler: ListProjectsHandler
    get_project_detail_handler: GetProjectDetailHandler
    project_task_dispatcher: ProjectTaskDispatcher

    # --- 调度与 AI 角色过程查询 ---
    list_runtime_stages_handler: ListRuntimeStagesHandler
    list_worker_tasks_handler: ListWorkerTasksHandler


@dataclass(frozen=True)
class ProjectCommandHandlers:
    """绑定当前数据库事务的项目写用例。"""

    create: CreateProjectHandler
    start: StartProjectHandler
    stop: StopProjectHandler
    delete: DeleteProjectHandler


async def create_service_container() -> ServiceContainer:
    """创建并组装所有应用级依赖。

    在 FastAPI 启动事件中调用一次。
    """
    # 基础设施
    redis = Redis.from_url(_REDIS_URL, decode_responses=False)

    # 安全
    password_hasher = Argon2idHasher()
    session_store = RedisSessionStore(redis, default_ttl_seconds=_DEFAULT_SESSION_TTL)
    audit_logger = NoOpAuditLogger()

    # 领域服务
    auth_service = AuthenticationService()

    # 应用处理器
    get_system_status_handler = GetSystemStatusHandler()

    initialize_system_handler = InitializeSystemHandler(
        password_hasher=password_hasher,
        audit_logger=audit_logger,
    )

    login_handler = LoginHandler(
        password_hasher=password_hasher,
        session_store=session_store,
        audit_logger=audit_logger,
        auth_service=auth_service,
    )

    logout_handler = LogoutHandler(session_store=session_store)

    # --- 账号管理处理器 ---
    create_user_handler = CreateUserHandler(
        password_hasher=password_hasher,
        audit_logger=audit_logger,
    )

    update_user_handler = UpdateUserHandler(
        audit_logger=audit_logger,
    )

    reset_password_handler = ResetPasswordHandler(
        password_hasher=password_hasher,
        audit_logger=audit_logger,
    )

    change_own_password_handler = ChangeOwnPasswordHandler(
        password_hasher=password_hasher,
        audit_logger=audit_logger,
    )

    get_user_list_handler = GetUserListHandler()
    get_user_detail_handler = GetUserDetailHandler()
    list_projects_handler = ListProjectsHandler()
    get_project_detail_handler = GetProjectDetailHandler()
    project_task_dispatcher = ApiProjectTaskDispatcher()
    list_runtime_stages_handler = ListRuntimeStagesHandler()
    list_worker_tasks_handler = ListWorkerTasksHandler()

    return ServiceContainer(
        redis=redis,
        session_factory=async_session_factory,
        password_hasher=password_hasher,
        session_store=session_store,
        audit_logger=audit_logger,
        auth_service=auth_service,
        get_system_status_handler=get_system_status_handler,
        initialize_system_handler=initialize_system_handler,
        login_handler=login_handler,
        logout_handler=logout_handler,
        create_user_handler=create_user_handler,
        update_user_handler=update_user_handler,
        reset_password_handler=reset_password_handler,
        change_own_password_handler=change_own_password_handler,
        get_user_list_handler=get_user_list_handler,
        get_user_detail_handler=get_user_detail_handler,
        list_projects_handler=list_projects_handler,
        get_project_detail_handler=get_project_detail_handler,
        project_task_dispatcher=project_task_dispatcher,
        list_runtime_stages_handler=list_runtime_stages_handler,
        list_worker_tasks_handler=list_worker_tasks_handler,
    )


def create_user_repo(session: AsyncSession) -> UserRepository:
    """为当前请求创建 UserRepository 实例。

    每个 HTTP 请求使用独立的数据库会话和仓储实例。
    """
    return SqlAlchemyUserRepository(session)


def create_project_repo(session: AsyncSession) -> ProjectRepository:
    """为当前请求创建项目仓储。"""

    return SqlAlchemyProjectRepository(session)


def create_scheduling_repo(session: AsyncSession) -> SqlAlchemySchedulingRepository:
    """为当前请求创建调度查询仓储。"""

    return SqlAlchemySchedulingRepository(session)


def create_project_command_handlers(session: AsyncSession) -> ProjectCommandHandlers:
    """创建与当前事务共享审计写入器的项目命令处理器。"""

    audit_logger = SqlAlchemyAuditLogger(session)
    return ProjectCommandHandlers(
        create=CreateProjectHandler(audit_logger),
        start=StartProjectHandler(audit_logger),
        stop=StopProjectHandler(audit_logger),
        delete=DeleteProjectHandler(audit_logger),
    )


def get_service_container(app) -> ServiceContainer:
    """从 FastAPI app.state 中获取 ServiceContainer。

    Args:
        app: FastAPI 应用实例（或 Request.app）。

    Returns:
        应用级 ServiceContainer 单例。
    """
    return app.state.container
