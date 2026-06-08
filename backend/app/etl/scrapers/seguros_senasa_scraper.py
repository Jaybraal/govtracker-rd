"""
Sector Seguros / Salud (SENASA) — República Dominicana.

Siembra el caso "Operación Cobra" (Ministerio Público, diciembre de 2025):
red de corrupción dentro del Seguro Nacional de Salud (SeNaSa) encabezada
por su exdirector ejecutivo, Hazim Albainy (Santiago Hazim).

──────────────────────────────────────────────────────────────────────────────
CORRECCIÓN APLICADA EN ESTA SESIÓN (2026-06-07) — eliminación de citas a prensa
──────────────────────────────────────────────────────────────────────────────
La versión anterior de este archivo citaba como `fuente` una mezcla de
"Ministerio Público (expediente 'caso SENASA') / Listín Diario" —y, en el
docstring, una lista de URLs exclusivamente periodísticas (listindiario.com,
n.com.do, power800am.com)— para sembrar 3 empresas ("Khersum, S.R.L.",
"Deleste, S.R.L.", "Farmacard, S.R.L."), 1 contrato con monto exacto
(RD$3,882,113,916.57 a Khersum, con `monto_pagado` igualado a
`monto_original` sin fuente que confirmara el desembolso real) y 1 registro
de auditoría de la Cámara de Cuentas. Esto viola la regla del usuario: "no
quiero nada de pereodistas oficiales o afines ya que son manipulables, pero
si estan en documentos oficiones escritos no".

Se buscó si el Ministerio Público (pgr.gob.do — sala de prensa oficial) o la
Cámara de Cuentas (camaradecuentas.gob.do) habían publicado ELLOS MISMOS,
en notas de prensa o informes propios, los nombres de esas empresas y esas
cifras exactas:
  - pgr.gob.do SÍ tiene una sala de prensa con comunicados oficiales sobre
    el caso (operación "Cobra", lanzada el 7-dic-2025) que nombran a los
    imputados —incluido Eduardo Read Estrella— y dan cifras agregadas del
    fraude. NINGÚN comunicado oficial del MP menciona "Khersum", "Deleste",
    "Farmacard" ni desglosa montos por empresa: ese nivel de detalle
    (nombres de empresas, monto exacto a Khersum, nombre del intermediario)
    proviene exclusivamente de la investigación periodística de Listín
    Diario sobre el expediente, no de un documento oficial publicado.
  - camaradecuentas.gob.do — el buscador del portal y el listado oficial de
    informes (/index.php/informes) no arrojan ningún resultado para "SENASA"
    ni "PROMESE": no se localizó el informe que supuestamente documentaba
    irregularidades de RD$480 millones en el programa SENASA-PROMESE/CAL
    (esa cifra y su atribución a la Cámara de Cuentas provienen, de nuevo,
    solo de un artículo de n.com.do).

Conclusión: se ELIMINARON las 3 empresas, el contrato con monto calculado y
el registro de auditoría —"omitir en vez de inventar" aplicado en cadena: si
la empresa, el contrato o el informe solo son citables vía un intermediario
periodístico, tampoco son citables aquí. Lo que SÍ queda —reescrito desde
cero, citando ÚNICAMENTE comunicados oficiales de la sala de prensa del
Ministerio Público (pgr.gob.do)— es la descripción del caso "Operación
Cobra": nombres de imputados, cargos imputados y cifras agregadas, todos
verificados palabra por palabra contra el texto de esos comunicados (y, de
hecho, más precisos que la versión anterior: el MP habla de "al menos 15 mil
millones de pesos" defraudados y "más de 2 mil millones" en sobornos, cifras
oficiales mayores a las que circularon en la cobertura de prensa de
RD$12,000 millones / RD$1,621 millones).

Fuentes oficiales (Ministerio Público — Procuraduría General de la
República, sala de prensa, pgr.gob.do):
- https://pgr.gob.do/el-ministerio-publico-pone-en-marcha-la-operacion-cobra-inicia-judicializacion-en-busca-de-sanciones-penales-y-el-decomiso-del-dinero-sustraido-al-patrimonio-publico/  (07-dic-2025, comunicado de lanzamiento — lista completa de imputados, cargos y cifras)
- https://pgr.gob.do/tribunal-ratifica-prision-preventiva-a-santiago-hazim-y-otros-6-procesados-a-partir-de-la-operacion-cobra/
- https://pgr.gob.do/ministerio-publico-asegura-que-hazim-albainy-encabezo-un-entramado-corrupto-para-beneficiarse-del-senasa/
- https://pgr.gob.do/entramado-de-corrupcion-impactado-con-la-operacion-cobra-capto-miles-de-millones-en-sobornos-para-enriquecerse/  (12-dic-2025)
- https://pgr.gob.do/3-imputados-de-la-operacion-cobra-confesaron-en-el-tribunal-que-pagaron-sobornos-a-funcionarios-del-senasa/  (12-dic-2025)
- https://pgr.gob.do/wilson-camacho-todo-el-que-ha-sustraido-dinero-del-senasa-estara-en-el-banquillo-de-los-acusados/

IMPORTANTE: no se incluyen cifras, empresas, cédulas ni nombres que no
aparezcan textualmente en estos comunicados oficiales del Ministerio Público.
"""
import asyncio
from loguru import logger
from ...core.database import SessionLocal
from ...models.company import Company, LegalRepresentative
from ...models.institution import Institution, InstitutionType
from ...models.contract import Contract
from ...models.official import Official


