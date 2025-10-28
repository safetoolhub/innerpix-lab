"""
PhotoKit Manager - Punto de entrada de la aplicación

Aplicación de gestión de archivos multimedia con normalización,
detección de Live Photos, unificación de directorios y limpieza de duplicados.
"""
import sys
import os

# Configurar Qt para evitar warnings de Wayland
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.wayland=false'

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
import config


def main():
    """Punto de entrada principal de la aplicación"""
    app = QApplication(sys.argv)

    # Configurar la aplicación
    app.setApplicationName(config.Config.APP_NAME)
    app.setApplicationVersion(config.Config.APP_VERSION)
    app.setOrganizationName("Novacode-labs")

    # Crear y mostrar ventana principal
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
