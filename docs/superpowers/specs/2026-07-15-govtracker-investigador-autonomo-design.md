# GovTracker RD → Investigador Autónomo

**Fecha:** 2026-07-15
**Estado:** Spec aprobado para implementación
**Autor:** Branel + Claude

---

## 1. Objetivo

Convertir GovTracker RD de un panel de consulta pasiva en un **investigador autónomo** que:

- **(a)** se mantenga actualizado solo, sin intervención manual;
- **(b)** detecte irregularidades con **precisión**, no con volumen;
- **(c)** analice cruzando fuentes que hoy no se cruzan;
- **(d)** avise proactivamente por Telegram y correo.

### Qué NO puede hacer este sistema (límite honesto)

Este sistema **no puede encontrar "todo lo que el gobierno esconde"**. Solo detecta patrones en lo que el gobierno **sí publica**. Lo que nunca se subió a un portal es invisible para cualquier software.

Lo que sí hace: encontrar lo que está **escondido a plena vista** — patrones que nadie cruza porque son 655K contratos, 7.3M de filas de nómina y 450 comunicados judiciales. Esa es la ventaja real y es suficiente.

---

## 2. Realidad verificada del proyecto (2026-07-15)

Todo lo de esta sección fue verificado **leyendo código y consultando las bases de datos reales**, no la documentación. Cualquier implementador debe asumir que esto es correcto y que los docs previos pueden mentir.

### 2.1 Lo que funciona y es valioso

| Activo | Volumen real |
|---|---|
| `contratos` | 655,247 filas |
| `empresas` | 131,848 |
| `representantes_legales` | 123,128 |
| `nominas.db` → `empleados` | **7,368,633** |
| `gasto_ejecutado.db` → `gasto_detalle` | 231,966 |
| `pgr.db` → `comunicados` | 450 |
| `instituciones` | 737 |
| `proveedores_inhabilitados` | 2,009 |

De 19 scrapers, **~9 son ETL en vivo funcional**: `dgcp_bulk_importer` (la joya: 655K contratos), `hacienda_ejecucion_importer`, `camara_diputados_scraper`, `congreso_comisiones_scraper`, los 3 de nóminas (`diputados`, `map`, `pgr`), `pgr_scraper`, `dgii_scraper` (manual).

Los scrapers deduplican bien por clave natural (RPE/RNC/nº contrato/URL vista). **Reconstruir desde cero es seguro.**

### 2.2 Problemas críticos verificados

**P1 — El motor de detección no está en git.**
`git log -- backend/app/services/alert_scanner.py` devuelve **vacío**. Nunca se ha commiteado. Igual que `etl_run.py`, `map_nominas_scraper.py`, `hacienda_ejecucion_importer.py`, `gasto_ejecutado.py`, `GastoEjecutado.tsx`. Existen solo en el disco local. El commit `c4e7fe4` dice *"add conflict-of-interest alert rule"* pero la regla vive en el archivo sin rastrear: **el historial de git describe trabajo que no contiene.**

**P2 — No existe repo remoto.** `git remote -v` está vacío. El proyecto es 100% local.

**P3 — Cero automatización.** No hay Celery Beat en `docker-compose.yml` (solo `db`, `redis`, `backend`, `worker`, `frontend`), ni APScheduler, ni cron, ni GitHub Actions. Todo se dispara a mano por endpoints POST. El propio código lo admite en `api/routes/etl.py:213`: *"manual hoy; programable con cron/scheduler cuando esto esté desplegado"*.

**P4 — `run_incremental()` es un alias vacío.** En `app/etl/pipeline.py` es literalmente `return await self.run_full()`. La incrementalidad real vive en cada importador, no en el orquestador.

**P5 — `etl_runs` tiene 0 filas.** El modelo de auditoría existe pero nunca se usó. Hoy es imposible responder "¿cuándo se actualizó esto por última vez?".

**P6 — Las alertas son ruido, no señal.**

