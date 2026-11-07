"""Remove redundant refresh token indexes.

Revision ID: 20261107_0003
Revises: 20261107_0002
Create Date: 2026-11-07
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261107_0003"
down_revision: Union[str, Sequence[str], None] = "20261107_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Keep only the indexes required beyond unique constraints."""
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_jti", table_name="refresh_tokens")


def downgrade() -> None:
    """Restore non-unique lookup indexes."""
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=False)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=False)
