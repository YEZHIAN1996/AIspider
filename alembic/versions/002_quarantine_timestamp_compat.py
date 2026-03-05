"""兼容迁移：spider_quarantine 时间列统一为 TIMESTAMPTZ

Revision ID: 002_quarantine_timestamp_compat
Revises: 001_initial
Create Date: 2026-03-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_quarantine_timestamp_compat"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 兼容早期手动建表场景：created_at/resolved_at 可能是浮点 epoch 秒
    op.execute(
        """
        DO $$
        DECLARE
            created_t text;
            resolved_t text;
        BEGIN
            SELECT data_type
            INTO created_t
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'spider_quarantine'
              AND column_name = 'created_at';

            SELECT data_type
            INTO resolved_t
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'spider_quarantine'
              AND column_name = 'resolved_at';

            IF created_t IN ('double precision', 'real', 'numeric') THEN
                ALTER TABLE spider_quarantine
                    ALTER COLUMN created_at DROP DEFAULT,
                    ALTER COLUMN created_at TYPE TIMESTAMPTZ
                        USING to_timestamp(created_at),
                    ALTER COLUMN created_at SET DEFAULT now(),
                    ALTER COLUMN created_at SET NOT NULL;
            END IF;

            IF resolved_t IN ('double precision', 'real', 'numeric') THEN
                ALTER TABLE spider_quarantine
                    ALTER COLUMN resolved_at TYPE TIMESTAMPTZ
                        USING CASE
                            WHEN resolved_at IS NULL THEN NULL
                            ELSE to_timestamp(resolved_at)
                        END;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # 回滚为 epoch 秒（double precision）
    op.execute(
        """
        DO $$
        DECLARE
            created_t text;
            resolved_t text;
        BEGIN
            SELECT data_type
            INTO created_t
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'spider_quarantine'
              AND column_name = 'created_at';

            SELECT data_type
            INTO resolved_t
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'spider_quarantine'
              AND column_name = 'resolved_at';

            IF created_t = 'timestamp with time zone' THEN
                ALTER TABLE spider_quarantine
                    ALTER COLUMN created_at DROP DEFAULT,
                    ALTER COLUMN created_at TYPE DOUBLE PRECISION
                        USING EXTRACT(EPOCH FROM created_at),
                    ALTER COLUMN created_at SET NOT NULL;
            END IF;

            IF resolved_t = 'timestamp with time zone' THEN
                ALTER TABLE spider_quarantine
                    ALTER COLUMN resolved_at TYPE DOUBLE PRECISION
                        USING CASE
                            WHEN resolved_at IS NULL THEN NULL
                            ELSE EXTRACT(EPOCH FROM resolved_at)
                        END;
            END IF;
        END
        $$;
        """
    )
