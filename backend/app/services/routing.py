"""
CivicLens AI/ML Pipeline — Stage 5: Department Routing & SLA Engine

Routing: Rule-based mapping (category, confidence, jurisdiction) → primary + secondary dept.
SLA: Dynamic deadline = now + max(floor, base × priority_multiplier)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.complaint import ComplaintPriority
from app.models.department import Department

logger = logging.getLogger(__name__)

ROUTING_TABLE: Dict[str, Dict[str, str]] = {
    "Infrastructure & Roads":          {"primary": "ROADS",    "secondary": "TRAFFIC"},
    "Water Supply & Drainage":         {"primary": "WATER",    "secondary": "SANITATION"},
    "Electricity & Street Lighting":   {"primary": "POWER",    "secondary": "EMERGENCY"},
    "Sanitation & Waste Management":   {"primary": "SANITATION","secondary": "HEALTH"},
    "Public Health & Environment":     {"primary": "HEALTH",   "secondary": "SANITATION"},
    "Traffic & Road Safety":           {"primary": "TRAFFIC",  "secondary": "ROADS"},
    "Building Safety":                 {"primary": "SAFETY",   "secondary": "EMERGENCY"},
    "Parks & Public Spaces":           {"primary": "PARKS",    "secondary": "ROADS"},
    # Legacy categories
    "Roads & Infrastructure":          {"primary": "ROADS",    "secondary": "TRAFFIC"},
    "Water Supply & Sewage":           {"primary": "WATER",    "secondary": "SANITATION"},
    "Sanitation & Solid Waste":        {"primary": "SANITATION","secondary": "HEALTH"},
    "Public Health":                   {"primary": "HEALTH",   "secondary": "SANITATION"},
}

AUTO_ROUTE_CONFIDENCE_THRESHOLD = 0.60

PRIORITY_SLA_MULTIPLIERS = {
    ComplaintPriority.CRITICAL: 0.20,
    ComplaintPriority.HIGH:     0.50,
    ComplaintPriority.MEDIUM:   1.00,
    ComplaintPriority.LOW:      1.50,
}

PRIORITY_SLA_FLOOR_HOURS = {
    ComplaintPriority.CRITICAL: 2,
    ComplaintPriority.HIGH:     8,
    ComplaintPriority.MEDIUM:   24,
    ComplaintPriority.LOW:      48,
}


class RoutingService:
    """Rule-based department routing engine — no ML model, fully explainable."""

    def resolve_department(
        self,
        db: Session,
        category: str,
        confidence: float,
        suggested_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        if confidence < AUTO_ROUTE_CONFIDENCE_THRESHOLD:
            return {
                "department": None,
                "needs_manual_review": True,
                "reason": f"Confidence {confidence:.0%} below auto-route threshold",
                "secondary_department_code": None,
            }

        mapping = ROUTING_TABLE.get(category)
        primary_code = suggested_code or (mapping["primary"] if mapping else None)
        secondary_code = mapping["secondary"] if mapping else None

        if primary_code:
            dept = db.query(Department).filter(Department.code == primary_code).first()
            if dept:
                return {
                    "department": dept,
                    "needs_manual_review": False,
                    "reason": f"Auto-routed via '{category}' → {primary_code}",
                    "secondary_department_code": secondary_code,
                }

        if category:
            dept = (
                db.query(Department)
                .filter(Department.name.ilike(f"%{category.split('&')[0].strip()}%"))
                .first()
            )
            if dept:
                return {
                    "department": dept,
                    "needs_manual_review": False,
                    "reason": f"Auto-routed via name match → {dept.code}",
                    "secondary_department_code": secondary_code,
                }

        dept = db.query(Department).first()
        return {
            "department": dept,
            "needs_manual_review": True,
            "reason": f"No mapping for '{category}' — routed to default",
            "secondary_department_code": None,
        }

    def calculate_sla_deadline(
        self,
        department: Optional[Department],
        priority: ComplaintPriority,
    ) -> datetime:
        base_hours = department.sla_hours if department else 48
        multiplier = PRIORITY_SLA_MULTIPLIERS.get(priority, 1.0)
        floor_hours = PRIORITY_SLA_FLOOR_HOURS.get(priority, 24)
        effective_hours = max(floor_hours, int(base_hours * multiplier))
        return datetime.utcnow() + timedelta(hours=effective_hours)

    def validate_reassignment(
        self,
        db: Session,
        new_department_code: str,
        reason: str,
    ) -> Dict[str, Any]:
        if not reason or len(reason.strip()) < 10:
            return {"valid": False, "error": "Reassignment reason must be at least 10 characters."}
        new_dept = db.query(Department).filter(Department.code == new_department_code).first()
        if not new_dept:
            return {"valid": False, "error": f"Department '{new_department_code}' not found."}
        return {"valid": True, "department": new_dept}


routing_service = RoutingService()
