"""Create inventory and import/export orders."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20261107_0006"
down_revision: Union[str, Sequence[str], None] = "20261107_0005"
branch_labels = depends_on = None

def upgrade() -> None:
    op.create_table("inventory", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("warehouse_id", sa.Uuid(), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False), sa.Column("product_id", sa.Uuid(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False), sa.Column("quantity", sa.Numeric(18,3), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.UniqueConstraint("warehouse_id", "product_id", name="uq_inventory_warehouse_product"))
    for table, cols in [("inventory", ["warehouse_id"]), ("inventory", ["product_id"])]: op.create_index(f"ix_{table}_{cols[0]}", table, cols)
    for prefix, supplier in [("import", True), ("export", False)]:
        columns=[sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("warehouse_id",sa.Uuid(),sa.ForeignKey("warehouses.id",ondelete="RESTRICT"),nullable=False),sa.Column("status",sa.String(10),nullable=False),sa.Column("created_by_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),sa.Column("confirmed_by_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="RESTRICT")),sa.Column("confirmed_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()")),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.text("now()"))]
        if supplier: columns.insert(2,sa.Column("supplier_id",sa.Uuid(),sa.ForeignKey("suppliers.id",ondelete="RESTRICT"),nullable=False))
        op.create_table(f"{prefix}_orders",*columns)
        op.create_table(f"{prefix}_order_lines",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column(f"{prefix}_order_id",sa.Uuid(),sa.ForeignKey(f"{prefix}_orders.id",ondelete="RESTRICT"),nullable=False),sa.Column("product_id",sa.Uuid(),sa.ForeignKey("products.id",ondelete="RESTRICT"),nullable=False),sa.Column("quantity",sa.Numeric(18,3),nullable=False),sa.CheckConstraint("quantity > 0",name=f"ck_{prefix}_line_quantity_positive"),sa.UniqueConstraint(f"{prefix}_order_id","product_id",name=f"uq_{prefix}_order_line_product"))
    op.create_table("inventory_movements",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("movement_type",sa.String(10),nullable=False),sa.Column("warehouse_id",sa.Uuid(),sa.ForeignKey("warehouses.id",ondelete="RESTRICT"),nullable=False),sa.Column("product_id",sa.Uuid(),sa.ForeignKey("products.id",ondelete="RESTRICT"),nullable=False),sa.Column("quantity_delta",sa.Numeric(18,3),nullable=False),sa.Column("import_order_id",sa.Uuid(),sa.ForeignKey("import_orders.id",ondelete="RESTRICT")),sa.Column("export_order_id",sa.Uuid(),sa.ForeignKey("export_orders.id",ondelete="RESTRICT")),sa.Column("performed_by_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="RESTRICT"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()")),sa.CheckConstraint("quantity_delta <> 0",name="ck_inventory_movement_nonzero"))
def downgrade() -> None:
    op.drop_table("inventory_movements"); op.drop_table("export_order_lines"); op.drop_table("export_orders"); op.drop_table("import_order_lines"); op.drop_table("import_orders"); op.drop_index("ix_inventory_product_id",table_name="inventory"); op.drop_index("ix_inventory_warehouse_id",table_name="inventory"); op.drop_table("inventory")
