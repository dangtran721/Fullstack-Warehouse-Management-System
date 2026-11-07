import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_roles
from app.db.session import get_db
from app.models.user import UserRole
from app.schemas.locations import SupplierCreate, SupplierResponse, SupplierUpdate, WarehouseCreate, WarehouseResponse, WarehouseUpdate
from app.services import locations
from app.services.catalog import ConflictError, NotFoundError


router = APIRouter(tags=["locations"])
SessionDependency = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[object, Depends(require_roles(UserRole.ADMIN))]
Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


def translate_error(error: Exception) -> HTTPException:
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=404, detail="Resource not found.")
    return HTTPException(status_code=409, detail="Resource already exists or is currently in use.")


@router.get("/warehouses", response_model=list[WarehouseResponse])
def read_warehouses(session: SessionDependency, current_user: CurrentUser, skip: Skip = 0, limit: Limit = 20, search: str | None = None, is_active: bool | None = None):
    return locations.list_warehouses(session, skip, limit, search, is_active)


@router.post("/warehouses", response_model=WarehouseResponse, status_code=201)
def create_warehouse(data: WarehouseCreate, session: SessionDependency, admin: AdminUser):
    try: return locations.create_warehouse(session, data)
    except ConflictError as error: raise translate_error(error) from error


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def read_warehouse(warehouse_id: uuid.UUID, session: SessionDependency, current_user: CurrentUser):
    try: return locations.get_warehouse(session, warehouse_id)
    except NotFoundError as error: raise translate_error(error) from error


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(warehouse_id: uuid.UUID, data: WarehouseUpdate, session: SessionDependency, admin: AdminUser):
    try: return locations.update_warehouse(session, warehouse_id, data)
    except (NotFoundError, ConflictError) as error: raise translate_error(error) from error


@router.delete("/warehouses/{warehouse_id}", status_code=204)
def delete_warehouse(warehouse_id: uuid.UUID, session: SessionDependency, admin: AdminUser) -> Response:
    try: locations.delete_warehouse(session, warehouse_id)
    except (NotFoundError, ConflictError) as error: raise translate_error(error) from error
    return Response(status_code=204)


@router.get("/suppliers", response_model=list[SupplierResponse])
def read_suppliers(session: SessionDependency, current_user: CurrentUser, skip: Skip = 0, limit: Limit = 20, search: str | None = None, is_active: bool | None = None):
    return locations.list_suppliers(session, skip, limit, search, is_active)


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
def create_supplier(data: SupplierCreate, session: SessionDependency, admin: AdminUser):
    try: return locations.create_supplier(session, data)
    except ConflictError as error: raise translate_error(error) from error


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
def read_supplier(supplier_id: uuid.UUID, session: SessionDependency, current_user: CurrentUser):
    try: return locations.get_supplier(session, supplier_id)
    except NotFoundError as error: raise translate_error(error) from error


@router.put("/suppliers/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: uuid.UUID, data: SupplierUpdate, session: SessionDependency, admin: AdminUser):
    try: return locations.update_supplier(session, supplier_id, data)
    except (NotFoundError, ConflictError) as error: raise translate_error(error) from error


@router.delete("/suppliers/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: uuid.UUID, session: SessionDependency, admin: AdminUser) -> Response:
    try: locations.delete_supplier(session, supplier_id)
    except (NotFoundError, ConflictError) as error: raise translate_error(error) from error
    return Response(status_code=204)
