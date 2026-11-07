import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_roles
from app.db.session import get_db
from app.models.user import UserRole
from app.schemas.catalog import CategoryCreate, CategoryResponse, ProductCreate, ProductResponse, ProductUpdate, UnitCreate, UnitResponse
from app.services import catalog


router = APIRouter(tags=["catalog"])
SessionDependency = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[object, Depends(require_roles(UserRole.ADMIN))]
PaginationSkip = Annotated[int, Query(ge=0)]
PaginationLimit = Annotated[int, Query(ge=1, le=100)]


def translate_error(error: Exception) -> HTTPException:
    if isinstance(error, catalog.NotFoundError):
        return HTTPException(status_code=404, detail="Resource not found.")
    return HTTPException(status_code=409, detail="Resource already exists or is currently in use.")


@router.get("/categories", response_model=list[CategoryResponse])
def read_categories(session: SessionDependency, current_user: CurrentUser, skip: PaginationSkip = 0, limit: PaginationLimit = 20, search: str | None = None):
    return catalog.list_categories(session, skip, limit, search)


@router.post("/categories", response_model=CategoryResponse, status_code=201)
def create_category(data: CategoryCreate, session: SessionDependency, admin: AdminUser):
    try: return catalog.create_category(session, data)
    except catalog.ConflictError as error: raise translate_error(error) from error


@router.get("/categories/{category_id}", response_model=CategoryResponse)
def read_category(category_id: uuid.UUID, session: SessionDependency, current_user: CurrentUser):
    try: return catalog.get_category(session, category_id)
    except catalog.NotFoundError as error: raise translate_error(error) from error


@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: uuid.UUID, data: CategoryCreate, session: SessionDependency, admin: AdminUser):
    try: return catalog.update_category(session, category_id, data)
    except (catalog.NotFoundError, catalog.ConflictError) as error: raise translate_error(error) from error


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: uuid.UUID, session: SessionDependency, admin: AdminUser) -> Response:
    try: catalog.delete_category(session, category_id)
    except (catalog.NotFoundError, catalog.ConflictError) as error: raise translate_error(error) from error
    return Response(status_code=204)


@router.get("/units", response_model=list[UnitResponse])
def read_units(session: SessionDependency, current_user: CurrentUser, skip: PaginationSkip = 0, limit: PaginationLimit = 20, search: str | None = None):
    return catalog.list_units(session, skip, limit, search)


@router.post("/units", response_model=UnitResponse, status_code=201)
def create_unit(data: UnitCreate, session: SessionDependency, admin: AdminUser):
    try: return catalog.create_unit(session, data)
    except catalog.ConflictError as error: raise translate_error(error) from error


@router.get("/units/{unit_id}", response_model=UnitResponse)
def read_unit(unit_id: uuid.UUID, session: SessionDependency, current_user: CurrentUser):
    try: return catalog.get_unit(session, unit_id)
    except catalog.NotFoundError as error: raise translate_error(error) from error


@router.put("/units/{unit_id}", response_model=UnitResponse)
def update_unit(unit_id: uuid.UUID, data: UnitCreate, session: SessionDependency, admin: AdminUser):
    try: return catalog.update_unit(session, unit_id, data)
    except (catalog.NotFoundError, catalog.ConflictError) as error: raise translate_error(error) from error


@router.delete("/units/{unit_id}", status_code=204)
def delete_unit(unit_id: uuid.UUID, session: SessionDependency, admin: AdminUser) -> Response:
    try: catalog.delete_unit(session, unit_id)
    except (catalog.NotFoundError, catalog.ConflictError) as error: raise translate_error(error) from error
    return Response(status_code=204)


@router.get("/products", response_model=list[ProductResponse])
def read_products(session: SessionDependency, current_user: CurrentUser, skip: PaginationSkip = 0, limit: PaginationLimit = 20, search: str | None = None, category_id: uuid.UUID | None = None, is_active: bool | None = None):
    return catalog.list_products(session, skip, limit, search, category_id, is_active)


@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(data: ProductCreate, session: SessionDependency, admin: AdminUser):
    try: return catalog.create_product(session, data)
    except (catalog.NotFoundError, catalog.ConflictError) as error: raise translate_error(error) from error


@router.get("/products/{product_id}", response_model=ProductResponse)
def read_product(product_id: uuid.UUID, session: SessionDependency, current_user: CurrentUser):
    try: return catalog.get_product(session, product_id)
    except catalog.NotFoundError as error: raise translate_error(error) from error


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: uuid.UUID, data: ProductUpdate, session: SessionDependency, admin: AdminUser):
    try: return catalog.update_product(session, product_id, data)
    except (catalog.NotFoundError, catalog.ConflictError) as error: raise translate_error(error) from error


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: uuid.UUID, session: SessionDependency, admin: AdminUser) -> Response:
    try: catalog.delete_product(session, product_id)
    except (catalog.NotFoundError, catalog.ConflictError) as error: raise translate_error(error) from error
    return Response(status_code=204)
