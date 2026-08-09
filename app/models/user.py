from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    invitation_token = Column(String(255), nullable=True, index=True)
    invitation_expires = Column(DateTime, nullable=True)
    password_set = Column(Boolean, default=False, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    entries = relationship("Entry", back_populates="user", foreign_keys="Entry.user_id")
    creator = relationship(
        "User",
        remote_side="User.id",
        back_populates="created_users",
        foreign_keys="User.created_by"
    )
    created_users = relationship("User", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="user", foreign_keys="AuditLog.user_id")
    dropdown_configs = relationship("DropdownConfig", back_populates="created_by_user")