| Tipo | Cantidad | % |
|---|---|---|
| EMPRESA_CONCENTRADA | 26,490 | 78.1% |
| PROVEEDOR_INHABILITADO | 6,403 | 18.9% |
| EMPRESA_CAUTIVA | 931 | 2.7% |
| CONTRATO_GRANDE | 33 | 0.1% |
| ANOMALIA_MONTO | 21 | |
| INCREMENTO_PRECIO | 9 | |
| MUCHAS_ADENDAS | 8 | |
| POSIBLE_CONFLICTO | 2 | |
| **Total** | **33,897** | |

El 97% son tres reglas de baja especificidad. **Notificar esto tal cual haría inútil el sistema desde el día 1.**

**P7 — `representantes_legales.cedula` está VACÍA.** 0 de 123,128 filas tienen cédula. `total_empresas` es 0 en todas. Por eso `POSIBLE_CONFLICTO` solo halló 2 coincidencias: cruza por **texto de nombre**, sin identificador que confirme identidad. Cualquier regla basada en cédula es **imposible hoy**.

**P8 — `pgr.comunicados.imputados` está poblado pero contaminado.** 450/450 tienen valor, pero el extractor recoge cualquier secuencia capitalizada. Ejemplo real:
> `Santo Domingo Este; Francis Yoel Terrero Ramírez; El Ministerio Público; María Sánchez; Jean Carlos Evangelista Montero; Código Penal Dominicano; Derechos Fundamentales; Primer Tribunal Colegiado`

Mezcla personas reales con lugares, instituciones y leyes. **Inservible para cruzar sin limpieza previa.** Solo 92/450 tienen `montos`.

**P9 — Fuentes congeladas.** `sib_scraper` (bancos) = catálogo fijo con cifras de **2022**. `cooperativas` = 0 filas. `jce`, `combustibles`, `seguridad`, `seguros_senasa` = semillas fijas de pocos casos. `seguros.db` (2,737 filas) es **huérfana**: la lee `api/routes/seguros.py` pero ningún scraper la llena.

**P10 — `intelligence.py` no escala.** 553 líneas que recalculan sobre 655K contratos **en cada request HTTP**, sin caché ni materialización.

**P11 — 8 de 19 scrapers no están en `pipeline.py`.** `dgcp_bulk_importer`, `hacienda_ejecucion_importer`, los 3 de nóminas, `pgr_scraper`, `punta_catalina_seed`, `dgii_scraper` solo se disparan por endpoints sueltos. **Nota: los dos primeros son los más importantes del proyecto.** Cualquier automatización debe ensamblarlos explícitamente.

**P12 — 25 archivos sin commitear** (19 modificados + 6 sin rastrear), 853 inserciones / 934 eliminaciones.

### 2.3 Esquemas verificados (para no adivinar)

```
contratos: id, numero_contrato, numero_proceso, institution_id, company_id, project_id,
  loan_id, descripcion, objeto, modalidad, estado, monto_original, monto_actual,
  monto_pagado, moneda, fecha_firma, fecha_inicio, fecha_fin_planificada, fecha_fin_real,
  oficial_firmante, oficial_aprobador, tiene_adendas, num_adendas, incremento_porcentual,
  retraso_dias, financiado_prestamo, es_mayor_100m, fuente, url_fuente, raw_data,
  created_at, updated_at

representantes_legales: id, company_id, nombre, cedula(VACÍA), cargo, email, telefono,
  activo, total_empresas(=0), created_at

nominas.db → empleados: id, institucion, nombre_raw, nombre, funcion, salario, mes, anio, fuente
nominas.db → meta_descarga: dataset_id, titulo, institucion, url, descargado_en, filas

gasto_ejecutado.db → gasto_institucion: id, institucion, institucion_norm, anio, mes,
  presupuesto_inicial, presupuesto_vigente, devengado
gasto_ejecutado.db → gasto_detalle: id, institucion_norm, anio, mes, programa, actividad, devengado
gasto_ejecutado.db → gasto_funcion: id, finalidad, anio, mes, presupuesto_vigente, devengado

pgr.db → comunicados: id, url, slug, titulo, cuerpo, fecha, tipo, operacion, montos,
  imputados(CONTAMINADO), scraped_at
```

