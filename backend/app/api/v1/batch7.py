import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.api.deps import CurrentUser, require_roles
from app.db.session import get_db
from app.models.user import UserRole
from app.schemas.inventory import AdjustmentCreate, DocumentStatus, InventoryResponse, MovementResponse, ThresholdUpdate, TransferCreate, TransferResponse
from app.models.inventory import MovementType
from app.services import batch7
from app.services.inventory import InsufficientStockError, InvalidStateError
from app.services.catalog import ConflictError, NotFoundError
router=APIRouter(tags=["inventory operations"]); DB=Annotated[Session,Depends(get_db)]; Admin=Annotated[object,Depends(require_roles(UserRole.ADMIN))]
def err(e): return HTTPException(404,"Resource not found.") if isinstance(e,NotFoundError) else HTTPException(409,"Invalid inventory operation.")
@router.post('/transfers',response_model=TransferResponse,status_code=201)
def create(data:TransferCreate,session:DB,user:CurrentUser):
 try:return batch7.create_transfer(session,data,user)
 except (NotFoundError,ConflictError) as e:raise err(e) from e
@router.get('/transfers',response_model=list[TransferResponse])
def list_transfers(session: DB, user: CurrentUser, status: DocumentStatus | None = None, warehouse_id: uuid.UUID | None = None, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
 return batch7.list_transfers(session,status,warehouse_id,skip,limit)
@router.get('/transfers/{order_id}',response_model=TransferResponse)
def get(order_id:uuid.UUID,session:DB,user:CurrentUser):
 try:return batch7.get_transfer(session,order_id)
 except NotFoundError as e:raise err(e) from e
@router.post('/transfers/{order_id}/confirm',response_model=TransferResponse)
def confirm(order_id:uuid.UUID,session:DB,user:CurrentUser):
 try:return batch7.confirm_transfer(session,order_id,user)
 except (NotFoundError,ConflictError,InsufficientStockError,InvalidStateError) as e:raise err(e) from e
@router.post('/transfers/{order_id}/cancel',status_code=204)
def cancel(order_id:uuid.UUID,session:DB,user:CurrentUser):
 try:batch7.cancel_transfer(session,order_id)
 except (NotFoundError,InvalidStateError) as e:raise err(e) from e
 return Response(status_code=204)
@router.post('/adjustments',status_code=201)
def adjustment(data:AdjustmentCreate,session:DB,admin:Admin,user:CurrentUser):
 try:return batch7.adjust(session,data,user)
 except (NotFoundError,ConflictError,InsufficientStockError) as e:raise err(e) from e
@router.get('/inventory-movements',response_model=list[MovementResponse])
def list_movements(session: DB, user: CurrentUser, warehouse_id: uuid.UUID | None = None, product_id: uuid.UUID | None = None, movement_type: MovementType | None = None, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
 return batch7.list_movements(session,warehouse_id,product_id,movement_type,skip,limit)
@router.put('/inventory/{warehouse_id}/{product_id}/threshold',response_model=InventoryResponse)
def threshold(warehouse_id:uuid.UUID,product_id:uuid.UUID,data:ThresholdUpdate,session:DB,admin:Admin): return batch7.set_threshold(session,warehouse_id,product_id,data)
@router.get('/alerts/low-stock',response_model=list[InventoryResponse])
def alerts(session:DB,user:CurrentUser,warehouse_id:uuid.UUID|None=None):return batch7.alerts(session,warehouse_id)
