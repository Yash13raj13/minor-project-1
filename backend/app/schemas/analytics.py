from typing import Dict, List, Optional
from pydantic import BaseModel


class StatusBreakdown(BaseModel):
    submitted: int = 0
    under_review: int = 0
    assigned: int = 0
    in_progress: int = 0
    resolved: int = 0
    rejected: int = 0
    duplicate: int = 0


class PriorityBreakdown(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


class DepartmentMetric(BaseModel):
    department_id: int
    name: str
    total_complaints: int
    resolved_complaints: int
    pending_complaints: int
    sla_compliance_rate: float


class WardMetric(BaseModel):
    ward: str
    count: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TrendPoint(BaseModel):
    date: str
    count: int


class DashboardAnalytics(BaseModel):
    total_complaints: int
    resolved_count: int
    pending_count: int
    duplicates_detected: int
    resolution_rate: float
    avg_resolution_hours: float
    status_distribution: StatusBreakdown
    priority_distribution: PriorityBreakdown
    department_metrics: List[DepartmentMetric]
    ward_hotspots: List[WardMetric]
    daily_trend: List[TrendPoint]

