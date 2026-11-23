"""
CivicLens AI API endpoints — Classify, Duplicate Check, Reindex, Pipeline Explain,
Corroboration Query, and Officer Correction tracking.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_admin, get_current_active_officer, get_db
from app.models.ai_models import ComplaintPrediction, CorroborationRecord, IncidentCluster, IncidentReport
from app.models.complaint import Complaint, ComplaintStatus
from app.models.user import User
from app.schemas.complaint import DuplicateCandidate, DuplicateCheckResponse
from app.services.classifier import classifier_service, priority_engine
from app.services.duplicate_finder import duplicate_service, corroboration_engine
from app.services.preprocessor import preprocessor

router = APIRouter(prefix="/ai", tags=["AI & Intelligence Services"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PreprocessRequest(BaseModel):
    text: str

class PreprocessResponse(BaseModel):
    original_text: str
    normalised_text: str
    processed_text: str
    language: str

class ClassifyRequest(BaseModel):
    title: str
    description: str

class ClassifyResponse(BaseModel):
    category: str
    subcategory: str
    confidence: float
    hazard: bool
    hazard_type: Optional[str] = None
    immediate_risk: bool
    suggested_department_code: str
    secondary_department_code: str

class AttributeRequest(BaseModel):
    title: str
    description: str
    hazard: bool = False
    corroboration_score: float = 2.0
    time_pending_days: float = 0.0

class AttributeResponse(BaseModel):
    priority: str
    priority_score: float
    safety_override: bool
    explanation: str
    components: dict
    attributes: dict
    corroboration_score: float

class DuplicateQueryRequest(BaseModel):
    title: str
    description: str
    threshold: float = 0.80
    top_k: int = 5
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    category: Optional[str] = None

class CorroborationRequest(BaseModel):
    cluster_id: int

class OfficerCorrectionRequest(BaseModel):
    complaint_id: int
    corrected_category: Optional[str] = None
    corrected_priority: Optional[str] = None
    reason: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/preprocess", response_model=PreprocessResponse)
def preprocess_text(req: PreprocessRequest):
    """Stage 1: Multilingual text preprocessing (language detect, normalise, lemmatise)."""
    result = preprocessor.preprocess(req.text)
    return result


@router.post("/classify", response_model=ClassifyResponse)
def classify_complaint(req: ClassifyRequest):
    """Stage 2: Category classification + incident attribute extraction + hazard detection."""
    preprocessed = preprocessor.preprocess(f"{req.title}. {req.description}")
    result = classifier_service.classify(
        title=req.title,
        description=req.description,
        language=preprocessed["language"],
    )
    return {
        "category": result["category"],
        "subcategory": result.get("subcategory", "General"),
        "confidence": result["confidence"],
        "hazard": result["hazard"],
        "hazard_type": result.get("hazard_type"),
        "immediate_risk": result.get("immediate_risk", False),
        "suggested_department_code": result["suggested_department_code"],
        "secondary_department_code": result.get("secondary_department_code", ""),
    }


@router.post("/priority", response_model=AttributeResponse)
def score_priority(req: AttributeRequest):
    """
    Stage 3: Deterministic priority scoring.
    P = 0.35·S + 0.25·I + 0.15·E + 0.10·C + 0.15·T
    with safety override.
    """
    result = priority_engine.compute_full_priority(
        title=req.title,
        description=req.description,
        hazard=req.hazard,
        corroboration_score=req.corroboration_score,
        time_pending_days=req.time_pending_days,
    )
    return result


@router.post("/check-duplicates", response_model=DuplicateCheckResponse)
def check_duplicate_complaints(
    req: DuplicateQueryRequest,
    db: Session = Depends(get_db),
):
    """Stage 4: FAISS semantic duplicate detection with contextual verification."""
    matches = duplicate_service.find_duplicates(
        title=req.title,
        description=req.description,
        top_k=req.top_k,
        similarity_threshold=req.threshold,
        latitude=req.latitude,
        longitude=req.longitude,
        category=req.category,
    )

    candidates: List[DuplicateCandidate] = []
    for m in matches:
        complaint = db.query(Complaint).filter(Complaint.id == m["complaint_id"]).first()
        if complaint:
            candidates.append(DuplicateCandidate(
                complaint_id=complaint.id,
                tracking_number=complaint.tracking_number,
                title=complaint.title,
                description=complaint.description,
                similarity_score=m["similarity_score"],
                status=complaint.status.value,
                created_at=complaint.created_at,
            ))

    return DuplicateCheckResponse(
        is_duplicate=len(candidates) > 0,
        match_count=len(candidates),
        candidates=candidates,
    )


@router.get("/corroboration/{cluster_id}")
def get_corroboration(cluster_id: int, db: Session = Depends(get_db)):
    """Stage 5: Get corroboration score and reporter count for an incident cluster."""
    cluster = db.query(IncidentCluster).filter(IncidentCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Incident cluster not found")

    reports = db.query(IncidentReport).filter(IncidentReport.cluster_id == cluster_id).all()
    unique_users = cluster.unique_reporter_count

    return {
        "cluster_id": cluster_id,
        "total_reports": cluster.total_report_count,
        "unique_reporters": unique_users,
        "corroboration_score": corroboration_engine.corroboration_score(unique_users),
        "context_score_example": corroboration_engine.context_score(
            evidence_quality=2.0, unique_users=unique_users
        ),
        "category": cluster.category,
        "priority": cluster.priority,
    }


@router.post("/officer-correction")
def record_officer_correction(
    req: OfficerCorrectionRequest,
    db: Session = Depends(get_db),
    officer: User = Depends(get_current_active_officer),
):
    """
    Record an officer's manual correction of AI prediction (category or priority).
    Critical for model evaluation and future fine-tuning datasets.
    """
    pred = db.query(ComplaintPrediction).filter(
        ComplaintPrediction.complaint_id == req.complaint_id
    ).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found for this complaint")

    pred.officer_corrected = True
    pred.officer_corrected_category = req.corrected_category
    pred.officer_corrected_priority = req.corrected_priority
    pred.corrected_by_id = officer.id
    from datetime import datetime
    pred.corrected_at = datetime.utcnow()
    db.commit()

    return {
        "status": "correction_recorded",
        "complaint_id": req.complaint_id,
        "corrected_by": officer.email,
        "note": "This correction will be used to evaluate and fine-tune the classifier.",
    }


@router.post("/reindex")
def reindex_vector_database(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_active_admin),
):
    """Admin: Rebuild the FAISS vector index from all active complaints."""
    complaints = (
        db.query(
            Complaint.id, Complaint.title, Complaint.description,
            Complaint.latitude, Complaint.longitude, Complaint.category,
        )
        .filter(Complaint.status != ComplaintStatus.REJECTED)
        .all()
    )
    records = [(c[0], c[1], c[2], c[3], c[4], c[5], None) for c in complaints]
    duplicate_service.rebuild_index(records)
    return {
        "status": "success",
        "reindexed_count": len(records),
        "embedding_model": duplicate_service.model_name,
        "message": f"FAISS index rebuilt with {len(records)} complaints.",
    }


@router.get("/pipeline/status")
def pipeline_status():
    """Returns current status of all AI pipeline components."""
    return {
        "preprocessor": "active",
        "classifier": {
            "zero_shot_loaded": classifier_service._zs_pipeline is not None,
            "finetuned_loaded": classifier_service._ft_model is not None,
            "initialized": classifier_service._initialized,
        },
        "duplicate_finder": {
            "model": duplicate_service.model_name,
            "index_size": duplicate_service.index_size,
            "initialized": duplicate_service._initialized,
        },
        "priority_engine": "active (deterministic)",
        "routing_engine": "active (rule-based)",
    }


@router.get("/datasets/summary")
def get_datasets_summary():
    """Returns metadata and breakdown of all integrated training datasets."""
    import os
    import csv

    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    master_path = os.path.join(data_dir, "dataset_civiclens_master_hybrid.csv")
    
    total_master = 18693
    languages = {"English": 16957, "Hinglish": 967, "Hindi": 461, "Marathi": 212, "Other Indic": 96}
    
    datasets = [
        {
            "id": "bbmp_bengaluru",
            "name": "BBMP Grievances Dataset (Bengaluru)",
            "source": "OpenCity / Sahaaya 2.0 (Karnataka)",
            "records": 10000,
            "languages": ["English", "Kannada-English"],
            "focus": "Real municipal complaints & department routing patterns",
            "status": "Integrated & Normalized",
        },
        {
            "id": "nyc_311",
            "name": "NYC 311 Municipal Service Requests",
            "source": "NYC OpenData Socrata API",
            "records": 5000,
            "languages": ["English"],
            "focus": "High-volume road hazards, sanitation & streetlight service requests",
            "status": "Integrated & Normalized",
        },
        {
            "id": "cpgrams_india",
            "name": "CPGRAMS Pan-India Grievance Corpus",
            "source": "Central Public Grievance Portal (Data.gov.in)",
            "records": 5000,
            "languages": ["Hindi", "English", "Multilingual Indic"],
            "focus": "Indian central governance language & department escalation routing",
            "status": "Integrated & Normalized",
        },
        {
            "id": "comilingua_hinglish",
            "name": "COMI-LINGUA Code-Mixed Dataset",
            "source": "LingoIITGN (Hugging Face)",
            "records": 2000,
            "languages": ["Hinglish (Hindi-English)"],
            "focus": "Romanized Hindi normalization, POS & colloquial code-mix handling",
            "status": "Integrated & Normalized",
        },
        {
            "id": "civicnlp_marathi",
            "name": "Bilingual Civic Complaint Dataset (CivicNLP-608)",
            "source": "IEEE DataPort (DOI: 10.21227/13nz-rt85 / Sanjivani CoE)",
            "records": 608,
            "languages": ["Marathi (Devanagari)", "English"],
            "focus": "Bilingual public service complaint categorization & incident attributes",
            "status": "Integrated & Fine-tuned",
        },
    ]

    return {
        "total_master_records": total_master,
        "datasets": datasets,
        "languages": languages,
        "categories_count": 8,
    }


@router.get("/datasets/samples")
def get_dataset_samples(language: Optional[str] = None, limit: int = 15):
    """Returns authentic sample records from the master training dataset."""
    import os
    import csv

    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
    master_path = os.path.join(data_dir, "dataset_civiclens_master_hybrid.csv")
    
    samples = []
    if os.path.exists(master_path):
        with open(master_path, "r", encoding="utf-8") as f:
            all_rows = list(csv.DictReader(f))

        if not language or language.lower() == "all":
            # Balanced multi-source selection: 2 from each of the 5 sources
            sources = [
                ("CivicNLP-608-Marathi", ["Marathi", "mr"]),
                ("COMI-LINGUA", ["hi-en", "Hinglish"]),
                ("CPGRAMS_India", ["hi", "Hindi"]),
                ("BBMP_Bengaluru", ["en", "English"]),
                ("NYC_311", ["en", "English"]),
            ]
            for src_name, valid_langs in sources:
                matching = [
                    r for r in all_rows 
                    if src_name.lower() in str(r.get("source", "")).lower() 
                    or any(vl.lower() in str(r.get("language", "")).lower() for vl in valid_langs)
                ]
                for row in matching[:2]:
                    samples.append({
                        "id": row.get("complaint_id", ""),
                        "text": row.get("complaint_text") or row.get("text", ""),
                        "category": row.get("category", ""),
                        "subcategory": row.get("subcategory", "General"),
                        "language": row.get("language", ""),
                        "severity": row.get("severity", "Medium"),
                        "immediate_risk": str(row.get("immediate_risk", "False")).lower() in ["true", "1"],
                        "source": row.get("source", src_name),
                    })
        else:
            l_low = language.lower()
            for row in all_rows:
                row_lang = str(row.get("language", "")).lower()
                if l_low == "marathi" and row_lang not in ["marathi", "mr"]:
                    continue
                elif l_low in ["hindi", "hinglish"] and row_lang not in ["hi", "hi-en", "hindi", "hinglish"]:
                    continue
                elif l_low == "english" and row_lang not in ["en", "english"]:
                    continue
                elif l_low not in ["marathi", "hindi", "hinglish", "english"] and l_low not in row_lang:
                    continue

                samples.append({
                    "id": row.get("complaint_id", ""),
                    "text": row.get("complaint_text") or row.get("text", ""),
                    "category": row.get("category", ""),
                    "subcategory": row.get("subcategory", "General"),
                    "language": row.get("language", ""),
                    "severity": row.get("severity", "Medium"),
                    "immediate_risk": str(row.get("immediate_risk", "False")).lower() in ["true", "1"],
                    "source": row.get("source", "Master Dataset"),
                })
                if len(samples) >= limit:
                    break

    return {"count": len(samples), "samples": samples}
