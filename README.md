# CivicLens 🏛️🔍
### AI-Powered Governance Complaint Intelligence Platform

CivicLens is an end-to-end intelligent complaint triaging, duplicate detection, and governance analytics system built to streamline citizen grievances and civic workflows.

---

## 🛠️ Technology Stack
- **Backend**: FastAPI, SQLAlchemy ORM, Alembic, PostgreSQL / SQLite
- **AI & NLP Engine**: Hugging Face Transformers (classification), Sentence Transformers + FAISS (semantic vector duplicate detection)
- **Frontend**: React.js, Tailwind CSS, Leaflet (interactive GIS maps), Chart.js / ECharts
- **Authentication**: JWT Bearer token authentication with Role-Based Access Control (Citizen, Officer, Admin)

---

## 🚀 Backend Setup & Execution

### 1. Requirements
Ensure Python 3.10+ is installed on your machine.

### 2. Virtual Environment Setup
```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
Configure `.env` with your database credentials:
- **Default Instant Mode**: SQLite (`sqlite:///./civiclens.db`) works out of the box without any setup.
- **Production PostgreSQL**:
  ```env
  DATABASE_URL="postgresql+psycopg2://postgres:your_password@localhost:5432/civiclens_db"
  ```

### 5. Seed Initial Data
Populate standard municipal departments, test accounts, and sample civic complaints:
```bash
python seed.py
```

### 6. Run the FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
```
- **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 💻 Frontend Setup & Execution (React.js + Tailwind)

### 1. Requirements
Ensure Node.js (v18+) and npm are installed.

### 2. Install & Start Development Server
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 👥 Default Demo Credentials (from `seed.py`)
| Role | Email | Password |
|---|---|---|
| **Super Admin** | `admin@civiclens.gov` | `Admin@123` |
| **Sanitation Officer** | `officer@civiclens.gov` | `Officer@123` |
| **Citizen** | `citizen@civiclens.gov` | `Citizen@123` |

---

## 🧠 AI & Intelligence Pipeline (Hybrid Architecture)

1. **Multilingual Preprocessing** (`backend/app/services/preprocessor.py`):
   - Normalises Hindi, Hinglish, and English text with Indic NLP and Stanza.
   - Preserves negation particles ("nahi", "not"), numbers, and intensity words while filtering noise.

2. **Multilingual Classifier & Decision Model** (`backend/app/services/classifier.py`):
   - **Models**: `LatentAILabs/yama-indic` or fine-tuned `FacebookAI/xlm-roberta-base`.
   - Categorizes raw complaint descriptions into 8 civic categories and subcategories.
   - Extracts factual incident attributes independently: `severity`, `immediate_risk`, `public_exposure`, `ongoing_incident`, `urgency_claim`.

3. **Deterministic Priority Scoring Engine**:
   - Computes weighted formula: `P = 0.35·S + 0.25·I + 0.15·E + 0.10·C + 0.15·T`.
   - **Safety Override**: Live wires, collapsing structures, gas leaks, and active fires immediately trigger `CRITICAL` priority regardless of score.
   - **Time Escalation Guard**: Routine complaints pending over time cap at `HIGH`; only verified safety hazards trigger `CRITICAL`.
   - **Audit-Only Urgency Claims**: Citizen phrases like "very urgent" are logged for officer review but do not inflate the numerical priority score.

4. **Semantic Duplicate Search with FAISS** (`backend/app/services/duplicate_finder.py`):
   - Generates multilingual dense embeddings using Indic BGE-M3 or `BAAI/bge-m3`.
   - Evaluates spatial proximity (`GEO_WINDOW_DEGREES`) and semantic similarity using `faiss.IndexFlatIP`.
   - Independent Corroboration Engine: calculates `C = min(5, 2·log₂(1+N))` from distinct reports.

5. **Automated Department Routing & Dynamic SLA** (`backend/app/services/routing.py`):
   - Assigns primary and secondary handling departments.
   - Enforces SLA floors: `CRITICAL` (2h), `HIGH` (8h), `MEDIUM` (24h), `LOW` (48h).

---

## 🎯 Training Datasets & Multi-Source Configuration

CivicLens uses a **Hybrid Multi-Dataset Architecture** combining real Indian municipal grievances, large-scale civic service requests, and multilingual Indian language datasets:

| Dataset | Records | Source | Role in CivicLens |
|---|---|---|---|
| **BBMP Grievances** | 10,000 | Bengaluru Smart City / Sahaaya 2.0 | Indian municipal routing, ward mappings, local civic issues |
| **NYC 311** | 5,000 | NYC OpenData Socrata API | Large-scale civic issues (potholes, sewers, streetlights) |
| **CPGRAMS** | 5,000 | Indian Central & Pan-India Grievances | Real government grievance language & multilingual text (EN/HI) |
| **COMI-LINGUA** | 2,000 | LingoIITGN (Hugging Face) | Hinglish code-mixed normalisation |
| **🏆 Master Hybrid** | **18,473** | Deduped & Consolidated Master Set | **End-to-End Multilingual Classifier Fine-Tuning** |

### Generate / Re-download Datasets:
```bash
cd backend

