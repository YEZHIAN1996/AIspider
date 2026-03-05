"""添加东方财富公告表

Revision ID: 004_eastmoney_notice
Revises: 003_auth_users
Create Date: 2026-03-05

"""
from alembic import op
import sqlalchemy as sa

revision = '004_eastmoney_notice'
down_revision = '003_auth_users'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'eastmoney_notices',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('stock_code', sa.String(10), nullable=False, index=True),
        sa.Column('stock_name', sa.String(50), nullable=False),
        sa.Column('user', sa.String(50)),
        sa.Column('art_code', sa.String(50), nullable=False),
        sa.Column('notice_date', sa.String(20)),
        sa.Column('title', sa.Text()),
        sa.Column('detail_url', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('stock_code', 'art_code', name='uq_stock_art')
    )


def downgrade():
    op.drop_table('eastmoney_notices')
