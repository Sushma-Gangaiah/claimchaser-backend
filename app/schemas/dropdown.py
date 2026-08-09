from pydantic import BaseModel
from typing import List
from uuid import UUID
from datetime import datetime


class DropdownOptionCreate(BaseModel):
    value: str


class DropdownConfigBase(BaseModel):
    field_key: str
    label: str
    options: List[str]
    is_required: bool = False


class DropdownConfigCreate(DropdownConfigBase):
    pass


class DropdownConfigUpdate(BaseModel):
    label: str | None = None
    options: List[str] | None = None
    is_required: bool | None = None


class DropdownConfigResponse(DropdownConfigBase):
    model_config = {"from_attributes": True}

    id: UUID
    created_by: UUID
    updated_at: datetime