# ─────────────────────────────────────────────────────────────────────────────
# INSTITUCIONES DEL SISTEMA DE SEGURIDAD SOCIAL Y SALUD
# Descripción del caso SENASA reescrita citando solo comunicados oficiales del
# Ministerio Público (pgr.gob.do — ver lista de fuentes en el docstring).
# ─────────────────────────────────────────────────────────────────────────────
_DESC_SENASA = (
    "ARS (Administradora de Riesgos de Salud) estatal: administra el régimen "
    "subsidiado y parte del contributivo-subsidiado del Sistema Dominicano de "
    "Seguridad Social (Ley 87-01), con cobertura sobre más de 7 millones de "
    "afiliados. El 7 de diciembre de 2025 el Ministerio Público puso en marcha "
    "la 'Operación Cobra': 25 fiscales, apoyados por más de 200 agentes de la "
    "Policía Nacional, realizaron 12 allanamientos y arrestaron a 10 personas "
    "señaladas de defraudar al SeNaSa con, según la propia Procuraduría "
    "General, 'al menos 15 mil millones de pesos' y de cobrar sobornos por "
    "'más de 2 mil millones de pesos'. Encabeza el entramado el exdirector "
    "ejecutivo Hazim Albainy (Santiago Hazim); junto a él fueron procesados "
    "Eduardo Read Estrella, Gustavo Enrique Messina Cruz, Germán Rafael Robles "
    "Quiñones, Francisco Iván Minaya Pérez, Cinty Acosta Sención, Heidi "
    "Mariela Pineda Perdomo, Ramón Alan Speakler Mateo, Rafael Luis Martínez "
    "Hazim y Ada Ledesma Ubiera. El Ministerio Público —encabezado por la "
    "procuradora general Yeni Berenice Reynoso— les imputa coalición de "
    "funcionarios, prevaricación, asociación de malhechores, cobro de "
    "soborno, estafa contra el Estado dominicano, desfalco, falsificación, "
    "uso de documentos falsos y lavado de activos, y solicitó que el caso sea "
    "declarado de tramitación compleja. El 12 de diciembre de 2025 el MP "
    "informó que 3 de los imputados confesaron ante el juez Rigoberto Sena "
    "haber pagado sobornos a funcionarios del SeNaSa, incluido Hazim."
)

