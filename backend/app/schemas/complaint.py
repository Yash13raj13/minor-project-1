from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.complaint import ComplaintPriority, ComplaintStatus
from app.schemas.department import DepartmentResponse


class ComplaintBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    category: Optional[str] = "General"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    ward: Optional[str] = None
    image_url: Optional[str] = None


class ComplaintCreate(ComplaintBase):
    department_id: Optional[int] = None
    force_submit_duplicate: Optional[bool] = False


class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    priority: Optional[ComplaintPriority] = None
    department_id: Optional[int] = None
    assigned_officer_id: Optional[int] = None
    remarks: Optional[str] = None


class StatusUpdate(BaseModel):
    status: ComplaintStatus
    remarks: Optional[str] = "Status updated by authority"


class CitizenBrief(BaseModel):
    id: int
    full_name: str
    email: str

    class Config:
        from_attributes = True


class ComplaintResponse(ComplaintBase):
    id: int
    tracking_number: str
    priority: ComplaintPriority
    status: ComplaintStatus
    citizen_id: int
    citizen: Optional[CitizenBrief] = None
    department_id: Optional[int] = None
    department: Optional[DepartmentResponse] = None
    assigned_officer_id: Optional[int] = None
    ai_category: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_priority_score: Optional[float] = None
    is_duplicate: bool
    duplicate_of_id: Optional[int] = None
    similarity_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DuplicateCandidate(BaseModel):
    complaint_id: int
    tracking_number: str
    title: str
    description: str
    similarity_score: float
    status: str
    created_at: datetime


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    match_count: int
    candidates: List[DuplicateCandidate] = []