### 2.4 Tamaños (definen la arquitectura)

| Archivo | Tamaño |
|---|---|
| `backend/govtracker_test.db` | **320 MB** ← el que importa a diario |
| `backend/data/nominas.db` | **2.2 GB** ← mensual, no diario |
| `backend/data/gasto_ejecutado.db` | 112 MB |
| `backend/data/pgr.db` | 2.1 MB |
| `backend/data/seguros.db` | 320 KB |
| `backend/data/govtracker_test.db` | **0 B — huérfano, borrar** |

Todos los `.db` están correctamente en `.gitignore`.

---

## 3. Decisiones tomadas

| Decisión | Elección | Razón |
|---|---|---|
| Dónde corre | **GitHub Actions**, repo **privado** | Cron real que corre con la Mac apagada. Gratis. Railway costaría dinero por 2.8 GB. Privado porque es una herramienta para investigar al gobierno del país donde vive el usuario. |
| Frecuencia | **Diaria**, 06:00 AST (10:00 UTC) | DGCP publica por lotes; más frecuencia gasta CI sin ganar nada. |
| Avisos | **Telegram + Gmail digest** | Telegram = golpe inmediato. Correo = revisión con calma. |
| Correo destino | **marianobranel@gmail.com** (confirmado por el usuario) | |
| Alcance ahora | Fases 0–3 | Fases 4–5 después. |

### Persistencia de la BD entre corridas

GitHub Actions es efímero; la BD vive en la Mac. Solución:

- **Solo `govtracker_test.db` (320 MB) viaja a diario.** Se guarda en `actions/cache` con clave por fecha (`govtracker-db-{{ github.run_id }}`) y `restore-keys` por prefijo para recuperar la más reciente.
- **Si la caché falla → reconstrucción completa** desde los CSV de DGCP. Más lenta pero nunca rota (los importadores deduplican).
- **`nominas.db` (2.2 GB) NO viaja a diario.** El MAP publica mensual → workflow mensual propio.
- **La BD de CI es la fuente de verdad** del pipeline automático. La Mac puede descargar el artefacto cuando el usuario quiera navegar en local.

---

## 4. Arquitectura

```
┌─ GitHub Actions: investigar.yml (cron diario 10:00 UTC) ──────────┐
│                                                                    │
│  1. restaurar govtracker_test.db desde caché (320MB)              │
│       └─ miss → reconstruir desde CSV DGCP                        │
│  2. ETL incremental:                                              │
│       dgcp_bulk_importer → hacienda_ejecucion → camara_diputados  │
│       → congreso_comisiones → pgr_scraper                         │
│       └─ cada uno registra EtlRun (inicio, fin, filas, error)     │
│  3. alert_scanner.run_alert_scan()                                │
│  4. diff: alertas creadas en ESTA corrida                         │
│  5. si hay nuevas → Telegram (severidad ALTA/CRÍTICA)             │
│                   → Gmail digest (todas, agrupadas)               │
│  6. guardar BD en caché                                           │
└───────────────────────────────────────────────────────────────────┘

┌─ GitHub Actions: nominas.yml (cron mensual, día 5) ───────────────┐
│  map_nominas + diputados_nominas + pgr_nominas → detección cruzada│
└───────────────────────────────────────────────────────────────────┘
```

### Módulos nuevos

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `app/services/notifier.py` | Interfaz `Notifier` + `TelegramNotifier` + `GmailNotifier`. Solo formatea y envía. | secretos |
| `app/services/digest.py` | Toma alertas nuevas → texto agrupado por severidad. Sin I/O. | modelos |
| `app/services/alert_diff.py` | Determina qué alertas son nuevas desde la última `EtlRun`. | `Alert`, `EtlRun` |
| `app/etl/orchestrator.py` | Corre los scrapers en orden, registra `EtlRun`, tolera fallos individuales. | scrapers |
| `scripts/investigar.py` | Punto de entrada del workflow. Ensambla lo anterior. | todo |

