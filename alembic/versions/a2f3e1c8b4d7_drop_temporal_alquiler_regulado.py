"""drop temporal and alquiler_regulado from filters

Revision ID: a2f3e1c8b4d7
Revises: ed5916ce4755
Create Date: 2026-05-24 17:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = 'a2f3e1c8b4d7'
down_revision: str | None = 'ed5916ce4755'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('filters') as batch_op:
        batch_op.drop_column('temporal')
        batch_op.drop_column('alquiler_regulado')


def downgrade() -> None:
    import sqlalchemy as sa
    with op.batch_alter_table('filters') as batch_op:
        batch_op.add_column(sa.Column('temporal', sa.String(length=10), nullable=False, server_default='any'))
        batch_op.add_column(sa.Column('alquiler_regulado', sa.String(length=10), nullable=False, server_default='any'))
