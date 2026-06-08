"""
Sector Combustibles / Derivados del Petróleo — República Dominicana.
Fuentes: Portal de Transparencia del MICM (micm.gob.do), Portal Transaccional
de la Dirección General de Contrataciones Públicas (DGCP).

Este scraper solo siembra casos con expediente público verificable
(número de proceso, fechas, montos y documentos oficiales). No se incluyen
empresas ni personas sin un contrato o hallazgo documentado y enlazable.
"""
import asyncio
from datetime import datetime
from loguru import logger
from ...core.database import SessionLocal
from ...models.company import Company, LegalRepresentative
from ...models.institution import Institution, InstitutionType
from ...models.contract import Contract, ModalidadCompra, ContractStatus


# ─────────────────────────────────────────────────────────────────────────────
# EMPRESAS DEL SECTOR COMBUSTIBLES — solo casos con contrato público verificable
# ─────────────────────────────────────────────────────────────────────────────
EMPRESAS_COMBUSTIBLES = [
    {
        # RNC no localizado en el padrón público de la DGII al momento de la siembra;
        # se deja sin valor para no inventar un número. Deduplicación por nombre.
        "rnc": None,
        "nombre": "V Energy, S.A. (anteriormente Sunix Petroleum, S.R.L.)",
        "nombre_comercial": "V Energy",
        "tipo_empresa": "Sociedad Anónima",
        "sector": "Combustibles / Distribución y suministro",
        "nota": "Sunix Petroleum, S.R.L. ganó la Licitación Pública Nacional "
                "MICM-CCC-LPN-2022-0004 para suministrar combustible (gasolina y "
                "gasoil) al Ministerio de Industria, Comercio y Mipymes (MICM). "
                "En diciembre de 2022, mientras el contrato estaba vigente, Sunix "
                "Petroleum fue absorbida mediante fusión por V Energy, S.A., que "
                "asumió sus obligaciones contractuales mediante una adenda — un caso "
                "real, documentado en el portal de transparencia del MICM, que ilustra "
                "cómo la identidad jurídica de un contratista del Estado puede cambiar "
                "a mitad de la ejecución sin necesidad de abrir un nuevo proceso "
                "competitivo, lo que dificulta el seguimiento público del contrato.",
        "contratos_conocidos": [
            {
                "numero": "MICM-CCC-LPN-2022-0004",
                "desc": "Contratación de servicios para la adquisición de combustible "
                        "(gasolina y gasoil) para uso del Ministerio de Industria, "
                        "Comercio y Mipymes (MICM). Proceso de Licitación Pública "
                        "Nacional convocado el 31/05/2022 a través del Portal "
                        "Transaccional de la DGCP; apertura de ofertas técnicas el "
                        "21/07/2022; contrato firmado el 12/08/2022 con Sunix "
                        "Petroleum, S.R.L. por RD$12,300,000. En diciembre de 2022, "
                        "tras la fusión por absorción de Sunix Petroleum por V Energy, "
                        "S.A., se emitió una adenda que transfirió la titularidad del "
                        "contrato a V Energy, S.A. en los mismos términos originales.",
                "monto_dop": 12_300_000,
                "anio": 2022,
                "fecha_firma": datetime(2022, 8, 12),
                "modalidad": ModalidadCompra.LICITACION_PUBLICA,
                "estado": ContractStatus.COMPLETADO,
                "adendas": 1,
                "fuente": "Portal de Transparencia MICM — expediente MICM-CCC-LPN-2022-0004",
                "url_fuente": "https://www.micm.gob.do/transparencia/compras-y-contrataciones-publicas/"
                              "category/micm-ccc-lpn-2022-0004-contratacion-de-servicios-para-la-adquisicion-"
                              "de-combustible-gasolina-y-gasoil-para-uso-de-este-ministerio-de-industria-"
                              "comercio-y-mipymes-micm",
                "raw_data": {
                    "convocatoria": "2022-05-31",
                    "apertura_oferta_tecnica": "2022-07-21",
                    "firma_contrato": "2022-08-12",
                    "contratista_original": "Sunix Petroleum, S.R.L.",
                    "evento": "Fusión por absorción — diciembre de 2022",
                    "contratista_sucesor": "V Energy, S.A.",
                    "instrumento_traspaso": "Adenda I al contrato MICM-CCC-LPN-2022-0004",
                },
            },
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# INSTITUCIONES DEL SECTOR QUE COMPRAN COMBUSTIBLE
# ─────────────────────────────────────────────────────────────────────────────
INSTITUCIONES_CONSUMIDORAS = [
    ("MICM",  "Ministerio de Industria, Comercio y Mipymes", InstitutionType.MINISTERIO),
    ("MFFAA", "Ministerio de las Fuerzas Armadas", InstitutionType.MINISTERIO),
    ("PN",    "Policía Nacional", InstitutionType.ORGANISMO_AUTONOMO),
    ("OMSA",  "Oficina Metropolitana de Servicios de Autobuses", InstitutionType.ORGANISMO_AUTONOMO),
    ("CNE",   "Comisión Nacional de Energía", InstitutionType.ORGANISMO_AUTONOMO),
    ("AERODOM", "Aeropuertos Dominicanos Siglo XXI", InstitutionType.EMPRESA_PUBLICA),
]


class CombustiblesScraper:

    def __init__(self):
        self.db = SessionLocal()

    async def run(self) -> int:
        logger.info("Iniciando scraper Combustibles (datos reales verificables)...")
        count = await self._seed_instituciones()
        count += await self._seed_empresas_y_contratos()
        self.db.close()
        logger.info(f"Combustibles: {count} registros creados")
        return count

    async def _seed_instituciones(self) -> int:
        count = 0
        for siglas, nombre, tipo in INSTITUCIONES_CONSUMIDORAS:
            if not self.db.query(Institution).filter(Institution.siglas == siglas).first():
                self.db.add(Institution(
                    codigo=f"INST-{siglas}",
                    nombre=nombre, siglas=siglas, tipo=tipo,
                ))
                count += 1
        self.db.commit()
        return count

    def _find_or_create_company(self, emp_data: dict) -> tuple:
        """Busca por RNC si existe; si no, deduplica por nombre (evita inventar RNC)."""
        if emp_data.get("rnc"):
            comp = self.db.query(Company).filter(Company.rnc == emp_data["rnc"]).first()
        else:
            comp = self.db.query(Company).filter(Company.nombre == emp_data["nombre"]).first()
        created = False
        if not comp:
            comp = Company(
                rnc=emp_data.get("rnc"),
                nombre=emp_data["nombre"],
                nombre_comercial=emp_data.get("nombre_comercial"),
                tipo_empresa=emp_data.get("tipo_empresa"),
                sector=emp_data.get("sector"),
            )
            self.db.add(comp)
            self.db.flush()
            created = True
        return comp, created

    async def _seed_empresas_y_contratos(self) -> int:
        count = 0
        for emp_data in EMPRESAS_COMBUSTIBLES:
            comp, created = self._find_or_create_company(emp_data)
            if created:
                count += 1

            for rep in emp_data.get("representantes", []):
                exists = self.db.query(LegalRepresentative).filter(
                    LegalRepresentative.company_id == comp.id,
                    LegalRepresentative.nombre == rep["nombre"],
                ).first()
                if not exists:
                    self.db.add(LegalRepresentative(
                        company_id=comp.id,
                        nombre=rep["nombre"],
                        cargo=rep.get("cargo", ""),
                        cedula=rep.get("cedula", ""),
                    ))

            for ct_data in emp_data.get("contratos_conocidos", []):
                inst = self._get_or_create_inst_for_contract(ct_data["desc"])
                numero = ct_data.get("numero") or f"COMB-{comp.id}-{ct_data['anio']}-{count:04d}"
                if inst and not self.db.query(Contract).filter(Contract.numero_contrato == numero).first():
                    monto_dop = ct_data["monto_dop"]
                    adendas = ct_data.get("adendas", 0)
                    c = Contract(
                        numero_contrato=numero,
                        institution_id=inst.id,
                        company_id=comp.id,
                        descripcion=ct_data["desc"],
                        objeto=ct_data["desc"],
                        modalidad=ct_data["modalidad"],
                        estado=ct_data.get("estado", ContractStatus.COMPLETADO),
                        monto_original=monto_dop,
                        monto_actual=monto_dop,
                        monto_pagado=monto_dop,
                        moneda="DOP",
                        fecha_firma=ct_data.get("fecha_firma") or datetime(ct_data["anio"], 1, 1),
                        tiene_adendas=adendas > 0,
                        num_adendas=adendas,
                        incremento_porcentual=0,
                        es_mayor_100m=monto_dop >= 100_000_000,
                        financiado_prestamo=False,
                        fuente=ct_data.get("fuente", "Portal de Transparencia MICM"),
                        url_fuente=ct_data.get("url_fuente"),
                        raw_data=ct_data.get("raw_data"),
                    )
                    self.db.add(c)
                    count += 1

        self.db.commit()
        self._update_stats()
        return count

    def _get_or_create_inst_for_contract(self, desc: str) -> Institution:
        desc_lower = desc.lower()
        mapping = {
            "micm": "MICM", "industria, comercio": "MICM",
            "mopc": "MOPC", "carretera": "MOPC",
            "policía": "PN", "policia": "PN",
            "ejército": "MFFAA", "ejercito": "MFFAA", "armadas": "MFFAA",
            "hospital": "MSP", "msp": "MSP", "salud": "MSP",
            "escuela": "MINERD", "plantel": "MINERD", "minerd": "MINERD",
            "aeropuerto": "AERODOM", "aerodom": "AERODOM",
            "cdeee": "CDEEE", "central": "CDEEE",
        }
        for keyword, siglas in mapping.items():
            if keyword in desc_lower:
                inst = self.db.query(Institution).filter(Institution.siglas == siglas).first()
                if inst:
                    return inst
        return self.db.query(Institution).filter(Institution.siglas == "MICM").first()

    def _update_stats(self):
        from sqlalchemy import func
        companies = self.db.query(Company).all()
        for comp in companies:
            r = self.db.query(
                func.count(Contract.id),
                func.sum(Contract.monto_original),
                func.count(func.distinct(Contract.institution_id)),
            ).filter(Contract.company_id == comp.id).first()
            if r and r[0]:
                comp.total_contratos = r[0]
                comp.total_monto_recibido = r[1] or 0
                comp.total_instituciones = r[2] or 0
        insts = self.db.query(Institution).all()
        for inst in insts:
            r = self.db.query(
                func.count(Contract.id),
                func.sum(Contract.monto_original),
            ).filter(Contract.institution_id == inst.id).first()
            if r and r[0]:
                inst.total_contratos = r[0]
                inst.total_monto_contratos = r[1] or 0
        self.db.commit()


async def run_combustibles_scraper():
    s = CombustiblesScraper()
    return await s.run()
