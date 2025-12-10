from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QFrame, QTreeWidget, QTreeWidgetItem, QLineEdit,
    QComboBox, QMessageBox, QMenu, QWidget
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QColor, QShowEvent
from services.result_types import DuplicateGroup
from utils.format_utils import format_size
from utils.logger import get_logger
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from .base_dialog import BaseDialog
from .dialog_utils import show_file_details_dialog
from datetime import datetime


class ExactCopiesDialog(BaseDialog):
    """
    Diálogo para gestionar copias exactas.
    
    Muestra fotos y vídeos idénticos digitalmente (mismo SHA256),
    incluso si tienen nombres diferentes. Permite eliminar duplicados
    con diferentes estrategias de conservación.
    """
    
    # Constantes para paginación
    INITIAL_LOAD = 50
    LOAD_INCREMENT = 50
    WARNING_THRESHOLD = 200
    
    def __init__(self, analysis, parent=None, metadata_cache=None):
        super().__init__(parent)
        self.logger = get_logger('ExactCopiesDialog')
        self.analysis = analysis
        self.metadata_cache = metadata_cache
        self.keep_strategy = 'oldest'
        self.accepted_plan = None
        
        # Estado de grupos
        self.all_groups = analysis.groups  # Todos los grupos originales
        self.filtered_groups = analysis.groups  # Grupos después de filtrar
        self.loaded_count = 0  # Cuántos grupos se han cargado en el tree
        
        # Referencias a widgets (nuevos nombres)
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
        
        self.init_ui()
    
    def _get_modification_time(self, file_path: Path) -> float:
        """
        Obtiene el timestamp de modificación usando metadata_cache si está disponible.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            Timestamp de modificación (epoch seconds)
        """
        if self.metadata_cache:
            dates = self.metadata_cache.get_all_dates(file_path)
            if dates and dates.get('filesystem_modification_date'):
                return dates['filesystem_modification_date'].timestamp()
        
        # Fallback a stat() directo si no hay cache o no se encuentra
        return file_path.stat().st_mtime
    
    def _calculate_recoverable_space(self):
        """Calcula el espacio total recuperable según los grupos filtrados y la estrategia.
        
        El espacio recuperable es la suma de todos los archivos que se eliminarán
        (todos excepto el que se conserva en cada grupo según la estrategia).
        """
        total_recoverable = 0
        
        for group in self.filtered_groups:
            # Determinar qué archivo mantener según estrategia
            if self.keep_strategy == 'oldest':
                keep_file = min(group.files, key=lambda f: self._get_modification_time(f))
            else:  # newest
                keep_file = max(group.files, key=lambda f: self._get_modification_time(f))
            
            # Sumar el tamaño de todos los archivos excepto el que se mantiene
            for file_path in group.files:
                if file_path != keep_file:
                    total_recoverable += file_path.stat().st_size
        
        return total_recoverable
    
    def init_ui(self):
        self.setWindowTitle("Gestionar copias exactas")
        self.setModal(True)
        self.resize(1100, 900)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(int(DesignSystem.SPACE_12))
        layout.setContentsMargins(0, 0, 0, int(DesignSystem.SPACE_20))
        
        # Header compacto integrado con métricas inline
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='content-copy',
            title='Copias exactas detectadas',
            description='Archivos 100% idénticos bit a bit (mismo SHA256), incluso con nombres diferentes. '
                       'Si las fechas o metadatos son diferentes, no se considera idéntico.',
            metrics=[
                {
                    'value': str(self.analysis.total_groups),
                    'label': 'Grupos',
                    'color': DesignSystem.COLOR_PRIMARY
                },
                {
                    'value': str(self.analysis.total_duplicates),
                    'label': 'Copias',
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
        
        # Contenedor con margen para el resto del contenido
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
        
        # Selector de estrategia con cards (debajo del header)
        self.strategy_selector = self._create_strategy_selector()
        content_layout.addWidget(self.strategy_selector)
        
        # Advertencia si hay muchos grupos
        if len(self.all_groups) > self.WARNING_THRESHOLD:
            warning_many = QLabel(
                f"Hay {len(self.all_groups)} grupos de duplicados. "
                f"Se cargarán inicialmente {self.INITIAL_LOAD} grupos. "
                f"Usa la búsqueda y filtros para encontrar grupos específicos más rápido."
            )
            warning_many.setTextFormat(Qt.TextFormat.RichText)
            warning_many.setWordWrap(True)
            warning_many.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                               stop:0 {DesignSystem.COLOR_BG_1}, 
                                               stop:1 {DesignSystem.COLOR_BG_2});
                    border: none;
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_12}px;
                    color: {DesignSystem.COLOR_TEXT_SECONDARY};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                }}
            """)
            content_layout.addWidget(warning_many)
        
        # ========== BARRA DE BÚSQUEDA Y FILTROS ==========
        # Campo de búsqueda elevado con Material Design
        search_card = QFrame()
        search_card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px;
            }}
        """)
        search_card_layout = QVBoxLayout(search_card)
        search_card_layout.setSpacing(int(DesignSystem.SPACE_12))
        search_card_layout.setContentsMargins(0, 0, 0, 0)
        
        # Fila de búsqueda
        search_row = QHBoxLayout()
        search_row.setSpacing(int(DesignSystem.SPACE_12))
        
        # Input de búsqueda con icono interno
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
        search_icon.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        search_container_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre o ruta de archivo...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
                padding: 0px;
            }}
            QLineEdit::placeholder {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """)
        search_container_layout.addWidget(self.search_input, 1)
        
        search_container.setStyleSheet(f"""
            QWidget {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QWidget:focus-within {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
        """)
        
        search_row.addWidget(search_container, 3)
        
        # ComboBox de filtros con estilo Material
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Todos los grupos",
            "Grupos grandes (>10 MB)",
            "Grupos muy grandes (>50 MB)",
            "Grupos enormes (>100 MB)",
            "Muchas copias (3+)",
            "Muchas copias (5+)"
        ])
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.filter_combo.setFixedHeight(int(DesignSystem.SPACE_8 * 5))  # Mismo altura que search_container
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
                min-width: 200px;
            }}
            QComboBox:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {DesignSystem.SPACE_8}px;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
        """)
        self.filter_combo.setToolTip("Filtra grupos por tamaño o cantidad de archivos")
        
        search_row.addWidget(self.filter_combo, 2)
        
        search_card_layout.addLayout(search_row)
        
        # Información de estado con chips Material Design
        status_row = QHBoxLayout()
        status_row.setSpacing(int(DesignSystem.SPACE_8))
        
        # Chip de grupos cargados
        self.loaded_chip = QLabel()
        self.loaded_chip.setStyleSheet(f"""
            QLabel {{
                background-color: {DesignSystem.COLOR_INFO};
                color: {DesignSystem.COLOR_SURFACE};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
        """)
        status_row.addWidget(self.loaded_chip)
        
        # Chip de grupos filtrados (solo visible cuando hay filtros)
        self.filtered_chip = QLabel()
        self.filtered_chip.setStyleSheet(f"""
            QLabel {{
                background-color: {DesignSystem.COLOR_WARNING};
                color: {DesignSystem.COLOR_SURFACE};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
        """)
        self.filtered_chip.hide()  # Oculto por defecto
        status_row.addWidget(self.filtered_chip)
        
        status_row.addStretch()
        
        # Botón para cargar todos (solo visible cuando hay más grupos)
        self.load_all_btn = QPushButton()
        icon_manager.set_button_icon(self.load_all_btn, 'download', size=16)
        self.load_all_btn.clicked.connect(self._load_all_groups)
        self.load_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {DesignSystem.COLOR_PRIMARY};
                border: 2px solid {DesignSystem.COLOR_PRIMARY};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
        """)
        self.load_all_btn.hide()  # Oculto hasta que se sepa si hay más grupos
        status_row.addWidget(self.load_all_btn)
        
        search_card_layout.addLayout(status_row)
        
        content_layout.addWidget(search_card)
        
        # ========== ÁRBOL DE GRUPOS ==========
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Grupos / Archivos", "Tamaño", "Fecha", "Ubicación", "Estado"])
        self.tree_widget.setColumnWidth(0, 300)  # Ajustado para grupos más simples
        self.tree_widget.setColumnWidth(1, 120)
        self.tree_widget.setColumnWidth(2, 140)  # Más espacio para fecha completa
        self.tree_widget.setColumnWidth(3, 200)  # Más espacio para ubicación
        self.tree_widget.setColumnWidth(4, 130)
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.setRootIsDecorated(True)
        self.tree_widget.setAnimated(True)
        self.tree_widget.setIndentation(20)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                outline: none;
                background-color: {DesignSystem.COLOR_SURFACE};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px;
            }}
            QTreeWidget::item {{
                border: none;
                outline: none;
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
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
        """)
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)
        content_layout.addWidget(self.tree_widget)
        
        # ========== PAGINACIÓN INTELIGENTE ==========
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
        
        # Indicador de progreso visual
        self.progress_indicator = QLabel()
        self.progress_indicator.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                background-color: transparent;
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
            }}
        """)
        self.progress_indicator.setToolTip("Porcentaje de grupos cargados en la lista")
        pagination_layout.addWidget(self.progress_indicator)
        
        # Barra de progreso visual
        self.progress_bar_container = QFrame()
        self.progress_bar_container.setFixedHeight(8)
        self.progress_bar_container.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BORDER};
                border-radius: 4px;
            }}
        """)
        self.progress_bar_container.setToolTip(
            "Progreso de carga: muestra cuántos grupos de los filtrados se han cargado en la lista. "
            "Si cambias filtros, el progreso se reinicia para los nuevos resultados."
        )
        
        # Barra de progreso interna
        self.progress_bar_fill = QFrame(self.progress_bar_container)
        self.progress_bar_fill.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                border-radius: 4px;
            }}
        """)
        self.progress_bar_fill.setGeometry(0, 0, 0, 8)
        
        pagination_layout.addWidget(self.progress_bar_container, 1)
        
        # Botón para cargar más grupos
        self.load_more_btn = QPushButton()
        icon_manager.set_button_icon(self.load_more_btn, 'refresh', size=18)
        self.load_more_btn.clicked.connect(self._load_more_groups)
        self.load_more_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_10}px {DesignSystem.SPACE_20}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                min-width: 160px;
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SURFACE_DISABLED};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """)
        pagination_layout.addWidget(self.load_more_btn)
        
        content_layout.addWidget(pagination_card)
        
        # Cargar grupos iniciales
        self._load_initial_groups()
        
        # Opciones de seguridad (método centralizado)
        security_options = self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de eliminar",
            dry_run_label="Modo simulación (no eliminar archivos realmente)"
        )
        content_layout.addWidget(security_options)

        # Botones con estilo Material Design
        buttons = self.make_ok_cancel_buttons(
            ok_text="Eliminar Ahora",
            button_style='danger'
        )
        content_layout.addWidget(buttons)
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())
    
    def _create_strategy_selector(self) -> QFrame:
        """Crea selector de estrategia usando el método centralizado de BaseDialog."""
        strategies = [
            ('oldest', 'clock-outline', 'Mantener el más antiguo', 
             'Conserva el archivo con fecha de modificación más antigua. Recomendado para preservar originales.'),
            ('newest', 'update', 'Mantener el más reciente', 
             'Conserva el archivo con fecha de modificación más reciente. Útil para versiones editadas.')
        ]
        
        return self._create_option_selector(
            title="Elige qué archivo conservar en cada grupo",
            title_icon='ruler',
            options=strategies,
            selected_value=self.keep_strategy,
            on_change_callback=self._on_strategy_changed
        )
    
    def _on_strategy_changed(self, new_strategy: str) -> None:
        """Maneja el cambio de estrategia de eliminación.
        
        Args:
            new_strategy: Nueva estrategia seleccionada ('oldest', 'newest')
        """
        if new_strategy == self.keep_strategy:
            return
        
        self.logger.info(f"Cambiando estrategia de eliminación: {self.keep_strategy} -> {new_strategy}")
        self.keep_strategy = new_strategy
        
        # Actualizar estilos de las cards usando el método centralizado
        if hasattr(self, 'strategy_selector'):
            self._update_option_selector_styles(
                self.strategy_selector,
                ['oldest', 'newest'],
                self.keep_strategy
            )
        
        # Actualizar métrica de espacio recuperable en el header
        recoverable_space = self._calculate_recoverable_space()
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(recoverable_space))
        
        # Actualizar estado de archivos en el tree
        self._update_status_labels()
    
    def _load_initial_groups(self):
        """Carga los primeros grupos según INITIAL_LOAD"""
        self.loaded_count = 0
        self._load_groups_batch(self.INITIAL_LOAD)
    
    def _load_more_groups(self):
        """Carga el siguiente lote de grupos"""
        self._load_groups_batch(self.LOAD_INCREMENT)
    
    def _load_all_groups(self):
        """Carga todos los grupos restantes"""
        remaining = len(self.filtered_groups) - self.loaded_count
        if remaining > 100:
            reply = QMessageBox.question(
                self,
                "Cargar Todos",
                f"Esto cargará {remaining} grupos más. Puede tardar un momento. ¿Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self._load_groups_batch(remaining)
    
    def _load_groups_batch(self, count: int):
        """Carga un lote de grupos en el tree widget y actualiza la UI"""
        start_idx = self.loaded_count
        end_idx = min(start_idx + count, len(self.filtered_groups))
        
        for i in range(start_idx, end_idx):
            group = self.filtered_groups[i]
            self._add_group_to_tree(group, i + 1)
        
        self.loaded_count = end_idx
        self._update_pagination_ui()
    
    def _update_pagination_ui(self):
        """Actualiza todos los elementos de la UI de paginación"""
        total_filtered = len(self.filtered_groups)
        total_original = len(self.all_groups)
        
        # Actualizar chips de estado
        self.loaded_chip.setText(f"📊 Mostrando {self.loaded_count} de {total_filtered}")
        
        # Mostrar chip de filtrado si hay filtros activos
        if total_filtered < total_original:
            self.filtered_chip.setText(f"🔍 {total_original - total_filtered} grupos ocultos")
            self.filtered_chip.show()
        else:
            self.filtered_chip.hide()
        
        # Actualizar barra de progreso
        if total_filtered > 0:
            progress_percent = (self.loaded_count / total_filtered) * 100
            bar_width = int((self.progress_bar_container.width() * progress_percent) / 100)
            self.progress_bar_fill.setFixedWidth(bar_width)
            
            # Actualizar indicador de progreso
            self.progress_indicator.setText(f"{int(progress_percent)}%")
        else:
            # No hay grupos filtrados - resetear barra de progreso
            self.progress_bar_fill.setFixedWidth(0)
            self.progress_indicator.setText("0%")
        
        # Actualizar botón "Cargar Más"
        remaining = total_filtered - self.loaded_count
        
        if remaining <= 0:
            # Ya se cargaron todos
            self.load_more_btn.setEnabled(False)
            self.load_more_btn.setText("✓ Todos cargados")
            icon_manager.set_button_icon(self.load_more_btn, 'check-circle', size=18)
            self.load_more_btn.setToolTip("Todos los grupos están cargados")
        else:
            # Aún hay más grupos por cargar
            self.load_more_btn.setEnabled(True)
            to_load = min(self.LOAD_INCREMENT, remaining)
            self.load_more_btn.setText(f"Cargar {to_load} más")
            icon_manager.set_button_icon(self.load_more_btn, 'refresh', size=18)
            self.load_more_btn.setToolTip(f"Cargar los siguientes {to_load} grupos ({remaining} pendientes)")
        
        # Mostrar/ocultar botón "Cargar Todos"
        if remaining > self.LOAD_INCREMENT:
            self.load_all_btn.setText(f"Cargar todos ({remaining})")
            self.load_all_btn.setToolTip(f"Cargar los {remaining} grupos restantes de una vez")
            self.load_all_btn.show()
        else:
            self.load_all_btn.hide()
    
    def _add_group_to_tree(self, group: DuplicateGroup, group_number: int):
        """Añade un grupo como nodo padre expandible en el tree con estilo Material Design"""
        # Nodo padre del grupo
        group_item = QTreeWidgetItem(self.tree_widget)
        file_count = len(group.files)
        
        # Calcular espacio a liberar (total - archivo que se mantendrá)
        if self.keep_strategy == 'oldest':
            keep_file = min(group.files, key=lambda f: self._get_modification_time(f))
        else:  # newest
            keep_file = max(group.files, key=lambda f: self._get_modification_time(f))
        
        keep_file_size = keep_file.stat().st_size
        space_to_free = group.total_size - keep_file_size
        
        # Textos del grupo - Solo mostrar info básica en columna 0
        group_item.setText(0, f"Grupo #{group_number} • {file_count} copias")
        # Las otras columnas quedan vacías para grupos - solo se usan para archivos
        
        # Estilo del grupo padre estándar (Bold + Blue + BASE size)
        font = group_item.font(0)
        font.setBold(True)
        font.setPointSize(int(DesignSystem.FONT_SIZE_XS))
        group_item.setFont(0, font)
        group_item.setForeground(0, QColor(DesignSystem.COLOR_PRIMARY))
        
        # Tooltip informativo sobre doble click
        group_item.setToolTip(0, f"Grupo #{group_number} con {file_count} archivos idénticos\n"
                                 f"▶ 💡 Doble clic para expandir y ver detalles de archivos\n"
                                 f"💡 Las columnas muestran información de cada archivo individual")
        
        # Color de fondo sutil Material Design
        group_item.setBackground(0, QColor(DesignSystem.COLOR_BG_1))
        group_item.setBackground(1, QColor(DesignSystem.COLOR_BG_1))
        group_item.setBackground(2, QColor(DesignSystem.COLOR_BG_1))
        group_item.setBackground(3, QColor(DesignSystem.COLOR_BG_1))
        group_item.setBackground(4, QColor(DesignSystem.COLOR_BG_1))
        
        # Color del texto de la columna de espacio recuperable
        group_item.setForeground(4, QColor(DesignSystem.COLOR_SUCCESS))
        font_space = group_item.font(4)
        font_space.setBold(True)
        group_item.setFont(4, font_space)
        
        # Añadir archivos como hijos
        for file_path in group.files:
            file_item = QTreeWidgetItem(group_item)
            
            # Determinar si este archivo se mantiene o se elimina
            is_keep = file_path == keep_file
            
            # Icono según tipo de archivo (con color diferenciado)
            ext = file_path.suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                icon_name = "image"
            elif ext in ['.mov', '.mp4', '.avi', '.mkv']:
                icon_name = "video"
            elif ext in ['.heic', '.heif']:
                icon_name = "camera"
            else:
                icon_name = "file"
            
            file_item.setIcon(0, icon_manager.get_icon(icon_name, size=18))
            file_item.setText(0, file_path.name)
            file_item.setText(1, format_size(file_path.stat().st_size))
            
            # Fecha de modificación con formato mejorado
            mtime = datetime.fromtimestamp(self._get_modification_time(file_path))
            file_item.setText(2, mtime.strftime('%d/%m/%Y %H:%M'))
            
            # Ruta del directorio padre
            path_str = str(file_path.parent)
            file_item.setText(3, path_str)
            
            # Estado: mantener o eliminar con iconos y colores Material Design
            if is_keep:
                file_item.setText(4, "✓ Mantener")
                file_item.setForeground(4, QColor(DesignSystem.COLOR_SUCCESS))
                
                # Resaltar archivo que se mantiene con fondo sutil
                for col in range(5):
                    file_item.setBackground(col, QColor(f"{DesignSystem.COLOR_SUCCESS}15"))  # 15 = alpha hex
                
                font_keep = file_item.font(4)
                font_keep.setBold(True)
                file_item.setFont(4, font_keep)
            else:
                file_item.setText(4, "✗ Eliminar")
                file_item.setForeground(4, QColor(DesignSystem.COLOR_ERROR))
            
            # Guardar referencia al archivo en el item
            file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            
            # Tooltips informativos
            tooltip_text = (
                f"<b>{file_path.name}</b><br>"
                f"📂 {file_path.parent}<br>"
                f"📊 {format_size(file_path.stat().st_size)}<br>"
                f"📅 {mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>"
                f"{'✓ Se conservará' if is_keep else '✗ Se eliminará'}"
            )
            file_item.setToolTip(0, tooltip_text)
            file_item.setToolTip(1, tooltip_text)
            file_item.setToolTip(2, tooltip_text)
            file_item.setToolTip(3, f"Ruta completa: {file_path}")
            file_item.setToolTip(4, tooltip_text)
    
    def _update_status_labels(self):
        """Actualiza las etiquetas de estado según la estrategia seleccionada con estilo Material Design"""
        # Recorrer todos los grupos cargados y actualizar el estado
        for i in range(self.tree_widget.topLevelItemCount()):
            group_item = self.tree_widget.topLevelItem(i)
            
            # Obtener archivos del grupo
            files = []
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                filepath = child.data(0, Qt.ItemDataRole.UserRole)
                if filepath:
                    files.append(filepath)
            
            if not files:
                continue
            
            # Determinar archivo a mantener según estrategia
            if self.keep_strategy == 'oldest':
                keep_file = min(files, key=lambda f: self._get_modification_time(f))
            elif self.keep_strategy == 'newest':
                keep_file = max(files, key=lambda f: self._get_modification_time(f))
            else:
                keep_file = files[0]  # Fallback
            
            # Actualizar estado de cada archivo hijo con colores Material Design
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                filepath = child.data(0, Qt.ItemDataRole.UserRole)
                
                if filepath == keep_file:
                    child.setText(4, "✓ Mantener")
                    child.setForeground(4, QColor(DesignSystem.COLOR_SUCCESS))
                    
                    # Resaltar archivo que se mantiene
                    for col in range(5):
                        child.setBackground(col, QColor(f"{DesignSystem.COLOR_SUCCESS}15"))
                    
                    font_keep = child.font(4)
                    font_keep.setBold(True)
                    child.setFont(4, font_keep)
                else:
                    child.setText(4, "✗ Eliminar")
                    child.setForeground(4, QColor(DesignSystem.COLOR_ERROR))
                    
                    # Limpiar fondo resaltado
                    for col in range(5):
                        child.setBackground(col, QColor("transparent"))
                    
                    font_del = child.font(4)
                    font_del.setBold(False)
                    child.setFont(4, font_del)
    
    def _on_search_changed(self):
        """Maneja cambios en la búsqueda"""
        search_text = self.search_input.text().strip().lower()
        self._apply_filters(search_text)
    
    def _on_filter_changed(self):
        """Maneja cambios en el filtro de tamaño/cantidad"""
        search_text = self.search_input.text().strip().lower()
        self._apply_filters(search_text)
    
    def _apply_filters(self, search_text: str = ""):
        """Aplica búsqueda y filtros a los grupos"""
        filtered = self.all_groups
        
        # Aplicar búsqueda por texto
        if search_text:
            filtered = [
                group for group in filtered
                if any(search_text in str(f).lower() for f in group.files)
            ]
        
        # Aplicar filtro de combo
        filter_idx = self.filter_combo.currentIndex()
        if filter_idx == 1:  # >10 MB
            filtered = [g for g in filtered if g.total_size > 10 * 1024 * 1024]
        elif filter_idx == 2:  # >50 MB
            filtered = [g for g in filtered if g.total_size > 50 * 1024 * 1024]
        elif filter_idx == 3:  # >100 MB
            filtered = [g for g in filtered if g.total_size > 100 * 1024 * 1024]
        elif filter_idx == 4:  # 3+ archivos
            filtered = [g for g in filtered if len(g.files) >= 3]
        elif filter_idx == 5:  # 5+ archivos
            filtered = [g for g in filtered if len(g.files) >= 5]
        
        # Actualizar grupos filtrados y recargar
        self.filtered_groups = filtered
        self.tree_widget.clear()
        self.loaded_count = 0
        
        # Actualizar métrica de espacio recuperable en el header
        recoverable_space = self._calculate_recoverable_space()
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(recoverable_space))
        
        if len(self.filtered_groups) == 0:
            # No hay resultados - mostrar mensaje en chips
            self.loaded_chip.setText("⚠️ Sin resultados")
            self.loaded_chip.setStyleSheet(f"""
                QLabel {{
                    background-color: {DesignSystem.COLOR_WARNING};
                    color: {DesignSystem.COLOR_SURFACE};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_12}px;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
            """)
            self.load_more_btn.setEnabled(False)
            self.load_all_btn.hide()
            # Actualizar UI de paginación para mostrar progreso en 0%
            self._update_pagination_ui()
        else:
            # Restaurar estilo normal del chip
            self.loaded_chip.setStyleSheet(f"""
                QLabel {{
                    background-color: {DesignSystem.COLOR_INFO};
                    color: {DesignSystem.COLOR_SURFACE};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_12}px;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
            """)
            # Cargar primeros grupos
            self._load_initial_groups()
    
    def _on_item_double_clicked(self, item, column):
        """Maneja doble click en un item del tree"""
        # Obtener el archivo asociado al item
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if file_path and isinstance(file_path, Path):
            # Es un archivo, abrirlo
            self._open_file(file_path)
        else:
            # Es un grupo, expandir/colapsar
            item.setExpanded(not item.isExpanded())
    
    def _show_context_menu(self, position):
        """Muestra el menú contextual para un archivo con estilo Material Design"""
        from .dialog_utils import open_file, open_folder
        
        item = self.tree_widget.itemAt(position)
        if not item:
            return
        
        # Obtener el archivo asociado al item
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not isinstance(file_path, Path):
            return  # Es un grupo padre, no mostrar menú
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_16}px;
                border-radius: {DesignSystem.RADIUS_SMALL}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
            QMenu::item:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {DesignSystem.COLOR_BORDER};
                margin: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
            }}
        """)
        
        # Acción: Abrir archivo
        open_action = menu.addAction("Abrir archivo")
        open_action.triggered.connect(lambda: open_file(file_path, self))
        
        # Acción: Abrir carpeta
        open_folder_action = menu.addAction("Abrir carpeta contenedora")
        open_folder_action.triggered.connect(lambda: open_folder(file_path.parent, self))
        
        menu.addSeparator()
        
        # Acción: Ver detalles
        details_action = menu.addAction("Ver detalles del archivo")
        details_action.triggered.connect(lambda: self._show_file_details(file_path))
        
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))
    
    def _show_file_details(self, file_path: Path):
        """Muestra diálogo con detalles del archivo"""
        # Determinar el estado del archivo (mantener/eliminar)
        # Buscar en qué grupo está este archivo
        status_info = None
        for group in self.filtered_groups:
            if file_path in group.files:
                # Determinar qué archivo se mantiene
                if self.keep_strategy == 'oldest':
                    keep_file = min(group.files, key=lambda f: self._get_modification_time(f))
                else:
                    keep_file = max(group.files, key=lambda f: self._get_modification_time(f))
                
                is_keep = file_path == keep_file
                status_info = {
                    'metadata': {
                        'Estado': 'Se mantendrá' if is_keep else 'Se eliminará',
                        'Grupo': f'{len(group.files)} archivos duplicados',
                        'Espacio grupo': format_size(group.total_size),
                        'Estrategia': 'Mantener más antiguo' if self.keep_strategy == 'oldest' else 'Mantener más reciente'
                    }
                }
                break
        
        show_file_details_dialog(file_path, self, status_info)
    
    def _open_file(self, file_path: Path):
        """Abre un archivo con la aplicación predeterminada del sistema"""
        if file_path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
        else:
            QMessageBox.warning(
                self,
                "Archivo no encontrado",
                f"No se encontró el archivo:\n{file_path}"
            )
    


    def showEvent(self, event: QShowEvent):
        """Actualizar la barra de progreso cuando el diálogo se muestre completamente"""
        super().showEvent(event)
        # Actualizar la barra de progreso ahora que el layout está procesado
        self._update_pagination_ui()
    
    def accept(self):
        self.accepted_plan = {
            'groups': self.analysis.groups,
            'keep_strategy': self.keep_strategy,
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        super().accept()
