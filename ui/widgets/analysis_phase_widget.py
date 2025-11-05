"""
Widget que muestra el progreso de cada fase del análisis (ESTADO 2)
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager


class AnalysisPhaseWidget(QFrame):
    """
    Card que muestra las diferentes fases del análisis
    con indicadores de estado:
    - ✓ Completado
    - ⏳ En proceso
    - ⏸ Pendiente
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase_labels = {}
        self.phase_icons = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz del widget"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_20}px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(DesignSystem.SPACE_8)
        
        header_icon = QLabel()
        icon_manager.set_label_icon(
            header_icon,
            'magnify',
            color=DesignSystem.COLOR_TEXT,
            size=16
        )
        header_layout.addWidget(header_icon)
        
        header_text = QLabel("¿Qué estamos analizando?")
        header_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """)
        header_layout.addWidget(header_text)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Fases del análisis
        phases = [
            ("live_photos", "Detectando Live Photos..."),
            ("heic", "Buscando duplicados HEIC/JPG..."),
            ("duplicates", "Identificando duplicados exactos..."),
            ("similar", "Duplicados similares (puedes hacerlo después)")
        ]
        
        for phase_id, phase_text in phases:
            phase_layout = self._create_phase_item(phase_id, phase_text)
            layout.addLayout(phase_layout)
    
    def _create_phase_item(self, phase_id: str, text: str) -> QHBoxLayout:
        """
        Crea un item de fase con icono + texto
        
        Args:
            phase_id: ID de la fase
            text: Texto descriptivo
        
        Returns:
            Layout horizontal con el item
        """
        item_layout = QHBoxLayout()
        item_layout.setSpacing(DesignSystem.SPACE_8)
        
        # Icono de estado (pendiente por defecto)
        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label,
            'pause-circle',
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=14
        )
        self.phase_icons[phase_id] = icon_label
        item_layout.addWidget(icon_label)
        
        # Texto
        text_label = QLabel(text)
        text_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        self.phase_labels[phase_id] = text_label
        item_layout.addWidget(text_label)
        
        item_layout.addStretch()
        
        return item_layout
    
    def set_phase_status(self, phase_id: str, status: str):
        """
        Actualiza el estado visual de una fase
        
        Args:
            phase_id: ID de la fase
            status: 'pending', 'running', 'completed'
        """
        if phase_id not in self.phase_icons:
            return
        
        icon_label = self.phase_icons[phase_id]
        text_label = self.phase_labels[phase_id]
        
        if status == 'completed':
            icon_manager.set_label_icon(
                icon_label,
                'check-circle',
                color=DesignSystem.COLOR_SUCCESS,
                size=14
            )
            text_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT};
            """)
        
        elif status == 'running':
            icon_manager.set_label_icon(
                icon_label,
                'loading',
                color=DesignSystem.COLOR_WARNING,
                size=14
            )
            text_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            """)
        
        else:  # pending
            icon_manager.set_label_icon(
                icon_label,
                'pause-circle',
                color=DesignSystem.COLOR_TEXT_SECONDARY,
                size=14
            )
            text_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            """)
