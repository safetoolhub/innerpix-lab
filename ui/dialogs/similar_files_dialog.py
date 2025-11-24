"""
Diálogo de gestión de archivos similares con diseño moderno y profesional.
Permite ajustar la sensibilidad de detección en tiempo real y gestionar
los grupos de archivos similares detectados con una experiencia de usuario fluida.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSlider, QPushButton,
    QDialogButtonBox, QCheckBox, QGroupBox, QScrollArea, QWidget,
    QGridLayout, QSizePolicy, QProgressBar, QMenu, QDialog, QSpinBox
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QDesktopServices, QCursor, QImage, QColor, QIcon
from config import Config
from services.similar_files_detector import SimilarFilesAnalysis
from services.result_types import DuplicateGroup
from utils.format_utils import format_size
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from .base_dialog import BaseDialog

class ImagePreviewDialog(QDialog):
    """Diálogo modal para mostrar vista previa ampliada de una imagen con diseño moderno."""
    
    def __init__(self, image_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Vista previa - {image_path.name}")
        self.setModal(True)
        self.resize(1000, 800)
        self.setStyleSheet(f"background-color: {DesignSystem.COLOR_BACKGROUND};")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar superior
        toolbar = QFrame()
        toolbar.setStyleSheet(f"background-color: {DesignSystem.COLOR_SURFACE}; border-bottom: 1px solid {DesignSystem.COLOR_BORDER};")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(DesignSystem.SPACE_16, DesignSystem.SPACE_8, DesignSystem.SPACE_16, DesignSystem.SPACE_8)
        
        file_info = QLabel(f"{image_path.name}")
        file_info.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; font-size: {DesignSystem.FONT_SIZE_MD}px; color: {DesignSystem.COLOR_TEXT};")
        toolbar_layout.addWidget(file_info)
        toolbar_layout.addStretch()
        
        layout.addWidget(toolbar)
        
        # Scroll area para la imagen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setStyleSheet(f"background-color: {DesignSystem.COLOR_BACKGROUND}; border: none;")
        
        # Label con imagen
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            # Escalar si es muy grande, pero mantener calidad
            screen_size = self.screen().availableSize()
            max_w = screen_size.width() * 0.8
            max_h = screen_size.height() * 0.8
            
            if pixmap.width() > max_w or pixmap.height() > max_h:
                pixmap = pixmap.scaled(
                    int(max_w), int(max_h),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            image_label.setPixmap(pixmap)
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
        button_container.setStyleSheet(f"background-color: {DesignSystem.COLOR_SURFACE}; border-top: 1px solid {DesignSystem.COLOR_BORDER};")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
            DesignSystem.SPACE_16, DesignSystem.SPACE_12
        )
        
        close_btn = QPushButton("Cerrar")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        close_btn.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addWidget(button_container)


class SimilarFilesDialog(BaseDialog):
    """
    Diálogo para gestionar archivos similares con UX mejorado.
    """

    # Constantes para navegación progresiva (desde Config)
    MAX_GROUPS_WARNING = Config.SIMILAR_FILES_MAX_GROUPS_WARNING
    MAX_GROUPS_NAVIGABLE = Config.SIMILAR_FILES_MAX_GROUPS_NAVIGABLE
    LARGE_DATASET_THRESHOLD = Config.SIMILAR_FILES_LARGE_DATASET_THRESHOLD
    
    def __init__(self, analysis: SimilarFilesAnalysis, parent=None):
        super().__init__(parent)
        
        self.analysis = analysis
        
        # Ajustar sensibilidad inicial según tamaño del dataset
        # Para datasets grandes (>10K archivos), iniciar con sensibilidad 100%
        # para generar el mínimo de grupos y evitar bloqueos
        total_files = len(analysis.perceptual_hashes)
        if total_files >= self.LARGE_DATASET_THRESHOLD:
            self.current_sensitivity = Config.SIMILAR_FILES_LARGE_DATASET_SENSITIVITY  # 100% para datasets grandes
        else:
            self.current_sensitivity = Config.SIMILAR_FILES_DEFAULT_SENSITIVITY  # 85% para datasets pequeños
        
        self.current_result = None
        self.current_group_index = 0
        self.selections = {}  # {group_index: [files_to_delete]}
        
        # Filtros
        self.filter_min_files = 2
        self.filter_min_size_mb = 0
        self.all_groups = []
        self.filtered_groups = []  # Grupos después de filtrar
        self.navigable_groups = []  # Grupos limitados para navegación
        
        # Lazy loading progresivo
        self.files_processed = 0  # Cuántos archivos hemos procesado
        self.total_files = len(analysis.perceptual_hashes)
        self.batch_size = Config.SIMILAR_FILES_INITIAL_BATCH_SIZE
        
        self.accepted_plan = None
        
        self._setup_ui()
        # Cargar primer batch DESPUÉS de que el UI esté listo (usando QTimer)
        # Esto evita crashes de segmentation fault
        QTimer.singleShot(100, self._load_next_batch)
    
    def _setup_ui(self):
        """Configura la interfaz moderna del diálogo."""
        self.setWindowTitle("Gestionar Archivos Similares")
        self.setModal(True)
        self.resize(1280, 900)
        self.setMinimumSize(1100, 750)
        
        # Estilo base del diálogo
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
            }}
            QLabel {{
                background-color: transparent;
            }}
        """)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Header Compacto (usando método estandarizado de BaseDialog)
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='content-duplicate',
            title='Archivos Similares',
            description='Detecta y gestiona imágenes visualmente idénticas',
            metrics=[
                {'value': '0', 'label': 'Grupos', 'color': DesignSystem.COLOR_PRIMARY},
                {'value': '0', 'label': 'Duplicados', 'color': DesignSystem.COLOR_WARNING},
                {'value': '0 B', 'label': 'Recuperable', 'color': DesignSystem.COLOR_SUCCESS}
            ]
        )
        main_layout.addWidget(self.header_frame)
        
        # Contenedor principal con padding
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setSpacing(DesignSystem.SPACE_16)
        content_layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_20, DesignSystem.SPACE_24, DesignSystem.SPACE_20)
        
        # 2. Panel de Control (Sensibilidad + Filtros + Acciones Rápidas)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(DesignSystem.SPACE_16)
        
        sensitivity_card = self._create_sensitivity_card()
        filters_card = self._create_filters_card()
        quick_actions_card = self._create_quick_actions_card()
        
        # Ajustar stretch factors para balancear (3:2:3)
        controls_layout.addWidget(sensitivity_card, stretch=3)
        controls_layout.addWidget(filters_card, stretch=2)
        controls_layout.addWidget(quick_actions_card, stretch=3)
        
        content_layout.addLayout(controls_layout)
        
        # 3. Área de Trabajo (Navegación + Grid)
        workspace_card = QFrame()
        workspace_card.setObjectName("workspace_card")
        workspace_card.setStyleSheet(f"""
            QFrame#workspace_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """)
        workspace_layout = QVBoxLayout(workspace_card)
        workspace_layout.setSpacing(0)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        
        # Barra de herramientas del workspace (Solo Navegación)
        workspace_toolbar = self._create_workspace_toolbar()
        workspace_layout.addWidget(workspace_toolbar)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER_LIGHT};")
        workspace_layout.addWidget(separator)
        
        # Contenedor del grupo actual (Grid de imágenes)
        self.group_container = QWidget()
        self.group_layout = QVBoxLayout(self.group_container)
        self.group_layout.setContentsMargins(DesignSystem.SPACE_20, DesignSystem.SPACE_20, DesignSystem.SPACE_20, DesignSystem.SPACE_20)
        self.group_layout.setSpacing(DesignSystem.SPACE_16)
        
        workspace_layout.addWidget(self.group_container, stretch=1)
        
        content_layout.addWidget(workspace_card, stretch=1)
        
        main_layout.addWidget(content_wrapper, stretch=1)
        
        # 4. Footer (Opciones de seguridad + Botones)
        # Opciones de seguridad (usando método estándar de BaseDialog)
        security_options = self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de eliminar",
            dry_run_label="Modo simulación (no eliminar archivos realmente)"
        )
        content_layout.addWidget(security_options)
        
        # Botones de acción
        button_box = self.make_ok_cancel_buttons(
            ok_text="Eliminar Seleccionados",
            ok_enabled=False,
            button_style='danger'
        )
        self.delete_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        content_layout.addWidget(button_box)



    def _create_sensitivity_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sensitivity_card")
        card.setStyleSheet(f"""
            QFrame#sensitivity_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """)
        layout = QVBoxLayout(card)
        # Reducir márgenes para hacerlo más compacto
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        # Header de la card
        header = QHBoxLayout()
        icon = icon_manager.create_icon_label('tune', size=16, color=DesignSystem.COLOR_TEXT)
        title = QLabel("Sensibilidad")
        title.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; font-size: {DesignSystem.FONT_SIZE_BASE}px;")
        
        self.sensitivity_value_label = QLabel(f"{self.current_sensitivity}%")
        self.sensitivity_value_label.setStyleSheet(f"color: {DesignSystem.COLOR_PRIMARY}; font-weight: {DesignSystem.FONT_WEIGHT_BOLD};")
        
        header.addWidget(icon)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.sensitivity_value_label)
        layout.addLayout(header)
        
        # Slider
        slider_container = QHBoxLayout()
        
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(30, 100)
        self.sensitivity_slider.setValue(self.current_sensitivity)
        self.sensitivity_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sensitivity_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                height: 4px;
                background: {DesignSystem.COLOR_BACKGROUND};
                margin: 2px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border: 2px solid {DesignSystem.COLOR_SURFACE};
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 9px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {DesignSystem.COLOR_PRIMARY_HOVER};
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 10px;
            }}
            QSlider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 2px;
            }}
        """)
        
        slider_container.addWidget(QLabel("Min", styleSheet=f"font-size: {DesignSystem.FONT_SIZE_XS}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};"))
        slider_container.addWidget(self.sensitivity_slider, 1)
        slider_container.addWidget(QLabel("Max", styleSheet=f"font-size: {DesignSystem.FONT_SIZE_XS}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};"))
        
        layout.addLayout(slider_container)
        
        # Conexiones
        self.sensitivity_slider.valueChanged.connect(self._on_slider_value_changed)
        self.sensitivity_slider.sliderReleased.connect(self._on_slider_released)
        
        # Info adicional para datasets grandes
        total_files = len(self.analysis.perceptual_hashes)
        if total_files >= self.LARGE_DATASET_THRESHOLD:
            info_label = QLabel(
                f"ℹ️ Dataset grande ({total_files:,} archivos)\n"
                f"Ajusta la sensibilidad y pulsa el botón central para generar grupos.\n"
                f"⚡ Mayor sensibilidad = menos grupos, más rápido"
            )
            info_label.setWordWrap(True)
            info_label.setStyleSheet(f"""
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                background-color: {DesignSystem.COLOR_WARNING_BG};
                padding: {DesignSystem.SPACE_8}px;
                border-radius: {DesignSystem.RADIUS_SM}px;
            """)
            layout.addWidget(info_label)
            
            # Warning extra para dejar claro que puede ser lento
            warning_label = QLabel(
                "⚠️ Nota: Ajustar la sensibilidad puede tomar unos segundos."
            )
            warning_label.setStyleSheet(f"""
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                font-style: italic;
                margin-top: {DesignSystem.SPACE_4}px;
            """)
            layout.addWidget(warning_label)
        
        return card

    def _create_filters_card(self) -> QFrame:
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
        # Reducir márgenes
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        # Header
        header = QHBoxLayout()
        header.setSpacing(DesignSystem.SPACE_8)
        header.addWidget(icon_manager.create_icon_label('filter-variant', size=16))
        header.addWidget(QLabel("Filtros", styleSheet=f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; font-size: {DesignSystem.FONT_SIZE_BASE}px;"))
        header.addStretch()
        
        reset_btn = QPushButton("Reset")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                color: {DesignSystem.COLOR_PRIMARY};
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                padding: 0;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        reset_btn.clicked.connect(self._reset_filters)
        header.addWidget(reset_btn)
        
        layout.addLayout(header)
        
        # Inputs en una sola fila para ahorrar espacio vertical
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(DesignSystem.SPACE_12)
        
        # Min Archivos
        files_layout = QHBoxLayout()
        files_layout.setSpacing(DesignSystem.SPACE_4)
        files_layout.addWidget(QLabel("Archivos:", styleSheet=f"font-size: {DesignSystem.FONT_SIZE_SM}px;"))
        
        from ui.widgets.custom_spinbox import CustomSpinBox
        self.min_files_spin = CustomSpinBox()
        self.min_files_spin.setRange(2, 50)
        self.min_files_spin.setValue(self.filter_min_files)
        self.min_files_spin.setFixedWidth(80)
        self.min_files_spin.valueChanged.connect(self._on_filters_changed)
        files_layout.addWidget(self.min_files_spin)
        
        inputs_layout.addLayout(files_layout)
        
        # Min Tamaño
        size_layout = QHBoxLayout()
        size_layout.setSpacing(DesignSystem.SPACE_4)
        size_layout.addWidget(QLabel("MB:", styleSheet=f"font-size: {DesignSystem.FONT_SIZE_SM}px;"))
        
        self.min_size_spin = CustomSpinBox()
        self.min_size_spin.setRange(0, 1000)
        self.min_size_spin.setValue(self.filter_min_size_mb)
        self.min_size_spin.setFixedWidth(80)
        self.min_size_spin.valueChanged.connect(self._on_filters_changed)
        size_layout.addWidget(self.min_size_spin)
        
        inputs_layout.addLayout(size_layout)
        
        layout.addLayout(inputs_layout)
        
        # Warning para filtros en datasets grandes
        total_files = len(self.analysis.perceptual_hashes)
        if total_files >= self.LARGE_DATASET_THRESHOLD:
            filter_warning = QLabel("⚠️ Filtrar puede ser lento con muchos archivos")
            filter_warning.setStyleSheet(f"""
                color: {DesignSystem.COLOR_WARNING};
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                margin-top: {DesignSystem.SPACE_4}px;
            """)
            filter_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(filter_warning)
        
        return card

    def _create_quick_actions_card(self) -> QFrame:
        """Nueva card para acciones rápidas (Smart Select)"""
        card = QFrame()
        card.setObjectName("quick_actions_card")
        card.setStyleSheet(f"""
            QFrame#quick_actions_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        # Header
        header = QHBoxLayout()
        header.addWidget(icon_manager.create_icon_label('flash', size=16, color=DesignSystem.COLOR_WARNING))
        header.addWidget(QLabel("Selección Rápida", styleSheet=f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; font-size: {DesignSystem.FONT_SIZE_BASE}px;"))
        header.addStretch()
        
        # Botón Limpiar (mini)
        clear_btn = QPushButton("Limpiar")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                padding: 0;
            }}
            QPushButton:hover {{ color: {DesignSystem.COLOR_DANGER}; }}
        """)
        clear_btn.clicked.connect(self._clear_current_group_selection)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        # Botones de acción
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(DesignSystem.SPACE_8)
        
        strategies = [
            ("1º", "keep_first", "Mantener primero"),
            ("Último", "keep_last", "Mantener último"),
            ("Mejor", "keep_largest", "Mantener mejor calidad"),
        ]
        
        for text, strategy, tooltip in strategies:
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DesignSystem.COLOR_BACKGROUND};
                    border: 1px solid {DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: 4px 8px;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    color: {DesignSystem.COLOR_TEXT};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                    border-color: {DesignSystem.COLOR_PRIMARY};
                    color: {DesignSystem.COLOR_PRIMARY};
                }}
            """)
            btn.clicked.connect(lambda checked, s=strategy: self._apply_strategy_current_group(s))
            actions_layout.addWidget(btn)
            
        layout.addLayout(actions_layout)
        
        return card

    def _create_workspace_toolbar(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_16, DesignSystem.SPACE_12, DesignSystem.SPACE_16, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Navegación izquierda
        self.prev_btn = self.make_styled_button(
            icon_name='chevron-left',
            button_style='secondary',
            tooltip="Grupo Anterior"
        )
        self.prev_btn.clicked.connect(self._previous_group)
        
        self.group_counter_label = QLabel("Grupo 0 de 0")
        self.group_counter_label.setMinimumWidth(200)  # Asegurar espacio suficiente
        self.group_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_counter_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT};")
        
        self.next_btn = self.make_styled_button(
            icon_name='chevron-right',
            button_style='secondary',
            tooltip="Siguiente Grupo"
        )
        self.next_btn.clicked.connect(self._next_group)
        
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(DesignSystem.SPACE_8)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.group_counter_label)
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
        
        layout.addStretch()
        
        # Botón "Cargar más grupos" (permanente en toolbar)
        self.load_more_btn = self.make_styled_button(
            text="Cargar más grupos",
            icon_name='plus-circle',
            button_style='primary',
            tooltip="Cargar siguiente lote de archivos para análisis"
        )
        self.load_more_btn.clicked.connect(self._load_next_batch)
        self.load_more_btn.setVisible(False)  # Oculto hasta que sea necesario
        layout.addWidget(self.load_more_btn)
        
        layout.addStretch()
        
        # Separador vertical
        v_sep = QFrame()
        v_sep.setFrameShape(QFrame.Shape.VLine)
        v_sep.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER};")
        layout.addWidget(v_sep)
        
        # Contador de archivos seleccionados (Estabilizado)
        selection_container = QHBoxLayout()
        selection_container.setSpacing(DesignSystem.SPACE_8)
        
        selection_icon = icon_manager.create_icon_label('checkbox-marked-circle', size=18, color=DesignSystem.COLOR_DANGER)
        selection_container.addWidget(selection_icon)
        
        self.global_summary_label = QLabel("0 archivos seleccionados (0 B)")
        # Fijar ancho mínimo para evitar saltos
        self.global_summary_label.setMinimumWidth(250) 
        self.global_summary_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.global_summary_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; color: {DesignSystem.COLOR_TEXT};")
        selection_container.addWidget(self.global_summary_label)
        
        layout.addLayout(selection_container)
        
        return container



    # ================= LÓGICA DE NEGOCIO =================

    def _show_loading_message(self):
        """Muestra mensaje mientras se carga el primer batch."""
        # Limpiar contenedor
        for i in reversed(range(self.group_layout.count())):
            w = self.group_layout.itemAt(i).widget()
            if w: w.setParent(None)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Icono de carga
        icon_label = icon_manager.create_icon_label(
            'loading',
            size=48,
            color=DesignSystem.COLOR_PRIMARY
        )
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Mensaje
        msg = QLabel("Generando primeros grupos...\n\nEsto solo toma unos segundos")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_MD}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(msg)
        
        self.group_layout.addWidget(container)
        
        # Deshabilitar navegación
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.group_counter_label.setText("Cargando...")
    
    def _load_next_batch(self):
        """Carga el siguiente batch de archivos para clustering incremental."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from utils.logger import get_logger
        
        logger = get_logger('SimilarFilesDialog')
        
        try:
            # Determinar cuántos archivos procesar
            if self.files_processed == 0:
                batch = Config.SIMILAR_FILES_INITIAL_BATCH_SIZE
            else:
                batch = Config.SIMILAR_FILES_LOAD_MORE_BATCH_SIZE
            
            start_idx = self.files_processed
            end_idx = min(start_idx + batch, self.total_files)
            
            if start_idx >= self.total_files:
                logger.info("Todos los archivos ya procesados")
                return
            
            # Mostrar cursor de espera
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                # Obtener subset de hashes
                all_hashes = list(self.analysis.perceptual_hashes.items())
                batch_hashes = dict(all_hashes[start_idx:end_idx])
                existing_hashes = dict(all_hashes[:start_idx])
                
                logger.info(
                    f"Procesando batch {start_idx:,}-{end_idx:,} "
                    f"({end_idx - start_idx:,} archivos) con sensibilidad {self.current_sensitivity}%"
                )
                
                # Crear análisis temporal con subset
                from services.similar_files_detector import SimilarFilesAnalysis
                temp_analysis = SimilarFilesAnalysis()
                temp_analysis.workspace_path = self.analysis.workspace_path
                
                # Usar find_new_groups para comparar batch actual vs todo lo anterior
                batch_result = temp_analysis.find_new_groups(
                    new_hashes=batch_hashes,
                    existing_hashes=existing_hashes,
                    sensitivity=self.current_sensitivity
                )
                
                # Agregar grupos nuevos a la lista existente
                new_groups_count = len(batch_result.groups)
                self.all_groups.extend(batch_result.groups)
                
                logger.info(f"Batch completado: +{new_groups_count:,} grupos nuevos (total: {len(self.all_groups):,})")
                
                # Actualizar contador
                self.files_processed = end_idx
                
                # Aplicar filtros y mostrar
                self._apply_current_filters()
                
                # Si hay más archivos, mostrar botón "Cargar más"
                if self.files_processed < self.total_files:
                    self._show_load_more_button()
                # Si ya hay grupos navegables pero no estamos mostrando ninguno, mostrar el primero
                elif self.navigable_groups and self.current_group_index >= len(self.navigable_groups):
                    self.current_group_index = 0
                    self._load_group(0)
                
            finally:
                QApplication.restoreOverrideCursor()
        
        except Exception as e:
            logger.error(f"Error en _load_next_batch: {e}")
            QApplication.restoreOverrideCursor()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Error cargando batch: {str(e)}\n\nVer logs para detalles."
            )
            raise
    
    def _show_load_more_button(self):
        """Actualiza el botón permanente de la toolbar para mostrar archivos pendientes."""
        remaining = self.total_files - self.files_processed
        
        if remaining > 0:
            # Actualizar texto del botón en la toolbar
            self.load_more_btn.setText(f"Cargar más grupos ({remaining:,} pendientes)")
            self.load_more_btn.setVisible(True)
        else:
            # Ocultar si no hay más archivos pendientes
            self.load_more_btn.setVisible(False)

    def _load_initial_results(self):
        """Método legacy - ya no se llama al inicio."""
        self._update_results(self.current_sensitivity)

    def _on_slider_value_changed(self, value: int):
        self.current_sensitivity = value
        self.sensitivity_value_label.setText(f"{value}%")

    def _on_slider_released(self):
        # NO regenerar automáticamente - solo si ya hay grupos cargados
        if self.all_groups:
            self._update_results(self.current_sensitivity)

    def _update_results(self, sensitivity: int):
        """Regenera grupos desde cero con nueva sensibilidad (solo archivos ya procesados)."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from utils.logger import get_logger
        
        logger = get_logger('SimilarFilesDialog')
        
        if self.files_processed == 0:
            logger.warning("No hay archivos procesados aún")
            return
        
        # Mostrar cursor de espera
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # Recalcular grupos solo con archivos ya procesados
            all_hashes = list(self.analysis.perceptual_hashes.items())
            processed_hashes = dict(all_hashes[:self.files_processed])
            
            logger.info(
                f"Regenerando grupos con sensibilidad {sensitivity}% "
                f"({self.files_processed:,} archivos procesados)"
            )
            
            from services.similar_files_detector import SimilarFilesAnalysis
            temp_analysis = SimilarFilesAnalysis()
            temp_analysis.perceptual_hashes = processed_hashes
            temp_analysis.workspace_path = self.analysis.workspace_path
            temp_analysis.total_files = len(processed_hashes)
            
            result = temp_analysis.get_groups(sensitivity)
            self.all_groups = result.groups.copy()
            
            logger.info(f"Regenerados {len(self.all_groups):,} grupos")
            
            self.selections.clear()
            self._apply_current_filters()
            
        finally:
            QApplication.restoreOverrideCursor()

    def _on_filters_changed(self):
        self.filter_min_files = self.min_files_spin.value()
        self.filter_min_size_mb = self.min_size_spin.value()
        self._apply_current_filters()

    def _reset_filters(self):
        self.min_files_spin.setValue(2)
        self.min_size_spin.setValue(0)

    def _apply_current_filters(self):
        if not self.all_groups:
            self._show_no_groups_message()
            return

        filtered_groups = []
        min_size_bytes = self.filter_min_size_mb * 1024 * 1024
        
        for group in self.all_groups:
            if len(group.files) < self.filter_min_files:
                continue
            if min_size_bytes > 0:
                if not any(f.stat().st_size >= min_size_bytes for f in group.files):
                    continue
            filtered_groups.append(group)
        
        self.filtered_groups = filtered_groups
        self._apply_navigation_limit()
        
        self.current_group_index = 0
        if self.navigable_groups:
            self._load_group(0)
        else:
            self._show_no_groups_message()

    def _apply_navigation_limit(self):
        """Limita los grupos navegables para evitar bloqueo de UI."""
        total_groups = len(self.filtered_groups)
        
        if total_groups > self.MAX_GROUPS_WARNING:
            # Advertir al usuario
            from PyQt6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Muchos grupos detectados")
            
            if total_groups > self.MAX_GROUPS_NAVIGABLE:
                msg.setText(
                    f"Se detectaron {total_groups:,} grupos de similares.\n\n"
                    f"Por rendimiento, solo se mostrarán los primeros {self.MAX_GROUPS_NAVIGABLE:,} grupos.\n\n"
                    f"💡 Sugerencia: Aumenta la sensibilidad o aplica filtros más estrictos para reducir el número de grupos."
                )
                self.navigable_groups = self.filtered_groups[:self.MAX_GROUPS_NAVIGABLE]
            else:
                msg.setText(
                    f"Se detectaron {total_groups:,} grupos de similares.\n\n"
                    f"La navegación puede ser lenta con tantos grupos.\n\n"
                    f"💡 Sugerencia: Considera aumentar la sensibilidad o aplicar filtros para trabajar más cómodamente."
                )
                self.navigable_groups = self.filtered_groups
            
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
        else:
            self.navigable_groups = self.filtered_groups
        
        # Actualizar métricas del header
        self._update_header_metrics()
    
    def _update_header_metrics(self):
        groups = self.navigable_groups
        total_groups = len(groups)
        total_duplicates = sum(len(g.files) - 1 for g in groups)
        space_potential = sum((len(g.files) - 1) * g.files[0].stat().st_size for g in groups if g.files)
        
        # Mostrar advertencia si hay grupos ocultos
        groups_label = str(total_groups)
        if len(self.filtered_groups) > len(self.navigable_groups):
            groups_label = f"{total_groups} de {len(self.filtered_groups)}"
        
        # Usar el método estandarizado de BaseDialog para actualizar métricas
        self._update_header_metric(self.header_frame, 'Grupos', groups_label)
        self._update_header_metric(self.header_frame, 'Duplicados', str(total_duplicates))
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(space_potential))

    def _show_no_groups_message(self):
        # Limpiar contenedor
        for i in reversed(range(self.group_layout.count())):
            w = self.group_layout.itemAt(i).widget()
            if w: w.setParent(None)
            
        msg = QLabel("No se encontraron grupos con los filtros actuales.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_LG}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        self.group_layout.addWidget(msg)
        
        self.group_counter_label.setText("0 de 0")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

    def _load_group(self, index):
        if not 0 <= index < len(self.navigable_groups):
            return
            
        self.current_group_index = index
        group = self.navigable_groups[index]
        
        # Actualizar contador (mostrar navegables y total si difieren)
        total_display = len(self.navigable_groups)
        if len(self.filtered_groups) > len(self.navigable_groups):
            counter_text = f"Grupo {index + 1} de {total_display} ({len(self.filtered_groups)} totales)"
        else:
            counter_text = f"Grupo {index + 1} de {total_display}"
        
        self.group_counter_label.setText(counter_text)
        self.prev_btn.setEnabled(True)
        self.next_btn.setEnabled(True)
        
        # Limpiar contenedor
        for i in reversed(range(self.group_layout.count())):
            w = self.group_layout.itemAt(i).widget()
            if w: w.setParent(None)
            
        # Info de similitud del grupo
        sim_info = self._create_group_similarity_info(group)
        self.group_layout.addWidget(sim_info)
        
        # Grid de imágenes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(DesignSystem.SPACE_16)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        current_selection = self.selections.get(index, [])
        
        cols = 3
        for i, file_path in enumerate(group.files):
            row = i // cols
            col = i % cols
            card = self._create_file_card(file_path, file_path in current_selection)
            grid_layout.addWidget(card, row, col)
            
        scroll.setWidget(grid_widget)
        self.group_layout.addWidget(scroll)

    def _create_group_similarity_info(self, group) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_12)
        
        score = group.similarity_score
        color = DesignSystem.COLOR_SUCCESS if score >= 95 else DesignSystem.COLOR_PRIMARY if score >= 85 else DesignSystem.COLOR_WARNING
        
        # Barra de progreso circular o lineal
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(score))
        progress.setFixedWidth(150)
        progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        
        label = QLabel(f"Similitud Visual: {score:.1f}%")
        label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {color};")
        
        layout.addWidget(label)
        layout.addWidget(progress)
        layout.addStretch()
        
        return container

    def _create_file_card(self, file_path: Path, is_selected: bool) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        
        card.setStyleSheet(self._get_card_style(is_selected))
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_8)
        layout.setContentsMargins(DesignSystem.SPACE_8, DesignSystem.SPACE_8, DesignSystem.SPACE_8, DesignSystem.SPACE_8)
        
        # Header: Checkbox y Tamaño
        header = QHBoxLayout()
        checkbox = QCheckBox("Eliminar")
        checkbox.setChecked(is_selected)
        checkbox.setStyleSheet(f"""
            QCheckBox {{ color: {DesignSystem.COLOR_DANGER}; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; }}
        """)
        # Usar lambda para capturar el path
        checkbox.toggled.connect(lambda checked, f=file_path: self._toggle_file_selection(f, checked))
        
        size_lbl = QLabel(format_size(file_path.stat().st_size))
        size_lbl.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_XS}px;")
        
        header.addWidget(checkbox)
        header.addStretch()
        header.addWidget(size_lbl)
        layout.addLayout(header)
        
        # Thumbnail
        thumb_lbl, is_video = self._create_thumbnail(file_path)
        if thumb_lbl:
            thumb_lbl.mousePressEvent = lambda e, f=file_path: self._show_image_preview(f)
            layout.addWidget(thumb_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Nombre archivo
        name_lbl = QLabel(file_path.name)
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT};")
        layout.addWidget(name_lbl)
        
        # Click en toda la card selecciona/deselecciona (opcional, a veces confuso si hay preview)
        # card.mousePressEvent = lambda e: checkbox.toggle() 
        
        # Guardar path para búsqueda posterior
        card.setProperty("file_path", str(file_path))
        
        return card

    def _get_card_style(self, is_selected: bool) -> str:
        border_color = DesignSystem.COLOR_DANGER if is_selected else DesignSystem.COLOR_BORDER
        bg_color = "#FFF5F5" if is_selected else DesignSystem.COLOR_SURFACE
        width = 2 if is_selected else 1
        
        return f"""
            QFrame {{
                background-color: {bg_color};
                border: {width}px solid {border_color};
                border-radius: {DesignSystem.RADIUS_MD}px;
            }}
            QFrame:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """

    def _toggle_file_selection(self, file_path, checked):
        if self.current_group_index not in self.selections:
            self.selections[self.current_group_index] = []
            
        if checked:
            if file_path not in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].append(file_path)
        else:
            if file_path in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].remove(file_path)
                
        self._update_summary()
        
        # Actualizar visualmente la card específica sin recargar todo el grid
        # Esto evita el segfault por destruir el widget que emitió la señal
        self._update_card_visuals(file_path, checked)

    def _update_card_visuals(self, file_path: Path, is_selected: bool):
        """Busca y actualiza el estilo de la card específica en el grid actual."""
        # Buscar el QScrollArea en el layout del grupo
        scroll_area = None
        for i in range(self.group_layout.count()):
            item = self.group_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), QScrollArea):
                scroll_area = item.widget()
                break
        
        if not scroll_area: return
        
        grid_widget = scroll_area.widget()
        if not grid_widget: return
        
        grid_layout = grid_widget.layout()
        if not grid_layout: return
        
        # Buscar la card por la propiedad file_path
        target_path = str(file_path)
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(i)
            card = item.widget()
            if card and card.property("file_path") == target_path:
                card.setStyleSheet(self._get_card_style(is_selected))
                
                # También actualizar el estado del checkbox si no fue el origen del cambio
                # (aunque en este caso el toggle viene del checkbox, es bueno mantener consistencia)
                # Encontrar el checkbox dentro de la card
                checkbox = card.findChild(QCheckBox)
                if checkbox:
                    # Bloquear señales para evitar recursión infinita si cambiamos programáticamente
                    was_blocked = checkbox.signalsBlocked()
                    checkbox.blockSignals(True)
                    checkbox.setChecked(is_selected)
                    checkbox.blockSignals(was_blocked)
                break

    def _update_summary(self):
        total_files = sum(len(l) for l in self.selections.values())
        total_bytes = 0
        for files in self.selections.values():
            total_bytes += sum(f.stat().st_size for f in files)
            
        self.global_summary_label.setText(f"{total_files} archivos seleccionados ({format_size(total_bytes)})")
        self.delete_btn.setEnabled(total_files > 0)
        self.delete_btn.setText(f"Eliminar {total_files} Archivos")

    def _previous_group(self):
        if self.navigable_groups:
            new_index = (self.current_group_index - 1) % len(self.navigable_groups)
            self._load_group(new_index)

    def _next_group(self):
        if self.navigable_groups:
            new_index = (self.current_group_index + 1) % len(self.navigable_groups)
            self._load_group(new_index)

    def _apply_strategy_current_group(self, strategy):
        if not self.navigable_groups: return
        
        group = self.navigable_groups[self.current_group_index]
        files = group.files
        if len(files) < 2: return
        
        to_delete = []
        if strategy == 'keep_first':
            to_delete = files[1:]
        elif strategy == 'keep_last':
            to_delete = files[:-1]
        elif strategy == 'keep_largest':
            sorted_files = sorted(files, key=lambda f: f.stat().st_size, reverse=True)
            to_delete = sorted_files[1:]
            
        self.selections[self.current_group_index] = list(to_delete)
        self._load_group(self.current_group_index)
        self._update_summary()

    def _clear_current_group_selection(self):
        if self.current_group_index in self.selections:
            self.selections[self.current_group_index] = []
            self._load_group(self.current_group_index)
            self._update_summary()

    def accept(self):
        """Construye el plan de eliminación con los archivos seleccionados."""
        selected_groups = []
        for group_index, files_to_delete in self.selections.items():
            if files_to_delete:
                # Obtener el grupo original para metadata
                original_group = self.all_groups[group_index]
                # Crear grupo con solo los archivos seleccionados para eliminar
                selected_group = DuplicateGroup(
                    hash_value=original_group.hash_value,
                    files=files_to_delete,
                    total_size=sum(f.stat().st_size for f in files_to_delete),
                    similarity_score=original_group.similarity_score
                )
                selected_groups.append(selected_group)
        
        self.accepted_plan = {
            'groups': selected_groups,
            'keep_strategy': 'manual',
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        super().accept()

    # --- Helpers reutilizados (simplificados) ---
    def _create_thumbnail(self, file_path: Path):
        # Lógica similar a la original pero simplificada visualmente
        # Retorna (QLabel, is_video)
        try:
            pixmap = QPixmap(str(file_path))
            if pixmap.isNull(): return None, False
            
            pixmap = pixmap.scaled(Config.THUMBNAIL_SIZE, Config.THUMBNAIL_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl = QLabel()
            lbl.setPixmap(pixmap)
            lbl.setFixedSize(Config.THUMBNAIL_SIZE, Config.THUMBNAIL_SIZE)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"background-color: {DesignSystem.COLOR_BACKGROUND}; border-radius: 4px;")
            return lbl, False
        except:
            return None, False

    def _show_image_preview(self, file_path):
        dialog = ImagePreviewDialog(file_path, self)
        dialog.exec()
