"""
Widget de card de progreso para el análisis (ESTADO 2)
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import pyqtSignal

from ui.styles.design_system import DesignSystem
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from utils.settings_manager import settings_manager
from pathlib import Path
from ui.screens.analysis_phase_widget import AnalysisPhaseWidget


class ProgressCard(QFrame):
    """
    Card que muestra el progreso del análisis de directorio
    Incluye:
    - Ruta del directorio
    - Barra de progreso indeterminada (animada)
    - Fases del análisis con indicadores de estado
    """
    
    # Señales
    cancel_requested = pyqtSignal()  # Cuando el usuario cancela el análisis
    
    def __init__(self, directory_path: str, parent=None):
        super().__init__(parent)
        self.directory_path = directory_path
        self.phase_widget = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz de la card"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        # Header unificado: Icono + "Carpeta:" + Ruta + Botón Cancelar
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
        self.path_label.setStyleSheet(f"""
            font-family: {DesignSystem.FONT_FAMILY_MONO};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        header_layout.addWidget(self.path_label)
        
        # 4. Stretch
        header_layout.addStretch()
        
        # 5. Botón cancelar (discreto, en la esquina)
        self.cancel_btn = QPushButton("Cancelar")
        icon_manager.set_button_icon(self.cancel_btn, 'close', size=14)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
            QPushButton:hover {{
                background: {DesignSystem.COLOR_BG_2};
                border-color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        header_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(header_layout)
        
        # Actualizar visualización según configuración
        self.update_path_display()
        
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
        
        # Separador antes de las fases
        phase_separator = QFrame()
        phase_separator.setFrameShape(QFrame.Shape.HLine)
        phase_separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        phase_separator.setFixedHeight(1)
        layout.addWidget(phase_separator)
        
        # Widget de fases del análisis
        self.phase_widget = AnalysisPhaseWidget()
        layout.addWidget(self.phase_widget)
    
    def mark_completed(self):
        """Marca el análisis como completado"""
        # Ocultar botón de cancelar cuando se completa
        self.cancel_btn.hide()
        
        # Cambiar icono a checkmark
        icon_manager.set_label_icon(
            self.status_icon,
            'check-circle',
            color=DesignSystem.COLOR_SUCCESS,
            size=16
        )
        
        # Cambiar texto con indicación de transición automática
        self.status_label.setText("Análisis completado - Cargando resultados...")
        self.status_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_SUCCESS};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        
        # Detener animación de barra indeterminada
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
    
    def stop_progress(self):
        """Detiene la barra de progreso (por error o cancelación)"""
        # Detener animación de barra indeterminada
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        # Mostrar botón de cancelar (por si el usuario quiere interactuar)
        self.cancel_btn.show()
    
    def get_phase_widget(self):
        """Retorna el widget de fases para acceso externo"""
        return self.phase_widget
    
    def set_phase_status(self, phase_id: str, status: str):
        """Delegar llamada al widget de fases"""
        if self.phase_widget:
            self.phase_widget.set_phase_status(phase_id, status)
    
    def update_phase_progress(self, phase_id: str, current: int, total: int):
        """Delegar actualización de progreso al widget de fases"""
        if self.phase_widget:
            self.phase_widget.update_phase_progress(phase_id, current, total)
    
    def update_phase_text(self, phase_id: str, text: str):
        """Delegar actualización de texto al widget de fases"""
        if self.phase_widget:
            self.phase_widget.update_phase_text(phase_id, text)
    
    def reset_phases(self):
        """Delegar llamada al widget de fases"""
        if self.phase_widget:
            self.phase_widget.reset_all_phases()
    
    def reset(self):
        """Resetea el estado del análisis para reinicio"""
        # Resetear barra de progreso a modo indeterminado
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(0)
        
        # Resetear icono y texto
        icon_manager.set_label_icon(
            self.status_icon,
            'progress-clock',
            color=DesignSystem.COLOR_PRIMARY,
            size=16
        )
        self.status_label.setText("Analizando tu colección...")
        self.status_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        
        # Resetear fases
        self.reset_phases()

    def update_path_display(self):
        """Actualiza la visualización de la ruta según la configuración"""
        show_full = settings_manager.get_show_full_path()
        
        if show_full:
            self.path_label.setText(self.directory_path)
        else:
            # Mostrar solo el nombre de la carpeta
            folder_name = Path(self.directory_path).name
            self.path_label.setText(folder_name)
