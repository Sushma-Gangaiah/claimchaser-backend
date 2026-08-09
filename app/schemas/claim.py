from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from app.models import ClaimStatus, WorkStatus


class ClaimBase(BaseModel):
    claims_number: str
    account_number: str
    service_date: Optional[date] = None
    provider_name: Optional[str] = None
    payer_name: Optional[str] = None
    category: Optional[str] = None
    billed_amount: Optional[Decimal] = None
    balance_amount: Optional[Decimal] = None
    comments: Optional[str] = None


class ClaimCreate(ClaimBase):
    entry_id: UUID


class ClaimUpdate(BaseModel):
    provider_name: Optional[str] = None
    payer_name: Optional[str] = None
    category: Optional[str] = None
    comments: Optional[str] = None
    claim_status: Optional[ClaimStatus] = None
    action_task: Optional[str] = None
    assigned_user: Optional[str] = None
    escalation: Optional[bool] = None
    work_status: Optional[WorkStatus] = None


class ClaimResponse(ClaimBase):
    id: UUID
    entry_id: UUID
    claim_status: ClaimStatus
    action_task: Optional[str]
    worked_date: Optional[date]
    escalation: bool
    assigned_user: Optional[str]
    work_status: WorkStatus
    software: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
