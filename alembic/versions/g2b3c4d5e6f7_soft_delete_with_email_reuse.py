"""soft_delete_with_email_reuse

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g2b3c4d5e6f7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop existing unique indexes
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')

    # Step 2: Create partial unique index on email (only active users)
    # This allows deleted users' emails to be reused
    op.execute("""
        CREATE UNIQUE INDEX ix_users_email_active
        ON users (email)
        WHERE is_active = true
    """)

    # Step 3: Create regular (non-unique) indexes for query performance
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=False)

    # Step 4: Add deleted_at column for audit trail
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove deleted_at column
    op.drop_column('users', 'deleted_at')

    # Drop partial unique index
    op.drop_index('ix_users_email_active', table_name='users')

    # Drop regular indexes
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')

    # Recreate original unique indexes
    # WARNING: This will fail if there are duplicate emails/usernames among inactive users
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
