from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QMenu
from PyQt6.QtCore import Qt

import config
from ui import styles


class Header(QWidget):
    """Componente Header para la ventana principal.

    Construye el título y el botón de menú que delega acciones al
    `MainWindow` padre (toggle_config, show_about_dialog).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        layout = QHBoxLayout(self)

        # Título
        title = QLabel(f"🎬 {config.config.APP_NAME}")
        title.setStyleSheet(styles.STYLE_TITLE_LABEL)
        layout.addWidget(title)

        layout.addStretch()

        # Botón de menú con dropdown
        menu_btn = QPushButton("⋮")
        menu_btn.setFixedSize(40, 40)
        menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        menu_btn.setToolTip("Menú de opciones")
        menu_btn.setStyleSheet(styles.STYLE_MENU_BUTTON)

        # Crear menú desplegable
        menu = QMenu(self)
        menu.setStyleSheet(styles.STYLE_MENU)

        # Añadir acciones al menú
        config_action = menu.addAction("⚙️  Configuración")
        # delegar al MainWindow
        if self.main_window is not None:
            config_action.triggered.connect(self.main_window.toggle_config)

        menu.addSeparator()

        about_action = menu.addAction("ℹ️  Acerca de")
        if self.main_window is not None:
            about_action.triggered.connect(self.main_window.show_about_dialog)

        # Asignar menú al botón
        menu_btn.setMenu(menu)

        layout.addWidget(menu_btn)
