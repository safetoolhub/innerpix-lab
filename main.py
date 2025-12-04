"""
Pixaro Lab - Punto de entrada de la aplicación

Aplicación de gestión de archivos multimedia con herramientas para la organización y limpieza de duplicados
"""
import sys
import os

# Configurar Qt para evitar warnings de Wayland
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.wayland=false'

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.styles.design_system import DesignSystem
from config import Config
from utils.logger import configure_logging, get_logger
from utils import get_optimal_window_config
from utils.settings_manager import settings_manager
import logging


def main():
    """Punto de entrada principal de la aplicación"""
    # Leer nivel de log desde configuración persistente
    saved_log_level = settings_manager.get_log_level("INFO")  # INFO por defecto
    saved_dual_log = settings_manager.get_dual_log_enabled()  # True por defecto
    
    # Configurar sistema de logging con nivel guardado
    log_file, logs_dir = configure_logging(
        logs_dir=Config.DEFAULT_LOG_DIR,
        level=saved_log_level,
        dual_log_enabled=saved_dual_log
    )
    
    # Cargar configuración persistente
    Config.USE_VIDEO_METADATA = settings_manager.get_bool(
        settings_manager.KEY_USE_VIDEO_METADATA, 
        False  # Por defecto deshabilitado
    )
    
    # Obtener logger y mostrar información de inicio
    logger = get_logger()
    log_level = logging.getLevelName(logger.logger.level)
    
    # Obtener información del sistema
    sys_info = Config.get_system_info()
    
    logger.info("=" * 80)
    logger.info(f"Iniciando {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info("=" * 80)
    logger.info("")
    logger.info("📊 CONFIGURACIÓN DEL SISTEMA:")
    logger.info(f"  • RAM Total: {sys_info['ram_total_gb']:.2f} GB")
    if sys_info['ram_available_gb']:
        logger.info(f"  • RAM Disponible: {sys_info['ram_available_gb']:.2f} GB")
    logger.info(f"  • CPU Cores: {sys_info['cpu_count']}")
    logger.info(f"  • Workers I/O (hashing): {sys_info['io_workers']}")
    logger.info(f"  • Workers CPU (imágenes): {sys_info['cpu_workers']}")
    if not sys_info['psutil_available']:
        logger.info("  ⚠️  psutil no disponible, usando valores por defecto")
    logger.info("")
    logger.info("💾 CONFIGURACIÓN DE MEMORIA:")
    logger.info(f"  • Máx. entradas en caché (inicial): {sys_info['max_cache_entries']:,}")
    logger.info(f"  • Umbral dataset grande: {sys_info['large_dataset_threshold']:,} archivos")
    logger.info(f"  • Apertura auto diálogo: {sys_info['auto_open_threshold']:,} archivos")
    logger.info("")
    logger.info("📁 CONFIGURACIÓN DE LOGS:")
    logger.info(f"  • Nivel de log: {log_level}")
    logger.info(f"  • Archivo de log: {log_file}")
    logger.info(f"  • Directorio de logs: {logs_dir}")
    if saved_dual_log and saved_log_level in ('INFO', 'DEBUG'):
        logger.info(f"  • Dual logging: activado (se creará archivo adicional _WARNERROR)")
    else:
        logger.info(f"  • Dual logging: {'desactivado' if not saved_dual_log else 'no aplicable (nivel WARNING/ERROR)'}")
    logger.info("")
    logger.info("⚙️  CONFIGURACIÓN DE ANÁLISIS:")
    logger.info(f"  • Metadatos de video: {'habilitada' if Config.USE_VIDEO_METADATA else 'deshabilitada'}")
    logger.info("=" * 80)
    logger.info("")
    
    app = QApplication(sys.argv)

    # Configurar la aplicación
    app.setApplicationName(Config.APP_NAME)
    app.setApplicationVersion(Config.APP_VERSION)
    app.setOrganizationName("PixaroLab")

    # Crear y mostrar ventana principal (nueva implementación)
    window = MainWindow()
    
    # Configurar tamaño de ventana usando utilidad desacoplada
    action, window_size, center_pos = get_optimal_window_config()
    
    if action == 'resize' and window_size and center_pos:
        # Monitor 2K+ o superior: mostrar en FullHD centrado
        window.resize(window_size.width, window_size.height)
        window.move(center_pos[0], center_pos[1])
        logger.info(f"Ventana configurada en FullHD ({window_size}) centrada en pantalla")
    else:
        # Monitor FullHD o inferior: maximizar
        window.showMaximized()
        logger.info("Ventana maximizada")
    
    window.show()
    
    logger.info("Ventana principal mostrada")

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
