"""
CivicLens — Full AI Pipeline complaint filing endpoint.

Implements all 6 stages:
  1. Preprocessing (language detection, normalisation)
  2. Classification (category, subcategory, incident attributes)
  3. Priority scoring (weighted formula + safety override)
  4. Duplicate detection (FAISS semantic search + contextual verification)
  5. Corroboration (independent reporter counting)
  6. Routing & SLA (rule-based department assignment + deadline)
"""
from datetime import datetime
import hashlib
import random
import string
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_officer, get_current_user, get_db
from app.models.ai_models import (
    ComplaintPrediction, CorroborationRecord, IncidentCluster,
    IncidentReport, PriorityHistory, SLARecord,
)
from app.models.audit_log import AuditLog
from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus
from app.models.feedback import ComplaintFeedback
from app.models.user import User, UserRole
from app.schemas.audit_log import AuditLogResponse
from app.schemas.complaint import (
    ComplaintCreate, ComplaintResponse, ComplaintUpdate, StatusUpdate,
)
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.services.classifier import classifier_service, priority_engine
from app.services.duplicate_finder import duplicate_service, corroboration_engine
from app.services.preprocessor import preprocessor
from app.services.routing import routing_service

router = APIRouter(prefix="/complaints", tags=["Complaints"])


def generate_tracking_number() -> str:
    year = datetime.utcnow().year
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"CVL-{year}-{rand}"


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# POST /complaints/ — Full AI-pipeline complaint submission
# ---------------------------------------------------------------------------

