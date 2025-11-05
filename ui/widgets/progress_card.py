"""
Widget de card de progreso para el análisis (ESTADO 2)
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager


class ProgressCard(QFrame):
    """
    Card que muestra el progreso del análisis de directorio
    Incluye:
    - Ruta del directorio
    - Barra de progreso con porcentaje
    - Estadísticas en tiempo real
    """
    
    # Señales
    cancel_requested = pyqtSignal()  # Cuando el usuario cancela el análisis
    
    def __init__(self, directory_path: str, parent=None):
        super().__init__(parent)
        self.directory_path = directory_path
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
        
        # Header con icono folder
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
        
        header_text = QLabel("Directorio seleccionado")
        header_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """)
        header_layout.addWidget(header_text)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Ruta del directorio (mono)
        self.path_label = QLabel(self.directory_path)
        self.path_label.setProperty("class", "mono")
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Estado: "Analizando tu colección..."
        status_layout = QHBoxLayout()
        status_layout.setSpacing(DesignSystem.SPACE_8)
        
        self.status_icon = QLabel()
        icon_manager.set_label_icon(
            self.status_icon, 
            'loading', 
            color=DesignSystem.COLOR_PRIMARY, 
            size=16
        )
        status_layout.addWidget(self.status_icon)
        
        self.status_label = QLabel("Analizando tu colección...")
        self.status_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
        
        # Barra de progreso + porcentaje
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(DesignSystem.SPACE_12)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(DesignSystem.get_progressbar_style())
        progress_layout.addWidget(self.progress_bar, 1)
        
        self.percentage_label = QLabel("0%")
        self.percentage_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        progress_layout.addWidget(self.percentage_label)
        
        layout.addLayout(progress_layout)
        
        # Estadísticas en tiempo real
        self.stats_label = QLabel("Iniciando análisis...")
        self.stats_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(self.stats_label)
    
    def update_progress(self, current: int, total: int, percentage: int):
        """
        Actualiza la barra de progreso
        
        Args:
            current: Archivos analizados
            total: Total de archivos
            percentage: Porcentaje (0-100)
        """
        self.progress_bar.setValue(percentage)
        self.percentage_label.setText(f"{percentage}%")
    
    def update_stats(self, stats_text: str):
        """
        Actualiza el texto de estadísticas
        
        Args:
            stats_text: Texto formateado con stats (ej: "1,924 de 2,847 archivos • 10.3 GB")
        """
        # Agregar icono de estadísticas al principio si no está
        if not stats_text.startswith("📊"):
            stats_text = f"📊 {stats_text}"
        self.stats_label.setText(stats_text)
    
    def update_status(self, status_text: str):
        """
        Actualiza el texto de estado
        
        Args:
            status_text: Nuevo estado (ej: "Analizando imágenes...")
        """
        self.status_label.setText(status_text)
    
    def mark_completed(self):
        """Marca el análisis como completado"""
        # Cambiar icono a checkmark
        icon_manager.set_label_icon(
            self.status_icon,
            'check-circle',
            color=DesignSystem.COLOR_SUCCESS,
            size=16
        )
        
        # Cambiar texto
        self.status_label.setText("Análisis completado")
        self.status_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_SUCCESS};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        
        # Barra al 100%
        self.progress_bar.setValue(100)
        self.percentage_label.setText("100%")
