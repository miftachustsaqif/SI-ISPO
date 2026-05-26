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
from datetime import datetime, timezone, timedelta


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
    # Certification & sale status
    ispo_certified: bool = False
    sertifikat_ispo: Optional[str] = None  # certificate number
    siap_jual: str = "Draft"  # Draft / Siap Jual / Habis / Reserved
    halal_certified: bool = False
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
    ispo_certified: Optional[bool] = False
    sertifikat_ispo: Optional[str] = None
    siap_jual: Optional[str] = "Draft"
    halal_certified: Optional[bool] = False


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


class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nomor: str
    buyer_email: str
    buyer_nama: str
    supplier: str
    product_id: str
    product_kode: str
    product_nama: str
    qty: float
    satuan: str
    harga_per_unit: float
    harga_total: float
    status: str = "Pending"  # Pending, Dikonfirmasi, Dikirim, Diterima, Selesai, Dibatalkan
    tgl_pesan: str
    tgl_kirim: Optional[str] = None
    tgl_terima: Optional[str] = None
    catatan: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrderCreate(BaseModel):
    nomor: Optional[str] = None
    buyer_email: str
    buyer_nama: str
    supplier: str
    product_id: str
    qty: float
    catatan: Optional[str] = None


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

    # Product chain: use comprehensive seed dataset
    from seed_data import build_products_seed
    products_data = build_products_seed(plot_ids)
    created: Dict[str, str] = {}
    # Multi-pass insert to resolve parent kode→id references
    pending = products_data[:]
    safety = 0
    while pending and safety < 20:
        safety += 1
        next_pending = []
        for prod in pending:
            parents_kode = prod.get("parents", [])
            plot_name = prod.get("plot")
            # Check if all parent kodes have been resolved
            if any(pk not in created for pk in parents_kode):
                next_pending.append(prod)
                continue
            # Build the Product
            payload = {k: v for k, v in prod.items() if k not in ("parents", "plot")}
            payload["parent_ids"] = [created[pk] for pk in parents_kode]
            if plot_name:
                payload["plot_id"] = plot_ids.get(plot_name)
            p = Product(**payload)
            doc = p.model_dump()
            doc["created_at"] = doc["created_at"].isoformat()
            await db.products.insert_one(doc)
            created[p.kode] = p.id
        if len(next_pending) == len(pending):
            break  # no progress, avoid infinite loop
        pending = next_pending

    return {
        "ok": True,
        "plots": len(plots_data),
        "products": await db.products.count_documents({}),
        "orders": await _seed_orders_inline(),
    }


async def _seed_orders_inline():
    """Inline helper used by /seed to also create order history."""
    await db.orders.delete_many({})
    buyers = [
        {"email": "buyer@test.com", "nama": "Global Oils Trading Ltd."},
        {"email": "buyer.eu@example.com", "nama": "EuroPalm Importers GmbH"},
        {"email": "buyer.id@example.com", "nama": "PT Distribusi Nusantara"},
        {"email": "buyer.jp@example.com", "nama": "Sakura Trading Co. Ltd."},
        {"email": "buyer.in@example.com", "nama": "Mumbai Oils Pvt. Ltd."},
        {"email": "retailer@example.com", "nama": "PT Indomart Retail"},
        {"email": "hotel@example.com", "nama": "Hotel Group Indonesia"},
        {"email": "industri@example.com", "nama": "PT Industri Pangan Sehat"},
    ]
    products = await db.products.find(
        {"tersedia_marketplace": True, "siap_jual": "Siap Jual"}, {"_id": 0}
    ).to_list(500)
    if not products:
        return 0
    import random
    random.seed(42)
    statuses = ["Pending", "Dikonfirmasi", "Dikirim", "Diterima", "Selesai", "Selesai", "Selesai"]
    catatan_options = [
        "Pengiriman urgent untuk Lebaran",
        "Kirim ke gudang utama Jakarta",
        "Untuk distribusi retail Jabodetabek",
        "Persiapan stok ramadhan",
        "Ekspor ke pasar Eropa, EUDR compliant",
        "Order rutin bulanan",
        "Trial sample untuk Q2",
        None, None, None,
    ]
    n = 0
    while n < 32:
        buyer = random.choice(buyers)
        product = random.choice(products)
        min_o = float(product.get("minimum_order") or 1)
        qty = round(min_o * random.uniform(1.0, 8.0), 0)
        harga = float(product.get("harga") or 0)
        status = random.choice(statuses)
        days_ago = random.randint(1, 90)
        tgl_pesan_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        tgl_pesan = tgl_pesan_dt.strftime("%Y-%m-%d")
        order = {
            "id": str(uuid.uuid4()),
            "nomor": f"ORD-2025-{(n+1):04d}",
            "buyer_email": buyer["email"],
            "buyer_nama": buyer["nama"],
            "supplier": product["produsen"],
            "product_id": product["id"],
            "product_kode": product["kode"],
            "product_nama": product["nama"],
            "qty": qty,
            "satuan": product.get("satuan", "pcs"),
            "harga_per_unit": harga,
            "harga_total": harga * qty,
            "status": status,
            "tgl_pesan": tgl_pesan,
            "tgl_kirim": (tgl_pesan_dt + timedelta(days=random.randint(2, 7))).strftime("%Y-%m-%d") if status in ("Dikirim", "Diterima", "Selesai") else None,
            "tgl_terima": (tgl_pesan_dt + timedelta(days=random.randint(5, 14))).strftime("%Y-%m-%d") if status in ("Diterima", "Selesai") else None,
            "catatan": random.choice(catatan_options),
            "created_at": tgl_pesan_dt.isoformat(),
        }
        await db.orders.insert_one(order)
        n += 1
    return n


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


