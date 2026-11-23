"""
New database models for CivicLens hybrid AI pipeline:
  - ComplaintPrediction   : stores classifier output per complaint
  - IncidentCluster       : groups semantically duplicate complaints
  - IncidentReport        : links a complaint to a cluster
  - CorroborationRecord   : unique-reporter counts per cluster
  - PriorityHistory       : full priority score audit trail
  - SLARecord             : SLA deadlines and breach tracking
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class ComplaintPrediction(Base):
    """AI pipeline output for each complaint — versioned for model evaluation."""
    __tablename__ = "complaint_predictions"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)

    # Classification
    model_version = Column(String(80), default="zero-shot-mDeBERTa")
    language_detected = Column(String(20), nullable=True)
    category = Column(String(80), nullable=True)
    subcategory = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    method = Column(String(30), nullable=True)   # "finetuned" | "zero-shot" | "heuristic"

    # Incident attributes
    severity = Column(Integer, nullable=True)         # 0-5
    immediate_risk = Column(Integer, nullable=True)   # 0-5
    public_exposure = Column(Integer, nullable=True)  # 0-5
    evidence_quality = Column(Integer, nullable=True) # 0-5
    urgency_claim = Column(Boolean, default=False)
    incident_ongoing = Column(Boolean, default=False)
    hazard = Column(Boolean, default=False)
    hazard_type = Column(String(200), nullable=True)
    immediate_risk_flag = Column(Boolean, default=False)

    # Priority
    priority_score = Column(Float, nullable=True)
    priority_label = Column(String(20), nullable=True)
    safety_override = Column(Boolean, default=False)
    priority_explanation = Column(Text, nullable=True)
    priority_components = Column(JSON, nullable=True)   # {S, I, E, C, T}

    # Routing
    suggested_department_code = Column(String(20), nullable=True)
    secondary_department_code = Column(String(20), nullable=True)
    needs_manual_review = Column(Boolean, default=False)
    routing_reason = Column(Text, nullable=True)

    # Officer correction tracking
    officer_corrected = Column(Boolean, default=False)
    officer_corrected_category = Column(String(80), nullable=True)
    officer_corrected_priority = Column(String(20), nullable=True)
    corrected_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    corrected_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    complaint = relationship("Complaint", backref="prediction", foreign_keys=[complaint_id])


class IncidentCluster(Base):
    """Groups of complaints reporting the same physical incident."""
    __tablename__ = "incident_clusters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False)
    category = Column(String(80), nullable=True)
    priority = Column(String(20), nullable=True)
    status = Column(String(30), default="ACTIVE")
    unique_reporter_count = Column(Integer, default=1)
    total_report_count = Column(Integer, default=1)
    corroboration_score = Column(Float, default=2.0)
    # Representative coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    ward = Column(String(80), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reports = relationship("IncidentReport", back_populates="cluster", cascade="all, delete-orphan")
    corroboration = relationship("CorroborationRecord", back_populates="cluster", uselist=False, cascade="all, delete-orphan")


class IncidentReport(Base):
    """Links a complaint to an incident cluster."""
    __tablename__ = "incident_reports"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("incident_clusters.id"), nullable=False, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=True)
    is_anchor = Column(Boolean, default=False)   # First report in cluster
    created_at = Column(DateTime, default=datetime.utcnow)

    cluster = relationship("IncidentCluster", back_populates="reports")
    complaint = relationship("Complaint")


class CorroborationRecord(Base):
    """Independent reporter counts per incident cluster."""
    __tablename__ = "corroboration_records"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("incident_clusters.id"), unique=True, nullable=False, index=True)
    unique_user_count = Column(Integer, default=1)
    corroboration_score = Column(Float, default=2.0)
    # IP-hash fingerprints (hashed only, never raw)
    ip_hash_flags = Column(Integer, default=0)   # count of shared-IP signals (weak)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cluster = relationship("IncidentCluster", back_populates="corroboration")


class PriorityHistory(Base):
    """Full priority score audit trail with component breakdown."""
    __tablename__ = "priority_history"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    priority_before = Column(String(20), nullable=True)
    priority_after = Column(String(20), nullable=False)
    score_before = Column(Float, nullable=True)
    score_after = Column(Float, nullable=False)
    trigger = Column(String(80), nullable=True)   # "initial" | "corroboration_update" | "time_escalation" | "officer_override"
    components = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    complaint = relationship("Complaint")


class SLARecord(Base):
    """SLA deadline tracking and breach monitoring."""
    __tablename__ = "sla_records"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), unique=True, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    priority = Column(String(20), nullable=False)
    sla_deadline = Column(DateTime, nullable=False)
    sla_hours = Column(Integer, nullable=False)
    is_breached = Column(Boolean, default=False)
    breached_at = Column(DateTime, nullable=True)
    resolved_within_sla = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint")
    department = relationship("Department")

