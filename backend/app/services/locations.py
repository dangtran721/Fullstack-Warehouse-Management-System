import uuid

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.locations import Supplier, Warehouse
from app.services.catalog import ConflictError, NotFoundError


def _save(session: Session, entity):
    session.add(entity)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ConflictError from error
    session.refresh(entity)
    return entity


def _list(session: Session, model, skip: int, limit: int, search: str | None, is_active: bool | None):
    statement = select(model)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(model.name.ilike(pattern), model.code.ilike(pattern.upper())))
    if is_active is not None:
        statement = statement.where(model.is_active == is_active)
    return list(session.scalars(statement.order_by(model.name).offset(skip).limit(limit)))


def _get(session: Session, model, entity_id: uuid.UUID):
    entity = session.get(model, entity_id)
    if entity is None:
        raise NotFoundError
    return entity


def _update(session: Session, model, entity_id: uuid.UUID, data):
    entity = _get(session, model, entity_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(entity, field, value)
    return _save(session, entity)


def _delete(session: Session, model, entity_id: uuid.UUID) -> None:
    entity = _get(session, model, entity_id)
    session.delete(entity)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ConflictError from error


def list_warehouses(session: Session, skip: int, limit: int, search: str | None, is_active: bool | None) -> list[Warehouse]:
    return _list(session, Warehouse, skip, limit, search, is_active)


def create_warehouse(session: Session, data) -> Warehouse:
    return _save(session, Warehouse(**data.model_dump()))


def get_warehouse(session: Session, warehouse_id: uuid.UUID) -> Warehouse:
    return _get(session, Warehouse, warehouse_id)


def update_warehouse(session: Session, warehouse_id: uuid.UUID, data) -> Warehouse:
    return _update(session, Warehouse, warehouse_id, data)


def delete_warehouse(session: Session, warehouse_id: uuid.UUID) -> None:
    _delete(session, Warehouse, warehouse_id)


def list_suppliers(session: Session, skip: int, limit: int, search: str | None, is_active: bool | None) -> list[Supplier]:
    return _list(session, Supplier, skip, limit, search, is_active)


def create_supplier(session: Session, data) -> Supplier:
    return _save(session, Supplier(**data.model_dump()))


def get_supplier(session: Session, supplier_id: uuid.UUID) -> Supplier:
    return _get(session, Supplier, supplier_id)


def update_supplier(session: Session, supplier_id: uuid.UUID, data) -> Supplier:
    return _update(session, Supplier, supplier_id, data)


def delete_supplier(session: Session, supplier_id: uuid.UUID) -> None:
    _delete(session, Supplier, supplier_id)
