"""
Parser de PDFs para contratos, auditorías y resoluciones gubernamentales.
"""
import re
import os
from typing import Optional
from pathlib import Path
from loguru import logger


class PDFParser:

    def extract_text(self, filepath: str) -> Optional[str]:
        """Extrae texto de PDF usando pdfplumber (principal) o PyMuPDF (fallback)."""
        try:
            return self._extract_pdfplumber(filepath)
        except Exception as e:
            logger.warning(f"pdfplumber falló: {e}, intentando PyMuPDF")
            try:
                return self._extract_pymupdf(filepath)
            except Exception as e2:
                logger.error(f"PyMuPDF falló: {e2}")
                return None

    def _extract_pdfplumber(self, filepath: str) -> str:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                # También extraer tablas
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            text_parts.append(" | ".join(str(c or "") for c in row))
        return "\n".join(text_parts)

    def _extract_pymupdf(self, filepath: str) -> str:
        import fitz
        doc = fitz.open(filepath)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)

    def extract_contract_data(self, text: str) -> dict:
        """Extrae campos estructurados del texto de un contrato."""
        data = {}

        # Número de contrato
        patterns_numero = [
            r"(?:Contrato|CONTRACT)\s*N[oO°\.]*\s*:?\s*([A-Z0-9\-/]+)",
            r"(?:Número|Numero)\s+de\s+[Cc]ontrato\s*:?\s*([A-Z0-9\-/]+)",
        ]
        for p in patterns_numero:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                data["numero_contrato"] = m.group(1).strip()
                break

        # Monto
        patterns_monto = [
            r"(?:MONTO|Monto|Valor)\s*:?\s*RD\$?\s*([\d,\.]+)",
            r"(?:SUMA|Suma)\s+de\s+RD\$?\s*([\d,\.]+)",
            r"(?:TOTAL|Total)\s*:?\s*RD\$?\s*([\d,\.]+)",
        ]
        for p in patterns_monto:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                try:
                    data["monto"] = float(m.group(1).replace(",", ""))
                except ValueError:
                    pass
                break

        # Fecha
        pattern_fecha = r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})"
        m = re.search(pattern_fecha, text, re.IGNORECASE)
        if m:
            data["fecha_texto"] = m.group(0)

        # RNC proveedor
        m = re.search(r"RNC\s*:?\s*(\d{9,11})", text, re.IGNORECASE)
        if m:
            data["rnc_proveedor"] = m.group(1)

        # Empresa
        patterns_empresa = [
            r"(?:empresa|compañía|sociedad|contratista)\s+([A-Z][A-Z\s,\.]+(?:S\.R\.L\.|S\.A\.|EIRL|C\s*por\s*A))",
        ]
        for p in patterns_empresa:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                data["empresa"] = m.group(1).strip()
                break

        # Objeto del contrato
        m = re.search(r"(?:OBJETO|Objeto)\s*(?:DEL\s+CONTRATO)?\s*:?\s*(.+?)(?:\n|\.)", text, re.IGNORECASE)
        if m:
            data["objeto"] = m.group(1).strip()[:500]

        return data

    def extract_audit_findings(self, text: str) -> list:
        """Extrae hallazgos de auditoría del texto."""
        findings = []
        pattern = r"(?:Hallazgo|HALLAZGO)\s+[N°nNo\.]*\s*(\d+)\s*[:\-]?\s*(.+?)(?=Hallazgo|HALLAZGO|\Z)"
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        for num, desc in matches:
            desc_clean = re.sub(r'\s+', ' ', desc).strip()[:1000]
            monto_m = re.search(r"RD\$?\s*([\d,\.]+)", desc_clean)
            findings.append({
                "numero": num,
                "descripcion": desc_clean,
                "monto": float(monto_m.group(1).replace(",", "")) if monto_m else None,
            })
        return findings


class ExcelParser:

    def parse_contracts_excel(self, filepath: str) -> list:
        """Parsea archivo Excel de contratos (formato DGCP estándar)."""
        import pandas as pd
        df = pd.read_excel(filepath, engine="openpyxl")
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        records = []
        for _, row in df.iterrows():
            record = row.to_dict()
            # Normalizar nombres de columnas comunes
            record = self._normalize_columns(record)
            records.append(record)
        return records

    def parse_budget_csv(self, filepath: str) -> list:
        import pandas as pd
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        return df.to_dict("records")

    def _normalize_columns(self, row: dict) -> dict:
        aliases = {
            "no._de_contrato": "numero_contrato",
            "número_contrato": "numero_contrato",
            "monto_contrato": "monto_original",
            "nombre_proveedor": "empresa_nombre",
            "nombre_institución": "institucion_nombre",
            "fecha_firma": "fecha_contrato",
        }
        return {aliases.get(k, k): v for k, v in row.items()}
