"""
Scraper para Crédito Público RD — préstamos internacionales y bonos soberanos.
Fuente: creditopublico.gob.do

ESTÁNDAR DE FUENTES: cada registro de KNOWN_LOANS proviene de un comunicado o
documento oficial publicado directamente por la institución involucrada
(Ministerio de Hacienda, Presidencia de la República, Fondo Monetario
Internacional) — NO de coberturas de prensa de terceros, siguiendo el criterio
de que estas últimas son fuentes manipulables. `url_fuente` enlaza siempre al
comunicado oficial original.

Notas de criterio aplicadas:
- Cuando el comunicado reporta una tasa flotante (Libor + margen) sin indicar
  la tasa total efectiva, se omite `tasa_interes` (None): el margen fijo no
  equivale a la tasa total y registrarlo como tal sería inventar un dato.
- Cuando el comunicado solo da el año de vencimiento de un bono (sin día/mes),
  se omite `fecha_vencimiento` (el campo es DateTime; rellenar día/mes sería
  inventar precisión que la fuente no ofrece) y el año queda citado en texto.
- Las colocaciones de bonos en un solo evento pero con tramos de distinto
  cupón/plazo/ISIN se registran como préstamos independientes, porque el
  modelo `Loan` solo admite una tasa y un plazo por registro — combinarlos
  en un único registro implicaría inventar un promedio que la fuente no da.
- Para bonos, `monto_desembolsado = monto_aprobado`: a diferencia de un
  préstamo con desembolsos programados, la liquidación de una emisión de
  bonos transfiere la totalidad de lo colocado de una sola vez (característica
  del instrumento, no una cifra estimada).

Se eliminó del listado el financiamiento de China Eximbank para la Planta
Termoeléctrica Punta Catalina: ese préstamo ya está sembrado —con mayor detalle
y mejor fuente (resolución del Congreso, fechas, tasa)— por
`punta_catalina_seed.py`, que es la fuente única de verdad para ese caso.
"""
import httpx
import asyncio
from datetime import datetime
from typing import Optional
from loguru import logger
from bs4 import BeautifulSoup
from ...core.config import settings
from ...core.database import SessionLocal
from ...models.loan import Loan, LoanStatus


