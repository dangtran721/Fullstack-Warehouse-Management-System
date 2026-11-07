"""Initialize migration history.

Revision ID: 20261107_0001
Revises:
Create Date: 2026-11-07

This baseline intentionally contains no business tables. Domain schemas are
introduced by their corresponding implementation batches.
"""

from typing import Sequence, Union


revision: str = "20261107_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Initialize Alembic revision tracking."""


def downgrade() -> None:
    """Revert Alembic revision tracking."""