INSTITUCIONES_SECTOR = [
    ("SENASA",     "Seguro Nacional de Salud", InstitutionType.ORGANISMO_AUTONOMO, _DESC_SENASA),
    ("SISALRIL",   "Superintendencia de Salud y Riesgos Laborales", InstitutionType.ORGANISMO_AUTONOMO,
     "Regulador de las ARS y ARL del Sistema Dominicano de Seguridad Social: "
     "aprueba tarifas, autoriza la operación de aseguradoras de salud y resuelve "
     "reclamos de afiliados."),
    ("CNSS",       "Consejo Nacional de Seguridad Social", InstitutionType.ORGANISMO_AUTONOMO, None),
    ("TSS",        "Tesorería de la Seguridad Social", InstitutionType.ORGANISMO_AUTONOMO, None),
    ("PROMESECAL", "Programa de Medicamentos Esenciales / Central de Apoyo Logístico (PROMESE/CAL)",
     InstitutionType.ORGANISMO_AUTONOMO,
     "Entidad estatal de adquisición y distribución de medicamentos esenciales "
     "del Sistema Nacional de Salud."),
]

# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONARIOS SEÑALADOS — solo el cargo previo (institución verificable);
# el resto de imputados de la Operación Cobra no tenían cargo en SENASA
# documentado en los comunicados del MP, por lo que no se siembran como
# `Official` (evita asociarlos a una institución sin respaldo).
# ─────────────────────────────────────────────────────────────────────────────
OFICIALES_SECTOR = [
    {
        "nombre": "SANTIAGO HAZIM",
        "cargo": "Exdirector ejecutivo de SENASA (nombrado 'Hazim Albainy' en los "
                 "comunicados oficiales del Ministerio Público) — señalado como "
                 "cabecilla del entramado de corrupción desarticulado el 7 de "
                 "diciembre de 2025 mediante la 'Operación Cobra'. Según la "
                 "Procuraduría General de la República, el grupo defraudó al "
                 "SeNaSa y a sus más de 7 millones de afiliados con al menos "
                 "15 mil millones de pesos y cobró sobornos superiores a "
                 "2 mil millones de pesos.",
        "institucion_siglas": "SENASA",
    },
]

TC = 56.5  # Tipo de cambio referencia (no usado: no hay montos en USD en este scraper)


class SegurosSenasaScraper:

    def __init__(self):
        self.db = SessionLocal()

    async def run(self) -> int:
        logger.info("Iniciando scraper Seguros / SENASA (caso Operación Cobra — solo fuentes oficiales MP)...")
        count = await self._seed_instituciones()
        count += await self._seed_oficiales()
        self.db.close()
        logger.info(f"Seguros/SENASA: {count} registros creados")
        return count

    async def _seed_instituciones(self) -> int:
        count = 0
        for siglas, nombre, tipo, descripcion in INSTITUCIONES_SECTOR:
            inst = self.db.query(Institution).filter(Institution.siglas == siglas).first()
            if not inst:
                self.db.add(Institution(
                    codigo=f"INST-{siglas}",
                    nombre=nombre, siglas=siglas, tipo=tipo,
                    descripcion=descripcion,
                ))
                count += 1
            elif descripcion and not inst.descripcion:
                inst.descripcion = descripcion
        self.db.commit()
        return count

    async def _seed_oficiales(self) -> int:
        count = 0
        for of_data in OFICIALES_SECTOR:
            inst = self.db.query(Institution).filter(
                Institution.siglas == of_data["institucion_siglas"]
            ).first()
            exists = self.db.query(Official).filter(Official.nombre == of_data["nombre"]).first()
            if not exists:
                self.db.add(Official(
                    institution_id=inst.id if inst else None,
                    nombre=of_data["nombre"],
                    cargo=of_data["cargo"],
                ))
                count += 1
        self.db.commit()
        return count


async def run_seguros_senasa_scraper():
    s = SegurosSenasaScraper()
    return await s.run()
