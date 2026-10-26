from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models.complaint import Complaint, ComplaintStatus
from app.services.duplicate_finder import duplicate_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    
    # Pre-index active complaints into FAISS vector database
    db = SessionLocal()
    try:
        complaints = (
            db.query(Complaint.id, Complaint.title, Complaint.description)
            .filter(Complaint.status != ComplaintStatus.REJECTED)
            .all()
        )
        if complaints:
            duplicate_service.rebuild_index([(c[0], c[1], c[2]) for c in complaints])
    except Exception as e:
        print(f"Vector index warm-up notice: {e}")
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered Governance Complaint Intelligence Platform: Text Classification, FAISS Semantic Duplicate Detection, SLA Analytics, and Geospatial Mapping.",
    version="1.0.0",
    lifespan=lifespan,
)

# Set CORS origins
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
        "status": "operational",
        "api_docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}

