import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.inventory import DocumentStatus, MovementType


Quantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=3)]


class OrderLineCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Quantity


class ImportOrderCreate(BaseModel):
    warehouse_id: uuid.UUID
    supplier_id: uuid.UUID
    lines: list[OrderLineCreate] = Field(min_length=1)


class ExportOrderCreate(BaseModel):
    warehouse_id: uuid.UUID
    lines: list[OrderLineCreate] = Field(min_length=1)


class OrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal


class ImportOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    warehouse_id: uuid.UUID
    supplier_id: uuid.UUID
    status: DocumentStatus
    created_by_id: uuid.UUID
    confirmed_by_id: uuid.UUID | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    lines: list[OrderLineResponse]


class ExportOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    warehouse_id: uuid.UUID
    status: DocumentStatus
    created_by_id: uuid.UUID
    confirmed_by_id: uuid.UUID | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    lines: list[OrderLineResponse]


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    min_quantity: Decimal | None
    updated_at: datetime

class TransferCreate(BaseModel):
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    lines: list[OrderLineCreate] = Field(min_length=1)

class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    status: DocumentStatus
    lines: list[OrderLineResponse]

class AdjustmentCreate(BaseModel):
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    quantity_delta: Annotated[Decimal, Field(max_digits=18, decimal_places=3)]
    reason: Annotated[str, Field(min_length=1, max_length=1000)]

    @field_validator("quantity_delta")
    @classmethod
    def nonzero_delta(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("Quantity adjustment must not be zero.")
        return value

class ThresholdUpdate(BaseModel):
    min_quantity: Annotated[Decimal | None, Field(ge=0, max_digits=18, decimal_places=3)] = None


class MovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    movement_type: MovementType
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    quantity_delta: Decimal
    import_order_id: uuid.UUID | None
    export_order_id: uuid.UUID | None
    performed_by_id: uuid.UUID
    created_at: datetime
