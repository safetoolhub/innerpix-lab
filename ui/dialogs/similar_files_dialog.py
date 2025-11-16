"""
Diálogo de gestión de archivos similares con slider interactivo.

Permite ajustar la sensibilidad de detección en tiempo real y gestionar
los grupos de archivos similares detectados sin necesidad de reanalizar.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSlider, QPushButton,
    QDialogButtonBox, QCheckBox, QGroupBox, QScrollArea, QWidget,
    QGridLayout, QSizePolicy, QProgressBar, QMenu, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QDesktopServices, QCursor, QImage
from PyQt6.QtCore import QUrl
from config import Config
from services.similar_files_detector import SimilarFilesAnalysis, DuplicateGroup
from utils.format_utils import format_size
from ui.styles.design_system import DesignSystem  # Keep for backwards compatibility with existing code
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from .base_dialog import BaseDialog
from .dialog_utils import show_file_details_dialog


class ImagePreviewDialog(QDialog):
    """Diálogo modal para mostrar vista previa ampliada de una imagen."""
    
    def __init__(self, image_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Vista previa - {image_path.name}")
        self.setModal(True)
        self.resize(900, 700)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area para la imagen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setStyleSheet(f"background-color: {DesignSystem.COLOR_BACKGROUND};")
        
        # Label con imagen
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            # Escalar manteniendo aspecto, máximo 1600x1200
            scaled = pixmap.scaled(
                1600, 1200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            image_label.setPixmap(scaled)
        else:
            image_label.setText("❌ No se pudo cargar la imagen")
            image_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_40}px;
            """)
        
        scroll.setWidget(image_label)
        layout.addWidget(scroll)
        
        # Botón cerrar en la parte inferior
        button_container = QWidget()
        button_container.setStyleSheet(f"background-color: {DesignSystem.COLOR_SURFACE};")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12
        )
        
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        close_btn.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addWidget(button_container)


