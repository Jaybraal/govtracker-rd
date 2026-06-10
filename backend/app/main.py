from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
import os

from .core.config import settings
from .core.database import engine, Base
from .api.routes import contracts, companies, institutions, loans, graph, alerts, ai_chat, export, etl, intelligence, cooperatives, banks, political_parties, legislators, nominas, seguros, pgr

# Crear tablas
Base.metadata.create_all(bind=engine)

# Crear directorios de datos
os.makedirs(settings.DOCUMENTS_PATH, exist_ok=True)
os.makedirs(settings.EXPORTS_PATH, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plataforma de auditoría ciudadana del gasto público de República Dominicana",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rutas
app.include_router(contracts.router, prefix="/api")
app.include_router(companies.router, prefix="/api")
app.include_router(institutions.router, prefix="/api")
app.include_router(loans.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(ai_chat.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(etl.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(cooperatives.router,     prefix="/api")
app.include_router(banks.router,            prefix="/api")
app.include_router(political_parties.router, prefix="/api")
app.include_router(legislators.router,       prefix="/api")
app.include_router(nominas.router,           prefix="/api")
app.include_router(seguros.router,           prefix="/api")
app.include_router(pgr.router,               prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}


@app.get("/api/stats")
def global_stats(db=None):
    from .core.database import SessionLocal
    from .models.contract import Contract
    from .models.company import Company
    from .models.institution import Institution
    from .models.loan import Loan
    from .models.alert import Alert
    from sqlalchemy import func
    db = SessionLocal()
    try:
        return {
            "total_contratos": db.query(func.count(Contract.id)).scalar(),
            "total_monto_contratos": db.query(func.sum(Contract.monto_original)).scalar() or 0,
            "total_empresas": db.query(func.count(Company.id)).scalar(),
            "total_instituciones": db.query(func.count(Institution.id)).scalar(),
            "total_prestamos": db.query(func.count(Loan.id)).scalar(),
            "total_monto_prestamos": db.query(func.sum(Loan.monto_aprobado)).scalar() or 0,
            "alertas_activas": db.query(func.count(Alert.id)).filter(
                Alert.descartada == False, Alert.revisada == False
            ).scalar(),
        }
    finally:
        db.close()


logger.info(f"GovTracker RD v{settings.APP_VERSION} iniciado")