**Principio de aislamiento:** `digest.py` no sabe enviar; `notifier.py` no sabe qué es una alerta interesante; `alert_diff.py` no sabe formatear. Cada uno se testea solo.

---

## 5. Fases

### FASE 0 — Salvar lo que existe (BLOQUEANTE)

> Sin esto no hay Actions y el motor de detección sigue a un disco duro de desaparecer.

- **0.1** Revisar los 25 cambios pendientes. Commitear en cambios lógicos separados (no un commit gigante).
- **0.2** Verificar que `backend/.env` sigue ignorado y que **ningún secreto** entra al repo. Solo `.env.example` se rastrea. Confirmar antes de push.
- **0.3** Borrar `backend/data/govtracker_test.db` (0 B, huérfano y confuso).
- **0.4** Crear repo **PRIVADO** en GitHub (`gh repo create --private`) y push de `master`.
- **0.5** Añadir `pytest` a `requirements.txt` y crear `backend/tests/`. **Hoy no hay ni un test.**

**Aceptación:** `git log -- backend/app/services/alert_scanner.py` devuelve commits. El repo existe en GitHub, privado. `pytest` corre (aunque sea con 1 test trivial).

---

### FASE 1 — Autonomía

- **1.1** `EtlRun` real: `orchestrator.py` registra inicio/fin/filas nuevas/error por scraper. Un scraper que falla **no aborta** los demás (hoy un fallo mata la corrida).
- **1.2** Registrar en `pipeline.py` los 8 scrapers huérfanos — con prioridad a `dgcp_bulk_importer` y `hacienda_ejecucion_importer`, que son los más importantes y hoy no están.
- **1.3** Arreglar `run_incremental()`: debe correr solo las fuentes con cadencia diaria, no ser un alias de `run_full()`.
- **1.4** `.github/workflows/investigar.yml`: cron `0 10 * * *`, Python 3.11+, caché de BD con `restore-keys`, fallback a reconstrucción, `workflow_dispatch` para disparo manual.
- **1.5** Timeout de 45 min y notificación de fallo del workflow (un cron que muere en silencio es peor que no tenerlo).

**Aceptación:** `workflow_dispatch` manual corre verde end-to-end. `SELECT COUNT(*) FROM etl_runs` > 0. Segunda corrida seguida NO duplica contratos.

---

### FASE 2 — Que te lo muestre

- **2.1** `alert_diff.py`: alertas nuevas desde la última corrida exitosa. **Sin esto llegan 33,897 alertas viejas cada día.**
- **2.2** `digest.py`: agrupa por severidad, ordena CRÍTICA→ALTA→MEDIA, incluye monto, institución, empresa y enlace a la fuente. Tope de 20 ítems por mensaje + "y N más".
- **2.3** `TelegramNotifier`: solo **CRÍTICA y ALTA**. Silencio es una feature.
- **2.4** `GmailNotifier` vía SMTP `smtp.gmail.com:465` + `nodemailer`-equivalente en Python (`smtplib`). Digest diario completo a **marianobranel@gmail.com**. Solo envía si hay algo nuevo — un correo diario de "0 hallazgos" entrena a ignorarlo.
- **2.5** Tests con transporte simulado + **una prueba de envío real verificada por el usuario** antes de dar la fase por buena.

> ⚠️ **Las credenciales del CRM no son reutilizables por archivo.** El CRM guarda `gmail_user` / `gmail_app_password` **cifrados con AES-256-GCM en Firestore** (`org_tokens/{orgId}`, ver `CRM-Auto/lib/gmail.ts`). Un job de Python no puede leerlas. Se usa el **mismo buzón**, pero hace falta generar una contraseña de aplicación nueva y guardarla como secreto de GitHub.