# ─────────── Orders (B2B marketplace orders) ───────────
@api_router.get("/orders", response_model=List[Order])
async def list_orders(buyer_email: Optional[str] = None, supplier: Optional[str] = None,
                       status: Optional[str] = None):
    q: Dict[str, Any] = {}
    if buyer_email:
        q["buyer_email"] = buyer_email
    if supplier:
        q["supplier"] = supplier
    if status:
        q["status"] = status
    items = await db.orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for o in items:
        if isinstance(o.get("created_at"), str):
            o["created_at"] = datetime.fromisoformat(o["created_at"])
    return items


@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    doc = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return doc


@api_router.post("/orders", response_model=Order)
async def create_order(payload: OrderCreate):
    prod = await db.products.find_one({"id": payload.product_id}, {"_id": 0})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.qty <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")
    harga = float(prod.get("harga") or 0)
    obj = Order(
        nomor=payload.nomor or f"ORD-{uuid.uuid4().hex[:8].upper()}",
        buyer_email=payload.buyer_email,
        buyer_nama=payload.buyer_nama,
        supplier=payload.supplier,
        product_id=payload.product_id,
        product_kode=prod["kode"],
        product_nama=prod["nama"],
        qty=payload.qty,
        satuan=prod.get("satuan", "pcs"),
        harga_per_unit=harga,
        harga_total=harga * payload.qty,
        status="Pending",
        tgl_pesan=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        catatan=payload.catatan,
    )
    doc = obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.orders.insert_one(doc)
    return obj


@api_router.put("/orders/{order_id}/status", response_model=Order)
async def update_order_status(order_id: str, payload: StatusUpdate):
    valid = ["Pending", "Dikonfirmasi", "Dikirim", "Diterima", "Selesai", "Dibatalkan"]
    if payload.status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of {valid}")
    update = {"status": payload.status}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if payload.status == "Dikirim":
        update["tgl_kirim"] = today
    elif payload.status in ("Diterima", "Selesai"):
        update["tgl_terima"] = today
    result = await db.orders.find_one_and_update(
        {"id": order_id}, {"$set": update},
        return_document=True, projection={"_id": 0}
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    if isinstance(result.get("created_at"), str):
        result["created_at"] = datetime.fromisoformat(result["created_at"])
    return result


@api_router.post("/seed-orders")
async def seed_orders():
    """Seed B2B order history showing 'produk mana jalan kemana'."""
    await db.orders.delete_many({})
    buyers = [
        {"email": "buyer@test.com", "nama": "Global Oils Trading Ltd."},
        {"email": "buyer.eu@example.com", "nama": "EuroPalm Importers GmbH"},
        {"email": "buyer.id@example.com", "nama": "PT Distribusi Nusantara"},
        {"email": "buyer.jp@example.com", "nama": "Sakura Trading Co. Ltd."},
        {"email": "buyer.in@example.com", "nama": "Mumbai Oils Pvt. Ltd."},
        {"email": "retailer@example.com", "nama": "PT Indomart Retail"},
        {"email": "hotel@example.com", "nama": "Hotel Group Indonesia"},
        {"email": "industri@example.com", "nama": "PT Industri Pangan Sehat"},
    ]
    # Get available marketplace products
    products = await db.products.find(
        {"tersedia_marketplace": True, "siap_jual": "Siap Jual"}, {"_id": 0}
    ).to_list(500)
    if not products:
        return {"ok": False, "error": "No marketplace products available. Run /api/seed first."}

    import random
    random.seed(42)
    statuses = ["Pending", "Dikonfirmasi", "Dikirim", "Diterima", "Selesai", "Selesai", "Selesai"]
    catatan_options = [
        "Pengiriman urgent untuk Lebaran",
        "Kirim ke gudang utama Jakarta",
        "Untuk distribusi retail Jabodetabek",
        "Persiapan stok ramadhan",
        "Ekspor ke pasar Eropa, EUDR compliant",
        "Order rutin bulanan",
        "Trial sample untuk Q2",
        None, None, None,
    ]
    orders_to_create = 32
    n = 0
    while n < orders_to_create:
        buyer = random.choice(buyers)
        product = random.choice(products)
        # qty based on min_order
        min_o = float(product.get("minimum_order") or 1)
        qty = round(min_o * random.uniform(1.0, 8.0), 0)
        harga = float(product.get("harga") or 0)
        status = random.choice(statuses)
        days_ago = random.randint(1, 90)
        tgl_pesan_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        tgl_pesan = tgl_pesan_dt.strftime("%Y-%m-%d")
        order = {
            "id": str(uuid.uuid4()),
            "nomor": f"ORD-2025-{(n+1):04d}",
            "buyer_email": buyer["email"],
            "buyer_nama": buyer["nama"],
            "supplier": product["produsen"],
            "product_id": product["id"],
            "product_kode": product["kode"],
            "product_nama": product["nama"],
            "qty": qty,
            "satuan": product.get("satuan", "pcs"),
            "harga_per_unit": harga,
            "harga_total": harga * qty,
            "status": status,
            "tgl_pesan": tgl_pesan,
            "tgl_kirim": (tgl_pesan_dt + timedelta(days=random.randint(2, 7))).strftime("%Y-%m-%d") if status in ("Dikirim", "Diterima", "Selesai") else None,
            "tgl_terima": (tgl_pesan_dt + timedelta(days=random.randint(5, 14))).strftime("%Y-%m-%d") if status in ("Diterima", "Selesai") else None,
            "catatan": random.choice(catatan_options),
            "created_at": tgl_pesan_dt.isoformat(),
        }
        await db.orders.insert_one(order)
        n += 1

    return {"ok": True, "orders_created": n}


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
