from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import httpx
import json
from ...core.database import get_db
from ...core.config import settings
from ...models.contract import Contract
from ...models.company import Company
from ...models.institution import Institution
from ...models.loan import Loan

router = APIRouter(prefix="/ai", tags=["IA Analista"])


class ChatMessage(BaseModel):
    message: str
    context: Optional[str] = None


@router.post("/chat")
async def chat(payload: ChatMessage, db: Session = Depends(get_db)):
    """
    IA conversacional que responde preguntas sobre datos gubernamentales.
    Usa Ollama local si disponible, sino análisis con reglas.
    """
    query = payload.message.lower()
    context_data = _build_context(query, db)

    if await _ollama_available():
        answer = await _ask_ollama(payload.message, context_data)
    else:
        answer = _rule_based_analysis(query, db)

    return {"answer": answer, "context_used": context_data[:500] if context_data else None}


@router.post("/analyze-contract/{contract_id}")
async def analyze_contract(contract_id: int, db: Session = Depends(get_db)):
    """Análisis IA de un contrato específico."""
    c = db.query(Contract).filter(Contract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "Contrato no encontrado")

    flags = []
    if c.es_mayor_100m:
        flags.append(f"Contrato de alto valor: RD${c.monto_original:,.0f}")
    if c.modalidad == "contratacion_directa":
        flags.append("Modalidad contratación directa — requiere justificación")
    if c.num_adendas >= 3:
        flags.append(f"Tiene {c.num_adendas} adendas")
    if c.incremento_porcentual >= 25:
        flags.append(f"Incremento de precio del {c.incremento_porcentual:.1f}%")
    if c.retraso_dias > 90:
        flags.append(f"Retraso de {c.retraso_dias} días")

    risk_score = min(100, len(flags) * 20 + (c.incremento_porcentual or 0) / 2)
    risk_level = "BAJO" if risk_score < 30 else "MEDIO" if risk_score < 60 else "ALTO"

    return {
        "contract_id": contract_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "flags": flags,
        "summary": _generate_contract_summary(c, flags, risk_level),
    }


@router.get("/search")
def semantic_search(
    q: str,
    db: Session = Depends(get_db),
    limit: int = 20,
):
    """Búsqueda semántica en contratos, empresas e instituciones."""
    results = []

    # Contratos
    contratos = db.query(Contract).filter(
        Contract.descripcion.ilike(f"%{q}%") |
        Contract.objeto.ilike(f"%{q}%") |
        Contract.numero_contrato.ilike(f"%{q}%")
    ).limit(10).all()
    for c in contratos:
        results.append({
            "type": "contrato",
            "id": c.id,
            "title": c.descripcion or c.objeto or c.numero_contrato,
            "subtitle": f"RD${c.monto_original:,.0f}",
            "url": f"/contracts/{c.id}",
        })

    # Empresas
    empresas = db.query(Company).filter(
        Company.nombre.ilike(f"%{q}%") | Company.rnc.ilike(f"%{q}%")
    ).limit(5).all()
    for e in empresas:
        results.append({
            "type": "empresa",
            "id": e.id,
            "title": e.nombre,
            "subtitle": f"RNC: {e.rnc} — {e.total_contratos} contratos",
            "url": f"/companies/{e.id}",
        })

    # Instituciones
    insts = db.query(Institution).filter(
        Institution.nombre.ilike(f"%{q}%") | Institution.siglas.ilike(f"%{q}%")
    ).limit(5).all()
    for i in insts:
        results.append({
            "type": "institucion",
            "id": i.id,
            "title": i.nombre,
            "subtitle": i.siglas,
            "url": f"/institutions/{i.id}",
        })

    return {"query": q, "results": results}


