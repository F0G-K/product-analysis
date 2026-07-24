-- ============================================================================
-- 产品管理智能助手平台 - 数据库初始化脚本
-- 目标: PostgreSQL 16+
-- 基于: PRD V1.2 + 概要设计总纲 + 数据库设计文档
-- ============================================================================

-- 0. 初始设置
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- 文本模糊搜索

-- 应用角色（RLS 使用）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'CHANGE_ME_IN_PRODUCTION';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'platform_admin') THEN
        CREATE ROLE platform_admin WITH LOGIN PASSWORD 'CHANGE_ME_IN_PRODUCTION' BYPASSRLS;
    END IF;
END
$$;


-- ============================================================================
-- 1. 租户与用户认证模块
-- ============================================================================

-- 1.1 tenants
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(128) NOT NULL,
    slug            VARCHAR(64)  NOT NULL,
    admin_user_id   UUID,
    status          VARCHAR(16)  NOT NULL DEFAULT 'active',
    max_users       INTEGER,
    max_projects    INTEGER,
    settings        JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_tenants_slug ON tenants (slug) WHERE deleted_at IS NULL;
CREATE INDEX idx_tenants_status ON tenants (status) WHERE deleted_at IS NULL;

-- 1.2 users
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID         NOT NULL,
    email               VARCHAR(256) NOT NULL,
    password_hash       VARCHAR(256),
    name                VARCHAR(128) NOT NULL,
    avatar_url          VARCHAR(512),
    role                VARCHAR(32)  NOT NULL DEFAULT 'project_member',
    is_first_login      BOOLEAN      NOT NULL DEFAULT true,
    locked_until        TIMESTAMPTZ,
    failed_login_count  INTEGER      NOT NULL DEFAULT 0,
    password_changed_at TIMESTAMPTZ,
    last_login_at       TIMESTAMPTZ,
    last_login_ip       INET,
    auth_provider       VARCHAR(16)  NOT NULL DEFAULT 'local',
    sso_external_id     VARCHAR(256),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_users_tenant_email ON users (tenant_id, email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_sso_external ON users (tenant_id, sso_external_id) WHERE sso_external_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_users_locked ON users (locked_until) WHERE locked_until IS NOT NULL AND deleted_at IS NULL;

-- 1.3 user_sessions
CREATE TABLE user_sessions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID         NOT NULL,
    token_hash        VARCHAR(128) NOT NULL,
    device_info       VARCHAR(256),
    ip_address        INET         NOT NULL,
    user_agent        TEXT,
    logged_in_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_active_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at        TIMESTAMPTZ  NOT NULL,
    is_active         BOOLEAN      NOT NULL DEFAULT true,
    terminated_reason VARCHAR(64),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_sessions_token ON user_sessions (token_hash);
CREATE INDEX idx_sessions_user_active ON user_sessions (user_id, is_active);
CREATE INDEX idx_sessions_expires ON user_sessions (expires_at) WHERE is_active = true;

-- 1.4 mfa_configs
CREATE TABLE mfa_configs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID         NOT NULL,
    totp_secret_encrypted VARCHAR(512) NOT NULL,
    is_enabled            BOOLEAN      NOT NULL DEFAULT false,
    bound_at              TIMESTAMPTZ,
    last_used_at          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_mfa_user ON mfa_configs (user_id);

-- 1.5 mfa_recovery_codes
CREATE TABLE mfa_recovery_codes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mfa_config_id UUID        NOT NULL,
    code_hash     VARCHAR(128) NOT NULL,
    is_used       BOOLEAN     NOT NULL DEFAULT false,
    used_at       TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_recovery_codes_mfa ON mfa_recovery_codes (mfa_config_id, is_used);

-- 1.6 sso_configs
CREATE TABLE sso_configs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             UUID NOT NULL,
    protocol              VARCHAR(16)  NOT NULL,
    idp_metadata_url      VARCHAR(512),
    idp_metadata_xml      TEXT,
    idp_entity_id         VARCHAR(512),
    idp_sso_url           VARCHAR(512),
    idp_certificate       TEXT,
    sp_entity_id          VARCHAR(512),
    sp_acs_url            VARCHAR(512),
    attribute_mapping     JSONB        NOT NULL DEFAULT '{}',
    allowed_email_domains TEXT[],
    jit_provisioning      BOOLEAN      NOT NULL DEFAULT false,
    is_enabled            BOOLEAN      NOT NULL DEFAULT false,
    last_tested_at        TIMESTAMPTZ,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_sso_tenant ON sso_configs (tenant_id);

-- 1.7 password_reset_tokens
CREATE TABLE password_reset_tokens (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID         NOT NULL,
    token_hash VARCHAR(128) NOT NULL,
    expires_at TIMESTAMPTZ  NOT NULL,
    is_used    BOOLEAN      NOT NULL DEFAULT false,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_reset_tokens_user ON password_reset_tokens (user_id, is_used);
CREATE INDEX idx_reset_tokens_hash ON password_reset_tokens (token_hash);

-- 1.8 invitations
CREATE TABLE invitations (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL,
    inviter_id         UUID         NOT NULL,
    email              VARCHAR(256) NOT NULL,
    token_hash         VARCHAR(128) NOT NULL,
    expires_at         TIMESTAMPTZ  NOT NULL,
    is_activated       BOOLEAN      NOT NULL DEFAULT false,
    activated_user_id  UUID,
    activated_at       TIMESTAMPTZ,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_invitations_tenant ON invitations (tenant_id, email);
CREATE INDEX idx_invitations_token ON invitations (token_hash);

-- 1.9 login_audit_logs（按月分区）
CREATE TABLE login_audit_logs (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL,
    user_id            UUID,
    email              VARCHAR(256),
    operation          VARCHAR(32)  NOT NULL,
    result             VARCHAR(16)  NOT NULL,
    failure_reason     VARCHAR(128),
    ip_address         INET         NOT NULL,
    user_agent         TEXT,
    device_fingerprint VARCHAR(128),
    metadata           JSONB        NOT NULL DEFAULT '{}',
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_login_audit_tenant_time ON login_audit_logs (tenant_id, created_at DESC);
CREATE INDEX idx_login_audit_user ON login_audit_logs (user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_login_audit_ip ON login_audit_logs (ip_address);


-- ============================================================================
-- 2. 项目与数据源管理模块
-- ============================================================================

-- 2.1 projects
CREATE TABLE projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID         NOT NULL,
    name        VARCHAR(128) NOT NULL,
    description TEXT,
    status      VARCHAR(16)  NOT NULL DEFAULT 'active',
    timezone    VARCHAR(64)  NOT NULL DEFAULT 'Asia/Shanghai',
    settings    JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

CREATE INDEX idx_projects_tenant ON projects (tenant_id, status) WHERE deleted_at IS NULL;

-- 2.2 project_members
CREATE TABLE project_members (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID        NOT NULL,
    user_id    UUID        NOT NULL,
    role       VARCHAR(32) NOT NULL DEFAULT 'project_member',
    joined_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_project_user UNIQUE (project_id, user_id)
);

CREATE INDEX idx_members_project ON project_members (project_id, role);
CREATE INDEX idx_members_user ON project_members (user_id);

-- 2.3 data_sources
CREATE TABLE data_sources (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID         NOT NULL,
    project_id        UUID         NOT NULL,
    name              VARCHAR(128) NOT NULL,
    source_type       VARCHAR(32)  NOT NULL,
    connection_config JSONB        NOT NULL,
    sync_interval     INTEGER      DEFAULT 3600,
    status            VARCHAR(16)  NOT NULL DEFAULT 'disconnected',
    last_sync_at      TIMESTAMPTZ,
    last_sync_status  VARCHAR(16),
    error_message     TEXT,
    created_by        UUID         NOT NULL,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ
);

CREATE INDEX idx_sources_project ON data_sources (project_id, source_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_sources_tenant ON data_sources (tenant_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_sources_config ON data_sources USING GIN (connection_config);

-- 2.4 sync_records（按月分区）
CREATE TABLE sync_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source_id  UUID        NOT NULL,
    sync_type       VARCHAR(16) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    sync_scope      JSONB,
    result          VARCHAR(16) NOT NULL,
    failure_reason  TEXT,
    items_added     INTEGER     NOT NULL DEFAULT 0,
    items_updated   INTEGER     NOT NULL DEFAULT 0,
    items_deleted   INTEGER     NOT NULL DEFAULT 0,
    items_failed    INTEGER     NOT NULL DEFAULT 0,
    error_details   JSONB,
    triggered_by    UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_sync_records_source ON sync_records (data_source_id, started_at DESC);
CREATE INDEX idx_sync_records_tenant_time ON sync_records (tenant_id, started_at DESC);


-- ============================================================================
-- 3. 需求池与评估模型模块
-- ============================================================================

-- 3.1 requirements
CREATE TABLE requirements (
    id                           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                    UUID         NOT NULL,
    project_id                   UUID         NOT NULL,
    external_id                  VARCHAR(128),
    name                         VARCHAR(256) NOT NULL,
    background                   TEXT,
    target_users                 TEXT,
    core_scenarios               TEXT,
    user_coverage_description    TEXT,
    business_value_description   TEXT,
    strategic_alignment          TEXT,
    estimated_man_days           NUMERIC(10,1),
    estimated_duration_days      INTEGER,
    technical_complexity         VARCHAR(16),
    dependencies                 TEXT,
    business_risks               TEXT,
    technical_risks              TEXT,
    compliance_risks             TEXT,
    delivery_risks               TEXT,
    proposer_id                  UUID,
    assignee_id                  UUID,
    expected_launch_date         DATE,
    status                       VARCHAR(32) NOT NULL DEFAULT 'draft',
    current_priority             VARCHAR(4),
    current_total_score          NUMERIC(5,1),
    latest_assessment_task_id    UUID,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                   TIMESTAMPTZ
);

CREATE INDEX idx_requirements_project ON requirements (project_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_requirements_tenant ON requirements (tenant_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_requirements_priority ON requirements (project_id, current_priority) WHERE deleted_at IS NULL;
CREATE INDEX idx_requirements_assignee ON requirements (assignee_id) WHERE deleted_at IS NULL;

-- 3.2 assessment_models
CREATE TABLE assessment_models (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             UUID         NOT NULL,
    project_id            UUID         NOT NULL,
    name                  VARCHAR(128) NOT NULL,
    version               INTEGER      NOT NULL DEFAULT 1,
    total_score_formula   TEXT         NOT NULL,
    priority_thresholds   JSONB        NOT NULL,
    status                VARCHAR(16)  NOT NULL DEFAULT 'draft',
    effective_from        TIMESTAMPTZ,
    effective_to          TIMESTAMPTZ,
    created_by            UUID         NOT NULL,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_models_project_status ON assessment_models (project_id, status);

-- 3.3 assessment_dimensions
CREATE TABLE assessment_dimensions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id          UUID         NOT NULL,
    name              VARCHAR(64)  NOT NULL,
    weight            NUMERIC(4,3) NOT NULL CHECK (weight >= 0.100 AND weight <= 0.400),
    scoring_direction VARCHAR(8)   NOT NULL DEFAULT 'positive',
    sort_order        INTEGER      NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_dimensions_model ON assessment_dimensions (model_id, sort_order);

-- 3.4 assessment_scoring_anchors
CREATE TABLE assessment_scoring_anchors (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dimension_id UUID        NOT NULL,
    score        INTEGER     NOT NULL CHECK (score BETWEEN 1 AND 5),
    description  TEXT        NOT NULL,
    criteria     TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_anchor_dimension_score UNIQUE (dimension_id, score)
);

-- 3.5 assessment_tasks（继承 tasks，task_id 外键后添加）
CREATE TABLE assessment_tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id             UUID         NOT NULL,
    requirement_id      UUID         NOT NULL,
    model_id            UUID         NOT NULL,
    total_score         NUMERIC(5,1),
    suggested_priority  VARCHAR(4),
    has_risk_flag       BOOLEAN      NOT NULL DEFAULT false,
    risk_flag_detail    TEXT,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT uq_assess_task UNIQUE (task_id)
);

CREATE INDEX idx_assess_tasks_requirement ON assessment_tasks (requirement_id, created_at DESC);

-- 3.6 assessment_dimension_scores
CREATE TABLE assessment_dimension_scores (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_task_id    UUID         NOT NULL,
    dimension_id          UUID         NOT NULL,
    raw_score             INTEGER      NOT NULL CHECK (raw_score BETWEEN 1 AND 5),
    converted_score       NUMERIC(5,1) NOT NULL,
    evidence_citations    TEXT,
    inference_explanation TEXT,
    missing_evidence      TEXT,
    confidence            VARCHAR(8)   NOT NULL DEFAULT 'medium',
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_dim_scores_task ON assessment_dimension_scores (assessment_task_id, dimension_id);

-- 3.7 assessment_sensitivity_results
CREATE TABLE assessment_sensitivity_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_task_id  UUID         NOT NULL,
    adjusted_weights    JSONB        NOT NULL,
    adjusted_total_score NUMERIC(5,1) NOT NULL,
    priority_changed    BOOLEAN      NOT NULL DEFAULT false,
    original_priority   VARCHAR(4),
    new_priority        VARCHAR(4),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_sensitivity_task ON assessment_sensitivity_results (assessment_task_id);

-- 3.8 assessment_confirmations
CREATE TABLE assessment_confirmations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_task_id  UUID        NOT NULL,
    confirmed_by        UUID        NOT NULL,
    confirmation_type   VARCHAR(16) NOT NULL,
    adjustments         JSONB,
    adjustment_reason   TEXT,
    needs_review        BOOLEAN     NOT NULL DEFAULT false,
    reviewer_id         UUID,
    review_status       VARCHAR(16),
    review_comment      TEXT,
    reviewed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assess_confirms_task ON assessment_confirmations (assessment_task_id, created_at DESC);
CREATE INDEX idx_assess_confirms_review ON assessment_confirmations (reviewer_id, review_status) WHERE needs_review = true;


-- ============================================================================
-- 4. 交付物一致性检查模块
-- ============================================================================

-- 4.1 deliverables
CREATE TABLE deliverables (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID         NOT NULL,
    project_id        UUID         NOT NULL,
    requirement_id    UUID,
    deliverable_type  VARCHAR(32)  NOT NULL,
    name              VARCHAR(256) NOT NULL,
    source_system     VARCHAR(64),
    source_version    VARCHAR(64),
    file_path         VARCHAR(1024),
    content_summary   TEXT,
    is_primary_version BOOLEAN     NOT NULL DEFAULT false,
    sync_record_id    UUID,
    vector_store_ref  VARCHAR(256),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ
);

CREATE INDEX idx_deliverables_project_type ON deliverables (project_id, deliverable_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_deliverables_requirement ON deliverables (requirement_id, deliverable_type) WHERE deleted_at IS NULL;

-- 4.2 check_baselines
CREATE TABLE check_baselines (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID         NOT NULL,
    project_id           UUID         NOT NULL,
    requirement_id       UUID,
    baseline_number      VARCHAR(32)  NOT NULL,
    check_scope          VARCHAR(32)  NOT NULL DEFAULT 'full',
    previous_baseline_id UUID,
    status               VARCHAR(16)  NOT NULL DEFAULT 'active',
    created_by           UUID         NOT NULL,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_baselines_project ON check_baselines (project_id, created_at DESC);
CREATE INDEX idx_baselines_requirement ON check_baselines (requirement_id, status);
CREATE UNIQUE INDEX idx_baselines_number ON check_baselines (project_id, baseline_number);

-- 4.3 baseline_deliverables
CREATE TABLE baseline_deliverables (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    baseline_id      UUID         NOT NULL,
    deliverable_id   UUID         NOT NULL,
    snapshot_version INTEGER      NOT NULL DEFAULT 1,
    snapshot_path    VARCHAR(1024),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT uq_baseline_deliverable UNIQUE (baseline_id, deliverable_id)
);

-- 4.4 check_rules
CREATE TABLE check_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID         NOT NULL,
    project_id      UUID,
    dimension       VARCHAR(32)  NOT NULL,
    name            VARCHAR(256) NOT NULL,
    description     TEXT,
    judgment_logic  TEXT         NOT NULL,
    suggested_level VARCHAR(16)  NOT NULL DEFAULT 'general',
    is_enabled      BOOLEAN      NOT NULL DEFAULT true,
    priority        INTEGER      NOT NULL DEFAULT 0,
    created_by      UUID         NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_rules_project_dim ON check_rules (project_id, dimension, is_enabled) WHERE deleted_at IS NULL;
CREATE INDEX idx_rules_global ON check_rules (tenant_id, dimension, is_enabled) WHERE project_id IS NULL AND deleted_at IS NULL;

-- 4.5 check_tasks（继承 tasks，task_id 外键后添加）
CREATE TABLE check_tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID        NOT NULL,
    baseline_id     UUID        NOT NULL,
    total_issues    INTEGER     NOT NULL DEFAULT 0,
    blocker_count   INTEGER     NOT NULL DEFAULT 0,
    critical_count  INTEGER     NOT NULL DEFAULT 0,
    general_count   INTEGER     NOT NULL DEFAULT 0,
    info_count      INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_check_task UNIQUE (task_id)
);

CREATE INDEX idx_check_tasks_baseline ON check_tasks (baseline_id, created_at DESC);

-- 4.6 check_issues
CREATE TABLE check_issues (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_task_id         UUID         NOT NULL,
    rule_id               UUID,
    dimension             VARCHAR(32)  NOT NULL,
    title                 VARCHAR(512) NOT NULL,
    level                 VARCHAR(16)  NOT NULL,
    adjusted_level        VARCHAR(16),
    level_adjust_reason   TEXT,
    confidence            VARCHAR(8)   NOT NULL DEFAULT 'medium',
    involved_deliverables JSONB        NOT NULL,
    conflict_comparison   TEXT,
    potential_impact      TEXT,
    suggested_fix         TEXT,
    recommended_role      VARCHAR(32),
    status                VARCHAR(16)  NOT NULL DEFAULT 'pending',
    assigned_to           UUID,
    planned_fix_date      DATE,
    closed_at             TIMESTAMPTZ,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_issues_task ON check_issues (check_task_id, dimension, status);
CREATE INDEX idx_issues_status ON check_issues (status, assigned_to);
CREATE INDEX idx_issues_level ON check_issues (check_task_id, level);
CREATE INDEX idx_issues_deliverables ON check_issues USING GIN (involved_deliverables);

-- 4.7 issue_assignments
CREATE TABLE issue_assignments (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id               UUID        NOT NULL,
    assignee_id            UUID        NOT NULL,
    operation              VARCHAR(16) NOT NULL,
    fix_description        TEXT,
    new_material_version   VARCHAR(64),
    new_material_path      VARCHAR(1024),
    waiver_reason          TEXT,
    waiver_valid_until     DATE,
    waiver_approvals       JSONB,
    false_positive_reason  TEXT,
    operator_id            UUID        NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assignments_issue ON issue_assignments (issue_id, created_at DESC);

-- 4.8 issue_rechecks
CREATE TABLE issue_rechecks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id            UUID        NOT NULL,
    recheck_baseline_id UUID        NOT NULL,
    recheck_result      VARCHAR(16) NOT NULL,
    recheck_detail      TEXT,
    rechecked_by        UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rechecks_issue ON issue_rechecks (issue_id, created_at DESC);


-- ============================================================================
-- 5. 上线问题归因模块
-- ============================================================================

-- 5.1 release_versions
CREATE TABLE release_versions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    project_id              UUID         NOT NULL,
    version_number          VARCHAR(32)  NOT NULL,
    release_date            DATE,
    associated_requirements JSONB        NOT NULL DEFAULT '[]',
    status                  VARCHAR(16)  NOT NULL DEFAULT 'planned',
    release_notes           TEXT,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at              TIMESTAMPTZ
);

CREATE INDEX idx_releases_project ON release_versions (project_id, release_date DESC) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX idx_releases_number ON release_versions (project_id, version_number) WHERE deleted_at IS NULL;
CREATE INDEX idx_releases_requirements ON release_versions USING GIN (associated_requirements);

-- 5.2 attribution_tasks（继承 tasks，task_id 外键后添加）
CREATE TABLE attribution_tasks (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id                  UUID         NOT NULL,
    release_version_id       UUID         NOT NULL,
    anomaly_name             VARCHAR(256) NOT NULL,
    anomaly_window_start     TIMESTAMPTZ  NOT NULL,
    anomaly_window_end       TIMESTAMPTZ,
    impact_scope             TEXT,
    user_impact              TEXT,
    current_handling_status  VARCHAR(32)  NOT NULL DEFAULT 'investigating',
    associated_alerts        JSONB        NOT NULL DEFAULT '[]',
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT uq_attrib_task UNIQUE (task_id)
);

CREATE INDEX idx_attrib_tasks_version ON attribution_tasks (release_version_id, created_at DESC);

-- 5.3 timeline_events
CREATE TABLE timeline_events (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attribution_task_id  UUID         NOT NULL,
    event_source         VARCHAR(32)  NOT NULL,
    original_timestamp   TIMESTAMPTZ  NOT NULL,
    project_timestamp    TIMESTAMPTZ  NOT NULL,
    summary              TEXT         NOT NULL,
    source_url           VARCHAR(1024),
    related_object_type  VARCHAR(32),
    related_object_id    VARCHAR(128),
    event_data           JSONB        NOT NULL DEFAULT '{}',
    credibility          VARCHAR(16)  NOT NULL DEFAULT 'confirmed',
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_timeline_task ON timeline_events (attribution_task_id, project_timestamp);
CREATE INDEX idx_timeline_source ON timeline_events (event_source, project_timestamp);
CREATE INDEX idx_timeline_object ON timeline_events (related_object_type, related_object_id);
CREATE INDEX idx_timeline_data ON timeline_events USING GIN (event_data);

-- 5.4 attribution_results
CREATE TABLE attribution_results (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attribution_task_id    UUID        NOT NULL,
    category               VARCHAR(32) NOT NULL,
    is_primary             BOOLEAN     NOT NULL DEFAULT false,
    confidence             VARCHAR(8)  NOT NULL DEFAULT 'medium',
    supporting_evidence    JSONB       NOT NULL DEFAULT '[]',
    counter_evidence       JSONB       NOT NULL DEFAULT '[]',
    missing_evidence       JSONB       NOT NULL DEFAULT '[]',
    reasoning_chain        TEXT,
    short_term_mitigation  TEXT,
    long_term_improvement  TEXT,
    suggested_owner_role   VARCHAR(32),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_attrib_results_task ON attribution_results (attribution_task_id, is_primary);
CREATE INDEX idx_attrib_results_category ON attribution_results (attribution_task_id, category);
CREATE INDEX idx_attrib_results_support ON attribution_results USING GIN (supporting_evidence);
CREATE INDEX idx_attrib_results_counter ON attribution_results USING GIN (counter_evidence);

-- 5.5 attribution_confirmations
CREATE TABLE attribution_confirmations (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attribution_task_id  UUID        NOT NULL,
    confirmed_by         UUID        NOT NULL,
    operation            VARCHAR(16) NOT NULL,
    confirmed_category   VARCHAR(32),
    revise_reason        TEXT,
    dispute_explanation  TEXT,
    dispute_resolved     BOOLEAN,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_attrib_confirms_task ON attribution_confirmations (attribution_task_id, created_at DESC);


-- ============================================================================
-- 6. 公共模块 — 通用任务表（必须先于子任务表创建）
-- ============================================================================

-- 6.0 tasks — 通用任务主表
-- 注：虽然建表顺序靠后，但 assessment_tasks / check_tasks / attribution_tasks 的
--     task_id 外键约束在 7.1 节统一添加，所以顺序不影响 DDL 执行。
CREATE TABLE tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID         NOT NULL,
    project_id          UUID         NOT NULL,
    task_type           VARCHAR(32)  NOT NULL,
    status              VARCHAR(32)  NOT NULL DEFAULT 'draft',
    title               VARCHAR(256) NOT NULL,
    description         TEXT,
    input_snapshot_id   UUID,
    model_name          VARCHAR(64),
    model_version       VARCHAR(64),
    prompt_version      VARCHAR(40),
    temperature         NUMERIC(3,2) DEFAULT 0.3,
    created_by          UUID         NOT NULL,
    confirmed_by        UUID,
    confirmed_at        TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    failure_reason      TEXT,
    retry_count         INTEGER      NOT NULL DEFAULT 0,
    retry_of_task_id    UUID,
    error_details       JSONB,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_tenant_type_status ON tasks (tenant_id, task_type, status);
CREATE INDEX idx_tasks_project ON tasks (project_id, created_at DESC);
CREATE INDEX idx_tasks_creator ON tasks (created_by, status);
CREATE INDEX idx_tasks_status_created ON tasks (status, created_at DESC);

-- 6.1 snapshots
CREATE TABLE snapshots (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                       UUID         NOT NULL,
    task_type                       VARCHAR(32)  NOT NULL,
    task_id                         UUID         NOT NULL,
    snapshot_data                   JSONB        NOT NULL,
    snapshot_storage_path           VARCHAR(1024),
    associated_deliverable_versions JSONB        NOT NULL DEFAULT '[]',
    snapshot_at                     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_at                      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_snapshots_task ON snapshots (task_type, task_id);
CREATE INDEX idx_snapshots_tenant_time ON snapshots (tenant_id, snapshot_at DESC);
CREATE INDEX idx_snapshots_data ON snapshots USING GIN (snapshot_data);

-- 6.2 evidence_items
CREATE TABLE evidence_items (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             UUID         NOT NULL,
    task_type             VARCHAR(32)  NOT NULL,
    task_id               UUID         NOT NULL,
    evidence_type         VARCHAR(16)  NOT NULL,
    citation_location     VARCHAR(512),
    content_summary       TEXT,
    related_conclusion_id VARCHAR(64),
    excerpt_text          TEXT,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_evidence_task ON evidence_items (task_type, task_id, evidence_type);
CREATE INDEX idx_evidence_conclusion ON evidence_items (related_conclusion_id);

-- 6.3 model_governance_records（按月分区）
CREATE TABLE model_governance_records (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID         NOT NULL,
    task_type               VARCHAR(32)  NOT NULL,
    task_id                 UUID         NOT NULL,
    call_phase              VARCHAR(32)  NOT NULL,
    model_name              VARCHAR(64)  NOT NULL,
    model_version           VARCHAR(64)  NOT NULL,
    prompt_template_version VARCHAR(40)  NOT NULL,
    prompt_template_name    VARCHAR(128),
    temperature             NUMERIC(3,2) NOT NULL DEFAULT 0.3,
    max_tokens              INTEGER      NOT NULL DEFAULT 4096,
    prompt_tokens           INTEGER,
    completion_tokens       INTEGER,
    total_tokens            INTEGER,
    latency_ms              INTEGER,
    request_id              VARCHAR(128),
    is_cached               BOOLEAN      NOT NULL DEFAULT false,
    error_info              JSONB,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_gov_task ON model_governance_records (task_type, task_id, call_phase);
CREATE INDEX idx_gov_model_time ON model_governance_records (model_name, created_at DESC);
CREATE UNIQUE INDEX idx_gov_request ON model_governance_records (request_id);

-- 6.4 audit_logs（按月分区）
CREATE TABLE audit_logs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      UUID         NOT NULL,
    operator_id    UUID,
    operation      VARCHAR(64)  NOT NULL,
    object_type    VARCHAR(32)  NOT NULL,
    object_id      UUID,
    changes_before JSONB,
    changes_after  JSONB,
    source_ip      INET,
    user_agent     TEXT,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_audit_tenant_time ON audit_logs (tenant_id, created_at DESC);
CREATE INDEX idx_audit_object ON audit_logs (object_type, object_id);
CREATE INDEX idx_audit_operator ON audit_logs (operator_id, created_at DESC) WHERE operator_id IS NOT NULL;
CREATE INDEX idx_audit_operation ON audit_logs (operation, created_at DESC);

-- 6.5 notifications（按月分区）
CREATE TABLE notifications (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL,
    recipient_id       UUID         NOT NULL,
    notification_type  VARCHAR(32)  NOT NULL,
    title              VARCHAR(256) NOT NULL,
    content            TEXT,
    is_read            BOOLEAN      NOT NULL DEFAULT false,
    read_at            TIMESTAMPTZ,
    channel            VARCHAR(16)  NOT NULL DEFAULT 'in_app',
    related_task_type  VARCHAR(32),
    related_task_id    UUID,
    sent_at            TIMESTAMPTZ,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_notifications_recipient ON notifications (recipient_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_tenant_type ON notifications (tenant_id, notification_type, created_at DESC);

-- 6.6 exports
CREATE TABLE exports (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID         NOT NULL,
    task_type        VARCHAR(32)  NOT NULL,
    task_id          UUID         NOT NULL,
    export_format    VARCHAR(16)  NOT NULL,
    file_path        VARCHAR(1024) NOT NULL,
    file_size_bytes  BIGINT,
    exported_by      UUID         NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_exports_task ON exports (task_type, task_id, created_at DESC);
CREATE INDEX idx_exports_user ON exports (exported_by, created_at DESC);


-- ============================================================================
-- 7. 外键约束（统一添加，解除建表顺序依赖）
-- ============================================================================

-- 7.1 租户与用户认证
ALTER TABLE tenants ADD CONSTRAINT fk_tenants_admin FOREIGN KEY (admin_user_id) REFERENCES users(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE users ADD CONSTRAINT fk_users_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

ALTER TABLE user_sessions ADD CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE mfa_configs ADD CONSTRAINT fk_mfa_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE mfa_recovery_codes ADD CONSTRAINT fk_recovery_codes_mfa FOREIGN KEY (mfa_config_id) REFERENCES mfa_configs(id) ON DELETE CASCADE;

ALTER TABLE sso_configs ADD CONSTRAINT fk_sso_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

ALTER TABLE password_reset_tokens ADD CONSTRAINT fk_reset_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE invitations ADD CONSTRAINT fk_invitations_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE invitations ADD CONSTRAINT fk_invitations_inviter FOREIGN KEY (inviter_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE invitations ADD CONSTRAINT fk_invitations_activated_user FOREIGN KEY (activated_user_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE login_audit_logs ADD CONSTRAINT fk_login_audit_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE login_audit_logs ADD CONSTRAINT fk_login_audit_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- 7.2 项目与数据源
ALTER TABLE projects ADD CONSTRAINT fk_projects_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;

ALTER TABLE project_members ADD CONSTRAINT fk_members_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE project_members ADD CONSTRAINT fk_members_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE data_sources ADD CONSTRAINT fk_sources_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE data_sources ADD CONSTRAINT fk_sources_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE data_sources ADD CONSTRAINT fk_sources_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE sync_records ADD CONSTRAINT fk_sync_records_source FOREIGN KEY (data_source_id) REFERENCES data_sources(id) ON DELETE CASCADE;
ALTER TABLE sync_records ADD CONSTRAINT fk_sync_records_trigger FOREIGN KEY (triggered_by) REFERENCES users(id) ON DELETE SET NULL;

-- 7.3 需求与评估
ALTER TABLE requirements ADD CONSTRAINT fk_requirements_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE requirements ADD CONSTRAINT fk_requirements_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT;
ALTER TABLE requirements ADD CONSTRAINT fk_requirements_proposer FOREIGN KEY (proposer_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE requirements ADD CONSTRAINT fk_requirements_assignee FOREIGN KEY (assignee_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE assessment_models ADD CONSTRAINT fk_models_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE assessment_models ADD CONSTRAINT fk_models_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT;
ALTER TABLE assessment_models ADD CONSTRAINT fk_models_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE assessment_dimensions ADD CONSTRAINT fk_dimensions_model FOREIGN KEY (model_id) REFERENCES assessment_models(id) ON DELETE CASCADE;

ALTER TABLE assessment_scoring_anchors ADD CONSTRAINT fk_anchors_dimension FOREIGN KEY (dimension_id) REFERENCES assessment_dimensions(id) ON DELETE CASCADE;

-- 7.4 一致性检查
ALTER TABLE deliverables ADD CONSTRAINT fk_deliverables_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE deliverables ADD CONSTRAINT fk_deliverables_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT;
ALTER TABLE deliverables ADD CONSTRAINT fk_deliverables_requirement FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE SET NULL;
ALTER TABLE deliverables ADD CONSTRAINT fk_deliverables_sync FOREIGN KEY (sync_record_id) REFERENCES sync_records(id) ON DELETE SET NULL;

ALTER TABLE check_baselines ADD CONSTRAINT fk_baselines_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE check_baselines ADD CONSTRAINT fk_baselines_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT;
ALTER TABLE check_baselines ADD CONSTRAINT fk_baselines_requirement FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE SET NULL;
ALTER TABLE check_baselines ADD CONSTRAINT fk_baselines_previous FOREIGN KEY (previous_baseline_id) REFERENCES check_baselines(id) ON DELETE SET NULL;
ALTER TABLE check_baselines ADD CONSTRAINT fk_baselines_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE baseline_deliverables ADD CONSTRAINT fk_bl_deliverables_baseline FOREIGN KEY (baseline_id) REFERENCES check_baselines(id) ON DELETE CASCADE;
ALTER TABLE baseline_deliverables ADD CONSTRAINT fk_bl_deliverables_deliverable FOREIGN KEY (deliverable_id) REFERENCES deliverables(id) ON DELETE RESTRICT;

ALTER TABLE check_rules ADD CONSTRAINT fk_rules_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE check_rules ADD CONSTRAINT fk_rules_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE check_rules ADD CONSTRAINT fk_rules_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;

-- 7.5 归因模块
ALTER TABLE release_versions ADD CONSTRAINT fk_releases_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE release_versions ADD CONSTRAINT fk_releases_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT;

-- 7.6 公共模块 — 核心任务关联
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_confirmer FOREIGN KEY (confirmed_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_retry_of FOREIGN KEY (retry_of_task_id) REFERENCES tasks(id) ON DELETE SET NULL;

-- 任务子类型 → tasks
ALTER TABLE assessment_tasks ADD CONSTRAINT fk_assess_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
ALTER TABLE assessment_tasks ADD CONSTRAINT fk_assess_requirement FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE RESTRICT;
ALTER TABLE assessment_tasks ADD CONSTRAINT fk_assess_model FOREIGN KEY (model_id) REFERENCES assessment_models(id) ON DELETE RESTRICT;

ALTER TABLE check_tasks ADD CONSTRAINT fk_check_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
ALTER TABLE check_tasks ADD CONSTRAINT fk_check_baseline FOREIGN KEY (baseline_id) REFERENCES check_baselines(id) ON DELETE RESTRICT;

ALTER TABLE attribution_tasks ADD CONSTRAINT fk_attrib_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE;
ALTER TABLE attribution_tasks ADD CONSTRAINT fk_attrib_version FOREIGN KEY (release_version_id) REFERENCES release_versions(id) ON DELETE RESTRICT;

-- 评估明细
ALTER TABLE assessment_dimension_scores ADD CONSTRAINT fk_dim_scores_task FOREIGN KEY (assessment_task_id) REFERENCES assessment_tasks(id) ON DELETE CASCADE;
ALTER TABLE assessment_dimension_scores ADD CONSTRAINT fk_dim_scores_dimension FOREIGN KEY (dimension_id) REFERENCES assessment_dimensions(id) ON DELETE RESTRICT;

ALTER TABLE assessment_sensitivity_results ADD CONSTRAINT fk_sensitivity_task FOREIGN KEY (assessment_task_id) REFERENCES assessment_tasks(id) ON DELETE CASCADE;

ALTER TABLE assessment_confirmations ADD CONSTRAINT fk_assess_confirms_task FOREIGN KEY (assessment_task_id) REFERENCES assessment_tasks(id) ON DELETE CASCADE;
ALTER TABLE assessment_confirmations ADD CONSTRAINT fk_assess_confirms_user FOREIGN KEY (confirmed_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE assessment_confirmations ADD CONSTRAINT fk_assess_confirms_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL;

-- 检查问题
ALTER TABLE check_issues ADD CONSTRAINT fk_issues_task FOREIGN KEY (check_task_id) REFERENCES check_tasks(id) ON DELETE RESTRICT;
ALTER TABLE check_issues ADD CONSTRAINT fk_issues_rule FOREIGN KEY (rule_id) REFERENCES check_rules(id) ON DELETE SET NULL;
ALTER TABLE check_issues ADD CONSTRAINT fk_issues_assignee FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE issue_assignments ADD CONSTRAINT fk_assignments_issue FOREIGN KEY (issue_id) REFERENCES check_issues(id) ON DELETE CASCADE;
ALTER TABLE issue_assignments ADD CONSTRAINT fk_assignments_assignee FOREIGN KEY (assignee_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE issue_assignments ADD CONSTRAINT fk_assignments_operator FOREIGN KEY (operator_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE issue_rechecks ADD CONSTRAINT fk_rechecks_issue FOREIGN KEY (issue_id) REFERENCES check_issues(id) ON DELETE CASCADE;
ALTER TABLE issue_rechecks ADD CONSTRAINT fk_rechecks_baseline FOREIGN KEY (recheck_baseline_id) REFERENCES check_baselines(id) ON DELETE RESTRICT;
ALTER TABLE issue_rechecks ADD CONSTRAINT fk_rechecks_user FOREIGN KEY (rechecked_by) REFERENCES users(id) ON DELETE SET NULL;

-- 归因明细
ALTER TABLE timeline_events ADD CONSTRAINT fk_timeline_task FOREIGN KEY (attribution_task_id) REFERENCES attribution_tasks(id) ON DELETE CASCADE;

ALTER TABLE attribution_results ADD CONSTRAINT fk_attrib_results_task FOREIGN KEY (attribution_task_id) REFERENCES attribution_tasks(id) ON DELETE CASCADE;

ALTER TABLE attribution_confirmations ADD CONSTRAINT fk_attrib_confirms_task FOREIGN KEY (attribution_task_id) REFERENCES attribution_tasks(id) ON DELETE CASCADE;
ALTER TABLE attribution_confirmations ADD CONSTRAINT fk_attrib_confirms_user FOREIGN KEY (confirmed_by) REFERENCES users(id) ON DELETE SET NULL;

-- 公共模块
ALTER TABLE snapshots ADD CONSTRAINT fk_snapshots_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE snapshots ADD CONSTRAINT fk_snapshots_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT;

ALTER TABLE evidence_items ADD CONSTRAINT fk_evidence_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE evidence_items ADD CONSTRAINT fk_evidence_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT;

ALTER TABLE model_governance_records ADD CONSTRAINT fk_gov_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE model_governance_records ADD CONSTRAINT fk_gov_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT;

ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_operator FOREIGN KEY (operator_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE notifications ADD CONSTRAINT fk_notifications_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE notifications ADD CONSTRAINT fk_notifications_recipient FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE exports ADD CONSTRAINT fk_exports_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT;
ALTER TABLE exports ADD CONSTRAINT fk_exports_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE RESTRICT;
ALTER TABLE exports ADD CONSTRAINT fk_exports_user FOREIGN KEY (exported_by) REFERENCES users(id) ON DELETE SET NULL;


-- ============================================================================
-- 8. 触发器
-- ============================================================================

-- 8.1 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有含 updated_at 的业务表创建触发器
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT table_name FROM information_schema.columns
        WHERE column_name = 'updated_at'
          AND table_schema = 'public'
          AND table_name NOT IN ('login_audit_logs', 'audit_logs')  -- 不可修改的表
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',
            tbl, tbl
        );
    END LOOP;
END
$$;

-- 8.2 任务状态流转约束
CREATE OR REPLACE FUNCTION validate_task_status_transition()
RETURNS TRIGGER AS $$
BEGIN
    -- 终态不可变更
    IF OLD.status IN ('completed', 'cancelled') THEN
        RAISE EXCEPTION 'Cannot change terminal status ''%''', OLD.status;
    END IF;

    -- 已完成的任务不可回退
    IF OLD.status = 'completed' AND NEW.status <> 'completed' THEN
        RAISE EXCEPTION 'Cannot revert a completed task from % to %', OLD.status, NEW.status;
    END IF;

    -- 已取消的任务不可恢复
    IF OLD.status = 'cancelled' AND NEW.status <> 'cancelled' THEN
        RAISE EXCEPTION 'Cannot revert a cancelled task';
    END IF;

    -- 失败的任务只能重试
    IF OLD.status = 'failed' AND NEW.status NOT IN ('draft', 'validating', 'failed') THEN
        RAISE EXCEPTION 'Failed task can only retry, not transition to %', NEW.status;
    END IF;

    -- 每个起点的合法目标
    CASE OLD.status
        WHEN 'draft' THEN
            IF NEW.status NOT IN ('draft', 'validating', 'cancelled') THEN
                RAISE EXCEPTION 'Invalid transition from draft to %', NEW.status;
            END IF;
        WHEN 'validating' THEN
            IF NEW.status NOT IN ('analyzing', 'failed', 'cancelled') THEN
                RAISE EXCEPTION 'Invalid transition from validating to %', NEW.status;
            END IF;
        WHEN 'analyzing' THEN
            IF NEW.status NOT IN ('pending_review', 'failed', 'cancelled') THEN
                RAISE EXCEPTION 'Invalid transition from analyzing to %', NEW.status;
            END IF;
        WHEN 'pending_review' THEN
            IF NEW.status NOT IN ('completed', 'analyzing', 'cancelled', 'pending_review') THEN
                RAISE EXCEPTION 'Invalid transition from pending_review to %', NEW.status;
            END IF;
        WHEN 'failed' THEN
            -- handled above
            NULL;
        ELSE
            RAISE EXCEPTION 'Unknown status: %', OLD.status;
    END CASE;

    -- 重试时自增 retry_count
    IF OLD.status = 'failed' AND NEW.status = 'draft' THEN
        NEW.retry_count = COALESCE(OLD.retry_count, 0) + 1;
    END IF;

    -- 进入分析中时要求 input_snapshot_id
    IF NEW.status = 'analyzing' AND NEW.input_snapshot_id IS NULL THEN
        RAISE EXCEPTION 'Cannot start analysis without input_snapshot_id';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_task_status_transition
    BEFORE UPDATE OF status ON tasks
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION validate_task_status_transition();

-- 8.3 基线不可变性
CREATE OR REPLACE FUNCTION prevent_baseline_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.baseline_number <> NEW.baseline_number
       OR OLD.check_scope <> NEW.check_scope
       OR OLD.project_id <> NEW.project_id THEN
        RAISE EXCEPTION 'Baseline % is immutable (number, scope, project cannot change)', OLD.baseline_number;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_baseline_immutable
    BEFORE UPDATE ON check_baselines
    FOR EACH ROW
    EXECUTE FUNCTION prevent_baseline_modification();

-- 8.4 并发会话数限制
CREATE OR REPLACE FUNCTION enforce_concurrent_session_limit()
RETURNS TRIGGER AS $$
DECLARE
    active_count INTEGER;
    oldest_id    UUID;
BEGIN
    SELECT COUNT(*) INTO active_count
    FROM user_sessions
    WHERE user_id = NEW.user_id AND is_active = true;

    IF active_count >= 3 THEN
        SELECT id INTO oldest_id
        FROM user_sessions
        WHERE user_id = NEW.user_id AND is_active = true
        ORDER BY logged_in_at ASC
        LIMIT 1;

        UPDATE user_sessions
        SET is_active = false,
            terminated_reason = 'concurrent_limit',
            updated_at = now()
        WHERE id = oldest_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_concurrent_session_limit
    BEFORE INSERT ON user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION enforce_concurrent_session_limit();


-- ============================================================================
-- 9. Row-Level Security（租户数据隔离）
-- ============================================================================

-- 9.1 租户上下文设置函数
CREATE OR REPLACE FUNCTION set_tenant_context(tenant_id UUID)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_tenant_id', tenant_id::TEXT, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 9.2 为所有含 tenant_id 的业务表启用 RLS
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT table_name FROM information_schema.columns
        WHERE column_name = 'tenant_id'
          AND table_schema = 'public'
          AND table_name NOT IN ('login_audit_logs', 'audit_logs')  -- 审计表由独立策略控制
    LOOP
        -- 启用 RLS
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);

        -- 创建租户隔离策略
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I FOR ALL TO app_user USING (tenant_id = current_setting(''app.current_tenant_id'')::UUID)',
            tbl
        );
    END LOOP;
END
$$;

-- 9.3 审计日志特殊策略（只读，不可修改/删除）
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE login_audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_read_by_tenant ON audit_logs FOR SELECT TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

CREATE POLICY login_audit_read_by_tenant ON login_audit_logs FOR SELECT TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- app_user 角色不允许 INSERT/UPDATE/DELETE 审计日志（应用层通过 platform_admin 写入）


-- ============================================================================
-- 10. 每月分区自动创建（示例 — 生产环境由 cron/scheduler 调用）
-- ============================================================================

CREATE OR REPLACE FUNCTION create_monthly_partitions(
    target_table TEXT,
    months_ahead INTEGER DEFAULT 3
)
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
BEGIN
    FOR i IN 0..(months_ahead - 1) LOOP
        partition_date := date_trunc('month', now()) + (i || ' months')::INTERVAL;
        partition_name := target_table || '_' || to_char(partition_date, 'YYYY_MM');
        start_date := to_char(partition_date, 'YYYY-MM-DD');
        end_date := to_char(partition_date + INTERVAL '1 month', 'YYYY-MM-DD');

        -- 仅在分区不存在时创建
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
            partition_name, target_table, start_date, end_date
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 初始化 4 个月的分区（当月 + 未来 3 个月）
SELECT create_monthly_partitions('login_audit_logs', 4);
SELECT create_monthly_partitions('sync_records', 4);
SELECT create_monthly_partitions('model_governance_records', 4);
SELECT create_monthly_partitions('audit_logs', 4);
SELECT create_monthly_partitions('notifications', 4);


-- ============================================================================
-- 11. 默认数据
-- ============================================================================

-- 11.1 默认评估模型维度
-- 通过应用层初始化更灵活，此处提供参考 INSERT 语句
/*
INSERT INTO assessment_dimensions (model_id, name, weight, scoring_direction, sort_order) VALUES
    ('<model-uuid>', '用户覆盖',   0.200, 'positive', 1),
    ('<model-uuid>', '业务价值',   0.300, 'positive', 2),
    ('<model-uuid>', '战略匹配度', 0.200, 'positive', 3),
    ('<model-uuid>', '实现成本',   0.150, 'negative', 4),
    ('<model-uuid>', '风险',       0.150, 'negative', 5);
*/

-- 11.2 默认优先级阈值
-- 存储在 assessment_models.priority_thresholds JSONB 中
-- '{"P0":80, "P1":65, "P2":50, "P3":0}'


-- ============================================================================
-- 初始化完成
-- ============================================================================
