from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # e.g., "STATUS_CHANGE", "ASSIGNED_DEPARTMENT", "AI_DUPLICATE_FLAG"
    previous_state = Column(String(100), nullable=True)
    new_state = Column(String(100), nullable=True)
    remarks = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    complaint = relationship("Complaint", back_populates="audit_logs")
    performer = relationship("User", back_populates="audit_actions")

