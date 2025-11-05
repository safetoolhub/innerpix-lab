"""
Pixaro Lab - Punto de entrada de la aplicación

Aplicación de gestión de archivos multimedia con herramientas para la organización y limpieza de duplicados
"""
import sys
import os

# Configurar Qt para evitar warnings de Wayland
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.wayland=false'

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QScreen
from ui.main_window import MainWindow
from ui.styles.design_system import DesignSystem
from config import Config
from ui.managers.logging_manager import LoggingManager
from utils import get_optimal_window_config
import logging


def main():
    """Punto de entrada principal de la aplicación"""
    # Inicializar logging manager
    logging_manager = LoggingManager(
        default_dir=Config.DEFAULT_LOG_DIR,
        level="INFO",
        logger_name="PixaroLab"
    )
    
    # Inicializar logger y mostrar nivel de log actual
    logger = logging_manager.logger
    log_level = logging.getLevelName(logger.level)
    logger.info("=" * 80)
    logger.info(f"Iniciando {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info(f"Nivel de log: {log_level}")
    logger.info("=" * 80)
    
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
