"""
Widget de Tool Card para el grid de herramientas (STAGE 3)
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QRect
from PyQt6.QtGui import QCursor, QLinearGradient, QBrush, QPalette, QColor

from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager


class ToolCard(QFrame):
    """
    Card clicable para cada herramienta del grid
    
    Incluye:
    - Icono + título (alineado izquierda)
    - Badge de estado (esquina superior derecha)
    - Descripción (reducida)
    - Botón de acción (centrado)
    """
    
    # Señales
    clicked = pyqtSignal()  # Emitida cuando se hace clic en la card
    
    def __init__(
        self,
        icon_name: str,
        title: str,
        description: str,
        action_text: str,
        parent=None
    ):
        super().__init__(parent)
        self.icon_name = icon_name
        self.title_text = title
        self.description_text = description
        self.action_text = action_text
        
        # Estado
        self.has_results = False
        self.is_enabled = True
        
        self._setup_ui()
        self._setup_interactions()
    
    def _setup_ui(self):
        """Configura la interfaz de la card con estilos estables"""
        # Estilo consolidado y estable para evitar jitter.
        self.setStyleSheet(f"""
            ToolCard {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
            ToolCard:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: rgba(37, 99, 235, 0.02);
            }}
            ToolCard[enabled_state="disabled"] {{
                background-color: {DesignSystem.COLOR_SURFACE_DISABLED};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """)
        self.setProperty("enabled_state", "enabled")
        
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_8)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_12, 
                                 DesignSystem.SPACE_12, DesignSystem.SPACE_12)
        
        # Header: Icono + Título + Badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(DesignSystem.SPACE_8)
        
        self.icon_label = QLabel()
        icon_manager.set_label_icon(self.icon_label, self.icon_name, color=DesignSystem.COLOR_PRIMARY, size=24)
        header_layout.addWidget(self.icon_label)
        
        self.title_label = QLabel(self.title_text)
        self.title_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_BASE}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT};")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # Badge (PENDIENTE / NADA ENCONTRADO / NUMERO)
        self.badge_label = QLabel("")
        self.badge_label.setObjectName("statusBadge")
        self.badge_label.setVisible(False)
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_badge_style(DesignSystem.COLOR_SECONDARY) # Default style
        header_layout.addWidget(self.badge_label)
        
        layout.addLayout(header_layout)
        
        # Descripción
        self.description_label = QLabel(self.description_text)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        layout.addWidget(self.description_label)
        
        layout.addStretch()
        
        # Contenedor para status (ahora vacío por defecto para ahorrar espacio)
        self.status_container = QVBoxLayout()
        layout.addLayout(self.status_container)
        
        # Botón de acción
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        self.action_button = QPushButton(self.action_text)
        self.action_button.setMinimumWidth(180)
        
        # QSS para el botón con estados claros
        self.action_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: white;
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 10px 20px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            }}
            QPushButton:hover {{ 
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER}; 
            }}
            
            /* Clase para ANALIZAR (Ámbar) */
            QPushButton[class="warning"] {{
                background-color: {DesignSystem.COLOR_WARNING};
                color: {DesignSystem.COLOR_TEXT};
            }}
            QPushButton[class="warning"]:hover {{
                background-color: #e5ac06; /* Ámbar más oscuro */
            }}
            
            /* Clase para GESTIONAR (Azul) - ya es el default por QPushButton arriba, pero lo repetimos por claridad */
            QPushButton[class="primary"] {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: white;
            }}
            
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SURFACE_DISABLED};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """)
        self.action_button.clicked.connect(self._on_button_clicked)
        btn_container.addWidget(self.action_button)
        btn_container.addStretch()
        layout.addLayout(btn_container)

    def _update_badge_style(self, bg_color: str):
        self.badge_label.setStyleSheet(f"""
            QLabel#statusBadge {{
                background-color: {bg_color};
                color: white;
                border-radius: 9px;
                padding: 1px 6px;
                min-width: 14px;
                font-size: 10px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            }}
        """)

    def _setup_interactions(self):
        self.mousePressEvent = self._on_card_clicked
        
    def enterEvent(self, event):
        if not self.is_enabled: return
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)
        
    def leaveEvent(self, event):
        self.setGraphicsEffect(None)

    def _on_card_clicked(self, event):
        if self.is_enabled: self.clicked.emit()
    
    def _on_button_clicked(self, event=None):
        if self.is_enabled: self.clicked.emit()

    def set_action_text(self, text: str):
        self.action_text = text
        self.action_button.setText(text)

    def _clear_status(self):
        while self.status_container.count():
            item = self.status_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): self._clear_layout(item.layout())

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): self._clear_layout(item.layout())

    def set_status_with_results(self, count_text: str, size_text: str = None, badge_count: int = None):
        """Configura el estado cuando hay resultados (GESTIONAR / AZUL)"""
        self.has_results = True
        self.is_enabled = True
        self._clear_status()
        
        # Badge azul con número
        if badge_count is not None and badge_count > 0:
            self.badge_label.setText(str(badge_count))
            self._update_badge_style(DesignSystem.COLOR_PRIMARY)
            self.badge_label.setVisible(True)
        else:
            self.badge_label.setVisible(False)
            
        self.set_action_text("Gestionar ahora")
        self.action_button.setProperty("class", "primary")
        self.set_enabled(True) 
        self._refresh_style()

    def set_status_pending(self, info_text: str = None):
        """Estado pendiente de análisis (ANALIZAR / ÁMBAR)"""
        self.has_results = False
        self.is_enabled = True
        self._clear_status()
        
        # Badge ámbar
        self.badge_label.setText("PENDIENTE")
        self._update_badge_style(DesignSystem.COLOR_WARNING)
        self.badge_label.setVisible(True)
        
        self.set_action_text("Analizar ahora")
        self.action_button.setProperty("class", "warning")
        self.set_enabled(True)
        self._refresh_style()

    def set_status_no_results(self, message: str = None):
        """Estado sin resultados (NADA QUE ELIMINAR / GRIS)"""
        self.has_results = False
        self._clear_status()
        
        # Badge gris
        self.badge_label.setText("NADA ENCONTRADO")
        self._update_badge_style(DesignSystem.COLOR_TEXT_SECONDARY)
        self.badge_label.setVisible(True)
        
        # Deshabilitar botón y cambiar texto
        self.set_action_text("No hay nada que eliminar")
        self.set_enabled(False)
        self._refresh_style()

    def set_status_ready(self, count_text: str):
        self.has_results = True
        self.is_enabled = True
        self._clear_status()
        # Para Organizar/Renombrar, mostramos un check y el texto en el centro si es necesario,
        # o simplemente dejamos el badge con la cuenta si se proporcionara.
        label = QLabel(count_text)
        label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT};")
        self.status_container.addWidget(label)
        self.badge_label.setVisible(False)
        self._refresh_style()

    def set_enabled(self, enabled: bool):
        self.is_enabled = enabled
        self.action_button.setEnabled(enabled)
        self.setProperty("enabled_state", "enabled" if enabled else "disabled")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor))
        self._refresh_style()

    def _refresh_style(self):
        """Refresca el estilo de la card y del botón de acción"""
        # Refrescar la card
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Refrescar el botón específicamente (crucial para cambios de property/class)
        self.action_button.style().unpolish(self.action_button)
        self.action_button.style().polish(self.action_button)
        self.action_button.update()
