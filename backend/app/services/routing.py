from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.complaint import ComplaintPriority
from app.services.classifier import classifier_service


class RoutingService:
    """
    Department routing and dynamic SLA assignment engine.
    """

    @staticmethod
    def resolve_department(
        db: Session,
        suggested_code: str,
        category: Optional[str] = None,
    ) -> Optional[Department]:
        # Try finding by code
        dept = db.query(Department).filter(Department.code == suggested_code).first()
        if dept:
            return dept

        # Fallback search by category name
        if category:
            dept = (
                db.query(Department)
                .filter(Department.name.ilike(f"%{category}%"))
                .first()
            )
            if dept:
                return dept

        # Default fallback to first department
        return db.query(Department).first()

    @staticmethod
    def calculate_target_sla(
        department: Optional[Department],
        priority: ComplaintPriority,
    ) -> datetime:
        base_hours = department.sla_hours if department else 48

        # Accelerate resolution SLA for higher priority
        if priority == ComplaintPriority.CRITICAL:
            effective_hours = max(4, int(base_hours * 0.25))  # e.g., 6 to 12 hours
        elif priority == ComplaintPriority.HIGH:
            effective_hours = max(12, int(base_hours * 0.50))
        elif priority == ComplaintPriority.LOW:
            effective_hours = int(base_hours * 1.5)
        else:
            effective_hours = base_hours

        return datetime.utcnow() + timedelta(hours=effective_hours)


routing_service = RoutingService()

