"""PostgreSQL-only verification of inventory row locking."""
import os
import threading
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.catalog import Category, Product, Unit
from app.models.inventory import ExportOrder, ExportOrderLine, Inventory
from app.models.locations import Warehouse
from app.models.user import User, UserRole
from app.services.inventory import InsufficientStockError, confirm_export


DATABASE_URL = os.getenv("WMS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires WMS_TEST_DATABASE_URL")


def test_concurrent_staff_exports_preserve_available_inventory():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    factory = sessionmaker(bind=engine)
    session = factory()
    suffix = uuid.uuid4().hex[:8]
    category = Category(name=f"concurrency-{suffix}")
    unit = Unit(name=f"unit-{suffix}", code=f"U{suffix[:6]}")
    warehouse = Warehouse(code=f"W{suffix[:6]}", name=f"Warehouse {suffix}")
    staff = User(
        username=f"staff-{suffix}",
        email=f"staff-{suffix}@test.local",
        password_hash="unused",
        role=UserRole.STAFF,
    )
    session.add_all([category, unit, warehouse, staff])
    session.flush()
    product = Product(sku=f"P{suffix}", name=f"Product {suffix}", category_id=category.id, unit_id=unit.id)
    session.add(product)
    session.flush()
    session.add(Inventory(warehouse_id=warehouse.id, product_id=product.id, quantity=Decimal("10")))
    orders = []
    for _ in range(2):
        order = ExportOrder(warehouse_id=warehouse.id, created_by_id=staff.id)
        order.lines = [ExportOrderLine(product_id=product.id, quantity=Decimal("6"))]
        session.add(order)
        orders.append(order)
    session.commit()
    order_ids = [order.id for order in orders]
    staff_id, warehouse_id, product_id = staff.id, warehouse.id, product.id
    session.close()

    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def confirm(order_id):
        worker_session = factory()
        try:
            worker = worker_session.get(User, staff_id)
            barrier.wait(timeout=10)
            confirm_export(worker_session, order_id, worker)
            outcomes.append("confirmed")
        except InsufficientStockError:
            outcomes.append("insufficient")
        finally:
            worker_session.close()

    threads = [threading.Thread(target=confirm, args=(order_id,)) for order_id in order_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
        assert not thread.is_alive()

    verification_session = factory()
    try:
        inventory = verification_session.query(Inventory).filter_by(warehouse_id=warehouse_id, product_id=product_id).one()
        assert sorted(outcomes) == ["confirmed", "insufficient"]
        assert inventory.quantity == Decimal("4.000")
    finally:
        verification_session.close()
