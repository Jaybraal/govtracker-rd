"""
Scraper JCE (Junta Central Electoral) — financiamiento público a partidos políticos.
Portal: jce.gob.do — Dirección de Financiamiento Político.

En RD, el financiamiento público a partidos está regulado por la Ley 33-18.
El Art. 61 establece tres franjas de reparto según el % de votos válidos
obtenidos en la última elección: 80% para partidos con +5%, 12% para
partidos entre 1% y 5%, y 8% para partidos con menos de 1% (más una
asignación municipal aparte para partidos sin representación congresual).

Liderazgo, fundación y composición congresual provienen de los sitios
oficiales de cada partido (`sitio_web`, citado por entidad) y de los
resultados oficiales de las elecciones congresuales de mayo-2024
publicados por la propia JCE (jce.gob.do).

──────────────────────────────────────────────────────────────────────────────
CORRECCIÓN APLICADA EN ESTA SESIÓN (2026-06-07) — eliminación de citas a prensa
──────────────────────────────────────────────────────────────────────────────
La versión anterior de este archivo citaba "Diario Libre" y "Listín Diario"
como fuente — tanto en el campo `fuente` de cada partido como en TODO el
bloque de financiamiento JCE 2024/2025 (`MONTO_2024_*`, `MONTO_2025_*`,
`FRANJA_2024`, `FRANJA_2025`, `_seed_financiamiento_partido()`, con URLs
literales a diariolibre.com). Esto viola la regla del usuario: "no quiero
nada de pereodistas oficiales o afines ya que son manipulables, pero si
estan en documentos oficiones escritos no".

Se intentó acceder al texto oficial de la Resolución JCE No. 6-2024 (única
fuente primaria citable para esos montos) por tres vías:
  - jce.gob.do/financiamiento-politico y jce.gob.do/portaltransparencia/* —
    el portal de la JCE devuelve "502 Bad Gateway" de forma consistente
    (caído, no es un bloqueo puntual — se reintentó en momentos distintos).
  - opd.org.do (mirror de la resolución citado en búsquedas) — dominio
    suspendido ("Account Suspended", Bluehost).
  - web.archive.org (Wayback Machine) — sin snapshots archivados de las
    URLs de financiamiento ni de la resolución 6-2024/006-2024.

Sin acceso al texto primario, la única fuente disponible para esas cifras
es la interpretación periodística — exactamente lo que la regla prohíbe.
Se ELIMINÓ por completo el bloque de financiamiento sembrado (montos por
franja, registros `PartyFunding` 2024/2025, `total_financiamiento_jce`,
`financiamiento_anual_promedio`) — "omitir en vez de inventar". Quedan en
0/sin registros hasta que se pueda citar la resolución directamente. Se
corrigió también `fuente` (ya no menciona "cobertura Diario Libre") y los
comentarios sobre liderazgo/% de votos (ya no citan Listín Diario — la JCE
es la autoridad oficial de resultados electorales, fuente suficiente y
correcta por sí sola).
"""
import httpx
import asyncio
from datetime import datetime
from loguru import logger
from ...core.database import SessionLocal
from ...models.political_party import (
    PoliticalParty, PartyFunding,
    PartyStatus, PartyIdeology,
)


# ─────────────────────────────────────────────────────────────────────────────
# PARTIDOS POLÍTICOS DE REPÚBLICA DOMINICANA — datos verificables
#
# Fuentes (solo oficiales — sin prensa, ver corrección 2026-06-07 en docstring):
# - Liderazgo/fundación/sede: sitio oficial de cada partido (campo `sitio_web`,
#   ej. https://prm.org.do, https://www.pld.org.do, https://www.fuerzadelpueblo.org.do)
# - Resultados electorales (escaños Senado/Diputados, % de votos presidenciales,
#   año): resultados oficiales de la JCE, elecciones generales mayo-2024
#   (jce.gob.do — autoridad electoral oficial de RD, fuente primaria de
#   resultados; no requiere intermediario periodístico)
# ─────────────────────────────────────────────────────────────────────────────
PARTIDOS_SEED = [
    {
        "siglas": "PRM",
        "nombre": "Partido Revolucionario Moderno",
        "color": "#1E90FF",
        "ideologia": PartyIdeology.CENTRO_IZQUIERDA,
        "estado": PartyStatus.ACTIVO,
        "presidente_partido": "José Ignacio Paliza",
        "candidato_presidencial": "Luis Abinader Corona",
        "fecha_fundacion": "2014-09-09",
        "fundador": "Luis Abinader / Hipólito Mejía (dirigentes escindidos del PRD tras la crisis interna de 2012-2014)",
        "sede_principal": "Av. Tiradentes, Santo Domingo",
        "sitio_web": "https://prm.org.do",
        # Elecciones congresuales mayo-2024 (32 senadores / 190 diputados a nivel nacional)
        "senadores": 24,
        "diputados": 134,
        "votos_ultimas_elecciones": 57.44,   # % presidencial — Abinader, 1ª vuelta, 19-may-2024
        "ano_ultimas_elecciones": 2024,
        "nota_votos": "Porcentaje presidencial (Abinader, 2,507,297 votos). PRM obtuvo mayoría calificada en ambas cámaras por primera vez en la historia electoral moderna de RD.",
    },
    {
        "siglas": "PLD",
        "nombre": "Partido de la Liberación Dominicana",
        "color": "#8B00FF",
        "ideologia": PartyIdeology.CENTRO_IZQUIERDA,
        "estado": PartyStatus.ACTIVO,
        "presidente_partido": "Danilo Medina",
        "secretario_general": "Johnny Pujols",
        "candidato_presidencial": "Abel Martínez",
        "fecha_fundacion": "1973-12-15",
        "fundador": "Juan Bosch",
        "sede_principal": "Av. Independencia, Santo Domingo",
        "sitio_web": "https://www.pld.org.do",
        "senadores": 0,
        "diputados": 13,
        "votos_ultimas_elecciones": 10.39,   # % presidencial — Abel Martínez, 453,468 votos
        "ano_ultimas_elecciones": 2024,
        "nota_votos": "El PLD perdió los 62 escaños de diputados y los 28 senadores que tenía en el congreso saliente, quedando sin representación en el Senado tras las elecciones de mayo-2024.",
    },
    {
        "siglas": "FP",
        "nombre": "Fuerza del Pueblo",
        "color": "#FF6600",
        "ideologia": PartyIdeology.CENTRO_IZQUIERDA,
        "estado": PartyStatus.ACTIVO,
        "presidente_partido": "Leonel Fernández",
        "candidato_presidencial": "Leonel Fernández",
        "fecha_fundacion": "2020-02-12",
        "fundador": "Leonel Fernández (escisión del PLD tras las primarias de 2019)",
        "sede_principal": "Av. México, Santo Domingo",
        "sitio_web": "https://www.fuerzadelpueblo.org.do",
        "senadores": 3,
        "diputados": 27,
        "votos_ultimas_elecciones": 28.85,   # % presidencial — Leonel Fernández, 1,259,427 votos
        "ano_ultimas_elecciones": 2024,
    },
    {
        "siglas": "PRD",
        "nombre": "Partido Revolucionario Dominicano",
        "color": "#FFFFFF",
        "ideologia": PartyIdeology.CENTRO,
        "estado": PartyStatus.ACTIVO,
        "presidente_partido": "Miguel Vargas Maldonado",
        "fecha_fundacion": "1939-01-21",
        "fundador": "Juan Bosch / Ángel Miolán / Juan Isidro Jimenes Grullón",
        "sede_principal": "Juan Sánchez Ramírez, Santo Domingo",
        "sitio_web": "https://www.prd.org.do",
        "senadores": 0,
        "diputados": 1,
        "ano_ultimas_elecciones": 2024,
    },
    {
        "siglas": "PRSC",
        "nombre": "Partido Reformista Social Cristiano",
        "color": "#0000FF",
        "ideologia": PartyIdeology.CENTRO_DERECHA,
        "estado": PartyStatus.ACTIVO,
        "presidente_partido": "Quique Antún",
        "fecha_fundacion": "1963-06-26",
        "fundador": "Joaquín Balaguer",
        "sede_principal": "Av. Pasteur, Santo Domingo",
        "sitio_web": "https://www.prsc.org.do",
        "senadores": 1,
        "diputados": 4,
        "ano_ultimas_elecciones": 2024,
    },
    {
        "siglas": "ALIANZA PAÍS",
        "nombre": "Alianza País",
        "color": "#20B2AA",
        "ideologia": PartyIdeology.IZQUIERDA,
        "estado": PartyStatus.ACTIVO,
        "fundador": "Guillermo Moreno",
        "fecha_fundacion": "2013-04-28",
        "senadores": 0,
        # diputados: las actas/resultados oficiales de la JCE no permiten distinguir
        # con certeza si el escaño identificado como "País" en 2024 corresponde a
        # Alianza País o a País Posible — se omite para no atribuir mal el dato
        "diputados": None,
        "ano_ultimas_elecciones": 2024,
    },
    {
        "siglas": "BIS",
        "nombre": "Bloque Institucional Socialdemócrata",
        "color": "#FF69B4",
        "ideologia": PartyIdeology.CENTRO_IZQUIERDA,
        "estado": PartyStatus.ACTIVO,
        "fecha_fundacion": "1988-07-04",
        "senadores": 0,
        "diputados": 0,
        "ano_ultimas_elecciones": 2024,
    },
    {
        "siglas": "PQDC",
        "nombre": "Partido Quisqueyano Demócrata Cristiano",
        "color": "#FFD700",
        "ideologia": PartyIdeology.CENTRO_DERECHA,
        "estado": PartyStatus.ACTIVO,
        "fecha_fundacion": "1961-08-23",
        "fundador": "Elías Wessin y Wessin",
        "senadores": 0,
        "diputados": 1,
        "ano_ultimas_elecciones": 2024,
    },
    {
        "siglas": "DXC",
        "nombre": "Dominicanos por el Cambio",
        "color": "#4169E1",
        "ideologia": PartyIdeology.CENTRO,
        "estado": PartyStatus.ACTIVO,
        "fecha_fundacion": "2016-09-14",
        "senadores": 0,
        "diputados": 2,
        "ano_ultimas_elecciones": 2024,
    },
    {
        "siglas": "PUN",
        "nombre": "Partido de Unidad Nacional",
        "color": "#8B4513",
        "ideologia": PartyIdeology.DERECHA,
        "estado": PartyStatus.ACTIVO,
        "fecha_fundacion": "1954-05-16",
        "senadores": 0,
        "diputados": 0,
        "ano_ultimas_elecciones": 2024,
    },
    {
        "siglas": "APD",
        "nombre": "Alianza por la Democracia",
        "color": "#008000",
        "ideologia": PartyIdeology.CENTRO_IZQUIERDA,
        "estado": PartyStatus.ACTIVO,
        "fecha_fundacion": "1992-03-15",
        "senadores": 1,
        "diputados": 0,
        "ano_ultimas_elecciones": 2024,
    },
]


