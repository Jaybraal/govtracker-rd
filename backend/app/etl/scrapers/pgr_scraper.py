"""
Scraper de comunicados oficiales — Procuraduría General de la República (pgr.gob.do).

Extrae el índice de noticias paginado (9 artículos/página, ~991 páginas al 2026-06)
y el cuerpo completo de cada artículo individual.

Estrategia anti-bloqueo:
  - User-Agent de Chrome real
  - Delay aleatorio entre requests (1-3 s entre artículos, 2-5 s entre páginas)
  - Máx. 3 reintentos por URL con backoff
  - Modo incremental: para cuando encuentra una URL ya almacenada

Base de datos: data/pgr.db (SQLite independiente, NO el govtracker_test.db)
"""

import asyncio
import re
import sqlite3
import time
import unicodedata
from pathlib import Path
from random import uniform
from typing import Optional

import httpx
from loguru import logger

PGR_DB = Path(__file__).parent.parent.parent.parent / "data" / "pgr.db"
BASE_URL = "https://pgr.gob.do"
LIST_URL = f"{BASE_URL}/category/noticias/page/{{page}}/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-DO,es;q=0.9,en;q=0.8",
}

# ─── Palabras clave para clasificación ───────────────────────────────────────
TIPOS = {
    "operacion":   ["operación", "operacion", "allanamiento", "ejecución del plan"],
    "condena":     ["condena", "condena de ", "años de prisión", "sentencia"],
    "acusacion":   ["acusación", "acusacion", "imputado", "imputados", "acusado", "sometido"],
    "aprehension": ["aprehendido", "apresado", "detenido", "arresto", "capturado"],
    "requerimiento": ["requerimiento", "solicitud de prisión", "solicita prisión"],
    "comunicado":  ["ministerio público informa", "comunica", "anuncia"],
}

OPERACIONES_CONOCIDAS = [
    "Operación Cobra", "Caso Antipulpo", "Caso Calamar", "Caso Coral 5G",
    "Caso Medusa", "Caso Pulpo", "Caso Halcón", "Operación Calamar",
    "Operación Coral", "Operación Halcón", "Caso Coral", "Operación Anti-Pulpo",
]


