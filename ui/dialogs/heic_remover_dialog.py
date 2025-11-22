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
        toolbar.setContentsMargins(0, 0, 0, 0)
        
        # Búsqueda
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(DesignSystem.SPACE_8)
        
        search_icon = QLabel()
        icon_manager.set_label_icon(search_icon, 'search', size=DesignSystem.ICON_SIZE_SM, color=DesignSystem.COLOR_TEXT_SECONDARY)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setMinimumWidth(250)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
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
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        toolbar.addWidget(search_container)
        
        # Separador vertical
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER}; background-color: {DesignSystem.COLOR_BORDER};")
        sep.setFixedHeight(20)
        toolbar.addWidget(sep)
        
        # Filtro por directorio
        dir_container = QHBoxLayout()
        dir_container.setSpacing(DesignSystem.SPACE_8)
        
        dir_label = QLabel("Directorio:")
        dir_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        
        self.dir_combo = QComboBox()
        directories = ["Todos"] + sorted(list(set(
            str(pair.directory) for pair in self.analysis.duplicate_pairs
        )))
        self.dir_combo.addItems(directories)
        self.dir_combo.currentTextChanged.connect(self._apply_filters)
        self.dir_combo.setMinimumWidth(200)
        self.dir_combo.setStyleSheet(DesignSystem.get_combobox_style())
        self.dir_combo.setToolTip("Filtrar grupos por directorio")
        
        dir_container.addWidget(dir_label)
        dir_container.addWidget(self.dir_combo)
        toolbar.addLayout(dir_container)
        
        toolbar.addStretch()
        
        # Botón limpiar filtros
        clear_btn = QPushButton("Limpiar Filtros")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_BG_2};
                border-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        icon_manager.set_button_icon(clear_btn, 'close', size=DesignSystem.ICON_SIZE_SM)
        clear_btn.clicked.connect(self._clear_filters)
        clear_btn.setToolTip("Limpiar todos los filtros")
        toolbar.addWidget(clear_btn)
        
        # Contador de grupos
        self.counter_label = QLabel()
        self.counter_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_PRIMARY};
            margin-left: {DesignSystem.SPACE_12}px;
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        toolbar.addWidget(self.counter_label)
        
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
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Match file_organizer_dialog behavior
        tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        tree.setStyleSheet(f"""
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
        tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        tree.customContextMenuRequested.connect(self._show_context_menu)
        
        return tree
    
    def _create_pagination_controls(self):
        """Crea controles de paginación con estilo Material Design"""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px;
            }}
        """)
        layout = QHBoxLayout(widget)
        layout.setSpacing(DesignSystem.SPACE_8)
        layout.setContentsMargins(DesignSystem.SPACE_8, DesignSystem.SPACE_4, DesignSystem.SPACE_8, DesignSystem.SPACE_4)
        
        # Botones de navegación con iconos
        self.first_page_btn = QPushButton()
        self.first_page_btn.setToolTip("Primera página")
        icon_manager.set_button_icon(self.first_page_btn, 'skip-previous', size=DesignSystem.ICON_SIZE_MD)
        self.first_page_btn.clicked.connect(self._go_first_page)
        self.first_page_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.first_page_btn.setFixedSize(36, 36)
        layout.addWidget(self.first_page_btn)
        
        self.prev_page_btn = QPushButton()
        self.prev_page_btn.setToolTip("Página anterior")
        icon_manager.set_button_icon(self.prev_page_btn, 'chevron-left', size=DesignSystem.ICON_SIZE_MD)
        self.prev_page_btn.clicked.connect(self._go_prev_page)
        self.prev_page_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.prev_page_btn.setFixedSize(36, 36)
        layout.addWidget(self.prev_page_btn)
        
        # Indicador de página
        self.page_label = QLabel()
        self.page_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            padding: 0 {DesignSystem.SPACE_16}px;
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)
        
        self.next_page_btn = QPushButton()
        self.next_page_btn.setToolTip("Página siguiente")
        icon_manager.set_button_icon(self.next_page_btn, 'chevron-right', size=DesignSystem.ICON_SIZE_MD)
        self.next_page_btn.clicked.connect(self._go_next_page)
        self.next_page_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.next_page_btn.setFixedSize(36, 36)
        layout.addWidget(self.next_page_btn)
        
        self.last_page_btn = QPushButton()
        self.last_page_btn.setToolTip("Última página")
        icon_manager.set_button_icon(self.last_page_btn, 'skip-next', size=DesignSystem.ICON_SIZE_MD)
        self.last_page_btn.clicked.connect(self._go_last_page)
        self.last_page_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.last_page_btn.setFixedSize(36, 36)
        layout.addWidget(self.last_page_btn)
        
        layout.addStretch()
        
        # Items per page
        items_label = QLabel("Items por página:")
        items_label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        layout.addWidget(items_label)
        
        self.items_per_page_combo = QComboBox()
        self.items_per_page_combo.addItems(["100", "200", "500", "Todos"])
        self.items_per_page_combo.setCurrentText("200")
        self.items_per_page_combo.currentTextChanged.connect(self._change_items_per_page)
        self.items_per_page_combo.setFixedWidth(100)
        self.items_per_page_combo.setStyleSheet(DesignSystem.get_combobox_style())
        layout.addWidget(self.items_per_page_combo)
        
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
        group_item.setText(0, f"Grupo #{group_number} • {pair.base_name}")
        
        # Estilo del grupo padre estándar (Bold + Blue + BASE size)
        font = group_item.font(0)
        font.setBold(True)
        font.setPointSize(int(DesignSystem.FONT_SIZE_BASE))
        group_item.setFont(0, font)
        group_item.setForeground(0, QColor(DesignSystem.COLOR_PRIMARY))
        
        # Tooltip informativo
        group_item.setToolTip(0, f"Grupo #{group_number}: {pair.base_name}\n"
                                 f"▶ Doble clic para expandir y ver archivos HEIC y JPG\n"
                                 f"• Las columnas muestran información de cada archivo individual")
        
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
        
        # Guardar referencia al archivo JPG
        jpg_item.setData(0, Qt.ItemDataRole.UserRole, pair.jpg_path)
        
        # Tooltip para JPG
        jpg_mtime = datetime.fromtimestamp(pair.jpg_path.stat().st_mtime)
        jpg_item.setToolTip(0, f"<b>{pair.jpg_path.name}</b><br>"
                               f"📂 {pair.jpg_path.parent}<br>"
                               f"📊 {format_size(pair.jpg_size)}<br>"
                               f"📅 {jpg_mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>"
                               f"{'✓ Se conservará' if format_to_delete == 'HEIC' else '✗ Se eliminará'}")
    
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
