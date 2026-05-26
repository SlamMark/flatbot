"""add alert_carousels table

Revision ID: c7a4e92f1d8b
Revises: a2f3e1c8b4d7
Create Date: 2026-05-26 22:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c7a4e92f1d8b'
down_revision: str | None = 'a2f3e1c8b4d7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'alert_carousels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.String(length=50), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('filter_id', sa.Integer(), nullable=False),
        sa.Column('match_ids', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['filter_id'], ['filters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('alert_carousels')