**Aceptación:** el usuario recibe un Telegram y un correo reales con hallazgos reales.

---

### FASE 3 — Precisión y mejor uso de los datos

> Esta fase responde a *"dale un mejor uso a la información"*. **La respuesta honesta: hoy no se le da el uso adecuado, y la causa raíz es que los datos no están en la forma correcta.** Por eso 3.1 y 3.2 van antes que cualquier regla nueva.

#### 3.1 Reparar la identidad de personas (habilita todo lo demás)

`representantes_legales.cedula` está vacía en las 123,128 filas → todo cruce de personas es por texto → `POSIBLE_CONFLICTO` encuentra 2 coincidencias en un país con corrupción documentada. **La regla no es mala; está ciega.**

- Poblar `cedula` vía `dgii_scraper` (ya existe y funciona, hoy solo manual con `limit=200`).
- Calcular `total_empresas` (hoy 0 en todas) en `dgcp_bulk_importer.recompute_stats`.
- Centralizar la normalización de nombres en **un solo módulo** reutilizando el fix de case-folding Unicode de `c4e7fe4`. Hoy esa lógica está duplicada.

#### 3.2 Limpiar `imputados` de la PGR

El campo está poblado (450/450) pero mezcla personas con lugares, leyes y tribunales. Extraer entidades de persona reales con **Groq** (ya usado en el proyecto, barato) sobre `cuerpo`, guardando en tabla nueva `pgr_personas (comunicado_id, nombre, nombre_norm)`.
Son **450 comunicados: coste de una sola pasada, no recurrente.** Prompt conciso (regla del usuario: optimizar tokens).

#### 3.3 Subir la precisión de lo que ya existe

- `EMPRESA_CONCENTRADA` (26,490): elevar umbral y exigir **monto material**. 20 contratos de RD$50K no es señal. Objetivo: <500 alertas.
- `PROVEEDOR_INHABILITADO` (6,403): auditar. Verificar que compara contra la **fecha de inhabilitación** y no marca contratos anteriores. Sospecha de bug.
- Añadir `score` numérico al modelo `Alert` para ordenar el digest por relevancia, no solo por severidad categórica.

#### 3.4 Reglas nuevas (solo tras 3.1–3.3)

| Regla | Cruce | Datos | Viable |
|---|---|---|---|
| `NOMINA_Y_PROVEEDOR` | `empleados.nombre` × `representantes_legales.nombre` en la misma institución que contrata | 7.3M × 123K | ✅ Existe suelta en `nominas.py`; **unificar en `alert_scanner`** |
| `IMPUTADO_CONTRATISTA` | `pgr_personas` × representantes legales de empresas con contratos vigentes | tras 3.2 | ✅ Alta señal |
| `GASTO_SIN_CONTRATO` | `gasto_institucion.devengado` vs Σ contratos por institución/mes | 231K × 655K | ⚠️ Ver riesgo R3 |
| `REPRESENTANTE_MULTI_EMPRESA` | mismo representante en varias empresas contratando con la misma institución | tras 3.1 | ✅ Competencia simulada |

**Aceptación:** total de alertas < 2,000 (desde 33,897) **sin perder ninguna de las 73 accionables actuales**. Cada regla nueva con test sobre un caso real verificado a mano.

---

### FASE 4 — Fuentes muertas (posterior)

Bancos (cifras de 2022), cooperativas (0 filas), JCE, `seguros.db` huérfana. **Decisión pendiente por fuente: revivir el scraping o aceptar que son snapshots** y etiquetarlos como tales en la UI con su fecha. No dejarlos aparentando estar vivos.

### FASE 5 — Rendimiento (posterior)

Materializar `intelligence.py` en tablas precalculadas por el cron nocturno. Índices en `contratos(institution_id, fecha_firma)`, `contratos(company_id)`, `empleados(nombre, anio, mes)`. Alinea con el estándar obligatorio de indexing+caching del usuario.

