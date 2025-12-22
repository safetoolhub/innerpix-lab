"""
Widget de Summary Card - Resumen del directorio analizado (ESTADO 3)
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from ui.styles.design_system import DesignSystem
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from utils.settings_manager import settings_manager
from pathlib import Path


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
        self.num_images = 0
        self.num_videos = 0
        self.num_others = 0
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz de la card"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_6)
        
        # Header unificado: Icono + "Carpeta:" + Ruta + Botón "Cambiar"
        header_layout = QHBoxLayout()
        header_layout.setSpacing(DesignSystem.SPACE_8)
        
        # 1. Icono
        header_icon = QLabel()
        icon_manager.set_label_icon(
            header_icon,
            'folder-open',
            color=DesignSystem.COLOR_TEXT,
            size=16
        )
        header_layout.addWidget(header_icon)
        
        # 2. Etiqueta "Carpeta:"
        header_text = QLabel("Carpeta:")
        header_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        header_layout.addWidget(header_text)
        
        # 3. Ruta del directorio (mono)
        self.path_label = QLabel(self.directory_path)
        self.path_label.setProperty("class", "mono")
        self.path_label.setToolTip(self.directory_path)
        # Estilo específico para que se vea bien en línea
        self.path_label.setStyleSheet(f"""
            font-family: {DesignSystem.FONT_FAMILY_MONO};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        header_layout.addWidget(self.path_label)
        
        # 4. Espaciador
        header_layout.addStretch()
        
        # 5. Botón "Cambiar"
        btn_change = QPushButton("Cambiar")
        btn_change.setProperty("class", "secondary-small")
        btn_change.setToolTip("Seleccionar otra carpeta")
        btn_change.clicked.connect(self._on_change_clicked)
        header_layout.addWidget(btn_change)
        
        layout.addLayout(header_layout)
        
        # Actualizar visualización según configuración
        self.update_path_display()
        
        # Línea única: Estadísticas completas + Botón Reanalizar
        info_layout = QHBoxLayout()
        info_layout.setSpacing(DesignSystem.SPACE_8)
        
        # 0. Icono estadísticas
        stats_icon = QLabel()
        icon_manager.set_label_icon(
            stats_icon,
            'chart-bar',
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=16
        )
        info_layout.addWidget(stats_icon)
        
        # 1. Estadísticas (Archivos totales y Tamaño)
        self.stats_label = QLabel("Calculando...")
        self.stats_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        info_layout.addWidget(self.stats_label)
        
        # 2. Separador vertical
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER}; margin: 4px 0;")
        separator1.setFixedWidth(1)
        info_layout.addWidget(separator1)
        
        # 3. Desglose de tipos de archivo
        self.breakdown_label = QLabel("...")
        self.breakdown_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        info_layout.addWidget(self.breakdown_label)
        
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
    
    def update_stats(self, total_files: int, total_size: int = 0, num_images: int = 0, num_videos: int = 0, num_others: int = 0):
        """
        Actualiza las estadísticas mostradas
        
        Args:
            total_files: Número total de archivos
            total_size: Tamaño total en bytes
            num_images: Número de imágenes
            num_videos: Número de videos
            num_others: Número de archivos no soportados
        """
        self.total_files = total_files
        self.total_size = total_size
        self.num_images = num_images
        self.num_videos = num_videos
        self.num_others = num_others
        
        # Formatear estadísticas
        from utils.format_utils import format_file_count, format_size
        
        # Asegurar que total_size no sea None
        size_value = total_size if total_size is not None else 0
        stats_text = f"{format_file_count(total_files)} archivos • {format_size(size_value)}"
        
        self.stats_label.setText(stats_text)
        
        # Actualizar desglose de tipos
        breakdown_parts = []
        if num_images > 0:
            breakdown_parts.append(f"{format_file_count(num_images)} imágenes")
        if num_videos > 0:
            breakdown_parts.append(f"{format_file_count(num_videos)} videos")
        if num_others > 0:
            breakdown_parts.append(f"{format_file_count(num_others)} ficheros no soportados")
        
        if breakdown_parts:
            self.breakdown_label.setText(" • ".join(breakdown_parts))
        else:
            self.breakdown_label.setText("No hay archivos para mostrar")
    

    
    def _on_change_clicked(self):
        """Maneja el clic en "Cambiar..." """
        self.change_folder_requested.emit()
    
    def _on_reanalyze_clicked(self):
        """Maneja el clic en "Reanalizar" """
        self.reanalyze_requested.emit()

    def update_path_display(self):
        """Actualiza la visualización de la ruta según la configuración"""
        show_full = settings_manager.get_show_full_path()
        
        if show_full:
            self.path_label.setText(self.directory_path)
        else:
            # Mostrar solo el nombre de la carpeta
            folder_name = Path(self.directory_path).name
            self.path_label.setText(folder_name)
