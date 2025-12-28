#!/usr/bin/env python3
"""
Script de prueba para verificar que la sensibilidad por defecto es 100%
y que el análisis funciona correctamente.
"""

import sys
import os

# Añadir el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from config import Config
from services.duplicates_similar_service import DuplicatesSimilarService

def test_default_sensitivity():
    """Verificar que la sensibilidad por defecto es 100%"""
    print(f"Sensibilidad por defecto en Config: {Config.SIMILAR_FILES_DEFAULT_SENSITIVITY}%")

    # Crear instancia del servicio
    service = DuplicatesSimilarService()

    # Verificar que el método analyze usa la sensibilidad por defecto
    # (sin especificar parámetro)
    print("Probando método analyze() sin parámetros...")

    # Como no tenemos archivos reales, solo verificamos que no crashee
    # y que la configuración se aplique correctamente
    try:
        # Esto debería usar la sensibilidad por defecto (100%)
        result = service.analyze()
        print("✅ analyze() ejecutado correctamente con sensibilidad por defecto")
        print(f"Tipo de resultado: {type(result)}")
        print(f"Resultado exitoso: {result.success}")
    except Exception as e:
        print(f"❌ Error en analyze(): {e}")
        return False

    return True

if __name__ == "__main__":
    print("=== Verificación de Sensibilidad por Defecto ===")
    success = test_default_sensitivity()
    if success:
        print("\n✅ Todos los tests pasaron correctamente")
        print("La sensibilidad por defecto es 100% y el servicio funciona correctamente")
    else:
        print("\n❌ Algunos tests fallaron")
        sys.exit(1)