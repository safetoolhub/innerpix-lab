from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFrame
from PyQt5.QtCore import Qt

import config
from ui import styles


class SearchBar(QWidget):
    """Componente Search Bar que contiene el icono de carpeta, el campo de
    directorio y el botón principal de analizar. Provee `add_actions_widget`
    para inyectar un contenedor de acciones desde la ventana principal.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # Usar QFrame-like container visual para replicar el estilo original
        self.container = QFrame(self)
        self.container.setStyleSheet(styles.STYLE_SEARCH_CONTAINER)

        self.layout = QHBoxLayout(self.container)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(14, 10, 10, 10)

        folder_icon = QLabel("📂")
        folder_icon.setStyleSheet(styles.STYLE_FOLDER_ICON)
        self.layout.addWidget(folder_icon)

        self.directory_edit = QLineEdit()
        self.directory_edit.setPlaceholderText("Selecciona un directorio para analizar...")
        self.directory_edit.setReadOnly(True)
        self.directory_edit.setStyleSheet(styles.STYLE_DIRECTORY_EDIT_READONLY)
        self.layout.addWidget(self.directory_edit, stretch=1)

        self.analyze_btn = QPushButton("📁 Seleccionar y Analizar")
        self.analyze_btn.setMinimumWidth(200)
        self.analyze_btn.setFixedHeight(42)
        self.analyze_btn.setStyleSheet(styles.STYLE_ANALYZE_BUTTON_PRIMARY)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)

        # Conectar al método del MainWindow si existe
        if self.main_window is not None and hasattr(self.main_window, 'select_and_analyze_directory'):
            try:
                self.analyze_btn.clicked.connect(self.main_window.select_and_analyze_directory)
            except Exception:
                pass

        self.layout.addWidget(self.analyze_btn)

        # Hacer que el widget del SearchBar contenga el frame
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.container)

    def add_actions_widget(self, widget):
        """Añade un widget (por ejemplo `actions_container`) al final del layout."""
        # Insertar al final del layout
        self.layout.addWidget(widget)
