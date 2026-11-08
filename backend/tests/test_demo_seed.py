from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.inventory import DocumentStatus, ExportOrder, ImportOrder, Inventory, InventoryAdjustment, InventoryMovement, TransferOrder
from app.models.locations import Supplier, Warehouse
from app.models.catalog import Category, Product
from app.models.user import User, UserRole
from scripts.seed_demo_data import seed_demo_data


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(User(username="seed-admin", email="seed-admin@example.com", password_hash=hash_password("Password1"), role=UserRole.ADMIN))
    session.commit()
    session.close()
    yield factory
    Base.metadata.drop_all(engine)


def test_techstation_demo_seed_is_idempotent_and_preserves_inventory_integrity(session_factory):
    session = session_factory()
    try:
        admin = session.scalar(select(User).where(User.role == UserRole.ADMIN))
        summary = seed_demo_data(session, admin.username)
        snapshot = {
            "warehouses": session.scalar(select(func.count()).select_from(Warehouse)),
            "categories": session.scalar(select(func.count()).select_from(Category)),
            "suppliers": session.scalar(select(func.count()).select_from(Supplier)),
            "products": session.scalar(select(func.count()).select_from(Product)),
            "imports": session.scalar(select(func.count()).select_from(ImportOrder)),
            "exports": session.scalar(select(func.count()).select_from(ExportOrder)),
            "transfers": session.scalar(select(func.count()).select_from(TransferOrder)),
            "adjustments": session.scalar(select(func.count()).select_from(InventoryAdjustment)),
            "movements": session.scalar(select(func.count()).select_from(InventoryMovement)),
        }
        second = seed_demo_data(session, admin.username)
        assert summary.warehouses == 3 and summary.categories == 12 and summary.suppliers == 5 and summary.products == 24
        assert summary.imports_confirmed == 5 and summary.exports_confirmed == 5 and summary.transfers_confirmed == 4
        assert summary.adjustments == 2 and summary.out_of_stock_alerts >= 1
        assert second == summary
        assert snapshot == {
            "warehouses": 3, "categories": 12, "suppliers": 5, "products": 24,
            "imports": 7, "exports": 7, "transfers": 6, "adjustments": 2, "movements": 57,
        }
        assert session.scalar(select(func.count()).select_from(ImportOrder).where(ImportOrder.status == DocumentStatus.CONFIRMED)) == 5
        assert session.scalar(select(func.count()).select_from(ExportOrder).where(ExportOrder.status == DocumentStatus.CONFIRMED)) == 5
        assert session.scalar(select(func.count()).select_from(TransferOrder).where(TransferOrder.status == DocumentStatus.CONFIRMED)) == 4
        balances = {(item.warehouse_id, item.product_id): item.quantity for item in session.scalars(select(Inventory))}
        deltas = {}
        for movement in session.scalars(select(InventoryMovement)):
            key = (movement.warehouse_id, movement.product_id)
            deltas[key] = deltas.get(key, Decimal("0")) + movement.quantity_delta
        assert balances == deltas
        assert all(quantity >= 0 for quantity in balances.values())
        assert summary.low_stock_alerts >= 3
    finally:
        session.close()
