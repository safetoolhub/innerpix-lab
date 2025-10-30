"""
Pixaro Lab - Punto de entrada de la aplicación

Aplicación de gestión de archivos multimedia con normalización,
detección de Live Photos, unificación de directorios y limpieza de duplicados.
"""
import sys
import os

# Configurar Qt para evitar warnings de Wayland
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.wayland=false'

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from config import Config
from utils.logger import get_logger
import logging


def main():
    """Punto de entrada principal de la aplicación"""
    # Inicializar logger y mostrar nivel de log actual
    logger = get_logger("Main")
    log_level = logging.getLevelName(logger.logger.level)
    logger.info("=" * 80)
    logger.info(f"Iniciando {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info(f"Nivel de log: {log_level}")
    logger.info("=" * 80)
    
    app = QApplication(sys.argv)

    # Configurar la aplicación
    app.setApplicationName(Config.APP_NAME)
    app.setApplicationVersion(Config.APP_VERSION)
    app.setOrganizationName("PixaroLab")

    # Crear y mostrar ventana principal
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
