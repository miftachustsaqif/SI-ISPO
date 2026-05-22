# SI-ISPO - Sistem Informasi ISPO

## Original Problem Statement
"create this mockup for IISPO service the file is the guideline for it make it same like the file"
User uploaded an HTML mockup file (`180526_SI-ISPO SCI.html`, ~856KB, ~10K lines) for SI-ISPO (Sistem Informasi ISPO — Indonesian Sustainable Palm Oil information system).

## User Choices
- Implementation: **Show exactly like the HTML mockup** (option a)
- Backend: **FastAPI + MongoDB** (option b)
- Scope: **Same exactly as file**

## Architecture
- **Frontend** (`/app/frontend`): React shell renders the original mockup HTML inside a full-screen iframe (preserves 100% of the original UI/JS — Leaflet maps, QR codes, login, registration, public dashboard, app shell, all the screens).
  - `src/App.js` → fullscreen `<iframe src="/si-ispo.html">`
  - `public/si-ispo.html` → exact copy of user's uploaded mockup
- **Backend** (`/app/backend/server.py`): FastAPI + MongoDB scaffolding with CRUD endpoints, matching domain (certificates, companies, audits, stats). Falls back to mockup numbers (892 sertifikat, 7.8M Ha, 725 perusahaan, 18.2M ton) when DB is empty.

## API Endpoints (all `/api`-prefixed)
- `GET /api/` — health check
- `GET /api/stats` — homepage stats (sertifikat aktif, luas Ha, perusahaan, ton produksi)
- `GET/POST /api/certificates`, `GET /api/certificates/{id}`
- `GET/POST /api/companies`
- `GET/POST /api/audits`

## What's Implemented (2026-05-22)
- Static mockup served identically to the source file
- FastAPI backend with MongoDB CRUD for certificates/companies/audits + aggregated stats
- All backend endpoints verified via curl (create + list + stats)

## Backlog / Next
- P1: Wire mockup forms to backend APIs (currently mockup is self-contained dummy data)
- P1: Add authentication (JWT) for real login flow (mockup currently shows static "Masuk" button)
- P2: Add file upload for sertifikat documents (object storage)
- P2: Add reporting/export (PDF, Excel)
- P2: Real-time notifications via WebSocket
