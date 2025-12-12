"""
Diálogo de renombrado de archivos
Incluye filtrado, búsqueda, estadísticas detalladas y mejor UX
"""
from pathlib import Path
from collections import Counter
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialogButtonBox, QLabel, QCheckBox, QLineEdit, 
    QComboBox, QPushButton, QFrame, QApplication, QWidget
)
from PyQt6.QtGui import QColor, QFont, QCursor
from PyQt6.QtCore import Qt, QTimer
from utils.format_utils import format_size
from utils.settings_manager import settings_manager
from config import Config
from ui.styles.design_system import DesignSystem
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from utils.logger import get_logger
from .base_dialog import BaseDialog


class FileRenamerDialog(BaseDialog):
    """Diálogo de preview para renombrado con funcionalidades avanzadas"""
    
    # Configuración de paginación
    ITEMS_PER_PAGE = 250  # Mostrar 250 items por página para mejor rendimiento
    MAX_ITEMS_WITHOUT_PAGINATION = 500  # Sin paginación hasta 500 items

    def __init__(self, analysis_results, parent=None):
        super().__init__(parent)
        self.logger = get_logger('RenamingPreviewDialog')
        self.analysis_results = analysis_results  # RenameAnalysisResult (dataclass)
        self.accepted_plan = None
        
        # Datos filtrados para la tabla
        try:
            self.filtered_plan = list(analysis_results.renaming_plan)
        except AttributeError as e:
            self.logger.error(f"Error accediendo a renaming_plan: {e}")
            self.filtered_plan = []
        
        # Paginación
        self.current_page = 0
        self.total_pages = 0
        
        self.init_ui()
        self._update_table()

    def update_statistics(self, results):
        """Actualiza las estadísticas después del renombrado
        
        Args:
            results: RenameDeletionResult (dataclass)
        """
        if hasattr(self, 'stats_labels'):
            self.stats_labels['renamed'].setText(str(results.files_renamed))
            self.stats_labels['conflicts'].setText(str(results.conflicts_resolved))
            self.stats_labels['errors'].setText(str(len(results.errors)))

    def init_ui(self):
        self.setWindowTitle("Renombrado de archivos")
        self.setModal(True)
        self.resize(1200, 800)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, int(DesignSystem.SPACE_20))
        
        # Header compacto integrado con métricas inline
        header = self._create_compact_header_with_metrics(
            icon_name='rename-box-outline',
            title='Renombrado de archivos',
            description='Los archivos se renombrarán al formato YYYY-MM-DD_HH-MM-SS según fecha de creación.',
            metrics=[
                {
                    'value': str(self.analysis_results.items_count),
                    'label': 'Total',
                    'color': DesignSystem.COLOR_PRIMARY
                },
                {
                    'value': str(self.analysis_results.already_renamed),
                    'label': 'OK',
                    'color': DesignSystem.COLOR_SUCCESS
                },
                {
                    'value': str(self.analysis_results.need_renaming),
                    'label': 'Renombrar',
                    'color': DesignSystem.COLOR_WARNING
                },
                {
                    'value': str(self.analysis_results.conflicts),
                    'label': 'Conflictos',
                    'color': DesignSystem.COLOR_ERROR
                }
            ]
        )
        main_layout.addWidget(header)
        
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
        
        # Sección de información y advertencias
        info_section = self._create_info_section()
        content_layout.addWidget(info_section)
        
        # Barra de herramientas: filtros y búsqueda
        toolbar = self._create_toolbar()
        content_layout.addLayout(toolbar)
        
        # Tabla de cambios propuestos
        self.changes_table = self._create_changes_table()
        content_layout.addWidget(self.changes_table)
        
        # Controles de paginación (si hay muchos archivos)
        self.pagination_widget = self._create_pagination_controls()
        content_layout.addWidget(self.pagination_widget)
        
        # Panel de problemas (si hay) - colapsable al final
        if self.analysis_results.issues:
            problems_widget = self._create_problems_section()
            content_layout.addWidget(problems_widget)
        
        # Opciones de seguridad
        options_group = self._create_options_group()
        content_layout.addWidget(options_group)
        
        # Botones con estilo Material Design
        ok_enabled = self.analysis_results.need_renaming > 0
        ok_text = f"Proceder ({self.analysis_results.need_renaming})" if ok_enabled else None
        buttons = self.make_ok_cancel_buttons(
            ok_text=ok_text,
            ok_enabled=ok_enabled,
            button_style='primary'
        )
        self.buttons = buttons
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        content_layout.addWidget(buttons)
        
        # Actualizar tabla inicial
        self._update_table()
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())

    def _create_info_section(self):
        """Crea sección de información y advertencias"""
        message = (
            "El renombrado de archivos puede afectar a pares de archivos como Live Photos o HEIC+JPG "
            "si no se renombran juntos.<br><br>"
            "Los conflictos de nombre se resolverán añadiendo un sufijo numérico (ej: _1, _2) "
            "para evitar sobrescrituras."
        )
        
        return self._create_info_banner(
            title="Nota Importante",
            message=message
        )



    def _create_toolbar(self):
        """Crea la barra de herramientas con filtros y búsqueda"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(DesignSystem.SPACE_12)
        toolbar.setContentsMargins(0, 0, 0, 0)
        
        # Búsqueda
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(DesignSystem.SPACE_8)
        
        search_icon = QLabel()
        icon_manager.set_label_icon(search_icon, 'magnify', size=DesignSystem.ICON_SIZE_SM, color=DesignSystem.COLOR_TEXT_SECONDARY)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar archivo...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setMinimumWidth(200)
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
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        toolbar.addWidget(search_container)
        
        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER}; background-color: {DesignSystem.COLOR_BORDER};")
        sep.setFixedHeight(20)
        toolbar.addWidget(sep)
        
        # Filtro por estado/conflicto
        filter_label = QLabel("Estado:")
        filter_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Todos",
            "Solo conflictos",
            "Sin conflictos"
        ])
        self.filter_combo.currentTextChanged.connect(self._apply_filters)
        self.filter_combo.setMinimumWidth(150)
        self.filter_combo.setStyleSheet(DesignSystem.get_combobox_style())
        
        toolbar.addWidget(filter_label)
        toolbar.addWidget(self.filter_combo)
        
        # Filtro por tipo de archivo
        type_label = QLabel("Tipo:")
        type_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        
        self.type_combo = QComboBox()
        file_types = ["Todos"] + sorted(list(set(
            Config.get_file_type(item['original_path'].name) 
            for item in self.analysis_results.renaming_plan
        )))
        self.type_combo.addItems(file_types)
        self.type_combo.currentTextChanged.connect(self._apply_filters)
        self.type_combo.setMinimumWidth(120)
        self.type_combo.setStyleSheet(DesignSystem.get_combobox_style())
        
        toolbar.addWidget(type_label)
        toolbar.addWidget(self.type_combo)
        
        # Filtro por año
        year_label = QLabel("Año:")
        year_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        
        self.year_combo = QComboBox()
        years = ["Todos"] + [str(year) for year in sorted(self.analysis_results.files_by_year.keys(), reverse=True)]
        self.year_combo.addItems(years)
        self.year_combo.currentTextChanged.connect(self._apply_filters)
        self.year_combo.setMinimumWidth(100)
        self.year_combo.setStyleSheet(DesignSystem.get_combobox_style())
        
        toolbar.addWidget(year_label)
        toolbar.addWidget(self.year_combo)
        
        toolbar.addStretch()
        
        # Botón limpiar filtros
        clear_btn = QPushButton("Limpiar")
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
        toolbar.addWidget(clear_btn)
        
        # Contador de resultados
        self.counter_label = QLabel()
        self.counter_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_PRIMARY};
            margin-left: {DesignSystem.SPACE_12}px;
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        toolbar.addWidget(self.counter_label)
        
        return toolbar
    
    def _create_changes_table(self):
        """Crea la tabla de cambios propuestos"""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Original", "Nuevo", "Fecha", "Tipo", "Conflicto"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Hacer tabla no editable
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Estilos
        table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                outline: none;
                background-color: {DesignSystem.COLOR_SURFACE};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px;
            }}
            QTableWidget::item {{
                border: none;
                outline: none;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_4}px;
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};
            }}
            QTableWidget::item:hover {{
                background-color: {DesignSystem.COLOR_BG_2};
            }}
            QTableWidget::item:selected {{
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
        
        # Tooltip informativo
        table.setToolTip(
            "Doble clic en cualquier fila para abrir el archivo original\n"
            "Clic derecho para ver detalles y opciones"
        )
        
        # Conectar doble clic para abrir archivos
        table.itemDoubleClicked.connect(self._on_file_double_clicked)
        
        # Conectar menú contextual
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)
        
        return table
    
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
        
        # Botón primera página
        self.first_page_btn = QPushButton()
        self.first_page_btn.setToolTip("Primera página")
        icon_manager.set_button_icon(self.first_page_btn, 'skip-previous', size=DesignSystem.ICON_SIZE_MD)
        self.first_page_btn.clicked.connect(self._go_first_page)
        self.first_page_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.first_page_btn.setFixedSize(36, 36)
        layout.addWidget(self.first_page_btn)
        
        # Botón página anterior
        self.prev_page_btn = QPushButton()
        self.prev_page_btn.setToolTip("Página anterior")
        icon_manager.set_button_icon(self.prev_page_btn, 'chevron-left', size=DesignSystem.ICON_SIZE_MD)
        self.prev_page_btn.clicked.connect(self._go_prev_page)
        self.prev_page_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.prev_page_btn.setFixedSize(36, 36)
        layout.addWidget(self.prev_page_btn)
        
        # Label de página actual
        self.page_label = QLabel()
        self.page_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            padding: 0 {DesignSystem.SPACE_16}px;
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)
        
        # Botón página siguiente
        self.next_page_btn = QPushButton()
        self.next_page_btn.setToolTip("Página siguiente")
        icon_manager.set_button_icon(self.next_page_btn, 'chevron-right', size=DesignSystem.ICON_SIZE_MD)
        self.next_page_btn.clicked.connect(self._go_next_page)
        self.next_page_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.next_page_btn.setFixedSize(36, 36)
        layout.addWidget(self.next_page_btn)
        
        # Botón última página
        self.last_page_btn = QPushButton()
        self.last_page_btn.setToolTip("Última página")
        icon_manager.set_button_icon(self.last_page_btn, 'skip-next', size=DesignSystem.ICON_SIZE_MD)
        self.last_page_btn.clicked.connect(self._go_last_page)
        self.last_page_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        self.last_page_btn.setFixedSize(36, 36)
        layout.addWidget(self.last_page_btn)
        
        layout.addStretch()
        
        # Combo para cambiar items por página
        layout.addWidget(QLabel("Items por página:"))
        self.items_per_page_combo = QComboBox()
        self.items_per_page_combo.addItems(["100", "250", "500", "1000", "Todos"])
        self.items_per_page_combo.setCurrentText("250")
        self.items_per_page_combo.currentTextChanged.connect(self._change_items_per_page)
        self.items_per_page_combo.setFixedWidth(100)
        self.items_per_page_combo.setStyleSheet(DesignSystem.get_combobox_style())
        layout.addWidget(self.items_per_page_combo)
        
        widget.setVisible(False)  # Oculto por defecto
        return widget
    
    def _go_first_page(self):
        """Ir a la primera página"""
        self.current_page = 0
        # Usar QTimer para evitar congelación en UI
        QTimer.singleShot(0, self._update_table)
    
    def _go_prev_page(self):
        """Ir a la página anterior"""
        if self.current_page > 0:
            self.current_page -= 1
            QTimer.singleShot(0, self._update_table)
    
    def _go_next_page(self):
        """Ir a la página siguiente"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            QTimer.singleShot(0, self._update_table)
    
    def _go_last_page(self):
        """Ir a la última página"""
        self.current_page = max(0, self.total_pages - 1)
        QTimer.singleShot(0, self._update_table)
    
    def _change_items_per_page(self, text):
        """Cambia la cantidad de items por página"""
        if text == "Todos":
            self.ITEMS_PER_PAGE = len(self.filtered_plan)
        else:
            self.ITEMS_PER_PAGE = int(text)
        self.current_page = 0  # Resetear a primera página
        QTimer.singleShot(0, self._update_table)

    def _create_problems_section(self):
        """Crea sección colapsable de problemas"""
        group = QGroupBox(f"Archivos con Problemas ({len(self.analysis_results.issues)})")
        group.setCheckable(True)
        group.setChecked(False)  # Colapsado por defecto
        group.setMaximumHeight(150)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                margin-top: {DesignSystem.SPACE_12}px;
                padding-top: {DesignSystem.SPACE_12}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {DesignSystem.SPACE_12}px;
                padding: 0 {DesignSystem.SPACE_4}px;
            }}
        """)
        
        layout = QVBoxLayout()
        
        info = QLabel("Estos archivos no pueden procesarse y serán ignorados:")
        info.setStyleSheet(f"color: {DesignSystem.COLOR_WARNING}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        layout.addWidget(info)
        
        # Lista simple de problemas
        problems_text = "\n".join(self.analysis_results.issues[:10])
        if len(self.analysis_results.issues) > 10:
            problems_text += f"\n... y {len(self.analysis_results.issues) - 10} más"
        
        problems_label = QLabel(problems_text)
        problems_label.setWordWrap(True)
        problems_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        layout.addWidget(problems_label)
        
        group.setLayout(layout)
        return group

    def _create_options_group(self):
        """Crea el grupo de opciones de seguridad usando método centralizado"""
        return self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de renombrar",
            dry_run_label="Modo simulación (no renombrar realmente)"
        )

    def _analyze_file_types(self):
        """Analiza los tipos de archivo en el plan de renombrado"""
        type_counter = Counter()
        for item in self.analysis_results.renaming_plan:
            file_type = Config.get_file_type(item['original_path'].name)
            type_counter[file_type] += 1
        return type_counter

    def _apply_filters(self):
        """Aplica los filtros a la tabla"""
        search_text = self.search_input.text().lower()
        filter_option = self.filter_combo.currentText()
        year_filter = self.year_combo.currentText()
        type_filter = self.type_combo.currentText()
        
        self.filtered_plan = []
        
        for item in self.analysis_results.renaming_plan:
            # Filtro de búsqueda
            if search_text and search_text not in item['original_path'].name.lower():
                continue
            
            # Filtro por conflicto
            if filter_option == "Solo conflictos" and not item['has_conflict']:
                continue
            elif filter_option == "Sin conflictos" and item['has_conflict']:
                continue
            
            # Filtro por año
            if year_filter != "Todos" and str(item['date'].year) != year_filter:
                continue
            
            # Filtro por tipo de archivo
            if type_filter != "Todos":
                file_type = Config.get_file_type(item['original_path'].name)
                if file_type != type_filter:
                    continue
            
            self.filtered_plan.append(item)
        
        # Resetear a primera página cuando se cambian los filtros
        self.current_page = 0
        self._update_table()

    def _clear_filters(self):
        """Limpia todos los filtros"""
        self.search_input.clear()
        self.filter_combo.setCurrentIndex(0)
        self.year_combo.setCurrentIndex(0)
        self.type_combo.setCurrentIndex(0)

    def _update_table(self):
        """Actualiza la tabla con los datos filtrados y paginación"""
        # Mostrar cursor de espera
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        
        try:
            total_filtered = len(self.filtered_plan)
            
            # Determinar si necesitamos paginación
            use_pagination = total_filtered > self.MAX_ITEMS_WITHOUT_PAGINATION
            
            if use_pagination:
                # Calcular paginación
                self.total_pages = (total_filtered + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
                start_idx = self.current_page * self.ITEMS_PER_PAGE
                end_idx = min(start_idx + self.ITEMS_PER_PAGE, total_filtered)
                items_to_show = self.filtered_plan[start_idx:end_idx]
                
                # Actualizar controles de paginación
                self.pagination_widget.setVisible(True)
                self.page_label.setText(
                    f"Página {self.current_page + 1} de {self.total_pages} "
                    f"(mostrando {start_idx + 1}-{end_idx} de {total_filtered})"
                )
                
                # Habilitar/deshabilitar botones
                self.first_page_btn.setEnabled(self.current_page > 0)
                self.prev_page_btn.setEnabled(self.current_page > 0)
                self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
                self.last_page_btn.setEnabled(self.current_page < self.total_pages - 1)
            else:
                # Sin paginación, mostrar todos
                items_to_show = self.filtered_plan
                self.pagination_widget.setVisible(False)
            
            # Optimización: desactivar updates durante la carga
            self.changes_table.setUpdatesEnabled(False)
            self.changes_table.setSortingEnabled(False)
            
            # Limpiar tabla y redimensionar
            self.changes_table.clearContents()
            self.changes_table.setRowCount(len(items_to_show))
            
            # Procesar eventos cada 100 filas para evitar congelación
            for row, item in enumerate(items_to_show):
                # Original
                original_item = QTableWidgetItem(item['original_path'].name)
                original_item.setData(Qt.ItemDataRole.UserRole, str(item['original_path']))
                self.changes_table.setItem(row, 0, original_item)
                
                # Nuevo
                new_item = QTableWidgetItem(item['new_name'])
                if item['has_conflict']:
                    new_item.setBackground(QColor(255, 243, 205))
                self.changes_table.setItem(row, 1, new_item)
                
                # Fecha
                date_item = QTableWidgetItem(item['date'].strftime('%Y-%m-%d %H:%M:%S'))
                self.changes_table.setItem(row, 2, date_item)
                
                # Tipo
                file_type = Config.get_file_type(item['original_path'].name)
                type_item = QTableWidgetItem(file_type)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.changes_table.setItem(row, 3, type_item)
                
                # Conflicto
                conflict_text = "Sí" if item['has_conflict'] else "No"
                conflict_item = QTableWidgetItem(conflict_text)
                conflict_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if item['has_conflict']:
                    conflict_item.setBackground(QColor(255, 193, 7))  # DesignSystem.COLOR_CONFLICT_BG
                    conflict_item.setForeground(QColor(0, 0, 0))
                else:
                    conflict_item.setBackground(QColor(76, 175, 80))  # DesignSystem.COLOR_SUCCESS_BG
                    conflict_item.setForeground(QColor(255, 255, 255))
                self.changes_table.setItem(row, 4, conflict_item)
                
                # Procesar eventos cada 100 filas para mantener UI responsiva
                if row % 100 == 0:
                    QApplication.processEvents()
            
            # Reactivar updates y ordenamiento
            self.changes_table.setSortingEnabled(True)
            self.changes_table.setUpdatesEnabled(True)
            
            # Actualizar contador
            total = len(self.analysis_results.renaming_plan)
            if use_pagination:
                self.counter_label.setText(
                    f"Mostrando {len(items_to_show)} de {total_filtered} archivos filtrados "
                    f"({total} total)"
                )
            else:
                if total_filtered == total:
                    self.counter_label.setText(f"Mostrando {total_filtered} archivos")
                else:
                    self.counter_label.setText(f"Mostrando {total_filtered} de {total} archivos")
        
        finally:
            # Restaurar cursor normal
            QApplication.restoreOverrideCursor()
    
    def _on_file_double_clicked(self, item):
        """Abre el archivo con la aplicación predeterminada del sistema al hacer doble clic"""
        import subprocess
        import platform
        
        # Obtener la ruta del archivo desde la primera columna de la fila
        row = item.row()
        first_column_item = self.changes_table.item(row, 0)
        
        if not first_column_item:
            return
        
        file_path = first_column_item.data(Qt.ItemDataRole.UserRole)
        if not file_path:
            return
        
        file_path = Path(file_path)
        if not file_path.exists():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Archivo no encontrado", 
                f"El archivo no existe:\n{file_path}"
            )
            return
        
        # Abrir con la aplicación predeterminada según el sistema operativo
        try:
            system = platform.system()
            if system == 'Linux':
                subprocess.Popen(['xdg-open', str(file_path)])
            elif system == 'Darwin':  # macOS
                subprocess.Popen(['open', str(file_path)])
            elif system == 'Windows':
                subprocess.Popen(['start', str(file_path)], shell=True)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error al abrir archivo",
                f"No se pudo abrir el archivo:\n{str(e)}"
            )
    
    def _show_context_menu(self, position):
        """Muestra menú contextual para archivos"""
        from PyQt6.QtWidgets import QMenu
        
        # Obtener item seleccionado
        item = self.changes_table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        first_column_item = self.changes_table.item(row, 0)
        
        if not first_column_item:
            return
        
        file_path = first_column_item.data(Qt.ItemDataRole.UserRole)
        if not file_path:
            return
        
        file_path = Path(file_path)
        
        # Obtener información adicional del archivo desde filtered_plan
        file_info = None
        for plan_item in self.filtered_plan:
            if plan_item['original_path'] == file_path:
                file_info = plan_item
                break
        
        if not file_info:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        
        # Opción para abrir archivo
        open_file_action = menu.addAction("Abrir archivo")
        open_file_action.triggered.connect(lambda: self._open_file(file_path))
        
        # Opción para abrir carpeta
        open_folder_action = menu.addAction("Abrir carpeta")
        open_folder_action.triggered.connect(lambda: self._open_folder(file_path.parent))
        
        menu.addSeparator()
        
        # Opción para ver detalles
        details_action = menu.addAction("Ver detalles completos")
        details_action.triggered.connect(lambda: self._show_file_details(file_info))
        
        menu.exec(self.changes_table.viewport().mapToGlobal(position))
    
    def _open_file(self, file_path):
        """Abre un archivo específico"""
        from .dialog_utils import open_file
        open_file(file_path, self)
    
    def _open_folder(self, folder_path):
        """Abre una carpeta en el explorador de archivos"""
        from .dialog_utils import open_folder
        open_folder(folder_path, self)
    
    def _show_file_details(self, file_info):
        """Muestra un diálogo con detalles completos del archivo"""
        from .dialog_utils import show_file_details_dialog
        
        file_path = file_info['original_path']
        
        # Detectar tipo de archivo desde la extensión
        from config import Config
        file_type = 'Imagen' if Config.is_image_file(file_path) else 'Video' if Config.is_video_file(file_path) else 'Desconocido'
        
        additional_info = {
            'original_name': file_path.name,
            'new_name': file_info['new_name'],
            'file_type': file_type,
            'conflict': file_info.get('has_conflict', False),  # Key correcta: has_conflict
            'metadata': {
                'Fecha detectada': file_info['date'].strftime('%Y-%m-%d %H:%M:%S'),
                'Año': str(file_info['date'].year),  # Obtener año desde date
            }
        }
        
        if file_info.get('has_conflict'):  # Key correcta: has_conflict
            additional_info['metadata']['Conflicto'] = 'Sí - Se resolverá con sufijo numérico'
            if file_info.get('sequence'):
                additional_info['metadata']['Secuencia'] = f"#{file_info['sequence']}"
        
        show_file_details_dialog(file_path, self, additional_info)

    def accept(self):
        # Pasar el analysis completo + parámetros por separado
        self.accepted_plan = {
            'analysis': self.analysis_results,  # Ya es RenameAnalysisResult dataclass
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        super().accept()
