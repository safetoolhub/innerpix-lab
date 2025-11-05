#!/usr/bin/env bash
# Script para ejecutar la suite de tests de Pixaro Lab

set -e

echo "🚀 Ejecutando suite de tests de Pixaro Lab"
echo "=========================================="

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    echo "📦 Activando entorno virtual..."
    source .venv/bin/activate
fi

# Verificar que pytest está instalado
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest no está instalado. Instálalo con: pip install pytest pytest-cov"
    exit 1
fi

# Ejecutar tests
echo "🧪 Ejecutando tests..."
pytest "$@"

# Mostrar resumen
echo ""
echo "✅ Tests completados"
echo "📊 Reporte de cobertura disponible en: htmlcov/index.html"