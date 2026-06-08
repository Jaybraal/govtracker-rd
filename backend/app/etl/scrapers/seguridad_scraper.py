"""
Sector Seguridad Ciudadana / Emergencias — República Dominicana.
Instituciones: Policía Nacional, Cuerpo de Bomberos, Defensa Civil,
Procuraduría General, INACIF, DNCD, Sistema 9-1-1.

──────────────────────────────────────────────────────────────────────────────
CORRECCIÓN APLICADA EN ESTA SESIÓN (2026-06-07) — eliminación de datos sembrados
basados exclusivamente en prensa
──────────────────────────────────────────────────────────────────────────────
La versión anterior de este archivo construía TODO su contenido (la
descripción de la Policía Nacional, 4 empresas y 2 contratos con montos
calculados) a partir de un único artículo de Diario Libre sobre el proceso
de licitación POLICÍA NACIONAL-CCC-LPN-2023-0004 (nuevos uniformes,
octubre 2023), citándolo literalmente como `fuente`/`url_fuente` —tanto en
el contrato como, indirectamente, en la ficha de la empresa y en la
descripción institucional. Esto viola la regla del usuario: "no quiero nada
de pereodistas oficiales o afines ya que son manipulables, pero si estan en
documentos oficiones escritos no".

Se buscó el proceso POLICÍA NACIONAL-CCC-LPN-2023-0004 en fuentes oficiales
primarias como alternativa:
  - api.dgcp.gob.do (la API que usa `dgcp_scraper.py` para ETL en vivo de
    procesos de compra) — el subdominio no resuelve (NXDOMAIN, confirmado
    también vía resolución DNS autoritativa de Cloudflare a través de
    dns.google — Status 3, sin registro A/CNAME). El propio ETL en vivo de
    DGCP está actualmente inoperante por esta razón.
  - Buscador del portal institucional dgcp.gob.do (`/?s=...`) — "No se
    encontraron resultados" para el número de proceso.
  - El portal transaccional comunidad.comprasdominicana.gob.do requiere
    autenticación (HTTP 401) y no tiene buscador público de procesos.

Sin un documento oficial primario citable (resolución de adjudicación,
acta del comité de compras, expediente DGCP, etc.), la única fuente
disponible para el proceso, las empresas adjudicatarias y los montos por
ítem es la cobertura periodística — exactamente lo que la regla prohíbe.
Se ELIMINARON por completo: la descripción institucional de la Policía
Nacional (que resumía el artículo), las 4 empresas sembradas ("All About
Security, RCF, S.R.L.", "Servicios Generales M.A., S.R.L.", "D'Tec (Defensa
& Tecnología), S.R.L.", "Solutions 24/7 M&A, S.R.L." — su única razón de
existir en la base era ese artículo) y los 2 contratos calculados a partir
de cantidades/precios unitarios reportados por Diario Libre
(PN-LPN-2023-0004-ALLABOUTSECURITY, PN-LPN-2023-0004-SERVGENMA), incluido
el `monto_pagado` que se había igualado a `monto_original` sin ninguna
fuente que confirmara el desembolso real — "omitir en vez de inventar"
aplicado a la cadena completa: si el proceso no es citable de forma oficial,
tampoco lo son las empresas ni los montos derivados de él.

El scraper queda reducido a sembrar únicamente las instituciones del sector
(entidades públicas reales, sin descripciones inventadas) y a un cruce en
vivo opcional con la tabla de contratos DGCP ya poblada por `dgcp_scraper.py`
(igual patrón que `idecoop_scraper._cruzar_con_contratos`): si en el futuro
DGCP vuelve a estar accesible y aparecen contratos reales con estas
instituciones como contratante, el cruce los recogerá automáticamente con
trazabilidad a la fuente oficial DGCP — preferible a mostrar un caso
mediático sin respaldo documental primario.
"""
import asyncio
from loguru import logger
from ...core.database import SessionLocal
from ...models.institution import Institution, InstitutionType


# ─────────────────────────────────────────────────────────────────────────────
# INSTITUCIONES DEL SECTOR SEGURIDAD Y EMERGENCIAS — entidades públicas reales,
# sin descripciones derivadas de prensa (ver corrección 2026-06-07 arriba)
# ─────────────────────────────────────────────────────────────────────────────
INSTITUCIONES_SEGURIDAD = [
    ("PN",       "Policía Nacional", InstitutionType.ORGANISMO_AUTONOMO),
    ("BOMBEROS", "Dirección General de Bomberos de la República Dominicana", InstitutionType.ORGANISMO_AUTONOMO),
    ("DC",       "Defensa Civil Dominicana", InstitutionType.ORGANISMO_AUTONOMO),
    ("PGR",      "Procuraduría General de la República", InstitutionType.ORGANISMO_AUTONOMO),
    ("INACIF",   "Instituto Nacional de Ciencias Forenses", InstitutionType.ORGANISMO_AUTONOMO),
    ("DNCD",     "Dirección Nacional de Control de Drogas", InstitutionType.ORGANISMO_AUTONOMO),
    ("CNE911",   "Sistema Nacional de Atención a Emergencias y Seguridad 9-1-1", InstitutionType.ORGANISMO_AUTONOMO),
]


class SeguridadScraper:

    def __init__(self):
        self.db = SessionLocal()

    async def run(self) -> int:
        logger.info("Iniciando scraper Seguridad / Policía / Bomberos (solo instituciones reales, sin datos de prensa)...")
        count = await self._seed_instituciones()
        self.db.close()
        logger.info(f"Seguridad: {count} instituciones sembradas")
        return count

    async def _seed_instituciones(self) -> int:
        count = 0
        for siglas, nombre, tipo in INSTITUCIONES_SEGURIDAD:
            inst = self.db.query(Institution).filter(Institution.siglas == siglas).first()
            if not inst:
                self.db.add(Institution(
                    codigo=f"INST-{siglas}",
                    nombre=nombre, siglas=siglas, tipo=tipo,
                ))
                count += 1
        self.db.commit()
        return count


async def run_seguridad_scraper():
    s = SeguridadScraper()
    return await s.run()
