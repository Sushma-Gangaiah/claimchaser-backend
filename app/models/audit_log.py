from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("entries.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String(255), nullable=False)
    snapshot = Column(JSON, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    entry = relationship("Entry", back_populates="audit_logs", foreign_keys=[entry_id])
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