@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def file_complaint(
    complaint_in: ComplaintCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tracking_num = generate_tracking_number()
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = _hash_ip(client_ip)

    # ------------------------------------------------------------------ #
    # Stage 1: Preprocessing                                              #
    # ------------------------------------------------------------------ #
    preprocessed = preprocessor.preprocess(
        f"{complaint_in.title}. {complaint_in.description}"
    )
    language = preprocessed["language"]

    # ------------------------------------------------------------------ #
    # Stage 2: Classification (uses original_text for transformer)        #
    # ------------------------------------------------------------------ #
    clf = classifier_service.classify(
        title=complaint_in.title,
        description=complaint_in.description,
        language=language,
    )
    category = (
        complaint_in.category
        if complaint_in.category and complaint_in.category not in ("General", "")
        else clf["category"]
    )

    # ------------------------------------------------------------------ #
    # Stage 4: Semantic Duplicate Detection via FAISS                     #
    # ------------------------------------------------------------------ #
    dup_matches = duplicate_service.find_duplicates(
        title=complaint_in.title,
        description=complaint_in.description,
        top_k=3,
        similarity_threshold=0.80,
        latitude=complaint_in.latitude,
        longitude=complaint_in.longitude,
        category=category,
    )
    is_duplicate = len(dup_matches) > 0
    duplicate_of_id = dup_matches[0]["complaint_id"] if is_duplicate else None
    similarity_score = dup_matches[0]["similarity_score"] if is_duplicate else None

    # ------------------------------------------------------------------ #
    # Stage 5: Corroboration (count unique reporters for matched cluster)  #
    # ------------------------------------------------------------------ #
    unique_users = 1  # This report is from a new user (assume independent)
    if is_duplicate and duplicate_of_id:
        # Find the incident cluster for the duplicate
        parent_report = db.query(IncidentReport).filter(
            IncidentReport.complaint_id == duplicate_of_id
        ).first()
        if parent_report:
            cluster = db.query(IncidentCluster).filter(
                IncidentCluster.id == parent_report.cluster_id
            ).first()
            if cluster:
                unique_users = cluster.unique_reporter_count + 1

    C_corr = corroboration_engine.corroboration_score(unique_users)

    # ------------------------------------------------------------------ #
    # Stage 3: Priority Scoring                                           #
    # ------------------------------------------------------------------ #
    prio_result = priority_engine.compute_full_priority(
        title=complaint_in.title,
        description=complaint_in.description,
        hazard=clf["hazard"],
        hazard_type=clf["hazard_type"],
        corroboration_score=C_corr,
        time_pending_days=0.0,
    )
    priority_enum = ComplaintPriority[prio_result["priority"]]

    # ------------------------------------------------------------------ #
    # Stage 6: Department Routing & SLA                                   #
    # ------------------------------------------------------------------ #
    routing = routing_service.resolve_department(
        db=db,
        category=category,
        confidence=clf["confidence"],
        suggested_code=clf["suggested_department_code"],
    )
    dept_id = complaint_in.department_id or (
        routing["department"].id if routing["department"] else None
    )
    target_dept = routing["department"]

    # Initial status
    if is_duplicate and not complaint_in.force_submit_duplicate:
        initial_status = ComplaintStatus.DUPLICATE
    elif routing["needs_manual_review"]:
        initial_status = ComplaintStatus.UNDER_REVIEW
    else:
        initial_status = ComplaintStatus.SUBMITTED

    # ------------------------------------------------------------------ #
    # Persist complaint                                                   #
    # ------------------------------------------------------------------ #
    complaint = Complaint(
        tracking_number=tracking_num,
        title=complaint_in.title,
        description=complaint_in.description,
        category=category,
        priority=priority_enum,
        status=initial_status,
        latitude=complaint_in.latitude,
        longitude=complaint_in.longitude,
        address=complaint_in.address,
        ward=complaint_in.ward,
        image_url=complaint_in.image_url,
        citizen_id=current_user.id,
        department_id=dept_id,
        ai_category=clf["category"],
        ai_confidence=clf["confidence"],
        ai_priority_score=prio_result["priority_score"],
        is_duplicate=is_duplicate,
        duplicate_of_id=duplicate_of_id,
        similarity_score=similarity_score,
    )
    db.add(complaint)
    db.flush()

    # ------------------------------------------------------------------ #
    # Persist AI Prediction record                                        #
    # ------------------------------------------------------------------ #
    attrs = prio_result.get("attributes", {})
    prediction = ComplaintPrediction(
        complaint_id=complaint.id,
        language_detected=language,
        category=clf["category"],
        subcategory=clf.get("subcategory"),
        confidence=clf["confidence"],
        severity=attrs.get("severity"),
        immediate_risk=attrs.get("immediate_risk"),
        public_exposure=attrs.get("public_exposure"),
        evidence_quality=attrs.get("evidence_quality"),
        urgency_claim=attrs.get("urgency_claim", False),
        incident_ongoing=attrs.get("incident_ongoing", False),
        hazard=clf["hazard"],
        hazard_type=clf.get("hazard_type"),
        immediate_risk_flag=clf.get("immediate_risk", False),
        priority_score=prio_result["priority_score"],
        priority_label=prio_result["priority"],
        safety_override=prio_result.get("safety_override", False),
        priority_explanation=prio_result.get("explanation"),
        priority_components=prio_result.get("components"),
        suggested_department_code=clf["suggested_department_code"],
        secondary_department_code=clf.get("secondary_department_code"),
        needs_manual_review=routing["needs_manual_review"],
        routing_reason=routing["reason"],
    )
    db.add(prediction)

    # ------------------------------------------------------------------ #
    # Priority history                                                    #
    # ------------------------------------------------------------------ #
    ph = PriorityHistory(
        complaint_id=complaint.id,
        priority_before=None,
        priority_after=prio_result["priority"],
        score_before=None,
        score_after=prio_result["priority_score"],
        trigger="initial",
        components=prio_result.get("components"),
        explanation=prio_result.get("explanation"),
        performed_by_id=None,
    )
    db.add(ph)

    # ------------------------------------------------------------------ #
    # SLA record                                                          #
    # ------------------------------------------------------------------ #
    sla_deadline = routing_service.calculate_sla_deadline(target_dept, priority_enum)
    sla = SLARecord(
        complaint_id=complaint.id,
        department_id=dept_id,
        priority=priority_enum.value,
        sla_deadline=sla_deadline,
        sla_hours=target_dept.sla_hours if target_dept else 48,
    )
    db.add(sla)

    # ------------------------------------------------------------------ #
    # Incident cluster management                                         #
    # ------------------------------------------------------------------ #
    if is_duplicate and duplicate_of_id:
        # Find parent cluster and add this report
        parent_report = db.query(IncidentReport).filter(
            IncidentReport.complaint_id == duplicate_of_id
        ).first()
        cluster_id = parent_report.cluster_id if parent_report else None

        if cluster_id:
            cluster = db.query(IncidentCluster).filter(IncidentCluster.id == cluster_id).first()
            if cluster:
                cluster.total_report_count += 1
                cluster.unique_reporter_count += 1  # Assume distinct user (IP checked separately)
                cluster.corroboration_score = corroboration_engine.corroboration_score(
                    cluster.unique_reporter_count
                )
                db.add(IncidentReport(
                    cluster_id=cluster_id,
                    complaint_id=complaint.id,
                    similarity_score=similarity_score,
                    is_anchor=False,
                ))
    else:
        # Create a new cluster for this complaint
        cluster = IncidentCluster(
            title=complaint_in.title,
            category=category,
            priority=priority_enum.value,
            unique_reporter_count=1,
            total_report_count=1,
            corroboration_score=C_corr,
            latitude=complaint_in.latitude,
            longitude=complaint_in.longitude,
            ward=complaint_in.ward,
        )
        db.add(cluster)
        db.flush()
        db.add(IncidentReport(
            cluster_id=cluster.id,
            complaint_id=complaint.id,
            similarity_score=1.0,
            is_anchor=True,
        ))

    # ------------------------------------------------------------------ #
    # Audit log                                                           #
    # ------------------------------------------------------------------ #
    dup_note = f" Flagged as duplicate of #{duplicate_of_id} ({int(similarity_score * 100)}% similarity)." if is_duplicate else ""
    safety_note = f" ⚠ Safety override: {clf.get('hazard_type')}." if clf["hazard"] else ""
    audit_remarks = (
        f"Filed via CivicLens Portal. "
        f"Language: {language}. "
        f"AI: '{clf['category']}' ({int(clf['confidence'] * 100)}% conf), "
        f"Priority: {prio_result['priority']} (score={prio_result['priority_score']})."
        f"{safety_note}{dup_note} "
        f"Routing: {routing['reason']}."
    )
    db.add(AuditLog(
        complaint_id=complaint.id,
        performed_by_id=current_user.id,
        action="AI_TRIAGED_AND_FILED",
        previous_state=None,
        new_state=initial_status.value,
        remarks=audit_remarks,
    ))

    # Register into FAISS for future duplicate detection
    db.commit()
    duplicate_service.add_complaint(
        complaint.id, complaint.title, complaint.description,
        complaint.latitude, complaint.longitude, complaint.category,
        complaint.created_at.isoformat() if complaint.created_at else None,
    )
    db.refresh(complaint)
    return complaint


# ---------------------------------------------------------------------------
# GET /complaints/
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[ComplaintResponse])
def list_complaints(
    status: Optional[ComplaintStatus] = None,
    priority: Optional[ComplaintPriority] = None,
    department_id: Optional[int] = None,
    ward: Optional[str] = None,
    search: Optional[str] = None,
    citizen_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Complaint)
        .options(joinedload(Complaint.citizen), joinedload(Complaint.department))
        .order_by(Complaint.created_at.desc())
    )

    if current_user.role == UserRole.CITIZEN or citizen_only:
        query = query.filter(Complaint.citizen_id == current_user.id)
    elif current_user.role == UserRole.OFFICER and current_user.department_id and not department_id:
        query = query.filter(Complaint.department_id == current_user.department_id)

    if status:
        query = query.filter(Complaint.status == status)
    if priority:
        query = query.filter(Complaint.priority == priority)
    if department_id:
        query = query.filter(Complaint.department_id == department_id)
    if ward:
        query = query.filter(Complaint.ward == ward)
    if search:
        query = query.filter(
            Complaint.title.ilike(f"%{search}%")
            | Complaint.description.ilike(f"%{search}%")
            | Complaint.tracking_number.ilike(f"%{search}%")
        )
    return query.offset(skip).limit(limit).all()


