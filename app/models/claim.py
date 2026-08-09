from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey, UUID, Date, Numeric, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base
import enum


class ClaimStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class WorkStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("entries.id"), nullable=False, index=True)
    claims_number = Column(String(255), unique=True, nullable=False, index=True)
    account_number = Column(String(255), nullable=False, index=True)
    service_date = Column(Date, nullable=True)
    provider_name = Column(String(255), nullable=True)
    payer_name = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    billed_amount = Column(Numeric(15, 2), nullable=True)
    balance_amount = Column(Numeric(15, 2), nullable=True)
    comments = Column(Text, nullable=True)
    claim_status = Column(SQLEnum(ClaimStatus), default=ClaimStatus.NEW, nullable=False, index=True)
    action_task = Column(String(255), nullable=True)
    worked_date = Column(Date, nullable=True)
    escalation = Column(Boolean, default=False)
    assigned_user = Column(String(255), nullable=True, index=True)
    work_status = Column(SQLEnum(WorkStatus), default=WorkStatus.PENDING, nullable=False)
    software = Column(String(255), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    entry = relationship("Entry", back_populates="claims", foreign_keys=[entry_id])
