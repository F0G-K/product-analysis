"""项目管理模块数据库结构。

Revision ID: 002
Revises: 001
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建项目聚合、运行资源、幂等、审计和 Outbox 表。"""

    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("project_name", sa.String(128), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("task_content", sa.Text(), nullable=False),
        sa.Column("environment_type", sa.String(64), nullable=False),
        sa.Column(
            "project_status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'created'"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                name="fk_projects__created_by__users",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("stop_requested_at", sa.DateTime(timezone=True)),
        sa.Column("last_started_at", sa.DateTime(timezone=True)),
        sa.Column("last_finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(project_name)) BETWEEN 1 AND 128",
            name="project_name_nonempty",
        ),
        sa.CheckConstraint(
            "source_type IN ('local', 'repository')",
            name="source_type",
        ),
        sa.CheckConstraint(
            "char_length(btrim(source_path)) > 0",
            name="source_path_nonempty",
        ),
        sa.CheckConstraint(
            "source_type <> 'local' OR "
            "(source_path !~ '^/' AND source_path !~ '(^|/)\\.\\.(/|$)')",
            name="local_source_path",
        ),
        sa.CheckConstraint(
            "source_type <> 'repository' OR "
            "source_path !~ "
            "'^[a-zA-Z][a-zA-Z0-9+.-]*://[^/@[:space:]]+:[^/@[:space:]]+@'",
            name="repository_has_no_inline_password",
        ),
        sa.CheckConstraint(
            "char_length(btrim(task_content)) > 0",
            name="task_content_nonempty",
        ),
        sa.CheckConstraint(
            "environment_type ~ '^[a-z][a-z0-9_-]{0,63}$'",
            name="environment_type",
        ),
        sa.CheckConstraint(
            "project_status IN ('created', 'running', 'completed', 'failed', 'stopped')",
            name="project_status",
        ),
    )
    op.create_index(
        "ix_projects__created_by_created_at",
        "projects",
        ["created_by", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_projects__project_status_updated_at",
        "projects",
        ["project_status", sa.text("updated_at DESC")],
    )
    _create_updated_at_trigger("projects")

    op.create_table(
        "project_runtimes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "projects.id",
                name="fk_project_runtimes__project_id__projects",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("runtime_identifier", sa.String(128)),
        sa.Column(
            "container_status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("workspace_key", sa.Text()),
        sa.Column("repository_key", sa.Text()),
        sa.Column(
            "environment_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.Column("destroyed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "project_id",
            name="uq_project_runtimes__project_id",
        ),
        sa.UniqueConstraint(
            "id",
            "project_id",
            name="uq_project_runtimes__id_project_id",
        ),
        sa.CheckConstraint(
            "container_status IN "
            "('pending', 'starting', 'running', 'stopping', 'stopped', 'destroyed', 'failed')",
            name="container_status",
        ),
        sa.CheckConstraint(
            "runtime_identifier IS NULL OR char_length(btrim(runtime_identifier)) > 0",
            name="runtime_identifier_nonempty",
        ),
        sa.CheckConstraint(
            "workspace_key IS NULL OR "
            "(char_length(btrim(workspace_key)) > 0 AND workspace_key !~ '^/' "
            "AND workspace_key !~ '(^|/)\\.\\.(/|$)')",
            name="workspace_key_safe",
        ),
        sa.CheckConstraint(
            "repository_key IS NULL OR "
            "(char_length(btrim(repository_key)) > 0 AND repository_key !~ '^/' "
            "AND repository_key !~ '(^|/)\\.\\.(/|$)')",
            name="repository_key_safe",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(environment_snapshot) = 'object'",
            name="environment_snapshot_object",
        ),
        sa.CheckConstraint(
            "(stopped_at IS NULL OR started_at IS NULL OR stopped_at >= started_at) "
            "AND (destroyed_at IS NULL OR stopped_at IS NULL OR destroyed_at >= stopped_at)",
            name="time_order",
        ),
        sa.CheckConstraint(
            "container_status <> 'failed' OR error_message IS NOT NULL",
            name="failed_error",
        ),
    )
    op.create_index(
        "uq_project_runtimes__runtime_identifier",
        "project_runtimes",
        ["runtime_identifier"],
        unique=True,
        postgresql_where=sa.text("runtime_identifier IS NOT NULL"),
    )
    _create_updated_at_trigger("project_runtimes")

    op.create_table(
        "runtime_stages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "projects.id",
                name="fk_runtime_stages__project_id__projects",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("runtime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_name", sa.String(64), nullable=False),
        sa.Column("stage_order", sa.SmallInteger(), nullable=False),
        sa.Column(
            "stage_status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'idle'"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "id",
            "project_id",
            name="uq_runtime_stages__id_project_id",
        ),
        sa.UniqueConstraint(
            "runtime_id",
            "stage_name",
            name="uq_runtime_stages__runtime_id_stage_name",
        ),
        sa.UniqueConstraint(
            "runtime_id",
            "stage_order",
            name="uq_runtime_stages__runtime_id_stage_order",
        ),
        sa.ForeignKeyConstraint(
            ["runtime_id", "project_id"],
            ["project_runtimes.id", "project_runtimes.project_id"],
            name="fk_runtime_stages__runtime_scope__project_runtimes",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "(stage_name = 'environment_scan' AND stage_order = 1) OR "
            "(stage_name = 'code_analysis' AND stage_order = 2) OR "
            "(stage_name = 'vulnerability_verify' AND stage_order = 3) OR "
            "(stage_name = 'report_generate' AND stage_order = 4) OR "
            "(stage_name = 'done' AND stage_order = 5)",
            name="stage_name_order",
        ),
        sa.CheckConstraint(
            "stage_status IN ('idle', 'running', 'success', 'failed')",
            name="stage_status",
        ),
        sa.CheckConstraint(
            "(stage_status = 'idle' AND started_at IS NULL AND finished_at IS NULL) OR "
            "(stage_status = 'running' AND started_at IS NOT NULL AND finished_at IS NULL) OR "
            "(stage_status IN ('success', 'failed') AND started_at IS NOT NULL "
            "AND finished_at IS NOT NULL AND finished_at >= started_at)",
            name="status_times",
        ),
        sa.CheckConstraint(
            "stage_status <> 'failed' OR error_message IS NOT NULL",
            name="failed_error",
        ),
    )
    op.create_index(
        "ix_runtime_stages__project_id_stage_order",
        "runtime_stages",
        ["project_id", "stage_order"],
    )
    _create_updated_at_trigger("runtime_stages")

    op.create_table(
        "worker_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "projects.id",
                name="fk_worker_tasks__project_id__projects",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_role", sa.String(64), nullable=False),
        sa.Column("task_content", sa.Text(), nullable=False),
        sa.Column(
            "task_status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'idle'"),
        ),
        sa.Column("result_summary", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "id",
            "project_id",
            name="uq_worker_tasks__id_project_id",
        ),
        sa.UniqueConstraint(
            "id",
            "project_id",
            "stage_id",
            name="uq_worker_tasks__id_project_id_stage_id",
        ),
        sa.ForeignKeyConstraint(
            ["stage_id", "project_id"],
            ["runtime_stages.id", "runtime_stages.project_id"],
            name="fk_worker_tasks__stage_scope__runtime_stages",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "worker_role IN "
            "('general', 'environment_inspector', 'code_analyst', "
            "'vulnerability_verifier', 'report_editor', 'operations_assistant')",
            name="worker_role",
        ),
        sa.CheckConstraint(
            "task_status IN ('idle', 'running', 'success', 'failed')",
            name="task_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(task_content)) > 0",
            name="task_content_nonempty",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="attempt_count",
        ),
        sa.CheckConstraint(
            "idempotency_key IS NULL OR char_length(btrim(idempotency_key)) > 0",
            name="idempotency_key_nonempty",
        ),
        sa.CheckConstraint(
            "(task_status = 'idle' AND started_at IS NULL AND finished_at IS NULL) OR "
            "(task_status = 'running' AND started_at IS NOT NULL AND finished_at IS NULL) OR "
            "(task_status IN ('success', 'failed') AND started_at IS NOT NULL "
            "AND finished_at IS NOT NULL AND finished_at >= started_at)",
            name="status_times",
        ),
        sa.CheckConstraint(
            "task_status <> 'failed' OR char_length(btrim(error_message)) > 0",
            name="failed_error",
        ),
    )
    op.create_index(
        "ix_worker_tasks__project_id_created_at",
        "worker_tasks",
        ["project_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_worker_tasks__stage_id_task_status",
        "worker_tasks",
        ["stage_id", "task_status"],
    )
    op.create_index(
        "uq_worker_tasks__project_id_idempotency_key",
        "worker_tasks",
        ["project_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    _create_updated_at_trigger("worker_tasks")

    op.create_table(
        "system_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("default_timeout_seconds", sa.Integer()),
        sa.Column("max_concurrent_projects", sa.Integer()),
        sa.Column("log_retention_days", sa.Integer()),
        sa.Column("file_retention_days", sa.Integer()),
        sa.Column(
            "enabled_environment_types",
            postgresql.ARRAY(sa.String(64)),
            nullable=False,
            server_default=sa.text("ARRAY[]::varchar[]"),
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                name="fk_system_configs__updated_by__users",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("version", name="uq_system_configs__version"),
        sa.CheckConstraint("version > 0", name="version"),
        sa.CheckConstraint(
            "default_timeout_seconds IS NULL OR default_timeout_seconds > 0",
            name="default_timeout_seconds",
        ),
        sa.CheckConstraint(
            "max_concurrent_projects IS NULL OR max_concurrent_projects > 0",
            name="max_concurrent_projects",
        ),
        sa.CheckConstraint(
            "log_retention_days IS NULL OR log_retention_days > 0",
            name="log_retention_days",
        ),
        sa.CheckConstraint(
            "file_retention_days IS NULL OR file_retention_days > 0",
            name="file_retention_days",
        ),
        sa.CheckConstraint(
            "array_position(enabled_environment_types, NULL) IS NULL",
            name="environment_types_no_null",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(settings) = 'object'",
            name="settings_object",
        ),
    )
    op.create_index(
        "uq_system_configs__one_active",
        "system_configs",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    _create_updated_at_trigger("system_configs")

    op.create_table(
        "project_operations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                name="fk_project_operations__actor_user_id__users",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "projects.id",
                name="fk_project_operations__project_id__projects",
                ondelete="SET NULL",
            ),
        ),
        sa.Column("operation", sa.String(16), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("response_data", postgresql.JSONB(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "actor_user_id",
            "idempotency_key",
            name="uq_project_operations__actor_user_id_idempotency_key",
        ),
        sa.CheckConstraint(
            "operation IN ('start', 'stop', 'delete')",
            name="operation",
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="request_fingerprint",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(response_data) = 'object'",
            name="response_data_object",
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                name="fk_audit_logs__actor_user_id__users",
                ondelete="SET NULL",
            ),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "projects.id",
                name="fk_audit_logs__project_id__projects",
                ondelete="SET NULL",
            ),
        ),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("object_type", sa.String(64), nullable=False),
        sa.Column("object_id", sa.String(128)),
        sa.Column("result_status", sa.String(16), nullable=False),
        sa.Column("client_ip", postgresql.INET()),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "result_status IN ('success', 'failure', 'denied')",
            name="result_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(action)) > 0",
            name="action_nonempty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(object_type)) > 0",
            name="object_type_nonempty",
        ),
        sa.CheckConstraint(
            "object_id IS NULL OR char_length(btrim(object_id)) > 0",
            name="object_id_nonempty",
        ),
        sa.CheckConstraint(
            "idempotency_key IS NULL OR char_length(btrim(idempotency_key)) > 0",
            name="idempotency_key_nonempty",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="metadata_object",
        ),
    )
    op.create_index("ix_audit_logs__request_id", "audit_logs", ["request_id"])

    op.create_table(
        "domain_events",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "projects.id",
                name="fk_domain_events__project_id__projects",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "publish_status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.UniqueConstraint("event_id", name="uq_domain_events__event_id"),
        sa.UniqueConstraint(
            "project_id",
            "sequence",
            name="uq_domain_events__project_id_sequence",
        ),
        sa.CheckConstraint("sequence > 0", name="sequence"),
        sa.CheckConstraint(
            "event_type IN "
            "('project_status', 'stage_status', 'worker_status', 'chat_message', "
            "'runtime_log', 'resource_usage', 'vulnerability_found', 'report_ready')",
            name="event_type",
        ),
        sa.CheckConstraint(
            "char_length(btrim(aggregate_type)) > 0",
            name="aggregate_type_nonempty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(aggregate_id)) > 0",
            name="aggregate_id_nonempty",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="payload_object",
        ),
        sa.CheckConstraint(
            "publish_status IN ('pending', 'published', 'failed')",
            name="publish_status",
        ),
        sa.CheckConstraint(
            "retry_count >= 0",
            name="retry_count",
        ),
        sa.CheckConstraint(
            "(publish_status = 'pending' AND published_at IS NULL AND last_error IS NULL) OR "
            "(publish_status = 'published' AND published_at IS NOT NULL AND last_error IS NULL) OR "
            "(publish_status = 'failed' AND published_at IS NULL AND last_error IS NOT NULL)",
            name="publish_state",
        ),
    )
    op.create_index(
        "ix_domain_events__relay_pending",
        "domain_events",
        ["publish_status", "next_retry_at", "id"],
        postgresql_where=sa.text("publish_status IN ('pending', 'failed')"),
    )
    op.create_index(
        "ix_domain_events__project_id_occurred_at",
        "domain_events",
        ["project_id", sa.text("occurred_at DESC")],
    )


def downgrade() -> None:
    """回滚项目管理模块结构。"""

    op.drop_table("domain_events")
    op.drop_table("audit_logs")
    op.drop_table("project_operations")
    op.execute("DROP TRIGGER IF EXISTS trg_system_configs__set_updated_at ON system_configs")
    op.drop_table("system_configs")
    op.execute("DROP TRIGGER IF EXISTS trg_worker_tasks__set_updated_at ON worker_tasks")
    op.drop_table("worker_tasks")
    op.execute("DROP TRIGGER IF EXISTS trg_runtime_stages__set_updated_at ON runtime_stages")
    op.drop_table("runtime_stages")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_project_runtimes__set_updated_at ON project_runtimes"
    )
    op.drop_table("project_runtimes")
    op.execute("DROP TRIGGER IF EXISTS trg_projects__set_updated_at ON projects")
    op.drop_table("projects")


def _create_updated_at_trigger(table_name: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table_name}__set_updated_at
        BEFORE UPDATE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )
