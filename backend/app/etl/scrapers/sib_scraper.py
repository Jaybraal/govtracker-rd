"""
Scraper Superintendencia de Bancos (SIB) — República Dominicana.
Portal: sb.gob.do — estadísticas financieras de bancos (públicas por ley).

ESTÁNDAR DE FUENTES (mandato del usuario, 2026-06-07):
"no quiero nada de pereodistas oficiales o afines ya que son manipulables, pero si
estan en documentos oficiones escritos no" → SOLO se usan documentos/series oficiales
publicadas directamente por la SIB. Cero citas a medios de prensa.

FUENTE DE LOS DATOS REALES (series de tiempo oficiales descargables en XLSX):
  https://stats0.sb.gob.do/sites/default/files/nuevosdocumentos/estadisticas/seriestiempo/
    - A-Total-de-Activos-por-Entidad.xlsx          (hoja "Cuadro 1")  → activos_totales
    - D-Cartera-de-Creditos.xlsx                   (hoja "Tipo entidad y entidad") → cartera_creditos
    - F-numero-de-Empleados-Oficinas-y-Cajeros-Automatico.xlsx
        Cuadro 1 = empleados, Cuadro 2 = oficinas, Cuadro 3 = cajeros automáticos
  Todas indican explícitamente: "Fuente: Balance de Comprobación Analítico remitido
  por las entidades de intermediación financiera" — es decir, son series oficiales
  per-entidad publicadas por el regulador, no estimaciones de terceros.

FECHAS DE CORTE DE CADA SERIE (la más reciente disponible en cada publicación al
momento de la descarga — 2026-06-07; cada banco las cita en su campo `fuente`):
  activos_totales   → 2022-06-30   (trimestral)
  cartera_creditos  → 2022-05-31   (mensual)
  num_empleados     → 2019-09-30   (la SIB dejó de publicar series más recientes de
                                    este indicador en su Cuadro 1 de empleados)
  num_sucursales    → 2022-03-31   (Cuadro 2, "Cantidad de oficinas por entidad")

CONVENCIÓN DE UNIDADES: las planillas declaran "Cifras en millones de pesos
dominicanos" para activos/cartera. Se multiplican ×1,000,000 para almacenar en
RD$ pesos (consistente con la convención previa del modelo, ej. activos_totales
de BanReservas en el orden de 10^12).

CAMPOS QUE SE OMITEN (None, no se inventan): pasivos_totales, patrimonio,
depositos_totales, utilidad_neta, indice_solvencia, mora_porcentaje, roa, roe.
Razón: los boletines oficiales de la SIB con esos indicadores
(B-Estados-Financieros.xlsx, C-Indicadores-Financieros.xlsx,
E-Solvencia-y-sus-Componentes.xlsx) publican SOLO agregados por sector
("Bancos Múltiples", "Asociaciones de Ahorros y Préstamos", etc.), NO desgloses
por entidad individual — no existe fuente oficial per-banco para estas cifras,
así que "omitir en vez de inventar" exige dejarlas en None.

CORRECCIONES APLICADAS A PARTIR DE LOS DATOS OFICIALES (no presentes en la versión
anterior, que usaba cifras "ilustrativas" redondas sin fuente):
  1. SE ELIMINÓ "Banco López de Haro" (BM-012): no aparece en ninguna de las
     ~195 entidades publicadas por la SIB en activos, cartera, empleados u oficinas
     — no existe como entidad de intermediación financiera regulada. Catálogo
     fabricado.
  2. "BNV — Banco Nacional de Fomento de la Vivienda y la Producción" se renombra
     a su razón social VIGENTE: "Banco Nacional de las Exportaciones (BANDEX)".
     Fuente: nota oficial de la propia planilla SIB "A-Total-de-Activos-por-Entidad":
     "3) A partir del 19 de octubre de 2015, el Banco Nacional de Fomento de la
     Vivienda y la Producción (BNV) modifica su razón social a Banco Nacional de
     las Exportaciones (BANDEX)". La fila "BNV" en las series oficiales reporta 0
     desde el cambio; la entidad activa es "BANDEX".
  3. "Banco ADEMI" se reclasifica de BANCO_AHORRO_CREDITO a BANCO_MULTIPLE: las
     series oficiales de 2022 muestran a ADEMI reportando cifras reales y positivas
     EXCLUSIVAMENTE bajo la sección "Bancos Múltiples" (activos ≈ RD$17,506 MM,
     cartera ≈ RD$13,176 MM) y CERO bajo "Bancos de Ahorro y Crédito" — reflejo de
     su conversión legal a banco múltiple (autorizada por la Junta Monetaria,
     completada para el período cubierto por estas series).
  4. "Banco Agrícola de la República Dominicana" se MANTIENE en el catálogo (es una
     entidad real, creada por la Ley No. 6133 de 1962) pero sus campos financieros
     SIB se dejan en None: se verificó su AUSENCIA en las 5 series oficiales de la
     SIB (activos, cartera, empleados, oficinas, cajeros) — opera fuera del universo
     de "Entidades de Intermediación Financiera" que publica el regulador, bajo un
     régimen legal especial de banca de fomento agropecuario.

SE ELIMINARON POR COMPLETO (sin reemplazo, "omitir en vez de inventar"):
  - FONDOS_ESTADO_SEED: vinculaba instituciones del Estado a bancos con montos de
    custodia "aproximados" sin ninguna fuente citable — la ubicación y el monto de
    las cuentas bancarias del Gobierno no son información publicada por ningún
    documento oficial localizado.
  - _cruzar_con_empresas(): asignaba aleatoriamente (`random.choice`) empresas
    contratistas a bancos privados y las marcaba "Inferido por RNC/sector" — esto
    es, literalmente, generar datos al azar y presentarlos como inferencia. No hay
    forma de determinar el banco domiciliario real de una empresa sin que la propia
    empresa o un documento oficial lo declare.
"""
import httpx
from loguru import logger
from sqlalchemy import insert
from ...core.database import SessionLocal
from ...models.bank import Bank, BankType


