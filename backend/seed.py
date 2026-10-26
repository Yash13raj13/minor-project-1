from datetime import datetime, timedelta
from app.core.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus
from app.models.department import Department
from app.models.user import User, UserRole


def seed():
    print("🌱 Initializing CivicLens Database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Departments
        departments_data = [
            {
                "name": "Roads & Infrastructure",
                "code": "ROADS",
                "description": "Potholes, broken footpaths, road resurfacing, and bridge maintenance.",
                "contact_email": "roads@civiclens.gov",
                "sla_hours": 48,
            },
            {
                "name": "Sanitation & Solid Waste",
                "code": "SANITATION",
                "description": "Garbage pileups, missed waste collection, illegal dumping, and drain cleaning.",
                "contact_email": "sanitation@civiclens.gov",
                "sla_hours": 24,
            },
            {
                "name": "Water Supply & Sewage",
                "code": "WATER",
                "description": "Pipe bursts, contaminated drinking water, low pressure, and sewage overflow.",
                "contact_email": "water@civiclens.gov",
                "sla_hours": 36,
            },
            {
                "name": "Electricity & Street Lighting",
                "code": "POWER",
                "description": "Non-functional streetlights, exposed live wires, transformer faults, and power outages.",
                "contact_email": "power@civiclens.gov",
                "sla_hours": 24,
            },
            {
                "name": "Public Health & Environment",
                "code": "HEALTH",
                "description": "Mosquito breeding, stray animal hazards, noise violations, and air quality issues.",
                "contact_email": "health@civiclens.gov",
                "sla_hours": 48,
            },
        ]

        departments_map = {}
        for d_info in departments_data:
            dept = db.query(Department).filter(Department.code == d_info["code"]).first()
            if not dept:
                dept = Department(**d_info)
                db.add(dept)
                db.flush()
            departments_map[d_info["code"]] = dept
        print("✅ Departments seeded.")

        # 2. Users
        # Admin
        admin = db.query(User).filter(User.email == "admin@civiclens.gov").first()
        if not admin:
            admin = User(
                full_name="Municipal Commissioner",
                email="admin@civiclens.gov",
                hashed_password=get_password_hash("Admin@123"),
                phone="+91 98765 00001",
                role=UserRole.ADMIN,
            )
            db.add(admin)
            db.flush()

        # Sanitation Officer
        officer = db.query(User).filter(User.email == "officer@civiclens.gov").first()
        if not officer:
            officer = User(
                full_name="Rajesh Verma (Zonal Officer)",
                email="officer@civiclens.gov",
                hashed_password=get_password_hash("Officer@123"),
                phone="+91 98765 00002",
                role=UserRole.OFFICER,
                department_id=departments_map["SANITATION"].id,
            )
            db.add(officer)
            db.flush()

        # Citizen
        citizen = db.query(User).filter(User.email == "citizen@civiclens.gov").first()
        if not citizen:
            citizen = User(
                full_name="Priya Sharma",
                email="citizen@civiclens.gov",
                hashed_password=get_password_hash("Citizen@123"),
                phone="+91 98765 00003",
                role=UserRole.CITIZEN,
            )
            db.add(citizen)
            db.flush()
        print("✅ Default users created (Admin, Officer, Citizen).")

        # 3. Sample Complaints with Geolocation
        sample_complaints = [
            {
                "tracking_number": "CVL-2026-1001",
                "title": "Severe pothole causing traffic jam near Sector 14 market",
                "description": "Deep pothole spanning almost 3 feet in front of the main grocery junction. Two two-wheelers have skidded already.",
                "category": "Roads & Infrastructure",
                "dept_code": "ROADS",
                "priority": ComplaintPriority.HIGH,
                "status": ComplaintStatus.IN_PROGRESS,
                "lat": 28.6139,
                "lon": 77.2090,
                "address": "Sector 14 Market Crossing",
                "ward": "Ward 7 - Central",
                "ai_confidence": 0.94,
                "days_ago": 3,
            },
            {
                "tracking_number": "CVL-2026-1002",
                "title": "Uncollected garbage dump emitting toxic smell near primary school",
                "description": "Community bin overflowing for 5 days. Waste is spilling onto the road and stray dogs are tearing trash bags open.",
                "category": "Sanitation & Solid Waste",
                "dept_code": "SANITATION",
                "priority": ComplaintPriority.CRITICAL,
                "status": ComplaintStatus.ASSIGNED,
                "lat": 28.6250,
                "lon": 77.2180,
                "address": "Opposite Bal Bharati Public School",
                "ward": "Ward 12 - North",
                "ai_confidence": 0.98,
                "days_ago": 2,
            },
            {
                "tracking_number": "CVL-2026-1003",
                "title": "Major clean water pipeline rupture on 5th Avenue",
                "description": "Potable drinking water is gushing out on the street since early morning. Hundreds of liters wasted.",
                "category": "Water Supply & Sewage",
                "dept_code": "WATER",
                "priority": ComplaintPriority.CRITICAL,
                "status": ComplaintStatus.SUBMITTED,
                "lat": 28.6080,
                "lon": 77.2250,
                "address": "5th Avenue, Near Park Gate 3",
                "ward": "Ward 3 - East",
                "ai_confidence": 0.96,
                "days_ago": 1,
            },
            {
                "tracking_number": "CVL-2026-1004",
                "title": "Four consecutive street lights broken along ring road stretch",
                "description": "The entire stretch between pillar 42 and 46 is completely pitch black at night, making it very dangerous for pedestrians.",
                "category": "Electricity & Street Lighting",
                "dept_code": "POWER",
                "priority": ComplaintPriority.MEDIUM,
                "status": ComplaintStatus.RESOLVED,
                "lat": 28.6320,
                "lon": 77.2010,
                "address": "Outer Ring Road, Pillar 44",
                "ward": "Ward 7 - Central",
                "ai_confidence": 0.92,
                "days_ago": 5,
            },
            {
                "tracking_number": "CVL-2026-1005",
                "title": "Stagnant drainage water breeding mosquitoes near apartment complex",
                "description": "Blocked open drain has stagnant dirty water for over two weeks. Rising dengue risk for nearby residents.",
                "category": "Public Health & Environment",
                "dept_code": "HEALTH",
                "priority": ComplaintPriority.HIGH,
                "status": ComplaintStatus.UNDER_REVIEW,
                "lat": 28.5990,
                "lon": 77.2100,
                "address": "Greenview Enclave, Block C",
                "ward": "Ward 9 - South",
                "ai_confidence": 0.91,
                "days_ago": 4,
            },
        ]

        for sc in sample_complaints:
            existing_c = (
                db.query(Complaint)
                .filter(Complaint.tracking_number == sc["tracking_number"])
                .first()
            )
            if not existing_c:
                created_time = datetime.utcnow() - timedelta(days=sc["days_ago"])
                resolved_time = (
                    created_time + timedelta(hours=18)
                    if sc["status"] == ComplaintStatus.RESOLVED
                    else None
                )
                complaint = Complaint(
                    tracking_number=sc["tracking_number"],
                    title=sc["title"],
                    description=sc["description"],
                    category=sc["category"],
                    priority=sc["priority"],
                    status=sc["status"],
                    latitude=sc["lat"],
                    longitude=sc["lon"],
                    address=sc["address"],
                    ward=sc["ward"],
                    ai_category=sc["category"],
                    ai_confidence=sc["ai_confidence"],
                    citizen_id=citizen.id,
                    department_id=departments_map[sc["dept_code"]].id,
                    created_at=created_time,
                    resolved_at=resolved_time,
                )
                db.add(complaint)
                db.flush()

                audit = AuditLog(
                    complaint_id=complaint.id,
                    performed_by_id=citizen.id,
                    action="COMPLAINT_FILED",
                    previous_state=None,
                    new_state=sc["status"].value,
                    remarks="Initial complaint logged in CivicLens",
                    timestamp=created_time,
                )
                db.add(audit)

        db.commit()
        print("✅ Sample civic complaints and audit logs seeded successfully.")
        print("\nDefault Logins:")
        print("  - Admin:   admin@civiclens.gov   / Admin@123")
        print("  - Officer: officer@civiclens.gov / Officer@123")
        print("  - Citizen: citizen@civiclens.gov / Citizen@123")
    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed()

