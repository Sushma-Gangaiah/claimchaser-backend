from pydantic import BaseModel, field_validator, field_serializer
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal


class EntryBase(BaseModel):
    # New field structure
    client_code: Optional[str] = None
    patient_name: Optional[str] = None
    date_of_service: Optional[str] = None
    provider_name: Optional[str] = None
    location: Optional[str] = None
    payer_name: Optional[str] = None
    insurance_type: Optional[str] = None
    insurance_payer_type: Optional[str] = None
    claim_type: Optional[str] = None
    charges: Optional[str] = None
    paid_by_payer: Optional[str] = None
    payer_control_num: Optional[str] = None
    claim_due: Optional[Decimal] = None
    claims_number: Optional[str] = None
    last_submission_date: Optional[str] = None
    follow_up_date: Optional[str] = None
    date_worked: Optional[str] = None
    comments: Optional[str] = None

    # Renamed fields
    status_code: Optional[str] = "Pending"
    sub_status_code: Optional[str] = None
    action_code: Optional[str] = None

    work_status: Optional[str] = "not_started"
    software: Optional[str] = None
    escalation: bool = False
    user_name: Optional[str] = None


class EntryCreate(EntryBase):
    is_draft: bool = True
    worked_date: Optional[str] = None

    @field_validator('worked_date', mode='before')
    @classmethod
    def parse_worked_date(cls, v):
        if v is None or v == '':
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, datetime):
            if v.tzinfo is not None:
                v = v.replace(tzinfo=None)
            return v.isoformat()
        return v


class EntryUpdate(BaseModel):
    client_code: Optional[str] = None
    patient_name: Optional[str] = None
    date_of_service: Optional[str] = None
    provider_name: Optional[str] = None
    location: Optional[str] = None
    payer_name: Optional[str] = None
    insurance_type: Optional[str] = None
    insurance_payer_type: Optional[str] = None
    claim_type: Optional[str] = None
    charges: Optional[str] = None
    paid_by_payer: Optional[str] = None
    payer_control_num: Optional[str] = None
    claim_due: Optional[Decimal] = None
    claims_number: Optional[str] = None
    last_submission_date: Optional[str] = None
    follow_up_date: Optional[str] = None
    date_worked: Optional[str] = None
    comments: Optional[str] = None
    status_code: Optional[str] = None
    sub_status_code: Optional[str] = None
    action_code: Optional[str] = None
    work_status: Optional[str] = None
    software: Optional[str] = None
    escalation: Optional[bool] = None
    is_draft: Optional[bool] = None


class EntryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    user_id: UUID
    user_name: str
    client_code: Optional[str] = None
    patient_name: Optional[str] = None
    date_of_service: Optional[date] = None
    provider_name: Optional[str] = None
    location: Optional[str] = None
    payer_name: Optional[str] = None
    insurance_type: Optional[str] = None
    insurance_payer_type: Optional[str] = None
    claim_type: Optional[str] = None
    charges: Optional[Decimal] = None
    paid_by_payer: Optional[Decimal] = None
    payer_control_num: Optional[str] = None
    claim_due: Optional[Decimal] = None
    claims_number: Optional[str] = None
    last_submission_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    date_worked: Optional[date] = None
    comments: Optional[str] = None
    status_code: str
    sub_status_code: Optional[str] = None
    action_code: Optional[str] = None
    work_status: str
    software: Optional[str] = None
    escalation: bool
    is_draft: bool
    worked_date: datetime
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer('charges', 'paid_by_payer', 'claim_due')
    def serialize_amount(self, value):
        if value is None:
            return None
        if isinstance(value, Decimal):
            return str(value)
        return str(value)

    @field_serializer('date_of_service', 'last_submission_date', 'follow_up_date', 'date_worked')
    def serialize_date(self, value):
        if value is None:
            return None
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    @field_serializer('worked_date', 'created_at', 'updated_at', 'submitted_at')
    def serialize_datetime(self, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
