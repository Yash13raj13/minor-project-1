from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_admin, get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.models.user import User
from app.schemas.complaint import DuplicateCandidate, DuplicateCheckResponse
from app.services.classifier import classifier_service
from app.services.duplicate_finder import duplicate_service

router = APIRouter(prefix="/ai", tags=["AI & Intelligence Services"])


class ClassifyRequest(BaseModel):
    title: str
    description: str


class ClassifyResponse(BaseModel):
    category: str
    confidence: float
    priority: str
    priority_score: float
    suggested_department_code: str


class DuplicateQueryRequest(BaseModel):
    title: str
    description: str
    threshold: Optional[float] = 0.75
    top_k: Optional[int] = 5


@router.post("/classify", response_model=ClassifyResponse)
def classify_text(req: ClassifyRequest):
    result = classifier_service.classify(req.title, req.description)
    return result


@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
def check_duplicate_complaints(
    req: DuplicateQueryRequest,
    db: Session = Depends(get_db),
):
    matches = duplicate_service.find_duplicates(
        title=req.title,
        description=req.description,
        top_k=req.top_k,
        similarity_threshold=req.threshold,
    )

    candidates: List[DuplicateCandidate] = []
    for match in matches:
        complaint = (
            db.query(Complaint)
            .filter(Complaint.id == match["complaint_id"])
            .first()
        )
        if complaint:
            candidates.append(
                DuplicateCandidate(
                    complaint_id=complaint.id,
                    tracking_number=complaint.tracking_number,
                    title=complaint.title,
                    description=complaint.description,
                    similarity_score=match["similarity_score"],
                    status=complaint.status.value,
                    created_at=complaint.created_at,
                )
            )

    return DuplicateCheckResponse(
        is_duplicate=len(candidates) > 0,
        match_count=len(candidates),
        candidates=candidates,
    )


@router.post("/reindex")
def reindex_vector_database(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_active_admin),
):
    """
    Rebuilds the FAISS vector index from all active and open complaints in the database.
    """
    complaints = (
        db.query(Complaint.id, Complaint.title, Complaint.description)
        .filter(Complaint.status != ComplaintStatus.REJECTED)
        .all()
    )
    records = [(c[0], c[1], c[2]) for c in complaints]
    duplicate_service.rebuild_index(records)
    return {
        "status": "success",
        "reindexed_count": len(records),
        "message": f"Successfully rebuilt FAISS vector index with {len(records)} complaints.",
    }

