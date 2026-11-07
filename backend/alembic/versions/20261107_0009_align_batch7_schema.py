"""Align transfer and adjustment schema."""
from alembic import op
revision='20261107_0009';down_revision='20261107_0008';branch_labels=depends_on=None
def upgrade():
 for t,c in [('inventory_adjustments','product_id'),('inventory_adjustments','warehouse_id'),('transfer_order_lines','transfer_order_id'),('transfer_orders','destination_warehouse_id'),('transfer_orders','source_warehouse_id')]:op.create_index(f'ix_{t}_{c}',t,[c])
 op.alter_column('inventory_adjustments','created_at',nullable=False);op.alter_column('transfer_orders','created_at',nullable=False)
def downgrade():
 op.alter_column('transfer_orders','created_at',nullable=True);op.alter_column('inventory_adjustments','created_at',nullable=True)
 for t,c in [('transfer_orders','source_warehouse_id'),('transfer_orders','destination_warehouse_id'),('transfer_order_lines','transfer_order_id'),('inventory_adjustments','warehouse_id'),('inventory_adjustments','product_id')]:op.drop_index(f'ix_{t}_{c}',table_name=t)
