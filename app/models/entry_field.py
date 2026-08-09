from sqlalchemy import Column, String, Text, UUID, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class EntryField(Base):
    __tablename__ = "entry_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("entries.id"), nullable=False, index=True)
    field_key = Column(String(255), nullable=False, index=True)
    field_value = Column(Text, nullable=True)
    
    # Relationships
    entry = relationship("Entry", back_populates="entry_fields", foreign_keys=[entry_id])
