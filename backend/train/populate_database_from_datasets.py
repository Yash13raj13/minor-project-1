"""
CivicLens — Seed Real Grievances from Master Hybrid Dataset into SQLite Database.
Populates ~300 authentic complaints covering:
  - BBMP Bengaluru (10,000 dataset)
  - NYC 311 Service Requests (5,000 dataset)
  - CPGRAMS India (5,000 dataset)
  - COMI-LINGUA Hinglish (2,000 dataset)
  - IEEE DataPort CivicNLP-608 Marathi (608 dataset)

Includes realistic Indian coordinates (Bengaluru, Delhi, Pune),
assigned municipal departments, AI confidence scores, deterministic priorities,
realistic statuses, and audit histories.
"""

import os
import sys
import csv
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, Base, engine
from app.models.department import Department
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus
from app.models.audit_log import AuditLog
from app.models.ai_models import ComplaintPrediction, PriorityHistory, SLARecord
from app.services.duplicate_finder import duplicate_service

# Indian Municipal Clusters with realistic coordinates and wards
LOCATIONS = [
    # Bengaluru (BBMP)
    {"city": "Bengaluru", "lat": 12.9716, "lon": 77.5946, "ward": "Ward 112 - Domlur", "area": "Indiranagar 100ft Road"},
    {"city": "Bengaluru", "lat": 12.9352, "lon": 77.6245, "ward": "Ward 151 - Koramangala", "area": "Koramangala 4th Block"},
    {"city": "Bengaluru", "lat": 12.9141, "lon": 77.6321, "ward": "Ward 174 - HSR Layout", "area": "HSR Sector 2 Main Road"},
    {"city": "Bengaluru", "lat": 12.9784, "lon": 77.6408, "ward": "Ward 80 - Whitefield", "area": "ITPL Main Road"},
    {"city": "Bengaluru", "lat": 13.0358, "lon": 77.5970, "ward": "Ward 22 - Hebbal", "area": "Hebbal Flyover Junction"},
    {"city": "Bengaluru", "lat": 12.9250, "lon": 77.5838, "ward": "Ward 167 - Jayanagar", "area": "Jayanagar 4th Block Complex"},
    {"city": "Bengaluru", "lat": 12.9830, "lon": 77.6047, "ward": "Ward 110 - Sampangiram", "area": "MG Road Metro Crossing"},
    
    # Pune (PMC) - for Marathi complaints
    {"city": "Pune", "lat": 18.5204, "lon": 73.8567, "ward": "Ward 14 - Shivajinagar", "area": "FC Road, Shivajinagar"},
    {"city": "Pune", "lat": 18.5074, "lon": 73.8077, "ward": "Ward 28 - Kothrud", "area": "Kothrud Stand, Paud Road"},
    {"city": "Pune", "lat": 18.5679, "lon": 73.9143, "ward": "Ward 4 - Viman Nagar", "area": "Viman Nagar Central Mall"},
    {"city": "Pune", "lat": 18.5089, "lon": 73.9259, "ward": "Ward 21 - Hadapsar", "area": "Magarpatta South Gate"},
    {"city": "Pune", "lat": 18.5362, "lon": 73.8340, "ward": "Ward 9 - Aundh", "area": "Aundh DP Road"},

    # Delhi NCR
    {"city": "Delhi", "lat": 28.6139, "lon": 77.2090, "ward": "Ward 7 - Central", "area": "Connaught Place Outer Circle"},
    {"city": "Delhi", "lat": 28.6250, "lon": 77.2180, "ward": "Ward 12 - North", "area": "Bal Bharati Marg, Rajendra Nagar"},
    {"city": "Delhi", "lat": 28.6080, "lon": 77.2250, "ward": "Ward 3 - East", "area": "Laxmi Nagar Metro Pillar 42"},
    {"city": "Delhi", "lat": 28.6320, "lon": 77.2010, "ward": "Ward 7 - Central", "area": "Ring Road Stretch, Karol Bagh"},
    {"city": "Delhi", "lat": 28.5990, "lon": 77.2100, "ward": "Ward 9 - South", "area": "Greenview Enclave, Block C"},
]