---

## 6. Configuración

### Secretos de GitHub (`gh secret set`)

| Secreto | Uso | Origen |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | bot de avisos | @BotFather (nuevo) |
| `TELEGRAM_CHAT_ID` | destino | @userinfobot |
| `GMAIL_USER` | remitente | mismo buzón del CRM |
| `GMAIL_APP_PASSWORD` | SMTP | **contraseña de aplicación nueva** de Google |
| `ALERT_EMAIL_TO` | destino | `marianobranel@gmail.com` |
| `GROQ_API_KEY` | limpieza PGR (fase 3.2) | ya existe en el proyecto |

**Ningún secreto en el repo.** `backend/.env` seguirá ignorado; en CI se inyectan por `env:`.

---

## 7. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| **R1** | **Fatiga de alertas** mata el sistema. Es el riesgo #1: 33,897 alertas y 97% ruido. | Fase 3 antes de subir volumen. Telegram solo CRÍTICA/ALTA. Sin hallazgos → sin mensaje. |
| **R2** | **Falsos positivos por nombre.** Sin cédula, dos personas homónimas se confunden. Acusar a un inocente es un daño real. | Fase 3.1 primero. Hasta entonces, toda alerta por nombre se marca **"coincidencia por nombre, sin verificar"** en el mensaje. **No negociable.** |
| **R3** | **`GASTO_SIN_CONTRATO` sería ruido puro si es ingenuo.** El devengado incluye nóminas, transferencias y pensiones, que no son contratos. Restar solo contratos daría "gasto inexplicado" en todas las instituciones. | Restar también la nómina de esa institución/mes (`nominas.db`) y validar contra un caso conocido a mano **antes** de activarla. Si no se puede validar, **no se implementa.** |
| **R4** | La caché de Actions se desaloja a los 7 días sin uso. | El cron diario la mantiene viva. Fallback: reconstrucción completa. |
| **R5** | Los portales del gobierno cambian de HTML sin avisar. | `EtlRun` registra fallos por scraper; el orquestador no aborta; aviso si un scraper falla N días seguidos. |
| **R6** | Datos inventados. Regla firme del usuario: **omitir en vez de inventar**. | Ninguna fase añade datos de relleno. Fuentes vacías se muestran vacías. |
| **R7** | Los 2.2 GB de nóminas no caben cómodamente en CI. | Workflow mensual separado. Si falla, se corre en local. |

---

## 8. Criterios de aceptación global

1. `alert_scanner.py` y los otros 5 huérfanos están en git, en GitHub, repo privado.
2. El cron corre solo a diario y `etl_runs` registra cada corrida con filas y errores.
3. Dos corridas seguidas **no duplican** datos.
4. Llega Telegram con hallazgos **nuevos** (no los 33,897 viejos) — verificado por el usuario con un mensaje real.
5. Llega el digest a `marianobranel@gmail.com` — verificado con un correo real.
6. Total de alertas < 2,000 sin perder las 73 accionables.
7. Toda alerta por nombre sin cédula dice explícitamente que no está verificada.
8. `pytest` pasa. Cada regla nueva tiene test con caso real.

> **Nota de método (lección del mismo día):** en el proyecto hermano `armario-virtual`, un cliente de IA pasó meses "funcionando" con tests de `fetch` simulado que verificaban que el código llamaba a la API como el código creía — mientras la API real ignoraba todo y devolvía imágenes de una rana. **Los mocks verifican tus supuestos, no la realidad.** Ninguna fase aquí se declara terminada sin una ejecución real observada: un Telegram real, un correo real, una corrida verde de verdad.

---

## 9. Fuera de alcance

- Deploy del frontend (sigue en local).
- Reescribir `intelligence.py` (fase 5).
- Revivir fuentes congeladas (fase 4).
- Cualquier acción legal/pública con los hallazgos. Esto es una herramienta de investigación personal.
