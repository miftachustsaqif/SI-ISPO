from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="SI-ISPO API")
api_router = APIRouter(prefix="/api")


# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
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
    tipe: str  # e.g. "Perusahaan", "Pekebun"
    status: str  # "Aktif", "Suspend", "Kadaluarsa"
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
    tipe: str = "Perusahaan"  # Perusahaan / Pekebun / PKS / Buyer
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
    tipe: str  # Initial / Surveillance / Re-cert
    tgl_audit: str
    status: str = "Terjadwal"  # Terjadwal / Berjalan / Selesai
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


# ─────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────
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

    # ton produksi placeholder static value (matches mockup style)
    ton_produksi = float(os.environ.get("STATIC_TON_PRODUKSI", "18200000"))

    # Fallback to mockup numbers if DB empty (keeps parity with static mockup)
    if sertifikat_aktif == 0 and perusahaan == 0:
        return StatsOut(
            sertifikat_aktif=892,
            luas_ha=7_800_000,
            perusahaan=725,
            ton_produksi=18_200_000,
        )

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
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
