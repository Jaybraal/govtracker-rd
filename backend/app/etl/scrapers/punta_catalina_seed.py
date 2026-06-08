"""
Caso Punta Catalina — Seed de datos reales documentados oficialmente.
Central Termoeléctrica Punta Catalina (CTPC) — el proyecto de infraestructura
más grande de la historia dominicana moderna (752 MW nominales, carbón mineral,
Baní, Peravia).

FUENTES (100% oficiales — CERO periodistas/medios de noticias citados):

1. Cámara de Cuentas de la República Dominicana (CCRD): "Informe de
   Investigación Especial al Proyecto Central Termoeléctrica Punta Catalina
   (CTPC) de la Corporación Dominicana de Empresas Eléctricas Estatales
   (CDEEE)", período auditado 1-ene-2013 al 31-dic-2017, firmado el
   19-sep-2018 en Santo Domingo por Ledy A. Paulino, C.P.A. (Supervisora de
   Equipos de Auditoría). Ordenado mediante Decisiones DEC-2017-429
   (28-nov-2017) y DEC-2018-045 (23-ene-2018), Oficios de la Presidencia
   OP No.017840/2017 (19-dic-2017) y No.003800/2018 (9-mar-2018), a solicitud
   del Lic. Rubén Jiménez Bichara (CIE 001-1320324-4), Vicepresidente
   Ejecutivo CDEEE.
   URL: https://camaradecuentas.gob.do/phocadownload/seccion_de_Auditorias/Auditorias_realizadas/Auditorias_e_Investigaciones_Especiales/Punta_Catalina/Informe%20Especial%20Punta%20Catalina%202013-2017.pdf
   (PDF escaneado sin capa de texto — contenido extraído mediante OCR con
   tesseract/pytesseract sobre el documento oficial descargado de
   camaradecuentas.gob.do)

2. Gaceta Oficial No. 10763 (11-jul-2014): contiene la Resolución 219-14 que
   aprueba el Contrato No. 101-14 (firmado 14-abr-2014) — contrato EPC
   "llave en mano", conocido y aprobado por el Congreso Nacional.
   Fuente: creditopublico.gob.do / Cámara de Cuentas (citado textualmente en
   el informe oficial, sección "Objetivos del Proyecto").

3. Decretos de declaratoria de emergencia nacional aplicables al proyecto
   (citados en el Anexo 1 del informe oficial de la CCRD): 894-09
   (10-dic-2009), 143-11 (G.O. 10610, 17-mar-2011), 167-13 (G.O. 10717,
   25-jun-2013, deroga 894-09/358-10/143-11), 197-13 (G.O. 10719,
   16-jul-2013), 307-14 (G.O. 10772, 29-ago-2014), 324-17 (G.O. 10894,
   5-sep-2017).

4. Comisión Nacional de Energía (CNE) — comunicado oficial del 14-sep-2023:
   "CNE conoce funcionamiento operativo de la Central Termoeléctrica Punta
   Catalina" (visita encabezada por el Director Ejecutivo Edward Veras).
   Confirma operación activa: 720 MW combinados, hasta 30% de la demanda
   eléctrica nacional.
   URL: https://cne.gob.do/noticia/cne-conoce-funcionamiento-operativo-de-la-central-termoelectrica-punta-catalina/

────────────────────────────────────────────────────────────────────────────
CORRECCIÓN APLICADA EN ESTA SESIÓN (2026-06-07) — "omitir en vez de inventar":

La versión anterior de este archivo citaba en su docstring "Reportes de
prensa investigativa (Diario Libre, El Dinero, Noticias SIN)" — PROHIBIDO
por instrucción expresa del usuario ("no quiero nada de pereodistas...
son manipulables") — y contenía datos COMPLETAMENTE FABRICADOS que NO
existen en ningún registro oficial verificable:
  • Empresas inexistentes: "CAMC Engineering Co." (RNC 131089456, repr. legal
    "LIANG YAOZU"), "ODM Engineering S.R.L." (RNC 131045678, repr. legal
    "VÍCTOR DÍAZ RÚA", cédula 001-0134567-8), "China Gezhouba Group Corp."
  • Préstamo inexistente: "China Eximbank US$1,940M @ 2.0%, Resolución 05-2015"
    — no aparece en ningún registro de Crédito Público ni del Congreso
    Nacional (se buscó expresamente y no existe tal resolución/contrato).
  • Auditoría con código/período/conclusión FALSOS: "CC-AE-2021-018",
    "período 2014-2021", "fecha_publicacion 2021-11-30", "5 hallazgos por
    USD$160M" — el informe oficial real cubre 2013-2017, fue firmado el
    19-sep-2018, y su conclusión textual es: "no se determinaron hallazgos
    importantes que comunicar" (auditoría LIMPIA, sin observaciones).

La realidad documentada oficialmente es radicalmente distinta: el
contratista EPC real fue el "Consorcio Odebrecht-Tecnimont-Estrella"
(RNC 131-10756-7, Contrato No. 101-14 / Resolución 219-14), financiado
mediante banca alemana (Deutsche Bank) con garantía de seguro de crédito a
la exportación SACE (Italia) — NO mediante "China Eximbank". Se eliminaron
por completo las empresas/préstamo/auditoría fabricados y se reconstruyó el
caso desde cero usando ÚNICAMENTE cifras, nombres, fechas y conclusiones que
constan literalmente en el informe oficial de la Cámara de Cuentas (extraído
vía OCR) y en la Gaceta Oficial / comunicado de la CNE. Cualquier dato que
el informe oficial NO especifica (p. ej. monto principal del préstamo
Deutsche Bank, tasa de interés, número de proceso de licitación, nombres de
firmantes del Contrato 101-14) se OMITE expresamente (NULL) en lugar de
inventarse.
"""
import asyncio
from datetime import datetime
from loguru import logger
from sqlalchemy import insert, select
from ...core.database import SessionLocal
from ...models.company import Company
from ...models.institution import Institution, InstitutionType
from ...models.contract import Contract, ModalidadCompra, ContractStatus
from ...models.loan import Loan, LoanStatus, prestamos_instituciones
from ...models.project import Project, ProjectStatus
from ...models.audit import Audit


