import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


Name = Annotated[str, StringConstraints(min_length=1, max_length=100)]
ProductName = Annotated[str, StringConstraints(min_length=1, max_length=255)]


def normalize_text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("Value must not be empty.")
    return normalized


class CategoryCreate(BaseModel):
    name: Name

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return normalize_text(value).lower()


class CategoryUpdate(CategoryCreate):
    pass


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime


class UnitCreate(BaseModel):
    name: Name
    code: Annotated[str, StringConstraints(min_length=1, max_length=20)]

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return normalize_text(value).lower()

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return normalize_text(value).upper()


class UnitUpdate(UnitCreate):
    pass


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    code: str
    created_at: datetime
    updated_at: datetime


class ProductCreate(BaseModel):
    sku: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    name: ProductName
    description: Annotated[str | None, StringConstraints(max_length=5000)] = None
    category_id: uuid.UUID
    unit_id: uuid.UUID
    is_active: bool = True

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return normalize_text(value).upper()

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ProductUpdate(BaseModel):
    sku: Annotated[str | None, StringConstraints(min_length=1, max_length=64)] = None
    name: Annotated[str | None, StringConstraints(min_length=1, max_length=255)] = None
    description: Annotated[str | None, StringConstraints(max_length=5000)] = None
    category_id: uuid.UUID | None = None
    unit_id: uuid.UUID | None = None
    is_active: bool | None = None

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str | None) -> str | None:
        return normalize_text(value).upper() if value is not None else None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return normalize_text(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    sku: str
    name: str
    description: str | None
    category_id: uuid.UUID
    unit_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
