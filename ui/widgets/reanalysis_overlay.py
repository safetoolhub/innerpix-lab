"""
Overlay de re-análisis para Pixaro Lab.

Muestra un overlay semi-transparente sobre el Stage 3 durante el re-análisis
automático de las herramientas rápidas (Live Photos, HEIC, Copias Exactas,
Organizar, Renombrar).

Este widget:
- Es no-modal: el usuario puede seguir viendo el Stage 3 debajo
- Muestra qué herramienta se está analizando actualmente
- Tiene animaciones de fade in/out
- Usa 100% DesignSystem para styling
"""

from typing import Optional

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QWidget,
)

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from utils.logger import get_logger


class ReanalysisOverlay(QFrame):
    """
    Overlay semi-transparente que muestra el progreso del re-análisis.
    
    El overlay se posiciona sobre el Stage 3 y muestra:
    - Título: "Actualizando análisis..."
    - Herramienta actual con icono
    - Barra de progreso (5 herramientas)
    - Botón para cancelar (opcional)
    
    Signals:
        cancel_requested: Usuario solicitó cancelar el re-análisis
    """
    
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.logger = get_logger('ReanalysisOverlay')
        
        # Estado
        self._current_tool = ""
        self._total_tools = 5
        self._completed_tools = 0
        
        # Configuración básica
        self.setObjectName("reanalysisOverlay")
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Styling: fondo semi-transparente oscuro
        self.setStyleSheet(f"""
            QFrame#reanalysisOverlay {{
                background-color: {DesignSystem.COLOR_BACKGROUND_OVERLAY};
                border-radius: {DesignSystem.RADIUS_LARGE}px;
            }}
        """)
        
        # Inicialmente oculto
        self.setVisible(False)
        self.setWindowOpacity(0.0)
        
        # Animación de fade
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(300)  # 300ms fade
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz del overlay."""
        # Layout principal con padding
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            DesignSystem.SPACE_XL,
            DesignSystem.SPACE_XL,
            DesignSystem.SPACE_XL,
            DesignSystem.SPACE_XL,
        )
        main_layout.setSpacing(DesignSystem.SPACE_LG)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Card contenedor
        card = QFrame()
        card.setObjectName("reanalysisCard")
        card.setFixedWidth(500)
        card.setStyleSheet(f"""
            QFrame#reanalysisCard {{
                background-color: {DesignSystem.COLOR_BACKGROUND_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_MEDIUM}px;
                padding: {DesignSystem.SPACE_LG}px;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            DesignSystem.SPACE_LG,
            DesignSystem.SPACE_LG,
            DesignSystem.SPACE_LG,
            DesignSystem.SPACE_LG,
        )
        card_layout.setSpacing(DesignSystem.SPACE_MD)
        
        # Título con icono
        title_container = QHBoxLayout()
        title_container.setSpacing(DesignSystem.SPACE_SM)
        
        self._title_icon = QLabel()
        icon_manager.set_label_icon(
            self._title_icon,
            "refresh",
            color=DesignSystem.COLOR_PRIMARY,
            size=24,
        )
        title_container.addWidget(self._title_icon)
        
        self._title_label = QLabel("Actualizando análisis...")
        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_TEXT_PRIMARY};
                font-size: {DesignSystem.FONT_SIZE_H3}px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            }}
        """)
        title_container.addWidget(self._title_label)
        title_container.addStretch()
        
        card_layout.addLayout(title_container)
        
        # Descripción
        self._description_label = QLabel(
            "Se están actualizando las herramientas rápidas tras los cambios realizados."
        )
        self._description_label.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_BODY}px;
            }}
        """)
        self._description_label.setWordWrap(True)
        card_layout.addWidget(self._description_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BORDER};
                max-height: 1px;
            }}
        """)
        card_layout.addWidget(separator)
        
        # Herramienta actual
        current_tool_container = QHBoxLayout()
        current_tool_container.setSpacing(DesignSystem.SPACE_SM)
        
        current_tool_label = QLabel("Analizando:")
        current_tool_label.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_BODY}px;
            }}
        """)
        current_tool_container.addWidget(current_tool_label)
        
        self._current_tool_icon = QLabel()
        icon_manager.set_label_icon(
            self._current_tool_icon,
            "options",
            color=DesignSystem.COLOR_TEXT_PRIMARY,
            size=20,
        )
        current_tool_container.addWidget(self._current_tool_icon)
        
        self._current_tool_label = QLabel("...")
        self._current_tool_label.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_TEXT_PRIMARY};
                font-size: {DesignSystem.FONT_SIZE_BODY}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
        """)
        current_tool_container.addWidget(self._current_tool_label)
        current_tool_container.addStretch()
        
        card_layout.addLayout(current_tool_container)
        
        # Barra de progreso
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(self._total_tools)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%v / %m herramientas")
        self._progress_bar.setFixedHeight(28)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_SMALL}px;
                background-color: {DesignSystem.COLOR_BACKGROUND_PRIMARY};
                text-align: center;
                color: {DesignSystem.COLOR_TEXT_PRIMARY};
                font-size: {DesignSystem.FONT_SIZE_SMALL}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QProgressBar::chunk {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                border-radius: {DesignSystem.RADIUS_SMALL}px;
            }}
        """)
        card_layout.addWidget(self._progress_bar)
        
        # Mensaje de info
        info_container = QHBoxLayout()
        info_container.setSpacing(DesignSystem.SPACE_XS)
        
        info_icon = QLabel()
        icon_manager.set_label_icon(
            info_icon,
            "info",
            color=DesignSystem.COLOR_INFO,
            size=16,
        )
        info_container.addWidget(info_icon)
        
        info_label = QLabel("El proceso es rápido y no bloqueará la interfaz")
        info_label.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SMALL}px;
                font-style: italic;
            }}
        """)
        info_container.addWidget(info_label)
        info_container.addStretch()
        
        card_layout.addLayout(info_container)
        
        main_layout.addWidget(card)
    
    def show_overlay(self):
        """Muestra el overlay con animación de fade in."""
        self.logger.debug("Mostrando overlay de re-análisis")
        self.setVisible(True)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()
    
    def hide_overlay(self):
        """Oculta el overlay con animación de fade out."""
        self.logger.debug("Ocultando overlay de re-análisis")
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(lambda: self.setVisible(False))
        self._fade_animation.start()
    
    def update_progress(self, tool_name: str, completed: int):
        """
        Actualiza el progreso del re-análisis.
        
        Args:
            tool_name: Nombre display de la herramienta actual
            completed: Número de herramientas completadas (0-5)
        """
        self.logger.debug(f"Actualizando progreso: {tool_name} ({completed}/{self._total_tools})")
        
        self._current_tool = tool_name
        self._completed_tools = completed
        
        # Actualizar label e icono de herramienta actual
        self._current_tool_label.setText(tool_name)
        
        # Icono según herramienta
        tool_icons = {
            "Live Photos": "image-multiple",
            "HEIC/JPG": "file-image",
            "Copias Exactas": "content-copy",
            "Organizar": "folder-multiple",
            "Renombrar": "rename-box",
        }
        icon_name = tool_icons.get(tool_name, "options")
        icon_manager.set_label_icon(
            self._current_tool_icon,
            icon_name,
            color=DesignSystem.COLOR_PRIMARY,
            size=20,
        )
        
        # Actualizar barra de progreso
        self._progress_bar.setValue(completed)
    
    def reset(self):
        """Reinicia el estado del overlay."""
        self.logger.debug("Reiniciando overlay")
        self._current_tool = ""
        self._completed_tools = 0
        self._current_tool_label.setText("...")
        icon_manager.set_label_icon(
            self._current_tool_icon,
            "options",
            color=DesignSystem.COLOR_TEXT_PRIMARY,
            size=20,
        )
        self._progress_bar.setValue(0)
