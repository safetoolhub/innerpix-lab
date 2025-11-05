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
from config import Config
from ui.managers.logging_manager import LoggingManager
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
    window.show()
    
    logger.info("Ventana principal mostrada")

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
