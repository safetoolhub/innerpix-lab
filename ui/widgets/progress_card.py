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
    - Barra de progreso indeterminada (animada)
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
            'progress-clock', 
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
        
        # Barra de progreso (sin porcentaje)
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(DesignSystem.SPACE_12)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Modo indeterminado
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(DesignSystem.get_progressbar_style())
        progress_layout.addWidget(self.progress_bar, 1)
        
        layout.addLayout(progress_layout)
    
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
        
        # Detener animación de barra indeterminada
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