DEPT_CODE_MAP = {
    "Infrastructure & Roads": "ROADS",
    "Water Supply & Drainage": "WATER",
    "Sanitation & Waste Management": "SANITATION",
    "Electricity & Street Lighting": "POWER",
    "Public Health & Environment": "HEALTH",
    "Building Safety": "ROADS",
    "Traffic & Road Safety": "ROADS",
    "Parks & Public Spaces": "HEALTH",
}

STATUSES = [
    ComplaintStatus.SUBMITTED,
    ComplaintStatus.UNDER_REVIEW,
    ComplaintStatus.ASSIGNED,
    ComplaintStatus.IN_PROGRESS,
    ComplaintStatus.RESOLVED,
]

STATUS_WEIGHTS = [0.20, 0.20, 0.25, 0.20, 0.15]

def populate():
    print("="*70)
    print("🚀 POPULATING DATABASE FROM MASTER HYBRID DATASETS")
    print("="*70)

    db = SessionLocal()
    try:
        # 1. Fetch departments
        depts = {d.code: d for d in db.query(Department).all()}
        if not depts:
            print("No departments found, please run seed.py first.")
            return

        # 2. Fetch users
        citizen = db.query(User).filter(User.role == UserRole.CITIZEN).first()
        officer = db.query(User).filter(User.role == UserRole.OFFICER).first()
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()

        # 3. Read Master Dataset
        csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "dataset_civiclens_master_hybrid.csv")
        if not os.path.exists(csv_path):
            print("Master dataset not found:", csv_path)
            return

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        print(f"Total available master dataset records: {len(reader)}")

        # Select a balanced slice of 250 complaints:
        # Ensure Marathi, Hindi/Hinglish, BBMP, CPGRAMS, NYC 311 are represented
        marathi_rows = [r for r in reader if r.get("language") in ["Marathi", "mr"]]
        hindi_rows = [r for r in reader if r.get("language") in ["hi", "hi-en"]]
        bbmp_rows = [r for r in reader if r.get("source") == "BBMP_Bengaluru"]
        cpg_rows = [r for r in reader if r.get("source") == "CPGRAMS_India"]
        nyc_rows = [r for r in reader if r.get("source") == "NYC_311"]

        selected = []
        random.seed(42)
        # 40 Marathi complaints
        selected.extend(random.sample(marathi_rows, min(40, len(marathi_rows))))
        # 50 Hindi/Hinglish complaints
        selected.extend(random.sample(hindi_rows, min(50, len(hindi_rows))))
        # 60 BBMP complaints
        selected.extend(random.sample(bbmp_rows, min(60, len(bbmp_rows))))
        # 50 CPGRAMS complaints
        selected.extend(random.sample(cpg_rows, min(50, len(cpg_rows))))
        # 50 NYC 311 complaints
        selected.extend(random.sample(nyc_rows, min(50, len(nyc_rows))))

        random.shuffle(selected)
        print(f"Sampled {len(selected)} diverse real-world complaints for website ingestion.")

        # Wipe existing demo complaints if desired, or skip existing tracking numbers
        existing_numbers = set(r[0] for r in db.query(Complaint.tracking_number).all())

        new_complaints = []
        year = datetime.utcnow().year

        for i, row in enumerate(selected):
            track_num = f"CVL-{year}-{2000 + i}"
            if track_num in existing_numbers:
                continue

            text = row.get("complaint_text") or row.get("text", "")
            if not text:
                continue

            # Title & Description
            title = row.get("title")
            if not title:
                parts = text.split(".")
                title = parts[0][:80].strip()
                desc = text
            else:
                desc = row.get("description") or text

            cat = row.get("category", "Infrastructure & Roads")
            dept_code = DEPT_CODE_MAP.get(cat, "ROADS")
            dept = depts.get(dept_code) or list(depts.values())[0]

            # Priority
            sev = str(row.get("severity", "Medium")).upper()
            if sev in ["CRITICAL", "4", "5"]:
                prio = ComplaintPriority.CRITICAL
            elif sev in ["HIGH", "3"]:
                prio = ComplaintPriority.HIGH
            elif sev in ["LOW", "1"]:
                prio = ComplaintPriority.LOW
            else:
                prio = ComplaintPriority.MEDIUM

            # Status with realistic distribution
            stat = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]

            # Location
            lang = row.get("language", "en")
            if lang in ["Marathi", "mr"]:
                loc = random.choice([l for l in LOCATIONS if l["city"] == "Pune"] or LOCATIONS)
            elif "bbmp" in str(row.get("source", "")).lower():
                loc = random.choice([l for l in LOCATIONS if l["city"] == "Bengaluru"] or LOCATIONS)
            else:
                loc = random.choice(LOCATIONS)

            # Realistic timestamp in last 21 days
            days_ago = random.uniform(0.1, 21.0)
            created_at = datetime.utcnow() - timedelta(days=days_ago)
            resolved_at = created_at + timedelta(hours=random.uniform(6, 48)) if stat == ComplaintStatus.RESOLVED else None

            confidence = round(random.uniform(0.85, 0.98), 2)

            comp = Complaint(
                tracking_number=track_num,
                title=title,
                description=desc,
                category=cat,
                priority=prio,
                status=stat,
                latitude=loc["lat"] + random.uniform(-0.015, 0.015),
                longitude=loc["lon"] + random.uniform(-0.015, 0.015),
                address=f"{loc['area']}, {loc['city']}",
                ward=loc["ward"],
                ai_category=cat,
                ai_confidence=confidence,
                ai_priority_score=round(random.uniform(1.5, 4.5), 2),
                citizen_id=citizen.id if citizen else 1,
                department_id=dept.id,
                created_at=created_at,
                resolved_at=resolved_at,
            )
            db.add(comp)
            db.flush()

            # Add AI Prediction
            pred = ComplaintPrediction(
                complaint_id=comp.id,
                language_detected=lang,
                category=cat,
                subcategory=row.get("subcategory", "General"),
                confidence=confidence,
                severity=sev,
                immediate_risk=str(row.get("immediate_risk", "False")).lower() in ["true", "1"],
                public_exposure=str(row.get("public_exposure", "Medium")),
                priority_score=comp.ai_priority_score,
                priority_label=prio.value,
                suggested_department_code=dept.code,
                routing_reason=f"Matched to {dept.name} based on '{cat}'"
            )
            db.add(pred)

            # Add SLA record
            sla = SLARecord(
                complaint_id=comp.id,
                department_id=dept.id,
                priority=prio.value,
                sla_deadline=created_at + timedelta(hours=dept.sla_hours),
                sla_hours=dept.sla_hours,
            )
            db.add(sla)

            # Add Priority History
            ph = PriorityHistory(
                complaint_id=comp.id,
                priority_before=None,
                priority_after=prio.value,
                score_before=None,
                score_after=comp.ai_priority_score,
                trigger="initial",
                explanation=f"Deterministic priority computed from {sev} severity and public exposure.",
            )
            db.add(ph)

            # Add Audit Log
            audit = AuditLog(
                complaint_id=comp.id,
                performed_by_id=citizen.id if citizen else 1,
                action="COMPLAINT_FILED",
                previous_state=None,
                new_state=stat.value,
                remarks=f"Filed via CivicLens. AI Tag: '{cat}' ({int(confidence*100)}% conf). Source: {row.get('source', 'Citizen')}",
                timestamp=created_at,
            )
            db.add(audit)

            if stat != ComplaintStatus.SUBMITTED:
                status_audit = AuditLog(
                    complaint_id=comp.id,
                    performed_by_id=officer.id if officer else 1,
                    action="STATUS_CHANGE",
                    previous_state="SUBMITTED",
                    new_state=stat.value,
                    remarks=f"Triage update: Ticket transitioned to {stat.value}",
                    timestamp=created_at + timedelta(hours=random.uniform(1, 12)),
                )
                db.add(status_audit)

            new_complaints.append(comp)

        db.commit()
        print(f"✅ Successfully seeded {len(new_complaints)} real grievance records into the database!")

        # Rebuild FAISS Vector index
        print("⚡ Rebuilding FAISS vector index with all records...")
        all_comps = db.query(
            Complaint.id, Complaint.title, Complaint.description,
            Complaint.latitude, Complaint.longitude, Complaint.category
        ).all()
        records = [(c[0], c[1], c[2], c[3], c[4], c[5], None) for c in all_comps]
        duplicate_service.rebuild_index(records)
        print(f"🎯 FAISS Index rebuilt with {len(records)} complaints!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during population: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    populate()
