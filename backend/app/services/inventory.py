import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import Product
from app.models.inventory import DocumentStatus, ExportOrder, ExportOrderLine, ImportOrder, ImportOrderLine, Inventory, InventoryMovement, MovementType
from app.models.locations import Supplier, Warehouse
from app.models.user import User, UserRole
from app.schemas.inventory import ExportOrderCreate, ImportOrderCreate
from app.services.catalog import ConflictError, NotFoundError


class InsufficientStockError(Exception): pass
class InvalidStateError(Exception): pass


def _active(session: Session, model, entity_id: uuid.UUID):
    entity = session.get(model, entity_id)
    if entity is None: raise NotFoundError
    if not entity.is_active: raise ConflictError
    return entity


def _validate_lines(session: Session, lines) -> None:
    product_ids = [line.product_id for line in lines]
    if len(set(product_ids)) != len(product_ids): raise ConflictError
    products = list(session.scalars(select(Product).where(Product.id.in_(product_ids), Product.is_active.is_(True))))
    if len(products) != len(product_ids): raise NotFoundError


def create_import(session: Session, data: ImportOrderCreate, user: User) -> ImportOrder:
    _active(session, Warehouse, data.warehouse_id); _active(session, Supplier, data.supplier_id); _validate_lines(session, data.lines)
    order = ImportOrder(warehouse_id=data.warehouse_id, supplier_id=data.supplier_id, created_by_id=user.id)
    order.lines = [ImportOrderLine(product_id=line.product_id, quantity=line.quantity) for line in data.lines]
    session.add(order); session.commit(); session.refresh(order)
    return get_import(session, order.id)


def create_export(session: Session, data: ExportOrderCreate, user: User) -> ExportOrder:
    _active(session, Warehouse, data.warehouse_id); _validate_lines(session, data.lines)
    order = ExportOrder(warehouse_id=data.warehouse_id, created_by_id=user.id)
    order.lines = [ExportOrderLine(product_id=line.product_id, quantity=line.quantity) for line in data.lines]
    session.add(order); session.commit(); session.refresh(order)
    return get_export(session, order.id)


def get_import(session: Session, order_id: uuid.UUID) -> ImportOrder:
    order = session.scalar(select(ImportOrder).options(selectinload(ImportOrder.lines)).where(ImportOrder.id == order_id))
    if order is None: raise NotFoundError
    return order

def list_imports(session: Session, status: DocumentStatus | None, skip: int, limit: int):
    statement = select(ImportOrder).options(selectinload(ImportOrder.lines))
    if status: statement = statement.where(ImportOrder.status == status)
    return list(session.scalars(statement.order_by(ImportOrder.created_at.desc()).offset(skip).limit(limit)))


def get_export(session: Session, order_id: uuid.UUID) -> ExportOrder:
    order = session.scalar(select(ExportOrder).options(selectinload(ExportOrder.lines)).where(ExportOrder.id == order_id))
    if order is None: raise NotFoundError
    return order

def list_exports(session: Session, status: DocumentStatus | None, skip: int, limit: int):
    statement = select(ExportOrder).options(selectinload(ExportOrder.lines))
    if status: statement = statement.where(ExportOrder.status == status)
    return list(session.scalars(statement.order_by(ExportOrder.created_at.desc()).offset(skip).limit(limit)))


def list_inventory(session: Session, warehouse_id: uuid.UUID | None, product_id: uuid.UUID | None, search: str | None, skip: int, limit: int):
    statement = select(Inventory).join(Product)
    if warehouse_id: statement = statement.where(Inventory.warehouse_id == warehouse_id)
    if product_id: statement = statement.where(Inventory.product_id == product_id)
    if search: statement = statement.where(or_(Product.name.ilike(f"%{search.strip()}%"), Product.sku.ilike(f"%{search.strip().upper()}%")))
    return list(session.scalars(statement.order_by(Inventory.updated_at.desc()).offset(skip).limit(limit)))


def _locked_inventory(session: Session, warehouse_id: uuid.UUID, product_id: uuid.UUID) -> Inventory:
    inventory = session.scalar(select(Inventory).where(Inventory.warehouse_id == warehouse_id, Inventory.product_id == product_id).with_for_update())
    if inventory is None:
        inventory = Inventory(warehouse_id=warehouse_id, product_id=product_id, quantity=Decimal("0"))
        session.add(inventory); session.flush()
    return inventory


def confirm_import(session: Session, order_id: uuid.UUID, user: User) -> ImportOrder:
    try:
        order = session.scalar(select(ImportOrder).options(selectinload(ImportOrder.lines)).where(ImportOrder.id == order_id).with_for_update())
        if order is None: raise NotFoundError
        if order.status is not DocumentStatus.DRAFT: raise InvalidStateError
        _active(session, Warehouse, order.warehouse_id); _active(session, Supplier, order.supplier_id); _validate_lines(session, order.lines)
        for line in order.lines:
            item = _locked_inventory(session, order.warehouse_id, line.product_id); item.quantity += line.quantity
            session.add(InventoryMovement(movement_type=MovementType.IMPORT, warehouse_id=order.warehouse_id, product_id=line.product_id, quantity_delta=line.quantity, import_order_id=order.id, performed_by_id=user.id))
        order.status, order.confirmed_by_id, order.confirmed_at = DocumentStatus.CONFIRMED, user.id, datetime.now(timezone.utc)
        session.commit()
    except Exception:
        session.rollback(); raise
    return get_import(session, order_id)


def confirm_export(session: Session, order_id: uuid.UUID, user: User) -> ExportOrder:
    try:
        order = session.scalar(select(ExportOrder).options(selectinload(ExportOrder.lines)).where(ExportOrder.id == order_id).with_for_update())
        if order is None: raise NotFoundError
        if order.status is not DocumentStatus.DRAFT: raise InvalidStateError
        _active(session, Warehouse, order.warehouse_id); _validate_lines(session, order.lines)
        for line in order.lines:
            item = _locked_inventory(session, order.warehouse_id, line.product_id)
            if user.role is not UserRole.ADMIN and item.quantity < line.quantity: raise InsufficientStockError
            item.quantity -= line.quantity
            session.add(InventoryMovement(movement_type=MovementType.EXPORT, warehouse_id=order.warehouse_id, product_id=line.product_id, quantity_delta=-line.quantity, export_order_id=order.id, performed_by_id=user.id))
        order.status, order.confirmed_by_id, order.confirmed_at = DocumentStatus.CONFIRMED, user.id, datetime.now(timezone.utc)
        session.commit()
    except Exception:
        session.rollback(); raise
    return get_export(session, order_id)


def cancel_order(session: Session, order, order_id: uuid.UUID):
    document = session.get(order, order_id)
    if document is None: raise NotFoundError
    if document.status is not DocumentStatus.DRAFT: raise InvalidStateError
    document.status = DocumentStatus.CANCELLED; session.commit()
