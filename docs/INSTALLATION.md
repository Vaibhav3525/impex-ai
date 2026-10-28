# Installation and Setup Guide

## AI-Powered Global Import–Export Buyer Acquisition & Automation System

This guide walks through configuring and running the complete system locally on **Windows 11**.

---

## 1. System Requirements

- **Operating System:** Windows 11 (64-bit)
- **Python:** 3.12+ (tested on Python 3.12.10)
- **Node.js:** v18.17+ or v20+ (tested on Node.js v20)
- **Package Managers:** PowerShell, `pip`, `npm`
- **Database:** SQLite (default for MVP; no external database server needed)

---

## 2. Repository Layout

```
d:\antigravity\
├── backend\
│   ├── app\
│   │   ├── api\               # FastAPI REST endpoints
│   │   ├── core\              # Database and settings configuration
│   │   ├── models\            # SQLAlchemy models (Lead, Deal, Outreach, etc.)
│   │   ├── schemas\           # Pydantic v2 validation models
│   │   └── services\          # Domain logic (Verification, Scoring, Risk, SMTP)
│   ├── tests\                 # 14-day test suite (119+ unit tests)
│   ├── venv\                  # Python virtual environment
│   └── requirements.txt       # Backend dependencies
├── frontend\
│   ├── src\
│   │   ├── app\               # Next.js 14 App Router UI
│   │   └── lib\               # API client
│   ├── package.json
│   └── tailwind.config.ts
├── docs\                      # Architecture, verification, deliverability docs
├── pytest.ini
└── .env.example
```

---

## 3. Backend Setup

### Step 3.1: Activate Python Virtual Environment
Open PowerShell:
```powershell
cd d:\antigravity\backend
& "d:\antigravity\backend\venv\Scripts\Activate.ps1"
```
*(If creating a fresh virtual environment)*:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3.2: Environment Configuration
Copy `.env.example` to `.env`:
```powershell
copy ..\.env.example .env
```
Key configuration parameters:
- `DEBUG=True`
- `DATABASE_URL=sqlite:///./impex_leads.db`
- `OUTREACH_APPROVAL_MODE=Assisted` (Default Mode A for mandatory human signoff)
- `DAILY_DISPATCH_LIMIT=50`
- `HOURLY_DISPATCH_LIMIT=10`
- Optional SMTP parameters for live email dispatch (defaults to mock dispatch if unconfigured).

### Step 3.3: Verify Database Schema
The SQLite database schema automatically initializes on application startup:
```powershell
python -c "from app.core.database import init_db; init_db()"
```

### Step 3.4: Run the Backend Test Suite
```powershell
cd d:\antigravity
& "d:\antigravity\backend\venv\Scripts\pytest.exe" -v
```
All 119+ unit tests across Days 1–14 should pass in under 10 seconds.

### Step 3.5: Start the FastAPI Server
```powershell
cd d:\antigravity\backend
& "d:\antigravity\backend\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base: `http://localhost:8000/api/v1`
- Interactive Swagger UI: `http://localhost:8000/docs`
- Redoc UI: `http://localhost:8000/redoc`

---

## 4. Frontend Setup

### Step 4.1: Install Dependencies
Open a second PowerShell window:
```powershell
cd d:\antigravity\frontend
npm.cmd install
```

### Step 4.2: Build and Validate
```powershell
npm.cmd run build
```

### Step 4.3: Start the Development Server
```powershell
npm.cmd run dev
```
- Access the UI: `http://localhost:3000`
- Live features available:
  - Buyer Directory & 100-Point Audit Modal
  - 15-Stage CRM Kanban Board
  - Mode A Assisted Outreach Approval Queue
  - Payment Risk Guardian Alerts
  - Product Profile Matching & Lead Scorer

---

## 5. Security & Operating Invariants

1. **Zero Data Fabrication:** The system never creates fictitious emails, phone numbers, trading licenses, or contact details.
2. **Mode A Assisted Outreach by Default:** No automated outbound email is dispatched without manual human approval in the queue.
3. **Qualification != Payment Risk:** Commercial suitability is scored independently from financial non-payment risk.
4. **UN Comtrade Statistics Invariant:** Aggregate country trade data is never cited as individual buyer proof.

