"""
Diálogo de preview para renombrado - Rediseñado
Incluye filtrado, búsqueda, estadísticas detalladas y mejor UX
"""
from pathlib import Path
from collections import Counter
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialogButtonBox, QLabel, QCheckBox, QLineEdit, 
    QComboBox, QPushButton, QFrame, QApplication
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


class RenamingPreviewDialog(BaseDialog):
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
            results: RenameResult (dataclass)
        """
        if hasattr(self, 'stats_labels'):
            self.stats_labels['renamed'].setText(str(results.files_renamed))
            self.stats_labels['conflicts'].setText(str(results.conflicts_resolved))
            self.stats_labels['errors'].setText(str(len(results.errors)))

    def init_ui(self):
        self.setWindowTitle("Preview de Renombrado")
        self.setModal(True)
        self.resize(1200, 750)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(int(DesignSystem.SPACE_16))
        main_layout.setContentsMargins(0, 0, 0, int(DesignSystem.SPACE_20))
        
        # Header compacto integrado con métricas inline
        header = self._create_compact_header_with_metrics(
            icon_name='rename-outline',
            title='Preview de renombrado',
            description='Los archivos se renombrarán al formato YYYY-MM-DD_HH-MM-SS según fecha de creación.',
            metrics=[
                {
                    'value': str(self.analysis_results.total_files),
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
        content_container = QFrame()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(int(DesignSystem.SPACE_16))
        content_layout.setContentsMargins(
            int(DesignSystem.SPACE_24),
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_24),
            0
        )
        main_layout.addWidget(content_container)
        
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



    def _create_toolbar(self):
        """Crea la barra de herramientas con filtros y búsqueda"""
        toolbar = QHBoxLayout()
        
        # Búsqueda
        search_icon = QLabel()
        icon_manager.set_label_icon(search_icon, 'search', size=16)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar archivo...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setMaximumWidth(200)
        toolbar.addWidget(search_icon)
        toolbar.addWidget(self.search_input)
        
        # Separador
        toolbar.addWidget(QLabel("|"))
        
        # Filtro por estado/conflicto
        filter_label = QLabel("Estado:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Todos",
            "Solo conflictos",
            "Sin conflictos"
        ])
        self.filter_combo.currentTextChanged.connect(self._apply_filters)
        self.filter_combo.setMaximumWidth(150)
        toolbar.addWidget(filter_label)
        toolbar.addWidget(self.filter_combo)
        
        # Filtro por tipo de archivo
        type_label = QLabel("Tipo:")
        self.type_combo = QComboBox()
        file_types = ["Todos"] + sorted(list(set(
            Config.get_file_type(item['original_path'].name) 
            for item in self.analysis_results.renaming_plan
        )))
        self.type_combo.addItems(file_types)
        self.type_combo.currentTextChanged.connect(self._apply_filters)
        self.type_combo.setMaximumWidth(120)
        toolbar.addWidget(type_label)
        toolbar.addWidget(self.type_combo)
        
        # Filtro por año
        year_label = QLabel("Año:")
        self.year_combo = QComboBox()
        years = ["Todos"] + [str(year) for year in sorted(self.analysis_results.files_by_year.keys(), reverse=True)]
        self.year_combo.addItems(years)
        self.year_combo.currentTextChanged.connect(self._apply_filters)
        self.year_combo.setMaximumWidth(100)
        toolbar.addWidget(year_label)
        toolbar.addWidget(self.year_combo)
        
        # Separador
        toolbar.addWidget(QLabel("|"))
        
        # Botón limpiar filtros
        clear_btn = QPushButton("Limpiar")
        icon_manager.set_button_icon(clear_btn, 'close', size=16)
        clear_btn.clicked.connect(self._clear_filters)
        clear_btn.setMaximumWidth(80)
        toolbar.addWidget(clear_btn)
        
        # Contador de resultados
        self.counter_label = QLabel()
        self.counter_label.setStyleSheet(DesignSystem.STYLE_DIALOG_COUNTER_BOLD)
        toolbar.addWidget(self.counter_label)
        
        toolbar.addStretch()
        
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
        """Crea controles de paginación"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.StyledPanel)
        widget.setStyleSheet(DesignSystem.STYLE_DIALOG_PAGINATION_FRAME)
        layout = QHBoxLayout(widget)
        
        # Botón primera página
        self.first_page_btn = QPushButton("⏮ Primera")
        self.first_page_btn.clicked.connect(self._go_first_page)
        self.first_page_btn.setMaximumWidth(100)
        layout.addWidget(self.first_page_btn)
        
        # Botón página anterior
        self.prev_page_btn = QPushButton("◀ Anterior")
        self.prev_page_btn.clicked.connect(self._go_prev_page)
        self.prev_page_btn.setMaximumWidth(100)
        layout.addWidget(self.prev_page_btn)
        
        # Label de página actual
        self.page_label = QLabel()
        self.page_label.setStyleSheet(DesignSystem.STYLE_DIALOG_PAGE_LABEL)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)
        
        # Botón página siguiente
        self.next_page_btn = QPushButton("Siguiente ▶")
        self.next_page_btn.clicked.connect(self._go_next_page)
        self.next_page_btn.setMaximumWidth(100)
        layout.addWidget(self.next_page_btn)
        
        # Botón última página
        self.last_page_btn = QPushButton("Última ⏭")
        self.last_page_btn.clicked.connect(self._go_last_page)
        self.last_page_btn.setMaximumWidth(100)
        layout.addWidget(self.last_page_btn)
        
        layout.addStretch()
        
        # Combo para cambiar items por página
        layout.addWidget(QLabel("Items por página:"))
        self.items_per_page_combo = QComboBox()
        self.items_per_page_combo.addItems(["100", "250", "500", "1000", "Todos"])
        self.items_per_page_combo.setCurrentText("250")
        self.items_per_page_combo.currentTextChanged.connect(self._change_items_per_page)
        self.items_per_page_combo.setMaximumWidth(100)
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
        
        layout = QVBoxLayout()
        
        info = QLabel("Estos archivos no pueden procesarse y serán ignorados:")
        info.setStyleSheet(DesignSystem.STYLE_DIALOG_PROBLEM_INFO)
        layout.addWidget(info)
        
        # Lista simple de problemas
        problems_text = "\n".join(self.analysis_results.issues[:10])
        if len(self.analysis_results.issues) > 10:
            problems_text += f"\n... y {len(self.analysis_results.issues) - 10} más"
        
        problems_label = QLabel(problems_text)
        problems_label.setWordWrap(True)
        problems_label.setStyleSheet(DesignSystem.STYLE_DIALOG_PROBLEM_TEXT)
        layout.addWidget(problems_label)
        
        group.setLayout(layout)
        return group

    def _create_options_group(self):
        """Crea el grupo de opciones de seguridad"""
        options_group = QGroupBox("Opciones de Seguridad")
        # Asegurar que el título no se corte
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet(DesignSystem.STYLE_DIALOG_OPTIONS_GROUP)
        options_layout = QVBoxLayout()
        
        # Checkbox de backup (primero)
        self.add_backup_checkbox(options_layout, "Crear backup antes de renombrar (Recomendado)")
        
        # Checkbox de simulación (segundo)
        self.dry_run_checkbox = QCheckBox("Modo simulación (no renombrar realmente)")
        dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, 'false')
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() == 'true'
        self.dry_run_checkbox.setChecked(dry_run_default)
        options_layout.addWidget(self.dry_run_checkbox)
        
        options_group.setLayout(options_layout)
        return options_group

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
            'dry_run': self.dry_run_checkbox.isChecked()
        }
        super().accept()