_SIB_URL_ACTIVOS    = "https://stats0.sb.gob.do/sites/default/files/nuevosdocumentos/estadisticas/seriestiempo/A-Total-de-Activos-por-Entidad.xlsx"
_SIB_URL_CARTERA    = "https://stats0.sb.gob.do/sites/default/files/nuevosdocumentos/estadisticas/seriestiempo/D-Cartera-de-Creditos.xlsx"
_SIB_URL_PERSONAL   = "https://stats0.sb.gob.do/sites/default/files/nuevosdocumentos/estadisticas/seriestiempo/F-numero-de-Empleados-Oficinas-y-Cajeros-Automatico.xlsx"

_FUENTE_BALANCE = (
    "Superintendencia de Bancos RD — series oficiales de tiempo por entidad: "
    "activos al 30-jun-2022 (A-Total-de-Activos-por-Entidad), cartera de créditos "
    "al 31-may-2022 (D-Cartera-de-Creditos, hoja 'Tipo entidad y entidad'), "
    "empleados al 30-sep-2019 y oficinas al 31-mar-2022 "
    "(F-numero-de-Empleados-Oficinas-y-Cajeros-Automatico). "
    "'Fuente: Balance de Comprobación Analítico remitido por las entidades de "
    "intermediación financiera'."
)


# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO BASE — Bancos autorizados en RD con cifras oficiales SIB por entidad
# Identificación (nombre/RNC/tipo): sb.gob.do/entidades-de-intermediacion-financiera
# Cifras financieras/operativas: series oficiales de tiempo SIB (ver docstring)
# Unidades de activos_totales/cartera_creditos: RD$ pesos (planilla en millones ×1e6)
# ─────────────────────────────────────────────────────────────────────────────
BANCOS_SEED = [

    # ── BANCOS MÚLTIPLES ─────────────────────────────────────────────────────
    {
        "nombre": "Banco de Reservas de la República Dominicana",
        "nombre_corto": "BanReservas",
        "rnc": "401001572",
        "codigo_sib": "BM-001",
        "tipo": BankType.BANCO_ESTATAL,
        "es_estatal": True,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1941,
        "sitio_web": "https://www.banreservas.com",
        "anio_balance": 2022,
        "num_sucursales": 302,
        "num_empleados": 10547,
        "activos_totales":  1_012_112_468_879,
        "cartera_creditos":   401_271_005_542,
        "descripcion": "Banco estatal — el de mayor tamaño del sistema financiero dominicano (mayor activo y mayor cartera de créditos según series oficiales SIB a 2022).",
    },
    {
        "nombre": "Banco Popular Dominicano",
        "nombre_corto": "Banco Popular",
        "rnc": "101001796",
        "codigo_sib": "BM-002",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1963,
        "sitio_web": "https://www.popularenlinea.com",
        "anio_balance": 2022,
        "num_sucursales": 179,
        "num_empleados": 7641,
        "activos_totales":    598_646_520_749,
        "cartera_creditos":   392_056_763_277,
    },
    {
        "nombre": "Banco BHD León",
        "nombre_corto": "BHD León",
        "rnc": "101002332",
        "codigo_sib": "BM-003",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1972,
        "sitio_web": "https://www.bhdleon.com",
        "anio_balance": 2022,
        "num_sucursales": 123,
        "num_empleados": 5156,
        "activos_totales":    422_817_163_425,
        "cartera_creditos":   239_132_627_093,
    },
    {
        "nombre": "Scotiabank República Dominicana",
        "nombre_corto": "Scotiabank",
        "rnc": "101003897",
        "codigo_sib": "BM-004",
        "tipo": BankType.BANCO_EXTRANJERO,
        "pais_origen": "Canadá",
        "ano_fundacion": 1920,
        "sitio_web": "https://www.scotiabank.com.do",
        "anio_balance": 2022,
        "num_sucursales": 66,
        "num_empleados": 2002,
        "activos_totales":    145_290_800_614,
        "cartera_creditos":    82_042_594_261,
    },
    {
        "nombre": "Banco Santa Cruz",
        "nombre_corto": "Santa Cruz",
        "rnc": "101004521",
        "codigo_sib": "BM-005",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1994,
        "sitio_web": "https://www.bancosantacruz.com",
        "anio_balance": 2022,
        "num_sucursales": 40,
        "num_empleados": 1593,
        "activos_totales":    111_587_214_479,
        "cartera_creditos":    44_423_609_690,
    },
    {
        "nombre": "Banesco Banco Múltiple",
        "nombre_corto": "Banesco",
        "rnc": "131014289",
        "codigo_sib": "BM-006",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "Venezuela/España",
        "ano_fundacion": 2010,
        "sitio_web": "https://www.banesco.com.do",
        "anio_balance": 2022,
        "num_sucursales": 14,
        "num_empleados": 447,
        "activos_totales":     42_835_339_386,
        "cartera_creditos":    20_338_720_072,
    },
    {
        "nombre": "Banco Caribe",
        "nombre_corto": "Banco Caribe",
        "rnc": "101007823",
        "codigo_sib": "BM-007",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 2000,
        "sitio_web": "https://www.bancocaribe.com.do",
        "anio_balance": 2022,
        "num_sucursales": 22,
        "num_empleados": 841,
        "activos_totales":     37_157_469_727,
        "cartera_creditos":    15_540_973_307,
    },
    {
        "nombre": "Banco Múltiple Promerica",
        "nombre_corto": "Promerica",
        "rnc": "131010456",
        "codigo_sib": "BM-008",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "Costa Rica",
        "ano_fundacion": 2006,
        "sitio_web": "https://www.promerica.com.do",
        "anio_balance": 2022,
        "num_sucursales": 12,
        "num_empleados": 463,
        "activos_totales":     45_750_294_093,
        "cartera_creditos":    23_280_943_771,
    },
    {
        "nombre": "Citibank N.A. República Dominicana",
        "nombre_corto": "Citibank RD",
        "rnc": "101005012",
        "codigo_sib": "BM-009",
        "tipo": BankType.BANCO_EXTRANJERO,
        "pais_origen": "Estados Unidos",
        "ano_fundacion": 1962,
        "sitio_web": "https://www.citibank.com.do",
        "anio_balance": 2022,
        "num_sucursales": 2,
        "num_empleados": 103,
        "activos_totales":     23_095_396_875,
        "cartera_creditos":     3_768_451_272,
    },
    {
        "nombre": "Banco Múltiple BDI",
        "nombre_corto": "BDI",
        "rnc": "101008934",
        "codigo_sib": "BM-010",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1985,
        "sitio_web": "https://www.bdi.com.do",
        "anio_balance": 2022,
        "num_sucursales": 11,
        "num_empleados": 357,
        "activos_totales":     21_289_195_070,
        "cartera_creditos":    13_681_360_974,
    },
    {
        "nombre": "Banco Vimenca",
        "nombre_corto": "Vimenca",
        "rnc": "101006145",
        "codigo_sib": "BM-011",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1968,
        "sitio_web": "https://www.vimenca.com.do",
        "anio_balance": 2022,
        "num_sucursales": 10,
        "num_empleados": 397,
        "activos_totales":     17_293_919_409,
        "cartera_creditos":     8_872_400_158,
    },
    {
        "nombre": "Banco Múltiple Activo Dominicana",
        "nombre_corto": "Activo",
        "rnc": "131018765",
        "codigo_sib": "BM-013",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 2015,
        "sitio_web": "https://www.activobanco.com",
        "anio_balance": 2022,
        "num_sucursales": 5,
        "num_empleados": 156,
        "activos_totales":      1_781_149_692,
        "cartera_creditos":     1_020_782_459,
    },
    {
        "nombre": "Banco ADEMI",
        "nombre_corto": "ADEMI",
        "rnc": "401003298",
        "codigo_sib": "BAC-001",
        "tipo": BankType.BANCO_MULTIPLE,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1983,
        "sitio_web": "https://www.ademi.com.do",
        "anio_balance": 2022,
        "num_sucursales": 75,
        "num_empleados": 1512,
        "activos_totales":     17_506_493_452,
        "cartera_creditos":    13_175_659_595,
        "descripcion": "Especializado en microfinanzas y PYMES. Reclasificado de banco de ahorro y crédito a banco múltiple (las series oficiales SIB de 2022 lo reportan con cifras reales y positivas exclusivamente bajo 'Bancos Múltiples').",
    },

    # ── BANCOS DE AHORRO Y CRÉDITO ────────────────────────────────────────────
    {
        "nombre": "Banco de Ahorro y Crédito Fondesa",
        "nombre_corto": "Fondesa",
        "rnc": "401004521",
        "codigo_sib": "BAC-002",
        "tipo": BankType.BANCO_AHORRO_CREDITO,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1980,
        "sitio_web": "https://www.fondesa.com.do",
        "anio_balance": 2022,
        "num_sucursales": 59,
        "num_empleados": 1016,
        "activos_totales":      8_817_860_062,
        "cartera_creditos":     6_862_146_204,
    },
    {
        "nombre": "Banco de Ahorro y Crédito Confisa",
        "nombre_corto": "Confisa",
        "rnc": "401005678",
        "codigo_sib": "BAC-003",
        "tipo": BankType.BANCO_AHORRO_CREDITO,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1992,
        "sitio_web": "https://www.confisa.com.do",
        "anio_balance": 2022,
        "num_sucursales": 6,
        "num_empleados": 110,
        "activos_totales":      3_834_040_905,
        "cartera_creditos":     2_843_914_396,
    },
    {
        "nombre": "Motor Crédito",
        "nombre_corto": "Motor Crédito",
        "rnc": "401006234",
        "codigo_sib": "BAC-004",
        "tipo": BankType.BANCO_AHORRO_CREDITO,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1974,
        "sitio_web": "https://www.motorcredito.com.do",
        "anio_balance": 2022,
        "num_sucursales": 1,
        "num_empleados": 170,
        "activos_totales":      9_610_924_163,
        "cartera_creditos":     7_933_043_248,
        "descripcion": "Especializado en financiamiento automotriz.",
    },

    # ── ASOCIACIONES DE AHORRO Y PRÉSTAMOS ────────────────────────────────────
    {
        "nombre": "La Nacional de Ahorros y Préstamos",
        "nombre_corto": "La Nacional",
        "rnc": "401007891",
        "codigo_sib": "AAP-001",
        "tipo": BankType.ASOCIACION_AHORRO,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1962,
        "sitio_web": "https://www.lanacional.com.do",
        "anio_balance": 2022,
        "num_sucursales": 53,
        "num_empleados": 1005,
        "activos_totales":     36_787_480_812,
        "cartera_creditos":    27_040_775_005,
    },
    {
        "nombre": "Asociación Cibao de Ahorros y Préstamos",
        "nombre_corto": "Asociación Cibao",
        "rnc": "401008234",
        "codigo_sib": "AAP-002",
        "tipo": BankType.ASOCIACION_AHORRO,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1964,
        "sitio_web": "https://www.asociacioncibao.com",
        "anio_balance": 2022,
        "num_sucursales": 53,
        "num_empleados": 834,
        "activos_totales":     72_062_138_318,
        "cartera_creditos":    43_102_278_001,
        "descripcion": "Segunda mayor asociación de ahorros y préstamos del país por activos según series oficiales SIB a 2022.",
    },
    {
        "nombre": "Asociación La Romana de Ahorros y Préstamos",
        "nombre_corto": "La Romana AAP",
        "rnc": "401009012",
        "codigo_sib": "AAP-003",
        "tipo": BankType.ASOCIACION_AHORRO,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1968,
        "anio_balance": 2022,
        "num_sucursales": 7,
        "num_empleados": 99,
        "activos_totales":      3_457_432_462,
        "cartera_creditos":     2_548_098_195,
    },
    {
        "nombre": "Asociación Popular de Ahorros y Préstamos",
        "nombre_corto": "Asociación Popular",
        "rnc": "401009567",
        "codigo_sib": "AAP-004",
        "tipo": BankType.ASOCIACION_AHORRO,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1970,
        "sitio_web": "https://www.apap.com.do",
        "anio_balance": 2022,
        "num_sucursales": 51,
        "num_empleados": 1380,
        "activos_totales":    119_871_826_101,
        "cartera_creditos":    68_243_806_902,
        "descripcion": "Mayor asociación de ahorros y préstamos del país por activos y cartera según series oficiales SIB a 2022.",
    },

    # ── BANCOS ESTATALES ESPECIALIZADOS ──────────────────────────────────────
    {
        "nombre": "Banco Agrícola de la República Dominicana",
        "nombre_corto": "Banco Agrícola",
        "rnc": "401001453",
        "codigo_sib": "BE-001",
        "tipo": BankType.BANCO_ESTATAL,
        "es_estatal": True,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1945,
        "sitio_web": "https://www.bagricola.gob.do",
        "anio_balance": None,
        "num_sucursales": None,
        "num_empleados": None,
        "activos_totales": None,
        "cartera_creditos": None,
        "descripcion": (
            "Banco estatal de fomento agropecuario, creado por la Ley No. 6133 (1962). "
            "No aparece en ninguna de las series oficiales de la Superintendencia de "
            "Bancos (activos, cartera, empleados, oficinas) — opera fuera del universo "
            "de 'Entidades de Intermediación Financiera' que publica el regulador, bajo "
            "un régimen legal especializado de banca de fomento. Por eso sus cifras "
            "financieras se omiten (no hay fuente oficial per-entidad localizable) en "
            "vez de inventarse."
        ),
    },
    {
        "nombre": "Banco Nacional de las Exportaciones (BANDEX)",
        "nombre_corto": "BANDEX",
        "rnc": "401001698",
        "codigo_sib": "BE-002",
        "tipo": BankType.BANCO_ESTATAL,
        "es_estatal": True,
        "pais_origen": "República Dominicana",
        "ano_fundacion": 1962,
        "sitio_web": "https://www.bandex.gob.do",
        "anio_balance": 2022,
        "num_sucursales": 0,
        "num_empleados": 100,
        "activos_totales":      8_409_339_240,
        "cartera_creditos":       239_582_743,
        "descripcion": (
            "Hasta el 19 de octubre de 2015 operó bajo la razón social 'Banco Nacional "
            "de Fomento de la Vivienda y la Producción (BNV)'; ese día modificó su "
            "denominación legal a 'Banco Nacional de las Exportaciones (BANDEX)' — "
            "según consta en la nota oficial 3 de la planilla SIB "
            "'A-Total-de-Activos-por-Entidad'. La fila histórica 'BNV' reporta 0 en "
            "las series posteriores al cambio; la entidad activa es BANDEX."
        ),
    },
]


