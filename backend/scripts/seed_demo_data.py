"""Idempotent demo data for the fictional TechStation Distribution company.

The script deliberately uses the same application services as the API for every
inventory-changing operation. It never writes inventory balances or movements
directly.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_session_factory
from app.models.catalog import Category, Product, Unit
from app.models.inventory import (
    DocumentStatus,
    ExportOrder,
    ImportOrder,
    Inventory,
    InventoryAdjustment,
    InventoryMovement,
    TransferOrder,
)
from app.models.locations import Supplier, Warehouse
from app.models.user import User, UserRole
from app.schemas.catalog import CategoryCreate, ProductCreate, UnitCreate
from app.schemas.inventory import AdjustmentCreate, ExportOrderCreate, ImportOrderCreate, OrderLineCreate, ThresholdUpdate, TransferCreate
from app.schemas.locations import SupplierCreate, WarehouseCreate
from app.services import batch7, catalog, inventory, locations


DEMO_PREFIX = "TS-"

WAREHOUSES = (
    ("TS-HCM", "Kho Tổng TP.HCM", "Quận 1, TP.HCM"),
    ("TS-Q7", "Kho Chi Nhánh Quận 7", "Quận 7, TP.HCM"),
    ("TS-TD", "Kho Chi Nhánh Thủ Đức", "TP. Thủ Đức, TP.HCM"),
)

# Category has no parent_id in the approved schema. These names preserve the
# intended hierarchy without pretending the database supports a category tree.
CATEGORIES = (
    "thiết bị máy tính",
    "thiết bị máy tính - laptop",
    "thiết bị máy tính - màn hình",
    "thiết bị máy tính - bộ nhớ & lưu trữ",
    "phụ kiện công nghệ",
    "phụ kiện công nghệ - chuột",
    "phụ kiện công nghệ - bàn phím",
    "phụ kiện công nghệ - tai nghe",
    "văn phòng phẩm",
    "văn phòng phẩm - giấy in",
    "văn phòng phẩm - bút viết",
    "văn phòng phẩm - dụng cụ văn phòng",
)

UNITS = (
    ("cái", "PCS"),
    ("ram", "REAM"),
    ("cây", "PEN"),
    ("hộp", "BOX"),
    ("thùng", "CTN"),
    ("lốc", "PACK"),
)

SUPPLIERS = (
    ("TS-SUP-TECH", "TechSource Việt Nam", "techsource@techstation.example"),
    ("TS-SUP-DIGITAL", "Digital Parts Distribution", "digitalparts@techstation.example"),
    ("TS-SUP-PERIPHERAL", "Peripheral Hub", "peripheral@techstation.example"),
    ("TS-SUP-PAPER", "Office Paper Supply", "paper@techstation.example"),
    ("TS-SUP-STATIONERY", "Stationery Partner", "stationery@techstation.example"),
)

# SKU, display name, category name, base-unit code, import quantity.
PRODUCTS = (
    ("TS-LAP-DELL-3530", "Dell Inspiron 15 3530", "thiết bị máy tính - laptop", "PCS", "8"),
    ("TS-LAP-ASUS-V15", "ASUS Vivobook 15", "thiết bị máy tính - laptop", "PCS", "7"),
    ("TS-LAP-LENOVO-S3", "Lenovo IdeaPad Slim 3", "thiết bị máy tính - laptop", "PCS", "6"),
    ("TS-MON-DELL-P2422H", "Dell P2422H", "thiết bị máy tính - màn hình", "PCS", "12"),
    ("TS-MON-LG-24MP400", "LG 24MP400", "thiết bị máy tính - màn hình", "PCS", "12"),
    ("TS-MON-SAM-27", "Samsung Essential Monitor 27 inch", "thiết bị máy tính - màn hình", "PCS", "10"),
    ("TS-SSD-KINGSTON-NV2", "Kingston NV2 SSD 500GB", "thiết bị máy tính - bộ nhớ & lưu trữ", "PCS", "25"),
    ("TS-SSD-SAMSUNG-970", "Samsung 970 EVO Plus 1TB", "thiết bị máy tính - bộ nhớ & lưu trữ", "PCS", "18"),
    ("TS-RAM-KINGSTON-16", "Kingston Fury Beast RAM 16GB", "thiết bị máy tính - bộ nhớ & lưu trữ", "PCS", "20"),
    ("TS-MOUSE-G102", "Logitech G102", "phụ kiện công nghệ - chuột", "PCS", "60"),
    ("TS-MOUSE-M331", "Logitech M331 Silent", "phụ kiện công nghệ - chuột", "PCS", "50"),
    ("TS-MOUSE-RAPOO-M20", "Rapoo M20 Plus", "phụ kiện công nghệ - chuột", "PCS", "45"),
    ("TS-KEY-KEYCHRON-K2", "Keychron K2", "phụ kiện công nghệ - bàn phím", "PCS", "30"),
    ("TS-KEY-LOGI-K120", "Logitech K120", "phụ kiện công nghệ - bàn phím", "PCS", "30"),
    ("TS-KEY-DAREU-EK87", "DareU EK87", "phụ kiện công nghệ - bàn phím", "PCS", "25"),
    ("TS-HEAD-HYPERX-S2", "HyperX Cloud Stinger 2", "phụ kiện công nghệ - tai nghe", "PCS", "20"),
    ("TS-HEAD-LOGI-H390", "Logitech H390", "phụ kiện công nghệ - tai nghe", "PCS", "18"),
    ("TS-PAPER-DOUBLE-A", "Double A A4 80gsm", "văn phòng phẩm - giấy in", "REAM", "100"),
    ("TS-PAPER-PAPERONE", "PaperOne A4 70gsm", "văn phòng phẩm - giấy in", "REAM", "90"),
    ("TS-PEN-TL027-BLUE", "Thiên Long TL-027 xanh", "văn phòng phẩm - bút viết", "PEN", "200"),
    ("TS-PEN-TL027-BLACK", "Thiên Long TL-027 đen", "văn phòng phẩm - bút viết", "PEN", "150"),
    ("TS-PEN-PENTEL", "Pentel EnerGel", "văn phòng phẩm - bút viết", "PEN", "120"),
    ("TS-TOOL-STAPLER-10", "Bấm kim số 10", "văn phòng phẩm - dụng cụ văn phòng", "PCS", "50"),
    ("TS-TOOL-STAPLES-10", "Kim bấm số 10", "văn phòng phẩm - dụng cụ văn phòng", "BOX", "70"),
)


class SeedConflictError(RuntimeError):
    """A matching demo record exists in a different immutable state."""


@dataclass(frozen=True)
class SeedSummary:
    warehouses: int
    categories: int
    units: int
    suppliers: int
    products: int
    imports_confirmed: int
    exports_confirmed: int
    transfers_confirmed: int
    adjustments: int
    low_stock_alerts: int
    out_of_stock_alerts: int


def _lines(product_ids: dict[str, object], rows: Iterable[tuple[str, str]]) -> list[OrderLineCreate]:
    return [OrderLineCreate(product_id=product_ids[sku], quantity=Decimal(quantity)) for sku, quantity in rows]


def _signature(lines) -> tuple[tuple[str, Decimal], ...]:
    return tuple(sorted((str(line.product_id), Decimal(line.quantity)) for line in lines))


def _find_import(session: Session, user: User, warehouse_id, supplier_id, lines):
    expected = _signature(lines)
    orders = session.scalars(
        select(ImportOrder)
        .options(selectinload(ImportOrder.lines))
        .where(ImportOrder.created_by_id == user.id, ImportOrder.warehouse_id == warehouse_id, ImportOrder.supplier_id == supplier_id)
    )
    return next((order for order in orders if _signature(order.lines) == expected), None)


def _find_export(session: Session, user: User, warehouse_id, lines):
    expected = _signature(lines)
    orders = session.scalars(
        select(ExportOrder).options(selectinload(ExportOrder.lines)).where(ExportOrder.created_by_id == user.id, ExportOrder.warehouse_id == warehouse_id)
    )
    return next((order for order in orders if _signature(order.lines) == expected), None)


def _find_transfer(session: Session, user: User, source_id, destination_id, lines):
    expected = _signature(lines)
    orders = session.scalars(
        select(TransferOrder)
        .options(selectinload(TransferOrder.lines))
        .where(
            TransferOrder.created_by_id == user.id,
            TransferOrder.source_warehouse_id == source_id,
            TransferOrder.destination_warehouse_id == destination_id,
        )
    )
    return next((order for order in orders if _signature(order.lines) == expected), None)


def _ensure_import(session: Session, user: User, warehouse_id, supplier_id, lines, status: DocumentStatus):
    order = _find_import(session, user, warehouse_id, supplier_id, lines)
    if order is None:
        order = inventory.create_import(session, ImportOrderCreate(warehouse_id=warehouse_id, supplier_id=supplier_id, lines=lines), user)
    if order.status is status:
        return order
    if order.status is not DocumentStatus.DRAFT:
        raise SeedConflictError(f"Import {order.id} exists with {order.status}, expected {status}.")
    return inventory.confirm_import(session, order.id, user) if status is DocumentStatus.CONFIRMED else _cancel_import(session, order.id)


def _cancel_import(session: Session, order_id):
    inventory.cancel_order(session, ImportOrder, order_id)
    return inventory.get_import(session, order_id)


def _ensure_export(session: Session, user: User, warehouse_id, lines, status: DocumentStatus):
    order = _find_export(session, user, warehouse_id, lines)
    if order is None:
        order = inventory.create_export(session, ExportOrderCreate(warehouse_id=warehouse_id, lines=lines), user)
    if order.status is status:
        return order
    if order.status is not DocumentStatus.DRAFT:
        raise SeedConflictError(f"Export {order.id} exists with {order.status}, expected {status}.")
    return inventory.confirm_export(session, order.id, user) if status is DocumentStatus.CONFIRMED else _cancel_export(session, order.id)


def _cancel_export(session: Session, order_id):
    inventory.cancel_order(session, ExportOrder, order_id)
    return inventory.get_export(session, order_id)


def _ensure_transfer(session: Session, user: User, source_id, destination_id, lines, status: DocumentStatus):
    order = _find_transfer(session, user, source_id, destination_id, lines)
    if order is None:
        order = batch7.create_transfer(session, TransferCreate(source_warehouse_id=source_id, destination_warehouse_id=destination_id, lines=lines), user)
    if order.status is status:
        return order
    if order.status is not DocumentStatus.DRAFT:
        raise SeedConflictError(f"Transfer {order.id} exists with {order.status}, expected {status}.")
    if status is DocumentStatus.CONFIRMED:
        return batch7.confirm_transfer(session, order.id, user)
    batch7.cancel_transfer(session, order.id)
    return batch7.get_transfer(session, order.id)


def _ensure_adjustment(session: Session, user: User, warehouse_id, product_id, quantity_delta: str, reason: str):
    existing = session.scalar(
        select(InventoryAdjustment).where(
            InventoryAdjustment.performed_by_id == user.id,
            InventoryAdjustment.warehouse_id == warehouse_id,
            InventoryAdjustment.product_id == product_id,
            InventoryAdjustment.reason == reason,
        )
    )
    if existing is None:
        return batch7.adjust(
            session,
            AdjustmentCreate(warehouse_id=warehouse_id, product_id=product_id, quantity_delta=Decimal(quantity_delta), reason=reason),
            user,
        )
    return existing


def _master_data(session: Session):
    warehouses = {item.code: item for item in session.scalars(select(Warehouse).where(Warehouse.code.in_([row[0] for row in WAREHOUSES])))}
    for code, name, address in WAREHOUSES:
        if code not in warehouses:
            warehouses[code] = locations.create_warehouse(session, WarehouseCreate(code=code, name=name, address=address, description="TechStation Distribution demo warehouse"))

    categories = {item.name: item for item in session.scalars(select(Category).where(Category.name.in_(CATEGORIES)))}
    for name in CATEGORIES:
        if name not in categories:
            categories[name] = catalog.create_category(session, CategoryCreate(name=name))

    units = {item.code: item for item in session.scalars(select(Unit).where(Unit.code.in_([row[1] for row in UNITS])))}
    for name, code in UNITS:
        if code not in units:
            units[code] = catalog.create_unit(session, UnitCreate(name=name, code=code))

    suppliers = {item.code: item for item in session.scalars(select(Supplier).where(Supplier.code.in_([row[0] for row in SUPPLIERS])))}
    for code, name, email in SUPPLIERS:
        if code not in suppliers:
            suppliers[code] = locations.create_supplier(session, SupplierCreate(code=code, name=name, email=email, description="TechStation Distribution demo supplier"))

    skus = [row[0] for row in PRODUCTS]
    products = {item.sku: item for item in session.scalars(select(Product).where(Product.sku.in_(skus)))}
    for sku, name, category_name, unit_code, _ in PRODUCTS:
        if sku not in products:
            products[sku] = catalog.create_product(
                session,
                ProductCreate(sku=sku, name=name, category_id=categories[category_name].id, unit_id=units[unit_code].id, description="TechStation Distribution demo product"),
            )
    return warehouses, categories, units, suppliers, products


def seed_demo_data(session: Session, admin_username: str) -> SeedSummary:
    """Seed demo data with an existing ADMIN. Safe to run repeatedly."""
    admin = session.scalar(select(User).where(User.username == admin_username.strip().lower()))
    if admin is None or admin.role is not UserRole.ADMIN or not admin.is_active:
        raise ValueError("An active ADMIN user is required; the seed never creates or modifies users.")

    warehouses, categories, units, suppliers, products = _master_data(session)
    warehouse_ids = {code: value.id for code, value in warehouses.items()}
    supplier_ids = {code: value.id for code, value in suppliers.items()}
    product_ids = {sku: value.id for sku, value in products.items()}

    imports = (
        ("TS-SUP-TECH", (("TS-LAP-DELL-3530", "8"), ("TS-LAP-ASUS-V15", "7"), ("TS-LAP-LENOVO-S3", "6"))),
        ("TS-SUP-DIGITAL", (("TS-MON-DELL-P2422H", "12"), ("TS-MON-LG-24MP400", "12"), ("TS-MON-SAM-27", "10"), ("TS-SSD-KINGSTON-NV2", "25"), ("TS-SSD-SAMSUNG-970", "18"), ("TS-RAM-KINGSTON-16", "20"))),
        ("TS-SUP-PERIPHERAL", (("TS-MOUSE-G102", "60"), ("TS-MOUSE-M331", "50"), ("TS-MOUSE-RAPOO-M20", "45"), ("TS-KEY-KEYCHRON-K2", "30"), ("TS-KEY-LOGI-K120", "30"), ("TS-KEY-DAREU-EK87", "25"), ("TS-HEAD-HYPERX-S2", "20"), ("TS-HEAD-LOGI-H390", "18"))),
        ("TS-SUP-PAPER", (("TS-PAPER-DOUBLE-A", "100"), ("TS-PAPER-PAPERONE", "90"))),
        ("TS-SUP-STATIONERY", (("TS-PEN-TL027-BLUE", "200"), ("TS-PEN-TL027-BLACK", "150"), ("TS-PEN-PENTEL", "120"), ("TS-TOOL-STAPLER-10", "50"), ("TS-TOOL-STAPLES-10", "70"))),
    )
    for supplier_code, rows in imports:
        _ensure_import(session, admin, warehouse_ids["TS-HCM"], supplier_ids[supplier_code], _lines(product_ids, rows), DocumentStatus.CONFIRMED)

    _ensure_import(session, admin, warehouse_ids["TS-HCM"], supplier_ids["TS-SUP-TECH"], _lines(product_ids, (("TS-LAP-ASUS-V15", "1"),)), DocumentStatus.DRAFT)
    _ensure_import(session, admin, warehouse_ids["TS-HCM"], supplier_ids["TS-SUP-TECH"], _lines(product_ids, (("TS-LAP-LENOVO-S3", "1"),)), DocumentStatus.CANCELLED)

    transfers = (
        ("TS-Q7", (("TS-MOUSE-G102", "20"), ("TS-MOUSE-M331", "12"), ("TS-KEY-KEYCHRON-K2", "8"))),
        ("TS-TD", (("TS-MON-DELL-P2422H", "5"), ("TS-SSD-KINGSTON-NV2", "10"), ("TS-RAM-KINGSTON-16", "12"))),
        ("TS-Q7", (("TS-PAPER-DOUBLE-A", "30"), ("TS-PEN-TL027-BLUE", "60"), ("TS-TOOL-STAPLER-10", "20"))),
        ("TS-TD", (("TS-KEY-LOGI-K120", "12"), ("TS-HEAD-HYPERX-S2", "8"), ("TS-TOOL-STAPLES-10", "40"))),
    )
    for destination, rows in transfers:
        _ensure_transfer(session, admin, warehouse_ids["TS-HCM"], warehouse_ids[destination], _lines(product_ids, rows), DocumentStatus.CONFIRMED)
    _ensure_transfer(session, admin, warehouse_ids["TS-HCM"], warehouse_ids["TS-Q7"], _lines(product_ids, (("TS-MOUSE-RAPOO-M20", "1"),)), DocumentStatus.DRAFT)
    _ensure_transfer(session, admin, warehouse_ids["TS-HCM"], warehouse_ids["TS-TD"], _lines(product_ids, (("TS-HEAD-LOGI-H390", "1"),)), DocumentStatus.CANCELLED)

    exports = (
        ("TS-Q7", (("TS-MOUSE-M331", "8"),)),
        ("TS-Q7", (("TS-TOOL-STAPLER-10", "20"),)),
        ("TS-TD", (("TS-MON-DELL-P2422H", "2"), ("TS-SSD-KINGSTON-NV2", "3"))),
        ("TS-TD", (("TS-TOOL-STAPLES-10", "15"),)),
        ("TS-HCM", (("TS-LAP-DELL-3530", "1"), ("TS-PAPER-PAPERONE", "10"))),
    )
    for warehouse_code, rows in exports:
        _ensure_export(session, admin, warehouse_ids[warehouse_code], _lines(product_ids, rows), DocumentStatus.CONFIRMED)
    _ensure_export(session, admin, warehouse_ids["TS-HCM"], _lines(product_ids, (("TS-MOUSE-G102", "1"),)), DocumentStatus.DRAFT)
    _ensure_export(session, admin, warehouse_ids["TS-HCM"], _lines(product_ids, (("TS-MOUSE-RAPOO-M20", "1"),)), DocumentStatus.CANCELLED)

    _ensure_adjustment(session, admin, warehouse_ids["TS-Q7"], product_ids["TS-MOUSE-G102"], "2", "TechStation demo: stock count surplus")
    _ensure_adjustment(session, admin, warehouse_ids["TS-HCM"], product_ids["TS-MON-LG-24MP400"], "-1", "TechStation demo: stock count shortage")

    thresholds = (
        ("TS-Q7", "TS-MOUSE-M331", "8"),
        ("TS-Q7", "TS-TOOL-STAPLER-10", "5"),
        ("TS-TD", "TS-TOOL-STAPLES-10", "30"),
    )
    for warehouse_code, sku, minimum in thresholds:
        batch7.set_threshold(session, warehouse_ids[warehouse_code], product_ids[sku], ThresholdUpdate(min_quantity=Decimal(minimum)))

    alerts = batch7.alerts(session, None)
    out_of_stock = sum(item.quantity == 0 for item in alerts)
    return SeedSummary(
        warehouses=len(warehouses), categories=len(categories), units=len(units), suppliers=len(suppliers), products=len(products),
        imports_confirmed=len(imports), exports_confirmed=len(exports), transfers_confirmed=len(transfers), adjustments=2,
        low_stock_alerts=len(alerts), out_of_stock_alerts=out_of_stock,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed TechStation Distribution demo data without creating users.")
    parser.add_argument("--admin-username", required=True, help="Existing active ADMIN username used to create demo transactions.")
    args = parser.parse_args()
    session = get_session_factory()()
    try:
        summary = seed_demo_data(session, args.admin_username)
        print(summary)
    finally:
        session.close()


if __name__ == "__main__":
    main()
