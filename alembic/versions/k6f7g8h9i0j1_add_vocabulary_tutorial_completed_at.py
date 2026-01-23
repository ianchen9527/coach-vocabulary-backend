"""add_vocabulary_tutorial_completed_at

Revision ID: k6f7g8h9i0j1
Revises: j5e6f7g8h9i0
Create Date: 2024-01-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'k6f7g8h9i0j1'
down_revision: Union[str, None] = 'j5e6f7g8h9i0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('vocabulary_tutorial_completed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'vocabulary_tutorial_completed_at')
