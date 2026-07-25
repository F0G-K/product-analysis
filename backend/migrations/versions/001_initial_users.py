"""初始迁移：创建 users 表及触发器。

Revision ID: 001
Revises: None
Create Date: 2026-07-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 users 表和 set_updated_at 触发器。"""

    # 启用 pgcrypto 扩展（用于 gen_random_uuid()）
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # --- 创建 set_updated_at 触发器函数 ---
    op.execute("""
        CREATE FUNCTION set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at := CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$;
    """)

    # --- 创建 users 表 ---
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True),
                  primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # --- 唯一约束 ---
    op.create_unique_constraint("uq_users__username", "users", ["username"])

    # --- CHECK 约束 ---
    op.create_check_constraint(
        "ck_users__username_normalized",
        "users",
        sa.text(
            "username = lower(btrim(username)) "
            "AND char_length(username) BETWEEN 3 AND 64 "
            "AND username !~ '[[:space:]]'"
        ),
    )
    op.create_check_constraint(
        "ck_users__password_hash_nonempty",
        "users",
        sa.text("char_length(btrim(password_hash)) >= 20"),
    )
    op.create_check_constraint(
        "ck_users__role",
        "users",
        sa.text("role IN ('user', 'admin')"),
    )
    op.create_check_constraint(
        "ck_users__status",
        "users",
        sa.text("status IN ('active', 'disabled')"),
    )

    # --- set_updated_at 触发器 ---
    op.execute("""
        CREATE TRIGGER trg_users__set_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    # --- 表注释 ---
    op.execute("COMMENT ON TABLE users IS '系统用户及管理员账户'")
    op.execute("COMMENT ON COLUMN users.id IS '用户 UUID'")
    op.execute("COMMENT ON COLUMN users.username IS '规范化为小写的登录名'")
    op.execute("COMMENT ON COLUMN users.password_hash IS 'Argon2id 密码哈希'")
    op.execute("COMMENT ON COLUMN users.role IS '角色：user 或 admin'")
    op.execute("COMMENT ON COLUMN users.status IS '账户状态：active 或 disabled'")
    op.execute("COMMENT ON COLUMN users.created_at IS '创建时间，UTC'")
    op.execute("COMMENT ON COLUMN users.updated_at IS '更新时间，UTC'")
    op.execute("COMMENT ON FUNCTION set_updated_at() IS '统一维护业务表 updated_at'")


def downgrade() -> None:
    """删除 users 表。"""
    op.drop_table("users")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at() CASCADE")
