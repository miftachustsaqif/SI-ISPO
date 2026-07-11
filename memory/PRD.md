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

## Update — QR Code + Big Seed + ISPO Certification
### Added
- **QR Code generator** per produk di Product Detail page (pakai `qrcodejs` lib yang sudah ada di mockup). Hijau ISPO color (#1A5C1A), tombol Copy Link & Download PNG. QR encode URL `/si-ispo.html?trace=<product_id>`.
- **Public Trace mode** — buka `/si-ispo.html?trace=<product_id>` langsung tanpa login. Header hijau khusus, tombol "Login ke Sistem". Cocok untuk konsumen yang scan QR di kemasan produk fisik (buyer EU EUDR compliance scenarios).
- **Massive seed expansion**: dari 22 → **58 produk** terdistribusi:
  - Hulu (TBS): 8 batch dari 5 kebun (multiple panen periods)
  - Rafinasi: 16 (CPO ×7, PKO ×2, PKC ×1, RBD ×2, Olein ×2, Stearin ×2)
  - Pangan: 12 (Minyak Goreng 3 brand × multi-size, Margarin ×2, Shortening, Specialty Fats ×2, Pakan Ternak ×2)
  - Oleokimia: 14 (Fatty Acid ×2, Gliserol ×2, ME ×2, Sabun ×2, Deterjen ×2, Kosmetik ×4)
  - Bioenergi: 8 (Biodiesel B30/B40/B100, Biomassa PKS/EFB/Mesocarp Fiber, Biogas ×2 plant)
- **Certification fields**: `ispo_certified`, `sertifikat_ispo` (No. ISPO/CERT/2024/XXXX), `halal_certified`, `siap_jual` (Siap Jual/Habis/Reserved/Draft).
- **Marketplace cards** show: ✓ TRACKED, ✓ ISPO, ☪ HALAL, HABIS/RESERVED badges + kategori.
- **Product Detail badges**: ✓ HULU→HILIR TRACKED, ✓ ISPO BERSERTIFIKAT (with cert number ISPO/CERT/2024/XXXX), ☪ HALAL MUI, status Siap Jual/Habis/Reserved.

### Stats (after big seed)
- 58 products • 51 marketplace-listed • 55 ISPO-certified • 51 Siap Jual
- 5 plots • 11 users • Full hulu→hilir chains for Minyak Goreng/Margarin/Sabun/Biodiesel/Kosmetik

### Public Trace URL format
`https://<host>/si-ispo.html?trace=<product_id>` — printable QR code, no auth required.

## Update — Pesanan Saya + Admin Orders + Seed Orders
### Added
- **Pesanan Saya** page (buyer role): order history with status badges (Pending/Dikonfirmasi/Dikirim/Diterima/Selesai/Dibatalkan), search & filter, total stats (Total/Sedang Proses/Selesai/Total Nilai).
- **Semua Pesanan** page (Super Admin): same view but shows ALL orders system-wide with buyer→supplier flow visible (🏪 → 🏭).
- **Detail + Trace button per order** → opens the existing Product Detail page (with QR code + full hulu→hilir traceability tree to the originating kebun/TBS).
- **Quick Trace button** → opens the inline modal traceability view.
- **32 seed orders** across 8 international buyers (Global Oils Trading, EuroPalm Importers GmbH, Sakura Trading Co., Mumbai Oils Pvt., Hotel Group Indonesia, etc.) ordering 51 different marketplace products with realistic statuses, dates, prices, and catatan ("Pengiriman urgent untuk Lebaran", "Ekspor ke pasar Eropa EUDR compliant", "Persiapan stok ramadhan", etc.).

### Backend Endpoints
- `GET /api/orders?buyer_email=X&supplier=Y&status=Z`
- `GET /api/orders/{id}`
- `POST /api/orders` — validates product exists & qty>0, auto-computes harga_total
- `PUT /api/orders/{id}/status` — auto-fills tgl_kirim/tgl_terima based on status transition
- `POST /api/seed-orders` (standalone) — re-seed orders only
- `/api/seed` now also seeds orders (returns `{plots, products, orders}`)

### Stats (current)
- 5 plots • 11 users • 58 products (51 marketplace) • **32 orders** (Rp 27.47 Billion total value)
- Orders distribution: 19 Selesai, 5 Dikonfirmasi, 3 Dikirim, 3 Pending, 2 Diterima

### Flow Demonstration
Buyer click order → see product detail with **complete chain**: e.g. "EcoWash Sabun Cuci Piring (DET-002) ← Methyl Laurate (ME-002) ← PKO Riau (PKO-RIA-001) ← TBS Riau A1 (TBS-RIA-001) ← Kebun Inti Riau A1 (1250.5 ha, Tersertifikasi ISPO sejak 2012)". Admin sees same chain plus the buyer who ordered.

## Update — Clean Public Landing Page
### Added
- **New clean landing page** at `/landing.html` — replaces the previous login-first entry. Matches user's provided reference design.
- **Sticky white navbar** with SI-ISPO brand, menu (Beranda/Cari Sertifikat/Berita/Regulasi/FAQ/Peta Sebaran), ID language selector, Login & Registrasi buttons.
- **Split hero**: dark green background with palm oil plantation photo overlay + "Transparansi Sawit, Keberlanjutan untuk Indonesia" title + search bar + Login/Registrasi CTAs (left) — Statistik Terbuka card with 4 mini stat tiles (Sertifikat, Perusahaan, Luas Ha, Produksi) + donut chart (Sebaran Sertifikat Berdasarkan Jenis: Hulu/Hilir/Bioenergi) + mini Indonesia map (right).
- **5 quick action cards**: Cari Sertifikat, Cari Perusahaan, Cari Produk, Peta Sebaran, Berita & Publikasi — each with color-coded icon.
- **Content row**: Berita Terbaru list with news thumbnails + dates, big Leaflet map showing certified plots polygons, "Kenapa ISPO Penting?" dark green info card.
- **Footer** with copyright, quick links (Tentang, Privasi, Syarat, Kontak), social icons (Facebook, Twitter, Instagram, YouTube).
- **Fonts**: Plus Jakarta Sans (headings + body), JetBrains Mono (accents) — distinctive vs default Inter.
- **All CTA buttons** deep-link to `/si-ispo.html` (the full app with login flow) so nothing is broken.
- **Stats endpoint** now returns showcase baseline (893 certs, 726 companies, 7.8M ha) + any real DB additions on top.

### React entry
- `App.js` iframe now loads `/landing.html` by default (was `/si-ispo.html`).

## Update — Clean UI Overhaul for Login + Internal Pages
### Added
- **Comprehensive CSS override** injected at top of `si-ispo.html` — applies globally with `!important` to soften every visual layer without touching original mockup logic.
- **Font**: Plus Jakarta Sans applied everywhere (matches landing page — was inconsistent before)
- **Softer color tokens**: lighter borders (#EDEFED), softer shadows, muted background (#FAFBFA)
- **Whitespace expansion**: cards 22-24px padding, page-header 26px vertical, main content 26-32px padding, stat-card 22px, form field spacing 16px
- **Cleaner buttons**: 10px 18px padding, softer green shadow, hover lift effect
- **Cleaner inputs**: 11-14px padding, 9px radius, green focus ring
- **Cleaner tables**: 12-14px row padding, uppercase 11px headers, subtle hover
- **Cleaner sidebar nav**: 10-12px padding, subtle white transparency for active/hover
- **Cleaner topbar**: 14x28 padding, semi-transparent white with backdrop blur
- **Login page redesign**: airy form, clean demo login button grid (2-column), highlighted Super Admin gradient CTA, larger focus ring on inputs
- **Marketplace cards**: 14px radius, subtle lift on hover
- **Progress bars**: softer green, 6px height
- **Custom scrollbar**: subtle 8px grey rounded thumb

### Impact
Login page and every internal dashboard page (Dashboard, Marketplace, Pesanan Saya, Traceability, Peta, Admin views) now share consistent, modern, spacious design language with the new landing page.

## Update — Whitespace Overhaul v2 (Landing-Level Airy)
### Changes
- **Content padding**: 40x48px (was 26x32)
- **Cards**: 30x32px padding (was 22x24), 16px radius, 22px card-title bottom margin (was 16)
- **Stat cards**: 26x28px padding, 44px icons, 30px value font, 20px icon margin-bottom, 32px stats-row bottom-margin (was 22)
- **Page header**: 32px bottom padding (was 22), 30px h1 (was 26), 10px h1-to-p gap
- **Sidebar**: 260px width, 12x14px nav padding, 4px gap between items, 12x14px nb items with 3px margin
- **Topbar**: 18x40px padding (was 14x28), 68px min-height
- **Tables**: 16-22px header padding, 18-22px row padding (was 12-16 / 14-16)
- **Login form**: 40px padding, single-column demo buttons with 13-16px padding, 50px Super Admin CTA, 14-18px form field spacing
- **Grid layouts**: Force 20px gap on all `grid-template-columns` layouts
- **Section rhythm**: 32px+ vertical space between major sections

## Update — Content Max-Width + Empty States
### Added
- **Content max-width cap**: `#main-page` set to `max-width: 1440px; margin: 0 auto`. At 1600px+ viewports content is centered with additional side padding (60px vs 48px default). Prevents ugly stretching on ultra-wide monitors.
- **Reusable `emptyState({icon, title, subtitle, cta, cta2, testid})` helper** with:
  - Circular gradient background (soft green) with SVG illustration
  - 9 built-in icon options: box, cart, search, plot, people, cert, doc, audit, building
  - Big heading + subtitle + one or two CTA buttons (primary green + secondary outline)
  - Hover lift effect on CTAs
- **Empty state applied to**:
  - Marketplace grid (no products in category) → "Reset Filter" CTA
  - Produk & Traceability table (no products / no search match) → for suppliers: "+ Tambah Produk Baru", for viewers: "Reset Pencarian"
  - Pemetaan Lahan sidebar list (no plots) → "✏️ Tambah Polygon di Peta" CTA
  - Pesanan Saya / Admin Orders (no orders / no filter match) → for buyer: "🛒 Jelajahi Marketplace", for admin: info-only
  - Admin Users (no users / no filter match) → "+ Tambah User Baru" or "Reset Filter"
  - Admin Certificates/Audits/Companies → descriptive empty states with context

### Visual pattern
Every empty state uses the same design: 120px circle with soft green gradient (#F5F8F4 → #E7F3E4), 60px green SVG icon inside, 17px bold heading, 13.5px muted subtitle capped at 380px width, then 1-2 pill CTAs with green primary style.

## Update — Layout Refinement (Sidebar White + Content Fix)
### Changes
- **Sidebar redesigned**: Changed from full dark green gradient to white background with subtle border. Text is dark (#3C4A42 default, #0F1B15 on hover). Active item: soft green background (#E7F3E4) with 3px green left-accent bar. Icons: subtle green tint with .85 opacity default. Sidebar brand section and partner-logos strip: white with soft borders.
- **Content padding rebalanced**: 28px vertical × 36px horizontal (was 40×48). Removed `max-width: 1440px; margin: 0 auto` — content now fills available width naturally (fixed awkward right-side whitespace).
- **Cards proportional**: 22×24 padding (was 30×32), 12px radius (was 16px), 14px card title (was 15px)
- **Stat cards**: 20×22 padding, 38px icons (was 44), 24px value font (was 30px), 10.5px uppercase labels
- **Page header**: 22px h1 (was 30px), 22px bottom padding (was 32px)
- **Topbar**: 14×32 padding, 60px min-height, solid white bg
- **Responsive**: 32×48 padding at ≥1600px, 24×24 at ≤1200px
