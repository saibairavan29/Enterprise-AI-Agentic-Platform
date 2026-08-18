# Enterprise AI Decision Intelligence Platform

A state-of-the-art enterprise-grade platform that ingests, cleanses, standardizes, and repositories raw enterprise records, evaluating them using Machine Learning models and Rule-Based Profilers to compute Data Quality metrics and Explainable AI (XAI) predictions.

---

## 1. Core Feature Highlights
- **Phase 1 Ingestion Pipeline**: Cryptographic duplicate checking (SHA-256), signature validation, and multi-format support (`.pdf`, `.xlsx`, `.csv`, `.json`, `.txt`, `.png`).
- **Phase 2 Schema Resolution**: Custom resolvers to map varied files into standard enterprise fields with boundary checks preventing substring collisions.
- **Phase 3 Logical Repository**: Private vs Public repository separation (role-based boundary rules) and local file streaming for document previews.
- **Phase 4 EDQI (Explainable AI)**: Weighted quality profiling scoring, RandomForest quality grade classification, confidence metrics, clamped local fallback attributions, and dynamic improvement point recommendations.

---

## 2. Technical Prerequisites
Before setting up the project on a new machine, ensure you have:
- **Python**: Version `3.10` or higher.
- **Node.js**: Version `18.0` or higher (with `npm` package manager).
- **Database**: SQLite3 (default fallback) or PostgreSQL.

---

## 3. Installation & Setup Instructions

### Step A: Clone the Repository
```bash
git clone <your-repository-url>
cd "Enterprise Application"
```

### Step B: Backend (Django) Setup
1. Navigate to the backend root directory (if not already there):
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations to initialize the local database schema:
   ```bash
   python manage.py migrate
   ```
5. (Optional) Run the development server to verify the API backend:
   ```bash
   python manage.py runserver
   ```
   *The backend will boot at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).*

### Step C: Frontend (Vite + React) Setup
1. Open a new terminal window and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Boot the Vite development server:
   ```bash
   npm run dev
   ```
   *The frontend dashboard will boot at [http://localhost:5173/](http://localhost:5173/).*

---

## 4. Verification & Testing

### Running Backend Django Unit Tests
To run the full suite of unit tests, execute:
```bash
cd backend
python manage.py test edqi knowledge_conflict repository ingestion
```
All tests must report `OK`.

### Running Frontend Production Builds
To build the static assets for deployment and confirm there are no compilation issues:
```bash
cd frontend
npm run build
```
Vite assets will compile cleanly under `frontend/dist/`.

---

## 5. Main Directory Structure

```text
├── backend/                  # Django project root
│   ├── core/                 # Shared base logic
│   ├── ingestion/            # Phase 1 & 2 Ingestion pipeline
│   ├── repository/           # Phase 3 Logical repository Views & Models
│   ├── edqi/                 # Phase 4 Explainability & Data Quality models
│   ├── knowledge_conflict/   # Similarity matching & Conflict reviews
│   └── manage.py             # Django entry point
│
├── frontend/                 # Vite + React app root
│   ├── src/
│   │   ├── pages/            # View components (Dashboard.jsx, DataQualityExplainability.jsx)
│   │   ├── context/          # Shared contexts (AuthContext.jsx)
│   │   └── main.jsx          # React app entry point
│   ├── package.json
│   └── vite.config.js
│
├── Uploads/                  # Store path for physical files
│   └── raw/                  # Uploaded raw spreadsheets, images, PDFs
│
├── Project_Documentation.md  # Unified merged system details file
└── PROJECT_PROGRESS.md       # Tracks completion milestones and features
```

---

## 6. How to Deploy to Another Laptop
To upgrade or deploy this project to another laptop:
1. Zip/copy the parent directory (excluding virtual environments and `node_modules` folders to save space).
2. Unzip on the target laptop.
3. Follow the **Installation & Setup Instructions** above (the local database files will rebuild automatically on first migration).
4. Run `npm run build` and `python manage.py test` to confirm setup is fully successful.
