from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from ...core.database import get_db
from ...services.intelligence import (
    get_personas_interes,
    get_patrones_sospechosos,
    get_red_personas,
    get_nombres_frecuentes,
)

router = APIRouter(prefix="/intelligence", tags=["Inteligencia de Patrones"])


@router.get("/personas-interes")
def personas_interes(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
):
    """
    Ranking de personas de interés detectadas automáticamente.
    Combina: firmantes de contratos + representantes legales
    y detecta dobles roles, alta concentración de poder, etc.
    """
    return get_personas_interes(db, limit)


@router.get("/nombres-frecuentes")
def nombres_frecuentes(
    db: Session = Depends(get_db),
    min_apariciones: int = Query(2, ge=1),
    search: Optional[str] = None,
):
    """
    Todos los nombres que aparecen en el sistema rankeados por
    frecuencia y monto involucrado. Permite buscar una persona específica.
    """
    data = get_nombres_frecuentes(db, min_apariciones)
    if search:
        s = search.lower()
        data = [d for d in data if s in d["nombre"].lower()]
    return data


@router.get("/patrones")
def patrones_sospechosos(db: Session = Depends(get_db)):
    """
    Detecta patrones estadísticos anómalos:
    fraccionamiento, monopolio sectorial, dependencia única,
    contratación directa grande.
    """
    return get_patrones_sospechosos(db)


@router.get("/red-persona")
def red_persona(
    nombre: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
):
    """
    Grafo de conexiones para una persona específica.
    Muestra todos los contratos, empresas e instituciones asociados.
    """
    return get_red_personas(db, nombre)


@router.get("/resumen")
def resumen_inteligencia(db: Session = Depends(get_db)):
    """Vista rápida: top 10 personas + top 5 patrones + stats clave."""
    personas = get_personas_interes(db, limit=200)
    patrones = get_patrones_sospechosos(db)

    criticos = [p for p in patrones if p["severidad"] == "critica"]
    altos    = [p for p in patrones if p["severidad"] == "alta"]

    personas_doble_rol = [
        p for p in personas
        if "firmante" in p.get("roles", []) and "representante_legal" in p.get("roles", [])
    ]

    return {
        "top_personas": personas[:10],
        "top_patrones": patrones[:5],
        "stats": {
            "personas_detectadas": len(personas),
            "patrones_criticos": len(criticos),
            "patrones_altos": len(altos),
            "personas_doble_rol": len(personas_doble_rol),
            "total_patrones": len(patrones),
        },
    }
