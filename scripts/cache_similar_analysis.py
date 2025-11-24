#!/usr/bin/env python3
"""
Script de utilidad para cachear análisis de archivos similares.

PROPÓSITO:
Durante el desarrollo del diálogo de archivos similares, necesitas probar
con datasets grandes (40k+ archivos) pero analizar todo cada vez es MUY lento.

Este script te permite:
1. Analizar UNA VEZ el dataset grande
2. Guardar los resultados en un archivo
3. Cargar INSTANTÁNEAMENTE los resultados en futuras sesiones

USO:
1. Crear caché (primera vez, lento):
   python scripts/cache_similar_analysis.py create /path/to/photos

2. Cargar caché (futuras veces, instantáneo):
   python scripts/cache_similar_analysis.py load

3. Ver info de caché:
   python scripts/cache_similar_analysis.py info

El archivo de caché se guarda en:
   ~/Documents/Pixaro_Lab/dev_cache/similar_analysis.pkl
"""

import sys
from pathlib import Path
import time

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.similar_files_detector import SimilarFilesDetector, SimilarFilesAnalysis
from utils.logger import configure_logging, get_logger
from config import Config


# Configuración
CACHE_DIR = Path.home() / "Documents" / "Pixaro_Lab" / "dev_cache"
CACHE_FILE = CACHE_DIR / "similar_analysis.pkl"


def create_cache(directory: str):
    """
    Analiza un directorio y guarda el resultado en caché.
    
    Args:
        directory: Ruta del directorio a analizar
    """
    logger = get_logger('CacheScript')
    
    directory_path = Path(directory).resolve()
    if not directory_path.exists():
        logger.error(f"❌ El directorio no existe: {directory}")
        return
    
    if not directory_path.is_dir():
        logger.error(f"❌ La ruta no es un directorio: {directory}")
        return
    
    logger.info(f"🔍 Analizando directorio: {directory_path}")
    logger.info(f"⏳ Esto puede tardar varios minutos para datasets grandes...")
    
    detector = SimilarFilesDetector()
    
    def progress_callback(current, total, message):
        if current % 100 == 0:  # Log cada 100 archivos
            percentage = (current / total * 100) if total > 0 else 0
            logger.info(f"   Progreso: {current}/{total} ({percentage:.1f}%)")
        return True  # Continuar
    
    start_time = time.time()
    
    try:
        # Análisis inicial (calcula hashes)
        analysis = detector.analyze_initial(directory_path, progress_callback)
        
        elapsed = time.time() - start_time
        
        logger.info(f"✅ Análisis completado en {elapsed:.1f}s")
        logger.info(f"   • Archivos analizados: {analysis.total_files:,}")
        logger.info(f"   • Hashes calculados: {len(analysis.perceptual_hashes):,}")
        
        # Guardar en caché
        logger.info(f"💾 Guardando caché en: {CACHE_FILE}")
        analysis.save_to_file(CACHE_FILE)
        
        logger.info(f"✅ ¡Caché creada exitosamente!")
        logger.info(f"   Ahora puedes cargarla instantáneamente con:")
        logger.info(f"   python scripts/cache_similar_analysis.py load")
        
    except Exception as e:
        logger.error(f"❌ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()


def load_cache():
    """
    Carga y prueba el caché guardado.
    """
    logger = get_logger('CacheScript')
    
    if not CACHE_FILE.exists():
        logger.error(f"❌ No existe caché en: {CACHE_FILE}")
        logger.info(f"   Crea uno primero con:")
        logger.info(f"   python scripts/cache_similar_analysis.py create /path/to/photos")
        return None
    
    logger.info(f"📂 Cargando caché desde: {CACHE_FILE}")
    
    start_time = time.time()
    
    try:
        analysis = SimilarFilesAnalysis.load_from_file(CACHE_FILE)
        
        elapsed = time.time() - start_time
        
        logger.info(f"✅ Caché cargada en {elapsed:.3f}s (¡instantáneo!)")
        logger.info(f"   • Archivos: {analysis.total_files:,}")
        logger.info(f"   • Hashes: {len(analysis.perceptual_hashes):,}")
        logger.info(f"   • Workspace: {analysis.workspace_path}")
        logger.info(f"   • Timestamp: {analysis.analysis_timestamp}")
        
        # Prueba rápida de clustering
        logger.info(f"\n🧪 Prueba de clustering con diferentes sensibilidades...")
        
        for sens in [100, 85, 50]:
            start = time.time()
            result = analysis.get_groups(sens)
            elapsed = time.time() - start
            
            logger.info(
                f"   Sens {sens}%: {result.total_groups} grupos, "
                f"{result.total_similar} duplicados "
                f"({elapsed:.3f}s)"
            )
        
        logger.info(f"\n✅ ¡La caché funciona perfectamente!")
        logger.info(f"   Ahora puedes usarla en tu código de prueba")
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Error cargando caché: {e}")
        import traceback
        traceback.print_exc()
        return None


def show_info():
    """
    Muestra información sobre la caché existente.
    """
    logger = get_logger('CacheScript')
    
    if not CACHE_FILE.exists():
        logger.info(f"❌ No existe caché en: {CACHE_FILE}")
        return
    
    import os
    from datetime import datetime
    
    size_kb = CACHE_FILE.stat().st_size / 1024
    modified = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
    
    logger.info(f"📊 Información de caché:")
    logger.info(f"   • Ubicación: {CACHE_FILE}")
    logger.info(f"   • Tamaño: {size_kb:.1f} KB")
    logger.info(f"   • Modificado: {modified}")
    
    # Intentar cargar para más detalles
    try:
        analysis = SimilarFilesAnalysis.load_from_file(CACHE_FILE)
        logger.info(f"   • Archivos: {analysis.total_files:,}")
        logger.info(f"   • Workspace: {analysis.workspace_path}")
        logger.info(f"   • Timestamp análisis: {analysis.analysis_timestamp}")
    except Exception as e:
        logger.warning(f"   No se pudo cargar para más detalles: {e}")


def main():
    """Función principal del script."""
    # Configurar logging
    logs_dir = Path.home() / "Documents" / "Pixaro_Lab" / "logs"
    configure_logging(logs_dir, level="INFO")
    
    logger = get_logger('CacheScript')
    
    if len(sys.argv) < 2:
        logger.info("❌ Uso incorrecto")
        logger.info("")
        logger.info("Comandos disponibles:")
        logger.info("  create <directorio>  - Crea caché del directorio")
        logger.info("  load                 - Carga y prueba la caché")
        logger.info("  info                 - Muestra info de la caché")
        logger.info("")
        logger.info("Ejemplos:")
        logger.info("  python scripts/cache_similar_analysis.py create /home/user/Photos")
        logger.info("  python scripts/cache_similar_analysis.py load")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "create":
        if len(sys.argv) < 3:
            logger.error("❌ Falta el directorio a analizar")
            logger.info("Uso: python scripts/cache_similar_analysis.py create <directorio>")
            sys.exit(1)
        create_cache(sys.argv[2])
    
    elif command == "load":
        load_cache()
    
    elif command == "info":
        show_info()
    
    else:
        logger.error(f"❌ Comando desconocido: {command}")
        logger.info("Comandos válidos: create, load, info")
        sys.exit(1)


if __name__ == "__main__":
    main()
