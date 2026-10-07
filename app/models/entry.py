from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UUID, Date, Numeric, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base


class Entry(Base):
    __tablename__ = "entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    user_name = Column(String(255), nullable=False)
    worked_date = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    submitted_at = Column(DateTime(timezone=False), nullable=True)

    # Updated field structure based on new requirements
    client_code = Column(String(255), nullable=True, index=True)
    patient_name = Column(String(255), nullable=True)
    date_of_service = Column(Date, nullable=True)
    provider_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    payer_name = Column(String(255), nullable=True)
    insurance_type = Column(String(255), nullable=True)
    insurance_payer_type = Column(String(255), nullable=True)
    claim_type = Column(String(255), nullable=True)
    charges = Column(Numeric(15, 2), nullable=True)
    paid_by_payer = Column(Numeric(15, 2), nullable=True)
    claim_due = Column(Numeric(15, 2), nullable=True)
    payer_control_num = Column(String(255), nullable=True)
    claims_number = Column(String(255), nullable=True)
    last_submission_date = Column(Date, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    date_worked = Column(Date, nullable=True)
    comments = Column(Text, nullable=True)

    # Renamed fields: status -> status_code, action_taken -> sub_status_code
    status_code = Column(String(255), default="Pending", nullable=False)
    sub_status_code = Column(String(255), nullable=True)
    action_code = Column(String(255), nullable=True)

    escalation = Column(Boolean, default=False)
    work_status = Column(String(50), default="not_started", nullable=False)
    software = Column(String(255), nullable=True)
    is_draft = Column(Boolean, default=True, nullable=False)
    submitted_at = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="entries", foreign_keys=[user_id])
    claims = relationship("Claim", back_populates="entry", cascade="all, delete-orphan")
    entry_fields = relationship("EntryField", back_populates="entry", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="entry", cascade="all, delete-orphan")
