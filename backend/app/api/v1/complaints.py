from datetime import datetime
import random
import string
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_officer, get_current_user, get_db
from app.models.audit_log import AuditLog
from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus
from app.models.department import Department
from app.models.feedback import ComplaintFeedback
from app.models.user import User, UserRole
from app.schemas.audit_log import AuditLogResponse
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintUpdate,
    StatusUpdate,
)
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.services.classifier import classifier_service
from app.services.duplicate_finder import duplicate_service
from app.services.routing import routing_service

router = APIRouter(prefix="/complaints", tags=["Complaints"])


def generate_tracking_number() -> str:
    year = datetime.utcnow().year
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"CVL-{year}-{random_str}"


@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def file_complaint(
    complaint_in: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tracking_num = generate_tracking_number()

    # 1. AI Classification & Priority Scoring
    ai_result = classifier_service.classify(
        title=complaint_in.title,
        description=complaint_in.description,
    )

    category = complaint_in.category if complaint_in.category and complaint_in.category != "General" else ai_result["category"]
    priority_enum = ComplaintPriority[ai_result["priority"]]

    # 2. Intelligent Department Routing
    dept_id = complaint_in.department_id
    if not dept_id:
        target_dept = routing_service.resolve_department(
            db,
            suggested_code=ai_result["suggested_department_code"],
            category=category,
        )
        if target_dept:
            dept_id = target_dept.id

    # 3. Semantic Duplicate Detection via FAISS
    duplicates = duplicate_service.find_duplicates(
        title=complaint_in.title,
        description=complaint_in.description,
        top_k=1,
        similarity_threshold=0.80,
    )

    is_duplicate = False
    duplicate_of_id = None
    similarity_score = None

    if duplicates:
        is_duplicate = True
        duplicate_of_id = duplicates[0]["complaint_id"]
        similarity_score = duplicates[0]["similarity_score"]

    initial_status = ComplaintStatus.DUPLICATE if (is_duplicate and not complaint_in.force_submit_duplicate) else ComplaintStatus.SUBMITTED

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
        ai_category=ai_result["category"],
        ai_confidence=ai_result["confidence"],
        ai_priority_score=ai_result["priority_score"],
        is_duplicate=is_duplicate,
        duplicate_of_id=duplicate_of_id,
        similarity_score=similarity_score,
    )
    db.add(complaint)
    db.flush()

    # Register into FAISS index for subsequent vector searches
    duplicate_service.add_complaint(complaint.id, complaint.title, complaint.description)

    # Record initial audit entry
    audit_remarks = f"Complaint filed. AI categorized as '{category}' ({int(ai_result['confidence']*100)}% conf) with {priority_enum.value} priority."
    if is_duplicate:
        audit_remarks += f" Flagged as duplicate of Complaint #{duplicate_of_id} (Similarity: {int(similarity_score * 100)}%)."

    audit = AuditLog(
        complaint_id=complaint.id,
        performed_by_id=current_user.id,
        action="AI_TRIAGED_AND_FILED",
        previous_state=None,
        new_state=initial_status.value,
        remarks=audit_remarks,
    )
    db.add(audit)
    db.commit()
    db.refresh(complaint)
    return complaint


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
        .options(
            joinedload(Complaint.citizen),
            joinedload(Complaint.department),
        )
        .order_by(Complaint.created_at.desc())
    )

    # If regular citizen and requested citizen_only, or citizen viewing list
    if current_user.role == UserRole.CITIZEN or citizen_only:
        query = query.filter(Complaint.citizen_id == current_user.id)
    elif current_user.role == UserRole.OFFICER and current_user.department_id:
        # Officer defaults to seeing complaints in their department unless filtered
        if not department_id:
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
            (Complaint.title.ilike(f"%{search}%"))
            | (Complaint.description.ilike(f"%{search}%"))
            | (Complaint.tracking_number.ilike(f"%{search}%"))
        )

    return query.offset(skip).limit(limit).all()


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = (
        db.query(Complaint)
        .options(
            joinedload(Complaint.citizen),
            joinedload(Complaint.department),
        )
        .filter(Complaint.id == complaint_id)
        .first()
    )
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # If citizen, ensure ownership
    if current_user.role == UserRole.CITIZEN and complaint.citizen_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You do not have access to view this complaint"
        )
    return complaint


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

    audit = AuditLog(
        complaint_id=complaint.id,
        performed_by_id=officer.id,
        action="STATUS_CHANGE",
        previous_state=old_status,
        new_state=status_in.status.value,
        remarks=status_in.remarks,
    )
    db.add(audit)
    db.commit()
    db.refresh(complaint)
    return complaint


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
        complaint.priority = update_in.priority

    audit = AuditLog(
        complaint_id=complaint.id,
        performed_by_id=officer.id,
        action="REASSIGNMENT_OR_UPDATE",
        previous_state=complaint.status.value,
        new_state=complaint.status.value,
        remarks=update_in.remarks or "Officer updated assignment or priority details",
    )
    db.add(audit)
    db.commit()
    db.refresh(complaint)
    return complaint


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
        raise HTTPException(status_code=400, detail="Feedback can only be submitted after resolution")

    existing_fb = db.query(ComplaintFeedback).filter(ComplaintFeedback.complaint_id == complaint_id).first()
    if existing_fb:
        existing_fb.rating = feedback_in.rating
        existing_fb.comment = feedback_in.comment
        db.commit()
        db.refresh(existing_fb)
        return existing_fb

    feedback = ComplaintFeedback(
        complaint_id=complaint_id,
        citizen_id=current_user.id,
        rating=feedback_in.rating,
        comment=feedback_in.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback

