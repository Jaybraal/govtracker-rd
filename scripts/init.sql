-- GovTracker RD — Inicialización de base de datos
-- Este script se ejecuta automáticamente al crear el contenedor

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Para búsqueda de texto rápida

-- Índice GIN para búsquedas full-text en contratos
-- (Se crea después de que SQLAlchemy haya creado las tablas)
-- CREATE INDEX CONCURRENTLY idx_contratos_descripcion_fts
--   ON contratos USING gin(to_tsvector('spanish', coalesce(descripcion, '') || ' ' || coalesce(objeto, '')));

-- CREATE INDEX CONCURRENTLY idx_empresas_nombre_trgm
--   ON empresas USING gin(nombre gin_trgm_ops);

SELECT 'GovTracker RD DB inicializada correctamente' AS mensaje;
