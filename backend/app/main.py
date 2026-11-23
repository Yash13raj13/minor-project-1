from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models.complaint import Complaint, ComplaintStatus
from app.services.duplicate_finder import duplicate_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create all database tables (including new AI pipeline tables)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created.")

    # 2. Warm-up FAISS vector index from existing complaints
    db = SessionLocal()
    try:
        complaints = (
            db.query(
                Complaint.id,
                Complaint.title,
                Complaint.description,
                Complaint.latitude,
                Complaint.longitude,
                Complaint.category,
            )
            .filter(Complaint.status != ComplaintStatus.REJECTED)
            .all()
        )
        if complaints:
            records = [(c[0], c[1], c[2], c[3], c[4], c[5], None) for c in complaints]
            duplicate_service.rebuild_index(records)
            logger.info(f"FAISS index warmed up with {len(records)} complaints.")
        else:
            logger.info("No existing complaints — FAISS index starts empty.")
    except Exception as e:
        logger.warning(f"FAISS warm-up skipped: {e}")
    finally:
        db.close()

    # 3. Load custom trained models if present
    import os
    from app.services.classifier import classifier_service
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    classifier_path = os.path.join(base_dir, "models", "classifier")
    if os.path.exists(classifier_path):
        try:
            classifier_service.load_finetuned_model(classifier_path)
            logger.info(f"Custom fine-tuned classifier head loaded from {classifier_path}.")
        except Exception as e:
            logger.warning(f"Could not load custom classifier: {e}")

    embeddings_path = os.path.join(base_dir, "models", "embeddings")
    if os.path.exists(embeddings_path):
        try:
            duplicate_service.load_finetuned_model(embeddings_path)
            logger.info(f"Custom fine-tuned embeddings loaded from {embeddings_path}.")
        except Exception as e:
            logger.warning(f"Could not load custom embeddings: {e}")

    yield
    logger.info("CivicLens shutdown.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "CivicLens: AI-Powered Governance Complaint Intelligence Platform.\n\n"
        "**AI Pipeline:**\n"
        "1. Multilingual preprocessing (EN/HI/Hinglish) via Stanza + Indic NLP\n"
        "2. Complaint classification via mDeBERTa / XLM-RoBERTa-base\n"
        "3. Priority scoring: P = 0.35·S + 0.25·I + 0.15·E + 0.10·C + 0.15·T\n"
        "4. Semantic duplicate detection via Indic BGE-M3 + FAISS\n"
        "5. Independent corroboration: C = min(5, 2·log₂(1+N))\n"
        "6. Rule-based department routing + dynamic SLA"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def root():
    return {
        "platform": settings.PROJECT_NAME,
        "version": "2.0.0",
        "status": "operational",
        "ai_pipeline": "active",
        "api_docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    from app.services.duplicate_finder import duplicate_service
    return {
        "status": "healthy",
        "faiss_index_size": duplicate_service.index_size,
        "embedding_model": duplicate_service.model_name,
    }
