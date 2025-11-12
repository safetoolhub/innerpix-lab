"""
Widget de Tool Card para el grid de herramientas (STAGE 3)
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager


class ToolCard(QFrame):
    """
    Card clicable para cada herramienta del grid
    
    Incluye:
    - Icono + título
    - Descripción (3-4 líneas)
    - Estado/resultados
    - Botón de acción
    - Toda la card es clicable
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
        """
        Args:
            icon_name: Nombre del icono en icon_manager
            title: Título de la herramienta
            description: Descripción (3-4 líneas)
            action_text: Texto del botón de acción
        """
        super().__init__(parent)
        self.icon_name = icon_name
        self.title_text = title
        self.description_text = description
        self.action_text = action_text
        
        # Estado
        self.has_results = False
        self.status_lines = []
        
        self._setup_ui()
        self._setup_interactions()
    
    def _setup_ui(self):
        """Configura la interfaz de la card"""
        # Estilo de la card
        self.setStyleSheet(f"""
            ToolCard {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_20}px;
            }}
            ToolCard:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: rgba(37, 99, 235, 0.02);
            }}
        """)
        
        self.setMinimumHeight(220)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header: Icono + Título
        header_layout = QHBoxLayout()
        header_layout.setSpacing(DesignSystem.SPACE_8)
        
        self.icon_label = QLabel()
        icon_manager.set_label_icon(
            self.icon_label,
            self.icon_name,
            color=DesignSystem.COLOR_PRIMARY,
            size=24
        )
        header_layout.addWidget(self.icon_label)
        
        self.title_label = QLabel(self.title_text)
        self.title_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Descripción
        self.description_label = QLabel(self.description_text)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            line-height: {int(DesignSystem.FONT_SIZE_BASE * DesignSystem.LINE_HEIGHT_NORMAL)}px;
        """)
        layout.addWidget(self.description_label)
        
        # Espaciador flexible
        layout.addStretch()
        
        # Contenedor para líneas de estado (se llena dinámicamente)
        self.status_container = QVBoxLayout()
        self.status_container.setSpacing(DesignSystem.SPACE_4)
        layout.addLayout(self.status_container)
        
        # Espaciador antes del botón
        layout.addSpacing(DesignSystem.SPACE_12)
        
        # Botón de acción centrado
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        
        self.action_button = QPushButton(self.action_text)
        self.action_button.setObjectName("primary-button")
        self.action_button.setMinimumWidth(200)
        # Aplicar estilos directamente al botón
        self.action_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 10px 24px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        self.action_button.clicked.connect(self._on_button_clicked)
        btn_container.addWidget(self.action_button)
        
        btn_container.addStretch()
        layout.addLayout(btn_container)
    
    def _setup_interactions(self):
        """Configura las interacciones de la card"""
        # Toda la card es clicable
        self.mousePressEvent = self._on_card_clicked
    
    def _on_card_clicked(self, event):
        """Maneja el clic en la card"""
        self.clicked.emit()
    
    def _on_button_clicked(self):
        """Maneja el clic en el botón (igual que clic en card)"""
        self.clicked.emit()
    
    def set_status_with_results(self, count_text: str, size_text: str = None):
        """
        Configura el estado cuando hay resultados del análisis
        
        Args:
            count_text: Texto con cantidad (ej: "234 Live Photos detectadas")
            size_text: Texto con espacio recuperable (ej: "~1.8 GB recuperables")
        """
        self.has_results = True
        self._clear_status()
        
        # Línea 1: Checkmark + cantidad
        line1_layout = QHBoxLayout()
        line1_layout.setSpacing(DesignSystem.SPACE_6)
        line1_layout.setContentsMargins(0, 0, 0, 0)
        
        check_icon = QLabel()
        icon_manager.set_label_icon(
            check_icon,
            'check-circle',
            color=DesignSystem.COLOR_SUCCESS,
            size=14
        )
        line1_layout.addWidget(check_icon)
        
        count_label = QLabel(count_text)
        count_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """)
        line1_layout.addWidget(count_label)
        line1_layout.addStretch()
        
        self.status_container.addLayout(line1_layout)
        
        # Línea 2: Disco + espacio (si se proporciona)
        if size_text:
            line2_layout = QHBoxLayout()
            line2_layout.setSpacing(DesignSystem.SPACE_6)
            line2_layout.setContentsMargins(0, 0, 0, 0)
            
            disk_icon = QLabel()
            icon_manager.set_label_icon(
                disk_icon,
                'disk',
                color=DesignSystem.COLOR_TEXT_SECONDARY,
                size=14
            )
            line2_layout.addWidget(disk_icon)
            
            size_label = QLabel(size_text)
            size_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            """)
            line2_layout.addWidget(size_label)
            line2_layout.addStretch()
            
            self.status_container.addLayout(line2_layout)
        
        # Cambiar botón a primario
        self.action_button.setProperty("class", "primary")
        self.action_button.setStyle(self.action_button.style())
    
    def set_status_pending(self, info_text: str):
        """
        Configura el estado cuando está pendiente de análisis
        
        Args:
            info_text: Texto informativo (ej: "Este análisis puede tardar unos minutos.")
        """
        self.has_results = False
        self._clear_status()
        
        # Línea 1: Icono pausa + "Pendiente de análisis"
        line1_layout = QHBoxLayout()
        line1_layout.setSpacing(DesignSystem.SPACE_6)
        line1_layout.setContentsMargins(0, 0, 0, 0)
        
        pause_icon = QLabel()
        icon_manager.set_label_icon(
            pause_icon,
            'pause-circle',
            color=DesignSystem.COLOR_WARNING,
            size=14
        )
        line1_layout.addWidget(pause_icon)
        
        pending_label = QLabel("Pendiente de análisis")
        pending_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_WARNING};
        """)
        line1_layout.addWidget(pending_label)
        line1_layout.addStretch()
        
        self.status_container.addLayout(line1_layout)
        
        # Línea 2: Info adicional
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        self.status_container.addWidget(info_label)
        
        # Cambiar botón a secundario
        self.action_button.setProperty("class", "secondary")
        self.action_button.setStyle(self.action_button.style())
    
    def set_status_ready(self, count_text: str):
        """
        Configura el estado cuando está listo (sin análisis específico)
        Para herramientas como Organizar y Renombrar
        
        Args:
            count_text: Texto con cantidad (ej: "2,847 archivos listos")
        """
        self.has_results = True
        self._clear_status()
        
        # Línea única: Checkmark + texto
        line_layout = QHBoxLayout()
        line_layout.setSpacing(DesignSystem.SPACE_6)
        line_layout.setContentsMargins(0, 0, 0, 0)
        
        check_icon = QLabel()
        icon_manager.set_label_icon(
            check_icon,
            'check-circle',
            color=DesignSystem.COLOR_SUCCESS,
            size=14
        )
        line_layout.addWidget(check_icon)
        
        count_label = QLabel(count_text)
        count_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        line_layout.addWidget(count_label)
        line_layout.addStretch()
        
        self.status_container.addLayout(line_layout)
        
        # Botón primario
        self.action_button.setProperty("class", "primary")
        self.action_button.setStyle(self.action_button.style())
    
    def _clear_status(self):
        """Limpia todas las líneas de estado"""
        while self.status_container.count():
            item = self.status_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _clear_layout(self, layout):
        """Limpia recursivamente un layout"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