def _build_context(query: str, db: Session) -> str:
    ctx = []
    # Stats generales siempre útiles
    total_contratos = db.query(func.count(Contract.id)).scalar()
    total_monto = db.query(func.sum(Contract.monto_original)).scalar() or 0
    ctx.append(f"Base de datos: {total_contratos} contratos, RD${total_monto:,.0f} total")

    if "inapa" in query:
        inst = db.query(Institution).filter(Institution.siglas.ilike("%INAPA%")).first()
        if inst:
            ctx.append(f"INAPA: {inst.total_contratos} contratos, RD${inst.total_monto_contratos:,.0f}")

    if "bid" in query or "banco interamericano" in query:
        loans = db.query(Loan).filter(Loan.acreedor.ilike("%BID%")).all()
        for l in loans:
            ctx.append(f"Préstamo BID: {l.descripcion} — USD${l.monto_aprobado:,.0f}")

    if "empresa" in query or "company" in query:
        top = db.query(Company).order_by(desc(Company.total_monto_recibido)).limit(5).all()
        for c in top:
            ctx.append(f"Top empresa: {c.nombre} — RD${c.total_monto_recibido:,.0f}")

    return "\n".join(ctx)


async def _ollama_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def _ask_ollama(message: str, context: str) -> str:
    system_prompt = """Eres un analista experto en auditoría gubernamental de República Dominicana.
Tienes acceso a datos de contratos públicos, préstamos internacionales, empresas contratistas
y funcionarios. Responde en español, de forma precisa y directa. Si detectas irregularidades,
señálalas claramente. Basa tus respuestas en los datos de contexto proporcionados."""

    prompt = f"""Contexto de datos:
{context}

Pregunta del usuario:
{message}

Responde de forma clara y estructurada:"""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt,
                  "system": system_prompt, "stream": False},
        )
        if resp.status_code == 200:
            return resp.json().get("response", "Sin respuesta")
        return _rule_based_analysis(message.lower(), None)


def _rule_based_analysis(query: str, db: Optional[Session]) -> str:
    if db is None:
        return "Sistema de análisis no disponible. Instala Ollama y el modelo llama3 para IA avanzada."

    if any(k in query for k in ["mayor", "grande", "top", "100 millon"]):
        contratos = db.query(Contract).filter(Contract.es_mayor_100m == True)\
                      .order_by(desc(Contract.monto_original)).limit(5).all()
        lines = [f"Top contratos >RD$100M:"]
        for c in contratos:
            lines.append(f"• {c.numero_contrato}: RD${c.monto_original:,.0f}")
        return "\n".join(lines)

    if any(k in query for k in ["empresa", "company", "recibido"]):
        top = db.query(Company).order_by(desc(Company.total_monto_recibido)).limit(5).all()
        lines = ["Top 5 empresas por monto recibido:"]
        for c in top:
            lines.append(f"• {c.nombre}: RD${c.total_monto_recibido:,.0f} ({c.total_contratos} contratos)")
        return "\n".join(lines)

    if any(k in query for k in ["prestamo", "bid", "banco mundial", "bm"]):
        loans = db.query(Loan).order_by(desc(Loan.monto_aprobado)).limit(5).all()
        lines = ["Préstamos internacionales:"]
        for l in loans:
            lines.append(f"• {l.acreedor}: USD${l.monto_aprobado:,.0f} — {l.descripcion}")
        return "\n".join(lines)

    return ("No encontré una respuesta automática específica para esa consulta. "
            "Instala Ollama con `ollama pull llama3` para respuestas avanzadas en lenguaje natural.")


def _generate_contract_summary(c: Contract, flags: list, risk_level: str) -> str:
    summary = f"Contrato {c.numero_contrato or 'S/N'}\n"
    summary += f"Monto: RD${c.monto_original:,.0f}\n"
    summary += f"Modalidad: {c.modalidad}\n"
    summary += f"Nivel de riesgo: {risk_level}\n"
    if flags:
        summary += "Hallazgos:\n" + "\n".join(f"  ⚠ {f}" for f in flags)
    else:
        summary += "Sin hallazgos de riesgo identificados."
    return summary
