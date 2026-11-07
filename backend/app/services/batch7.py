import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.inventory import DocumentStatus, Inventory, InventoryAdjustment, InventoryMovement, MovementType, TransferOrder, TransferOrderLine
from app.models.locations import Warehouse
from app.models.catalog import Product
from app.models.user import User
from app.schemas.inventory import AdjustmentCreate, ThresholdUpdate, TransferCreate
from app.services.catalog import ConflictError, NotFoundError
from app.services.inventory import InsufficientStockError, InvalidStateError, _active, _locked_inventory, _validate_lines

def create_transfer(session: Session, data: TransferCreate, user: User):
    if data.source_warehouse_id == data.destination_warehouse_id: raise ConflictError
    _active(session, Warehouse, data.source_warehouse_id); _active(session, Warehouse, data.destination_warehouse_id); _validate_lines(session, data.lines)
    order=TransferOrder(source_warehouse_id=data.source_warehouse_id,destination_warehouse_id=data.destination_warehouse_id,created_by_id=user.id); order.lines=[TransferOrderLine(product_id=x.product_id,quantity=x.quantity) for x in data.lines]; session.add(order);session.commit();return get_transfer(session,order.id)
def get_transfer(session: Session, order_id: uuid.UUID):
    order=session.scalar(select(TransferOrder).options(selectinload(TransferOrder.lines)).where(TransferOrder.id==order_id))
    if not order: raise NotFoundError
    return order
def confirm_transfer(session: Session, order_id: uuid.UUID, user: User):
    try:
        order=session.scalar(select(TransferOrder).options(selectinload(TransferOrder.lines)).where(TransferOrder.id==order_id).with_for_update())
        if not order: raise NotFoundError
        if order.status is not DocumentStatus.DRAFT: raise InvalidStateError
        _active(session,Warehouse,order.source_warehouse_id);_active(session,Warehouse,order.destination_warehouse_id);_validate_lines(session,order.lines)
        for line in order.lines:
            source=_locked_inventory(session,order.source_warehouse_id,line.product_id)
            if source.quantity < line.quantity: raise InsufficientStockError
            destination=_locked_inventory(session,order.destination_warehouse_id,line.product_id);source.quantity-=line.quantity;destination.quantity+=line.quantity
            session.add_all([InventoryMovement(movement_type=MovementType.TRANSFER,warehouse_id=order.source_warehouse_id,product_id=line.product_id,quantity_delta=-line.quantity,performed_by_id=user.id),InventoryMovement(movement_type=MovementType.TRANSFER,warehouse_id=order.destination_warehouse_id,product_id=line.product_id,quantity_delta=line.quantity,performed_by_id=user.id)])
        order.status=DocumentStatus.CONFIRMED;order.confirmed_by_id=user.id;order.confirmed_at=datetime.now(timezone.utc);session.commit()
    except Exception: session.rollback();raise
    return get_transfer(session,order_id)
def cancel_transfer(session: Session, order_id: uuid.UUID):
    order=session.get(TransferOrder,order_id)
    if not order: raise NotFoundError
    if order.status is not DocumentStatus.DRAFT: raise InvalidStateError
    order.status=DocumentStatus.CANCELLED;session.commit()
def adjust(session: Session,data:AdjustmentCreate,user:User):
    try:
        _active(session,Warehouse,data.warehouse_id);_active(session,Product,data.product_id);item=_locked_inventory(session,data.warehouse_id,data.product_id)
        if item.quantity+data.quantity_delta<0: raise InsufficientStockError
        item.quantity+=data.quantity_delta; adjustment=InventoryAdjustment(**data.model_dump(),performed_by_id=user.id);session.add(adjustment);session.add(InventoryMovement(movement_type=MovementType.ADJUSTMENT,warehouse_id=data.warehouse_id,product_id=data.product_id,quantity_delta=data.quantity_delta,performed_by_id=user.id));session.commit();return adjustment
    except Exception: session.rollback();raise
def set_threshold(session:Session,warehouse_id:uuid.UUID,product_id:uuid.UUID,data:ThresholdUpdate):
    item=_locked_inventory(session,warehouse_id,product_id);item.min_quantity=data.min_quantity;session.commit();session.refresh(item);return item
def alerts(session:Session,warehouse_id:uuid.UUID|None):
    q=select(Inventory).where(Inventory.min_quantity.is_not(None),Inventory.quantity<=Inventory.min_quantity)
    if warehouse_id:q=q.where(Inventory.warehouse_id==warehouse_id)
    return list(session.scalars(q.order_by(Inventory.quantity)))
