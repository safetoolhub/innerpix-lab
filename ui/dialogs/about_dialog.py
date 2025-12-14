from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QWidget
)
from PyQt6.QtCore import Qt
from config import Config
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager


class AboutDialog(QDialog):
    """Diálogo 'Acerca de' compacto y consistente con DesignSystem"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Acerca de {Config.APP_NAME}")
        self.setModal(True)
        self.setFixedSize(520, 540)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === HEADER ===
        header = QFrame()
        header.setStyleSheet(
            f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {DesignSystem.COLOR_PRIMARY}, stop:1 {DesignSystem.COLOR_PRIMARY_HOVER});
                border-top-left-radius: {DesignSystem.RADIUS_LG}px;
                border-top-right-radius: {DesignSystem.RADIUS_LG}px;
            }}
            """
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 18, 20, 18)
        header_layout.setSpacing(6)

        # Título
        title = QLabel(Config.APP_NAME)
        title.setProperty("class", "title")
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        # Versión
        version = QLabel(f"Versión {Config.APP_VERSION}")
        version.setStyleSheet(f"color: rgba(255, 255, 255, 0.95); font-size: {DesignSystem.FONT_SIZE_SM}px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(version)

        main_layout.addWidget(header)

        # === CONTENIDO ===
        content = QFrame()
        content.setProperty("class", "card")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(12)

        # Descripción
        description = QLabel(Config.APP_DESCRIPTION)
        description.setProperty("class", "secondary")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        content_layout.addWidget(description)

        # Separador
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        line1.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER}; height: 1px;")
        content_layout.addWidget(line1)

        # Título de herramientas
        tools_title = QLabel("Herramientas")
        tools_title.setProperty("class", "header")
        content_layout.addWidget(tools_title)

        # Grid de herramientas
        tools_grid = QGridLayout()
        tools_grid.setHorizontalSpacing(15)
        tools_grid.setVerticalSpacing(12)
        tools_grid.setContentsMargins(5, 5, 5, 5)

        tools = [
            ("camera-burst", "Live Photos"),
            ("file-image", "HEIC/JPG Duplicados"),
            ("content-copy", "Copias exactas"),
            ("image-search", "Archivos similares"),
            ("folder-move", "Organizar Archivos"),
            ("rename-box", "Renombrar Archivos"),
            ("trash-alt", "Archivos Vacíos"),
        ]

        for i, (icon_name, name) in enumerate(tools):
            row = i // 2
            col = i % 2

            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(4, 4, 4, 4)
            h.setSpacing(8)

            icon_label = QLabel()
            icon_manager.set_label_icon(icon_label, icon_name, color=DesignSystem.COLOR_TEXT_SECONDARY, size=16)
            h.addWidget(icon_label)

            name_label = QLabel(name)
            name_label.setProperty("class", "small")
            h.addWidget(name_label)

            tools_grid.addWidget(container, row, col)

        content_layout.addLayout(tools_grid)

        # Funcionalidades adicionales (Backups y Logs)
        additional_layout = QHBoxLayout()
        additional_layout.setSpacing(20)
        additional_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        additional_layout.setContentsMargins(0, 8, 0, 0)

        # Backups
        backup_container = QWidget()
        backup_h = QHBoxLayout(backup_container)
        backup_h.setContentsMargins(0, 0, 0, 0)
        backup_h.setSpacing(6)
        backup_icon = QLabel()
        icon_manager.set_label_icon(backup_icon, "backup-restore", color=DesignSystem.COLOR_TEXT_SECONDARY, size=14)
        backup_label = QLabel("Backups Automáticos")
        backup_label.setProperty("class", "small")
        backup_label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        backup_h.addWidget(backup_icon)
        backup_h.addWidget(backup_label)

        # Logs
        logs_container = QWidget()
        logs_h = QHBoxLayout(logs_container)
        logs_h.setContentsMargins(0, 0, 0, 0)
        logs_h.setSpacing(6)
        logs_icon = QLabel()
        icon_manager.set_label_icon(logs_icon, "history", color=DesignSystem.COLOR_TEXT_SECONDARY, size=14)
        logs_label = QLabel("Registros de Operaciones")
        logs_label.setProperty("class", "small")
        logs_label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        logs_h.addWidget(logs_icon)
        logs_h.addWidget(logs_label)

        additional_layout.addWidget(backup_container)
        additional_layout.addWidget(logs_container)
        
        content_layout.addLayout(additional_layout)

        # Separador
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        line2.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER}; height: 1px;")
        content_layout.addWidget(line2)

        # Info técnica
        tech_info = QLabel("Tecnología: PyQt6 • Python 3.x • Multiplataforma")
        tech_info.setProperty("class", "small")
        tech_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(tech_info)

        # Créditos
        credits = QLabel("Desarrollado con dedicación para simplificar la gestión de fotos")
        credits.setProperty("class", "small")
        credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(credits)

        main_layout.addWidget(content)

        # === FOOTER ===
        footer = QFrame()
        footer.setProperty("class", "card")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 16, 8)

        footer_layout.addStretch()

        # Botón cerrar con estilo Material Design
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(close_btn)

        footer_layout.addStretch()

        main_layout.addWidget(footer)
