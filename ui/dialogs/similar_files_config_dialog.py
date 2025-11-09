"""
Diálogo de configuración para el análisis de archivos similares.
Permite ajustar la sensibilidad del análisis perceptual.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QSlider, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager


class SimilarFilesConfigDialog(QDialog):
    """
    Diálogo para configurar el análisis de archivos similares.
    
    Permite ajustar la sensibilidad (0-20) del análisis perceptual hash.
    Detecta fotos y vídeos visualmente similares: recortes, rotaciones,
    ediciones o diferentes resoluciones.
    
    Menor valor = más estricto (solo muy similares).
    Mayor valor = más permisivo (detecta más similitudes).
    """
    
    def __init__(self, parent=None, file_count: int = 0, previous_sensitivity: int = 10):
        """
        Args:
            parent: Widget padre
            file_count: Número de archivos a analizar
            previous_sensitivity: Valor de sensibilidad previo (0-20)
        """
        super().__init__(parent)
        self.file_count = file_count
        self.sensitivity_value = previous_sensitivity
        
        self._setup_ui()
        self._apply_styles()
        self._connect_signals()
    
    def _setup_ui(self):
        """Configura la interfaz del diálogo"""
        self.setWindowTitle("Configurar análisis de archivos similares")
        self.setModal(True)
        self.setFixedWidth(600)
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.CustomizeWindowHint | 
            Qt.WindowType.WindowTitleHint | 
            Qt.WindowType.WindowCloseButtonHint
        )
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(DesignSystem.SPACE_20)
        main_layout.setContentsMargins(
            DesignSystem.SPACE_24, 
            DesignSystem.SPACE_24, 
            DesignSystem.SPACE_24, 
            DesignSystem.SPACE_24
        )
        
        # Texto introductorio
        intro_label = QLabel(
            "Ajusta la sensibilidad del análisis de similitud\n"
            "para detectar imágenes parecidas:"
        )
        intro_label.setObjectName("intro_text")
        intro_label.setWordWrap(True)
        main_layout.addWidget(intro_label)
        
        # Card de configuración del slider
        config_card = self._create_slider_card()
        main_layout.addWidget(config_card)
        
        # Sección informativa
        info_section = self._create_info_section()
        main_layout.addWidget(info_section)
        
        # Separador
        separator1 = self._create_separator()
        main_layout.addWidget(separator1)
        
        # Tiempo estimado
        time_container = self._create_time_estimate()
        main_layout.addWidget(time_container)
        
        # Advertencia
        warning_container = self._create_warning()
        main_layout.addWidget(warning_container)
        
        # Separador
        separator2 = self._create_separator()
        main_layout.addWidget(separator2)
        
        # Botones
        buttons_layout = self._create_buttons()
        main_layout.addLayout(buttons_layout)
    
    def _create_slider_card(self) -> QFrame:
        """Crea la card con el slider de sensibilidad"""
        card = QFrame()
        card.setObjectName("slider_card")
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(DesignSystem.SPACE_16)
        card_layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20
        )
        
        # Título
        title = QLabel("Sensibilidad de detección")
        title.setObjectName("card_title")
        card_layout.addWidget(title)
        
        # Slider
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setMinimum(0)
        self.sensitivity_slider.setMaximum(20)
        self.sensitivity_slider.setValue(self.sensitivity_value)
        self.sensitivity_slider.setTickInterval(2)
        self.sensitivity_slider.setSingleStep(1)
        self.sensitivity_slider.setPageStep(5)
        self.sensitivity_slider.setObjectName("sensitivity_slider")
        card_layout.addWidget(self.sensitivity_slider)
        
        # Labels min/max
        labels_layout = QHBoxLayout()
        labels_layout.setSpacing(0)
        
        min_label = QLabel("Más estricto\n(0)")
        min_label.setObjectName("slider_label")
        min_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        max_label = QLabel("Más permisivo\n(20)")
        max_label.setObjectName("slider_label")
        max_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        labels_layout.addWidget(min_label)
        labels_layout.addStretch()
        labels_layout.addWidget(max_label)
        card_layout.addLayout(labels_layout)
        
        # Display del valor actual
        value_layout = QHBoxLayout()
        
        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label,
            "target",
            color=DesignSystem.COLOR_PRIMARY,
            size=16
        )
        
        self.value_display = QLabel(f"Valor seleccionado: {self.sensitivity_value}")
        self.value_display.setObjectName("value_display")
        
        value_layout.addWidget(icon_label)
        value_layout.addWidget(self.value_display)
        value_layout.addStretch()
        
        card_layout.addLayout(value_layout)
        
        return card
    
    def _create_info_section(self) -> QFrame:
        """Crea la sección informativa"""
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(DesignSystem.SPACE_12)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Título con icono
        title_layout = QHBoxLayout()
        
        info_icon = QLabel()
        icon_manager.set_label_icon(
            info_icon,
            "info",
            color=DesignSystem.COLOR_PRIMARY,
            size=18
        )
        
        title = QLabel("¿Qué significa esto?")
        title.setObjectName("info_title")
        
        title_layout.addWidget(info_icon)
        title_layout.addWidget(title)
        title_layout.addStretch()
        info_layout.addLayout(title_layout)
        
        # Explicaciones
        explanations = [
            "• 0-5: Detecta solo imágenes muy similares\n"
            "  (mismo objeto, ángulos ligeramente diferentes)",
            
            "• 5-15: Balance recomendado (predeterminado: 10)\n"
            "  Detecta recortes, rotaciones, ajustes de color",
            
            "• 15-20: Detecta similitudes más amplias\n"
            "  (misma escena, objetos o sujetos parecidos)"
        ]
        
        for explanation in explanations:
            label = QLabel(explanation)
            label.setObjectName("explanation_text")
            label.setWordWrap(True)
            info_layout.addWidget(label)
        
        return info_frame
    
    def _create_time_estimate(self) -> QFrame:
        """Crea el contenedor de tiempo estimado"""
        container = QFrame()
        container.setObjectName("time_container")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12
        )
        layout.setSpacing(DesignSystem.SPACE_8)
        
        icon = QLabel()
        icon_manager.set_label_icon(
            icon,
            "clock",
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=16
        )
        
        # Estimar tiempo: aproximadamente 1 minuto por cada 500 archivos
        estimated_minutes = max(1, self.file_count // 500)
        time_text = QLabel(
            f"Tiempo estimado: ~{estimated_minutes}-{estimated_minutes + 1} min "
            f"({self.file_count:,} archivos)"
        )
        time_text.setObjectName("time_text")
        
        layout.addWidget(icon)
        layout.addWidget(time_text)
        layout.addStretch()
        
        return container
    
    def _create_warning(self) -> QFrame:
        """Crea el contenedor de advertencia"""
        container = QFrame()
        container.setObjectName("warning_container")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12
        )
        layout.setSpacing(DesignSystem.SPACE_8)
        
        icon = QLabel()
        icon_manager.set_label_icon(
            icon,
            "error",
            color=DesignSystem.COLOR_WARNING,
            size=16
        )
        
        warning_text = QLabel(
            "El análisis se ejecutará en modo bloqueante.\n"
            "No podrás usar la aplicación hasta que termine."
        )
        warning_text.setObjectName("warning_text")
        warning_text.setWordWrap(True)
        
        layout.addWidget(icon)
        layout.addWidget(warning_text)
        
        return container
    
    def _create_separator(self) -> QFrame:
        """Crea un separador horizontal"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        return separator
    
    def _create_buttons(self) -> QHBoxLayout:
        """Crea los botones de acción"""
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        # Botón Cancelar
        cancel_button = QPushButton("Cancelar")
        cancel_button.setObjectName("cancel_button")
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)
        
        # Botón Iniciar análisis
        start_button = QPushButton("Iniciar análisis")
        start_icon_label = QLabel()
        icon_manager.set_label_icon(
            start_icon_label,
            "play-circle",
            color=DesignSystem.COLOR_PRIMARY_TEXT,
            size=16
        )
        start_button.setObjectName("start_button")
        start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        start_button.clicked.connect(self.accept)
        
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(start_button)
        
        return buttons_layout
    
    def _connect_signals(self):
        """Conecta las señales"""
        self.sensitivity_slider.valueChanged.connect(self._on_slider_changed)
    
    def _on_slider_changed(self, value: int):
        """Actualiza el display cuando cambia el slider"""
        self.sensitivity_value = value
        self.value_display.setText(f"Valor seleccionado: {value}")
    
    def get_sensitivity_value(self) -> int:
        """Retorna el valor de sensibilidad seleccionado (0-20)"""
        return self.sensitivity_value
    
    def _apply_styles(self):
        """Aplica estilos siguiendo el DesignSystem"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            
            QLabel#intro_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                line-height: {DesignSystem.LINE_HEIGHT_RELAXED};
            }}
            
            QFrame#slider_card {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
            
            QLabel#card_title {{
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QSlider#sensitivity_slider {{
                min-height: 30px;
            }}
            
            QSlider#sensitivity_slider::groove:horizontal {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                height: 6px;
                background: {DesignSystem.COLOR_BG_2};
                border-radius: 3px;
            }}
            
            QSlider#sensitivity_slider::handle:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border: 2px solid {DesignSystem.COLOR_SURFACE};
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }}
            
            QSlider#sensitivity_slider::handle:horizontal:hover {{
                background: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            
            QSlider#sensitivity_slider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 3px;
            }}
            
            QLabel#slider_label {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QLabel#value_display {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                color: {DesignSystem.COLOR_PRIMARY};
            }}
            
            QLabel#info_title {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QLabel#explanation_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                line-height: {DesignSystem.LINE_HEIGHT_RELAXED};
            }}
            
            QFrame#time_container {{
                background-color: {DesignSystem.COLOR_BG_1};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            
            QLabel#time_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QFrame#warning_container {{
                background-color: {DesignSystem.COLOR_BG_4};
                border: 1px solid {DesignSystem.COLOR_WARNING};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            
            QLabel#warning_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QFrame#separator {{
                background-color: {DesignSystem.COLOR_BORDER};
                max-height: 1px;
            }}
            
            QPushButton#cancel_button {{
                background-color: transparent;
                border: 2px solid {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_24}px;
                border-radius: {DesignSystem.RADIUS_FULL}px;
                min-width: 100px;
            }}
            
            QPushButton#cancel_button:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY};
            }}
            
            QPushButton#start_button {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                border: none;
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_24}px;
                border-radius: {DesignSystem.RADIUS_FULL}px;
                min-width: 140px;
            }}
            
            QPushButton#start_button:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
        """)
