"""
Diálogo de gestión de archivos similares (70-95% similitud).

Este diálogo está diseñado para archivos SIMILARES pero NO idénticos.
Para copias visuales idénticas (100%), usar el diálogo Visual Identical.

Flujo:
1. Los hashes perceptuales ya están calculados (DuplicatesSimilarAnalysis)
2. El diálogo se muestra con estado de carga
3. El clustering se ejecuta después de que el diálogo sea visible
4. El usuario ajusta sensibilidad con slider (regenera en tiempo real)
"""

from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSlider, QPushButton,
    QDialogButtonBox, QCheckBox, QScrollArea, QWidget,
    QGridLayout, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QColor
from services.duplicates_similar_service import DuplicatesSimilarAnalysis
from services.result_types import DuplicateGroup
from utils.format_utils import format_size
from utils.image_loader import load_image_as_qpixmap
from utils.video_thumbnail import get_video_thumbnail
from utils.platform_utils import open_file_with_default_app
from utils.logger import get_logger
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from .base_dialog import BaseDialog
from .dialog_utils import show_file_details_dialog
from .image_preview_dialog import ImagePreviewDialog


class DuplicatesSimilarDialog(BaseDialog):
    """
    Diálogo para gestionar archivos similares (70-95% de similitud).
    
    IMPORTANTE: Este diálogo es para archivos SIMILARES, no idénticos.
    Para copias idénticas, usar el diálogo "Copias Visuales Idénticas".
    """
    
    DEFAULT_SENSITIVITY = 85
    
    def __init__(self, analysis: DuplicatesSimilarAnalysis, parent=None):
        super().__init__(parent)
        
        self.logger = get_logger('DuplicatesSimilarDialog')
        self.analysis = analysis
        
        self.current_sensitivity = self.DEFAULT_SENSITIVITY
        self.current_result = None
        self.all_groups = []
        self.current_group_index = 0
        self.selections = {}
        self.accepted_plan = None
        self._is_loading = True
        
        self._setup_ui()
        self._show_loading_state()
        
        # Cargar grupos DESPUÉS de que el diálogo sea visible
        QTimer.singleShot(100, self._initial_load)
    
    def _setup_ui(self):
        """Configura la interfaz del diálogo."""
        self.setWindowTitle("Gestionar Archivos Similares")
        self.setModal(True)
        self.resize(1280, 900)
        self.setMinimumSize(1100, 750)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='image-search',
            title='Archivos Similares',
            description='Detecta imágenes parecidas (ediciones, recortes, diferentes resoluciones)',
            metrics=[
                {'value': '-', 'label': 'Grupos', 'color': DesignSystem.COLOR_PRIMARY},
                {'value': '-', 'label': 'Similares', 'color': DesignSystem.COLOR_WARNING},
                {'value': '-', 'label': 'Recuperable', 'color': DesignSystem.COLOR_SUCCESS}
            ]
        )
        main_layout.addWidget(self.header_frame)
        
        # Contenedor principal
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setSpacing(DesignSystem.SPACE_16)
        content_layout.setContentsMargins(
            DesignSystem.SPACE_24, DesignSystem.SPACE_20,
            DesignSystem.SPACE_24, DesignSystem.SPACE_20
        )
        
        # Barra de sensibilidad
        self.sensitivity_bar = self._create_sensitivity_bar()
        content_layout.addWidget(self.sensitivity_bar)
        
        # Info card
        self.info_card = self._create_info_card()
        content_layout.addWidget(self.info_card)
        
        # Área de trabajo
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
        
        # Toolbar de navegación
        self.workspace_toolbar = self._create_navigation_toolbar()
        workspace_layout.addWidget(self.workspace_toolbar)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER_LIGHT};")
        workspace_layout.addWidget(separator)
        
        # Contenedor de grupos
        self.group_container = QWidget()
        self.group_layout = QVBoxLayout(self.group_container)
        self.group_layout.setContentsMargins(
            DesignSystem.SPACE_20, DesignSystem.SPACE_20,
            DesignSystem.SPACE_20, DesignSystem.SPACE_20
        )
        self.group_layout.setSpacing(DesignSystem.SPACE_16)
        
        workspace_layout.addWidget(self.group_container, stretch=1)
        content_layout.addWidget(workspace_card, stretch=1)
        
        main_layout.addWidget(content_wrapper, stretch=1)
        
        # Opciones de seguridad
        security_options = self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de eliminar",
            dry_run_label="Modo simulación"
        )
        content_layout.addWidget(security_options)
        
        # Botones
        button_box = self.make_ok_cancel_buttons(
            ok_text="Eliminar Seleccionados",
            ok_enabled=False,
            button_style='danger'
        )
        self.delete_btn: Optional[QPushButton] = button_box.button(QDialogButtonBox.StandardButton.Ok)
        content_layout.addWidget(button_box)

    def _create_sensitivity_bar(self) -> QFrame:
        """Crea la barra de control de sensibilidad."""
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
            DesignSystem.SPACE_16, DesignSystem.SPACE_12
        )
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Icono y label
        icon = icon_manager.create_icon_label('target', size=18, color=DesignSystem.COLOR_TEXT_SECONDARY)
        layout.addWidget(icon)
        
        sens_label = QLabel("Sensibilidad:")
        sens_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; color: {DesignSystem.COLOR_TEXT};")
        layout.addWidget(sens_label)
        
        # Marcadores
        low_label = QLabel("Baja")
        low_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_XS}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        layout.addWidget(low_label)
        
        # Slider (70-95%)
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(70, 95)
        self.sensitivity_slider.setValue(self.current_sensitivity)
        self.sensitivity_slider.setFixedWidth(200)
        self.sensitivity_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sensitivity_slider.setToolTip(
            "Ajusta qué tan parecidas deben ser las imágenes.\n"
            "• 95%: Muy similares\n• 85%: Similar (recomendado)\n• 70%: Más tolerante"
        )
        self.sensitivity_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                height: 6px;
                background: {DesignSystem.COLOR_BACKGROUND};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border: 2px solid {DesignSystem.COLOR_SURFACE};
                width: 18px; height: 18px;
                margin: -7px 0;
                border-radius: 10px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QSlider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.sensitivity_slider)
        
        high_label = QLabel("Alta")
        high_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_XS}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        layout.addWidget(high_label)
        
        self.sensitivity_value_label = QLabel(f"{self.current_sensitivity}%")
        self.sensitivity_value_label.setFixedWidth(50)
        self.sensitivity_value_label.setStyleSheet(f"""
            color: {DesignSystem.COLOR_PRIMARY}; 
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            font-size: {DesignSystem.FONT_SIZE_MD}px;
        """)
        layout.addWidget(self.sensitivity_value_label)
        
        layout.addStretch()
        
        # Acciones rápidas
        actions_label = QLabel("Selección:")
        actions_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; color: {DesignSystem.COLOR_TEXT};")
        layout.addWidget(actions_label)
        
        for text, strategy, tooltip in [
            ("Mantener mejor", "keep_largest", "Conservar archivo de mayor calidad"),
            ("Mantener primero", "keep_first", "Conservar primer archivo"),
        ]:
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DesignSystem.COLOR_BACKGROUND};
                    border: 1px solid {DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: 6px 12px;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    color: {DesignSystem.COLOR_TEXT};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                    border-color: {DesignSystem.COLOR_PRIMARY};
                    color: {DesignSystem.COLOR_PRIMARY};
                }}
            """)
            btn.clicked.connect(lambda _, s=strategy: self._apply_strategy(s))
            layout.addWidget(btn)
        
        # Conexiones
        self.sensitivity_slider.valueChanged.connect(self._on_slider_changed)
        self.sensitivity_slider.sliderReleased.connect(self._on_slider_released)
        
        return toolbar

    def _create_info_card(self) -> QFrame:
        """Crea tarjeta informativa."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_INFO_BG};
                border: 1px solid {DesignSystem.COLOR_INFO};
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_12}px;
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        icon = icon_manager.create_icon_label('information-outline', size=20, color=DesignSystem.COLOR_INFO)
        layout.addWidget(icon)
        
        text = QLabel(
            "<b>Consejo:</b> Esta herramienta detecta imágenes <i>similares</i> "
            "(recortes, ediciones, diferentes resoluciones). "
            "Para eliminar copias <i>idénticas</i> visualmente, "
            "usa primero \"Copias Visuales Idénticas\"."
        )
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        layout.addWidget(text, stretch=1)
        
        return card

    def _create_navigation_toolbar(self) -> QWidget:
        """Crea la barra de navegación."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
            DesignSystem.SPACE_16, DesignSystem.SPACE_12
        )
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Navegación
        self.prev_btn = self.make_styled_button(icon_name='chevron-left', button_style='secondary', tooltip="Anterior")
        self.prev_btn.clicked.connect(self._previous_group)
        self.prev_btn.setEnabled(False)
        
        self.group_counter_label = QLabel("Cargando...")
        self.group_counter_label.setMinimumWidth(200)
        self.group_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_counter_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT};")
        
        self.next_btn = self.make_styled_button(icon_name='chevron-right', button_style='secondary', tooltip="Siguiente")
        self.next_btn.clicked.connect(self._next_group)
        self.next_btn.setEnabled(False)
        
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(DesignSystem.SPACE_8)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.group_counter_label)
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
        layout.addStretch()
        
        # Contador de selección
        self.global_summary_label = QLabel("0 archivos seleccionados (0 B)")
        self.global_summary_label.setMinimumWidth(250)
        self.global_summary_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.global_summary_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; color: {DesignSystem.COLOR_TEXT};")
        layout.addWidget(self.global_summary_label)
        
        return container

    # ================= LOADING STATE =================

    def _show_loading_state(self):
        """Muestra estado de carga mientras se procesan los grupos."""
        for i in reversed(range(self.group_layout.count())):
            item = self.group_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)  # type: ignore[union-attr]
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_20)
        
        # Spinner animado
        spinner = QLabel()
        spinner.setFixedSize(64, 64)
        spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Usar icono de loading con animación CSS
        loading_icon = icon_manager.get_icon('loading', size=48, color=DesignSystem.COLOR_PRIMARY)
        spinner.setPixmap(loading_icon.pixmap(48, 48))
        spinner.setStyleSheet("""
            QLabel {
                background: transparent;
            }
        """)
        layout.addWidget(spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Mensaje
        self.loading_label = QLabel("Analizando similitud entre imágenes...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        layout.addWidget(self.loading_label)
        
        # Submensaje
        total_files = len(self.analysis.perceptual_hashes)
        sub_msg = QLabel(f"Procesando {total_files:,} archivos con sensibilidad {self.current_sensitivity}%")
        sub_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_msg.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(sub_msg)
        
        self.group_layout.addWidget(container)
        
        # Deshabilitar controles durante carga
        self.sensitivity_slider.setEnabled(False)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

    def _initial_load(self):
        """Carga inicial de grupos (llamada después de mostrar el diálogo)."""
        from PyQt6.QtWidgets import QApplication
        
        # Procesar eventos para asegurar que el diálogo está visible
        QApplication.processEvents()
        
        self._regenerate_groups()
        self._is_loading = False
        self.sensitivity_slider.setEnabled(True)

    # ================= LÓGICA =================

    def _on_slider_changed(self, value: int):
        """Actualiza el label mientras se mueve el slider."""
        self.current_sensitivity = value
        self.sensitivity_value_label.setText(f"{value}%")

    def _on_slider_released(self):
        """Regenera grupos cuando se suelta el slider."""
        if not self._is_loading:
            self._regenerate_groups()

    def _regenerate_groups(self):
        """Regenera los grupos con la sensibilidad actual."""
        from PyQt6.QtWidgets import QApplication
        
        self.logger.info(f"Regenerando grupos con sensibilidad {self.current_sensitivity}%...")
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.analysis.get_groups(self.current_sensitivity)
            self.current_result = result
            self.all_groups = result.groups.copy()
            
            self.logger.info(f"Encontrados {len(self.all_groups)} grupos")
            
            self.selections.clear()
            self._update_header_metrics()
            
            if self.all_groups:
                self.current_group_index = 0
                self._load_group(0)
            else:
                self._show_no_groups_message()
                
        finally:
            QApplication.restoreOverrideCursor()

    def _update_header_metrics(self):
        """Actualiza las métricas del header."""
        total_groups = len(self.all_groups)
        total_similar = sum(len(g.files) - 1 for g in self.all_groups)
        space_potential = sum(
            (len(g.files) - 1) * (g.total_size // len(g.files))
            for g in self.all_groups if g.files
        )
        
        self._update_header_metric(self.header_frame, 'Grupos', str(total_groups))
        self._update_header_metric(self.header_frame, 'Similares', str(total_similar))
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(space_potential))

    def _show_no_groups_message(self):
        """Muestra mensaje cuando no hay grupos."""
        for i in reversed(range(self.group_layout.count())):
            item = self.group_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)  # type: ignore[union-attr]
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        icon_label = icon_manager.create_icon_label('check-circle', size=64, color=DesignSystem.COLOR_SUCCESS)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        msg = QLabel(
            f"No se encontraron archivos similares\n"
            f"con sensibilidad {self.current_sensitivity}%\n\n"
            "Reduce la sensibilidad para detectar\n"
            "archivos con más diferencias."
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_MD}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        layout.addWidget(msg)
        
        self.group_layout.addWidget(container)
        
        self.group_counter_label.setText("0 de 0")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

    def _load_group(self, index: int):
        """Carga y muestra un grupo específico."""
        if not 0 <= index < len(self.all_groups):
            return
        
        self.current_group_index = index
        group = self.all_groups[index]
        
        self.group_counter_label.setText(f"Grupo {index + 1} de {len(self.all_groups)}")
        self.prev_btn.setEnabled(len(self.all_groups) > 1)
        self.next_btn.setEnabled(len(self.all_groups) > 1)
        
        # Limpiar
        for i in reversed(range(self.group_layout.count())):
            item = self.group_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)  # type: ignore[union-attr]
        
        # Info de similitud
        sim_info = self._create_group_similarity_info(group)
        self.group_layout.addWidget(sim_info)
        
        # Grid
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
            card = self._create_file_card(file_path, file_path in current_selection)
            grid_layout.addWidget(card, i // cols, i % cols)
        
        scroll.setWidget(grid_widget)
        self.group_layout.addWidget(scroll)

    def _create_group_similarity_info(self, group) -> QWidget:
        """Crea widget con info de similitud."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        score = group.similarity_score
        color = (
            DesignSystem.COLOR_SUCCESS if score >= 95 else
            DesignSystem.COLOR_PRIMARY if score >= 85 else
            DesignSystem.COLOR_WARNING
        )
        
        badge = QLabel(f"{score:.1f}% Similitud")
        badge.setStyleSheet(f"""
            background-color: {color}20; color: {color};
            border: 1px solid {color}40; border-radius: 12px;
            padding: 4px 12px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        layout.addWidget(badge)
        
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(score))
        progress.setFixedWidth(120)
        progress.setTextVisible(False)
        progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: {DesignSystem.COLOR_BORDER_LIGHT};
                border-radius: 2px; height: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color}; border-radius: 2px;
            }}
        """)
        layout.addWidget(progress)
        
        files_info = QLabel(f"{len(group.files)} archivos · {format_size(group.total_size)}")
        files_info.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        layout.addWidget(files_info)
        
        layout.addStretch()
        return container

    def _create_file_card(self, file_path: Path, is_selected: bool) -> QFrame:
        """Crea tarjeta para un archivo."""
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mouseDoubleClickEvent = lambda e: show_file_details_dialog(file_path, self)  # type: ignore[assignment]
        card.setStyleSheet(self._get_card_style(is_selected))
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_8)
        layout.setContentsMargins(DesignSystem.SPACE_8, DesignSystem.SPACE_8, DesignSystem.SPACE_8, DesignSystem.SPACE_8)
        
        # Header
        header = QHBoxLayout()
        
        checkbox = QCheckBox("Eliminar")
        checkbox.setChecked(is_selected)
        checkbox.setStyleSheet(f"QCheckBox {{ color: {DesignSystem.COLOR_DANGER}; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; }}")
        checkbox.toggled.connect(lambda checked, f=file_path: self._toggle_selection(f, checked))
        header.addWidget(checkbox)
        
        header.addStretch()
        
        info_badge = self._create_info_badge(file_path)
        header.addWidget(info_badge)
        
        try:
            size_text = format_size(file_path.stat().st_size)
        except:
            size_text = "?"
        size_lbl = QLabel(size_text)
        size_lbl.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_XS}px;")
        header.addWidget(size_lbl)
        
        layout.addLayout(header)
        
        # Thumbnail
        thumb_lbl, is_video = self._create_thumbnail(file_path)
        if thumb_lbl:
            thumb_lbl.mousePressEvent = lambda e, f=file_path, v=is_video: self._handle_thumbnail_click(f, v)  # type: ignore[assignment]
            layout.addWidget(thumb_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Nombre
        name_lbl = QLabel(file_path.name)
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT};")
        layout.addWidget(name_lbl)
        
        # Fecha
        date_info = self._get_file_date_info(file_path)
        if date_info:
            date_lbl = QLabel(date_info)
            date_lbl.setWordWrap(True)
            date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            date_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_XS}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
            layout.addWidget(date_lbl)
        
        card.setProperty("file_path", str(file_path))
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(lambda pos, f=file_path: self._show_context_menu(f))
        
        return card

    def _create_info_badge(self, file_path: Path) -> QLabel:
        """Crea badge de info."""
        badge = QLabel()
        info_icon = icon_manager.get_icon('information-outline', size=16, color=DesignSystem.COLOR_PRIMARY)
        badge.setPixmap(info_icon.pixmap(16, 16))
        badge.setFixedSize(20, 20)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(DesignSystem.get_info_badge_style())
        badge.setCursor(Qt.CursorShape.PointingHandCursor)
        badge.mousePressEvent = lambda e, f=file_path: show_file_details_dialog(f, self)  # type: ignore[assignment]
        return badge

    def _get_card_style(self, is_selected: bool) -> str:
        border_color = DesignSystem.COLOR_DANGER if is_selected else DesignSystem.COLOR_BORDER
        bg_color = DesignSystem.COLOR_DANGER_BG if is_selected else DesignSystem.COLOR_SURFACE
        width = 2 if is_selected else 1
        return f"""
            QFrame {{
                background-color: {bg_color};
                border: {width}px solid {border_color};
                border-radius: {DesignSystem.RADIUS_MD}px;
            }}
            QFrame:hover {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}
        """

    def _toggle_selection(self, file_path: Path, checked: bool):
        """Toggle selección."""
        if self.current_group_index not in self.selections:
            self.selections[self.current_group_index] = []
        
        if checked and file_path not in self.selections[self.current_group_index]:
            self.selections[self.current_group_index].append(file_path)
        elif not checked and file_path in self.selections[self.current_group_index]:
            self.selections[self.current_group_index].remove(file_path)
        
        self._update_summary()
        self._update_card_visual(file_path, checked)

    def _update_card_visual(self, file_path: Path, is_selected: bool):
        """Actualiza visual de tarjeta."""
        scroll_area: Optional[QScrollArea] = None
        for i in range(self.group_layout.count()):
            item = self.group_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QScrollArea):
                scroll_area = item.widget()  # type: ignore[assignment]
                break
        
        if not scroll_area or not scroll_area.widget():
            return
        
        inner_widget = scroll_area.widget()
        if not inner_widget:
            return
        grid_layout = inner_widget.layout()
        if not grid_layout:
            return
        
        target = str(file_path)
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(i)
            card = item.widget() if item else None
            if card and card.property("file_path") == target:
                card.setStyleSheet(self._get_card_style(is_selected))
                checkbox = card.findChild(QCheckBox)
                if checkbox:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(is_selected)
                    checkbox.blockSignals(False)
                break

    def _update_summary(self):
        """Actualiza resumen."""
        total_files = sum(len(l) for l in self.selections.values())
        total_bytes = sum(
            f.stat().st_size for files in self.selections.values() for f in files if f.exists()
        )
        
        self.global_summary_label.setText(f"{total_files} archivos seleccionados ({format_size(total_bytes)})")
        if self.delete_btn:
            self.delete_btn.setEnabled(total_files > 0)
            self.delete_btn.setText(f"Eliminar {total_files} Archivos")

    def _previous_group(self):
        if self.all_groups:
            self._load_group((self.current_group_index - 1) % len(self.all_groups))

    def _next_group(self):
        if self.all_groups:
            self._load_group((self.current_group_index + 1) % len(self.all_groups))

    def _apply_strategy(self, strategy: str):
        """Aplica estrategia al grupo actual."""
        if not self.all_groups:
            return
        
        group = self.all_groups[self.current_group_index]
        files = group.files
        if len(files) < 2:
            return
        
        if strategy == 'keep_first':
            to_delete = files[1:]
        elif strategy == 'keep_largest':
            sorted_files = sorted(files, key=lambda f: f.stat().st_size if f.exists() else 0, reverse=True)
            to_delete = sorted_files[1:]
        else:
            to_delete = []
        
        self.selections[self.current_group_index] = list(to_delete)
        self._load_group(self.current_group_index)
        self._update_summary()

    def _show_context_menu(self, file_path: Path):
        """Muestra menú contextual."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        
        action = menu.addAction(icon_manager.get_icon('information-outline'), "Ver detalles")
        if action:
            action.triggered.connect(lambda: show_file_details_dialog(file_path, self))
        
        menu.exec(QCursor.pos())

    def accept(self):
        """Construye plan de eliminación."""
        selected_groups = []
        for idx, files_to_delete in self.selections.items():
            if files_to_delete and idx < len(self.all_groups):
                og = self.all_groups[idx]
                selected_groups.append(DuplicateGroup(
                    hash_value=og.hash_value,
                    files=files_to_delete,
                    total_size=sum(f.stat().st_size for f in files_to_delete if f.exists()),
                    similarity_score=og.similarity_score
                ))
        
        from services.result_types import DuplicateAnalysisResult
        self.accepted_plan = {
            'analysis': DuplicateAnalysisResult(
                groups=selected_groups,
                mode='perceptual',
                items_count=len(selected_groups),
                total_groups=len(selected_groups),
                space_wasted=sum(g.total_size for g in selected_groups)
            ),
            'keep_strategy': 'manual',
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        super().accept()

    def _get_file_date_info(self, file_path: Path) -> str:
        """Obtiene info de fecha."""
        try:
            from utils.date_utils import select_best_date_from_file, get_all_metadata_from_file
            
            file_metadata = get_all_metadata_from_file(file_path)
            selected_date, source = select_best_date_from_file(file_metadata)
            
            if not selected_date:
                return ""
            
            date_str = selected_date.strftime('%Y-%m-%d %H:%M:%S')
            if source:
                source_short = 'EXIF' if 'EXIF' in source else 'Nombre' if 'Filename' in source else 'Mod.' if 'mtime' in source else source[:10]
            else:
                source_short = '?'
            return f"{date_str}\n({source_short})"
        except Exception:
            return ""

    def _create_thumbnail(self, file_path: Path):
        """Crea thumbnail."""
        try:
            from utils.file_utils import is_video_file
            is_video = is_video_file(str(file_path))
            
            if is_video:
                pixmap = get_video_thumbnail(file_path, max_size=(280, 280), frame_position=0.25)
                if pixmap and not pixmap.isNull():
                    pixmap = self._add_play_overlay(pixmap)
                else:
                    return None, True
            else:
                pixmap = load_image_as_qpixmap(file_path, max_size=(280, 280))
                if not pixmap or pixmap.isNull():
                    return None, False
            
            lbl = QLabel()
            lbl.setPixmap(pixmap)
            lbl.setFixedSize(280, 280)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"background-color: {DesignSystem.COLOR_BACKGROUND}; border-radius: 4px;")
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            
            return lbl, is_video
        except Exception as e:
            self.logger.debug(f"Error thumbnail: {e}")
            return None, False

    def _add_play_overlay(self, pixmap: QPixmap) -> QPixmap:
        """Agrega overlay de play."""
        result = QPixmap(pixmap.size())
        result.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(0, 0, pixmap)
        painter.fillRect(result.rect(), QColor(0, 0, 0, 60))
        
        play_icon = icon_manager.get_icon('play-circle', color=DesignSystem.COLOR_SURFACE)
        icon_pixmap = play_icon.pixmap(QSize(64, 64))
        x = (pixmap.width() - 64) // 2
        y = (pixmap.height() - 64) // 2
        painter.drawPixmap(x, y, icon_pixmap)
        painter.end()
        
        return result

    def _handle_thumbnail_click(self, file_path: Path, is_video: bool):
        """Maneja click en thumbnail."""
        if is_video:
            open_file_with_default_app(file_path)
        else:
            ImagePreviewDialog(file_path, self).exec()
