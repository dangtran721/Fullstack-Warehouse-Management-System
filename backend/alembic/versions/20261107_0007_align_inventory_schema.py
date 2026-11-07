"""Align inventory indexes and timestamp constraints."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20261107_0007"
down_revision: Union[str, Sequence[str], None] = "20261107_0006"
branch_labels = depends_on = None

def upgrade() -> None:
    for table, column in [("import_orders","warehouse_id"),("import_orders","supplier_id"),("import_orders","status"),("import_orders","created_by_id"),("export_orders","warehouse_id"),("export_orders","status"),("export_orders","created_by_id"),("import_order_lines","import_order_id"),("import_order_lines","product_id"),("export_order_lines","export_order_id"),("export_order_lines","product_id"),("inventory_movements","movement_type"),("inventory_movements","warehouse_id"),("inventory_movements","product_id"),("inventory_movements","import_order_id"),("inventory_movements","export_order_id"),("inventory_movements","performed_by_id")]: op.create_index(f"ix_{table}_{column}",table,[column])
    for table in ["inventory","import_orders","export_orders"]:
        op.alter_column(table,"created_at",nullable=False); op.alter_column(table,"updated_at",nullable=False)
    op.alter_column("inventory_movements","created_at",nullable=False)

def downgrade() -> None:
    for table in ["inventory","import_orders","export_orders"]:
        op.alter_column(table,"updated_at",nullable=True); op.alter_column(table,"created_at",nullable=True)
    op.alter_column("inventory_movements","created_at",nullable=True)
    for table, column in [("inventory_movements","performed_by_id"),("inventory_movements","export_order_id"),("inventory_movements","import_order_id"),("inventory_movements","product_id"),("inventory_movements","warehouse_id"),("inventory_movements","movement_type"),("export_order_lines","product_id"),("export_order_lines","export_order_id"),("import_order_lines","product_id"),("import_order_lines","import_order_id"),("export_orders","created_by_id"),("export_orders","status"),("export_orders","warehouse_id"),("import_orders","created_by_id"),("import_orders","status"),("import_orders","supplier_id"),("import_orders","warehouse_id")]: op.drop_index(f"ix_{table}_{column}",table_name=table)
