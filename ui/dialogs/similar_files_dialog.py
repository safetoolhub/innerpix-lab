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

    def __init__(self, analysis: SimilarFilesAnalysis, parent=None):
        super().__init__(parent)
        
        self.analysis = analysis
        self.current_sensitivity = 85
        self.current_result = None
        self.current_group_index = 0
        self.selections = {}  # {group_index: [files_to_delete]}
        
        # Filtros
        self.filter_min_files = 2
        self.filter_min_size_mb = 0
        self.all_groups = []
        
        self._setup_ui()
        self._load_initial_results()
    
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
        
        # 1. Header Moderno
        self.header_frame = self._create_modern_header()
        main_layout.addWidget(self.header_frame)
        
        # Contenedor principal con padding
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setSpacing(DesignSystem.SPACE_16)
        content_layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_20, DesignSystem.SPACE_24, DesignSystem.SPACE_20)
        
        # 2. Panel de Control (Sensibilidad + Filtros)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(DesignSystem.SPACE_16)
        
        sensitivity_card = self._create_sensitivity_card()
        filters_card = self._create_filters_card()
        
        controls_layout.addWidget(sensitivity_card, stretch=3)
        controls_layout.addWidget(filters_card, stretch=2)
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
        
        # Barra de herramientas del workspace (Navegación y Acciones de Grupo)
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
        
        # 4. Footer (Resumen y Botones de Acción Global)
        footer = self._create_footer()
        main_layout.addWidget(footer)

    def _create_modern_header(self) -> QFrame:
        """Crea un header moderno con métricas clave."""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_16, DesignSystem.SPACE_24, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_24)
        
        # Título e Icono
        title_container = QHBoxLayout()
        title_container.setSpacing(DesignSystem.SPACE_12)
        
        icon_label = icon_manager.create_icon_label('content-duplicate', size=28, color=DesignSystem.COLOR_PRIMARY)
        title_container.addWidget(icon_label)
        
        text_container = QVBoxLayout()
        text_container.setSpacing(2)
        title = QLabel("Archivos Similares")
        title.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_XL}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT};")
        subtitle = QLabel("Detecta y gestiona imágenes visualmente idénticas")
        subtitle.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        text_container.addWidget(title)
        text_container.addWidget(subtitle)
        title_container.addLayout(text_container)
        
        layout.addLayout(title_container)
        layout.addStretch()
        
        # Métricas
        self.metric_groups = self._create_metric_badge("Grupos", "0", DesignSystem.COLOR_PRIMARY)
        self.metric_duplicates = self._create_metric_badge("Duplicados", "0", DesignSystem.COLOR_WARNING)
        self.metric_space = self._create_metric_badge("Recuperable", "0 B", DesignSystem.COLOR_SUCCESS)
        
        layout.addWidget(self.metric_groups)
        layout.addWidget(self.metric_duplicates)
        layout.addWidget(self.metric_space)
        
        return header

    def _create_metric_badge(self, label: str, value: str, color: str) -> QFrame:
        badge = QFrame()
        badge.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border-radius: {DesignSystem.RADIUS_MD}px;
            }}
        """)
        layout = QVBoxLayout(badge)
        layout.setContentsMargins(DesignSystem.SPACE_16, DesignSystem.SPACE_8, DesignSystem.SPACE_16, DesignSystem.SPACE_8)
        layout.setSpacing(2)
        
        val_label = QLabel(value)
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_LG}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {color};")
        
        lbl_label = QLabel(label.upper())
        lbl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_XS}px; font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; color: {DesignSystem.COLOR_TEXT_SECONDARY}; letter-spacing: 0.5px;")
        
        layout.addWidget(val_label)
        layout.addWidget(lbl_label)
        
        # Guardar referencia para actualizar
        if label == "Grupos": self.lbl_groups_val = val_label
        elif label == "Duplicados": self.lbl_duplicates_val = val_label
        elif label == "Recuperable": self.lbl_space_val = val_label
        
        return badge

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
        layout.setContentsMargins(DesignSystem.SPACE_16, DesignSystem.SPACE_16, DesignSystem.SPACE_16, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        # Header de la card
        header = QHBoxLayout()
        icon = icon_manager.create_icon_label('tune', size=18, color=DesignSystem.COLOR_TEXT)
        title = QLabel("Sensibilidad de Detección")
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
                height: 6px;
                background: {DesignSystem.COLOR_BACKGROUND};
                margin: 2px 0;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border: 2px solid {DesignSystem.COLOR_SURFACE};
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 10px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {DesignSystem.COLOR_PRIMARY_HOVER};
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 11px;
            }}
            QSlider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 3px;
            }}
        """)
        
        slider_container.addWidget(QLabel("Permisivo"))
        slider_container.addWidget(self.sensitivity_slider, 1)
        slider_container.addWidget(QLabel("Estricto"))
        
        layout.addLayout(slider_container)
        
        # Conexiones
        self.sensitivity_slider.valueChanged.connect(self._on_slider_value_changed)
        self.sensitivity_slider.sliderReleased.connect(self._on_slider_released)
        
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
        layout = QHBoxLayout(card)
        layout.setContentsMargins(DesignSystem.SPACE_16, DesignSystem.SPACE_16, DesignSystem.SPACE_16, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Icono y Título
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        header = QHBoxLayout()
        header.addWidget(icon_manager.create_icon_label('filter-variant', size=18))
        header.addWidget(QLabel("Filtros", styleSheet=f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"))
        header.addStretch()
        title_layout.addLayout(header)
        
        reset_btn = QPushButton("Resetear")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                color: {DesignSystem.COLOR_PRIMARY};
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        reset_btn.clicked.connect(self._reset_filters)
        title_layout.addWidget(reset_btn)
        
        layout.addLayout(title_layout)
        
        # Inputs
        inputs_layout = QGridLayout()
        inputs_layout.setHorizontalSpacing(DesignSystem.SPACE_12)
        inputs_layout.setVerticalSpacing(DesignSystem.SPACE_8)
        
        # Min Archivos
        self.min_files_spin = QSpinBox()
        self.min_files_spin.setRange(2, 50)
        self.min_files_spin.setValue(self.filter_min_files)
        self.min_files_spin.setSuffix(" archivos")
        self.min_files_spin.setStyleSheet(self._get_spinbox_style())
        self.min_files_spin.valueChanged.connect(self._on_filters_changed)
        
        inputs_layout.addWidget(QLabel("Mín. Archivos:"), 0, 0)
        inputs_layout.addWidget(self.min_files_spin, 0, 1)
        
        # Min Tamaño
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 1000)
        self.min_size_spin.setValue(self.filter_min_size_mb)
        self.min_size_spin.setSuffix(" MB")
        self.min_size_spin.setStyleSheet(self._get_spinbox_style())
        self.min_size_spin.valueChanged.connect(self._on_filters_changed)
        
        inputs_layout.addWidget(QLabel("Mín. Tamaño:"), 1, 0)
        inputs_layout.addWidget(self.min_size_spin, 1, 1)
        
        layout.addLayout(inputs_layout)
        
        return card

    def _get_spinbox_style(self):
        return f"""
            QSpinBox {{
                padding: 4px 8px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                background: {DesignSystem.COLOR_BACKGROUND};
                selection-background-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QSpinBox:focus {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 20px;
                background: transparent;
                border-left: 1px solid {DesignSystem.COLOR_BORDER};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {DesignSystem.COLOR_SECONDARY_LIGHT};
            }}
        """

    def _create_workspace_toolbar(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_16, DesignSystem.SPACE_12, DesignSystem.SPACE_16, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Navegación izquierda
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(icon_manager.get_icon('chevron-left'))
        self.prev_btn.setToolTip("Grupo Anterior")
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.prev_btn.clicked.connect(self._previous_group)
        
        self.group_counter_label = QLabel("Grupo 0 de 0")
        self.group_counter_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT};")
        
        self.next_btn = QPushButton()
        self.next_btn.setIcon(icon_manager.get_icon('chevron-right'))
        self.next_btn.setToolTip("Siguiente Grupo")
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.next_btn.clicked.connect(self._next_group)
        
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(DesignSystem.SPACE_8)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.group_counter_label)
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
        
        # Separador vertical
        v_sep = QFrame()
        v_sep.setFrameShape(QFrame.Shape.VLine)
        v_sep.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER};")
        layout.addWidget(v_sep)
        
        # Acciones Rápidas (Smart Select)
        layout.addWidget(QLabel("Selección Rápida:", styleSheet=f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;"))
        
        strategies = [
            ("Mantener 1º", "keep_first", "Mantener solo el primer archivo"),
            ("Mantener Último", "keep_last", "Mantener solo el último archivo"),
            ("Mejor Calidad", "keep_largest", "Mantener el archivo más pesado"),
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
                    padding: 4px 12px;
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
            layout.addWidget(btn)
            
        layout.addStretch()
        
        # Botón Limpiar Selección
        clear_btn = QPushButton("Limpiar Selección")
        clear_btn.setIcon(icon_manager.get_icon('close', size=14))
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            QPushButton:hover {{ color: {DesignSystem.COLOR_DANGER}; }}
        """)
        clear_btn.clicked.connect(self._clear_current_group_selection)
        layout.addWidget(clear_btn)
        
        return container

    def _create_footer(self) -> QFrame:
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border-top: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_16, DesignSystem.SPACE_24, DesignSystem.SPACE_16)
        
        # Resumen de selección global
        self.global_summary_label = QLabel("0 archivos seleccionados (0 B)")
        self.global_summary_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; color: {DesignSystem.COLOR_TEXT};")
        layout.addWidget(self.global_summary_label)
        
        layout.addStretch()
        
        # Botones
        button_box = self.make_ok_cancel_buttons(
            ok_text="Eliminar Seleccionados",
            ok_enabled=False,
            button_style='danger'
        )
        self.delete_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        layout.addWidget(button_box)
        
        return footer

    # ================= LÓGICA DE NEGOCIO =================

    def _load_initial_results(self):
        self._update_results(self.current_sensitivity)

    def _on_slider_value_changed(self, value: int):
        self.current_sensitivity = value
        self.sensitivity_value_label.setText(f"{value}%")

    def _on_slider_released(self):
        self._update_results(self.current_sensitivity)

    def _update_results(self, sensitivity: int):
        self.current_result = self.analysis.get_groups(sensitivity)
        self.all_groups = self.current_result.groups.copy()
        self.selections.clear()
        self._apply_current_filters()

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
            
        self.analysis.groups = filtered_groups
        self._update_header_metrics()
        
        self.current_group_index = 0
        if filtered_groups:
            self._load_group(0)
        else:
            self._show_no_groups_message()

    def _update_header_metrics(self):
        groups = self.analysis.groups
        total_groups = len(groups)
        total_duplicates = sum(len(g.files) - 1 for g in groups)
        space_potential = sum((len(g.files) - 1) * g.files[0].stat().st_size for g in groups if g.files)
        
        self.lbl_groups_val.setText(str(total_groups))
        self.lbl_duplicates_val.setText(str(total_duplicates))
        self.lbl_space_val.setText(format_size(space_potential))

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
        if not 0 <= index < len(self.analysis.groups):
            return
            
        self.current_group_index = index
        group = self.analysis.groups[index]
        
        # Actualizar contador
        self.group_counter_label.setText(f"Grupo {index + 1} de {len(self.analysis.groups)}")
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
        
        # Estilo dinámico según selección
        border_color = DesignSystem.COLOR_DANGER if is_selected else DesignSystem.COLOR_BORDER
        bg_color = "#FFF5F5" if is_selected else DesignSystem.COLOR_SURFACE
        width = 2 if is_selected else 1
        
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: {width}px solid {border_color};
                border-radius: {DesignSystem.RADIUS_MD}px;
            }}
            QFrame:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        
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
        
        return card

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
        # Recargar solo para actualizar estilos visuales (borde rojo)
        # Idealmente optimizar para no recargar todo el grid, pero por ahora ok
        self._load_group(self.current_group_index)

    def _update_summary(self):
        total_files = sum(len(l) for l in self.selections.values())
        total_bytes = 0
        for files in self.selections.values():
            total_bytes += sum(f.stat().st_size for f in files)
            
        self.global_summary_label.setText(f"{total_files} archivos seleccionados ({format_size(total_bytes)})")
        self.delete_btn.setEnabled(total_files > 0)
        self.delete_btn.setText(f"Eliminar {total_files} Archivos")

    def _previous_group(self):
        if self.analysis.groups:
            new_index = (self.current_group_index - 1) % len(self.analysis.groups)
            self._load_group(new_index)

    def _next_group(self):
        if self.analysis.groups:
            new_index = (self.current_group_index + 1) % len(self.analysis.groups)
            self._load_group(new_index)

    def _apply_strategy_current_group(self, strategy):
        if not self.analysis.groups: return
        
        group = self.analysis.groups[self.current_group_index]
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
