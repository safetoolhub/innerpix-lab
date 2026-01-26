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
from utils.file_utils import get_file_type, is_image_file, is_video_file
from config import Config
from ui.styles.design_system import DesignSystem
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from utils.logger import get_logger
from .base_dialog import BaseDialog


class FileRenamerDialog(BaseDialog):
    """Diálogo de preview para renombrado con funcionalidades avanzadas"""
    
    # Constantes para carga progresiva
    INITIAL_LOAD = 100
    LOAD_INCREMENT = 100
    WARNING_THRESHOLD = 500

    def __init__(self, analysis_results, parent=None):
        super().__init__(parent)
        self.logger = get_logger('RenamingPreviewDialog')
        self.analysis_results = analysis_results  # RenameAnalysisResult (dataclass)
        self.accepted_plan = None
        
        # Datos de archivos
        try:
            self.all_items = list(analysis_results.renaming_plan)
            self.filtered_plan = list(analysis_results.renaming_plan)
        except AttributeError as e:
            self.logger.error(f"Error accediendo a renaming_plan: {e}")
            self.all_items = []
            self.filtered_plan = []
        
        # Carga progresiva
        self.loaded_count = 0
        self.pagination_bar = None
        
        self.init_ui()
        self._load_initial_items()

    def update_statistics(self, results):
        """Actualiza las estadísticas después del renombrado
        
        Args:
            results: RenameExecutionResult (dataclass)
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
        
        # Barra de filtros unificada
        self.filter_bar = self._create_filter_bar()
        content_layout.addWidget(self.filter_bar)
        
        # Tabla de cambios propuestos
        self.changes_table = self._create_changes_table()
        content_layout.addWidget(self.changes_table)
        
        # Barra de carga progresiva
        self.pagination_bar = self._create_progressive_loading_bar(
            on_load_more=self._load_more_items,
            on_load_all=self._load_all_items
        )
        content_layout.addWidget(self.pagination_bar)
        
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
        
        # Inicializar all_items desde analysis_results
        self.all_items = list(self.analysis_results.renaming_plan)
        
        # Actualizar tabla inicial
        self._apply_filters()

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



    def _create_filter_bar(self) -> QWidget:
        """Crea barra de filtros unificada usando método base"""
        # Preparar opciones para filtros dinámicos
        file_types = sorted(list(set(
            get_file_type(item['original_path'].name) 
            for item in self.analysis_results.renaming_plan
        )))
        date_sources = sorted(list(set(
            item.get('date_source', 'Desconocido') 
            for item in self.analysis_results.renaming_plan
        )))
        years = [str(year) for year in sorted(self.analysis_results.files_by_year.keys(), reverse=True)]
        
        # Configuración de filtros expandibles
        expandable_filters = [
            {
                'id': 'conflict',
                'type': 'combo',
                'tooltip': 'Filtrar por estado de conflicto',
                'options': ["Todos", "Solo conflictos", "Sin conflictos"],
                'on_change': lambda idx: self._apply_filters(),
                'default_index': 0,
                'min_width': 150
            },
            {
                'id': 'file_type',
                'type': 'combo',
                'tooltip': 'Filtrar por tipo de archivo',
                'options': ["Todos"] + file_types,
                'on_change': lambda idx: self._apply_filters(),
                'default_index': 0,
                'min_width': 120
            },
            {
                'id': 'source',
                'type': 'combo',
                'tooltip': 'Filtrar por fuente de la fecha',
                'options': ["Todos"] + date_sources,
                'on_change': lambda idx: self._apply_filters(),
                'default_index': 0,
                'min_width': 180
            },
            {
                'id': 'year',
                'type': 'combo',
                'tooltip': 'Filtrar por año',
                'options': ["Todos"] + years,
                'on_change': lambda idx: self._apply_filters(),
                'default_index': 0,
                'min_width': 100
            }
        ]
        
        # Crear barra unificada
        filter_bar = self._create_unified_filter_bar(
            on_search_changed=self._apply_filters,
            on_size_filter_changed=lambda idx: self._apply_filters(),
            expandable_filters=expandable_filters,
            is_files_mode=True
        )
        
        # Guardar referencias a componentes
        self.search_input = filter_bar.search_input
        self.size_filter_combo = filter_bar.size_filter_combo  # Renombrar para evitar conflicto
        self.status_chip = filter_bar.status_chip
        self.expand_button = filter_bar.expand_btn
        
        # Referencias a filtros expandibles
        self.filter_combo = filter_bar.filter_widgets.get('conflict')  # Filtro de conflictos
        self.type_combo = filter_bar.filter_widgets.get('file_type')
        self.source_combo = filter_bar.filter_widgets.get('source')
        self.year_combo = filter_bar.filter_widgets.get('year')
        
        return filter_bar
    
    def _create_changes_table(self):
        """Crea la tabla de cambios propuestos"""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Original", "Nuevo", "Fecha", "Fuente", "Tipo"
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
            file_type = get_file_type(item['original_path'].name)
            type_counter[file_type] += 1
        return type_counter

    def _apply_filters(self):
        """Aplica los filtros a la tabla"""
        search_text = self.search_input.text().lower() if self.search_input else ""
        size_filter = self.size_filter_combo.currentText() if hasattr(self, 'size_filter_combo') and self.size_filter_combo else "Todos los tamaños"
        filter_option = self.filter_combo.currentText() if self.filter_combo else "Todos"
        year_filter = self.year_combo.currentText() if self.year_combo else "Todos"
        type_filter = self.type_combo.currentText() if self.type_combo else "Todos"
        source_filter = self.source_combo.currentText() if self.source_combo else "Todos"
        
        self.filtered_plan = []
        
        for item in self.all_items:
            # Filtro de búsqueda
            if search_text and search_text not in item['original_path'].name.lower():
                continue
            
            # Filtro por tamaño
            file_size = item.get('size', 0)
            if file_size and not self._matches_size_filter(file_size, size_filter):
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
                file_type = get_file_type(item['original_path'].name)
                if file_type != type_filter:
                    continue
            
            # Filtro por fuente de fecha
            if source_filter != "Todos":
                item_source = item.get('date_source', 'Desconocido')
                if item_source != source_filter:
                    continue
            
            self.filtered_plan.append(item)
        
        # Reiniciar carga progresiva
        self._load_initial_items()
    
    def _matches_size_filter(self, file_size: int, filter_value: str) -> bool:
        """Verifica si el tamaño del archivo coincide con el filtro seleccionado."""
        if filter_value == "Todos los tamaños":
            return True
        
        mb = file_size / (1024 * 1024)
        
        if filter_value == "< 1 MB":
            return mb < 1
        elif filter_value == "1 - 10 MB":
            return 1 <= mb < 10
        elif filter_value == "10 - 100 MB":
            return 10 <= mb < 100
        elif filter_value == "> 100 MB":
            return mb >= 100
        
        return True

    def _clear_filters(self):
        """Limpia todos los filtros"""
        if self.search_input:
            self.search_input.clear()
        if hasattr(self, 'size_filter_combo') and self.size_filter_combo:
            self.size_filter_combo.setCurrentIndex(0)
        if self.filter_combo:
            self.filter_combo.setCurrentIndex(0)
        if self.year_combo:
            self.year_combo.setCurrentIndex(0)
        if self.source_combo:
            self.source_combo.setCurrentIndex(0)
        if self.type_combo:
            self.type_combo.setCurrentIndex(0)
    
    # ========================================================================
    # LÓGICA DE CARGA PROGRESIVA
    # ========================================================================
    
    def _load_initial_items(self):
        """Carga los items iniciales en la tabla."""
        self.loaded_count = 0
        self.changes_table.setRowCount(0)
        self._load_more_items()
    
    def _load_more_items(self):
        """Carga más items en la tabla."""
        start = self.loaded_count
        end = min(start + self.LOAD_INCREMENT, len(self.filtered_plan))
        
        items_to_load = self.filtered_plan[start:end]
        
        # Optimización: desactivar updates durante la carga
        self.changes_table.setUpdatesEnabled(False)
        self.changes_table.setSortingEnabled(False)
        
        # Añadir filas
        current_row_count = self.changes_table.rowCount()
        self.changes_table.setRowCount(current_row_count + len(items_to_load))
        
        for i, item in enumerate(items_to_load):
            row = current_row_count + i
            has_conflict = item.get('has_conflict', False)
            conflict_color = QColor(255, 200, 200) if has_conflict else None
            
            # Original
            original_item = QTableWidgetItem(item['original_path'].name)
            original_item.setData(Qt.ItemDataRole.UserRole, str(item['original_path']))
            if conflict_color:
                original_item.setBackground(conflict_color)
            self.changes_table.setItem(row, 0, original_item)
            
            # Nuevo
            new_item = QTableWidgetItem(item['new_name'])
            if conflict_color:
                new_item.setBackground(conflict_color)
            self.changes_table.setItem(row, 1, new_item)
            
            # Fecha
            date_item = QTableWidgetItem(item['date'].strftime('%Y-%m-%d %H:%M:%S'))
            if conflict_color:
                date_item.setBackground(conflict_color)
            self.changes_table.setItem(row, 2, date_item)
            
            # Fuente de la fecha
            date_source = item.get('date_source', 'Desconocido')
            source_item = QTableWidgetItem(date_source)
            source_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if conflict_color:
                source_item.setBackground(conflict_color)
            self.changes_table.setItem(row, 3, source_item)
            
            # Tipo
            file_type = get_file_type(item['original_path'].name)
            type_item = QTableWidgetItem(file_type)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if conflict_color:
                type_item.setBackground(conflict_color)
            self.changes_table.setItem(row, 4, type_item)
        
        # Reactivar updates
        self.changes_table.setSortingEnabled(True)
        self.changes_table.setUpdatesEnabled(True)
        
        self.loaded_count = end
        self._update_pagination_ui()
    
    def _load_all_items(self):
        """Carga todos los items restantes."""
        from PyQt6.QtWidgets import QMessageBox
        
        if len(self.filtered_plan) > 1000:
            reply = QMessageBox.question(
                self,
                "Cargar todos los archivos",
                f"Hay {len(self.filtered_plan)} archivos. ¿Seguro que quieres cargarlos todos?\n"
                "Esto puede tardar y consumir memoria.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        while self.loaded_count < len(self.filtered_plan):
            self._load_more_items()
    
    def _update_pagination_ui(self):
        """Actualiza la UI de la barra de carga progresiva."""
        if self.pagination_bar:
            self._update_progressive_loading_ui(
                pagination_bar=self.pagination_bar,
                loaded_count=self.loaded_count,
                filtered_count=len(self.filtered_plan),
                total_count=len(self.all_items),
                load_increment=self.LOAD_INCREMENT
            )
        
        # Actualizar chip de estado (independiente del loaded_count)
        self._update_filter_chip(
            status_chip=self.status_chip,
            filtered_count=len(self.filtered_plan),
            total_count=len(self.all_items),
            loaded_count=self.loaded_count,
            is_files_mode=True
        )
    
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
        file_type = 'Imagen' if is_image_file(file_path) else 'Video' if is_video_file(file_path) else 'Desconocido'
        
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
