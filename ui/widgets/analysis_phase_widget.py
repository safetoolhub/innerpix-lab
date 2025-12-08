"""
Widget que muestra el progreso de cada fase del análisis (STAGE 2)
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel

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
        self.phase_counters = {}  # Nuevos contadores de progreso
        self.phase_original_texts = {}  # Textos originales de cada fase
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz del widget"""
        # Sin borde, sin padding extra - solo el contenido
        self.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)  # Sin espacio entre fases para máxima compacidad
        layout.setContentsMargins(0, 0, 0, 0)  # Sin márgenes
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(DesignSystem.SPACE_6)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_icon = QLabel()
        icon_manager.set_label_icon(
            header_icon,
            'magnify',
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=14
        )
        header_layout.addWidget(header_icon)
        
        header_text = QLabel("¿Qué estamos analizando?")
        header_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        header_layout.addWidget(header_text)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addSpacing(DesignSystem.SPACE_2)  # Separador más pequeño después del header
        
        # Fases del análisis (9 fases totales)
        phases = [
            ("scan", "Escaneando archivos..."),
            ("renaming", "Analizando nombres de archivos..."),
            ("live_photos", "Buscando Live Photos..."),
            ("heic", "Buscando duplicados HEIC/JPG..."),
            ("duplicates", "Identificando copias exactas..."),
            ("duplicates_similar", "Identificando archivos similares..."),
            ("zero_byte", "Buscando archivos vacíos..."),
            ("organization", "Analizando estructura de carpetas..."),
            ("calculating_size", "Calculando tamaño del directorio..."),
            ("finalizing", "Finalizando análisis...")
        ]
        
        for phase_id, phase_text in phases:
            phase_layout = self._create_phase_item(phase_id, phase_text)
            layout.addLayout(phase_layout)
            # Guardar el texto original para poder modificarlo después
            self.phase_original_texts[phase_id] = phase_text
    
    def _create_phase_item(self, phase_id: str, text: str) -> QHBoxLayout:
        """
        Crea un item de fase con icono + texto (diseño compacto)
        
        Args:
            phase_id: ID de la fase
            text: Texto descriptivo
        
        Returns:
            Layout horizontal con el item
        """
        item_layout = QHBoxLayout()
        item_layout.setSpacing(DesignSystem.SPACE_6)  # Espacio compacto entre icono y texto
        item_layout.setContentsMargins(0, 0, 0, 0)
        
        # Icono de estado (pendiente por defecto)
        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label,
            'pause-circle',
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=12  # Icono más pequeño
        )
        self.phase_icons[phase_id] = icon_label
        item_layout.addWidget(icon_label)
        
        # Texto compacto
        text_label = QLabel(text)
        text_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            line-height: 1.0;
        """)
        self.phase_labels[phase_id] = text_label
        item_layout.addWidget(text_label)
        
        # Contador de progreso (inicialmente oculto)
        counter_label = QLabel("")
        counter_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-family: {DesignSystem.FONT_FAMILY_MONO};
            line-height: 1.0;
        """)
        counter_label.hide()  # Oculto por defecto
        self.phase_counters[phase_id] = counter_label
        item_layout.addWidget(counter_label)
        
        item_layout.addStretch()
        
        return item_layout
    
    def set_phase_status(self, phase_id: str, status: str):
        """
        Actualiza el estado visual de una fase
        
        Args:
            phase_id: ID de la fase
            status: 'pending', 'running', 'completed', 'alert-circle', 'skipped'
        """
        if phase_id not in self.phase_icons:
            return
        
        icon_label = self.phase_icons[phase_id]
        text_label = self.phase_labels[phase_id]
        counter_label = self.phase_counters[phase_id]
        
        if status == 'completed':
            icon_manager.set_label_icon(
                icon_label,
                'check-circle',
                color=DesignSystem.COLOR_SUCCESS,
                size=12
            )
            # Añadir "- OK" al texto original
            original_text = self.phase_original_texts.get(phase_id, "")
            # Remover "..." del final si existe
            if original_text.endswith("..."):
                original_text = original_text[:-3]
            text_label.setText(f"{original_text} - OK")
            text_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                color: {DesignSystem.COLOR_SUCCESS};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                line-height: 1.0;
            """)
            # Ocultar contador cuando se completa
            counter_label.hide()
        
        elif status == 'running':
            icon_manager.set_label_icon(
                icon_label,
                'progress-clock',
                color=DesignSystem.COLOR_PRIMARY,
                size=12
            )
            # Restaurar texto original sin modificación durante ejecución
            original_text = self.phase_original_texts.get(phase_id, "")
            text_label.setText(original_text)
            text_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                color: {DesignSystem.COLOR_PRIMARY};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                line-height: 1.0;
            """)
            # Mostrar contador en azul cuando está en ejecución
            counter_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_PRIMARY};
                font-family: {DesignSystem.FONT_FAMILY_MONO};
                line-height: 1.0;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            """)
            counter_label.show()
        
        elif status == 'alert-circle':
            icon_manager.set_label_icon(
                icon_label,
                'alert-circle',  # Usar 'alert-circle' que mapea a 'mdi6.alert-circle'
                color=DesignSystem.COLOR_ERROR,
                size=12
            )
            text_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                color: {DesignSystem.COLOR_ERROR};
                line-height: 1.0;
            """)
            # Ocultar contador en caso de error
            counter_label.hide()
        
        elif status == 'skipped':
            icon_manager.set_label_icon(
                icon_label,
                'close-circle',
                color=DesignSystem.COLOR_TEXT_SECONDARY,
                size=12
            )
            text_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-style: italic;
                line-height: 1.0;
            """)
            # Mostrar "No realizado" en el contador
            counter_label.setText("(se realizará más adelante)")
            counter_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-family: {DesignSystem.FONT_FAMILY_BASE};
                line-height: 1.0;
                font-style: italic;
            """)
            counter_label.show()
        
        else:  # pending
            icon_manager.set_label_icon(
                icon_label,
                'pause-circle',
                color=DesignSystem.COLOR_TEXT_SECONDARY,
                size=12
            )
            text_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                line-height: 1.0;
            """)
            # Ocultar contador cuando está pendiente
            counter_label.hide()
    
    def reset_all_phases(self):
        """Resetea todas las fases a estado pendiente"""
        for phase_id in self.phase_icons.keys():
            self.set_phase_status(phase_id, 'pending')
    
    def update_phase_progress(self, phase_id: str, current: int, total: int):
        """
        Actualiza el contador de progreso de una fase
        
        Args:
            phase_id: ID de la fase
            current: Número de archivos procesados
            total: Total de archivos
        """
        if phase_id not in self.phase_counters:
            return
        
        counter_label = self.phase_counters[phase_id]
        counter_label.setText(f"({current}/{total})")
        counter_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_PRIMARY};
            font-family: {DesignSystem.FONT_FAMILY_MONO};
            line-height: 1.0;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
    
    def update_phase_text(self, phase_id: str, text: str):
        """
        Actualiza el texto descriptivo de una fase (temporalmente)
        
        Args:
            phase_id: ID de la fase
            text: Nuevo texto a mostrar
        """
        if phase_id not in self.phase_labels:
            return
        
        text_label = self.phase_labels[phase_id]
        text_label.setText(text)
