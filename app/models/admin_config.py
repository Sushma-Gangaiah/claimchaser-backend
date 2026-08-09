from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base


class AdminDropdownConfig(Base):
    """
    Admin-managed dropdown configurations for various fields
    Supports: client_code, insurance_type, insurance_payer_type, claim_type, action_code
    """
    __tablename__ = "admin_dropdown_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_key = Column(String(255), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    options = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
