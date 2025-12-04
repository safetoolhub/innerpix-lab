#!/usr/bin/env python3
"""
Script para verificar el estado actual del dual logging.
"""
import sys
from pathlib import Path

# Verificar configuración guardada sin importar toda la UI
def check_settings():
    # Leer desde QSettings directamente
    try:
        from PyQt6.QtCore import QSettings
        settings = QSettings("PixaroLab", "Pixaro Lab")
        
        dual_log = settings.value("logging/dual_log_enabled", True, type=bool)
        log_level = settings.value("logging/level", "INFO", type=str)
        
        print("=" * 80)
        print("VERIFICACIÓN DE CONFIGURACIÓN GUARDADA")
        print("=" * 80)
        print(f"\n📋 Valores en QSettings:")
        print(f"  • logging/dual_log_enabled: {dual_log}")
        print(f"  • logging/level: {log_level}")
        
        print(f"\n🔍 Análisis:")
        if log_level in ('INFO', 'DEBUG'):
            if dual_log:
                print(f"  ✅ Con nivel {log_level} y dual_log=True: Se crearán 2 archivos")
                print(f"     - pixaro_lab_YYYYMMDD_HHMMSS_{log_level}.log")
                print(f"     - pixaro_lab_YYYYMMDD_HHMMSS_WARNERROR.log")
            else:
                print(f"  ✅ Con nivel {log_level} y dual_log=False: Se creará 1 archivo")
                print(f"     - pixaro_lab_YYYYMMDD_HHMMSS_{log_level}.log")
        else:
            print(f"  ✅ Con nivel {log_level}: Se creará 1 archivo (dual_log no aplica)")
            print(f"     - pixaro_lab_YYYYMMDD_HHMMSS_{log_level}.log")
        
        print("\n" + "=" * 80)
        print("Para aplicar los cambios:")
        print("  1. Cierra la aplicación completamente")
        print("  2. Vuelve a abrirla")
        print("  3. Los nuevos archivos de log reflejarán tu configuración")
        print("=" * 80)
        
    except ImportError:
        print("PyQt6 no disponible. No se puede verificar QSettings.")
        sys.exit(1)

if __name__ == "__main__":
    check_settings()