class SimilarFilesDialog(BaseDialog):
    """
    Diálogo para gestionar archivos similares con slider de sensibilidad.
    
    Permite ajustar la sensibilidad en tiempo real y ver cómo afecta
    a los grupos detectados, sin necesidad de reanalizar.
    """

    def __init__(self, analysis: SimilarFilesAnalysis, parent=None):
        """
        Inicializa el diálogo.
        
        Args:
            analysis: Objeto SimilarFilesAnalysis con hashes calculados
            parent: Widget padre
        """
        super().__init__(parent)
        
        self.analysis = analysis
        self.current_sensitivity = 85  # Valor inicial predeterminado
        self.current_result = None
        self.current_group_index = 0
        self.selections = {}  # {group_index: [files_to_delete]}
        self.accepted_plan = None
        
        # Filtros
        self.filter_min_files = 2  # Mínimo archivos por grupo
        self.filter_min_size_mb = 0  # Tamaño mínimo en MB (0 = sin filtro)
        self.all_groups = []  # Grupos sin filtrar (para poder restaurar)
        
        self._setup_ui()
        self._load_initial_results()
    
    def _setup_ui(self):
        """Configura la interfaz del diálogo."""
        # Configuración de la ventana (más alta para dar espacio a las imágenes)
        self.setWindowTitle("Gestionar archivos similares")
        self.setModal(True)
        self.resize(1200, 850)
        self.setMinimumSize(1000, 700)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_12)
        
        # --- HEADER: Título compacto con métricas iniciales (se actualizarán) ---
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='content-duplicate',
            title='Archivos similares detectados',
            description='Imágenes visualmente parecidas (perceptual hash). Ajusta la sensibilidad para refinar.',
            metrics=[
                {'value': '0', 'label': 'Grupos', 'color': DesignSystem.COLOR_PRIMARY},
                {'value': '0', 'label': 'Duplicados', 'color': DesignSystem.COLOR_WARNING},
                {'value': '0 B', 'label': 'Recuperable', 'color': DesignSystem.COLOR_SUCCESS}
            ]
        )
        main_layout.addWidget(self.header_frame)
        
        # Contenedor con márgenes para el resto del contenido
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(DesignSystem.SPACE_12)
        content_layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_8,
            DesignSystem.SPACE_20,
            0
        )
        main_layout.addWidget(content_container)
        
        # --- SECCIÓN 1: Sensibilidad y Filtros en horizontal (más compacto) ---
        sensitivity_filters_layout = QHBoxLayout()
        sensitivity_filters_layout.setSpacing(DesignSystem.SPACE_12)
        
        sensitivity_card = self._create_sensitivity_card()
        filters_card = self._create_filters_card()
        
        sensitivity_filters_layout.addWidget(sensitivity_card, stretch=2)
        sensitivity_filters_layout.addWidget(filters_card, stretch=1)
        
        content_layout.addLayout(sensitivity_filters_layout)
        
        # --- SECCIÓN 2: Selección automática (botones en una sola fila) ---
        strategies_card = self._create_strategies_card()
        content_layout.addWidget(strategies_card)
        
        # --- SECCIÓN 3: Navegación de grupos ---
        nav_layout = self._create_navigation_section()
        content_layout.addLayout(nav_layout)
        
        # --- SECCIÓN 4: Contenedor de grupo actual (con más espacio vertical) ---
        self.group_container = QGroupBox()
        self.group_layout = QVBoxLayout(self.group_container)
        self.group_layout.setSpacing(DesignSystem.SPACE_8)
        self.group_layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_8, DesignSystem.SPACE_12, DesignSystem.SPACE_8)
        content_layout.addWidget(self.group_container, stretch=1)  # Darle stretch para que ocupe más espacio
        
        # --- SECCIÓN 5: Resumen ---
        summary_group = self._create_summary_section()
        content_layout.addWidget(summary_group)
        
        # --- SECCIÓN 6: Opciones de seguridad (separadas, antes de botones) ---
        options_group = self._create_options_section()
        content_layout.addWidget(options_group)
        
        # --- SECCIÓN 7: Botones de acción ---
        buttons = self._create_action_buttons()
        content_layout.addWidget(buttons)
        
        # Aplicar estilos
        self.setStyleSheet(self._get_dialog_styles())
    
    def _create_sensitivity_card(self) -> QFrame:
        """
        Crea la card con slider de sensibilidad interactivo (compacta).
        
        Returns:
            QFrame con slider y controles
        """
        card = QFrame()
        card.setObjectName("sensitivity_card")
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_6)
        layout.setContentsMargins(
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_10,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_10
        )
        
        # Título de la card con icono
        title_layout = QHBoxLayout()
        title_icon = icon_manager.get_icon('tune', size=16)
        title_icon_label = QLabel()
        title_icon_label.setPixmap(title_icon.pixmap(16, 16))
        title_layout.addWidget(title_icon_label)
        
        title = QLabel("Ajustar sensibilidad")
        title.setObjectName("card_title")
        title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Layout del slider
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(DesignSystem.SPACE_10)
        
        # Label izquierda: 30% = Permisivo
        left_label = QLabel("30%\nPermisivo")
        left_label.setObjectName("slider_label")
        left_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        left_label.setToolTip(
            "Sensibilidad baja (30%):\n"
            "Agrupa imágenes que se parecen poco.\n"
            "Genera MÁS grupos con más archivos."
        )
        
        # Slider horizontal
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setObjectName("sensitivity_slider")
        self.sensitivity_slider.setRange(30, 100)
        self.sensitivity_slider.setValue(self.current_sensitivity)
        self.sensitivity_slider.setSingleStep(5)
        self.sensitivity_slider.setPageStep(10)
        self.sensitivity_slider.setTickInterval(10)
        self.sensitivity_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        self.sensitivity_slider.setToolTip(
            "Ajusta la sensibilidad de detección:\n"
            "• 100% = Muy estricto (solo casi idénticas)\n"
            "• 85% = Recomendado (muy similares)\n"
            "• 50% = Moderado (similares)\n"
            "• 30% = Permisivo (algo similares)"
        )
        
        # Label derecha: 100% = Estricto
        right_label = QLabel("100%\nEstricto")
        right_label.setObjectName("slider_label")
        right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        right_label.setToolTip(
            "Sensibilidad alta (100%):\n"
            "Solo agrupa imágenes casi idénticas.\n"
            "Genera MENOS grupos con archivos muy parecidos."
        )
        
        slider_layout.addWidget(left_label)
        slider_layout.addWidget(self.sensitivity_slider)
        slider_layout.addWidget(right_label)
        
        layout.addLayout(slider_layout)
        
        # Display de estadísticas en tiempo real (inline, más compacto)
        self.stats_label = QLabel()
        self.stats_label.setObjectName("stats_label")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_PRIMARY};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        layout.addWidget(self.stats_label)
        
        # Conectar señales
        self.sensitivity_slider.valueChanged.connect(
            self._on_slider_value_changed
        )
        self.sensitivity_slider.sliderReleased.connect(
            self._on_slider_released
        )
        
        return card
    
    def _create_filters_card(self) -> QFrame:
        """
        Card con filtros avanzados para refinar los grupos mostrados (compacta).
        
        Returns:
            QFrame con controles de filtrado
        """
        from PyQt6.QtWidgets import QSpinBox
        
        card = QFrame()
        card.setObjectName("filters_card")
        card.setStyleSheet(f"""
            QFrame#filters_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_6)
        layout.setContentsMargins(
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_10,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_10
        )
        
        # Título con icono
        title_layout = QHBoxLayout()
        icon = icon_manager.get_icon('filter-variant', size=16)
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(16, 16))
        title_layout.addWidget(icon_label)
        
        title = QLabel("Filtros")
        title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Grid de filtros (más compacto)
        from PyQt6.QtWidgets import QGridLayout
        filters_grid = QGridLayout()
        filters_grid.setSpacing(DesignSystem.SPACE_6)
        filters_grid.setColumnStretch(1, 1)
        
        # Estilo común para spinboxes con flechas Material Design
        spinbox_style = f"""
            QSpinBox {{
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_6}px;
                padding-right: 24px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                background-color: {DesignSystem.COLOR_BACKGROUND};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
            QSpinBox:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QSpinBox:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                border-width: 2px;
            }}
            QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {DesignSystem.COLOR_BORDER};
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER};
                border-top-right-radius: {DesignSystem.RADIUS_BASE}px;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QSpinBox::up-button:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY};
            }}
            QSpinBox::up-button:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QSpinBox::up-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid {DesignSystem.COLOR_TEXT};
                width: 0px;
                height: 0px;
                margin: 0px 6px;
            }}
            QSpinBox::up-arrow:hover {{
                border-bottom-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 20px;
                border-left: 1px solid {DesignSystem.COLOR_BORDER};
                border-top: 1px solid {DesignSystem.COLOR_BORDER};
                border-bottom-right-radius: {DesignSystem.RADIUS_BASE}px;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QSpinBox::down-button:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY};
            }}
            QSpinBox::down-button:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QSpinBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {DesignSystem.COLOR_TEXT};
                width: 0px;
                height: 0px;
                margin: 0px 6px;
            }}
            QSpinBox::down-arrow:hover {{
                border-top-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """
        
        # Filtro 1: Mínimo archivos por grupo
        min_files_label = QLabel("Mín. archivos:")
        min_files_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        min_files_label.setToolTip("Mostrar solo grupos con al menos N archivos")
        
        self.min_files_spin = QSpinBox()
        self.min_files_spin.setRange(2, 100)
        self.min_files_spin.setValue(self.filter_min_files)
        self.min_files_spin.setSuffix(" archivos")
        self.min_files_spin.setMinimumWidth(120)
        self.min_files_spin.setStyleSheet(spinbox_style)
        self.min_files_spin.setToolTip("Número mínimo de archivos que debe tener un grupo para mostrarse")
        self.min_files_spin.valueChanged.connect(self._on_filters_changed)
        
        filters_grid.addWidget(min_files_label, 0, 0)
        filters_grid.addWidget(self.min_files_spin, 0, 1)
        
        # Filtro 2: Tamaño mínimo
        min_size_label = QLabel("Tamaño mín.:")
        min_size_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        min_size_label.setToolTip("Mostrar solo archivos mayores a N MB")
        
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 100)
        self.min_size_spin.setValue(self.filter_min_size_mb)
        self.min_size_spin.setSuffix(" MB")
        self.min_size_spin.setMinimumWidth(120)
        self.min_size_spin.setStyleSheet(spinbox_style)
        self.min_size_spin.setToolTip(
            "Tamaño mínimo de archivo en MB. "
            "Grupos con todos los archivos menores serán ocultados. "
            "0 = sin filtro"
        )
        self.min_size_spin.valueChanged.connect(self._on_filters_changed)
        
        filters_grid.addWidget(min_size_label, 1, 0)
        filters_grid.addWidget(self.min_size_spin, 1, 1)
        
        layout.addLayout(filters_grid)
        
        # Botón resetear filtros (más pequeño)
        reset_btn = QPushButton("Resetear")
        reset_btn.setIcon(icon_manager.get_icon('refresh', size=14))
        reset_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        reset_btn.setToolTip("Restaurar filtros a valores predeterminados")
        reset_btn.clicked.connect(self._reset_filters)
        reset_btn.setMaximumWidth(100)
        layout.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        return card
    
    def _create_strategies_card(self) -> QFrame:
        """
        Card con estrategias de selección automática (botones en fila única).
        
        Returns:
            QFrame con botones de estrategias
        """
        card = QFrame()
        card.setObjectName("strategies_card")
        card.setStyleSheet(f"""
            QFrame#strategies_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_6)
        layout.setContentsMargins(
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_10,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_10
        )
        
        # Título con icono
        title_layout = QHBoxLayout()
        icon = icon_manager.get_icon('auto-fix', size=16)
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(16, 16))
        title_layout.addWidget(icon_label)
        
        title = QLabel("Selección automática")
        title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Botones de estrategia en una sola fila horizontal
        strategies_layout = QHBoxLayout()
        strategies_layout.setSpacing(DesignSystem.SPACE_8)
        
        strategies = [
            ('Mantener 1º', 'keep_first', 'Elimina todos excepto el primero de cada grupo'),
            ('Mantener último', 'keep_last', 'Elimina todos excepto el último de cada grupo'),
            ('Más grande', 'keep_largest', 'Elimina los archivos más pequeños de cada grupo'),
            ('Más pequeño', 'keep_smallest', 'Elimina los archivos más grandes de cada grupo'),
            ('Limpiar', 'clear', 'Deselecciona todos los archivos marcados'),
        ]
        
        for label, strategy, tooltip in strategies:
            btn = QPushButton(label)
            
            # Estilo diferente para el botón de limpiar
            if strategy == 'clear':
                btn.setStyleSheet(DesignSystem.get_secondary_button_style())
                btn.clicked.connect(self._clear_all_selections)
            else:
                btn.setStyleSheet(DesignSystem.get_primary_button_style())
                btn.clicked.connect(lambda checked, s=strategy: self._apply_strategy(s))
            
            btn.setToolTip(tooltip)
            strategies_layout.addWidget(btn)
        
        layout.addLayout(strategies_layout)
        
        return card
    
    def _create_warning_section(self) -> QFrame:
        """Crea la sección de advertencia."""
        warning_frame = QFrame()
        warning_frame.setObjectName("warning_frame")
        
        warning_layout = QVBoxLayout(warning_frame)
        warning_layout.setSpacing(DesignSystem.SPACE_8)
        warning_layout.setContentsMargins(
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_8,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_8
        )
        
        warning_icon = icon_manager.get_icon('warning', size=16)
        warning_text_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(warning_icon.pixmap(16, 16))
        warning_text_layout.addWidget(icon_label)
        
        warning = QLabel(
            "Estos archivos son similares pero NO idénticos. "
            "Revisa cada grupo cuidadosamente antes de eliminar."
        )
        warning.setWordWrap(True)
        warning.setObjectName("warning_text")
        warning_text_layout.addWidget(warning)
        warning_layout.addLayout(warning_text_layout)
        
        return warning_frame
    
    def _create_navigation_section(self) -> QHBoxLayout:
        """Crea la sección de navegación de grupos con Material Design."""
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(DesignSystem.SPACE_12)
        
        # Botón Anterior con estilo Material Design
        self.prev_btn = QPushButton("Anterior")
        self.prev_btn.setIcon(icon_manager.get_icon('chevron-left', size=18))
        self.prev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_16}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_BORDER};
            }}
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border-color: {DesignSystem.COLOR_BORDER};
            }}
        """)
        self.prev_btn.setToolTip("Navegar al grupo anterior (navegación circular)")
        self.prev_btn.clicked.connect(self._previous_group)
        
        # Label central con información del grupo
        self.group_label = QLabel()
        self.group_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
            padding: {DesignSystem.SPACE_8}px;
        """)
        
        # Botón Siguiente con estilo Material Design
        self.next_btn = QPushButton("Siguiente")
        self.next_btn.setIcon(icon_manager.get_icon('chevron-right', size=18))
        self.next_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # Icono a la derecha
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_16}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_BORDER};
            }}
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border-color: {DesignSystem.COLOR_BORDER};
            }}
        """)
        self.next_btn.setToolTip("Navegar al grupo siguiente (navegación circular)")
        self.next_btn.clicked.connect(self._next_group)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.group_label, 1)
        nav_layout.addWidget(self.next_btn)
        
        return nav_layout
    
    def _create_summary_section(self) -> QGroupBox:
        """Crea la sección de resumen (ocupa todo el ancho)."""
        summary_group = QGroupBox("Resumen")
        summary_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                margin-top: {DesignSystem.SPACE_8}px;
                padding-top: {DesignSystem.SPACE_8}px;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {DesignSystem.SPACE_12}px;
                padding: 0 {DesignSystem.SPACE_6}px;
            }}
        """)
        summary_group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        summary_group.setMinimumHeight(60)
        summary_group.setMaximumHeight(80)
        
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12
        )
        
        self.summary_label = QLabel()
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        self.summary_label.setWordWrap(True)
        self.summary_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.summary_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.summary_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        summary_layout.addWidget(self.summary_label)
        
        return summary_group
    
    def _create_options_section(self) -> QFrame:
        """Crea la sección de opciones de seguridad usando método centralizado."""
        return self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de eliminar",
            dry_run_label="Modo simulación (no eliminar archivos realmente)"
        )
    
    def _create_action_buttons(self) -> QDialogButtonBox:
        """Crea los botones de acción del diálogo con estilo Material Design."""
        buttons = self.make_ok_cancel_buttons(
            ok_text="Eliminar Seleccionados",
            ok_enabled=False,
            button_style='danger'
        )
        self.ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        
        return buttons

    def _load_group(self, index):
        """Carga y muestra un grupo específico con miniaturas"""
        if not 0 <= index < len(self.analysis.groups):
            return
        self.current_group_index = index
        group = self.analysis.groups[index]

        # Actualizar navegación
        total_groups = len(self.analysis.groups)
        self.group_label.setText(f"Grupo {index + 1} de {total_groups}")
        # Con navegación circular, los botones siempre están habilitados
        self.prev_btn.setEnabled(True)
        self.next_btn.setEnabled(True)

        # Limpiar layout anterior
        for i in reversed(range(self.group_layout.count())):
            widget = self.group_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Métrica de similitud visual
        similarity_widget = self._create_similarity_widget(group)
        self.group_layout.addWidget(similarity_widget)

        # Info del grupo
        info_label = QLabel(
            f"<b>Archivos:</b> {len(group.files)} | "
            f"<b>Tamaño total:</b> {format_size(group.total_size)}"
        )
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setStyleSheet(DesignSystem.STYLE_PANEL_LABEL)
        self.group_layout.addWidget(info_label)

        # Advertencia si hay demasiadas imágenes
        max_thumbnails = 20
        if len(group.files) > max_thumbnails:
            warning_label = QLabel(
                f"Este grupo tiene {len(group.files)} imágenes. "
                f"Para mejor rendimiento, usa el scroll para navegar."
            )
            warning_label.setStyleSheet(DesignSystem.STYLE_DIALOG_WARNING_ORANGE)
            warning_label.setWordWrap(True)
            self.group_layout.addWidget(warning_label)

        # Crear área con scroll para las miniaturas
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Widget contenedor de miniaturas
        thumbnails_widget = QWidget()
        thumbnails_layout = QGridLayout(thumbnails_widget)
        thumbnails_layout.setSpacing(10)

        previous_selection = self.selections.get(index, [])

        # Configurar grid (máximo 4 columnas para imágenes más grandes)
        max_columns = 4
        for row_idx, file_path in enumerate(group.files):
            row = row_idx // max_columns
            col = row_idx % max_columns

            # Frame contenedor para cada imagen
            frame = QFrame()
            frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            frame.setLineWidth(1)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setSpacing(0)
            frame_layout.setContentsMargins(0, 0, 0, 0)

            # === SECCIÓN 1: CHECKBOX DE ELIMINACIÓN ===
            delete_section = QWidget()
            delete_section_layout = QVBoxLayout(delete_section)
            delete_section_layout.setContentsMargins(8, 6, 8, 6)
            delete_section_layout.setSpacing(0)
            
            checkbox = QCheckBox("Eliminar")
            checkbox.setChecked(file_path in previous_selection)
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-weight: 600;
                    font-size: 10px;
                    padding: 4px;
                    color: #DC3545;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #DC3545;
                    border-radius: 4px;
                    background-color: white;
                }
                QCheckBox::indicator:checked {
                    background-color: #DC3545;
                    border-color: #DC3545;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTMuNSA0TDYgMTEuNSAyLjUgOCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
                }
                QCheckBox::indicator:hover {
                    border-color: #BB2D3B;
                }
            """)
            checkbox.stateChanged.connect(lambda state, f=file_path: self._on_selection_changed(f, state))
            delete_section_layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
            
            # Diseño más limpio: borde rojo sutil en lugar de fondo amarillo
            delete_section.setStyleSheet("""
                QWidget {
                    background-color: #FFFFFF;
                    padding: 6px;
                    border-bottom: 2px solid #F8D7DA;
                }
            """)
            frame_layout.addWidget(delete_section)

            # === SECCIÓN 2: MINIATURA (PREVIEW) ===
            preview_section = QWidget()
            preview_section_layout = QVBoxLayout(preview_section)
            preview_section_layout.setContentsMargins(4, 4, 4, 4)
            preview_section_layout.setSpacing(2)
            
            thumbnail_label, is_video = self._create_thumbnail(file_path)
            
            # Si es video, añadir indicador visual
            if is_video:
                video_indicator = QLabel("VIDEO")
                video_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
                video_indicator.setStyleSheet("""
                    background-color: #6F42C1;
                    color: white;
                    font-size: 8px;
                    font-weight: bold;
                    padding: 2px;
                    border-radius: 3px;
                    margin-bottom: 2px;
                """)
                preview_section_layout.addWidget(video_indicator)
            
            if thumbnail_label:
                thumbnail_label.mousePressEvent = lambda event, f=file_path: self._show_image_preview(f)
                thumbnail_label.setCursor(Qt.CursorShape.PointingHandCursor)
                thumbnail_label.setToolTip(f"Click para ver en tamaño completo: {file_path.name}")
                preview_section_layout.addWidget(thumbnail_label, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                # Si no se puede cargar la imagen, mostrar placeholder
                no_preview = QLabel("Sin vista previa")
                no_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_preview.setStyleSheet(DesignSystem.STYLE_DIALOG_NO_PREVIEW)
                preview_section_layout.addWidget(no_preview)
            
            preview_section.setStyleSheet("""
                QWidget {
                    background-color: #E9ECEF;
                    padding: 6px;
                }
            """)
            frame_layout.addWidget(preview_section)

            # === SECCIÓN 3: INFORMACIÓN COMPACTA DEL ARCHIVO (con menú contextual) ===
            info_section = QWidget()
            info_section.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            info_section.customContextMenuRequested.connect(
                lambda pos, f=file_path: self._show_file_context_menu(pos, f, info_section)
            )
            info_section.setCursor(Qt.CursorShape.PointingHandCursor)
            info_section.setToolTip("Clic derecho para más opciones")
            
            info_section_layout = QVBoxLayout(info_section)
            info_section_layout.setContentsMargins(6, 4, 6, 4)
            info_section_layout.setSpacing(2)
            
            from datetime import datetime
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # Nombre del archivo (con icono)
            name_label = QLabel(f"<b>{file_path.name[:22]}{'...' if len(file_path.name) > 22 else ''}</b>")
            name_label.setTextFormat(Qt.TextFormat.RichText)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setStyleSheet(f"font-size: 10px; color: {DesignSystem.COLOR_TEXT};")
            info_section_layout.addWidget(name_label)
            
            # Tamaño y fecha en una línea compacta
            details_label = QLabel(
                f"{format_size(file_path.stat().st_size)} • "
                f"{mtime.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            details_label.setStyleSheet(f"font-size: 9px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
            info_section_layout.addWidget(details_label)
            
            # Estilo con hover para indicar que es clickeable
            info_section.setStyleSheet("""
                QWidget {
                    background-color: #F8F9FA;
                    padding: 4px;
                    border-radius: 4px;
                }
                QWidget:hover {
                    background-color: #E9ECEF;
                }
            """)
            frame_layout.addWidget(info_section)

            # Destacar el frame si está seleccionado
            if file_path in previous_selection:
                frame.setStyleSheet("""
                    QFrame {
                        border: 2px solid #DC3545;
                        background-color: #FFFFFF;
                        border-radius: 6px;
                    }
                """)
            else:
                frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #CED4DA;
                        background-color: #FFFFFF;
                        border-radius: 6px;
                    }
                """)

            # Conectar cambios de selección para actualizar el estilo del frame
            checkbox.stateChanged.connect(
                lambda state, fr=frame, f=file_path: self._update_frame_style(fr, f, state)
            )

            thumbnails_layout.addWidget(frame, row, col)

        scroll_area.setWidget(thumbnails_widget)
        scroll_area.setMinimumHeight(350)
        scroll_area.setMaximumHeight(500)
        self.group_layout.addWidget(scroll_area)

        self._update_summary()

    def _create_similarity_widget(self, group) -> QWidget:
        """Crea un widget visual compacto para mostrar el grado de similitud usando Material Design"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_8, DesignSystem.SPACE_12, DesignSystem.SPACE_8)

        # Icono de similitud
        similarity_color, similarity_text = self._get_similarity_level(group.similarity_score)
        icon_label = icon_manager.create_icon_label('image-search', color=similarity_color, size=24)
        layout.addWidget(icon_label)
        
        # Contenedor de información (vertical)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Título + porcentaje en una línea
        title_layout = QHBoxLayout()
        title_layout.setSpacing(DesignSystem.SPACE_8)
        
        title_label = QLabel("Similitud:")
        title_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        title_layout.addWidget(title_label)
        
        percentage_label = QLabel(f"{group.similarity_score:.0f}%")
        percentage_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {similarity_color};
        """)
        title_layout.addWidget(percentage_label)
        title_layout.addStretch()
        
        info_layout.addLayout(title_layout)
        
        # Nivel de similitud
        level_label = QLabel(similarity_text)
        level_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        info_layout.addWidget(level_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Barra de progreso compacta (vertical, al lado derecho)
        progress_bar = QProgressBar()
        progress_bar.setOrientation(Qt.Orientation.Vertical)
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(int(group.similarity_score))
        progress_bar.setTextVisible(False)
        progress_bar.setFixedSize(8, 40)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: 4px;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QProgressBar::chunk {{
                background-color: {similarity_color};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(progress_bar)

        container.setStyleSheet(f"""
            QWidget {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
        """)

        return container

    def _get_similarity_level(self, score: float) -> tuple:
        """Retorna (color, texto) según el nivel de similitud"""
        if score >= 95:
            return (DesignSystem.COLOR_SUCCESS, "Casi idénticas")
        elif score >= 85:
            return (DesignSystem.COLOR_PRIMARY, "Muy similares")
        elif score >= 75:
            return (DesignSystem.COLOR_INFO, "Similares")
        elif score >= 65:
            return (DesignSystem.COLOR_WARNING, "Algo similares")
        else:
            return (DesignSystem.COLOR_ERROR, "Poco similares")
    
    def _get_similarity_description(self, score: float) -> str:
        """Retorna una descripción explicativa del nivel de similitud"""
        if score >= 95:
            return "Las imágenes son prácticamente idénticas. Diferencias mínimas o imperceptibles."
        elif score >= 85:
            return "Las imágenes son muy parecidas. Pueden tener pequeñas diferencias en calidad, resolución o edición."
        elif score >= 75:
            return "Las imágenes comparten características significativas pero tienen diferencias notables."
        elif score >= 65:
            return "Las imágenes tienen similitudes pero también diferencias considerables. Revisa cuidadosamente."
        else:
            return "Las imágenes tienen pocas similitudes. Verifica que realmente sean duplicados antes de eliminar."

    def _create_thumbnail(self, file_path: Path) -> tuple:
        """Crea una miniatura para un archivo de imagen o video.
        
        Returns:
            tuple: (QLabel con la miniatura, bool indicando si es video)
        """
        try:
            # Extensiones soportadas
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.heic', '.heif'}
            video_extensions = {'.mov', '.mp4', '.avi', '.mkv', '.m4v', '.webm'}
            
            file_ext = file_path.suffix.lower()
            is_video = file_ext in video_extensions
            
            # Si no es imagen ni video, retornar None
            if file_ext not in image_extensions and file_ext not in video_extensions:
                return None, False
            
            pixmap = None
            
            # Para videos, extraer un frame fijo (frame 1 segundo)
            if is_video:
                try:
                    import cv2
                    import numpy as np
                    from PyQt6.QtGui import QImage
                    
                    # Abrir video
                    cap = cv2.VideoCapture(str(file_path))
                    
                    # Ir al frame del segundo 1 (frame 30 aprox si es 30fps)
                    # Usamos frame fijo para que sea consistente entre comparaciones
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
                    
                    # Leer frame
                    ret, frame = cap.read()
                    cap.release()
                    
                    if ret:
                        # Convertir de BGR (OpenCV) a RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # Convertir a QImage
                        h, w, ch = frame_rgb.shape
                        bytes_per_line = ch * w
                        qimage = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                        
                        # Convertir a QPixmap
                        pixmap = QPixmap.fromImage(qimage)
                    
                except ImportError:
                    # OpenCV no disponible, intentar con otro método
                    pass
                except Exception:
                    pass
            else:
                # Para imágenes, intentar cargar con QPixmap
                pixmap = QPixmap(str(file_path))
                
                # Si QPixmap falla (puede pasar con HEIC), intentar con pillow
                if pixmap.isNull():
                    try:
                        from PIL import Image
                        from PyQt6.QtGui import QImage
                        import io
                        
                        # Cargar con Pillow y convertir a QPixmap
                        img = Image.open(str(file_path))
                        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                        
                        # Convertir PIL Image a QPixmap
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        
                        qimage = QImage()
                        qimage.loadFromData(img_byte_arr.read())
                        pixmap = QPixmap.fromImage(qimage)
                    except ImportError:
                        pass
                    except Exception:
                        pass

            if pixmap is None or pixmap.isNull():
                return None, is_video

            # Redimensionar manteniendo aspecto (150x150 máximo)
            scaled_pixmap = pixmap.scaled(
                Config.THUMBNAIL_SIZE, Config.THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            label = QLabel()
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedSize(Config.THUMBNAIL_SIZE, Config.THUMBNAIL_SIZE)
            label.setStyleSheet(DesignSystem.STYLE_DIALOG_LABEL_DISABLED)
            return label, is_video
        except Exception:
            return None, False

    def _update_frame_style(self, frame: QFrame, file_path: Path, state):
        """Actualiza el estilo visual del frame según el estado de selección"""
        if state == Qt.CheckState.Checked:
            frame.setStyleSheet("""
                QFrame {
                    border: 2px solid #DC3545;
                    background-color: #FFFFFF;
                    border-radius: 6px;
                }
            """)
        else:
            frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #CED4DA;
                    background-color: #FFFFFF;
                    border-radius: 6px;
                }
            """)

    def _on_selection_changed(self, file_path, state):
        """Maneja cambios en la selección"""
        if self.current_group_index not in self.selections:
            self.selections[self.current_group_index] = []
        # Qt6 emite state como int: 0 (Unchecked), 2 (Checked)
        if state == Qt.CheckState.Checked.value or state == Qt.CheckState.Checked:
            if file_path not in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].append(file_path)
        else:
            if file_path in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].remove(file_path)
        self._update_summary()
    
    def _load_initial_results(self):
        """Carga resultados iniciales con sensibilidad predeterminada."""
        self._update_results(self.current_sensitivity)
    
    def _on_slider_value_changed(self, value: int):
        """
        Se llama mientras el usuario mueve el slider.
        
        Solo actualiza el display numérico, no recalcula todavía
        para dar feedback inmediato sin lag.
        
        Args:
            value: Nuevo valor del slider (30-100)
        """
        self.current_sensitivity = value
        # Actualizar solo el texto de estadísticas actuales
        self.stats_label.setText(
            f"Sensibilidad: {value}% | "
            f"Grupos: {self.current_result.total_groups if self.current_result else 0} | "
            f"Espacio recuperable: "
            f"{format_size(self.current_result.space_potential if self.current_result else 0)}"
        )
    
    def _on_slider_released(self):
        """Se llama cuando el usuario suelta el slider."""
        # Recalcular grupos con nueva sensibilidad
        self._update_results(self.current_sensitivity)
    
    def _update_results(self, sensitivity: int):
        """
        Actualiza la UI con resultados de nueva sensibilidad.
        
        MUY RÁPIDO (< 1 segundo) porque usa hashes pre-calculados.
        
        Args:
            sensitivity: Sensibilidad de detección (30-100)
        """
        # Obtener grupos con nueva sensibilidad (RÁPIDO)
        self.current_result = self.analysis.get_groups(sensitivity)
        
        # Guardar todos los grupos (sin filtrar) para poder aplicar filtros
        self.all_groups = self.current_result.groups.copy()
        
        # LOG: Mostrar conteo antes de filtrar
        from utils.logger import get_logger
        logger = get_logger('SimilarFilesDialog')
        logger.info(f"Sensibilidad {sensitivity}%: {len(self.all_groups)} grupos ANTES de filtrar")
        
        # Actualizar estadísticas en la card de sensibilidad
        self.stats_label.setText(
            f"Sensibilidad: {sensitivity}% | "
            f"Grupos totales: {self.current_result.total_groups} | "
            f"Espacio recuperable: "
            f"{format_size(self.current_result.space_potential)}"
        )
        
        # Actualizar métricas del header compacto (con valores sin filtrar)
        self._update_header_metrics(
            groups=self.current_result.total_groups,
            duplicates=self.current_result.total_duplicates,
            space=self.current_result.space_potential
        )
        
        # Limpiar selecciones previas (los grupos han cambiado)
        self.selections.clear()
        
        # Aplicar filtros actuales
        self._apply_current_filters()
    
    def _show_no_groups_message(self):
        """Muestra mensaje cuando no hay grupos con la sensibilidad actual."""
        # Limpiar layout del contenedor de grupos
        for i in reversed(range(self.group_layout.count())):
            widget = self.group_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Mostrar mensaje informativo
        no_groups_label = QLabel(
            "No se encontraron grupos con esta sensibilidad.\n\n"
            "Prueba reducir la sensibilidad (mover slider a la izquierda) "
            "para detectar archivos menos similares."
        )
        no_groups_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_groups_label.setWordWrap(True)
        no_groups_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_40}px;
            }}
        """)
        self.group_layout.addWidget(no_groups_label)
        
        # Actualizar etiqueta de navegación
        self.group_label.setText("Sin grupos")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        
        # Actualizar resumen
        self.summary_label.setText(
            "<b>No hay archivos seleccionados.</b>"
        )
        self.ok_btn.setEnabled(False)
    
    def _get_dialog_styles(self) -> str:
        """Retorna los estilos CSS para el diálogo."""
        return f"""
            QDialog {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
            }}
            
            QFrame#sensitivity_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
            
            QLabel#card_title {{
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QLabel#slider_label {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QSlider#sensitivity_slider {{
                height: 24px;
            }}
            
            QSlider#sensitivity_slider::groove:horizontal {{
                background: {DesignSystem.COLOR_SECONDARY};
                height: 4px;
                border-radius: 2px;
            }}
            
            QSlider#sensitivity_slider::handle:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
                border: 2px solid {DesignSystem.COLOR_SURFACE};
            }}
            
            QSlider#sensitivity_slider::handle:horizontal:hover {{
                background: {DesignSystem.COLOR_PRIMARY_HOVER};
                width: 24px;
                height: 24px;
                margin: -10px 0;
                border-radius: 12px;
            }}
            
            QSlider#sensitivity_slider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 2px;
            }}
            
            QLabel#stats_label {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                color: {DesignSystem.COLOR_PRIMARY};
            }}
            
            QLabel#help_label {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QFrame#warning_frame {{
                background-color: {DesignSystem.COLOR_BG_4};
                border: 1px solid {DesignSystem.COLOR_WARNING};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            
            QLabel#warning_text {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QLabel#group_label {{
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                color: {DesignSystem.COLOR_TEXT};
            }}
        """

    # ========================================================================
    # FILTROS Y ESTRATEGIAS
    # ========================================================================
    
    def _on_filters_changed(self):
        """Callback cuando cambian los valores de los filtros."""
        self.filter_min_files = self.min_files_spin.value()
        self.filter_min_size_mb = self.min_size_spin.value()
        self._apply_current_filters()
    
    def _reset_filters(self):
        """Resetea los filtros a valores predeterminados."""
        self.min_files_spin.setValue(2)
        self.min_size_spin.setValue(0)
        # _on_filters_changed será llamado automáticamente por valueChanged
    
    def _apply_current_filters(self):
        """
        Aplica los filtros actuales a los grupos sin reanalizar.
        
        Filtra self.all_groups y actualiza self.analysis.groups con el resultado.
        """
        if not self.all_groups:
            self._show_no_groups_message()
            return
        
        # LOG: Mostrar estado de filtros
        from utils.logger import get_logger
        logger = get_logger('SimilarFilesDialog')
        logger.info(
            f"Aplicando filtros: min_files={self.filter_min_files}, "
            f"min_size_mb={self.filter_min_size_mb}"
        )
        
        # Aplicar filtros
        filtered_groups = []
        min_size_bytes = self.filter_min_size_mb * 1024 * 1024
        
        for group in self.all_groups:
            # Filtro 1: Mínimo archivos por grupo
            if len(group.files) < self.filter_min_files:
                logger.debug(f"Grupo filtrado: {len(group.files)} archivos < {self.filter_min_files}")
                continue
            
            # Filtro 2: Al menos un archivo debe cumplir el tamaño mínimo
            if min_size_bytes > 0:
                if not any(f.stat().st_size >= min_size_bytes for f in group.files):
                    logger.debug(f"Grupo filtrado: ningún archivo >= {self.filter_min_size_mb}MB")
                    continue
            
            filtered_groups.append(group)
        
        logger.info(f"Grupos DESPUÉS de filtrar: {len(filtered_groups)}")
        
        # Actualizar grupos mostrados
        self.analysis.groups = filtered_groups
        
        # Actualizar métricas del header con grupos FILTRADOS
        filtered_duplicates = sum(len(g.files) - 1 for g in filtered_groups)
        filtered_space = sum((len(g.files) - 1) * g.files[0].stat().st_size for g in filtered_groups if g.files)
        
        self._update_header_metrics(
            groups=len(filtered_groups),
            duplicates=filtered_duplicates,
            space=filtered_space
        )
        
        # Resetear al primer grupo
        self.current_group_index = 0
        
        # Recargar visualización
        if filtered_groups:
            self._load_group(0)
        else:
            self._show_no_groups_message()
    
    def _apply_strategy(self, strategy: str):
        """
        Aplica una estrategia de selección automática a todos los grupos visibles.
        
        Args:
            strategy: 'keep_first', 'keep_last', 'keep_largest', 'keep_smallest'
        """
        if not self.analysis.groups:
            return
        
        # Limpiar selecciones anteriores
        self.selections.clear()
        
        # Aplicar estrategia a cada grupo visible
        for idx, group in enumerate(self.analysis.groups):
            if len(group.files) < 2:
                continue
            
            if strategy == 'keep_first':
                # Eliminar todos menos el primero
                to_delete = group.files[1:]
            elif strategy == 'keep_last':
                # Eliminar todos menos el último
                to_delete = group.files[:-1]
            elif strategy == 'keep_largest':
                # Ordenar por tamaño descendente, eliminar todos menos el mayor
                sorted_files = sorted(group.files, key=lambda f: f.stat().st_size, reverse=True)
                to_delete = sorted_files[1:]
            elif strategy == 'keep_smallest':
                # Ordenar por tamaño ascendente, eliminar todos menos el menor
                sorted_files = sorted(group.files, key=lambda f: f.stat().st_size)
                to_delete = sorted_files[1:]
            else:
                continue
            
            self.selections[idx] = list(to_delete)
        
        # Recargar grupo actual para actualizar checkboxes
        self._load_group(self.current_group_index)
        
        # Mostrar mensaje de confirmación
        total_selected = sum(len(v) for v in self.selections.values())
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Estrategia aplicada",
            f"Se seleccionaron {total_selected} archivos para eliminar en "
            f"{len(self.selections)} grupos.\n\n"
            f"Revisa la selección antes de proceder."
        )
    
    def _clear_all_selections(self):
        """Limpia todas las selecciones de archivos."""
        self.selections.clear()
        self._load_group(self.current_group_index)
        self._update_summary()
    
    # ========================================================================
    # NAVEGACIÓN
    # ========================================================================

    def _previous_group(self):

        """Navega al grupo anterior (circular: desde el primero va al último)"""
        # Solo navegar si hay grupos
        if not self.analysis.groups:
            return
        
        total_groups = len(self.analysis.groups)
        if self.current_group_index == 0:
            # Estamos en el primero, ir al último
            self._load_group(total_groups - 1)
        else:
            self._load_group(self.current_group_index - 1)

    def _next_group(self):
        """Navega al grupo siguiente (circular: desde el último va al primero)"""
        # Solo navegar si hay grupos
        if not self.analysis.groups:
            return
        
        total_groups = len(self.analysis.groups)
        if self.current_group_index >= total_groups - 1:
            # Estamos en el último, ir al primero
            self._load_group(0)
        else:
            self._load_group(self.current_group_index + 1)

    def _update_summary(self):
        """Actualiza el resumen de archivos seleccionados y la métrica del header"""
        total_selected = sum(len(files) for files in self.selections.values())
        total_size = 0
        for files in self.selections.values():
            total_size += sum(f.stat().st_size for f in files)
        self.summary_label.setText(
            f"<b>Archivos seleccionados:</b> {total_selected} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Espacio a liberar:</b> {format_size(total_size)}"
        )
        self.ok_btn.setEnabled(total_selected > 0)
        
        # Actualizar métrica "Recuperable" en el header con el espacio de archivos seleccionados
        # Si no hay selecciones, mostrar el potencial total
        space_to_show = total_size if total_selected > 0 else (self.current_result.space_potential if self.current_result else 0)
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(space_to_show))
    
    def _update_header_metrics(self, groups: int, duplicates: int, space: int):
        """Actualiza las métricas del header compacto.
        
        Args:
            groups: Número de grupos detectados
            duplicates: Número total de duplicados
            space: Espacio recuperable en bytes
        """
        # Buscar y actualizar los QLabel de las métricas existentes en lugar de recrear el header
        # El header tiene un layout horizontal con métricas al final
        main_layout = self.header_frame.layout()
        if not main_layout:
            return
        
        # Las métricas están en un QHBoxLayout al final del main_layout
        # Buscar el último layout que contiene las métricas
        metrics_layout = None
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item and item.layout() and isinstance(item.layout(), QHBoxLayout):
                # El último QHBoxLayout con múltiples widgets es el de métricas
                if item.layout().count() > 1:
                    metrics_layout = item.layout()
        
        if not metrics_layout:
            return
        
        # Actualizar cada métrica (son QWidget con QVBoxLayout conteniendo value_label y label_widget)
        metrics_data = [
            str(groups),
            str(duplicates),
            format_size(space)
        ]
        
        for idx, new_value in enumerate(metrics_data):
            if idx < metrics_layout.count():
                metric_widget = metrics_layout.itemAt(idx).widget()
                if metric_widget and metric_widget.layout():
                    # El primer hijo del layout es el value_label
                    value_label = metric_widget.layout().itemAt(0).widget()
                    if value_label and isinstance(value_label, QLabel):
                        value_label.setText(new_value)


    def accept(self):
        # Crear grupos filtrados solo con archivos a eliminar
        groups_to_process = []
        for group_idx, files_to_delete in self.selections.items():
            if files_to_delete:
                original_group = self.analysis.groups[group_idx]
                groups_to_process.append(DuplicateGroup(
                    hash_value=original_group.hash_value,
                    files=files_to_delete,
                    total_size=sum(f.stat().st_size for f in files_to_delete),
                    similarity_score=original_group.similarity_score
                ))
        self.accepted_plan = {
            'groups': groups_to_process,
            'keep_strategy': 'manual',
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        super().accept()

    def _show_image_preview(self, image_path: Path):
        """Muestra un diálogo con preview ampliado de la imagen."""
        preview_dialog = ImagePreviewDialog(image_path, self)
        preview_dialog.exec()
    
    def _open_file(self, file_path: Path):
        """Abre un archivo con la aplicación predeterminada del sistema operativo"""
        if file_path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Archivo no encontrado", f"No se encontró el archivo:\n{file_path}")
    
    def _show_file_context_menu(self, position, file_path: Path, widget: QWidget):
        """Muestra menú contextual Material Design para un archivo con opciones de ver detalles"""
        menu = QMenu(self)
        
        # Estilo Material Design para el menú
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px;
            }}
            QMenu::item {{
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_16}px;
                border-radius: {DesignSystem.RADIUS_SMALL}px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
            QMenu::item:selected {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {DesignSystem.COLOR_BORDER};
                margin: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
            }}
        """)
        
        # Opción para ver detalles del archivo
        details_action = menu.addAction(icon_manager.get_icon('info', size=16), "Ver detalles del archivo")
        details_action.triggered.connect(lambda: self._show_file_details(file_path))
        
        menu.addSeparator()
        
        # Opción para abrir el archivo
        open_action = menu.addAction(icon_manager.get_icon('file', size=16), "Abrir archivo")
        open_action.triggered.connect(lambda: self._open_file(file_path))
        
        # Opción para abrir la carpeta
        from .dialog_utils import open_folder
        open_folder_action = menu.addAction(icon_manager.get_icon('folder-open', size=16), "Abrir carpeta")
        open_folder_action.triggered.connect(lambda: open_folder(file_path.parent, self))
        
        # Mostrar el menú en la posición exacta del cursor
        menu.exec(QCursor.pos())
    
    def _show_file_details(self, file_path: Path):
        """Muestra diálogo con detalles del archivo"""
        # Obtener el grupo actual para incluir contexto
        current_group = self.analysis.groups[self.current_group_index]
        
        # Preparar información adicional
        additional_info = {
            'file_type': Config.get_file_type(file_path),
            'metadata': {
                'Grupo': f'{self.current_group_index + 1} de {len(self.analysis.groups)}',
                'Similitud del grupo': f'{current_group.similarity_score:.1f}%',
                'Archivos en grupo': str(len(current_group.files)),
                'Tamaño total del grupo': format_size(current_group.total_size),
            }
        }
        
        # Mostrar diálogo de detalles usando la utilidad
        show_file_details_dialog(file_path, self, additional_info)
