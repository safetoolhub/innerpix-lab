"""
Widget de Summary Card - Resumen del directorio analizado (ESTADO 3)
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager


class SummaryCard(QFrame):
    """
    Card compacta que muestra el resumen del análisis completado
    
    Incluye:
    - Header con icono de carpeta
    - Ruta del directorio + botón "Cambiar..."
    - Estadísticas: archivos totales, tamaño, etc.
    - Espacio optimizable + botón "Reanalizar"
    """
    
    # Señales
    change_folder_requested = pyqtSignal()  # Cuando se hace clic en "Cambiar..."
    reanalyze_requested = pyqtSignal()  # Cuando se hace clic en "Reanalizar"
    
    def __init__(self, directory_path: str, parent=None):
        super().__init__(parent)
        self.directory_path = directory_path
        self.total_files = 0
        self.total_size = 0
        self.recoverable_space = 0
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz de la card"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_20}px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        # Header: Icono + Título + Botón "Cambiar..."
        header_layout = QHBoxLayout()
        header_layout.setSpacing(DesignSystem.SPACE_8)
        
        header_icon = QLabel()
        icon_manager.set_label_icon(
            header_icon,
            'folder-open',
            color=DesignSystem.COLOR_TEXT,
            size=16
        )
        header_layout.addWidget(header_icon)
        
        header_text = QLabel("Carpeta analizada")
        header_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """)
        header_layout.addWidget(header_text)
        header_layout.addStretch()
        
        # Botón "Cambiar..."
        btn_change = QPushButton("Cambiar...")
        btn_change.setProperty("class", "secondary-small")
        btn_change.setToolTip("Seleccionar otra carpeta")
        btn_change.clicked.connect(self._on_change_clicked)
        header_layout.addWidget(btn_change)
        
        layout.addLayout(header_layout)
        
        # Ruta del directorio (mono)
        self.path_label = QLabel(self.directory_path)
        self.path_label.setProperty("class", "mono")
        self.path_label.setWordWrap(True)
        self.path_label.setToolTip(self.directory_path)
        layout.addWidget(self.path_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Línea única: Análisis completado + Espacio optimizable + Botón Reanalizar
        info_layout = QHBoxLayout()
        info_layout.setSpacing(DesignSystem.SPACE_8)
        
        # Icono check
        check_icon = QLabel()
        icon_manager.set_label_icon(
            check_icon,
            'check-circle',
            color=DesignSystem.COLOR_SUCCESS,
            size=16
        )
        info_layout.addWidget(check_icon)
        
        # Estadísticas del análisis
        self.stats_label = QLabel("Análisis completado")
        self.stats_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        info_layout.addWidget(self.stats_label)
        
        
        # Icono disco
        disk_icon = QLabel()
        icon_manager.set_label_icon(
            disk_icon,
            'disk',
            color=DesignSystem.COLOR_TEXT,
            size=16
        )
        info_layout.addWidget(disk_icon)
        
        # Espacio optimizable
        self.space_label = QLabel("Espacio optimizable: calculando...")
        self.space_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        info_layout.addWidget(self.space_label)
        
        info_layout.addStretch()
        
        # Botón "Reanalizar"
        btn_reanalyze = QPushButton()
        icon_manager.set_button_icon(
            btn_reanalyze,
            'refresh',
            color=DesignSystem.COLOR_TEXT,
            size=16
        )
        btn_reanalyze.setText("Reanalizar")
        btn_reanalyze.setProperty("class", "secondary-small")
        btn_reanalyze.setToolTip("Volver a analizar la carpeta")
        btn_reanalyze.clicked.connect(self._on_reanalyze_clicked)
        info_layout.addWidget(btn_reanalyze)
        
        layout.addLayout(info_layout)
    
    def update_stats(self, total_files: int, total_size: int = 0):
        """
        Actualiza las estadísticas mostradas
        
        Args:
            total_files: Número total de archivos
            total_size: Tamaño total en bytes
        """
        self.total_files = total_files
        self.total_size = total_size
        
        # Formatear estadísticas
        from utils.format_utils import format_file_count, format_size
        
        stats_text = f"Análisis completado • {format_file_count(total_files)} archivos"
        if total_size > 0:
            stats_text += f" • {format_size(total_size)}"
        
        self.stats_label.setText(stats_text)
    
    def update_recoverable_space(self, recoverable_bytes: int):
        """
        Actualiza el espacio recuperable
        
        Args:
            recoverable_bytes: Espacio recuperable en bytes
        """
        self.recoverable_space = recoverable_bytes
        
        from utils.format_utils import format_size
        
        if recoverable_bytes > 0 and self.total_size > 0:
            percentage = int((recoverable_bytes / self.total_size) * 100)
            space_text = f"Espacio optimizable: ~{format_size(recoverable_bytes)} ({percentage}%)"
        elif recoverable_bytes > 0:
            space_text = f"Espacio optimizable: ~{format_size(recoverable_bytes)}"
        else:
            space_text = "No hay espacio optimizable detectado"
        
        self.space_label.setText(space_text)
    
    def _on_change_clicked(self):
        """Maneja el clic en "Cambiar..." """
        self.change_folder_requested.emit()
    
    def _on_reanalyze_clicked(self):
        """Maneja el clic en "Reanalizar" """
        self.reanalyze_requested.emit()
