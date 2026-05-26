from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query, Form
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import requests
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="SI-ISPO API")
api_router = APIRouter(prefix="/api")

# ─────────── Object Storage (Emergent) ───────────
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "si-ispo"
storage_key: Optional[str] = None
logger = logging.getLogger(__name__)


def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    if not EMERGENT_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY not set")
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ─────────── Models ───────────
class StatsOut(BaseModel):
    sertifikat_aktif: int
    luas_ha: float
    perusahaan: int
    ton_produksi: float


class Certificate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nomor: str
    pemegang: str
    tipe: str
    status: str = "Aktif"
    luas_ha: float = 0
    tgl_terbit: str
    tgl_kadaluarsa: str
    lembaga_sertifikasi: str = "LS SUCOFINDO"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CertificateCreate(BaseModel):
    nomor: str
    pemegang: str
    tipe: str
    status: str = "Aktif"
    luas_ha: float = 0
    tgl_terbit: str
    tgl_kadaluarsa: str
    lembaga_sertifikasi: Optional[str] = "LS SUCOFINDO"


class Company(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nama: str
    npwp: Optional[str] = None
    alamat: Optional[str] = None
    provinsi: Optional[str] = None
    tipe: str = "Perusahaan"
    luas_ha: float = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CompanyCreate(BaseModel):
    nama: str
    npwp: Optional[str] = None
    alamat: Optional[str] = None
    provinsi: Optional[str] = None
    tipe: str = "Perusahaan"
    luas_ha: float = 0


class Audit(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nomor: str
    perusahaan: str
    auditor: str
    tipe: str
    tgl_audit: str
    status: str = "Terjadwal"
    temuan_major: int = 0
    temuan_minor: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditCreate(BaseModel):
    nomor: str
    perusahaan: str
    auditor: str
    tipe: str
    tgl_audit: str
    status: Optional[str] = "Terjadwal"
    temuan_major: int = 0
    temuan_minor: int = 0


class Plot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nama: str
    pemilik: str
    provinsi: str
    kabupaten: Optional[str] = None
    luas_ha: float
    status_ispo: str = "Belum Sertifikasi"  # Belum, Proses, Tersertifikasi, Suspend
    polygon: List[List[float]] = []  # [[lat, lng], ...]
    centroid: Optional[List[float]] = None  # [lat, lng]
    tahun_tanam: Optional[int] = None
    catatan: Optional[str] = None
    documents: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlotCreate(BaseModel):
    nama: str
    pemilik: str
    provinsi: str
    kabupaten: Optional[str] = None
    luas_ha: float = 0
    status_ispo: Optional[str] = "Belum Sertifikasi"
    polygon: List[List[float]] = []
    centroid: Optional[List[float]] = None
    tahun_tanam: Optional[int] = None
    catatan: Optional[str] = None


class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kode: str
    nama: str
    kategori: str  # 'Hulu', 'Rafinasi', 'Pangan', 'Oleokimia', 'Bioenergi'
    jenis: str
    produsen: str
    jumlah: float = 0
    satuan: str = "ton"
    batch_date: Optional[str] = None
    plot_id: Optional[str] = None  # for TBS — origin plot (required for Hulu)
    parent_ids: List[str] = []  # upstream products (required for non-Hulu)
    status: str = "Active"
    catatan: Optional[str] = None
    # Marketplace fields
    harga: Optional[float] = None
    mata_uang: str = "IDR"
    tersedia_marketplace: bool = False
    deskripsi: Optional[str] = None
    spesifikasi: Optional[str] = None
    minimum_order: Optional[float] = None
    lokasi_gudang: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductCreate(BaseModel):
    kode: str
    nama: str
    kategori: str
    jenis: str
    produsen: str
    jumlah: float = 0
    satuan: str = "ton"
    batch_date: Optional[str] = None
    plot_id: Optional[str] = None
    parent_ids: List[str] = []
    catatan: Optional[str] = None
    harga: Optional[float] = None
    mata_uang: Optional[str] = "IDR"
    tersedia_marketplace: Optional[bool] = False
    deskripsi: Optional[str] = None
    spesifikasi: Optional[str] = None
    minimum_order: Optional[float] = None
    lokasi_gudang: Optional[str] = None


VALID_ROLES = ['superadmin', 'ls', 'pekebun', 'pks', 'buyer', 'auditor', 'auditor_int',
               'reviewer', 'perkebunan', 'bioenergy']


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    nama: str
    org: Optional[str] = None
    role: str
    status: str = "Active"  # Active / Suspended
    last_login: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreate(BaseModel):
    email: str
    nama: str
    org: Optional[str] = None
    role: str
    status: Optional[str] = "Active"


class RoleUpdate(BaseModel):
    role: str


class StatusUpdate(BaseModel):
    status: str


# ─────────── Routes ───────────
@api_router.get("/")
async def root():
    return {"app": "SI-ISPO", "status": "ok"}


@api_router.get("/stats", response_model=StatsOut)
async def get_stats():
    sertifikat_aktif = await db.certificates.count_documents({"status": "Aktif"})
    perusahaan = await db.companies.count_documents({})
    pipeline_ha = [{"$group": {"_id": None, "total": {"$sum": "$luas_ha"}}}]
    cert_ha = await db.certificates.aggregate(pipeline_ha).to_list(1)
    luas_ha = float(cert_ha[0]["total"]) if cert_ha else 0.0
    ton_produksi = float(os.environ.get("STATIC_TON_PRODUKSI", "18200000"))
    if sertifikat_aktif == 0 and perusahaan == 0:
        return StatsOut(sertifikat_aktif=892, luas_ha=7_800_000, perusahaan=725, ton_produksi=18_200_000)
    return StatsOut(
        sertifikat_aktif=sertifikat_aktif,
        luas_ha=luas_ha if luas_ha > 0 else 7_800_000,
        perusahaan=perusahaan,
        ton_produksi=ton_produksi,
    )


# Certificates
@api_router.get("/certificates", response_model=List[Certificate])
async def list_certificates():
    items = await db.certificates.find({}, {"_id": 0}).to_list(1000)
    for c in items:
        if isinstance(c.get("created_at"), str):
            c["created_at"] = datetime.fromisoformat(c["created_at"])
    return items


@api_router.post("/certificates", response_model=Certificate)
async def create_certificate(payload: CertificateCreate):
    cert = Certificate(**payload.model_dump())
    doc = cert.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.certificates.insert_one(doc)
    return cert


@api_router.get("/certificates/{cert_id}", response_model=Certificate)
async def get_certificate(cert_id: str):
    doc = await db.certificates.find_one({"id": cert_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return doc


# Companies
@api_router.get("/companies", response_model=List[Company])
async def list_companies():
    items = await db.companies.find({}, {"_id": 0}).to_list(1000)
    for c in items:
        if isinstance(c.get("created_at"), str):
            c["created_at"] = datetime.fromisoformat(c["created_at"])
    return items


@api_router.post("/companies", response_model=Company)
async def create_company(payload: CompanyCreate):
    obj = Company(**payload.model_dump())
    doc = obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.companies.insert_one(doc)
    return obj


# Audits
@api_router.get("/audits", response_model=List[Audit])
async def list_audits():
    items = await db.audits.find({}, {"_id": 0}).to_list(1000)
    for a in items:
        if isinstance(a.get("created_at"), str):
            a["created_at"] = datetime.fromisoformat(a["created_at"])
    return items


@api_router.post("/audits", response_model=Audit)
async def create_audit(payload: AuditCreate):
    obj = Audit(**payload.model_dump())
    doc = obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.audits.insert_one(doc)
    return obj


# Plots
@api_router.get("/plots", response_model=List[Plot])
async def list_plots():
    items = await db.plots.find({}, {"_id": 0}).to_list(1000)
    for p in items:
        if isinstance(p.get("created_at"), str):
            p["created_at"] = datetime.fromisoformat(p["created_at"])
    return items


@api_router.get("/plots/{plot_id}", response_model=Plot)
async def get_plot(plot_id: str):
    doc = await db.plots.find_one({"id": plot_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Plot not found")
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return doc


@api_router.post("/plots", response_model=Plot)
async def create_plot(payload: PlotCreate):
    obj = Plot(**payload.model_dump())
    doc = obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.plots.insert_one(doc)
    return obj


@api_router.put("/plots/{plot_id}", response_model=Plot)
async def update_plot(plot_id: str, payload: PlotCreate):
    update_data = payload.model_dump()
    result = await db.plots.find_one_and_update(
        {"id": plot_id},
        {"$set": update_data},
        return_document=True,
        projection={"_id": 0}
    )
    if not result:
        raise HTTPException(status_code=404, detail="Plot not found")
    if isinstance(result.get("created_at"), str):
        result["created_at"] = datetime.fromisoformat(result["created_at"])
    return result


@api_router.delete("/plots/{plot_id}")
async def delete_plot(plot_id: str):
    res = await db.plots.delete_one({"id": plot_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Plot not found")
    return {"ok": True}


# Documents (per plot)
@api_router.post("/plots/{plot_id}/documents")
async def upload_plot_document(plot_id: str, file: UploadFile = File(...), label: str = Form("")):
    plot = await db.plots.find_one({"id": plot_id}, {"_id": 0})
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")
    ext = (file.filename or "file.bin").rsplit(".", 1)[-1].lower()
    doc_id = str(uuid.uuid4())
    storage_path = f"{APP_NAME}/plots/{plot_id}/{doc_id}.{ext}"
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    put_object(storage_path, data, content_type)
    doc_meta = {
        "id": doc_id,
        "label": label or file.filename,
        "filename": file.filename,
        "content_type": content_type,
        "size": len(data),
        "storage_path": storage_path,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.plots.update_one({"id": plot_id}, {"$push": {"documents": doc_meta}})
    return doc_meta


@api_router.get("/files/{path:path}")
async def download_file(path: str):
    data, content_type = get_object(path)
    return Response(content=data, media_type=content_type)


# Products + traceability
@api_router.get("/products", response_model=List[Product])
async def list_products(kategori: Optional[str] = None, jenis: Optional[str] = None):
    q: Dict[str, Any] = {}
    if kategori:
        q["kategori"] = kategori
    if jenis:
        q["jenis"] = jenis
    items = await db.products.find(q, {"_id": 0}).to_list(1000)
    for p in items:
        if isinstance(p.get("created_at"), str):
            p["created_at"] = datetime.fromisoformat(p["created_at"])
    return items


@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    doc = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return doc


@api_router.post("/products", response_model=Product)
async def create_product(payload: ProductCreate):
    # Enforce traceability: Hulu products MUST originate from a plot;
    # downstream products MUST cite their parent products.
    if payload.kategori == "Hulu":
        if not payload.plot_id:
            raise HTTPException(
                status_code=400,
                detail="Produk kategori 'Hulu' (TBS) wajib mencantumkan plot_id (kebun asal)."
            )
        plot_exists = await db.plots.find_one({"id": payload.plot_id}, {"_id": 0})
        if not plot_exists:
            raise HTTPException(status_code=400, detail="plot_id tidak ditemukan di database lahan.")
    else:
        if not payload.parent_ids or len(payload.parent_ids) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Produk kategori '{payload.kategori}' wajib mencantumkan minimal 1 parent_id (bahan baku/produk hulu) untuk traceability."
            )
        for pid in payload.parent_ids:
            parent = await db.products.find_one({"id": pid}, {"_id": 0})
            if not parent:
                raise HTTPException(status_code=400, detail=f"parent_id {pid} tidak ditemukan.")
    obj = Product(**payload.model_dump())
    doc = obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.products.insert_one(doc)
    return obj


@api_router.get("/marketplace", response_model=List[Product])
async def list_marketplace(kategori: Optional[str] = None):
    q: Dict[str, Any] = {"tersedia_marketplace": True}
    if kategori:
        q["kategori"] = kategori
    items = await db.products.find(q, {"_id": 0}).to_list(1000)
    for p in items:
        if isinstance(p.get("created_at"), str):
            p["created_at"] = datetime.fromisoformat(p["created_at"])
    return items


@api_router.get("/products/{product_id}/trace")
async def trace_product(product_id: str):
    """Return upstream traceability tree for a product (recursive parents until TBS plots)."""
    visited = set()

    async def build(pid: str, depth: int = 0):
        if pid in visited or depth > 10:
            return None
        visited.add(pid)
        p = await db.products.find_one({"id": pid}, {"_id": 0})
        if not p:
            return None
        node = {
            "id": p["id"],
            "kode": p["kode"],
            "nama": p["nama"],
            "kategori": p["kategori"],
            "jenis": p["jenis"],
            "produsen": p["produsen"],
            "jumlah": p["jumlah"],
            "satuan": p["satuan"],
            "batch_date": p.get("batch_date"),
            "parents": [],
            "plot": None,
        }
        if p.get("plot_id"):
            plot = await db.plots.find_one({"id": p["plot_id"]}, {"_id": 0})
            if plot:
                plot.pop("documents", None)
                node["plot"] = plot
        for parent_id in p.get("parent_ids", []) or []:
            child = await build(parent_id, depth + 1)
            if child:
                node["parents"].append(child)
        return node

    tree = await build(product_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Product not found")
    return tree


# Seed demo data
@api_router.post("/seed")
async def seed_demo():
    await db.plots.delete_many({})
    await db.products.delete_many({})
    await db.users.delete_many({})

    # Seed users (including the Super Admin)
    seed_users = [
        {"email": "admin@si-ispo.go.id", "nama": "Super Admin SI-ISPO", "org": "Kementerian Pertanian RI", "role": "superadmin"},
        {"email": "ls@sucofindo.com", "nama": "LS SUCOFINDO", "org": "PT Sucofindo (Persero)", "role": "ls"},
        {"email": "pekebun@test.com", "nama": "Kelompok Tani Makmur", "org": "Koperasi Tani Riau", "role": "pekebun"},
        {"email": "pks@test.com", "nama": "PT Industri Sawit Makmur", "org": "PT Industri Sawit Makmur", "role": "pks"},
        {"email": "buyer@test.com", "nama": "Global Oils Trading Ltd.", "org": "Global Oils Trading Ltd.", "role": "buyer"},
        {"email": "auditor@test.com", "nama": "Siti Rahma, SST", "org": "LS SUCOFINDO", "role": "auditor"},
        {"email": "auditor.int@test.com", "nama": "Ir. Suhartono, S.P.", "org": "PT Sawit Nusantara", "role": "auditor_int"},
        {"email": "reviewer@test.com", "nama": "Dr. Hendra Wijaya", "org": "LS SUCOFINDO", "role": "reviewer"},
        {"email": "perkebunan@test.com", "nama": "PT Sawit Nusantara", "org": "PT Sawit Nusantara", "role": "perkebunan"},
        {"email": "bioenergy@test.com", "nama": "PT Bioenergi Sawit Indonesia", "org": "PT Bioenergi Sawit Indonesia", "role": "bioenergy"},
    ]
    for ud in seed_users:
        u = User(**ud)
        d = u.model_dump()
        d["created_at"] = d["created_at"].isoformat()
        await db.users.insert_one(d)

    plots_data = [
        {
            "nama": "Kebun Inti Riau A1", "pemilik": "PT Sawit Nusantara", "provinsi": "Riau",
            "kabupaten": "Pelalawan", "luas_ha": 1250.5, "status_ispo": "Tersertifikasi",
            "tahun_tanam": 2012,
            "polygon": [[0.45, 101.85], [0.45, 101.92], [0.40, 101.92], [0.40, 101.85]],
            "centroid": [0.425, 101.885],
            "catatan": "Lahan inti utama PT Sawit Nusantara, sertifikat ISPO No. 001/2023",
        },
        {
            "nama": "Kebun Plasma Sumut B2", "pemilik": "Kelompok Tani Makmur", "provinsi": "Sumatera Utara",
            "kabupaten": "Labuhanbatu", "luas_ha": 480.0, "status_ispo": "Proses",
            "tahun_tanam": 2015,
            "polygon": [[2.30, 99.80], [2.30, 99.86], [2.25, 99.86], [2.25, 99.80]],
            "centroid": [2.275, 99.83],
            "catatan": "Kebun plasma binaan, dalam tahap audit awal ISPO",
        },
        {
            "nama": "Kebun Kalbar C3", "pemilik": "PT Borneo Sawit Lestari", "provinsi": "Kalimantan Barat",
            "kabupaten": "Ketapang", "luas_ha": 2100.0, "status_ispo": "Tersertifikasi",
            "tahun_tanam": 2010,
            "polygon": [[-1.85, 110.10], [-1.85, 110.18], [-1.92, 110.18], [-1.92, 110.10]],
            "centroid": [-1.885, 110.14],
            "catatan": "Lahan besar dengan praktek NDPE compliance",
        },
        {
            "nama": "Kebun Aceh D4", "pemilik": "Koperasi Tani Aceh", "provinsi": "Aceh",
            "kabupaten": "Nagan Raya", "luas_ha": 320.0, "status_ispo": "Belum Sertifikasi",
            "tahun_tanam": 2018,
            "polygon": [[4.15, 96.45], [4.15, 96.50], [4.12, 96.50], [4.12, 96.45]],
            "centroid": [4.135, 96.475],
            "catatan": "Pekebun mandiri, sedang mempersiapkan dokumen ISPO",
        },
        {
            "nama": "Kebun Jambi E5", "pemilik": "PT Industri Sawit Makmur", "provinsi": "Jambi",
            "kabupaten": "Muaro Jambi", "luas_ha": 875.5, "status_ispo": "Tersertifikasi",
            "tahun_tanam": 2011,
            "polygon": [[-1.62, 103.55], [-1.62, 103.60], [-1.66, 103.60], [-1.66, 103.55]],
            "centroid": [-1.64, 103.575],
            "catatan": "Lahan PKS, sertifikat ISPO sejak 2020",
        },
    ]
    plot_ids = {}
    for pd in plots_data:
        plot = Plot(**pd)
        doc = plot.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.plots.insert_one(doc)
        plot_ids[plot.nama] = plot.id

    # Product chain:
    # TBS (panen) -> CPO -> RBD Palm Oil -> Minyak Goreng / Margarin / Olein -> Biodiesel
    # CPO -> PKO -> Fatty Acid -> Sabun & Detergen
    # TBS -> CPO -> Biomassa -> Biogas
    products_data = [
        # ── TBS (Hulu) ──
        {"kode": "TBS-RIA-001", "nama": "TBS Panen Riau A1 Batch Jan-2025", "kategori": "Hulu", "jenis": "TBS",
         "produsen": "PT Sawit Nusantara", "jumlah": 850, "satuan": "ton", "batch_date": "2025-01-15",
         "plot_id": plot_ids["Kebun Inti Riau A1"], "parent_ids": []},
        {"kode": "TBS-KBR-001", "nama": "TBS Panen Kalbar C3 Batch Feb-2025", "kategori": "Hulu", "jenis": "TBS",
         "produsen": "PT Borneo Sawit Lestari", "jumlah": 1450, "satuan": "ton", "batch_date": "2025-02-10",
         "plot_id": plot_ids["Kebun Kalbar C3"], "parent_ids": []},
        {"kode": "TBS-JBI-001", "nama": "TBS Panen Jambi E5 Batch Jan-2025", "kategori": "Hulu", "jenis": "TBS",
         "produsen": "PT Industri Sawit Makmur", "jumlah": 620, "satuan": "ton", "batch_date": "2025-01-20",
         "plot_id": plot_ids["Kebun Jambi E5"], "parent_ids": []},
    ]
    created = {}
    for prod in products_data:
        p = Product(**prod)
        d = p.model_dump()
        d["created_at"] = d["created_at"].isoformat()
        await db.products.insert_one(d)
        created[p.kode] = p.id

    # CPO from TBS (Rafinasi)
    cpo1 = Product(kode="CPO-RIA-001", nama="CPO Riau Batch Jan-2025", kategori="Rafinasi", jenis="CPO (Crude Palm Oil)",
                   produsen="PKS Pelalawan", jumlah=185, satuan="ton", batch_date="2025-01-18",
                   parent_ids=[created["TBS-RIA-001"]])
    cpo2 = Product(kode="CPO-KBR-001", nama="CPO Kalbar Batch Feb-2025", kategori="Rafinasi", jenis="CPO (Crude Palm Oil)",
                   produsen="PKS Ketapang", jumlah=310, satuan="ton", batch_date="2025-02-12",
                   parent_ids=[created["TBS-KBR-001"]])
    cpo3 = Product(kode="CPO-JBI-001", nama="CPO Jambi Batch Jan-2025", kategori="Rafinasi", jenis="CPO (Crude Palm Oil)",
                   produsen="PKS Muaro Jambi", jumlah=135, satuan="ton", batch_date="2025-01-22",
                   parent_ids=[created["TBS-JBI-001"]])
    for c in [cpo1, cpo2, cpo3]:
        d = c.model_dump(); d["created_at"] = d["created_at"].isoformat()
        await db.products.insert_one(d); created[c.kode] = c.id

    # PKO from TBS
    pko1 = Product(kode="PKO-RIA-001", nama="PKO Riau Batch Jan-2025", kategori="Rafinasi",
                   jenis="PKO (Palm Kernel Oil)", produsen="PKS Pelalawan", jumlah=20, satuan="ton",
                   batch_date="2025-01-18", parent_ids=[created["TBS-RIA-001"]])
    d = pko1.model_dump(); d["created_at"] = d["created_at"].isoformat()
    await db.products.insert_one(d); created[pko1.kode] = pko1.id

    # RBD Palm Oil from CPO
    rbd1 = Product(kode="RBD-001", nama="RBD Palm Oil Batch Feb-2025", kategori="Rafinasi",
                   jenis="RBD Palm Oil (Refined, Bleached, Deodorized)", produsen="PT Refinery Sumut",
                   jumlah=420, satuan="ton", batch_date="2025-02-15",
                   parent_ids=[cpo1.id, cpo2.id])
    d = rbd1.model_dump(); d["created_at"] = d["created_at"].isoformat()
    await db.products.insert_one(d); created[rbd1.kode] = rbd1.id

    # Palm Olein & Palm Stearin from RBD
    olein = Product(kode="OLN-001", nama="Palm Olein Batch Feb-2025", kategori="Rafinasi",
                    jenis="Palm Olein", produsen="PT Refinery Sumut", jumlah=290, satuan="ton",
                    batch_date="2025-02-18", parent_ids=[rbd1.id])
    stearin = Product(kode="STR-001", nama="Palm Stearin Batch Feb-2025", kategori="Rafinasi",
                      jenis="Palm Stearin", produsen="PT Refinery Sumut", jumlah=120, satuan="ton",
                      batch_date="2025-02-18", parent_ids=[rbd1.id])
    for c in [olein, stearin]:
        d = c.model_dump(); d["created_at"] = d["created_at"].isoformat()
        await db.products.insert_one(d); created[c.kode] = c.id

    # ── Pangan ──
    mg = Product(kode="MG-001", nama="Minyak Goreng SawitMurni 1L", kategori="Pangan",
                 jenis="Minyak Goreng Sawit", produsen="PT Pangan Sawit", jumlah=80000, satuan="liter",
                 batch_date="2025-02-20", parent_ids=[olein.id],
                 harga=18500, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Minyak goreng kelapa sawit kualitas premium, ISPO bersertifikat. Diproses dengan teknologi rafinasi modern.",
                 spesifikasi="Volume: 1L | FFA: <0.1% | Moisture: <0.1% | Kemasan: PET botol",
                 minimum_order=1000, lokasi_gudang="Gudang Medan, Sumatera Utara")
    marg = Product(kode="MARG-001", nama="Margarin Premium 250g", kategori="Pangan",
                   jenis="Margarin", produsen="PT Pangan Sawit", jumlah=50000, satuan="pcs",
                   batch_date="2025-02-22", parent_ids=[stearin.id, olein.id],
                   harga=12000, mata_uang="IDR", tersedia_marketplace=True,
                   deskripsi="Margarin premium dengan komposisi blend palm stearin & olein. Cocok untuk industri bakery.",
                   spesifikasi="Berat: 250g | SFC@10°C: 60% | Melting point: 38°C | Halal MUI",
                   minimum_order=500, lokasi_gudang="Gudang Surabaya, Jawa Timur")
    sf = Product(kode="SF-001", nama="Specialty Fats (CBS) 25kg", kategori="Pangan",
                 jenis="Lemak Khusus (Specialty Fats)", produsen="PT Pangan Sawit", jumlah=8000, satuan="kg",
                 batch_date="2025-02-25", parent_ids=[stearin.id],
                 harga=85000, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Cocoa Butter Substitute (CBS) untuk industri konfeksioneri & coklat. Profil leleh setara CB.",
                 spesifikasi="Berat: 25kg/karton | SMP: 32-34°C | SFC: matched cocoa butter | Trans fat free",
                 minimum_order=200, lokasi_gudang="Gudang Jakarta")
    pkn = Product(kode="PKN-001", nama="Pakan Ternak Berbasis Sawit", kategori="Pangan",
                  jenis="Pakan Ternak Berbasis Sawit", produsen="PT Pakan Nusantara", jumlah=15000, satuan="kg",
                  batch_date="2025-02-26", parent_ids=[created["TBS-RIA-001"]],
                  harga=6500, mata_uang="IDR", tersedia_marketplace=True,
                  deskripsi="Pakan ternak berbasis bungkil kelapa sawit. Sumber protein nabati untuk ternak ruminansia.",
                  spesifikasi="Protein: 16% | Lemak: 8% | Serat kasar: 12% | Kemasan karung 25kg",
                  minimum_order=1000, lokasi_gudang="Gudang Pekanbaru, Riau")
    for c in [mg, marg, sf, pkn]:
        d = c.model_dump(); d["created_at"] = d["created_at"].isoformat()
        await db.products.insert_one(d); created[c.kode] = c.id

    # ── Oleokimia ──
    fa = Product(kode="FA-001", nama="Asam Lemak (Fatty Acid)", kategori="Oleokimia",
                 jenis="Asam Lemak (Fatty Acids)", produsen="PT Oleo Indonesia", jumlah=180, satuan="ton",
                 batch_date="2025-03-01", parent_ids=[created["PKO-RIA-001"]],
                 harga=14500000, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Asam lemak hasil splitting PKO. Bahan baku industri sabun, deterjen, dan oleokimia lanjutan.",
                 spesifikasi="Acid value: 200-210 | Iodine value: 50-60 | Saponification value: 200-210",
                 minimum_order=20, lokasi_gudang="Gudang Dumai, Riau")
    gl = Product(kode="GL-001", nama="Gliserol Industri", kategori="Oleokimia",
                 jenis="Gliserol / Gliserin", produsen="PT Oleo Indonesia", jumlah=45, satuan="ton",
                 batch_date="2025-03-01", parent_ids=[created["PKO-RIA-001"]],
                 harga=11000000, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Gliserol crude hasil samping splitting fatty acid. Untuk industri kosmetik, farmasi, makanan.",
                 spesifikasi="Glycerol content: 80% min | Color: <100 APHA | Water: <15%",
                 minimum_order=10, lokasi_gudang="Gudang Dumai, Riau")
    me = Product(kode="ME-001", nama="Metil Ester", kategori="Oleokimia",
                 jenis="Metil Ester", produsen="PT Oleo Indonesia", jumlah=220, satuan="ton",
                 batch_date="2025-03-03", parent_ids=[cpo3.id],
                 harga=13800000, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Fatty Acid Methyl Ester (FAME) hasil transesterifikasi CPO. Feedstock biodiesel.",
                 spesifikasi="Ester content: 96.5% min | Sulfur: <10 ppm | Cetane: 51 min",
                 minimum_order=25, lokasi_gudang="Gudang Cilegon, Banten")
    sb = Product(kode="SB-001", nama="Sabun Mandi Berbasis Sawit", kategori="Oleokimia",
                 jenis="Sabun & Deterjen Berbasis Sawit", produsen="PT Sabun Nusantara", jumlah=120000, satuan="pcs",
                 batch_date="2025-03-05", parent_ids=[fa.id],
                 harga=4500, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Sabun mandi batang berbahan dasar palm fatty acid. Pelembab alami, aroma natural.",
                 spesifikasi="Berat: 80g/pcs | TFM: 76% | Halal MUI | Eco-friendly packaging",
                 minimum_order=2000, lokasi_gudang="Gudang Bekasi, Jawa Barat")
    ks = Product(kode="KS-001", nama="Lotion Perawatan Tubuh", kategori="Oleokimia",
                 jenis="Kosmetik & Perawatan Tubuh", produsen="PT Beauty Sawit", jumlah=25000, satuan="pcs",
                 batch_date="2025-03-08", parent_ids=[fa.id, gl.id],
                 harga=28000, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Body lotion dengan gliserin & emolien dari sawit berkelanjutan. Free paraben, halal certified.",
                 spesifikasi="Volume: 200ml | pH: 5.5 | Tested: dermatology safe | Halal MUI",
                 minimum_order=500, lokasi_gudang="Gudang Jakarta")
    for c in [fa, gl, me, sb, ks]:
        d = c.model_dump(); d["created_at"] = d["created_at"].isoformat()
        await db.products.insert_one(d); created[c.kode] = c.id

    # ── Bioenergi ──
    bd = Product(kode="BD-001", nama="Biodiesel B30", kategori="Bioenergi",
                 jenis="Biodiesel (Bahan Bakar Nabati)", produsen="PT Bioenergi Sawit Indonesia",
                 jumlah=210, satuan="ton", batch_date="2025-03-10",
                 parent_ids=[me.id, olein.id],
                 harga=12500000, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Biodiesel campuran B30 sesuai mandatory pemerintah RI. Penggunaan untuk transportasi & industri.",
                 spesifikasi="Cetane: 51 min | Density: 850-890 kg/m³ | Sulfur: <50 ppm | EN 14214 compliant",
                 minimum_order=50, lokasi_gudang="Terminal Tj. Priok, Jakarta")
    bm = Product(kode="BM-001", nama="Biomassa Cangkang Sawit", kategori="Bioenergi",
                 jenis="Biomassa", produsen="PT Bioenergi Sawit Indonesia", jumlah=350, satuan="ton",
                 batch_date="2025-03-11", parent_ids=[created["TBS-KBR-001"]],
                 harga=850000, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Palm Kernel Shell (PKS) untuk bahan bakar boiler/PLTU biomassa. Renewable energy source.",
                 spesifikasi="Calorific value: 4200 kcal/kg | Moisture: <15% | Ash: <5%",
                 minimum_order=100, lokasi_gudang="Pelabuhan Pontianak, Kalbar")
    bg = Product(kode="BG-001", nama="Biogas dari POME", kategori="Bioenergi",
                 jenis="Biogas (POME)", produsen="PT Bioenergi Sawit Indonesia", jumlah=85000, satuan="m³",
                 batch_date="2025-03-12", parent_ids=[cpo2.id],
                 harga=4500, mata_uang="IDR", tersedia_marketplace=True,
                 deskripsi="Biogas hasil pengolahan POME (Palm Oil Mill Effluent). Untuk pembangkit listrik on-site.",
                 spesifikasi="Methane content: 55-65% | H2S: <500 ppm | Pressure: 50-100 mbar",
                 minimum_order=5000, lokasi_gudang="Pabrik Ketapang, Kalbar")
    for c in [bd, bm, bg]:
        d = c.model_dump(); d["created_at"] = d["created_at"].isoformat()
        await db.products.insert_one(d); created[c.kode] = c.id

    return {
        "ok": True,
        "plots": len(plots_data),
        "products": await db.products.count_documents({}),
    }


# ─────────── Users / Roles management (Super Admin) ───────────
@api_router.get("/users", response_model=List[User])
async def list_users(role: Optional[str] = None, status: Optional[str] = None):
    q: Dict[str, Any] = {}
    if role:
        q["role"] = role
    if status:
        q["status"] = status
    items = await db.users.find(q, {"_id": 0}).to_list(1000)
    for u in items:
        if isinstance(u.get("created_at"), str):
            u["created_at"] = datetime.fromisoformat(u["created_at"])
    return items


@api_router.post("/users", response_model=User)
async def create_user(payload: UserCreate):
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {VALID_ROLES}")
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")
    obj = User(**payload.model_dump())
    doc = obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.users.insert_one(doc)
    return obj


@api_router.put("/users/{user_id}/role", response_model=User)
async def update_user_role(user_id: str, payload: RoleUpdate):
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {VALID_ROLES}")
    result = await db.users.find_one_and_update(
        {"id": user_id},
        {"$set": {"role": payload.role}},
        return_document=True,
        projection={"_id": 0}
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    if isinstance(result.get("created_at"), str):
        result["created_at"] = datetime.fromisoformat(result["created_at"])
    return result


@api_router.put("/users/{user_id}/status", response_model=User)
async def update_user_status(user_id: str, payload: StatusUpdate):
    if payload.status not in ("Active", "Suspended"):
        raise HTTPException(status_code=400, detail="status must be Active or Suspended")
    result = await db.users.find_one_and_update(
        {"id": user_id},
        {"$set": {"status": payload.status}},
        return_document=True,
        projection={"_id": 0}
    )
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    if isinstance(result.get("created_at"), str):
        result["created_at"] = datetime.fromisoformat(result["created_at"])
    return result


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    res = await db.users.delete_one({"id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@api_router.get("/admin/overview")
async def admin_overview():
    """Aggregate stats across the entire system for the Super Admin dashboard."""
    users_total = await db.users.count_documents({})
    users_active = await db.users.count_documents({"status": "Active"})
    users_suspended = await db.users.count_documents({"status": "Suspended"})

    pipe = [{"$group": {"_id": "$role", "n": {"$sum": 1}}}]
    by_role_raw = await db.users.aggregate(pipe).to_list(50)
    users_by_role = {r["_id"]: r["n"] for r in by_role_raw}

    plots_total = await db.plots.count_documents({})
    plots_cert = await db.plots.count_documents({"status_ispo": "Tersertifikasi"})
    plots_proses = await db.plots.count_documents({"status_ispo": "Proses"})
    plots_blm = await db.plots.count_documents({"status_ispo": "Belum Sertifikasi"})

    ha_pipe = [{"$group": {"_id": None, "total": {"$sum": "$luas_ha"}}}]
    ha_res = await db.plots.aggregate(ha_pipe).to_list(1)
    luas_total = float(ha_res[0]["total"]) if ha_res else 0

    products_total = await db.products.count_documents({})
    p_pipe = [{"$group": {"_id": "$kategori", "n": {"$sum": 1}}}]
    p_by_cat_raw = await db.products.aggregate(p_pipe).to_list(50)
    products_by_kategori = {r["_id"]: r["n"] for r in p_by_cat_raw}

    certs_total = await db.certificates.count_documents({})
    audits_total = await db.audits.count_documents({})
    companies_total = await db.companies.count_documents({})

    docs_pipe = [
        {"$project": {"docs": {"$size": {"$ifNull": ["$documents", []]}}}},
        {"$group": {"_id": None, "total": {"$sum": "$docs"}}},
    ]
    docs_res = await db.plots.aggregate(docs_pipe).to_list(1)
    documents_total = int(docs_res[0]["total"]) if docs_res else 0

    return {
        "users": {
            "total": users_total, "active": users_active, "suspended": users_suspended,
            "by_role": users_by_role,
        },
        "plots": {
            "total": plots_total, "tersertifikasi": plots_cert,
            "proses": plots_proses, "belum": plots_blm,
            "luas_total_ha": luas_total,
        },
        "products": {
            "total": products_total, "by_kategori": products_by_kategori,
        },
        "certificates": certs_total,
        "audits": audits_total,
        "companies": companies_total,
        "documents": documents_total,
    }


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@app.on_event("startup")
async def startup_event():
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