# Download all 3 primary datasets + compile Master Hybrid dataset:
python train/download_all_primary_datasets.py

# Or download individual datasets:
python train/configure_bbmp_dataset.py
```

### Launch Model Fine-Tuning on Master Dataset:
```bash
cd backend
python train/train_classifier.py --data_path data/dataset_civiclens_master_hybrid.csv --model_name LatentAILabs/yama-indic --epochs 4
```

### Dataset Structure (Section 3.3 Specification)
Each complaint contains textual & category fields:
- `complaint_text`: Natural complaint in English, Hindi, or Hinglish.
- `language`: Detected or annotated language (`en`, `hi`, `hinglish`).
- `category`: Primary municipal category.
- `subcategory`: Fine-grained incident type.

**Separately Labelled Incident Attributes** (never collapsed into a single label):
- `severity`: (1–5) Extent of physical damage or danger.
- `immediate_risk`: (0 or 1) Whether danger is active and uncontained.
- `public_exposure`: (1–5) Footfall and public vulnerability at the location.
- `ongoing_incident`: (0 or 1) Whether problem is continuously happening.
- `urgency_claim`: (0 or 1) Explicit subjective citizen urgency claim (audit-only).

### Launching Fine-Tuning:
```bash
cd backend

# Option A: Yama-Indic (Indian-language oriented structured decision model)
python train/train_classifier.py --model_name LatentAILabs/yama-indic --epochs 4

# Option B: XLM-RoBERTa-base (Supervised cross-lingual baseline with LoRA)
python train/train_classifier.py --model_name FacebookAI/xlm-roberta-base --use_lora --epochs 4
```

---

## 📂 Project Architecture (Current State)
```text
backend/
├── alembic/                # Alembic database migrations
├── app/
│   ├── api/
│   │   ├── deps.py         # JWT auth & role validation dependencies
│   │   └── v1/
│   │       ├── ai.py          # AI classification & duplicate checking endpoints
│   │       ├── analytics.py   # SLA, ward hotspots, complaint trends
│   │       ├── auth.py        # Login, registration, profile
│   │       ├── complaints.py  # Complaint filing, triaging, status updates, audit
│   │       ├── departments.py # Department management
│   │       └── router.py      # Master v1 API router
│   ├── core/
│   │   ├── config.py       # Pydantic environment settings
│   │   ├── database.py     # SQLAlchemy DB connection & session engine
│   │   └── security.py     # Password hashing & JWT token issuance
│   ├── models/             # SQLAlchemy ORM database models
│   │   ├── audit_log.py
│   │   ├── complaint.py
│   │   ├── department.py
│   │   ├── feedback.py
│   │   └── user.py
│   ├── schemas/            # Pydantic schemas (request/response validation)
│   ├── services/           # AI & Business Logic Engine
│   │   ├── classifier.py       # Hugging Face classification & priority scoring
│   │   ├── duplicate_finder.py # Sentence Transformers + FAISS vector search
│   │   └── routing.py          # Department assignment & dynamic SLA
│   └── main.py             # FastAPI entrypoint with vector warmup & CORS
├── seed.py                 # Initial data populator
└── requirements.txt
```

