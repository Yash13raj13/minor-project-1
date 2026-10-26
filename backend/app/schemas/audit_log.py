from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    complaint_id: int
    performed_by_id: Optional[int] = None
    action: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    remarks: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

