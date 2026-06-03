<div align="center">

# 🌬️ Vayu Drishti
### Hyper-Local AQI Intelligence Platform for Delhi

[![Platform Status](https://img.shields.io/badge/Platform-Live%20%26%20Operational-brightgreen?style=for-the-badge)](https://github.com/ABHICODZ/Breath-Analyzser)
[![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=PyTorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

*Transforming Delhi's sparse sensor grid into a living, ward-level air quality intelligence map.*

</div>

---

## 📌 The Problem We Solve

Delhi's air quality monitoring infrastructure consists of a **handful of CPCB stations** spread across a city of 32 million people spanning 1,484 km². Entire neighborhoods, residential colonies, schools, and industrial zones exist in blind spots — with no real data on the air residents breathe.

**Vayu Drishti eliminates this blind spot entirely.**

Rather than waiting for physical sensor infrastructure to scale, our platform uses a custom-trained AI model to interpolate and predict precise PM2.5 concentrations for *every coordinate* across all *251 wards of Delhi* — in real-time, continuously, at micro-climate resolution.

---

## 🏛️ Platform Architecture

Vayu Drishti is a full-stack, cloud-ready platform with four integrated layers:

```text
┌─────────────────────────────────────────────────────────────┐
│                 VAYU DRISHTI PLATFORM                       │
├────────────────┬────────────────┬──────────────┬────────────┤
│  React         │  FastAPI       │  PyTorch     │  Supabase  │
│  Frontend      │  Backend       │  ML Engine   │  Auth & DB │
│  (Vite +       │  (Python +     │  (Temporal   │  (Role     │
│   Leaflet)     │   CORS)        │   SpatialNet)│   Based)   │
└────────────────┴────────────────┴──────────────┴────────────┘
```

### Core Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React + Vite + TypeScript | Interactive spatial AQI map & user interface |
| **Styling** | Tailwind CSS | Responsive, dark-mode UI |
| **Mapping** | Leaflet.js | Real-time, zoomable Delhi ward overlays |
| **Backend API** | FastAPI (Python) | REST API serving live AQI predictions |
| **ML Engine** | PyTorch (`TemporalSpatialNet`) | Spatial interpolation neural network |
| **Authentication** | Supabase Auth + JWT | Role-based access (citizen / admin / officer) |
| **Database** | Supabase (PostgreSQL) | User profiles, complaints, tasks, session logs |
| **Satellite Data** | Google Earth Engine (Sentinel-5P) | Live atmospheric telemetry feeds |
| **Policy Engine** | Math Model + Multi-Agent LLM | Auto-generated municipal action directives & simulation |
| **Deployment** | Docker + Google Cloud Run | Containerized production environment |

---

## 🚀 Key Features

### 🗺️ 1. Hyper-Local AQI Map
The centerpiece of Vayu Drishti is a live, interactive Leaflet.js map overlaid on all 251 Delhi municipal wards. Instead of showing only the 20-odd hardware stations, the ML engine interpolates predicted PM2.5 values for every unmonitored location on the map.

- **Ward-level granularity** — every one of Delhi's 251 wards has an individual prediction.
- **Dynamic color coding** — Green → Satisfactory → Moderate → Poor → Very Poor → Severe.
- **Live refresh** — the backend autonomously runs the TNN inference loop every 5 minutes.

### 🧠 2. The AI Model (`TemporalSpatialNet`)
The platform's prediction engine is a custom PyTorch deep neural network trained on real CPCB/Kaggle Delhi AQI datasets. It processes 7 environment variables per location and outputs an accurate PM2.5 value in µg/m³.

**Feature Inputs (7 total):**
- **Spatial:** Latitude, Longitude, Distance from Delhi Centroid
- **Chemical:** SO2, NO2, PM10, CO (ppb) from nearby stations

### 🛡️ 3. Enterprise Admin Command Center
The platform includes a fully secured, role-gated Enterprise Admin Dashboard. Access is controlled via Supabase Role-Based Access Control — only users with `admin` or `officer` roles are granted entry.

**Admin Capabilities:**
- **Live Operations Monitoring:** Real-time AQI station feeds, dynamic heatmaps, and critical hotspot tracking.
- **Digital Twin Policy Simulator:** A mathematical simulator using CPCB source apportionment data to predict exactly how AQI will respond to specific interventions (e.g. 50% traffic reduction, construction bans) matching GRAP regulatory stages.
- **Deep Analytics:** City-wide statistical summaries, top worst/best wards, and AQI distribution metrics.

### 🏛️ 4. AI Governance Council
A multi-agent LLM framework that simulates a real municipal policy council. 5 distinct AI personas (Scientist, Public Health Officer, Economist, Enforcement Officer, Citizen) hold a 3-round debate on proposed interventions, outputting a clear consensus, voting tally, and final action recommendation for administrators.

### 🛰️ 5. Satellite Intelligence (Google Earth Engine)
The backend connects live to **Sentinel-5P TROPOMI** atmospheric sensors via the Google Earth Engine Python API. This detects pollution anomalies invisible to sparse ground-station grids (like biomass burning via CO density or construction dust via Aerosol Index).

### 👤 6. User Profile System
Citizens logging in via Supabase authentication have access to personalized health alerts. A specialized algorithm calculates individualized "safe outdoor exposure" times based on real-time AQI, the user's age, and whether they have asthma.

---

## 📂 Project Structure

```text
VayuDrishti/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory + CORS + request logging
│   │   ├── api/                     # All REST endpoints (Dashboard, GEE, Admin, Council)
│   │   ├── services/                # ML Engine, Policy Simulator, Satellite services
│   │   ├── db/                      # Supabase DB models & SQLAlchemy connections
│   │   └── core/                    # Config, settings, celery tasks
│   ├── train_vayu_v2.py             # 🔬 Core ML training scripts
│   └── requirements.txt             # Python dependencies
├── web-frontend/
│   ├── src/
│   │   ├── App.tsx                  # Main map dashboard & application routing
│   │   ├── pages/
│   │   │   ├── EnterpriseAdminDashboard.tsx  # Advanced Command Center UI
│   │   │   ├── AIAgentsCouncil.tsx           # Multi-agent simulation UI
│   │   │   └── UserProfile.tsx               # Citizen profile & history
│   │   ├── components/
│   │   │   └── LeafletMap.tsx       # Real-time data visualization
│   │   └── lib/apiClient.ts         # Robust frontend API client
│   └── package.json
├── supabase_schema.sql              # DB schema for profiles, complaints, tasks
└── README.md
```

---

## 🛠️ Setup & Running Locally

### Prerequisites
- Python 3.9+
- Node.js 18+
- A Supabase project (free tier works)

### 1. Backend
```bash
cd backend
pip install -r requirements.txt

# Copy and fill in your environment variables
cp .env.example .env

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend
```bash
cd web-frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 🔬 Training the ML Model

The model training scripts live in the `backend/` directory. To retrain the production model:

```bash
cd backend
python train_vayu_real_data.py
```

**Outputs:**
- `app/services/vayu_spatial_PRODUCTION.pt` — Production model weights
- Scalers for live inference

---

<div align="center">
  <strong>Built to give every citizen of Delhi the right to breathe transparently.</strong><br/>
  <i>One ward at a time.</i>
</div>
