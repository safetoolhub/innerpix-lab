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
    
    # Configurar fuente para soportar emojis
    # Qt en Linux puede tener problemas mostrando emojis de color.
    # Usamos una fuente con fallback a Noto Color Emoji.
    from PyQt6.QtGui import QFont, QFontDatabase
    
    # Intentar cargar fuente emoji si existe
    emoji_fonts = ["Noto Color Emoji", "Noto Emoji", "Segoe UI Emoji", "Apple Color Emoji"]
    for emoji_font in emoji_fonts:
        families = QFontDatabase.families()
        if emoji_font in families:
            logger.debug(f"Fuente emoji encontrada: {emoji_font}")
            break
    
    # Configurar fuente por defecto con soporte emoji
    font = QFont("sans-serif")
    font.setPointSize(10)
    app.setFont(font)
    
    # Aplicar estilo global para tooltips (debe ser a nivel de QApplication)
    from ui.styles import STYLE_GLOBAL_TOOLTIP
    app.setStyleSheet(STYLE_GLOBAL_TOOLTIP)

    # Crear y mostrar ventana principal
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