# ─── Utilidades HTML ──────────────────────────────────────────────────────────
def _strip(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&hellip;", "...", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _norm(s: str) -> str:
    """Normaliza a ASCII mayúsculas para comparaciones."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.upper()


# ─── Extracción de metadatos ──────────────────────────────────────────────────
def _extract_title(html: str) -> str:
    m = re.search(r'property="og:title"[^>]*content="([^"]+)"', html)
    if m:
        return _strip(m.group(1))
    m = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    return _strip(m.group(1)).split("|")[0].strip() if m else ""


def _extract_body(html: str) -> str:
    """Extrae el cuerpo del artículo (Elementor post-content)."""
    m = re.search(
        r'class="[^"]*post-content[^"]*"[^>]*>(.*?)</article>', html, re.DOTALL
    )
    if not m:
        m = re.search(
            r'class="elementor[^"]*post-content[^"]*"[^>]*>(.*?)</section>', html, re.DOTALL
        )
    return _strip(m.group(1)) if m else ""


def _extract_date(body: str, html: str) -> Optional[str]:
    """Intenta extraer fecha del cuerpo. Formato devuelto: YYYY-MM-DD."""
    # Patrón: "7 de diciembre de 2025", "12 de enero del 2024"
    MESES = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
    }
    pat = re.search(
        r"(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|octubre|noviembre|diciembre)\s+de[l]?\s+(\d{4})",
        body, re.IGNORECASE,
    )
    if pat:
        d, mes, y = pat.group(1), pat.group(2).lower(), pat.group(3)
        return f"{y}-{MESES[mes]}-{int(d):02d}"
    # Formato: "diciembre 7, 2025" o "diciembre 7 2025"
    pat2 = re.search(
        r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|octubre|noviembre|diciembre)\s+(\d{1,2}),?\s+(\d{4})",
        body, re.IGNORECASE,
    )
    if pat2:
        mes, d, y = pat2.group(1).lower(), pat2.group(2), pat2.group(3)
        return f"{y}-{MESES[mes]}-{int(d):02d}"
    return None


def _classify_tipo(titulo: str, body: str) -> str:
    texto = (titulo + " " + body[:500]).lower()
    for tipo, keywords in TIPOS.items():
        if any(kw in texto for kw in keywords):
            return tipo
    return "general"


_STOP_CASO = {
    "que", "el", "la", "los", "las", "un", "una", "de", "del", "en", "con",
    "por", "para", "fue", "es", "se", "su", "al", "le", "lo", "contra",
    "ante", "como", "este", "esta", "ese", "esa", "cual", "cuando",
}


def _extract_operacion(titulo: str, body: str) -> Optional[str]:
    texto = titulo + " " + body[:1000]
    for op in OPERACIONES_CONOCIDAS:
        if op.lower() in texto.lower():
            return op
    # Patrón: "Operación <Nombre>" — siempre válido si hay una palabra
    m_op = re.search(r"\bOperaci[oó]n\s+([A-ZÁÉÍÓÚÑ\w]+)", texto, re.IGNORECASE)
    if m_op:
        return f"Operación {m_op.group(1).title()}"
    # Patrón: "Caso <Nombre>" — solo si la palabra siguiente es un nombre propio
    # (comienza con mayúscula Y no está en la lista de palabras comunes)
    m_caso = re.search(r"\bCaso\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñA-Z]+)", texto)
    if m_caso:
        nombre = m_caso.group(1)
        if nombre.lower() not in _STOP_CASO and len(nombre) > 3:
            return f"Caso {nombre}"
    return None


def _extract_montos(body: str) -> Optional[str]:
    """Extrae menciones de montos (RD$X millones, X pesos, etc.)."""
    PATRONES = [
        r"RD\$[\d,\.]+\s*(?:millones?|mil millones?|billones?|pesos?)?",
        r"(?:más de\s+)?[\d,\.]+\s*(?:millones?|mil millones?)\s*(?:de\s+pesos)?",
        r"\$[\d,\.]+\s*(?:millones?|mil millones?|USD)?",
    ]
    found = []
    for p in PATRONES:
        found += re.findall(p, body[:2000], re.IGNORECASE)
    if not found:
        return None
    return "; ".join(dict.fromkeys(m.strip() for m in found[:5]))


def _extract_imputados(titulo: str, body: str) -> Optional[str]:
    """Extrae menciones de personas (patrones de nombre en mayúsculas)."""
    texto = titulo + " " + body[:3000]
    # Nombres de 2-4 palabras en mayúsculas (patrón dominicano)
    nombres = re.findall(
        r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+"
        r"(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2})\b",
        texto,
    )
    # Filtrar palabras comunes que no son nombres
    STOP = {
        "Ministerio Público", "República Dominicana", "Santo Domingo", "Procurador General",
        "Ministerio Publico", "Policía Nacional", "Cámara Penal", "Juzgado Penal",
        "Tribunal Colegiado", "Corte Apelación", "Sala Penal", "Sala Constitucional",
    }
    nombres_filtrados = [n for n in dict.fromkeys(nombres) if n not in STOP][:10]
    return "; ".join(nombres_filtrados) if nombres_filtrados else None


# ─── Base de datos ────────────────────────────────────────────────────────────
def _init_db():
    conn = sqlite3.connect(str(PGR_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comunicados (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            url             TEXT UNIQUE NOT NULL,
            slug            TEXT,
            titulo          TEXT,
            cuerpo          TEXT,
            fecha           TEXT,
            tipo            TEXT,
            operacion       TEXT,
            montos          TEXT,
            imputados       TEXT,
            scraped_at      TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tipo   ON comunicados(tipo)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_operacion ON comunicados(operacion)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fecha  ON comunicados(fecha)")
    conn.commit()
    return conn


def _url_exists(conn: sqlite3.Connection, url: str) -> bool:
    return bool(conn.execute("SELECT 1 FROM comunicados WHERE url=?", (url,)).fetchone())


def _save(conn: sqlite3.Connection, data: dict):
    conn.execute("""
        INSERT OR IGNORE INTO comunicados
            (url, slug, titulo, cuerpo, fecha, tipo, operacion, montos, imputados)
        VALUES (:url, :slug, :titulo, :cuerpo, :fecha, :tipo, :operacion, :montos, :imputados)
    """, data)
    conn.commit()


# ─── Fetcher async con retries ────────────────────────────────────────────────
async def _fetch(client: httpx.AsyncClient, url: str, retries: int = 3) -> Optional[str]:
    for attempt in range(retries):
        try:
            r = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
            if r.status_code == 200:
                return r.text
            if r.status_code in (404, 410):
                return None
            logger.warning(f"HTTP {r.status_code} en {url} (intento {attempt+1})")
        except Exception as e:
            logger.warning(f"Error en {url}: {e} (intento {attempt+1})")
        await asyncio.sleep(2 ** attempt + uniform(0, 1))
    return None


# ─── Parseo del listado ───────────────────────────────────────────────────────
def _parse_listing(html: str) -> list[dict]:
    """Devuelve lista de {url, titulo} desde una página de listado."""
    articles = re.findall(r"<article[^>]*>(.*?)</article>", html, re.DOTALL)
    results = []
    for art in articles:
        m = re.search(
            r'class="post-title"[^>]*href="([^"]+)"[^>]*title="([^"]+)"',
            art,
        )
        if not m:
            # Fallback: primer enlace pgr.gob.do en el artículo
            m2 = re.search(
                r'href="(https://pgr\.gob\.do/[^"]+)"[^>]*title="([^"]+)"',
                art,
            )
            if m2:
                results.append({"url": m2.group(1), "titulo": _strip(m2.group(2))})
        else:
            results.append({"url": m.group(1), "titulo": _strip(m.group(2))})
    return results


# ─── Scraper principal ────────────────────────────────────────────────────────
class PGRScraper:
    def __init__(self, max_pages: int = 100, incremental: bool = True):
        """
        max_pages: cuántas páginas del listado procesar (9 arts/pág).
        incremental: si True, para cuando encuentra URLs ya en la BD.
        """
        self.max_pages = max_pages
        self.incremental = incremental
        self.db = _init_db()
        self.saved = 0
        self.skipped = 0
        self.errors = 0

    async def run(self) -> int:
        logger.info(f"PGR Scraper — max_pages={self.max_pages}, incremental={self.incremental}")
        async with httpx.AsyncClient(timeout=30) as client:
            for page in range(1, self.max_pages + 1):
                url = LIST_URL.format(page=page)
                logger.info(f"Página {page}/{self.max_pages} → {url}")
                html = await _fetch(client, url)
                if not html:
                    logger.warning(f"No se pudo obtener página {page}, fin del scraping")
                    break

                items = _parse_listing(html)
                if not items:
                    logger.info(f"Página {page} sin artículos — fin del archivo")
                    break

                stop_early = False
                for item in items:
                    art_url = item["url"]
                    if _url_exists(self.db, art_url):
                        if self.incremental:
                            logger.info(f"URL ya existe (modo incremental): {art_url}")
                            stop_early = True
                            break
                        self.skipped += 1
                        continue

                    art_html = await _fetch(client, art_url)
                    if not art_html:
                        self.errors += 1
                        continue

                    titulo = _extract_title(art_html) or item["titulo"]
                    cuerpo = _extract_body(art_html)
                    fecha  = _extract_date(cuerpo, art_html)
                    tipo   = _classify_tipo(titulo, cuerpo)
                    op     = _extract_operacion(titulo, cuerpo)
                    montos = _extract_montos(cuerpo)
                    imps   = _extract_imputados(titulo, cuerpo)
                    slug   = art_url.rstrip("/").split("/")[-1]

                    _save(self.db, {
                        "url": art_url, "slug": slug, "titulo": titulo,
                        "cuerpo": cuerpo[:8000],  # limitar tamaño
                        "fecha": fecha, "tipo": tipo, "operacion": op,
                        "montos": montos, "imputados": imps,
                    })
                    self.saved += 1
                    logger.debug(f"  ✓ [{tipo}] {titulo[:70]}")
                    await asyncio.sleep(uniform(0.8, 2.0))

                if stop_early:
                    break

                await asyncio.sleep(uniform(1.5, 3.5))

        self.db.close()
        logger.info(
            f"PGR Scraper finalizado — guardados: {self.saved}, "
            f"omitidos: {self.skipped}, errores: {self.errors}"
        )
        return self.saved


async def run_pgr_scraper(max_pages: int = 100, incremental: bool = True) -> int:
    scraper = PGRScraper(max_pages=max_pages, incremental=incremental)
    return await scraper.run()
