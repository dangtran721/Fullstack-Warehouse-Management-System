"""Create warehouses and suppliers.

Revision ID: 20261107_0005
Revises: 20261107_0004
Create Date: 2026-11-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261107_0005"
down_revision: Union[str, Sequence[str], None] = "20261107_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_warehouses_code"),
    )
    op.create_index("ix_warehouses_code", "warehouses", ["code"])
    op.create_index("ix_warehouses_is_active", "warehouses", ["is_active"])
    op.create_index("ix_warehouses_name", "warehouses", ["name"])
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("contact_person", sa.String(150), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_suppliers_code"),
    )
    op.create_index("ix_suppliers_code", "suppliers", ["code"])
    op.create_index("ix_suppliers_email", "suppliers", ["email"])
    op.create_index("ix_suppliers_is_active", "suppliers", ["is_active"])
    op.create_index("ix_suppliers_name", "suppliers", ["name"])


def downgrade() -> None:
    op.drop_index("ix_suppliers_name", table_name="suppliers")
    op.drop_index("ix_suppliers_is_active", table_name="suppliers")
    op.drop_index("ix_suppliers_email", table_name="suppliers")
    op.drop_index("ix_suppliers_code", table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_index("ix_warehouses_name", table_name="warehouses")
    op.drop_index("ix_warehouses_is_active", table_name="warehouses")
    op.drop_index("ix_warehouses_code", table_name="warehouses")
    op.drop_table("warehouses")
