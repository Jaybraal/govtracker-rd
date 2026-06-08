#!/bin/bash
# GovTracker RD — Script de instalación y arranque
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║        GovTracker RD — Setup Inicial         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Instálalo desde https://docker.com"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose no está instalado."
    exit 1
fi

# Crear .env si no existe
if [ ! -f .env ]; then
    echo "📋 Creando .env desde .env.example..."
    cp .env.example .env
    echo "✅ .env creado. Puedes editarlo antes de continuar."
fi

# Arrancar servicios
echo ""
echo "🐳 Iniciando contenedores Docker..."
docker compose up -d --build

echo ""
echo "⏳ Esperando a que la base de datos esté lista..."
sleep 8

# Verificar backend
echo ""
echo "🔍 Verificando API..."
MAX_RETRIES=15
RETRY=0
until curl -sf http://localhost:8000/api/health > /dev/null || [ $RETRY -eq $MAX_RETRIES ]; do
    sleep 2
    RETRY=$((RETRY+1))
    echo "   Intento $RETRY/$MAX_RETRIES..."
done

if curl -sf http://localhost:8000/api/health > /dev/null; then
    echo "✅ Backend activo en http://localhost:8000"
    echo "✅ API Docs en http://localhost:8000/api/docs"
else
    echo "⚠️  Backend tardando en iniciar. Revisa: docker compose logs backend"
fi

echo ""
echo "🌐 Frontend: http://localhost:3000"
echo ""
echo "═══════════════════════════════════════════════"
echo "  SIGUIENTE PASO: Importar datos iniciales"
echo ""
echo "  1. Abre http://localhost:3000/etl"
echo "  2. Selecciona las fuentes y ejecuta el ETL"
echo "  3. O corre desde terminal:"
echo "     curl -X POST http://localhost:8000/api/etl/run"
echo ""
echo "  OPCIONAL: Instalar Ollama para IA avanzada:"
echo "     curl -fsSL https://ollama.ai/install.sh | sh"
echo "     ollama pull llama3"
echo "═══════════════════════════════════════════════"