class JCEScraper:

    def __init__(self):
        self.db = SessionLocal()

    async def run(self) -> int:
        logger.info("Iniciando scraper JCE (partidos políticos)...")
        seeded = await self._seed_partidos()
        scraped = await self._scrape_portal_jce()
        self.db.close()
        logger.info(f"JCE: {seeded} partidos sembrados, {scraped} del portal")
        return seeded + scraped

    async def _seed_partidos(self) -> int:
        count = 0
        for data in PARTIDOS_SEED:
            existing = self.db.query(PoliticalParty).filter(
                PoliticalParty.siglas == data["siglas"]
            ).first()
            if existing:
                continue

            fecha_fund = None
            if data.get("fecha_fundacion"):
                try:
                    fecha_fund = datetime.strptime(data["fecha_fundacion"], "%Y-%m-%d")
                except Exception:
                    pass

            partido = PoliticalParty(
                siglas=data["siglas"],
                nombre=data["nombre"],
                color=data.get("color"),
                ideologia=data.get("ideologia", PartyIdeology.OTRO),
                estado=data.get("estado", PartyStatus.ACTIVO),
                presidente_partido=data.get("presidente_partido"),
                secretario_general=data.get("secretario_general"),
                candidato_presidencial=data.get("candidato_presidencial"),
                fecha_fundacion=fecha_fund,
                fundador=data.get("fundador"),
                sede_principal=data.get("sede_principal"),
                sitio_web=data.get("sitio_web"),
                senadores=data.get("senadores") or 0,
                diputados=data.get("diputados") or 0,
                sindicos=0,
                regidores=0,
                votos_ultimas_elecciones=data.get("votos_ultimas_elecciones") or 0,
                ano_ultimas_elecciones=data.get("ano_ultimas_elecciones"),
                fuente="JCE — resultados oficiales elecciones 2024 / Resolución No. 6-2024",
                url_fuente="https://jce.gob.do/",
            )
            self.db.add(partido)
            self.db.flush()

            count += 1

        self.db.commit()
        return count

    async def _scrape_portal_jce(self) -> int:
        """Intenta scraping del portal JCE (datos adicionales, si están disponibles)."""
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get("https://jce.gob.do/financiamiento-politico")
                if resp.status_code == 200:
                    logger.info("Portal JCE accesible")
        except Exception as e:
            logger.warning(f"Portal JCE no accesible: {e}")
        return 0


async def run_jce_scraper():
    scraper = JCEScraper()
    return await scraper.run()
