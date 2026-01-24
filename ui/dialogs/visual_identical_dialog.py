"""
Diálogo de gestión de copias visuales idénticas.

Muestra archivos que son visualmente IDÉNTICOS al 100% aunque tengan
diferente resolución, compresión o metadatos (fechas, EXIF, etc.).

Diseño similar a DuplicatesExactDialog pero optimizado para el caso
de uso de detección visual (ej: fotos de WhatsApp, copias redimensionadas).
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QFrame, QTreeWidget, QTreeWidgetItem, QLineEdit,
    QComboBox, QMessageBox, QMenu, QWidget, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QColor, QShowEvent

from services.result_types import VisualIdenticalAnalysisResult, VisualIdenticalGroup
from services.file_metadata_repository_cache import FileInfoRepositoryCache
from utils.format_utils import format_size
from utils.logger import get_logger
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from .base_dialog import BaseDialog
from .dialog_utils import show_file_details_dialog


class VisualIdenticalDialog(BaseDialog):
    """
    Diálogo para gestionar copias visuales idénticas.
    
    Muestra archivos visualmente idénticos (mismo hash perceptual)
    aunque tengan diferente tamaño, resolución o metadatos.
    Permite eliminar duplicados con estrategias automáticas.
    """
    
    # Constantes para paginación
    INITIAL_LOAD = 100
    LOAD_INCREMENT = 100
    WARNING_THRESHOLD = 500
    
    def __init__(self, analysis: VisualIdenticalAnalysisResult, parent=None):
        super().__init__(parent)
        self.logger = get_logger('VisualIdenticalDialog')
        self.analysis = analysis
        self.repo = FileInfoRepositoryCache.get_instance()
        
        # Estrategia de conservación por defecto: mantener mejor calidad (más grande)
        self.keep_strategy = 'largest'
        self.accepted_plan = None
        
        # Estado de grupos
        self.all_groups = analysis.groups
        self.filtered_groups = analysis.groups
        self.loaded_count = 0
        
        # Referencias a widgets
        self.tree_widget = None
        self.search_input = None
        self.filter_combo = None
        self.loaded_chip = None
        self.filtered_chip = None
        self.load_more_btn = None
        self.load_all_btn = None
        self.progress_indicator = None
        self.progress_bar_container = None
        self.progress_bar_fill = None
        self.delete_btn = None
        
        self._init_ui()
    
    def _get_best_date_timestamp(self, file_path: Path) -> float:
        """Obtiene el timestamp de la mejor fecha disponible."""
        if self.repo:
            best_date, _ = self.repo.get_best_date(file_path)
            if best_date:
                return best_date.timestamp()
            
            fs_mtime = self.repo.get_filesystem_modification_date(file_path)
            if fs_mtime:
                return fs_mtime.timestamp()
        
        return file_path.stat().st_mtime if file_path.exists() else 0
    
    def _get_file_size(self, file_path: Path) -> int:
        """Obtiene el tamaño del archivo desde caché o disco."""
        if self.repo:
            meta = self.repo.get_file_metadata(file_path)
            if meta:
                return meta.fs_size
        return file_path.stat().st_size if file_path.exists() else 0
    
    def _calculate_recoverable_space(self) -> int:
        """Calcula el espacio total recuperable según la estrategia actual."""
        total_recoverable = 0
        
        for group in self.filtered_groups:
            if len(group.files) < 2:
                continue
                
            # Obtener tamaños
            sizes = []
            for f in group.files:
                sizes.append((f, self._get_file_size(f)))
            
            # Determinar qué archivo mantener según estrategia
            if self.keep_strategy == 'largest':
                keep_file = max(sizes, key=lambda x: x[1])[0]
            elif self.keep_strategy == 'smallest':
                keep_file = min(sizes, key=lambda x: x[1])[0]
            elif self.keep_strategy == 'oldest':
                keep_file = min(group.files, key=lambda f: self._get_best_date_timestamp(f))
            else:  # newest
                keep_file = max(group.files, key=lambda f: self._get_best_date_timestamp(f))
            
            # Sumar tamaños de archivos a eliminar
            for f, size in sizes:
                if f != keep_file:
                    total_recoverable += size
        
        return total_recoverable
    
    def _init_ui(self):
        """Configura la interfaz del diálogo."""
        self.setWindowTitle("Gestionar copias visuales idénticas")
        self.setModal(True)
        self.resize(1200, 900)
        self.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(int(DesignSystem.SPACE_12))
        layout.setContentsMargins(0, 0, 0, int(DesignSystem.SPACE_20))
        
        # Header compacto con métricas
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='image-multiple',
            title='Copias visuales idénticas',
            description='Archivos visualmente idénticos aunque tengan diferente resolución, '
                       'compresión o metadatos. Típico de fotos enviadas por WhatsApp o copias redimensionadas.',
            metrics=[
                {
                    'value': str(self.analysis.total_groups),
                    'label': 'Grupos',
                    'color': DesignSystem.COLOR_PRIMARY
                },
                {
                    'value': str(self.analysis.total_duplicates),
                    'label': 'Duplicados',
                    'color': DesignSystem.COLOR_WARNING
                },
                {
                    'value': format_size(self._calculate_recoverable_space()),
                    'label': 'Recuperable',
                    'color': DesignSystem.COLOR_SUCCESS
                }
            ]
        )
        layout.addWidget(self.header_frame)
        
        # Contenedor con margen para el resto
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(int(DesignSystem.SPACE_16))
        content_layout.setContentsMargins(
            int(DesignSystem.SPACE_24),
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_24),
            0
        )
        layout.addWidget(content_container)
        
        # Selector de estrategia
        self.strategy_selector = self._create_strategy_selector()
        content_layout.addWidget(self.strategy_selector)
        
        # Advertencia si hay muchos grupos
        if len(self.all_groups) > self.WARNING_THRESHOLD:
            warning = QLabel(
                f"<b>ℹ️ {len(self.all_groups)} grupos encontrados.</b> "
                f"Se cargan {self.INITIAL_LOAD} grupos inicialmente. "
                f"Usa búsqueda y filtros para encontrar grupos específicos."
            )
            warning.setTextFormat(Qt.TextFormat.RichText)
            warning.setWordWrap(True)
            warning.setStyleSheet(f"""
                QLabel {{
                    background: {DesignSystem.COLOR_INFO_BG};
                    border: 1px solid {DesignSystem.COLOR_INFO};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_12}px;
                    color: {DesignSystem.COLOR_TEXT};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                }}
            """)
            content_layout.addWidget(warning)
        
        # Barra de búsqueda y filtros
        search_card = self._create_search_bar()
        content_layout.addWidget(search_card)
        
        # Árbol de grupos
        self.tree_widget = self._create_tree_widget()
        content_layout.addWidget(self.tree_widget)
        
        # Paginación
        pagination_card = self._create_pagination_bar()
        content_layout.addWidget(pagination_card)
        
        # Opciones de seguridad
        security_options = self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de eliminar",
            dry_run_label="Modo simulación (no eliminar realmente)"
        )
        content_layout.addWidget(security_options)
        
        # Botones de acción
        button_box = self.make_ok_cancel_buttons(
            ok_text="Eliminar duplicados",
            ok_enabled=len(self.all_groups) > 0,
            button_style='danger'
        )
        self.delete_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        content_layout.addWidget(button_box)
        
        # Cargar grupos iniciales
        self._load_initial_groups()
    
    def _create_strategy_selector(self) -> QFrame:
        """Crea el selector de estrategia de conservación."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(int(DesignSystem.SPACE_12))
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Título
        title = QLabel("Estrategia de conservación")
        title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_MD}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(title)
        
        # Descripción
        desc = QLabel("Elige qué archivo conservar de cada grupo de duplicados:")
        desc.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        layout.addWidget(desc)
        
        # Botones de estrategia
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(int(DesignSystem.SPACE_12))
        
        strategies = [
            ('largest', 'arrow-expand-all', 'Mejor calidad', 'Conserva el archivo más grande (mejor resolución)'),
            ('smallest', 'arrow-collapse-all', 'Menor tamaño', 'Conserva el archivo más pequeño (ahorra espacio)'),
            ('oldest', 'clock-outline', 'Más antiguo', 'Conserva el archivo con fecha más antigua'),
            ('newest', 'clock-fast', 'Más reciente', 'Conserva el archivo con fecha más reciente'),
        ]
        
        self.strategy_buttons = {}
        
        for strategy_id, icon_name, label, tooltip in strategies:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(strategy_id == self.keep_strategy)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            icon_manager.set_button_icon(btn, icon_name, size=18)
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DesignSystem.COLOR_BG_1};
                    border: 2px solid {DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_20}px;
                    font-size: {DesignSystem.FONT_SIZE_BASE}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                    color: {DesignSystem.COLOR_TEXT};
                }}
                QPushButton:hover {{
                    border-color: {DesignSystem.COLOR_PRIMARY};
                    background-color: {DesignSystem.COLOR_SURFACE};
                }}
                QPushButton:checked {{
                    background-color: {DesignSystem.COLOR_PRIMARY};
                    border-color: {DesignSystem.COLOR_PRIMARY};
                    color: {DesignSystem.COLOR_PRIMARY_TEXT};
                }}
            """)
            
            btn.clicked.connect(lambda checked, s=strategy_id: self._on_strategy_changed(s))
            buttons_layout.addWidget(btn)
            self.strategy_buttons[strategy_id] = btn
        
        layout.addLayout(buttons_layout)
        
        return frame
    
    def _create_search_bar(self) -> QFrame:
        """Crea la barra de búsqueda y filtros."""
        search_card = QFrame()
        search_card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px;
            }}
        """)
        
        search_layout = QHBoxLayout(search_card)
        search_layout.setSpacing(int(DesignSystem.SPACE_12))
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        # Input de búsqueda
        search_container = QWidget()
        search_container_layout = QHBoxLayout(search_container)
        search_container_layout.setContentsMargins(
            int(DesignSystem.SPACE_12), 
            int(DesignSystem.SPACE_8),
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_8)
        )
        search_container_layout.setSpacing(int(DesignSystem.SPACE_8))
        
        search_icon = QLabel()
        icon_manager.set_label_icon(search_icon, 'magnify', size=18)
        search_container_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre o ruta...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
        """)
        search_container_layout.addWidget(self.search_input, 1)
        
        search_container.setStyleSheet(f"""
            QWidget {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
        """)
        search_layout.addWidget(search_container, 3)
        
        # Filtro por tamaño
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Todos los grupos",
            "Grupos grandes (>10 MB)",
            "Grupos muy grandes (>50 MB)",
            "Mucha variación de tamaño (>50%)",
            "Muchas copias (3+)",
            "Muchas copias (5+)"
        ])
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
                min-width: 220px;
            }}
        """)
        search_layout.addWidget(self.filter_combo, 2)
        
        # Chips de conteo
        self.loaded_chip = QLabel()
        self.loaded_chip.setStyleSheet(f"""
            QLabel {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            }}
        """)
        search_layout.addWidget(self.loaded_chip)
        
        self.filtered_chip = QLabel()
        self.filtered_chip.setStyleSheet(f"""
            QLabel {{
                background-color: {DesignSystem.COLOR_WARNING};
                color: {DesignSystem.COLOR_SURFACE};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            }}
        """)
        self.filtered_chip.hide()
        search_layout.addWidget(self.filtered_chip)
        
        return search_card
    
    def _create_tree_widget(self) -> QTreeWidget:
        """Crea el widget de árbol para mostrar grupos."""
        tree = QTreeWidget()
        tree.setHeaderLabels(["Grupos / Archivos", "Tamaño", "Fecha", "Ubicación", "Estado"])
        tree.setColumnWidth(0, 350)
        tree.setColumnWidth(1, 100)
        tree.setColumnWidth(2, 150)
        tree.setColumnWidth(3, 250)
        tree.setColumnWidth(4, 120)
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(True)
        tree.setAnimated(True)
        tree.setIndentation(20)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                background-color: {DesignSystem.COLOR_SURFACE};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QTreeWidget::item {{
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_4}px;
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};
            }}
            QTreeWidget::item:hover {{
                background-color: {DesignSystem.COLOR_BG_2};
            }}
            QTreeWidget::item:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT};
            }}
            QHeaderView::section {{
                background-color: {DesignSystem.COLOR_BG_1};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_8}px;
                border: none;
                border-bottom: 2px solid {DesignSystem.COLOR_BORDER};
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
        """)
        tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        tree.customContextMenuRequested.connect(self._show_context_menu)
        
        return tree
    
    def _create_pagination_bar(self) -> QFrame:
        """Crea la barra de paginación."""
        pagination_card = QFrame()
        pagination_card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_16}px;
            }}
        """)
        
        pagination_layout = QHBoxLayout(pagination_card)
        pagination_layout.setSpacing(int(DesignSystem.SPACE_12))
        pagination_layout.setContentsMargins(0, 0, 0, 0)
        
        # Indicador de progreso
        self.progress_indicator = QLabel()
        self.progress_indicator.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
        """)
        pagination_layout.addWidget(self.progress_indicator)
        
        # Barra de progreso
        self.progress_bar_container = QFrame()
        self.progress_bar_container.setFixedHeight(8)
        self.progress_bar_container.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BORDER};
                border-radius: 4px;
            }}
        """)
        
        self.progress_bar_fill = QFrame(self.progress_bar_container)
        self.progress_bar_fill.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                border-radius: 4px;
            }}
        """)
        self.progress_bar_fill.setGeometry(0, 0, 0, 8)
        
        pagination_layout.addWidget(self.progress_bar_container, 1)
        
        # Botón cargar todos
        self.load_all_btn = QPushButton("Cargar todos")
        icon_manager.set_button_icon(self.load_all_btn, 'download', size=16)
        self.load_all_btn.clicked.connect(self._load_all_groups)
        self.load_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {DesignSystem.COLOR_PRIMARY};
                border: 2px solid {DesignSystem.COLOR_PRIMARY};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_16}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
            }}
        """)
        self.load_all_btn.hide()
        pagination_layout.addWidget(self.load_all_btn)
        
        # Botón cargar más
        self.load_more_btn = QPushButton("Cargar más")
        icon_manager.set_button_icon(self.load_more_btn, 'refresh', size=18)
        self.load_more_btn.clicked.connect(self._load_more_groups)
        self.load_more_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_10}px {DesignSystem.SPACE_20}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
        """)
        pagination_layout.addWidget(self.load_more_btn)
        
        return pagination_card
    
    def _load_initial_groups(self):
        """Carga los grupos iniciales en el árbol."""
        self.loaded_count = 0
        self.tree_widget.clear()
        self._load_more_groups()
    
    def _load_more_groups(self):
        """Carga más grupos en el árbol."""
        start = self.loaded_count
        end = min(start + self.LOAD_INCREMENT, len(self.filtered_groups))
        
        for i in range(start, end):
            group = self.filtered_groups[i]
            self._add_group_to_tree(group, i + 1)
        
        self.loaded_count = end
        self._update_pagination_ui()
    
    def _load_all_groups(self):
        """Carga todos los grupos restantes."""
        if len(self.filtered_groups) > 1000:
            reply = QMessageBox.question(
                self,
                "Cargar todos los grupos",
                f"Hay {len(self.filtered_groups)} grupos. ¿Seguro que quieres cargarlos todos?\n"
                "Esto puede tardar y consumir memoria.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        while self.loaded_count < len(self.filtered_groups):
            self._load_more_groups()
    
    def _add_group_to_tree(self, group: VisualIdenticalGroup, group_num: int):
        """Añade un grupo al árbol con estilo Material Design."""
        from .dialog_utils import apply_group_item_style, create_group_tooltip
        
        # Determinar archivo a conservar
        keep_file = self._get_file_to_keep(group)
        file_count = len(group.files)
        
        # Crear item de grupo
        group_item = QTreeWidgetItem()
        group_item.setText(0, f"Grupo #{group_num} • {file_count} copias")
        # Las otras columnas quedan vacías para grupos - solo se usan para archivos
        
        # Aplicar estilo unificado de grupo
        apply_group_item_style(group_item, num_columns=5)
        
        # Tooltip informativo sobre doble click
        extra_info = ""
        if group.size_variation_percent > 10:
            extra_info = f"⚠ Variación de tamaño: {group.size_variation_percent:.0f}%"
        
        group_item.setToolTip(0, create_group_tooltip(
            group_num,
            f"{file_count} archivos visualmente idénticos",
            extra_info
        ))
        
        group_item.setData(0, Qt.ItemDataRole.UserRole, group)
        group_item.setExpanded(True)
        
        # Añadir archivos del grupo
        for i, file_path in enumerate(group.files):
            file_size = group.file_sizes[i] if i < len(group.file_sizes) else 0
            is_keep = file_path == keep_file
            
            self._add_file_to_group(group_item, file_path, file_size, is_keep)
        
        self.tree_widget.addTopLevelItem(group_item)
    
    def _add_file_to_group(self, parent_item: QTreeWidgetItem, file_path: Path, 
                           file_size: int, is_keep: bool):
        """Añade un archivo a un grupo en el árbol."""
        from .dialog_utils import apply_file_item_status, get_file_icon_name
        from ui.styles.icons import icon_manager
        
        file_item = QTreeWidgetItem()
        
        # Icono según tipo de archivo
        icon_name = get_file_icon_name(file_path)
        file_item.setIcon(0, icon_manager.get_icon(icon_name, size=18))
        
        # Nombre del archivo
        file_item.setText(0, file_path.name)
        
        # Tamaño
        file_item.setText(1, format_size(file_size))
        
        # Fecha
        best_date, source = self.repo.get_best_date(file_path) if self.repo else (None, None)
        if best_date:
            file_item.setText(2, best_date.strftime("%Y-%m-%d %H:%M"))
        else:
            file_item.setText(2, "-")
        
        # Ubicación
        file_item.setText(3, str(file_path.parent))
        
        # Estado (conservar/eliminar) - usar función común
        apply_file_item_status(file_item, is_keep, status_column=4)
        
        file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
        parent_item.addChild(file_item)
    
    def _get_file_to_keep(self, group: VisualIdenticalGroup) -> Path:
        """Determina qué archivo conservar según la estrategia."""
        if not group.files:
            return None
        
        if self.keep_strategy == 'largest':
            if group.file_sizes:
                max_idx = group.file_sizes.index(max(group.file_sizes))
                return group.files[max_idx]
            return max(group.files, key=lambda f: self._get_file_size(f))
        
        elif self.keep_strategy == 'smallest':
            if group.file_sizes:
                min_idx = group.file_sizes.index(min(group.file_sizes))
                return group.files[min_idx]
            return min(group.files, key=lambda f: self._get_file_size(f))
        
        elif self.keep_strategy == 'oldest':
            return min(group.files, key=lambda f: self._get_best_date_timestamp(f))
        
        else:  # newest
            return max(group.files, key=lambda f: self._get_best_date_timestamp(f))
    
    def _update_pagination_ui(self):
        """Actualiza la UI de paginación."""
        total = len(self.filtered_groups)
        loaded = self.loaded_count
        
        self.loaded_chip.setText(f"{loaded} cargados")
        
        if total != len(self.all_groups):
            self.filtered_chip.setText(f"{total} de {len(self.all_groups)}")
            self.filtered_chip.show()
        else:
            self.filtered_chip.hide()
        
        # Progreso
        if total > 0:
            percent = (loaded / total) * 100
            self.progress_indicator.setText(f"{percent:.0f}% cargado ({loaded}/{total})")
            
            # Actualizar barra
            bar_width = self.progress_bar_container.width()
            fill_width = int(bar_width * loaded / total)
            self.progress_bar_fill.setGeometry(0, 0, fill_width, 8)
        
        # Mostrar/ocultar botones
        has_more = loaded < total
        self.load_more_btn.setVisible(has_more)
        self.load_all_btn.setVisible(has_more and total > self.LOAD_INCREMENT * 2)
        
        if has_more:
            remaining = total - loaded
            self.load_more_btn.setText(f"Cargar {min(self.LOAD_INCREMENT, remaining)} más")
    
    def _on_strategy_changed(self, strategy: str):
        """Maneja el cambio de estrategia."""
        self.keep_strategy = strategy
        
        # Actualizar botones
        for s, btn in self.strategy_buttons.items():
            btn.setChecked(s == strategy)
        
        # Recargar árbol para reflejar nueva estrategia
        self._load_initial_groups()
        
        # Actualizar métrica de espacio recuperable
        self._update_header_metric(
            self.header_frame, 
            'Recuperable', 
            format_size(self._calculate_recoverable_space())
        )
    
    def _on_search_changed(self, text: str):
        """Maneja cambios en la búsqueda."""
        self._apply_filters()
    
    def _on_filter_changed(self, index: int):
        """Maneja cambios en el filtro."""
        self._apply_filters()
    
    def _apply_filters(self):
        """Aplica filtros de búsqueda y tamaño."""
        search_text = self.search_input.text().lower()
        filter_index = self.filter_combo.currentIndex()
        
        filtered = []
        
        for group in self.all_groups:
            # Filtro de búsqueda
            if search_text:
                matches = False
                for f in group.files:
                    if search_text in str(f).lower():
                        matches = True
                        break
                if not matches:
                    continue
            
            # Filtro por tamaño/cantidad
            if filter_index == 1:  # >10 MB
                if group.total_size < 10 * 1024 * 1024:
                    continue
            elif filter_index == 2:  # >50 MB
                if group.total_size < 50 * 1024 * 1024:
                    continue
            elif filter_index == 3:  # Mucha variación
                if group.size_variation_percent < 50:
                    continue
            elif filter_index == 4:  # 3+ copias
                if len(group.files) < 3:
                    continue
            elif filter_index == 5:  # 5+ copias
                if len(group.files) < 5:
                    continue
            
            filtered.append(group)
        
        self.filtered_groups = filtered
        self._load_initial_groups()
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Maneja doble clic: expande grupos o abre archivos."""
        from .dialog_utils import handle_tree_item_double_click
        handle_tree_item_double_click(item, column, self)
    
    def _show_context_menu(self, pos):
        """Muestra menú contextual para archivos individuales."""
        from .dialog_utils import show_file_context_menu
        show_file_context_menu(self.tree_widget, pos, self, details_callback=self._show_file_details)
    
    def _show_file_details(self, file_path: Path):
        """Muestra diálogo con detalles del archivo."""
        # Determinar el estado del archivo (mantener/eliminar)
        # Buscar en qué grupo está este archivo
        status_info = None
        for group in self.filtered_groups:
            if file_path in group.files:
                # Determinar qué archivo se mantiene
                keep_file = self._get_file_to_keep(group)
                
                is_keep = file_path == keep_file
                status_info = {
                    'metadata': {
                        'Estado': 'Se mantendrá' if is_keep else 'Se eliminará',
                        'Grupo': f'{len(group.files)} archivos visualmente idénticos',
                        'Espacio grupo': format_size(group.total_size),
                        'Estrategia': self._strategy_name()
                    }
                }
                break
        
        show_file_details_dialog(file_path, self, status_info)
    
    def accept(self):
        """Maneja la aceptación del diálogo."""
        # Recopilar archivos a eliminar
        files_to_delete = []
        
        for group in self.filtered_groups:
            keep_file = self._get_file_to_keep(group)
            for f in group.files:
                if f != keep_file:
                    files_to_delete.append(f)
        
        if not files_to_delete:
            QMessageBox.information(
                self,
                "Sin cambios",
                "No hay archivos para eliminar."
            )
            return
        
        # Confirmar
        total_size = sum(f.stat().st_size for f in files_to_delete if f.exists())
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"Se eliminarán {len(files_to_delete)} archivos "
            f"({format_size(total_size)}).\n\n"
            f"Estrategia: Conservar {self._strategy_name()}\n\n"
            f"¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Guardar plan para ejecución
        self.accepted_plan = {
            'groups': self.filtered_groups,  # Grupos para referencia
            'files_to_delete': files_to_delete,
            'keep_strategy': self.keep_strategy,
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        
        super().accept()
    
    def _strategy_name(self) -> str:
        """Devuelve el nombre legible de la estrategia."""
        names = {
            'largest': 'mejor calidad (más grande)',
            'smallest': 'menor tamaño',
            'oldest': 'más antiguo',
            'newest': 'más reciente'
        }
        return names.get(self.keep_strategy, self.keep_strategy)
