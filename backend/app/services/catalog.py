import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalog import Category, Product, Unit
from app.schemas.catalog import CategoryCreate, ProductCreate, ProductUpdate, UnitCreate


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


def _save(session: Session, entity):
    session.add(entity)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ConflictError from error
    session.refresh(entity)
    return entity


def list_categories(session: Session, skip: int, limit: int, search: str | None) -> list[Category]:
    statement = select(Category)
    if search:
        statement = statement.where(Category.name.ilike(f"%{search.strip().lower()}%"))
    return list(session.scalars(statement.order_by(Category.name).offset(skip).limit(limit)))


def create_category(session: Session, data: CategoryCreate) -> Category:
    return _save(session, Category(name=data.name))


def get_category(session: Session, category_id: uuid.UUID) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise NotFoundError
    return category


def update_category(session: Session, category_id: uuid.UUID, data: CategoryCreate) -> Category:
    category = get_category(session, category_id)
    category.name = data.name
    return _save(session, category)


def delete_category(session: Session, category_id: uuid.UUID) -> None:
    category = get_category(session, category_id)
    if session.scalar(select(func.count()).select_from(Product).where(Product.category_id == category_id)):
        raise ConflictError
    session.delete(category)
    session.commit()


def list_units(session: Session, skip: int, limit: int, search: str | None) -> list[Unit]:
    statement = select(Unit)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(Unit.name.ilike(pattern), Unit.code.ilike(pattern.upper())))
    return list(session.scalars(statement.order_by(Unit.name).offset(skip).limit(limit)))


def create_unit(session: Session, data: UnitCreate) -> Unit:
    return _save(session, Unit(name=data.name, code=data.code))


def get_unit(session: Session, unit_id: uuid.UUID) -> Unit:
    unit = session.get(Unit, unit_id)
    if unit is None:
        raise NotFoundError
    return unit


def update_unit(session: Session, unit_id: uuid.UUID, data: UnitCreate) -> Unit:
    unit = get_unit(session, unit_id)
    unit.name, unit.code = data.name, data.code
    return _save(session, unit)


def delete_unit(session: Session, unit_id: uuid.UUID) -> None:
    unit = get_unit(session, unit_id)
    if session.scalar(select(func.count()).select_from(Product).where(Product.unit_id == unit_id)):
        raise ConflictError
    session.delete(unit)
    session.commit()


def _validate_product_relations(session: Session, category_id: uuid.UUID, unit_id: uuid.UUID) -> None:
    if session.get(Category, category_id) is None or session.get(Unit, unit_id) is None:
        raise NotFoundError



def list_products(
    session: Session, skip: int, limit: int, search: str | None, category_id: uuid.UUID | None, is_active: bool | None
) -> list[Product]:
    statement = select(Product)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern.upper())))
    if category_id:
        statement = statement.where(Product.category_id == category_id)
    if is_active is not None:
        statement = statement.where(Product.is_active == is_active)
    return list(session.scalars(statement.order_by(Product.name).offset(skip).limit(limit)))


def create_product(session: Session, data: ProductCreate) -> Product:
    _validate_product_relations(session, data.category_id, data.unit_id)
    return _save(session, Product(**data.model_dump()))


def get_product(session: Session, product_id: uuid.UUID) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise NotFoundError
    return product


def update_product(session: Session, product_id: uuid.UUID, data: ProductUpdate) -> Product:
    product = get_product(session, product_id)
    values = data.model_dump(exclude_unset=True)
    category_id = values.get("category_id", product.category_id)
    unit_id = values.get("unit_id", product.unit_id)
    _validate_product_relations(session, category_id, unit_id)
    for field, value in values.items():
        setattr(product, field, value)
    return _save(session, product)


def delete_product(session: Session, product_id: uuid.UUID) -> None:
    product = get_product(session, product_id)
    session.delete(product)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ConflictError from error
