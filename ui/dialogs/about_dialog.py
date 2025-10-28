from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
import config


class AboutDialog(QDialog):
    """Diálogo 'Acerca de' extraído de `main_window.py`."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Acerca de")
        self.setModal(True)
        self.resize(520, 360)

        layout = QVBoxLayout(self)

        about_text = f"""
        <center>
        <h2>{config.config.APP_NAME}</h2>
        <p><b>Versión:</b> {config.config.APP_VERSION}</p>
        <p>{config.config.APP_DESCRIPTION}</p>
        <br>
        <p><b>Funcionalidades:</b></p>
        <ul style=\"text-align: left;\">
            <li>📝 Renombrado automático de archivos</li>
            <li>📱 Limpieza de Live Photos</li>
            <li>📁 Unificación de directorios</li>
            <li>🖼️ Eliminación de duplicados HEIC/JPG</li>
        </ul>
        <br>
        <p><small>Desarrollado con ❤️ usando PyQt5</small></p>
        </center>
        """

        label = QLabel()
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setText(about_text)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Botón de cerrar
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
