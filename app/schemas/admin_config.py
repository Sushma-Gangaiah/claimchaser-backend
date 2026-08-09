from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class AdminDropdownConfigBase(BaseModel):
    field_key: str
    label: str
    description: Optional[str] = None
    options: List[str] = []
    is_active: bool = True


class AdminDropdownConfigCreate(AdminDropdownConfigBase):
    pass


class AdminDropdownConfigUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    options: Optional[List[str]] = None
    is_active: Optional[bool] = None


class AdminDropdownConfigResponse(AdminDropdownConfigBase):
    model_config = {"from_attributes": True}

    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class AddOptionRequest(BaseModel):
    option: str


class RemoveOptionRequest(BaseModel):
    option: str