KNOWN_LOANS = [
    # ── FMI: Instrumento de Financiamiento Rápido — emergencia COVID-19 (2020) ──
    # Fuente: FMI, Comunicado de Prensa No. 20/195 (29 de abril de 2020)
    {"acreedor": "FMI - Fondo Monetario Internacional", "tipo_acreedor": "multilateral",
     "descripcion": "Instrumento de Financiamiento Rápido (RFI): asistencia de emergencia "
                    "ante el COVID-19 — DEG 477.4 millones (equivalentes a unos US$650 "
                    "millones, 100% de la cuota del país en el FMI), aprobada por el "
                    "Directorio Ejecutivo el 29 de abril de 2020 y desembolsada de inmediato",
     "objeto": "Apoyo de balanza de pagos y financiamiento de gasto sanitario y de "
               "protección social ante la pandemia de COVID-19",
     "monto_aprobado": 650_000_000, "monto_desembolsado": 650_000_000, "moneda": "USD",
     "estado": LoanStatus.COMPLETADO,
     "fecha_aprobacion": datetime(2020, 4, 29),
     "fuente": "Fondo Monetario Internacional — Comunicado de Prensa No. 20/195",
     "url_fuente": "https://www.imf.org/en/News/Articles/2020/04/30/pr-20195-dominican-republic-imf-executive-board-approves-us-650-million-in-emergency-assistance"},

    # ── BCIE: Presa de Monte Grande, Fase III (2018) ──────────────────────────
    # Fuente: Ministerio de Hacienda, comunicado oficial
    {"acreedor": "BCIE - Banco Centroamericano de Integración Económica", "tipo_acreedor": "multilateral",
     "descripcion": "Contrato de préstamo para ejecutar la Fase III del Proyecto Múltiple "
                    "Presa de Monte Grande (Barahona), suscrito el 9 de abril de 2018 por "
                    "el ministro de Hacienda Donald Guerrero Ortiz y el vicepresidente "
                    "ejecutivo del BCIE, Alejandro Rodríguez Zamora. Tasa pactada: Libor a "
                    "6 meses + margen fijo de 2.20% (variable; no se registra como tasa "
                    "única), comisión de compromiso de 0.25% semestral, de administración "
                    "y seguimiento de 0.25% y de estructuración de 0.75%. Plazo de "
                    "ejecución: 36 meses",
     "objeto": "Obras complementarias de la presa multipropósito de Monte Grande, "
               "ejecutadas por el INDRHI, en beneficio de la región Enriquillo",
     "monto_aprobado": 249_600_000, "moneda": "USD",
     "estado": LoanStatus.ACTIVO,
     "plazo_anos": 13,
     "fecha_aprobacion": datetime(2018, 4, 9),
     "fuente": "Ministerio de Hacienda — Comunicado oficial",
     "url_fuente": "https://www.hacienda.gob.do/republica-dominicana-suscribe-contrato/"},

    # ── BID: administración tributaria y gestión del gasto público (2017) ────
    # Fuente: Ministerio de Hacienda, comunicado oficial
    {"acreedor": "BID - Banco Interamericano de Desarrollo", "tipo_acreedor": "multilateral",
     "descripcion": "Contrato de préstamo para mejoras en la administración tributaria y "
                    "la gestión del gasto público, firmado el 2 de octubre de 2017 por el "
                    "ministro de Hacienda Donald Guerrero Ortiz y la representante del BID "
                    "en el país, Flora Montealegre Painter. Tasa pactada: Libor a 3 meses + "
                    "margen de fondeo del BID (variable; no se registra como tasa única). "
                    "Repago en 38 amortizaciones semestrales",
     "objeto": "Fortalecimiento institucional de la Dirección General de Impuestos "
               "Internos —DGII— (componente I) y del Ministerio de Hacienda (componente II)",
     "monto_aprobado": 50_000_000, "moneda": "USD",
     "estado": LoanStatus.ACTIVO,
     "plazo_anos": 19, "periodo_gracia_anos": 5,
     "fecha_aprobacion": datetime(2017, 10, 2),
     "fuente": "Ministerio de Hacienda — Comunicado oficial",
     "url_fuente": "https://www.hacienda.gob.do/ministerio-de-hacienda-y-bid-firman-prestamo-por-us50-millones-para-fortalecer-administracion-tributaria-y-gestion-del-gasto-publico/"},

    # ── Banco Mundial: segundo Cat-DDO — línea contingente ante desastres (2022) ──
    # Fuente: Ministerio de Hacienda, comunicado oficial
    {"acreedor": "Banco Mundial", "tipo_acreedor": "multilateral",
     "descripcion": "Segundo Préstamo para Políticas de Desarrollo con Opción de "
                    "Desembolso Diferido ante Catástrofes (Cat-DDO), anunciado el 5 de "
                    "diciembre de 2022 por el ministro de Hacienda José Manuel «Jochi» "
                    "Vicente y la representante residente del Banco Mundial, Alexandria "
                    "Valerio. Es la segunda operación de este tipo para el país: la "
                    "primera (2018) se desembolsó en 2020 como liquidez de respuesta al "
                    "COVID-19",
     "objeto": "Línea de liquidez contingente de desembolso inmediato para fortalecer la "
               "preparación, respuesta y recuperación del Estado dominicano ante riesgos "
               "de desastres naturales y sanitarios",
     "monto_aprobado": 230_000_000, "moneda": "USD",
     "estado": LoanStatus.ACTIVO,
     "fecha_aprobacion": datetime(2022, 12, 5),
     "fuente": "Ministerio de Hacienda — Comunicado oficial",
     "url_fuente": "https://www.hacienda.gob.do/banco-mundial-apoya-a-la-republica-dominicana-para-estar-mejor-preparada-ante-los-riesgos-de-desastres/"},

    # ── Bonos soberanos — colocación de enero 2021, US$2,500MM en 2 tramos ───
    # Fuente: Ministerio de Hacienda, comunicado oficial. Demanda conjunta de
    # US$10,000MM (4x lo ofrecido); asesores Citibank y JP Morgan; ministro
    # Jochi Vicente, viceministra de Crédito Público María José Martínez.
    # Cada tramo tiene cupón y vencimiento propios → registros independientes.
    {"acreedor": "Mercado Internacional de Capitales (tenedores de bonos soberanos)", "tipo_acreedor": "bono",
     "descripcion": "Colocación de bonos soberanos de enero de 2021 — tramo de "
                    "reapertura del bono con vencimiento en 2030 (rendimiento 3.87%, "
                    "primer tramo de una colocación conjunta de US$2,500 millones con "
                    "demanda total de US$10,000 millones)",
     "objeto": "Cobertura de necesidades de financiamiento externo presupuestadas para "
               "2021, conforme al Presupuesto General del Estado aprobado por el Congreso",
     "monto_aprobado": 1_000_000_000, "monto_desembolsado": 1_000_000_000, "moneda": "USD",
     "estado": LoanStatus.ACTIVO,
     "tasa_interes": 3.87, "plazo_anos": 9,
     "fecha_aprobacion": datetime(2021, 1, 14),
     "fuente": "Ministerio de Hacienda — Comunicado oficial",
     "url_fuente": "https://www.hacienda.gob.do/gobierno-emite-bonos-soberanos-por-us2500-millones/"},
    {"acreedor": "Mercado Internacional de Capitales (tenedores de bonos soberanos)", "tipo_acreedor": "bono",
     "descripcion": "Colocación de bonos soberanos de enero de 2021 — tramo de nueva "
                    "emisión con vencimiento en 2041 (rendimiento 5.30%), el primer bono "
                    "soberano de un país latinoamericano o de mercados emergentes con "
                    "plazo de 20 años (segundo tramo de una colocación conjunta de "
                    "US$2,500 millones con demanda total de US$10,000 millones)",
     "objeto": "Cobertura de necesidades de financiamiento externo presupuestadas para "
               "2021, conforme al Presupuesto General del Estado aprobado por el Congreso",
     "monto_aprobado": 1_500_000_000, "monto_desembolsado": 1_500_000_000, "moneda": "USD",
     "estado": LoanStatus.ACTIVO,
     "tasa_interes": 5.30, "plazo_anos": 20,
     "fecha_aprobacion": datetime(2021, 1, 14),
     "fuente": "Ministerio de Hacienda — Comunicado oficial",
     "url_fuente": "https://www.hacienda.gob.do/gobierno-emite-bonos-soberanos-por-us2500-millones/"},

    # ── Bonos soberanos — colocación histórica de septiembre 2020, US$3,800MM en 3 tramos ──
    # Fuente: Presidencia de la República, comunicado oficial: "la transacción más
    # grande registrada en Centroamérica y el Caribe". Demanda conjunta de
    # US$9,600MM (2.5x lo requerido); ministro Jochi Vicente; asesores Citibank
    # y JP Morgan. Cada tramo tiene cupón/moneda/vencimiento propios → registros
    # independientes.
    {"acreedor": "Mercado Internacional de Capitales (tenedores de bonos soberanos)", "tipo_acreedor": "bono",
     "descripcion": "Colocación histórica de bonos soberanos de septiembre de 2020 — "
                    "tramo de nueva emisión a 12 años, rendimiento 4.875% (primer tramo "
                    "de una colocación conjunta de US$3,800 millones con demanda total de "
                    "US$9,600 millones, calificada por la Presidencia como «la "
                    "transacción más grande registrada en Centroamérica y el Caribe»)",
     "objeto": "Financiamiento de los programas sociales Quédate en Casa, FASE y Pa Ti, "
               "del sector salud frente a la pandemia de COVID-19, y compromisos de "
               "cierre del año fiscal 2020",
     "monto_aprobado": 1_800_000_000, "monto_desembolsado": 1_800_000_000, "moneda": "USD",
     "estado": LoanStatus.ACTIVO,
     "tasa_interes": 4.875, "plazo_anos": 12,
     "fecha_aprobacion": datetime(2020, 9, 17),
     "fuente": "Presidencia de la República — Comunicado oficial",
     "url_fuente": "https://presidencia.gob.do/noticias/gobierno-logra-historica-emision-de-bonos-soberanos-por-3800-millones-de-dolares"},
    {"acreedor": "Mercado Internacional de Capitales (tenedores de bonos soberanos)", "tipo_acreedor": "bono",
     "descripcion": "Colocación histórica de bonos soberanos de septiembre de 2020 — "
                    "tramo de reapertura del bono con vencimiento en 2060, rendimiento "
                    "6.25% (segundo tramo de una colocación conjunta de US$3,800 millones "
                    "con demanda total de US$9,600 millones)",
     "objeto": "Financiamiento de los programas sociales Quédate en Casa, FASE y Pa Ti, "
               "del sector salud frente a la pandemia de COVID-19, y compromisos de "
               "cierre del año fiscal 2020",
     "monto_aprobado": 1_700_000_000, "monto_desembolsado": 1_700_000_000, "moneda": "USD",
     "estado": LoanStatus.ACTIVO,
     "tasa_interes": 6.25,
     "fecha_aprobacion": datetime(2020, 9, 17),
     "fuente": "Presidencia de la República — Comunicado oficial",
     "url_fuente": "https://presidencia.gob.do/noticias/gobierno-logra-historica-emision-de-bonos-soberanos-por-3800-millones-de-dolares"},
    {"acreedor": "Mercado Internacional de Capitales (tenedores de bonos en pesos dominicanos)", "tipo_acreedor": "bono",
     "descripcion": "Colocación histórica de bonos soberanos de septiembre de 2020 — "
                    "tramo de reapertura en pesos dominicanos con vencimiento en 2026, "
                    "RD$17,500 millones (equivalentes a unos US$300 millones), "
                    "rendimiento 10% (tercer tramo de una colocación conjunta de "
                    "US$3,800 millones con demanda total de US$9,600 millones)",
     "objeto": "Financiamiento de los programas sociales Quédate en Casa, FASE y Pa Ti, "
               "del sector salud frente a la pandemia de COVID-19, y compromisos de "
               "cierre del año fiscal 2020",
     "monto_aprobado": 17_500_000_000, "monto_desembolsado": 17_500_000_000, "moneda": "DOP",
     "estado": LoanStatus.ACTIVO,
     "tasa_interes": 10.0,
     "fecha_aprobacion": datetime(2020, 9, 17),
     "fuente": "Presidencia de la República — Comunicado oficial",
     "url_fuente": "https://presidencia.gob.do/noticias/gobierno-logra-historica-emision-de-bonos-soberanos-por-3800-millones-de-dolares"},

    # ── Bonos verdes — primera emisión soberana del país (2024) ──────────────
    # Fuente: Ministerio de Hacienda, comunicado oficial
    {"acreedor": "Mercado Internacional de Capitales (tenedores de bonos verdes soberanos)", "tipo_acreedor": "bono",
     "descripcion": "Primera emisión de bonos verdes soberanos de la historia del país "
                    "(concluida el 25 de junio de 2024), con demanda seis veces superior "
                    "al monto ofrecido y tasa unas 15 puntos básicos por debajo de "
                    "instrumentos convencionales. Emitida bajo el primer Marco de "
                    "Referencia para Bonos Verdes, Sociales y Sostenibles, verificado por "
                    "Standard & Poor's, dentro de la estrategia de deuda 2024-2028",
     "objeto": "Financiamiento de proyectos orientados en su totalidad a sostenibilidad "
               "ambiental: transporte bajo en carbono, energías renovables y "
               "conservación de recursos naturales",
     "monto_aprobado": 750_000_000, "monto_desembolsado": 750_000_000, "moneda": "USD",
     "estado": LoanStatus.ACTIVO,
     "tasa_interes": 6.70,
     "fecha_aprobacion": datetime(2024, 6, 25),
     "fuente": "Ministerio de Hacienda — Comunicado oficial",
     "url_fuente": "https://www.hacienda.gob.do/gobierno-dominicano-concluye-con-exito-su-primera-emision-de-bonos-verdes/"},

    # ── Bonos soberanos — emisión internacional de octubre 2025 ──────────────
    # Fuente: Presidencia de la República, comunicado oficial
    {"acreedor": "Mercado Internacional de Capitales (tenedores de bonos soberanos)", "tipo_acreedor": "bono",
     "descripcion": "Emisión internacional a 10 años (23 de octubre de 2025) que cerró "
                    "por completo las necesidades de financiamiento externo del "
                    "ejercicio fiscal 2025 — demanda de más de US$5,000 millones "
                    "(sobresuscripción de 3.1 veces); anunciada por el ministro de "
                    "Hacienda y Economía, Magín Díaz, y la viceministra de Crédito "
                    "Público, María José Martínez. El riesgo país (índice EMBI de J.P. "
                    "Morgan) se ubicó en torno a 200 puntos básicos, un mínimo histórico",
     "objeto": "Financiamiento conforme a la Ley de Presupuesto 2025: proyectos de "
               "infraestructura en transporte, energía, agua, salud y educación",
     "monto_aprobado": 1_600_000_000, "monto_desembolsado": 1_600_000_000, "moneda": "USD",
     "estado": LoanStatus.ACTIVO,
     "tasa_interes": 5.875, "plazo_anos": 10,
     "fecha_aprobacion": datetime(2025, 10, 23),
     "fuente": "Presidencia de la República — Comunicado oficial",
     "url_fuente": "https://presidencia.gob.do/noticias/la-republica-dominicana-concreta-emision-internacional-por-usd-1600-millones-10-anos"},
]


