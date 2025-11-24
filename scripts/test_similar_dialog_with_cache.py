"""
Script de ejemplo: Cómo usar la caché de análisis para desarrollo rápido.

Este script muestra cómo cargar instantáneamente un análisis pre-calculado
de 40k+ archivos para probar el diálogo de archivos similares.

FLUJO DE TRABAJO RECOMENDADO:

1. UNA VEZ (lento): Crea la caché del dataset grande
   $ python scripts/cache_similar_analysis.py create /path/to/40k/photos

2. SIEMPRE (instantáneo): Carga la caché en tus pruebas
   $ python scripts/test_similar_dialog_with_cache.py

Esto te permite iterar rápidamente en el desarrollo del diálogo
sin tener que esperar 5-10 minutos cada vez.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from services.similar_files_detector import SimilarFilesAnalysis
from ui.dialogs.similar_files_dialog import SimilarFilesDialog
from utils.logger import configure_logging, get_logger


# Ubicación del archivo de caché
CACHE_FILE = Path.home() / "Documents" / "Pixaro_Lab" / "dev_cache" / "similar_analysis.pkl"


def test_dialog_with_cached_data():
    """
    Prueba el diálogo de archivos similares con datos pre-calculados.
    
    Esto es INSTANTÁNEO (< 1 segundo para cargar 40k archivos).
    """
    # Configurar logging
    logs_dir = Path.home() / "Documents" / "Pixaro_Lab" / "logs"
    configure_logging(logs_dir, level="INFO")
    
    logger = get_logger('TestDialog')
    
    # Verificar que existe la caché
    if not CACHE_FILE.exists():
        logger.error(f"❌ No existe caché en: {CACHE_FILE}")
        logger.info(f"\n💡 Primero crea la caché con:")
        logger.info(f"   python scripts/cache_similar_analysis.py create /path/to/photos")
        return
    
    logger.info(f"📂 Cargando análisis desde caché...")
    
    # Cargar análisis (INSTANTÁNEO)
    analysis = SimilarFilesAnalysis.load_from_file(CACHE_FILE)
    
    logger.info(f"✅ Análisis cargado: {analysis.total_files:,} archivos")
    
    # Crear aplicación Qt
    app = QApplication(sys.argv)
    
    # Crear y mostrar diálogo con análisis pre-cargado
    logger.info(f"🚀 Abriendo diálogo de archivos similares...")
    logger.info("ℹ️  La sensibilidad inicial se ajusta automáticamente según el tamaño del dataset")
    logger.info(f"   (100% para >{10000:,} archivos, 85% para datasets pequeños)")
    
    dialog = SimilarFilesDialog(
        parent=None,
        analysis=analysis
    )
    
    # Mostrar diálogo
    dialog.show()
    
    logger.info(f"✅ Diálogo abierto. Puedes probarlo ahora.")
    logger.info(f"\n💡 Tips:")
    logger.info(f"   • Mueve el slider de sensibilidad para ver clustering en tiempo real")
    logger.info(f"   • Prueba con diferentes sensibilidades (30-100)")
    logger.info(f"   • Verifica el rendimiento con 40k+ archivos")
    logger.info(f"   • Cada cambio de sensibilidad es instantáneo (< 1 segundo)")
    
    # Ejecutar aplicación
    sys.exit(app.exec())


def test_clustering_performance():
    """
    Prueba solo el rendimiento del clustering sin UI.
    
    Útil para benchmarking y optimización.
    """
    # Configurar logging
    logs_dir = Path.home() / "Documents" / "Pixaro_Lab" / "logs"
    configure_logging(logs_dir, level="INFO")
    
    logger = get_logger('TestPerformance')
    
    if not CACHE_FILE.exists():
        logger.error(f"❌ No existe caché en: {CACHE_FILE}")
        return
    
    logger.info(f"📂 Cargando análisis...")
    analysis = SimilarFilesAnalysis.load_from_file(CACHE_FILE)
    
    logger.info(f"\n🧪 Testeando rendimiento de clustering...")
    
    import time
    
    sensitivities = [100, 90, 85, 80, 70, 60, 50, 40, 30]
    
    for sens in sensitivities:
        start = time.time()
        result = analysis.get_groups(sens)
        elapsed = time.time() - start
        
        logger.info(
            f"Sens {sens:3d}%: {result.total_groups:5d} grupos, "
            f"{result.total_similar:5d} duplicados, "
            f"similitud {result.min_similarity:.0f}-{result.max_similarity:.0f}% "
            f"({elapsed:6.3f}s)"
        )
    
    logger.info(f"\n✅ Test de rendimiento completado")


def generate_synthetic_analysis():
    """
    Genera un análisis sintético para pruebas sin necesidad de archivos reales.
    
    Útil si no tienes un dataset grande disponible.
    """
    logger = get_logger('TestSynthetic')
    
    logger.info(f"🔬 Generando análisis sintético...")
    
    # TODO: Implementar generación de datos sintéticos
    # Esto sería útil para pruebas unitarias sin depender de archivos reales
    
    logger.warning(f"⚠️  No implementado aún. Usa el script real con datos reales.")


if __name__ == "__main__":
    # Por defecto, abre el diálogo con datos cacheados
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "dialog":
            test_dialog_with_cached_data()
        elif mode == "perf":
            test_clustering_performance()
        elif mode == "synthetic":
            generate_synthetic_analysis()
        else:
            print(f"❌ Modo desconocido: {mode}")
            print(f"Modos válidos: dialog, perf, synthetic")
    else:
        # Modo por defecto: abrir diálogo
        test_dialog_with_cached_data()