_FUENTE_CC = (
    "Cámara de Cuentas de la República Dominicana — Informe de Investigación "
    "Especial al Proyecto Central Termoeléctrica Punta Catalina (CTPC) de la "
    "CDEEE, período 2013-2017, firmado 19-sep-2018 (OP No.017840/2017 / "
    "Decisiones DEC-2017-429 y DEC-2018-045) — extraído vía OCR del PDF oficial"
)
_URL_CC = (
    "https://camaradecuentas.gob.do/phocadownload/seccion_de_Auditorias/"
    "Auditorias_realizadas/Auditorias_e_Investigaciones_Especiales/Punta_Catalina/"
    "Informe%20Especial%20Punta%20Catalina%202013-2017.pdf"
)
_FUENTE_GACETA = (
    "Gaceta Oficial No. 10763 (11-jul-2014) — Resolución 219-14 que aprueba "
    "el Contrato No. 101-14 (EPC, firmado 14-abr-2014), citada textualmente "
    "en el informe oficial de la Cámara de Cuentas"
)
_URL_CNE = (
    "https://cne.gob.do/noticia/cne-conoce-funcionamiento-operativo-de-la-"
    "central-termoelectrica-punta-catalina/"
)
_FUENTE_PROYECTO = _FUENTE_CC + " | Comisión Nacional de Energía (comunicado 14-sep-2023): " + _URL_CNE


async def seed_punta_catalina():
    db = SessionLocal()
    logger.info("Sembrando caso Punta Catalina (datos oficiales verificados, sin periodistas)...")

    # ─── INSTITUCIÓN: CDEEE (real) ───────────────────────────────────────────
    cdeee = db.query(Institution).filter(Institution.siglas == "CDEEE").first()
    if not cdeee:
        cdeee = Institution(
            codigo="CDEEE-01",
            nombre="Corporación Dominicana de Empresas Eléctricas Estatales",
            siglas="CDEEE",
            tipo=InstitutionType.EMPRESA_PUBLICA,
            descripcion=(
                "Ente rector del sector eléctrico estatal dominicano. Líder y "
                "coordinador del Proyecto Central Termoeléctrica Punta Catalina "
                "(CTPC) conforme al Art. 138 de la Ley 125-01 (17-jun-2001) y "
                "Decreto 923-09 (30-dic-2009), a través de su Vicepresidencia "
                "Ejecutiva y la Unidad Ejecutora de Proyectos de Generación (UEPG)."
            ),
            sitio_web="https://www.cdeee.gob.do",
        )
        db.add(cdeee)
        db.flush()
        logger.info("  ✓ Institución CDEEE creada")

    # ─── EMPRESA: CONSORCIO ODEBRECHT-TECNIMONT-ESTRELLA (contratista EPC real) ──
    # RNC No. 131-10756-7 — consta literalmente en el informe oficial de la CCRD
    # (nota 1.6: "...Corporación...al Consorcio Odebrecht-Tecnimont-Estrella,
    # RNC No. 131-10756-7, por concepto de avance o anticipo al Contrato EPC 101/14").
    consorcio = db.query(Company).filter(Company.rnc == "131107567").first()
    if not consorcio:
        consorcio = Company(
            rnc="131107567",
            nombre="Consorcio Odebrecht-Tecnimont-Estrella",
            nombre_comercial="Consorcio Odebrecht-Tecnimont-Estrella",
            tipo_empresa="Consorcio (unión temporal de empresas)",
            sector="Construcción / Energía",
        )
        db.add(consorcio)
        db.flush()
        logger.info("  ✓ Empresa real creada: Consorcio Odebrecht-Tecnimont-Estrella (RNC 131-10756-7)")

    # ─── PRÉSTAMO: FINANCIAMIENTO DEUTSCHE BANK CON GARANTÍA SACE (real) ─────
    # NOTA: usamos insert() de Core (no el constructor ORM) para que los `None`
    # explícitos se guarden como NULL real y no como el `default=` de la columna
    # (ver hallazgo documentado en sib_scraper.py — ej. monto_desembolsado
    # tiene default=0; un None vía constructor ORM se habría guardado como 0,
    # lo cual sería FALSO: sí hubo desembolsos — solo que el informe oficial no
    # especifica el monto total exacto).
    prestamo = db.query(Loan).filter(Loan.codigo == "LOAN-DEUTSCHE-CTPC-2014").first()
    if not prestamo:
        result = db.execute(insert(Loan).values(
            codigo="LOAN-DEUTSCHE-CTPC-2014",
            acreedor=(
                "Deutsche Bank (financiamiento bancario con garantía de seguro "
                "de crédito a la exportación SACE — Servizi Assicurativi del "
                "Commercio Estero, agencia de crédito a la exportación de Italia)"
            ),
            tipo_acreedor="banca_comercial_con_garantia_eca",
            descripcion=(
                "Financiamiento externo de la construcción de la CTPC suscrito "
                "con el Deutsche Bank — documentado oficialmente en el informe "
                "de la Cámara de Cuentas (nota 1.3 y partida contable 'Intereses "
                "s/préstamo bancario'). Cifras OFICIALES verificadas, acumuladas "
                "al 31-dic-2017: prima del seguro de crédito SACE = "
                "US$82,500,000 (de los cuales el Ministerio de Hacienda pagó "
                "el 15% = US$12,375,000 mediante la partida 'Aporte pago Prima "
                "SACE'); intereses pagados sobre el préstamo bancario 2013-2017 "
                "= US$66,864,370 (RD$3,067,217,220 según registro contable de "
                "la cuenta Construcción en Proceso No. 107000551). El informe "
                "oficial NO detalla el monto principal aprobado, tasa de interés, "
                "plazo, período de gracia ni fecha de aprobación de este "
                "financiamiento — esos campos se OMITEN (NULL) por no constar "
                "en ninguna fuente oficial verificable (no se inventan)."
            ),
            objeto="Financiamiento construcción Central Termoeléctrica Punta Catalina (752 MW, Baní, Peravia)",
            estado=LoanStatus.ACTIVO,
            monto_aprobado=None,
            monto_desembolsado=None,
            moneda="USD",
            tasa_interes=None,
            plazo_anos=None,
            periodo_gracia_anos=None,
            fecha_aprobacion=None,
            fecha_primer_desembolso=None,
            fecha_vencimiento=None,
            resolucion_congreso=None,
            fecha_resolucion=None,
            fuente=_FUENTE_CC,
            url_fuente=_URL_CC,
        ))
        prestamo_id = result.inserted_primary_key[0]
        prestamo = db.get(Loan, prestamo_id)
        logger.info("  ✓ Préstamo real creado: Deutsche Bank + garantía SACE (cifras oficiales de la CCRD, NO 'China Eximbank')")

    # ─── PROYECTO: CTPC (real) ───────────────────────────────────────────────
    proyecto = db.query(Project).filter(Project.codigo == "CTPC-2014").first()
    if not proyecto:
        result = db.execute(insert(Project).values(
            codigo="CTPC-2014",
            loan_id=prestamo.id,
            nombre="Central Termoeléctrica Punta Catalina (CTPC)",
            descripcion=(
                "Central de generación eléctrica a base de carbón mineral, de "
                "752 MW de potencia nominal total (2 unidades de 376 MW c/u), "
                "más obras conexas (puerto para recepción de carbón, subestación "
                "138/345kV, líneas de transmisión a 138kV y 345kV, depósito de "
                "cenizas). Contabilizada por CDEEE en la cuenta 'Construcción en "
                "Proceso No. 107000551', con balance acumulado de "
                "RD$95,813,033,797 entre 2013 y el 31-dic-2017 (de los cuales "
                "RD$78,062,496,273 correspondieron a facturas del Consorcio "
                "Odebrecht-Tecnimont-Estrella). El precio total del proyecto fue "
                "ratificado en US$1,945,000,000 mediante el Acuerdo Marco del "
                "18-jun-2018 entre CDEEE y el Consorcio (que también creó un "
                "Fondo Contingente de US$336,000,000 para garantizar la "
                "continuidad de la obra durante el proceso de arbitraje "
                "internacional iniciado por el Consorcio, quien reclamó "
                "US$708,000,000). Operación confirmada activa por la Comisión "
                "Nacional de Energía (CNE) en visita oficial del 14-sep-2023: "
                "720 MW combinados, hasta 30% de la demanda eléctrica nacional."
            ),
            sector="Energía / Generación eléctrica",
            estado=ProjectStatus.COMPLETADO,
            provincia="Peravia",
            municipio="Baní",
            latitud=18.2746,
            longitud=-70.3326,
            monto_total=1_945_000_000,
            monto_ejecutado=None,   # NULL: el informe oficial reporta el balance acumulado en RD$
                                    # (RD$95,813,033,797 al 31-dic-2017), no en USD comparable a monto_total;
                                    # mezclar monedas sin tasa de cambio oficial documentada sería inventar.
            porcentaje_avance=100.0,
            retraso_dias=None,
            fecha_inicio_planificado=datetime(2014, 4, 14),   # fecha de firma del Contrato 101-14 (EPC)
            fecha_fin_planificado=datetime(2019, 2, 28),       # cronograma del Acuerdo Marco 18-jun-2018:
                                                                # Unidad 1 sincroniza dic-2018, Unidad 2 feb-2019
            fecha_inicio_real=None,
            fecha_fin_real=None,    # el informe oficial no certifica fecha exacta de puesta en marcha comercial;
                                    # se omite en vez de inventar (la operación activa SÍ está confirmada por CNE 2023)
            fuente=_FUENTE_PROYECTO,
            url_fuente=_URL_CC,
        ))
        proyecto_id = result.inserted_primary_key[0]
        proyecto = db.get(Project, proyecto_id)
        logger.info("  ✓ Proyecto CTPC creado con datos oficiales verificados (CCRD + CNE)")

    # ─── CONTRATO EPC PRINCIPAL: CONTRATO No. 101-14 (real) ──────────────────
    contrato = db.query(Contract).filter(Contract.numero_contrato == "101-14").first()
    if not contrato:
        result = db.execute(insert(Contract).values(
            numero_contrato="101-14",
            numero_proceso=None,   # el informe oficial no cita un número de proceso de licitación específico
            institution_id=cdeee.id,
            company_id=consorcio.id,
            project_id=proyecto.id,
            loan_id=prestamo.id,
            descripcion=(
                "Contrato EPC (Ejecución de Ingeniería, Procura y Construcción) "
                "tipo 'llave en mano', para diseño, suministro, construcción, "
                "pruebas y puesta en marcha de la Central Termoeléctrica Punta "
                "Catalina (752 MW, 2 unidades de 376 MW a carbón mineral). "
                "Conocido y aprobado por el Congreso Nacional mediante la "
                "Resolución 219-14 (Gaceta Oficial No. 10763, 11-jul-2014)."
            ),
            objeto="Construcción llave en mano (EPC) de la Central Termoeléctrica Punta Catalina",
            modalidad=ModalidadCompra.LICITACION_PUBLICA,
            estado=ContractStatus.COMPLETADO,
            monto_original=1_945_000_000,
            monto_actual=1_945_000_000,
            monto_pagado=None,   # el informe oficial documenta pagos parciales en RD$ (facturas del
                                 # Consorcio: RD$78,062,496,273 acumulado a 2017) sin tasa de cambio
                                 # oficial para convertir a USD — se omite en vez de inventar una tasa
            moneda="USD",
            fecha_firma=datetime(2014, 4, 14),
            fecha_inicio=None,
            fecha_fin_planificada=datetime(2019, 2, 28),
            fecha_fin_real=None,
            oficial_firmante=None,    # el informe oficial no identifica quién firmó el Contrato 101-14 por CDEEE
            oficial_aprobador=None,
            tiene_adendas=False,
            num_adendas=0,
            incremento_porcentual=0,
            retraso_dias=None,
            financiado_prestamo=True,
            es_mayor_100m=True,
            fuente=_FUENTE_GACETA + " | " + _FUENTE_CC,
            url_fuente=_URL_CC,
            raw_data={
                "contrato_numero": "101-14",
                "fecha_firma": "2014-04-14",
                "aprobacion_congreso": "Resolución 219-14, Gaceta Oficial No. 10763 (11-jul-2014)",
                "rnc_consorcio": "131-10756-7",
                "acuerdo_marco_2018": {
                    "fecha": "2018-06-18",
                    "precio_proyecto_ratificado_usd": 1_945_000_000,
                    "fondo_contingente_usd": 336_000_000,
                    "fondo_contingente_desglose": {
                        "anticipo_no_amortizado_usd": 136_000_000,
                        "a_desembolsar_via_cuenta_dedicada_usd": 200_000_000,
                    },
                    "penalidad_por_dia_atraso_usd": 220_000,
                    "reclamo_arbitraje_consorcio_usd": 708_000_000,
                    "firma_legal_defensa_cdeee": "Foley Hoag LLP",
                    "fuente": "Cámara de Cuentas — cap. IV Hechos Subsecuentes "
                              "(comunicación CDEEE-IN-2018-011329, 19-sep-2018, "
                              "Dr. Jaime Aristy Escuder, Administrador General CTPC)",
                },
                "cronograma_acuerdo_marco": {
                    "unidad_1_sincronizacion_planificada": "diciembre 2018",
                    "unidad_2_sincronizacion_planificada": "febrero 2019",
                },
                "ejecucion_segun_informe_oficial_ago_2018_pct": 95,
                "cuenta_contable_cdeee": "Construcción en Proceso No. 107000551",
                "balance_acumulado_2013_2017_rd": 95_813_033_797,
                "monto_revisado_por_ccrd_rd": 95_704_919_684,
                "facturas_consorcio_acumuladas_2013_2017_rd": 78_062_496_273,
                "anticipo_pagado_consorcio_rd": 6_445_540_000,
            },
        ))
        contrato_id = result.inserted_primary_key[0]
        logger.info("  ✓ Contrato real creado: EPC No. 101-14 (Consorcio Odebrecht-Tecnimont-Estrella)")

    # ─── AUDITORÍA: INVESTIGACIÓN ESPECIAL CÁMARA DE CUENTAS (real) ──────────
    auditoria = db.query(Audit).filter(Audit.titulo.ilike("%Punta Catalina%")).first()
    if not auditoria:
        auditoria = Audit(
            institution_id=cdeee.id,
            codigo="OP-017840-2017",
            titulo=(
                "Informe de Investigación Especial al Proyecto Central "
                "Termoeléctrica Punta Catalina (CTPC) de la Corporación "
                "Dominicana de Empresas Eléctricas Estatales (CDEEE)"
            ),
            tipo="Investigación Especial",
            organismo_auditor="Cámara de Cuentas de la República Dominicana",
            periodo_auditado="2013-2017",
            fecha_publicacion=datetime(2018, 9, 19),
            resumen=(
                "Investigación Especial ordenada mediante Decisión DEC-2017-429 "
                "(28-nov-2017, ampliada por DEC-2018-045 del 23-ene-2018) a "
                "solicitud del Lic. Rubén Jiménez Bichara (CIE 001-1320324-4, "
                "Vicepresidente Ejecutivo CDEEE), sobre la cuenta contable "
                "'Construcción en Proceso No. 107000551' del Proyecto CTPC "
                "(balance acumulado 2013-2017: RD$95,813,033,797; la CCRD "
                "examinó RD$95,704,919,684 — 99.89% del total). "
                "CONCLUSIÓN OFICIAL TEXTUAL (Cap. III, Descripción de los "
                "Hechos): 'no se determinaron hallazgos importantes que "
                "comunicar'. Cap. V Conclusión: el saldo de la cuenta "
                "correspondiente al Proyecto CTPC 'se presenta de manera "
                "razonable, conforme a las Normas de Auditoría y las Guías "
                "Profesionales de Auditoría emitidas por la CCRD'. Es decir: "
                "AUDITORÍA LIMPIA, sin observaciones ni hallazgos. Firmado el "
                "19-sep-2018 en Santo Domingo, D.N., por Ledy A. Paulino, "
                "C.P.A., Supervisora de Equipos de Auditoría."
            ),
            hallazgos=[],
            monto_observado=0,
            monto_recuperado=0,
            num_hallazgos=0,
            num_hallazgos_criticos=0,
            url_informe=_URL_CC,
        )
        db.add(auditoria)
        logger.info("  ✓ Auditoría real creada: Investigación Especial CCRD 2013-2017 (CONCLUSIÓN REAL: sin hallazgos — auditoría limpia)")

    # ─── Vincular préstamo ↔ institución CDEEE ───────────────────────────────
    exists = db.execute(
        select(prestamos_instituciones).where(
            prestamos_instituciones.c.prestamo_id == prestamo.id,
            prestamos_instituciones.c.institucion_id == cdeee.id,
        )
    ).first()
    if not exists:
        db.execute(prestamos_instituciones.insert().values(
            prestamo_id=prestamo.id, institucion_id=cdeee.id
        ))

    db.commit()
    db.close()
    logger.info("✅ Caso Punta Catalina sembrado con datos 100%% oficiales verificados (CCRD + Gaceta Oficial + CNE)")
    return {
        "instituciones": ["CDEEE"],
        "empresas": ["Consorcio Odebrecht-Tecnimont-Estrella (RNC 131-10756-7 — real, verificado en informe oficial CCRD)"],
        "prestamo": "Deutsche Bank + garantía SACE (cifras oficiales verificadas; se eliminó el 'China Eximbank' fabricado)",
        "contratos": 1,
        "auditoria": "Investigación Especial CCRD 2013-2017 — conclusión real: SIN HALLAZGOS (auditoría limpia, no '5 hallazgos por USD$160M' como decía la versión anterior)",
    }


if __name__ == "__main__":
    asyncio.run(seed_punta_catalina())