class CreditoPublicoScraper:

    def __init__(self):
        self.db = SessionLocal()

    async def run(self):
        logger.info("Iniciando scraper Crédito Público...")
        seeded = await self._seed_known_loans()
        scraped = await self._scrape_portal()
        self.db.close()
        logger.info(f"Crédito Público: {seeded} seeded, {scraped} scrapeados")
        return seeded + scraped

    async def _seed_known_loans(self) -> int:
        count = 0
        for i, loan_data in enumerate(KNOWN_LOANS):
            codigo = f"CP-{loan_data['tipo_acreedor'].upper()[:3]}-{i+1:04d}"
            existing = self.db.query(Loan).filter(Loan.codigo == codigo).first()
            if not existing:
                data = {"fuente": "Crédito Público RD", **loan_data}
                loan = Loan(codigo=codigo, **data)
                self.db.add(loan)
                count += 1
        self.db.commit()
        return count

    async def _scrape_portal(self) -> int:
        """Intenta scraping del portal oficial."""
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True,
                                          headers={"User-Agent": settings.USER_AGENT}) as client:
                resp = await client.get(f"{settings.CREDITO_PUBLICO_URL}/prestamos")
                if resp.status_code != 200:
                    return 0
                soup = BeautifulSoup(resp.text, "lxml")
                # Buscar tablas de préstamos
                tables = soup.find_all("table")
                if not tables:
                    return 0
                count = 0
                for table in tables:
                    rows = table.find_all("tr")[1:]
                    for row in rows:
                        cells = [td.get_text(strip=True) for td in row.find_all("td")]
                        if len(cells) >= 3:
                            await self._process_scraped_row(cells)
                            count += 1
                self.db.commit()
                return count
        except Exception as e:
            logger.warning(f"Portal scraping falló: {e}")
            return 0

    async def _process_scraped_row(self, cells: list):
        pass  # Implementar según estructura real del portal


async def run_credito_publico_scraper():
    scraper = CreditoPublicoScraper()
    return await scraper.run()
