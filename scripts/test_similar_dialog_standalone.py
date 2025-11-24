#!/usr/bin/env python3
"""
Script standalone para probar el diálogo de Similar Files con caché pre-cargada.

Este script demuestra cómo usar la caché persistente para desarrollo rápido:
- Carga instantáneamente un análisis pre-calculado (< 1 segundo)
- Abre el diálogo completo con datos reales
- Perfecto para iterar rápidamente en desarrollo de UI

Uso:
    python scripts/test_similar_dialog_standalone.py
    python scripts/test_similar_dialog_standalone.py --cache /path/to/custom/cache.pkl
    python scripts/test_similar_dialog_standalone.py --debug
"""

import sys
import argparse
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox

# Añadir el directorio raíz al path para importar módulos
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.similar_files_detector import SimilarFilesAnalysis
from ui.dialogs.similar_files_dialog import SimilarFilesDialog
from utils.logger import configure_logging, get_logger


def parse_arguments():
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Prueba el diálogo de Similar Files con caché pre-cargada"
    )
    
    parser.add_argument(
        "--cache",
        type=str,
        default=None,
        help="Path al archivo de caché (default: ~/Documents/Pixaro_Lab/dev_cache/similar_analysis.pkl)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Habilita modo debug con logging detallado"
    )
    
    return parser.parse_args()


def get_default_cache_file() -> Path:
    """Retorna el path por defecto del archivo de caché."""
    return Path.home() / "Documents" / "Pixaro_Lab" / "dev_cache" / "similar_analysis.pkl"


def load_cached_analysis(cache_file: Path, logger) -> SimilarFilesAnalysis | None:
    """
    Carga un análisis desde el archivo de caché.
    
    Args:
        cache_file: Path al archivo de caché
        logger: Logger para mensajes
        
    Returns:
        SimilarFilesAnalysis si se carga exitosamente, None si hay error
    """
    if not cache_file.exists():
        logger.error(f"❌ Archivo de caché no encontrado: {cache_file}")
        logger.info("\n💡 Para crear la caché, ejecuta:")
        logger.info(f"   python scripts/cache_similar_analysis.py create /path/to/photos")
        return None
    
    try:
        logger.info(f"📂 Cargando caché desde: {cache_file}")
        import time
        start_time = time.time()
        
        analysis = SimilarFilesAnalysis.load_from_file(cache_file)
        
        load_time = time.time() - start_time
        logger.info(f"✅ Caché cargada en {load_time:.3f}s")
        logger.info(f"   • Archivos: {analysis.total_files:,}")
        logger.info(f"   • Hashes calculados: {len(analysis.perceptual_hashes):,}")
        logger.info(f"   • Workspace: {analysis.workspace_path}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Error al cargar la caché: {e}")
        logger.info("\n💡 Intenta regenerar la caché:")
        logger.info(f"   python scripts/cache_similar_analysis.py create /path/to/photos")
        return None


def show_error_dialog(message: str, details: str = ""):
    """Muestra un diálogo de error al usuario."""
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("Error al cargar caché")
    msg_box.setText(message)
    
    if details:
        msg_box.setInformativeText(details)
    
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def main():
    """Función principal del script."""
    # Parsear argumentos
    args = parse_arguments()
    
    # Configurar logging
    log_level = "DEBUG" if args.debug else "INFO"
    logs_dir = Path.home() / "Documents" / "Pixaro_Lab" / "logs"
    configure_logging(logs_dir, level=log_level)
    logger = get_logger("TestSimilarDialogStandalone")
    
    logger.info("=" * 80)
    logger.info("🚀 Test Similar Files Dialog con Caché Pre-cargada")
    logger.info("=" * 80)
    
    # Determinar archivo de caché
    if args.cache:
        cache_file = Path(args.cache).expanduser()
        logger.info(f"📁 Usando caché personalizada: {cache_file}")
    else:
        cache_file = get_default_cache_file()
        logger.info(f"📁 Usando caché por defecto: {cache_file}")
    
    # Cargar análisis desde caché
    analysis = load_cached_analysis(cache_file, logger)
    
    if not analysis:
        # Crear aplicación solo para mostrar error
        app = QApplication(sys.argv)
        show_error_dialog(
            "No se pudo cargar el archivo de caché.",
            f"Asegúrate de crear la caché primero:\n"
            f"python scripts/cache_similar_analysis.py create /path/to/photos"
        )
        return 1
    
    # Crear aplicación PyQt6
    app = QApplication(sys.argv)
    
    # Crear y mostrar diálogo
    logger.info(f"\n🎨 Abriendo diálogo (sensibilidad se ajusta automáticamente según tamaño del dataset)")
    
    try:
        dialog = SimilarFilesDialog(
            parent=None,
            analysis=analysis
        )
        
        logger.info("✅ Diálogo creado exitosamente")
        logger.info("\n💡 Tips:")
        logger.info("   • Mueve el slider para ver diferentes agrupaciones")
        logger.info("   • Usa la paginación para navegar grupos grandes")
        logger.info("   • El clustering es instantáneo (datos pre-calculados)")
        logger.info("\n👉 Cierra el diálogo cuando termines de probar")
        
        dialog.show()
        exit_code = app.exec()
        
        logger.info(f"\n✅ Diálogo cerrado (exit code: {exit_code})")
        return exit_code
        
    except Exception as e:
        logger.error(f"❌ Error al crear el diálogo: {e}", exc_info=True)
        show_error_dialog(
            "Error al crear el diálogo",
            f"Detalles: {str(e)}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
