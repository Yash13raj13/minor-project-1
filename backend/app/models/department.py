from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    contact_email = Column(String(120), nullable=True)
    sla_hours = Column(Integer, default=48)  # Target resolution SLA in hours
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    officers = relationship("User", back_populates="department")
    complaints = relationship("Complaint", back_populates="department")

