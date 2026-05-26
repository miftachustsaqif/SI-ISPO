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

## Update — 2026-05-25
### Added Features
- **Pemetaan Lahan** (`pemetaan-lahan` page): Live Leaflet polygon map with OpenStreetMap, color-coded by ISPO status. Click polygon → detail panel. Draw new polygon via leaflet-draw, save to backend.
- **Document upload per plot**: Object storage integration (Emergent obj store), upload PDF/JPG/PNG evidence files (sertifikat lahan, foto drone, surat tanah) attached to each land plot.
- **Produk & Traceability** (`produk-trace` page): Full product catalog across 5 categories (Hulu/Rafinasi/Pangan/Oleokimia/Bioenergi) with kategori filter & search.
- **Traceability tree modal**: Recursive upstream chain from any product down to TBS source + origin plot (with land details: pemilik, luas, status ISPO).
- **Seeded demo data**: 5 plots (Riau, Sumut, Kalbar, Aceh, Jambi) + 22 products covering the full chain TBS → CPO/PKO → RBD → Olein/Stearin → Minyak Goreng/Margarin/Specialty Fats/Pakan + Fatty Acid → Sabun/Kosmetik + Metil Ester → Biodiesel + Biomassa + Biogas.

### New Backend Endpoints
- `GET/POST/PUT/DELETE /api/plots`, `GET /api/plots/{id}`
- `POST /api/plots/{id}/documents` (multipart upload → object storage)
- `GET /api/files/{path:path}` (serve from object storage)
- `GET/POST /api/products`, `GET /api/products/{id}`
- `GET /api/products/{id}/trace` (recursive parent chain → origin plot)
- `POST /api/seed`

### Implementation Note
New features are **injected** into the existing mockup HTML via a single appended `<script>` block (does not break original mockup). New nav items added to: LS, Pekebun, PKS, Perkebunan, Bioenergi, Buyer, Auditor roles.

## Update — Super Admin Feature
### Added
- **Super Admin role** (`superadmin`) with custom sidebar (Dashboard Admin, Manajemen User, Pemetaan Lahan, Produk, Semua Sertifikat/Audit/Perusahaan).
- **🛡️ Super Admin demo login button** — appears in login page demo grid.
- **Dashboard Super Admin** — stats overview (users by role, products by kategori, plots, documents) + quick action cards.
- **Manajemen User & Role** — table of all users with: inline role dropdown (instant change), status toggle (Active/Suspended), delete, search & filter, "+ Tambah User Baru" modal.
- **Read-only admin views**: Semua Sertifikat, Semua Audit, Semua Perusahaan.

### Backend
- `GET/POST /api/users`, `GET /api/users/{id}` implicit via list filter
- `PUT /api/users/{id}/role`, `PUT /api/users/{id}/status`
- `DELETE /api/users/{id}`
- `GET /api/admin/overview` (aggregate stats)
- Seeded 10 users (1 superadmin + 9 role personas).

### Credentials
- Admin demo login: click "🛡️ Super Admin (Lihat & Atur Semua)" on login page (one-click, no password needed in mockup).
- Backend account: `admin@si-ispo.go.id` (role: superadmin).

## Update — Marketplace + Product Detail + Supplier Form
### Added
- **Marketplace ISPO** (`marketplace`) — Grid of products available for sale, each card has "✓ HULU→HILIR TRACKED" badge, price/satuan, min order, produsen, lokasi gudang, category filter.
- **Product Detail page** (`produk-detail`) — Full product view: large icon, deskripsi, spesifikasi teknis (parsed from `|`-separated string), harga & min order, Request Quote button, **inline traceability tree** showing every parent product down to TBS + origin plot (with ISPO status).
- **Tambah Produk Baru modal** — Available to supplier roles (pekebun, pks, perkebunan, bioenergy, superadmin) via button on Produk page. Form has mandatory "Rantai Traceability" section that adapts:
  - Hulu (TBS) → must select Kebun Asal (plot)
  - Non-Hulu → must select 1+ parent products (multi-select from existing products)
- Marketplace pricing (12 of 22 seed products have prices), spesifikasi, deskripsi, lokasi gudang.

### Backend Validation (enforced)
- `POST /api/products` rejects:
  - Hulu without `plot_id` → 400 "wajib mencantumkan plot_id (kebun asal)"
  - Non-Hulu without `parent_ids` → 400 "wajib mencantumkan minimal 1 parent_id"
  - Invalid plot_id or parent_id → 400
- New endpoint: `GET /api/marketplace?kategori=X` (filters `tersedia_marketplace=true`)
- Product schema extended with: `harga`, `mata_uang`, `tersedia_marketplace`, `deskripsi`, `spesifikasi`, `minimum_order`, `lokasi_gudang`

### Role-Based Access
- All roles (incl. buyer/auditor/reviewer) can browse Marketplace & view Product Detail
- Only supplier roles see "+ Tambah Produk Baru" button on Produk page
- Super Admin nav now includes Marketplace ISPO too
