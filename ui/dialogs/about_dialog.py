from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from config import Config


class AboutDialog(QDialog):
    """Diálogo 'Acerca de' compacto y profesional"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Acerca de {Config.APP_NAME}")
        self.setModal(True)
        self.setFixedSize(520, 480)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === HEADER ===
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1976D2, stop:1 #2196F3);
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 25, 20, 25)
        header_layout.setSpacing(8)

        # Título
        title = QLabel(Config.APP_NAME)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        # Versión
        version = QLabel(f"Versión {Config.APP_VERSION}")
        version.setStyleSheet("color: rgba(255, 255, 255, 0.95); font-size: 13px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(version)

        main_layout.addWidget(header)

        # === CONTENIDO ===
        content = QFrame()
        from ui import styles as ui_styles
        content.setStyleSheet(ui_styles.STYLE_ABOUT_CONTENT_BG)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(25, 20, 25, 20)
        content_layout.setSpacing(15)

        # Descripción
        description = QLabel(Config.APP_DESCRIPTION)
        description.setStyleSheet(ui_styles.STYLE_ABOUT_DESCRIPTION)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        content_layout.addWidget(description)

        # Separador
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        line1.setStyleSheet(ui_styles.STYLE_ABOUT_LINE)
        content_layout.addWidget(line1)

        # Título de herramientas
        tools_title = QLabel("<b>🛠️ Herramientas</b>")
        tools_title.setStyleSheet(ui_styles.STYLE_ABOUT_TOOLS_TITLE)
        content_layout.addWidget(tools_title)

        # Grid de herramientas
        tools_grid = QGridLayout()
        tools_grid.setHorizontalSpacing(15)
        tools_grid.setVerticalSpacing(10)
        tools_grid.setContentsMargins(5, 5, 5, 5)

        tools = [
            ("📝", "Renombrado Inteligente"),
            ("📱", "Gestión de Live Photos"),
            ("📁", "Organización de Directorios"),
            ("🖼️", "Limpieza HEIC/JPG"),
            ("🔍", "Detección de Duplicados"),
            ("💾", "Backups Automáticos"),
        ]

        for i, (icon, name) in enumerate(tools):
            row = i // 2
            col = i % 2
            
            tool_widget = QLabel(f"{icon}  {name}")
            tool_widget.setStyleSheet(ui_styles.STYLE_ABOUT_TOOL_WIDGET)
            tools_grid.addWidget(tool_widget, row, col)

        content_layout.addLayout(tools_grid)

        # Separador
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        line2.setStyleSheet(ui_styles.STYLE_ABOUT_LINE)
        content_layout.addWidget(line2)

        # Info técnica
        tech_info = QLabel("💻 <b>Tecnología:</b> PyQt6 • Python 3.x • Multiplataforma")
        tech_info.setStyleSheet(ui_styles.STYLE_ABOUT_TECH_INFO)
        tech_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(tech_info)

        # Créditos
        credits = QLabel("Desarrollado con ❤️ para simplificar la gestión de fotos")
        credits.setStyleSheet(ui_styles.STYLE_ABOUT_CREDITS)
        credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(credits)

        main_layout.addWidget(content)

        # === FOOTER ===
        footer = QFrame()
        footer.setStyleSheet(ui_styles.STYLE_ABOUT_FOOTER)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 12, 20, 12)

        footer_layout.addStretch()

        # Botón cerrar
        close_btn = QPushButton("✓ Cerrar")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                padding: 10px 35px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(close_btn)

        footer_layout.addStretch()

        main_layout.addWidget(footer)
