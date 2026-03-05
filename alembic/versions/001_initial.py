"""初始建表：spider_results, spider_logs, spider_tasks, spider_quarantine

Revision ID: 001_initial
Revises: None
Create Date: 2026-02-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- spider_results: 爬虫抓取结果 ----
    op.create_table(
        "spider_results",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("spider_name", sa.String(128), nullable=False, index=True),
        sa.Column("spider_id", sa.String(64), nullable=False, index=True),
        sa.Column("trace_id", sa.String(64), index=True),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("data", sa.JSON, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            index=True,
        ),
    )

    # ---- spider_logs: 日志持久化 ----
    op.create_table(
        "spider_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("spider_name", sa.String(128), index=True),
        sa.Column("spider_id", sa.String(64), index=True),
        sa.Column("trace_id", sa.String(64), index=True),
        sa.Column("level", sa.String(16), nullable=False, index=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("module", sa.String(64)),
        sa.Column("extra", sa.JSON, server_default="{}"),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            index=True,
        ),
    )

    # ---- spider_tasks: 调度任务持久化（PG 备份） ----
    op.create_table(
        "spider_tasks",
        sa.Column("task_id", sa.String(128), primary_key=True),
        sa.Column("spider_name", sa.String(128), nullable=False, index=True),
        sa.Column("schedule_type", sa.String(16), nullable=False, server_default="cron"),
        sa.Column("schedule_expr", sa.String(64), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("spider_args", sa.JSON, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("last_run", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="idle"),
    )

    # ---- spider_quarantine: 脏数据隔离 ----
    op.create_table(
        "spider_quarantine",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("spider_name", sa.String(128), nullable=False, index=True),
        sa.Column("trace_id", sa.String(64), index=True),
        sa.Column("raw_data", sa.JSON, nullable=False),
        sa.Column("errors", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            index=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("spider_quarantine")
    op.drop_table("spider_tasks")
    op.drop_table("spider_logs")
    op.drop_table("spider_results")
