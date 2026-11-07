import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator

from app.schemas.catalog import normalize_text


Code = Annotated[str, StringConstraints(min_length=1, max_length=32)]
Name = Annotated[str, StringConstraints(min_length=1, max_length=150)]
Phone = Annotated[str, StringConstraints(max_length=30)]
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 .()\-]{5,24}$")


def normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


class WarehouseCreate(BaseModel):
    code: Code
    name: Name
    address: Annotated[str | None, StringConstraints(max_length=500)] = None
    description: Annotated[str | None, StringConstraints(max_length=5000)] = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return normalize_text(value).upper()

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("address", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return normalize_optional(value)


class WarehouseUpdate(BaseModel):
    code: Code | None = None
    name: Name | None = None
    address: Annotated[str | None, StringConstraints(max_length=500)] = None
    description: Annotated[str | None, StringConstraints(max_length=5000)] = None
    is_active: bool | None = None

    _normalize_code = field_validator("code")(lambda value: normalize_text(value).upper() if value is not None else None)
    _normalize_name = field_validator("name")(lambda value: normalize_text(value) if value is not None else None)
    _normalize_optional_text = field_validator("address", "description")(normalize_optional)


class WarehouseResponse(WarehouseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SupplierCreate(BaseModel):
    code: Code
    name: Name
    contact_person: Annotated[str | None, StringConstraints(max_length=150)] = None
    email: EmailStr | None = None
    phone: Phone | None = None
    address: Annotated[str | None, StringConstraints(max_length=500)] = None
    description: Annotated[str | None, StringConstraints(max_length=5000)] = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return normalize_text(value).upper()

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return normalize_text(value)

    @field_validator("contact_person", "address", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return normalize_optional(value)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).lower() if value is not None else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        value = normalize_optional(value)
        if value is not None and not PHONE_PATTERN.fullmatch(value):
            raise ValueError("Phone number format is invalid.")
        return value


class SupplierUpdate(BaseModel):
    code: Code | None = None
    name: Name | None = None
    contact_person: Annotated[str | None, StringConstraints(max_length=150)] = None
    email: EmailStr | None = None
    phone: Phone | None = None
    address: Annotated[str | None, StringConstraints(max_length=500)] = None
    description: Annotated[str | None, StringConstraints(max_length=5000)] = None
    is_active: bool | None = None

    _normalize_code = field_validator("code")(lambda value: normalize_text(value).upper() if value is not None else None)
    _normalize_name = field_validator("name")(lambda value: normalize_text(value) if value is not None else None)
    _normalize_optional_text = field_validator("contact_person", "address", "description")(normalize_optional)
    _normalize_email = field_validator("email")(lambda value: str(value).lower() if value is not None else None)
    _validate_phone = field_validator("phone")(SupplierCreate.validate_phone)


class SupplierResponse(SupplierCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
