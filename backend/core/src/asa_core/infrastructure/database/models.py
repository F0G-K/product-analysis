"""ORM Model 定义。"""

import uuid
from datetime import datetime
from typing import Any

from asa_core.infrastructure.database.base import Base
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column


class UserModel(Base):
    """users 表的 ORM 映射。

    字段与 docs/4_开发规范/数据库/init.sql 中 users 表定义严格一致。
    """

    __tablename__ = "users"

    # --- 主键 ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="用户 UUID",
    )

    # --- 核心字段 ---
    username: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="规范化为小写的登录名",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Argon2id 密码哈希",
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="角色：user 或 admin",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        server_default="active",
        nullable=False,
        comment="账户状态：active 或 disabled",
    )

    # --- 审计时间 ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间，UTC",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="更新时间，UTC",
    )

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, username={self.username!r}, role={self.role})>"


class ProjectModel(Base):
    """projects 表 ORM 映射。"""

    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(project_name)) BETWEEN 1 AND 128",
            name="project_name_nonempty",
        ),
        CheckConstraint(
            "source_type IN ('local', 'repository')",
            name="source_type",
        ),
        CheckConstraint(
            "char_length(btrim(source_path)) > 0",
            name="source_path_nonempty",
        ),
        CheckConstraint(
            "source_type <> 'local' OR (source_path !~ '^/' AND source_path !~ '(^|/)\\.\\.(/|$)')",
            name="local_source_path",
        ),
        CheckConstraint(
            "source_type <> 'repository' OR "
            "source_path !~ "
            "'^[a-zA-Z][a-zA-Z0-9+.-]*://[^/@[:space:]]+:[^/@[:space:]]+@'",
            name="repository_has_no_inline_password",
        ),
        CheckConstraint(
            "char_length(btrim(task_content)) > 0",
            name="task_content_nonempty",
        ),
        CheckConstraint(
            "environment_type ~ '^[a-z][a-z0-9_-]{0,63}$'",
            name="environment_type",
        ),
        CheckConstraint(
            "project_status IN ('created', 'running', 'completed', 'failed', 'stopped')",
            name="project_status",
        ),
        Index(
            "ix_projects__created_by_created_at",
            "created_by",
            text("created_at DESC"),
        ),
        Index(
            "ix_projects__project_status_updated_at",
            "project_status",
            text("updated_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    task_content: Mapped[str] = mapped_column(Text, nullable=False)
    environment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    project_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'created'"),
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_projects__created_by__users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    stop_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ProjectRuntimeModel(Base):
    """project_runtimes 表 ORM 映射。"""

    __tablename__ = "project_runtimes"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_runtimes__project_id"),
        UniqueConstraint("id", "project_id", name="uq_project_runtimes__id_project_id"),
        CheckConstraint(
            "container_status IN ('pending', 'starting', 'running', 'stopping', 'stopped', 'destroyed', 'failed')",
            name="container_status",
        ),
        CheckConstraint(
            "runtime_identifier IS NULL OR char_length(btrim(runtime_identifier)) > 0",
            name="runtime_identifier_nonempty",
        ),
        CheckConstraint(
            "workspace_key IS NULL OR "
            "(char_length(btrim(workspace_key)) > 0 AND workspace_key !~ '^/' "
            "AND workspace_key !~ '(^|/)\\.\\.(/|$)')",
            name="workspace_key_safe",
        ),
        CheckConstraint(
            "repository_key IS NULL OR "
            "(char_length(btrim(repository_key)) > 0 AND repository_key !~ '^/' "
            "AND repository_key !~ '(^|/)\\.\\.(/|$)')",
            name="repository_key_safe",
        ),
        CheckConstraint(
            "jsonb_typeof(environment_snapshot) = 'object'",
            name="environment_snapshot_object",
        ),
        CheckConstraint(
            "(stopped_at IS NULL OR started_at IS NULL OR stopped_at >= started_at) "
            "AND (destroyed_at IS NULL OR stopped_at IS NULL OR destroyed_at >= stopped_at)",
            name="time_order",
        ),
        CheckConstraint(
            "container_status <> 'failed' OR error_message IS NOT NULL",
            name="failed_error",
        ),
        Index(
            "uq_project_runtimes__runtime_identifier",
            "runtime_identifier",
            unique=True,
            postgresql_where=text("runtime_identifier IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            name="fk_project_runtimes__project_id__projects",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    runtime_identifier: Mapped[str | None] = mapped_column(String(128))
    container_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'pending'"),
    )
    workspace_key: Mapped[str | None] = mapped_column(Text)
    repository_key: Mapped[str | None] = mapped_column(Text)
    environment_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    destroyed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class RuntimeStageModel(Base):
    """runtime_stages 表 ORM 映射。"""

    __tablename__ = "runtime_stages"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "project_id",
            name="uq_runtime_stages__id_project_id",
        ),
        UniqueConstraint(
            "runtime_id",
            "stage_name",
            name="uq_runtime_stages__runtime_id_stage_name",
        ),
        UniqueConstraint(
            "runtime_id",
            "stage_order",
            name="uq_runtime_stages__runtime_id_stage_order",
        ),
        ForeignKeyConstraint(
            ["runtime_id", "project_id"],
            ["project_runtimes.id", "project_runtimes.project_id"],
            name="fk_runtime_stages__runtime_scope__project_runtimes",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "(stage_name = 'environment_scan' AND stage_order = 1) OR "
            "(stage_name = 'code_analysis' AND stage_order = 2) OR "
            "(stage_name = 'vulnerability_verify' AND stage_order = 3) OR "
            "(stage_name = 'report_generate' AND stage_order = 4) OR "
            "(stage_name = 'done' AND stage_order = 5)",
            name="stage_name_order",
        ),
        CheckConstraint(
            "stage_status IN ('idle', 'running', 'success', 'failed')",
            name="stage_status",
        ),
        CheckConstraint(
            "(stage_status = 'idle' AND started_at IS NULL AND finished_at IS NULL) OR "
            "(stage_status = 'running' AND started_at IS NOT NULL AND finished_at IS NULL) OR "
            "(stage_status IN ('success', 'failed') AND started_at IS NOT NULL "
            "AND finished_at IS NOT NULL AND finished_at >= started_at)",
            name="status_times",
        ),
        CheckConstraint(
            "stage_status <> 'failed' OR error_message IS NOT NULL",
            name="failed_error",
        ),
        Index(
            "ix_runtime_stages__project_id_stage_order",
            "project_id",
            "stage_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            name="fk_runtime_stages__project_id__projects",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    runtime_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    stage_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'idle'"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class WorkerTaskModel(Base):
    """worker_tasks 表 ORM 映射。"""

    __tablename__ = "worker_tasks"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_worker_tasks__id_project_id"),
        UniqueConstraint(
            "id",
            "project_id",
            "stage_id",
            name="uq_worker_tasks__id_project_id_stage_id",
        ),
        ForeignKeyConstraint(
            ["stage_id", "project_id"],
            ["runtime_stages.id", "runtime_stages.project_id"],
            name="fk_worker_tasks__stage_scope__runtime_stages",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "worker_role IN "
            "('general', 'environment_inspector', 'code_analyst', "
            "'vulnerability_verifier', 'report_editor', 'operations_assistant')",
            name="worker_role",
        ),
        CheckConstraint(
            "task_status IN ('idle', 'running', 'success', 'failed')",
            name="task_status",
        ),
        CheckConstraint(
            "char_length(btrim(task_content)) > 0",
            name="task_content_nonempty",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count"),
        CheckConstraint(
            "idempotency_key IS NULL OR char_length(btrim(idempotency_key)) > 0",
            name="idempotency_key_nonempty",
        ),
        CheckConstraint(
            "(task_status = 'idle' AND started_at IS NULL AND finished_at IS NULL) OR "
            "(task_status = 'running' AND started_at IS NOT NULL AND finished_at IS NULL) OR "
            "(task_status IN ('success', 'failed') AND started_at IS NOT NULL "
            "AND finished_at IS NOT NULL AND finished_at >= started_at)",
            name="status_times",
        ),
        CheckConstraint(
            "task_status <> 'failed' OR char_length(btrim(error_message)) > 0",
            name="failed_error",
        ),
        Index(
            "ix_worker_tasks__project_id_created_at",
            "project_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_worker_tasks__stage_id_task_status",
            "stage_id",
            "task_status",
        ),
        Index(
            "uq_worker_tasks__project_id_idempotency_key",
            "project_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            name="fk_worker_tasks__project_id__projects",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    worker_role: Mapped[str] = mapped_column(String(64), nullable=False)
    task_content: Mapped[str] = mapped_column(Text, nullable=False)
    task_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'idle'"),
    )
    result_summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SystemConfigModel(Base):
    """项目模块读取的生效系统配置。"""

    __tablename__ = "system_configs"
    __table_args__ = (
        UniqueConstraint("version", name="uq_system_configs__version"),
        CheckConstraint("version > 0", name="version"),
        CheckConstraint(
            "default_timeout_seconds IS NULL OR default_timeout_seconds > 0",
            name="default_timeout_seconds",
        ),
        CheckConstraint(
            "max_concurrent_projects IS NULL OR max_concurrent_projects > 0",
            name="max_concurrent_projects",
        ),
        CheckConstraint(
            "log_retention_days IS NULL OR log_retention_days > 0",
            name="log_retention_days",
        ),
        CheckConstraint(
            "file_retention_days IS NULL OR file_retention_days > 0",
            name="file_retention_days",
        ),
        CheckConstraint(
            "array_position(enabled_environment_types, NULL) IS NULL",
            name="environment_types_no_null",
        ),
        CheckConstraint(
            "jsonb_typeof(settings) = 'object'",
            name="settings_object",
        ),
        Index(
            "uq_system_configs__one_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    default_timeout_seconds: Mapped[int | None] = mapped_column(Integer)
    max_concurrent_projects: Mapped[int | None] = mapped_column(Integer)
    log_retention_days: Mapped[int | None] = mapped_column(Integer)
    file_retention_days: Mapped[int | None] = mapped_column(Integer)
    enabled_environment_types: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)),
        nullable=False,
        server_default=text("ARRAY[]::varchar[]"),
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    updated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_system_configs__updated_by__users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ProjectOperationModel(Base):
    """项目写操作幂等记录，保存首次受理响应。"""

    __tablename__ = "project_operations"
    __table_args__ = (
        UniqueConstraint(
            "actor_user_id",
            "idempotency_key",
            name="uq_project_operations__actor_user_id_idempotency_key",
        ),
        CheckConstraint(
            "operation IN ('start', 'stop', 'delete')",
            name="operation",
        ),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="request_fingerprint",
        ),
        CheckConstraint(
            "jsonb_typeof(response_data) = 'object'",
            name="response_data_object",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_project_operations__actor_user_id__users",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            name="fk_project_operations__project_id__projects",
            ondelete="SET NULL",
        ),
    )
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    response_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DomainEventModel(Base):
    """domain_events Outbox 表 ORM 映射。"""

    __tablename__ = "domain_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_domain_events__event_id"),
        UniqueConstraint(
            "project_id",
            "sequence",
            name="uq_domain_events__project_id_sequence",
        ),
        CheckConstraint("sequence > 0", name="sequence"),
        CheckConstraint(
            "event_type IN "
            "('project_status', 'stage_status', 'worker_status', 'chat_message', "
            "'runtime_log', 'resource_usage', 'vulnerability_found', 'report_ready')",
            name="event_type",
        ),
        CheckConstraint(
            "char_length(btrim(aggregate_type)) > 0",
            name="aggregate_type_nonempty",
        ),
        CheckConstraint(
            "char_length(btrim(aggregate_id)) > 0",
            name="aggregate_id_nonempty",
        ),
        CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="payload_object",
        ),
        CheckConstraint(
            "publish_status IN ('pending', 'published', 'failed')",
            name="publish_status",
        ),
        CheckConstraint("retry_count >= 0", name="retry_count"),
        CheckConstraint(
            "(publish_status = 'pending' AND published_at IS NULL AND last_error IS NULL) OR "
            "(publish_status = 'published' AND published_at IS NOT NULL AND last_error IS NULL) OR "
            "(publish_status = 'failed' AND published_at IS NULL AND last_error IS NOT NULL)",
            name="publish_state",
        ),
        Index(
            "ix_domain_events__relay_pending",
            "publish_status",
            "next_retry_at",
            "id",
            postgresql_where=text("publish_status IN ('pending', 'failed')"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            name="fk_domain_events__project_id__projects",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    publish_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'pending'"),
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class AuditLogModel(Base):
    """audit_logs 表 ORM 映射。"""

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "result_status IN ('success', 'failure', 'denied')",
            name="result_status",
        ),
        CheckConstraint(
            "char_length(btrim(action)) > 0",
            name="action_nonempty",
        ),
        CheckConstraint(
            "char_length(btrim(object_type)) > 0",
            name="object_type_nonempty",
        ),
        CheckConstraint(
            "object_id IS NULL OR char_length(btrim(object_id)) > 0",
            name="object_id_nonempty",
        ),
        CheckConstraint(
            "idempotency_key IS NULL OR char_length(btrim(idempotency_key)) > 0",
            name="idempotency_key_nonempty",
        ),
        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="metadata_object",
        ),
        Index("ix_audit_logs__request_id", "request_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            name="fk_audit_logs__actor_user_id__users",
            ondelete="SET NULL",
        ),
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            name="fk_audit_logs__project_id__projects",
            ondelete="SET NULL",
        ),
    )
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(128))
    result_status: Mapped[str] = mapped_column(String(16), nullable=False)
    client_ip: Mapped[str | None] = mapped_column(INET)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
