"""
Diálogo de eliminación de duplicados HEIC/JPG - Rediseñado
Grupos expandibles con archivos HEIC y JPG individuales, diseño Material Design
"""
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QDialogButtonBox, 
    QLabel, QTreeWidget, QTreeWidgetItem, QLineEdit, QComboBox, QPushButton,
    QFrame, QApplication, QWidget, QMenu
)
from PyQt6.QtGui import QColor, QFont, QCursor
from PyQt6.QtCore import Qt, QTimer
from config import Config
from utils.format_utils import format_size
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from .base_dialog import BaseDialog


class HEICDuplicateRemovalDialog(BaseDialog):
    """Diálogo para eliminación de duplicados HEIC/JPG con vista de grupos expandibles"""
    
    # Configuración de paginación
    ITEMS_PER_PAGE = 200
    MAX_ITEMS_WITHOUT_PAGINATION = 500

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.selected_format = 'jpg'
        self.accepted_plan = None
        
        # Datos filtrados
        self.filtered_pairs = list(analysis.duplicate_pairs)
        
        # Paginación
        self.current_page = 0
        self.total_pages = 0
        
        # Referencias a widgets
        self.tree_widget = None
        self.search_input = None
        self.dir_combo = None
        self.counter_label = None
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Limpieza de Duplicados HEIC/JPG")
        self.setModal(True)
        self.resize(1200, 800)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(int(DesignSystem.SPACE_12))
        main_layout.setContentsMargins(0, 0, 0, int(DesignSystem.SPACE_20))
        
        # Header compacto integrado con métricas inline
        initial_recoverable = self.analysis.potential_savings_keep_jpg if self.selected_format == 'jpg' else self.analysis.potential_savings_keep_heic
        
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='photo-library',
            title='Duplicados HEIC/JPG detectados',
            description='Fotos HEIC con versiones JPG idénticas. Elige qué formato conservar y libera espacio.',
            metrics=[
                {
                    'value': str(self.analysis.total_pairs),
                    'label': 'Grupos',
                    'color': DesignSystem.COLOR_PRIMARY
                },
                {
                    'value': format_size(initial_recoverable),
                    'label': 'Recuperable',
                    'color': DesignSystem.COLOR_SUCCESS
                }
            ]
        )
        main_layout.addWidget(self.header_frame)
        
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
        main_layout.addWidget(content_container)
        
        # Selector de formato con cards
        self.format_selector = self._create_format_selector()
        content_layout.addWidget(self.format_selector)
        
        # Barra de herramientas (filtros y búsqueda)
        toolbar = self._create_toolbar()
        content_layout.addLayout(toolbar)
        
        # TreeWidget de grupos expandibles
        self.tree_widget = self._create_files_tree()
        content_layout.addWidget(self.tree_widget)
        
        # Controles de paginación
        self.pagination_widget = self._create_pagination_controls()
        content_layout.addWidget(self.pagination_widget)
        
        # Opciones de seguridad
        options_group = self._create_options_group()
        content_layout.addWidget(options_group)
        
        # Botones con estilo Material Design
        ok_enabled = self.analysis.total_pairs > 0
        self.buttons = self.make_ok_cancel_buttons(
            ok_enabled=ok_enabled,
            button_style='danger'
        )
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_enabled:
            self._update_button_text()
        content_layout.addWidget(self.buttons)
        
        # Actualizar vista inicial
        self._update_tree()
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())

    def _create_format_selector(self) -> QFrame:
        """Crea selector de formato usando el método centralizado de BaseDialog."""
        formats = [
            ('jpg', 'image', 'Mantener JPG', 
             f'Máxima compatibilidad. Los JPG funcionan en todos los dispositivos. Liberarás {format_size(self.analysis.potential_savings_keep_jpg)}'),
            ('heic', 'camera', 'Mantener HEIC', 
             f'Archivos más pequeños pero requiere soporte HEIC. Liberarás {format_size(self.analysis.potential_savings_keep_heic)}')
        ]
        
        return self._create_option_selector(
            title="Elige qué formato conservar",
            title_icon='photo-library',
            options=formats,
            selected_value=self.selected_format,
            on_change_callback=self._on_format_card_changed
        )
    
    def _on_format_card_changed(self, new_format: str) -> None:
        """Maneja el cambio de formato seleccionado desde las cards.
        
        Args:
            new_format: Nuevo formato seleccionado ('jpg' o 'heic')
        """
        if new_format == self.selected_format:
            return
        
        self.selected_format = new_format
        
        # Actualizar estilos de las cards usando el método centralizado
        if hasattr(self, 'format_selector'):
            self._update_option_selector_styles(
                self.format_selector,
                ['jpg', 'heic'],
                self.selected_format
            )
        
        # Actualizar métrica de espacio recuperable en el header
        recoverable_space = self.analysis.potential_savings_keep_jpg if new_format == 'jpg' else self.analysis.potential_savings_keep_heic
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(recoverable_space))
        
        # Actualizar texto del botón OK
        self._update_button_text()
        
        # Actualizar tree
        self._update_tree()
    
    def _create_toolbar(self):
        """Crea barra de herramientas con filtros estilo Material Design"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(int(DesignSystem.SPACE_12))
        
        # Búsqueda
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        
        search_icon = QLabel()
        icon_manager.set_label_icon(search_icon, 'search', size=14)
        search_layout.addWidget(search_icon)
        
        search_text = QLabel("Buscar:")
        search_layout.addWidget(search_text)
        
        toolbar.addWidget(search_container)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nombre de archivo...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: {DesignSystem.SPACE_8}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QLineEdit:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        self.search_input.setToolTip("Buscar grupos por nombre de archivo base")
        toolbar.addWidget(self.search_input, 2)
        
        # Separador visual
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.VLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        separator_line.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER};")
        toolbar.addWidget(separator_line)
        
        # Filtro por directorio
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(4)
        
        filter_icon = QLabel()
        icon_manager.set_label_icon(filter_icon, 'folder-outline', size=14)
        filter_layout.addWidget(filter_icon)
        
        filter_text = QLabel("Directorio:")
        filter_layout.addWidget(filter_text)
        
        toolbar.addWidget(filter_container)
        
        # Contenedor para combobox con icono
        combo_container = QWidget()
        combo_layout = QHBoxLayout(combo_container)
        combo_layout.setContentsMargins(0, 0, 0, 0)
        combo_layout.setSpacing(0)
        
        self.dir_combo = QComboBox()
        directories = ["Todos"] + sorted(list(set(
            str(pair.directory) for pair in self.analysis.duplicate_pairs
        )))
        self.dir_combo.addItems(directories)
        self.dir_combo.currentTextChanged.connect(self._apply_filters)
        self.dir_combo.setStyleSheet(DesignSystem.get_combobox_style())
        self.dir_combo.setToolTip("Filtrar grupos por directorio")
        combo_layout.addWidget(self.dir_combo, 1)
        
        # Icono chevron-down
        chevron_icon = QLabel()
        icon_manager.set_label_icon(chevron_icon, 'chevron-down', size=14)
        chevron_icon.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY}; 
            padding-left: {DesignSystem.SPACE_4}px;
            background-color: transparent;
        """)
        combo_layout.addWidget(chevron_icon)
        
        toolbar.addWidget(combo_container, 1)
        
        # Separador visual
        separator_line2 = QFrame()
        separator_line2.setFrameShape(QFrame.Shape.VLine)
        separator_line2.setFrameShadow(QFrame.Shadow.Sunken)
        separator_line2.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER};")
        toolbar.addWidget(separator_line2)
        
        # Botón limpiar filtros
        clear_btn = QPushButton("Limpiar")
        icon_manager.set_button_icon(clear_btn, 'delete-sweep', size=16)
        clear_btn.clicked.connect(self._clear_filters)
        clear_btn.setToolTip("Limpiar todos los filtros")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
        """)
        toolbar.addWidget(clear_btn)
        
        # Contador de grupos con estilo mejorado
        self.counter_label = QLabel()
        self.counter_label.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            padding: {DesignSystem.SPACE_6}px;
        """)
        toolbar.addWidget(self.counter_label)
        
        toolbar.addStretch()
        return toolbar
    
    def _create_files_tree(self):
        """Crea TreeWidget con grupos expandibles estilo Material Design"""
        tree = QTreeWidget()
        tree.setHeaderLabels(["Grupos / Archivos", "Tamaño", "Tipo", "Estado"])
        tree.setColumnWidth(0, 350)
        tree.setColumnWidth(1, 120)
        tree.setColumnWidth(2, 100)
        tree.setColumnWidth(3, 150)
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(True)
        tree.setAnimated(True)
        tree.setIndentation(20)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                background-color: {DesignSystem.COLOR_SURFACE};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_4}px;
                border: none;
                min-height: 28px;
            }}
            QTreeWidget::item:hover {{
                background-color: {DesignSystem.COLOR_BG_1};
            }}
            QTreeWidget::item:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
            }}
            QTreeWidget::item:selected:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QHeaderView::section {{
                background-color: {DesignSystem.COLOR_BG_1};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                border: none;
                border-bottom: 2px solid {DesignSystem.COLOR_BORDER};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QHeaderView {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: none;
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER};
            }}
            QTreeWidget::branch {{
                background: transparent;
            }}
        """)
        tree.itemExpanded.connect(self._on_item_expanded)
        tree.itemCollapsed.connect(self._on_item_collapsed)
        tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        tree.customContextMenuRequested.connect(self._show_context_menu)
        
        return tree
    
    def _create_pagination_controls(self):
        """Crea controles de paginación con estilo Material Design"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.StyledPanel)
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BG_1};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px;
            }}
        """)
        layout = QHBoxLayout(widget)
        layout.setSpacing(int(DesignSystem.SPACE_8))
        
        # Estilo común para botones de paginación
        pagination_button_style = f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_BORDER};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """
        
        self.first_page_btn = QPushButton("Primera")
        icon_manager.set_button_icon(self.first_page_btn, 'skip-previous', size=16)
        self.first_page_btn.clicked.connect(self._go_first_page)
        self.first_page_btn.setMaximumWidth(100)
        self.first_page_btn.setStyleSheet(pagination_button_style)
        layout.addWidget(self.first_page_btn)
        
        self.prev_page_btn = QPushButton("Anterior")
        icon_manager.set_button_icon(self.prev_page_btn, 'chevron-left', size=16)
        self.prev_page_btn.clicked.connect(self._go_prev_page)
        self.prev_page_btn.setMaximumWidth(100)
        self.prev_page_btn.setStyleSheet(pagination_button_style)
        layout.addWidget(self.prev_page_btn)
        
        self.page_label = QLabel()
        self.page_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
            padding: 0 {DesignSystem.SPACE_20}px;
        """)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)
        
        self.next_page_btn = QPushButton("Siguiente")
        icon_manager.set_button_icon(self.next_page_btn, 'chevron-right', size=16)
        self.next_page_btn.clicked.connect(self._go_next_page)
        self.next_page_btn.setMaximumWidth(100)
        self.next_page_btn.setStyleSheet(pagination_button_style)
        layout.addWidget(self.next_page_btn)
        
        self.last_page_btn = QPushButton("Última")
        icon_manager.set_button_icon(self.last_page_btn, 'skip-next', size=16)
        self.last_page_btn.clicked.connect(self._go_last_page)
        self.last_page_btn.setMaximumWidth(100)
        self.last_page_btn.setStyleSheet(pagination_button_style)
        layout.addWidget(self.last_page_btn)
        
        layout.addStretch()
        
        # Label para "Items por página"
        items_label = QLabel("Items por página:")
        items_label.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        layout.addWidget(items_label)
        
        # Contenedor para combobox de paginación con icono
        pagination_combo_container = QWidget()
        pagination_combo_layout = QHBoxLayout(pagination_combo_container)
        pagination_combo_layout.setContentsMargins(0, 0, 0, 0)
        pagination_combo_layout.setSpacing(0)
        
        self.items_per_page_combo = QComboBox()
        self.items_per_page_combo.addItems(["100", "200", "500", "Todos"])
        self.items_per_page_combo.setCurrentText("200")
        self.items_per_page_combo.currentTextChanged.connect(self._change_items_per_page)
        self.items_per_page_combo.setMaximumWidth(100)
        self.items_per_page_combo.setStyleSheet(DesignSystem.get_combobox_style())
        pagination_combo_layout.addWidget(self.items_per_page_combo)
        
        # Icono chevron-down para paginación
        pagination_chevron = QLabel()
        icon_manager.set_label_icon(pagination_chevron, 'chevron-down', size=12)
        pagination_chevron.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY}; 
            padding-left: {DesignSystem.SPACE_2}px;
            background-color: transparent;
        """)
        pagination_combo_layout.addWidget(pagination_chevron)
        
        layout.addWidget(pagination_combo_container)
        
        widget.setVisible(False)
        return widget
    
    def _create_options_group(self):
        """Crea grupo de opciones de seguridad usando método centralizado"""
        return self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de eliminar",
            dry_run_label="Modo simulación (no eliminar realmente)"
        )
    
    def _apply_filters(self):
        """Aplica filtros a la lista de grupos"""
        search_text = self.search_input.text().lower()
        dir_filter = self.dir_combo.currentText()
        
        self.filtered_pairs = []
        
        for pair in self.analysis.duplicate_pairs:
            # Filtro de búsqueda
            if search_text and search_text not in pair.base_name.lower():
                continue
            
            # Filtro por directorio
            if dir_filter != "Todos" and str(pair.directory) != dir_filter:
                continue
            
            self.filtered_pairs.append(pair)
        
        self.current_page = 0
        self._update_tree()
    
    def _clear_filters(self):
        """Limpia todos los filtros"""
        self.search_input.clear()
        self.dir_combo.setCurrentIndex(0)
    
    def _go_first_page(self):
        self.current_page = 0
        QTimer.singleShot(0, self._update_tree)
    
    def _go_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            QTimer.singleShot(0, self._update_tree)
    
    def _go_next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            QTimer.singleShot(0, self._update_tree)
    
    def _go_last_page(self):
        self.current_page = max(0, self.total_pages - 1)
        QTimer.singleShot(0, self._update_tree)
    
    def _change_items_per_page(self, text):
        if text == "Todos":
            self.ITEMS_PER_PAGE = len(self.filtered_pairs)
        else:
            self.ITEMS_PER_PAGE = int(text)
        self.current_page = 0
        QTimer.singleShot(0, self._update_tree)
    
    def _update_tree(self):
        """Actualiza el TreeWidget con grupos expandibles"""
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        
        try:
            total_filtered = len(self.filtered_pairs)
            use_pagination = total_filtered > self.MAX_ITEMS_WITHOUT_PAGINATION
            
            if use_pagination:
                self.total_pages = (total_filtered + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
                start_idx = self.current_page * self.ITEMS_PER_PAGE
                end_idx = min(start_idx + self.ITEMS_PER_PAGE, total_filtered)
                items_to_show = self.filtered_pairs[start_idx:end_idx]
                
                self.pagination_widget.setVisible(True)
                self.page_label.setText(
                    f"Página {self.current_page + 1} de {self.total_pages} "
                    f"(mostrando {start_idx + 1}-{end_idx} de {total_filtered})"
                )
                
                self.first_page_btn.setEnabled(self.current_page > 0)
                self.prev_page_btn.setEnabled(self.current_page > 0)
                self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
                self.last_page_btn.setEnabled(self.current_page < self.total_pages - 1)
            else:
                items_to_show = self.filtered_pairs
                self.pagination_widget.setVisible(False)
            
            # Limpiar tree
            self.tree_widget.clear()
            
            # Determinar qué se conservará y eliminará según formato seleccionado
            format_to_keep = "JPG" if self.selected_format == 'jpg' else "HEIC"
            format_to_delete = "HEIC" if self.selected_format == 'jpg' else "JPG"
            
            # Añadir grupos
            for group_number, pair in enumerate(items_to_show, start=1):
                self._add_group_to_tree(pair, group_number, format_to_keep, format_to_delete)
                
                # Procesar eventos cada 20 grupos
                if group_number % 20 == 0:
                    QApplication.processEvents()
            
            # Actualizar contador
            total = len(self.analysis.duplicate_pairs)
            if use_pagination:
                self.counter_label.setText(
                    f"Mostrando {len(items_to_show)} de {total_filtered} grupos filtrados ({total} total)"
                )
            else:
                if total_filtered == total:
                    self.counter_label.setText(f"Mostrando {total_filtered} grupos")
                else:
                    self.counter_label.setText(f"Mostrando {total_filtered} de {total} grupos")
        
        finally:
            QApplication.restoreOverrideCursor()
    
    def _add_group_to_tree(self, pair, group_number, format_to_keep, format_to_delete):
        """Añade un grupo como nodo padre expandible con archivos HEIC y JPG"""
        # Nodo padre del grupo
        group_item = QTreeWidgetItem(self.tree_widget)
        
        # Texto del grupo - Solo columna 0
        group_item.setText(0, f"▶ Grupo #{group_number} • {pair.base_name}")
        
        # Estilo del grupo padre más sutil
        font = group_item.font(0)
        font.setBold(False)
        font.setPointSize(int(DesignSystem.FONT_SIZE_SM))
        group_item.setFont(0, font)
        
        # Tooltip informativo
        group_item.setToolTip(0, f"Grupo #{group_number}: {pair.base_name}\n"
                                 f"▶ � Doble clic para expandir y ver archivos HEIC y JPG\n"
                                 f"� Las columnas muestran información de cada archivo individual")
        
        # Color de fondo sutil para el grupo
        for col in range(4):
            group_item.setBackground(col, QColor(DesignSystem.COLOR_BG_1))
        
        # Añadir archivo HEIC como hijo
        heic_item = QTreeWidgetItem(group_item)
        heic_item.setIcon(0, icon_manager.get_icon('camera', size=16))
        heic_item.setText(0, pair.heic_path.name)
        heic_item.setText(1, format_size(pair.heic_size))
        heic_item.setText(2, "HEIC")
        
        if format_to_delete == "HEIC":
            heic_item.setText(3, "✗ Eliminar")
            heic_item.setForeground(3, QColor(DesignSystem.COLOR_ERROR))
        else:
            heic_item.setText(3, "✓ Conservar")
            heic_item.setForeground(3, QColor(DesignSystem.COLOR_SUCCESS))
            for col in range(4):
                heic_item.setBackground(col, QColor(f"{DesignSystem.COLOR_SUCCESS}15"))
        
        # Guardar referencia al archivo HEIC
        heic_item.setData(0, Qt.ItemDataRole.UserRole, pair.heic_path)
        
        # Tooltip para HEIC
        heic_mtime = datetime.fromtimestamp(pair.heic_path.stat().st_mtime)
        heic_item.setToolTip(0, f"<b>{pair.heic_path.name}</b><br>"
                                f"📂 {pair.heic_path.parent}<br>"
                                f"📊 {format_size(pair.heic_size)}<br>"
                                f"📅 {heic_mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>"
                                f"{'✓ Se conservará' if format_to_delete == 'JPG' else '✗ Se eliminará'}")
        
        # Añadir archivo JPG como hijo
        jpg_item = QTreeWidgetItem(group_item)
        jpg_item.setIcon(0, icon_manager.get_icon('image', size=16))
        jpg_item.setText(0, pair.jpg_path.name)
        jpg_item.setText(1, format_size(pair.jpg_size))
        jpg_item.setText(2, "JPG")
        
        if format_to_delete == "JPG":
            jpg_item.setText(3, "✗ Eliminar")
            jpg_item.setForeground(3, QColor(DesignSystem.COLOR_ERROR))
        else:
            jpg_item.setText(3, "✓ Conservar")
            jpg_item.setForeground(3, QColor(DesignSystem.COLOR_SUCCESS))
            for col in range(4):
                jpg_item.setBackground(col, QColor(f"{DesignSystem.COLOR_SUCCESS}15"))
        
        # Guardar referencia al archivo JPG
        jpg_item.setData(0, Qt.ItemDataRole.UserRole, pair.jpg_path)
        
        # Tooltip para JPG
        jpg_mtime = datetime.fromtimestamp(pair.jpg_path.stat().st_mtime)
        jpg_item.setToolTip(0, f"<b>{pair.jpg_path.name}</b><br>"
                               f"📂 {pair.jpg_path.parent}<br>"
                               f"📊 {format_size(pair.jpg_size)}<br>"
                               f"📅 {jpg_mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>"
                               f"{'✓ Se conservará' if format_to_delete == 'HEIC' else '✗ Se eliminará'}")
    
    def _on_item_expanded(self, item):
        """Actualiza el indicador visual cuando se expande un grupo"""
        if item.childCount() > 0:  # Es un grupo padre
            current_text = item.text(0)
            if current_text.startswith("▶ "):
                item.setText(0, f"▼ {current_text[2:]}")
            elif not current_text.startswith("▼"):
                item.setText(0, f"▼ {current_text}")

    def _on_item_collapsed(self, item):
        """Actualiza el indicador visual cuando se colapsa un grupo"""
        if item.childCount() > 0:  # Es un grupo padre
            current_text = item.text(0)
            if current_text.startswith("▼ "):
                item.setText(0, f"▶ {current_text[2:]}")
    
    def _on_item_double_clicked(self, item, column):
        """Maneja doble click: expande grupos o abre archivos"""
        from .dialog_utils import open_file
        
        # Obtener el archivo asociado al item
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if file_path and isinstance(file_path, Path):
            # Es un archivo, abrirlo
            open_file(file_path, self)
        else:
            # Es un grupo, expandir/colapsar
            item.setExpanded(not item.isExpanded())
    
    def _show_context_menu(self, position):
        """Muestra menú contextual para archivos individuales"""
        from .dialog_utils import open_file, open_folder, show_file_details_dialog
        
        item = self.tree_widget.itemAt(position)
        if not item:
            return
        
        # Obtener el archivo asociado al item
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not isinstance(file_path, Path):
            return  # Es un grupo padre, no mostrar menú
        
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        
        # Opciones para abrir archivo
        open_action = menu.addAction(icon_manager.get_icon('open-in-app'), "Abrir archivo")
        open_action.triggered.connect(lambda: open_file(file_path, self))
        
        # Opción para abrir carpeta
        open_folder_action = menu.addAction(icon_manager.get_icon('folder-open'), "Abrir carpeta contenedora")
        open_folder_action.triggered.connect(lambda: open_folder(file_path.parent, self))
        
        menu.addSeparator()
        
        # Opción para ver detalles
        details_action = menu.addAction(icon_manager.get_icon('info'), "Ver detalles del archivo")
        details_action.triggered.connect(lambda: show_file_details_dialog(file_path, self))
        
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))
    
    def _update_button_text(self):
        """Actualiza el texto del botón según el formato seleccionado"""
        if self.analysis.total_pairs > 0:
            if self.selected_format == 'jpg':
                savings = self.analysis.potential_savings_keep_jpg
            else:
                savings = self.analysis.potential_savings_keep_heic

            space_formatted = format_size(savings)
            self.ok_button.setText(
                f"Eliminar Duplicados ({self.analysis.total_pairs} grupos, {space_formatted})"
            )

    def accept(self):
        # Pasar el analysis completo + parámetros por separado
        self.accepted_plan = {
            'analysis': self.analysis,  # Ya es un HeicAnalysisResult dataclass
            'keep_format': self.selected_format,
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled(),
        }
        super().accept()