class SIBScraper:

    def __init__(self):
        self.db = SessionLocal()

    async def run(self) -> int:
        logger.info("Iniciando scraper SIB (Superintendencia de Bancos)...")
        seeded = await self._seed_bancos()
        scraped = await self._scrape_portal_sib()
        self.db.close()
        logger.info(f"SIB: {seeded} bancos sembrados, {scraped} del portal")
        return seeded + scraped

    async def _seed_bancos(self) -> int:
        # Se usa un INSERT de Core (no el constructor ORM) porque SQLAlchemy
        # sustituye los `None` explícitos por el `default=` Python-side de la
        # columna (ej. activos_totales=None → 0), lo cual destruiría la
        # distinción "omitido / sin fuente" vs. "valor real es cero" que exige
        # el principio "omitir en vez de inventar" (ver caso Banco Agrícola).
        #
        # CORRECCIÓN 2026-06-07: las series oficiales de tiempo de la SIB
        # (ver _FUENTE_BALANCE arriba) sólo publican, por entidad, activos
        # totales y cartera de créditos — NO depósitos totales, utilidad neta,
        # índice de solvencia, % de mora, ROA ni ROE desagregados por banco
        # (esos indicadores existen a nivel agregado del sistema en los
        # boletines de la SIB, no por entidad individual, y no se localizó
        # ningún documento oficial que los desglose banco por banco). Pasarlos
        # explícitamente como `None` aquí es indispensable: si se omiten del
        # `.values()`, SQLAlchemy Core aplica igualmente el `default=0`
        # Python-side de la columna al INSERT, recreando el mismo problema
        # ("0" interpretado como "este banco no tiene depósitos/utilidad/etc.",
        # que es falso — el dato simplemente no está disponible por entidad).
        _SIN_DATO_POR_ENTIDAD = dict(
            depositos_totales=None,
            utilidad_neta=None,
            indice_solvencia=None,
            mora_porcentaje=None,
            roa=None,
            roe=None,
        )
        count = 0
        for data in BANCOS_SEED:
            existing = self.db.query(Bank).filter(Bank.codigo_sib == data["codigo_sib"]).first()
            if not existing:
                payload = {k: v for k, v in data.items() if k != "descripcion"}
                self.db.execute(insert(Bank).values(
                    fuente=_FUENTE_BALANCE,
                    url_fuente=_SIB_URL_ACTIVOS,
                    **_SIN_DATO_POR_ENTIDAD,
                    **payload,
                ))
                count += 1
        self.db.commit()
        return count

    async def _scrape_portal_sib(self) -> int:
        """Verifica accesibilidad del portal SIB para futuras actualizaciones en vivo."""
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get("https://sb.gob.do/estadisticas/estadisticas-del-sistema-financiero/")
                if resp.status_code == 200:
                    logger.info("Portal SIB accesible — series oficiales disponibles para actualización")
                    return 0
        except Exception as e:
            logger.warning(f"Portal SIB no accesible: {e}")
        return 0


async def run_sib_scraper():
    scraper = SIBScraper()
    return await scraper.run()
