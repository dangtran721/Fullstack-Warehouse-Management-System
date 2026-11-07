import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.inventory import DocumentStatus, ExportOrderCreate, ExportOrderResponse, ImportOrderCreate, ImportOrderResponse, InventoryResponse
from app.services import inventory

router = APIRouter(tags=["inventory"])
DB = Annotated[Session, Depends(get_db)]
Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]

def error(exc: Exception) -> HTTPException:
    if isinstance(exc, inventory.NotFoundError): return HTTPException(404, "Resource not found.")
    if isinstance(exc, inventory.InsufficientStockError): return HTTPException(409, "Insufficient inventory.")
    if isinstance(exc, inventory.InvalidStateError): return HTTPException(409, "Order is not in draft status.")
    return HTTPException(409, "Resource is inactive or conflicts with current state.")

@router.get("/inventory", response_model=list[InventoryResponse])
def read_inventory(session: DB, current_user: CurrentUser, warehouse_id: uuid.UUID | None = None, product_id: uuid.UUID | None = None, search: str | None = None, skip: Skip = 0, limit: Limit = 20): return inventory.list_inventory(session, warehouse_id, product_id, search, skip, limit)

@router.post("/imports", response_model=ImportOrderResponse, status_code=201)
def create_import(data: ImportOrderCreate, session: DB, current_user: CurrentUser):
    try: return inventory.create_import(session, data, current_user)
    except (inventory.NotFoundError, inventory.ConflictError) as exc: raise error(exc) from exc
@router.get("/imports", response_model=list[ImportOrderResponse])
def read_imports(session: DB, current_user: CurrentUser, status: DocumentStatus | None = None, skip: Skip = 0, limit: Limit = 20): return inventory.list_imports(session, status, skip, limit)
@router.get("/imports/{order_id}", response_model=ImportOrderResponse)
def read_import(order_id: uuid.UUID, session: DB, current_user: CurrentUser):
    try: return inventory.get_import(session, order_id)
    except inventory.NotFoundError as exc: raise error(exc) from exc
@router.post("/imports/{order_id}/confirm", response_model=ImportOrderResponse)
def confirm_import(order_id: uuid.UUID, session: DB, current_user: CurrentUser):
    try: return inventory.confirm_import(session, order_id, current_user)
    except (inventory.NotFoundError, inventory.ConflictError, inventory.InvalidStateError) as exc: raise error(exc) from exc
@router.post("/imports/{order_id}/cancel", status_code=204)
def cancel_import(order_id: uuid.UUID, session: DB, current_user: CurrentUser):
    try: inventory.cancel_order(session, inventory.ImportOrder, order_id)
    except (inventory.NotFoundError, inventory.InvalidStateError) as exc: raise error(exc) from exc
    return Response(status_code=204)

@router.post("/exports", response_model=ExportOrderResponse, status_code=201)
def create_export(data: ExportOrderCreate, session: DB, current_user: CurrentUser):
    try: return inventory.create_export(session, data, current_user)
    except (inventory.NotFoundError, inventory.ConflictError) as exc: raise error(exc) from exc
@router.get("/exports", response_model=list[ExportOrderResponse])
def read_exports(session: DB, current_user: CurrentUser, status: DocumentStatus | None = None, skip: Skip = 0, limit: Limit = 20): return inventory.list_exports(session, status, skip, limit)
@router.get("/exports/{order_id}", response_model=ExportOrderResponse)
def read_export(order_id: uuid.UUID, session: DB, current_user: CurrentUser):
    try: return inventory.get_export(session, order_id)
    except inventory.NotFoundError as exc: raise error(exc) from exc
@router.post("/exports/{order_id}/confirm", response_model=ExportOrderResponse)
def confirm_export(order_id: uuid.UUID, session: DB, current_user: CurrentUser):
    try: return inventory.confirm_export(session, order_id, current_user)
    except (inventory.NotFoundError, inventory.ConflictError, inventory.InsufficientStockError, inventory.InvalidStateError) as exc: raise error(exc) from exc
@router.post("/exports/{order_id}/cancel", status_code=204)
def cancel_export(order_id: uuid.UUID, session: DB, current_user: CurrentUser):
    try: inventory.cancel_order(session, inventory.ExportOrder, order_id)
    except (inventory.NotFoundError, inventory.InvalidStateError) as exc: raise error(exc) from exc
    return Response(status_code=204)
