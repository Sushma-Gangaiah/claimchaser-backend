from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base


class DropdownConfig(Base):
    __tablename__ = "dropdown_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_key = Column(String(255), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=False)
    options = Column(JSON, nullable=False, default=list)
    is_required = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    created_by_user = relationship("User", back_populates="dropdown_configs", foreign_keys=[created_by])
