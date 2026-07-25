from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from redis.asyncio import Redis

from backend.ai.cached_llm_gateway import CachedLLMGateway
from backend.ai.evidence import ConfidenceAssessor, EvidenceLinker
from backend.ai.langgraph_workflow import LangGraphAnalysisWorkflow
from backend.ai.llm_gateway import AnthropicLLMGateway
from backend.ai.masking import SensitiveDataMasker
from backend.ai.roles import (
    ConfidenceAssessorRole,
    DocumentRetrieverRole,
    EvidenceLinkerRole,
    HumanReviewCoordinatorRole,
    InputValidatorRole,
    LLMAnalystRole,
    ResultFinalizerRole,
    RuleAnalystRole,
    SnapshotLockerRole,
)
from backend.ai.workflow import WorkflowRoles
from backend.core.database import create_database
from backend.core.settings import get_settings
from backend.domain.ports import DocumentRetriever
from backend.infrastructure.memory_adapters import (
    DeterministicRuleAnalyzer,
    NoopDocumentRetriever,
    UnavailableDocumentRetriever,
)
from backend.infrastructure.postgres_adapters import (
    PostgresGovernanceRecorder,
    PostgresResultStore,
    PostgresSnapshotStore,
    SQLAlchemyScenarioResultWriter,
    UnavailableScenarioResultWriter,
)
from backend.infrastructure.redis_adapters import (
    RedisEventPublisher,
    RedisLLMCache,
    RedisLockManager,
)
from backend.repositories.task_repository import SQLAlchemyTaskRepositoryFactory
from backend.scheduling.executor import TaskExecutor
from backend.scheduling.guard import RepositoryExecutionGuard, RepositoryProgressRecorder

DocumentRetrieverFactory = Callable[[], DocumentRetriever]
_document_retriever_factory: DocumentRetrieverFactory | None = None
ScenarioResultWriterFactory = Callable[[], SQLAlchemyScenarioResultWriter]
_scenario_result_writer_factory: ScenarioResultWriterFactory | None = None


def configure_document_retriever_factory(factory: DocumentRetrieverFactory) -> None:
    """由 RAG 模块注入真实检索器，保持调度模块不耦合具体向量库。"""
    global _document_retriever_factory
    _document_retriever_factory = factory


def configure_scenario_result_writer_factory(
    factory: ScenarioResultWriterFactory,
) -> None:
    """由评估、检查、归因模块注入各自结果表写入器。"""
    global _scenario_result_writer_factory
    _scenario_result_writer_factory = factory


def _create_retriever() -> DocumentRetriever:
    if _document_retriever_factory is not None:
        return _document_retriever_factory()
    if get_settings().environment == "development":
        return NoopDocumentRetriever()
    return UnavailableDocumentRetriever()


def _create_scenario_result_writer() -> SQLAlchemyScenarioResultWriter:
    if _scenario_result_writer_factory is not None:
        return _scenario_result_writer_factory()
    return UnavailableScenarioResultWriter()


@asynccontextmanager
async def create_executor_scope() -> AsyncIterator[TaskExecutor]:
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY 未配置，无法启动 AI 分析 Worker")

    engine, session_factory = create_database(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    repository_factory = SQLAlchemyTaskRepositoryFactory(session_factory)
    publisher = RedisEventPublisher(redis)
    gateway = AnthropicLLMGateway(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base_url,
        timeout_seconds=settings.llm_timeout_seconds,
    )

    checkpointer_context = AsyncPostgresSaver.from_conn_string(
        settings.checkpoint_database_url
    )
    try:
        async with checkpointer_context as checkpointer:
            await checkpointer.setup()
            masker = SensitiveDataMasker()
            roles = WorkflowRoles(
                validator=InputValidatorRole(),
                snapshot_locker=SnapshotLockerRole(
                    PostgresSnapshotStore(session_factory), masker
                ),
                retriever=DocumentRetrieverRole(_create_retriever(), masker),
                rule_analyst=RuleAnalystRole(DeterministicRuleAnalyzer()),
                llm_analyst=LLMAnalystRole(
                    CachedLLMGateway(gateway, RedisLLMCache(redis)),
                    PostgresGovernanceRecorder(session_factory),
                    masker,
                ),
                evidence_linker=EvidenceLinkerRole(EvidenceLinker()),
                confidence_assessor=ConfidenceAssessorRole(ConfidenceAssessor()),
                review_coordinator=HumanReviewCoordinatorRole(),
                finalizer=ResultFinalizerRole(
                    PostgresResultStore(
                        session_factory,
                        _create_scenario_result_writer(),
                    )
                ),
            )
            workflow = LangGraphAnalysisWorkflow(
                roles,
                checkpointer,
                execution_guard=RepositoryExecutionGuard(repository_factory),
                progress_recorder=RepositoryProgressRecorder(
                    repository_factory, publisher
                ),
            )
            yield TaskExecutor(
                repository_factory,
                input_store=_RedisInputStoreAdapter(redis),
                lock_manager=RedisLockManager(redis),
                publisher=publisher,
                workflow=workflow,
            )
    finally:
        await gateway.aclose()
        await redis.aclose()
        await engine.dispose()


class _RedisInputStoreAdapter:
    """延迟导入的薄包装，避免 bootstrap 暴露无关 Redis 细节。"""

    def __init__(self, redis: Redis) -> None:
        from backend.infrastructure.redis_adapters import RedisAnalysisInputStore

        self._store = RedisAnalysisInputStore(redis)

    async def get(self, task_id: UUID) -> Mapping[str, Any] | None:
        return await self._store.get(task_id)

    async def put(self, task_id: UUID, payload: Mapping[str, Any]) -> None:
        await self._store.put(task_id, payload)

    async def copy(self, source_task_id: UUID, target_task_id: UUID) -> None:
        await self._store.copy(source_task_id, target_task_id)
