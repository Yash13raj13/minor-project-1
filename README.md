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

## 🧠 AI & Intelligence Pipeline
1. **Complaint Categorization & Priority Scoring** (`backend/app/services/classifier.py`):
   - Categorizes raw complaint descriptions into municipal departments (`ROADS`, `SANITATION`, `WATER`, `POWER`, `HEALTH`).
   - Analyzes safety keywords and urgency indicators to assign appropriate priority levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
2. **Semantic Duplicate Search with FAISS** (`backend/app/services/duplicate_finder.py`):
   - Generates 384-dimensional dense sentence embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
   - Normalizes vectors and performs exact cosine similarity search via `faiss.IndexFlatIP`.
   - Automatically detects redundant reports and suggests ticket merging.
3. **Automated Department Routing & Dynamic SLA** (`backend/app/services/routing.py`):
   - Computes target SLA resolution deadlines based on department baseline and priority multipliers.

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