# ---------------------------------------------------------------------------
# GET /complaints/{id}
# ---------------------------------------------------------------------------

@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = (
        db.query(Complaint)
        .options(joinedload(Complaint.citizen), joinedload(Complaint.department))
        .filter(Complaint.id == complaint_id)
        .first()
    )
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if current_user.role == UserRole.CITIZEN and complaint.citizen_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return complaint


# ---------------------------------------------------------------------------
# PATCH /complaints/{id}/status
# ---------------------------------------------------------------------------

@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
def update_complaint_status(
    complaint_id: int,
    status_in: StatusUpdate,
    db: Session = Depends(get_db),
    officer: User = Depends(get_current_active_officer),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    old_status = complaint.status.value
    complaint.status = status_in.status
    if status_in.status == ComplaintStatus.RESOLVED:
        complaint.resolved_at = datetime.utcnow()
        # Mark SLA record
        sla = db.query(SLARecord).filter(SLARecord.complaint_id == complaint_id).first()
        if sla:
            sla.resolved_within_sla = complaint.resolved_at <= sla.sla_deadline
            sla.is_breached = not sla.resolved_within_sla

    db.add(AuditLog(
        complaint_id=complaint.id,
        performed_by_id=officer.id,
        action="STATUS_CHANGE",
        previous_state=old_status,
        new_state=status_in.status.value,
        remarks=status_in.remarks or f"Status updated to {status_in.status.value}",
    ))
    db.commit()
    db.refresh(complaint)
    return complaint


# ---------------------------------------------------------------------------
# PATCH /complaints/{id}/assign
# ---------------------------------------------------------------------------

@router.patch("/{complaint_id}/assign", response_model=ComplaintResponse)
def assign_complaint(
    complaint_id: int,
    update_in: ComplaintUpdate,
    db: Session = Depends(get_db),
    officer: User = Depends(get_current_active_officer),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if update_in.department_id is not None:
        complaint.department_id = update_in.department_id
    if update_in.assigned_officer_id is not None:
        complaint.assigned_officer_id = update_in.assigned_officer_id
    if update_in.priority is not None:
        old_priority = complaint.priority.value if complaint.priority else None
        complaint.priority = update_in.priority
        # Log priority change
        db.add(PriorityHistory(
            complaint_id=complaint.id,
            priority_before=old_priority,
            priority_after=update_in.priority.value,
            score_before=complaint.ai_priority_score,
            score_after=complaint.ai_priority_score,
            trigger="officer_override",
            explanation=update_in.remarks or "Officer manually adjusted priority",
            performed_by_id=officer.id,
        ))

    db.add(AuditLog(
        complaint_id=complaint.id,
        performed_by_id=officer.id,
        action="REASSIGNMENT_OR_UPDATE",
        previous_state=complaint.status.value,
        new_state=complaint.status.value,
        remarks=update_in.remarks or "Officer updated assignment/priority",
    ))
    db.commit()
    db.refresh(complaint)
    return complaint


# ---------------------------------------------------------------------------
# GET /complaints/{id}/audit
# ---------------------------------------------------------------------------

@router.get("/{complaint_id}/audit", response_model=List[AuditLogResponse])
def get_complaint_audit_trail(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(AuditLog)
        .filter(AuditLog.complaint_id == complaint_id)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# POST /complaints/{id}/feedback
# ---------------------------------------------------------------------------

@router.post("/{complaint_id}/feedback", response_model=FeedbackResponse)
def submit_feedback(
    complaint_id: int,
    feedback_in: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.citizen_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only complaint author can provide feedback")
    if complaint.status != ComplaintStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Feedback only available after resolution")

    existing = db.query(ComplaintFeedback).filter(ComplaintFeedback.complaint_id == complaint_id).first()
    if existing:
        existing.rating = feedback_in.rating
        existing.comment = feedback_in.comment
        db.commit()
        db.refresh(existing)
        return existing

    fb = ComplaintFeedback(complaint_id=complaint_id, citizen_id=current_user.id,
                           rating=feedback_in.rating, comment=feedback_in.comment)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb
