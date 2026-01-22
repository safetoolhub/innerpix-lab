"""
Diálogo de gestión de archivos similares (70-99% similitud).

Este diálogo está diseñado para archivos SIMILARES pero NO idénticos.
Para copias visuales idénticas (100%), usar el diálogo Visual Identical.

Flujo simplificado:
1. Los hashes perceptuales ya están calculados (DuplicatesSimilarAnalysis)
2. El usuario ajusta sensibilidad con slider
3. El clustering se hace en tiempo real (< 1 segundo)
4. Navegación simple por grupos
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSlider, QPushButton,
    QDialogButtonBox, QCheckBox, QScrollArea, QWidget,
    QGridLayout, QProgressBar, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QColor
from config import Config
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
    Diálogo para gestionar archivos similares (70-99% de similitud).
    
    IMPORTANTE: Este diálogo es para archivos SIMILARES, no idénticos.
    Para copias idénticas, usar el diálogo "Copias Visuales Idénticas".
    
    El slider de sensibilidad controla qué tan "parecidos" deben ser los archivos:
    - 95%: Muy similares (pequeñas diferencias)
    - 85%: Similar (recortes, ediciones menores) - RECOMENDADO
    - 70%: Algo similar (más diferencias toleradas)
    """
    
    # Sensibilidad por defecto: 85% es un buen balance
    DEFAULT_SENSITIVITY = 85
    
    def __init__(self, analysis: DuplicatesSimilarAnalysis, parent=None):
        super().__init__(parent)
        
        self.logger = get_logger('DuplicatesSimilarDialog')
        self.analysis = analysis
        
        # Estado inicial
        self.current_sensitivity = self.DEFAULT_SENSITIVITY
        self.current_result = None
        self.all_groups = []
        self.current_group_index = 0
        self.selections = {}  # {group_index: [files_to_delete]}
        self.accepted_plan = None
        
        self._setup_ui()
        
        # Mostrar advertencia si es apropiado
        self._show_visual_identical_warning()
        
        # Cargar grupos iniciales
        self._regenerate_groups()
    
    def _setup_ui(self):
        """Configura la interfaz del diálogo."""
        self.setWindowTitle("Gestionar Archivos Similares")
        self.setModal(True)
        self.resize(1280, 900)
        self.setMinimumSize(1100, 750)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Header
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='image-search',
            title='Archivos Similares',
            description='Detecta imágenes parecidas (ediciones, recortes, diferentes resoluciones)',
            metrics=[
                {'value': '0', 'label': 'Grupos', 'color': DesignSystem.COLOR_PRIMARY},
                {'value': '0', 'label': 'Similares', 'color': DesignSystem.COLOR_WARNING},
                {'value': '0 B', 'label': 'Recuperable', 'color': DesignSystem.COLOR_SUCCESS}
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
        
        # 2. Barra de sensibilidad
        sensitivity_bar = self._create_sensitivity_bar()
        content_layout.addWidget(sensitivity_bar)
        
        # 3. Info card (aviso sobre visual identical)
        self.info_card = self._create_info_card()
        content_layout.addWidget(self.info_card)
        
        # 4. Área de trabajo
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
        workspace_toolbar = self._create_navigation_toolbar()
        workspace_layout.addWidget(workspace_toolbar)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER_LIGHT};")
        workspace_layout.addWidget(separator)
        
        # Grid de imágenes
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
        
        # 5. Opciones de seguridad
        security_options = self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de eliminar",
            dry_run_label="Modo simulación"
        )
        content_layout.addWidget(security_options)
        
        # 6. Botones
        button_box = self.make_ok_cancel_buttons(
            ok_text="Eliminar Seleccionados",
            ok_enabled=False,
            button_style='danger'
        )
        self.delete_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
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
        
        # Icono
        icon = icon_manager.create_icon_label(
            'target', size=18, color=DesignSystem.COLOR_TEXT_SECONDARY
        )
        layout.addWidget(icon)
        
        # Label
        sens_label = QLabel("Sensibilidad:")
        sens_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; 
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(sens_label)
        
        # Marcadores de referencia: Baja - Media - Alta
        low_label = QLabel("Baja")
        low_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(low_label)
        
        # Slider (rango 70-95%, NO 100% porque eso es para identical)
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(70, 95)
        self.sensitivity_slider.setValue(self.current_sensitivity)
        self.sensitivity_slider.setFixedWidth(200)
        self.sensitivity_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sensitivity_slider.setToolTip(
            "Ajusta qué tan parecidas deben ser las imágenes para agruparlas.\n"
            "• 95%: Muy similares (pequeñas diferencias)\n"
            "• 85%: Similar (recomendado)\n"
            "• 70%: Más tolerante (más grupos)"
        )
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
            }}
            QSlider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.sensitivity_slider)
        
        high_label = QLabel("Alta")
        high_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(high_label)
        
        # Valor actual
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
        actions_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; 
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(actions_label)
        
        strategies = [
            ("Mantener mejor", "keep_largest", "Conservar archivo de mayor calidad"),
            ("Mantener primero", "keep_first", "Conservar primer archivo del grupo"),
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
            btn.clicked.connect(lambda _, s=strategy: self._apply_strategy_current_group(s))
            layout.addWidget(btn)
        
        # Conexiones
        self.sensitivity_slider.valueChanged.connect(self._on_slider_changed)
        self.sensitivity_slider.sliderReleased.connect(self._on_slider_released)
        
        return toolbar

    def _create_info_card(self) -> QFrame:
        """Crea tarjeta informativa sobre el uso correcto de esta herramienta."""
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
        
        icon = icon_manager.create_icon_label(
            'information-outline', size=20, color=DesignSystem.COLOR_INFO
        )
        layout.addWidget(icon)
        
        text = QLabel(
            "<b>Consejo:</b> Esta herramienta detecta imágenes <i>similares</i> "
            "(recortes, ediciones, diferentes resoluciones). "
            "Para eliminar copias <i>idénticas</i> visualmente, "
            "usa primero la herramienta \"Copias Visuales Idénticas\"."
        )
        text.setWordWrap(True)
        text.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        layout.addWidget(text, stretch=1)
        
        return card

    def _create_navigation_toolbar(self) -> QWidget:
        """Crea la barra de navegación entre grupos."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
            DesignSystem.SPACE_16, DesignSystem.SPACE_12
        )
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Navegación
        self.prev_btn = self.make_styled_button(
            icon_name='chevron-left',
            button_style='secondary',
            tooltip="Grupo Anterior"
        )
        self.prev_btn.clicked.connect(self._previous_group)
        
        self.group_counter_label = QLabel("Grupo 0 de 0")
        self.group_counter_label.setMinimumWidth(200)
        self.group_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_counter_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; 
            color: {DesignSystem.COLOR_TEXT};
        """)
        
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
        
        # Contador de selección
        self.global_summary_label = QLabel("0 archivos seleccionados (0 B)")
        self.global_summary_label.setMinimumWidth(250)
        self.global_summary_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.global_summary_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; 
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(self.global_summary_label)
        
        return container

    # ================= LÓGICA =================

    def _show_visual_identical_warning(self):
        """Muestra advertencia si hay muchos archivos y no se ha usado visual_identical."""
        total_files = len(self.analysis.perceptual_hashes)
        
        if total_files > 1000:
            # Solo mostrar una vez, no molestar
            self.logger.info(
                f"Dataset grande ({total_files:,} archivos). "
                "Recomendado usar Visual Identical primero."
            )

    def _on_slider_changed(self, value: int):
        """Actualiza el label mientras se mueve el slider."""
        self.current_sensitivity = value
        self.sensitivity_value_label.setText(f"{value}%")

    def _on_slider_released(self):
        """Regenera grupos cuando se suelta el slider."""
        self._regenerate_groups()

    def _regenerate_groups(self):
        """Regenera los grupos con la sensibilidad actual."""
        from PyQt6.QtWidgets import QApplication
        
        self.logger.info(f"Regenerando grupos con sensibilidad {self.current_sensitivity}%...")
        
        # Cursor de espera
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # Obtener grupos usando el método del análisis
            result = self.analysis.get_groups(self.current_sensitivity)
            self.current_result = result
            self.all_groups = result.groups.copy()
            
            self.logger.info(f"Encontrados {len(self.all_groups)} grupos")
            
            # Limpiar selecciones previas
            self.selections.clear()
            
            # Actualizar UI
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
        groups = self.all_groups
        total_groups = len(groups)
        total_similar = sum(len(g.files) - 1 for g in groups)
        space_potential = sum(
            (len(g.files) - 1) * (g.total_size // len(g.files))
            for g in groups if g.files
        )
        
        self._update_header_metric(self.header_frame, 'Grupos', str(total_groups))
        self._update_header_metric(self.header_frame, 'Similares', str(total_similar))
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(space_potential))

    def _show_no_groups_message(self):
        """Muestra mensaje cuando no hay grupos."""
        for i in reversed(range(self.group_layout.count())):
            w = self.group_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        icon_label = icon_manager.create_icon_label(
            'check-circle', size=64, color=DesignSystem.COLOR_SUCCESS
        )
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        msg = QLabel(
            "No se encontraron archivos similares\n"
            f"con sensibilidad {self.current_sensitivity}%\n\n"
            "Prueba a reducir la sensibilidad para\n"
            "detectar archivos con más diferencias."
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_MD}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
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
        
        # Actualizar contador
        self.group_counter_label.setText(f"Grupo {index + 1} de {len(self.all_groups)}")
        self.prev_btn.setEnabled(len(self.all_groups) > 1)
        self.next_btn.setEnabled(len(self.all_groups) > 1)
        
        # Limpiar contenedor
        for i in reversed(range(self.group_layout.count())):
            w = self.group_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        
        # Info de similitud
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
        """Crea widget con info de similitud del grupo."""
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
        
        # Badge
        badge = QLabel(f"{score:.1f}% Similitud")
        badge.setStyleSheet(f"""
            background-color: {color}20;
            color: {color};
            border: 1px solid {color}40;
            border-radius: 12px;
            padding: 4px 12px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        layout.addWidget(badge)
        
        # Barra
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(score))
        progress.setFixedWidth(120)
        progress.setTextVisible(False)
        progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: {DesignSystem.COLOR_BORDER_LIGHT};
                border-radius: 2px;
                height: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(progress)
        
        # Info de archivos
        files_info = QLabel(f"{len(group.files)} archivos · {format_size(group.total_size)}")
        files_info.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        layout.addWidget(files_info)
        
        layout.addStretch()
        
        return container

    def _create_file_card(self, file_path: Path, is_selected: bool) -> QFrame:
        """Crea tarjeta para un archivo."""
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mouseDoubleClickEvent = lambda e: show_file_details_dialog(file_path, self)
        card.setStyleSheet(self._get_card_style(is_selected))
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_8)
        layout.setContentsMargins(
            DesignSystem.SPACE_8, DesignSystem.SPACE_8,
            DesignSystem.SPACE_8, DesignSystem.SPACE_8
        )
        
        # Header: Checkbox + Tamaño
        header = QHBoxLayout()
        
        checkbox = QCheckBox("Eliminar")
        checkbox.setChecked(is_selected)
        checkbox.setStyleSheet(f"""
            QCheckBox {{ 
                color: {DesignSystem.COLOR_DANGER}; 
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; 
            }}
        """)
        checkbox.toggled.connect(
            lambda checked, f=file_path: self._toggle_file_selection(f, checked)
        )
        header.addWidget(checkbox)
        
        header.addStretch()
        
        # Info badge
        info_badge = self._create_info_badge(file_path)
        header.addWidget(info_badge)
        
        try:
            size_text = format_size(file_path.stat().st_size)
        except:
            size_text = "?"
        size_lbl = QLabel(size_text)
        size_lbl.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY}; 
            font-size: {DesignSystem.FONT_SIZE_XS}px;
        """)
        header.addWidget(size_lbl)
        
        layout.addLayout(header)
        
        # Thumbnail
        thumb_lbl, is_video = self._create_thumbnail(file_path)
        if thumb_lbl:
            thumb_lbl.mousePressEvent = lambda e, f=file_path, v=is_video: self._handle_thumbnail_click(f, v)
            layout.addWidget(thumb_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Nombre
        name_lbl = QLabel(file_path.name)
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px; 
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(name_lbl)
        
        # Fecha
        date_info = self._get_file_date_info(file_path)
        if date_info:
            date_lbl = QLabel(date_info)
            date_lbl.setWordWrap(True)
            date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            date_lbl.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            """)
            layout.addWidget(date_lbl)
        
        card.setProperty("file_path", str(file_path))
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, f=file_path: self._show_context_menu(pos, f)
        )
        
        return card

    def _create_info_badge(self, file_path: Path) -> QLabel:
        """Crea badge de info."""
        badge = QLabel()
        info_icon = icon_manager.get_icon(
            'information-outline', size=16, color=DesignSystem.COLOR_PRIMARY
        )
        badge.setPixmap(info_icon.pixmap(16, 16))
        badge.setFixedSize(20, 20)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(DesignSystem.get_info_badge_style())
        badge.setCursor(Qt.CursorShape.PointingHandCursor)
        badge.mousePressEvent = lambda e, f=file_path: show_file_details_dialog(f, self)
        return badge

    def _get_card_style(self, is_selected: bool) -> str:
        """Retorna estilo para la tarjeta según selección."""
        border_color = DesignSystem.COLOR_DANGER if is_selected else DesignSystem.COLOR_BORDER
        bg_color = DesignSystem.COLOR_DANGER_BG if is_selected else DesignSystem.COLOR_SURFACE
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

    def _toggle_file_selection(self, file_path: Path, checked: bool):
        """Toggle selección de archivo."""
        if self.current_group_index not in self.selections:
            self.selections[self.current_group_index] = []
        
        if checked:
            if file_path not in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].append(file_path)
        else:
            if file_path in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].remove(file_path)
        
        self._update_summary()
        self._update_card_visuals(file_path, checked)

    def _update_card_visuals(self, file_path: Path, is_selected: bool):
        """Actualiza visual de una tarjeta específica."""
        scroll_area = None
        for i in range(self.group_layout.count()):
            item = self.group_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), QScrollArea):
                scroll_area = item.widget()
                break
        
        if not scroll_area:
            return
        
        grid_widget = scroll_area.widget()
        if not grid_widget:
            return
        
        grid_layout = grid_widget.layout()
        if not grid_layout:
            return
        
        target_path = str(file_path)
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(i)
            card = item.widget()
            if card and card.property("file_path") == target_path:
                card.setStyleSheet(self._get_card_style(is_selected))
                checkbox = card.findChild(QCheckBox)
                if checkbox:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(is_selected)
                    checkbox.blockSignals(False)
                break

    def _update_summary(self):
        """Actualiza resumen de selección."""
        total_files = sum(len(l) for l in self.selections.values())
        total_bytes = 0
        for files in self.selections.values():
            for f in files:
                try:
                    total_bytes += f.stat().st_size
                except:
                    pass
        
        self.global_summary_label.setText(
            f"{total_files} archivos seleccionados ({format_size(total_bytes)})"
        )
        self.delete_btn.setEnabled(total_files > 0)
        self.delete_btn.setText(f"Eliminar {total_files} Archivos")

    def _previous_group(self):
        """Navega al grupo anterior."""
        if self.all_groups:
            new_index = (self.current_group_index - 1) % len(self.all_groups)
            self._load_group(new_index)

    def _next_group(self):
        """Navega al siguiente grupo."""
        if self.all_groups:
            new_index = (self.current_group_index + 1) % len(self.all_groups)
            self._load_group(new_index)

    def _apply_strategy_current_group(self, strategy: str):
        """Aplica estrategia de selección al grupo actual."""
        if not self.all_groups:
            return
        
        group = self.all_groups[self.current_group_index]
        files = group.files
        if len(files) < 2:
            return
        
        to_delete = []
        if strategy == 'keep_first':
            to_delete = files[1:]
        elif strategy == 'keep_largest':
            sorted_files = sorted(files, key=lambda f: f.stat().st_size, reverse=True)
            to_delete = sorted_files[1:]
        
        self.selections[self.current_group_index] = list(to_delete)
        self._load_group(self.current_group_index)
        self._update_summary()

    def _show_context_menu(self, pos, file_path: Path):
        """Muestra menú contextual."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        
        details_action = menu.addAction(
            icon_manager.get_icon('information-outline'), "Ver detalles"
        )
        details_action.triggered.connect(
            lambda: show_file_details_dialog(file_path, self)
        )
        
        menu.exec(QCursor.pos())

    def accept(self):
        """Construye plan de eliminación."""
        selected_groups = []
        for group_index, files_to_delete in self.selections.items():
            if files_to_delete and group_index < len(self.all_groups):
                original_group = self.all_groups[group_index]
                selected_group = DuplicateGroup(
                    hash_value=original_group.hash_value,
                    files=files_to_delete,
                    total_size=sum(f.stat().st_size for f in files_to_delete if f.exists()),
                    similarity_score=original_group.similarity_score
                )
                selected_groups.append(selected_group)
        
        from services.result_types import DuplicateAnalysisResult
        analysis = DuplicateAnalysisResult(
            groups=selected_groups,
            mode='perceptual',
            items_count=len(selected_groups),
            total_groups=len(selected_groups),
            space_wasted=sum(g.total_size for g in selected_groups)
        )
        
        self.accepted_plan = {
            'analysis': analysis,
            'keep_strategy': 'manual',
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        super().accept()

    def _get_file_date_info(self, file_path: Path) -> str:
        """Obtiene info de fecha del archivo."""
        try:
            from utils.date_utils import select_best_date_from_file, get_all_metadata_from_file
            
            file_metadata = get_all_metadata_from_file(file_path)
            selected_date, source = select_best_date_from_file(file_metadata)
            
            if not selected_date or not source:
                return ""
            
            date_str = selected_date.strftime('%Y-%m-%d %H:%M:%S')
            
            # Simplificar nombre de fuente
            if 'EXIF' in source:
                source_short = 'EXIF'
            elif 'Filename' in source:
                source_short = 'Nombre'
            elif 'mtime' in source:
                source_short = 'Modificación'
            else:
                source_short = source[:15]
            
            return f"{date_str}\n({source_short})"
            
        except Exception:
            return ""

    def _create_thumbnail(self, file_path: Path):
        """Crea thumbnail para imagen o video."""
        try:
            from utils.file_utils import is_video_file
            is_video = is_video_file(str(file_path))
            
            if is_video:
                pixmap = get_video_thumbnail(file_path, max_size=(280, 280), frame_position=0.25)
                if pixmap and not pixmap.isNull():
                    pixmap = self._add_play_icon_overlay(pixmap)
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
            lbl.setStyleSheet(f"""
                background-color: {DesignSystem.COLOR_BACKGROUND}; 
                border-radius: 4px;
            """)
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            
            return lbl, is_video
            
        except Exception as e:
            self.logger.debug(f"Error creando thumbnail: {e}")
            return None, False

    def _add_play_icon_overlay(self, pixmap: QPixmap) -> QPixmap:
        """Agrega icono de play sobre thumbnail de video."""
        result = QPixmap(pixmap.size())
        result.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, pixmap)
        painter.fillRect(result.rect(), QColor(0, 0, 0, 60))
        
        icon_size = 64
        play_icon = icon_manager.get_icon('play-circle', color=DesignSystem.COLOR_SURFACE)
        icon_pixmap = play_icon.pixmap(QSize(icon_size, icon_size))
        
        x = (pixmap.width() - icon_size) // 2
        y = (pixmap.height() - icon_size) // 2
        
        painter.drawPixmap(x, y, icon_pixmap)
        painter.end()
        
        return result

    def _handle_thumbnail_click(self, file_path: Path, is_video: bool):
        """Maneja click en thumbnail."""
        if is_video:
            open_file_with_default_app(file_path)
        else:
            dialog = ImagePreviewDialog(file_path, self)
            dialog.exec()
