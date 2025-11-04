"""
Ventana Principal de Pixaro Lab - Reimplementación desde cero
Estado 1 (Fase 1): Selector de carpeta y bienvenida
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QFileDialog, QScrollArea, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon

from ui.styles.design_system import DesignSystem
from ui.widgets.dropzone_widget import DropzoneWidget
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from utils.logger import get_logger
from utils.icons import icon_manager
from config import Config


class MainWindow(QMainWindow):
    """
    Ventana principal de Pixaro Lab
    Fase 1: Implementa ESTADO 1 (selector de carpeta)
    """
    
    # Señales
    folder_selected = pyqtSignal(str)  # Emite cuando se selecciona una carpeta
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('MainWindow')
        self.selected_folder = None
        self._setup_window()
        self._setup_ui()
        self._apply_stylesheet()
        self.logger.info("MainWindow inicializada en Estado 1")
    
    def _setup_window(self):
        """Configura las propiedades básicas de la ventana"""
        self.setWindowTitle(f"{Config.APP_NAME}")
        self.setMinimumSize(
            DesignSystem.WINDOW_MIN_WIDTH,
            DesignSystem.WINDOW_MIN_HEIGHT
        )
        self.resize(
            DesignSystem.WINDOW_DEFAULT_WIDTH,
            DesignSystem.WINDOW_DEFAULT_HEIGHT
        )
    
    def _setup_ui(self):
        """Configura la interfaz completa del ESTADO 1"""
        # Widget central con scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        central_widget = QWidget()
        scroll.setWidget(central_widget)
        self.setCentralWidget(scroll)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(
            DesignSystem.SPACE_32,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_32,
            DesignSystem.SPACE_20
        )
        main_layout.setSpacing(DesignSystem.SPACE_16)
        
        # Card de bienvenida (compacta con iconos integrados)
        self.welcome_card = self._create_welcome_card()
        main_layout.addWidget(self.welcome_card)
        
        # Card de selección de carpeta
        main_layout.addWidget(self._create_folder_selection_card())
        
        # Card "Paso siguiente"
        main_layout.addWidget(self._create_next_step_card())
        
        # Espaciador al final
        main_layout.addStretch()
    
    def _create_welcome_card(self) -> QFrame:
        """
        Crea la card de bienvenida ultra-compacta con iconos integrados
        """
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(250, 250, 250, 0.8);
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_16}px;
            }}
        """)
        
        # Layout horizontal para todo en una sola línea
        layout = QHBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Título de bienvenida (más pequeño)
        welcome_title = QLabel(f"¡Bienvenido a {Config.APP_NAME}!")
        welcome_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(welcome_title)
        
        # Separador vertical delgado
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator.setFixedWidth(1)
        layout.addWidget(separator)
        
        # Subtítulo inline
        welcome_subtitle = QLabel("Analiza y optimiza tu colección de fotos y vídeos")
        welcome_subtitle.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(welcome_subtitle)
        
        # Espaciador para empujar los iconos a la derecha
        layout.addStretch()
        
        # Botón de configuración (icono)
        btn_settings = QToolButton()
        btn_settings.setAutoRaise(True)
        btn_settings.setToolTip("Configuración")
        icon_manager.set_button_icon(btn_settings, 'settings', color=DesignSystem.COLOR_TEXT_SECONDARY, size=16)
        btn_settings.setIconSize(QSize(16, 16))
        btn_settings.clicked.connect(self._on_settings_clicked)
        btn_settings.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                padding: 4px;
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QToolButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY};
            }}
        """)
        layout.addWidget(btn_settings)
        
        # Botón de acerca de (icono)
        btn_about = QToolButton()
        btn_about.setAutoRaise(True)
        btn_about.setToolTip("Acerca de")
        icon_manager.set_button_icon(btn_about, 'about', color=DesignSystem.COLOR_TEXT_SECONDARY, size=16)
        btn_about.setIconSize(QSize(16, 16))
        btn_about.clicked.connect(self._on_about_clicked)
        btn_about.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                padding: 4px;
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QToolButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY};
            }}
        """)
        layout.addWidget(btn_about)
        
        return card
    
    def _create_folder_selection_card(self) -> QFrame:
        """Crea la card principal para seleccionar carpeta"""
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_20}px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Header de la card
        header_title = QLabel("Selecciona la carpeta con tus fotos")
        header_title.setProperty("class", "header")
        layout.addWidget(header_title)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Dropzone centrado
        dropzone_container = QHBoxLayout()
        dropzone_container.addStretch()
        
        self.dropzone = DropzoneWidget()
        self.dropzone.folder_dropped.connect(self._on_folder_selected)
        dropzone_container.addWidget(self.dropzone)
        
        dropzone_container.addStretch()
        layout.addLayout(dropzone_container)
        
        # Botón "Seleccionar carpeta..."
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        
        btn_select = QPushButton("Seleccionar carpeta...")
        btn_select.setProperty("class", "primary")
        btn_select.clicked.connect(self._on_browse_folder)
        btn_container.addWidget(btn_select)
        
        btn_container.addStretch()
        layout.addLayout(btn_container)
        
        # Separador horizontal
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator2.setFixedHeight(1)
        layout.addWidget(separator2)
        
        # Consejos compactos
        layout.addWidget(self._create_tip_box(
            "info",
            "Elige la carpeta donde tengas tus fotos y videos del iPhone, de WhatsApp, "
            "o cualquier colección que quieras organizar."
        ))
        
        layout.addWidget(self._create_tip_box(
            "check",
            "Pixaro Lab analizará esa carpeta y todas sus subcarpetas. "
            "No se modificará nada hasta que tú lo autorices."
        ))
        
        # TODO: Línea de última carpeta (si existe)
        # layout.addSpacing(DesignSystem.SPACE_16)
        # layout.addWidget(self._create_last_folder_line())
        
        return card
    
    def _create_tip_box(self, icon_name: str, text: str) -> QFrame:
        """Crea una caja de consejo con icono y texto"""
        tip = QFrame()
        tip.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(240, 240, 240, 0.5);
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
            }}
        """)
        
        layout = QHBoxLayout(tip)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        # Icono usando icon_manager
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, color=DesignSystem.COLOR_TEXT_SECONDARY, size=14)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(icon_label)
        
        # Texto
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            line-height: {DesignSystem.LINE_HEIGHT_NORMAL};
        """)
        layout.addWidget(text_label, 1)
        
        return tip
    
    def _create_next_step_card(self) -> QFrame:
        """Crea la card "Paso siguiente" (vacía inicialmente)"""
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_20}px;
                opacity: 0.5;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        # Header
        header_title = QLabel("Paso siguiente: Elige qué quieres hacer")
        header_title.setProperty("class", "header")
        layout.addWidget(header_title)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Texto centrado
        empty_text = QLabel("Las herramientas aparecerán aquí después de analizar tu carpeta")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-style: italic;
            padding: {DesignSystem.SPACE_24}px 0;
        """)
        layout.addWidget(empty_text)
        
        return card
    
    def _apply_stylesheet(self):
        """Aplica el stylesheet global"""
        self.setStyleSheet(DesignSystem.get_stylesheet())
    
    # ==================== SLOTS ====================
    
    def _on_browse_folder(self):
        """Abre el diálogo de selección de carpeta"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta con fotos",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self._on_folder_selected(folder)
    
    def _on_folder_selected(self, folder_path: str):
        """Maneja cuando se selecciona una carpeta"""
        path = Path(folder_path)
        
        if not path.exists():
            self.logger.error(f"La carpeta no existe: {folder_path}")
            # TODO: Mostrar mensaje de error
            return
        
        if not path.is_dir():
            self.logger.error(f"La ruta no es una carpeta: {folder_path}")
            # TODO: Mostrar mensaje "Selecciona una carpeta, no un archivo"
            return
        
        self.selected_folder = str(path)
        self.logger.info(f"Carpeta seleccionada: {self.selected_folder}")
        self.folder_selected.emit(self.selected_folder)
        
        # TODO: Transición al ESTADO 2 (siguiente fase)
    
    def _on_settings_clicked(self):
        """Abre el diálogo de configuración"""
        self.logger.info("Abriendo configuración")
        #dialog = SettingsDialog(self)
        #dialog.exec()
    
    def _on_about_clicked(self):
        """Abre el diálogo Acerca de"""
        self.logger.info("Abriendo Acerca de")
        dialog = AboutDialog(self)
        dialog.exec()
