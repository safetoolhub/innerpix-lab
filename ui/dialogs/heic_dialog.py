"""
Diálogo de eliminación de duplicados HEIC/JPG
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
from ui.styles.icons import icon_manager
from .base_dialog import BaseDialog


class HeicDialog(BaseDialog):
    """Diálogo para eliminación de duplicados HEIC/JPG con vista de grupos expandibles"""
    
    # Constantes para carga progresiva
    INITIAL_LOAD = 100
    LOAD_INCREMENT = 100
    WARNING_THRESHOLD = 500

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.selected_format = 'jpg'
        self.accepted_plan = None
        
        # Datos de grupos
        self.all_pairs = list(analysis.duplicate_pairs)
        self.filtered_pairs = list(analysis.duplicate_pairs)
        self.loaded_count = 0
        
        # Referencias a widgets
        self.tree_widget = None
        self.search_input = None
        self.dir_combo = None
        self.counter_label = None
        self.pagination_bar = None
        
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
            icon_name='image-album',
            title='Duplicados HEIC/JPG detectados',
            description='Fotos HEIC con versiones JPG idénticas. Elige qué formato conservar y libera espacio.',
            metrics=[
                {
                    'value': str(self.analysis.items_count),
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
        
        # Barra de carga progresiva
        self.pagination_bar = self._create_progressive_loading_bar(
            on_load_more=self._load_more_groups,
            on_load_all=self._load_all_groups
        )
        content_layout.addWidget(self.pagination_bar)
        
        # Opciones de seguridad
        options_group = self._create_options_group()
        content_layout.addWidget(options_group)
        
        # Botones con estilo Material Design
        ok_enabled = self.analysis.items_count > 0
        self.buttons = self.make_ok_cancel_buttons(
            ok_enabled=ok_enabled,
            button_style='danger'
        )
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_enabled:
            self._update_button_text()
        content_layout.addWidget(self.buttons)
        
        # Cargar grupos iniciales
        self._load_initial_groups()

    def _create_format_selector(self) -> QFrame:
        """Crea selector de formato usando el diseño compacto horizontal."""
        formats = [
            ('jpg', 'file-jpg-box', 'Mantener JPG', 
             f'Máxima compatibilidad. Liberarás {format_size(self.analysis.potential_savings_keep_jpg)}'),
            ('heic', 'file-image', 'Mantener HEIC', 
             f'Archivos más pequeños. Liberarás {format_size(self.analysis.potential_savings_keep_heic)}')
        ]
        
        frame = self._create_compact_strategy_selector(
            title="Conservar:",
            description="Elige qué formato mantener de cada par HEIC/JPG",
            strategies=formats,
            current_strategy=self.selected_format,
            on_strategy_changed=self._on_format_changed
        )
        
        # Guardar referencia a los botones para actualizarlos posteriormente
        self.format_buttons = frame.strategy_buttons
        
        return frame
    
    def _on_format_changed(self, new_format: str) -> None:
        """Maneja el cambio de formato seleccionado.
        
        Args:
            new_format: Nuevo formato seleccionado ('jpg' o 'heic')
        """
        if new_format == self.selected_format:
            return
        
        self.selected_format = new_format
        
        # Actualizar estilos de los botones
        if hasattr(self, 'format_buttons'):
            for fmt, btn in self.format_buttons.items():
                btn.setChecked(fmt == new_format)
        
        # Actualizar métrica de espacio recuperable en el header
        recoverable_space = self.analysis.potential_savings_keep_jpg if new_format == 'jpg' else self.analysis.potential_savings_keep_heic
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(recoverable_space))
        
        # Actualizar texto del botón OK
        self._update_button_text()
        
        # Recargar árbol con nuevo formato
        self._load_initial_groups()
    
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
        icon_manager.set_label_icon(search_icon, 'magnify', size=DesignSystem.ICON_SIZE_SM, color=DesignSystem.COLOR_TEXT_SECONDARY)
        
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
        
        # Filtro por directorio (sin etiqueta, estilo Material)
        self.dir_combo = QComboBox()
        directories = ["Todos los directorios"] + sorted(list(set(
            str(pair.directory) for pair in self.analysis.duplicate_pairs
        )))
        self.dir_combo.addItems(directories)
        self.dir_combo.currentTextChanged.connect(self._apply_filters)
        self.dir_combo.setMinimumWidth(200)
        self.dir_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
            QComboBox:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {DesignSystem.SPACE_8}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                selection-background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                selection-color: {DesignSystem.COLOR_TEXT};
                padding: {DesignSystem.SPACE_4}px;
            }}
        """)
        self.dir_combo.setToolTip("Filtrar grupos por directorio")
        toolbar.addWidget(self.dir_combo)
        
        # Filtro por origen de fecha (sin etiqueta, estilo Material)
        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "Todos los orígenes de fecha",
            "EXIF DateTimeOriginal",
            "EXIF CreateDate",
            "EXIF ModifyDate",
            "Filesystem (mtime)",
            "Filesystem (ctime)",
            "Filesystem (atime)"
        ])
        self.source_combo.currentTextChanged.connect(self._apply_filters)
        self.source_combo.setMinimumWidth(200)
        self.source_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
            QComboBox:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {DesignSystem.SPACE_8}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                selection-background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                selection-color: {DesignSystem.COLOR_TEXT};
                padding: {DesignSystem.SPACE_4}px;
            }}
        """)
        self.source_combo.setToolTip("Filtrar grupos por origen de la fecha de comparación")
        toolbar.addWidget(self.source_combo)
        
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
        
        # Contador de grupos (Estilo Badge Azul para homogeneizar)
        self.counter_label = QLabel()
        self.counter_label.setStyleSheet(f"""
            QLabel {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
                margin-left: {DesignSystem.SPACE_8}px;
            }}
        """)
        toolbar.addWidget(self.counter_label)
        
        return toolbar
    
    def _create_files_tree(self):
        """Crea TreeWidget con grupos expandibles estilo Material Design"""
        from .dialog_utils import create_groups_tree_widget
        
        return create_groups_tree_widget(
            headers=["Grupos / Archivos", "Tamaño", "Tipo", "Fecha", "Origen Fecha", "Estado"],
            column_widths=[300, 100, 80, 160, 150, 120],
            double_click_handler=self._on_item_double_clicked,
            context_menu_handler=self._show_context_menu
        )
    
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
        source_filter = self.source_combo.currentText()
        
        self.filtered_pairs = []
        
        for pair in self.all_pairs:
            # Filtro de búsqueda
            if search_text and search_text not in pair.base_name.lower():
                continue
            
            # Filtro por directorio
            if dir_filter != "Todos los directorios" and str(pair.directory) != dir_filter:
                continue
            
            # Filtro por origen de fecha
            if not self._matches_source_filter(pair.date_source, source_filter):
                continue
            
            self.filtered_pairs.append(pair)
        
        # Reiniciar carga progresiva
        self._load_initial_groups()
    
    def _matches_source_filter(self, date_source: str, filter_value: str) -> bool:
        """Verifica si el origen de fecha coincide con el filtro seleccionado.
        
        Args:
            date_source: Origen de la fecha (ej: 'exif_date_time_original', 'fs_mtime')
            filter_value: Valor del filtro seleccionado
            
        Returns:
            True si coincide con el filtro
        """
        if not date_source or filter_value == "Todos los orígenes de fecha":
            return True
        
        source_lower = date_source.lower()
        
        # Mapeo de filtros a patrones de búsqueda
        if filter_value == "EXIF DateTimeOriginal":
            return "exif_date_time_original" in source_lower or "exif_datetimeoriginal" in source_lower
        elif filter_value == "EXIF CreateDate":
            return "exif_create_date" in source_lower or "exif_createdate" in source_lower
        elif filter_value == "EXIF ModifyDate":
            return "exif_modify_date" in source_lower or "exif_modifydate" in source_lower or "exif_datetime" in source_lower
        elif filter_value == "Filesystem (mtime)":
            return "fs_mtime" in source_lower or "mtime" in source_lower
        elif filter_value == "Filesystem (ctime)":
            return "fs_ctime" in source_lower or "ctime" in source_lower
        elif filter_value == "Filesystem (atime)":
            return "fs_atime" in source_lower or "atime" in source_lower
        
        return False
    
    def _clear_filters(self):
        """Limpia todos los filtros"""
        self.search_input.clear()
        self.dir_combo.setCurrentIndex(0)
        self.source_combo.setCurrentIndex(0)
    
    # ========================================================================
    # LÓGICA DE CARGA PROGRESIVA
    # ========================================================================
    
    def _load_initial_groups(self):
        """Carga los grupos iniciales en el árbol."""
        self.loaded_count = 0
        self.tree_widget.clear()
        self._load_more_groups()
    
    def _load_more_groups(self):
        """Carga más grupos en el árbol."""
        start = self.loaded_count
        end = min(start + self.LOAD_INCREMENT, len(self.filtered_pairs))
        
        # Determinar qué se conservará y eliminará según formato seleccionado
        format_to_keep = "JPG" if self.selected_format == 'jpg' else "HEIC"
        format_to_delete = "HEIC" if self.selected_format == 'jpg' else "JPG"
        
        for i in range(start, end):
            pair = self.filtered_pairs[i]
            self._add_group_to_tree(pair, i + 1, format_to_keep, format_to_delete)
        
        self.loaded_count = end
        self._update_pagination_ui()
    
    def _load_all_groups(self):
        """Carga todos los grupos restantes."""
        from PyQt6.QtWidgets import QMessageBox
        
        if len(self.filtered_pairs) > 1000:
            reply = QMessageBox.question(
                self,
                "Cargar todos los grupos",
                f"Hay {len(self.filtered_pairs)} grupos. ¿Seguro que quieres cargarlos todos?\n"
                "Esto puede tardar y consumir memoria.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        while self.loaded_count < len(self.filtered_pairs):
            self._load_more_groups()
    
    def _update_pagination_ui(self):
        """Actualiza la UI de la barra de carga progresiva."""
        if self.pagination_bar:
            self._update_progressive_loading_ui(
                pagination_bar=self.pagination_bar,
                loaded_count=self.loaded_count,
                filtered_count=len(self.filtered_pairs),
                total_count=len(self.all_pairs),
                load_increment=self.LOAD_INCREMENT
            )
            
            # Actualizar contador
            total = len(self.all_pairs)
            filtered = len(self.filtered_pairs)
            if filtered == total:
                self.counter_label.setText(f"Mostrando {self.loaded_count} de {filtered} grupos")
            else:
                self.counter_label.setText(f"Mostrando {self.loaded_count} de {filtered} grupos filtrados ({total} total)")
    
    def _add_group_to_tree(self, pair, group_number, format_to_keep, format_to_delete):
        """Añade un grupo como nodo padre expandible con archivos HEIC y JPG"""
        from .dialog_utils import apply_group_item_style, create_group_tooltip
        
        # Nodo padre del grupo
        group_item = QTreeWidgetItem(self.tree_widget)
        
        # Texto del grupo - Solo columna 0
        group_item.setText(0, f"Grupo #{group_number} • {pair.base_name}")
        
        # Fecha y origen en el grupo
        group_date = pair.heic_date or pair.jpg_date
        if group_date:
            group_item.setText(3, group_date.strftime('%d/%m/%Y %H:%M:%S'))
        group_item.setText(4, pair.date_source or "")
        
        # Aplicar estilo unificado de grupo
        apply_group_item_style(group_item, num_columns=6)
        
        # Tooltip informativo
        extra_info = ""
        if pair.date_source:
            extra_info = f"Fecha común: {pair.date_source}"
            if pair.date_difference is not None:
                extra_info += f"\nDiferencia: {pair.date_difference:.3f}s"
        
        group_item.setToolTip(0, create_group_tooltip(
            group_number, 
            f"par HEIC/JPG: {pair.base_name}",
            extra_info
        ))
        
        # Añadir archivo HEIC como hijo
        heic_item = QTreeWidgetItem(group_item)
        heic_item.setIcon(0, icon_manager.get_icon('camera', size=16))
        heic_item.setText(0, pair.heic_path.name)
        heic_item.setText(1, format_size(pair.heic_size))
        heic_item.setText(2, "HEIC")
        if pair.heic_date:
            heic_item.setText(3, pair.heic_date.strftime('%d/%m/%Y %H:%M:%S'))
        heic_item.setText(4, pair.date_source or "")
        
        if format_to_delete == "HEIC":
            heic_item.setText(5, "✗ Eliminar")
            heic_item.setForeground(5, QColor(DesignSystem.COLOR_ERROR))
        else:
            heic_item.setText(5, "✓ Conservar")
            heic_item.setForeground(5, QColor(DesignSystem.COLOR_SUCCESS))
        
        # Guardar referencia al archivo HEIC
        heic_item.setData(0, Qt.ItemDataRole.UserRole, pair.heic_path)
        
        # Tooltip para HEIC
        heic_mtime = datetime.fromtimestamp(pair.heic_path.stat().st_mtime)
        heic_tooltip = (f"<b>{pair.heic_path.name}</b><br>"
                       f"Carpeta: {pair.heic_path.parent}<br>"
                       f"Tamaño: {format_size(pair.heic_size)}<br>"
                       f"Fecha: {heic_mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>")
        
        if pair.date_source:
             heic_tooltip += f"Origen fecha: {pair.date_source}<br>"
             
        heic_tooltip += f"{'✓ Se conservará' if format_to_delete == 'JPG' else '✗ Se eliminará'}"
        heic_item.setToolTip(0, heic_tooltip)
        
        # Añadir archivo JPG como hijo
        jpg_item = QTreeWidgetItem(group_item)
        jpg_item.setIcon(0, icon_manager.get_icon('image', size=16))
        jpg_item.setText(0, pair.jpg_path.name)
        jpg_item.setText(1, format_size(pair.jpg_size))
        jpg_item.setText(2, "JPG")
        if pair.jpg_date:
            jpg_item.setText(3, pair.jpg_date.strftime('%d/%m/%Y %H:%M:%S'))
        jpg_item.setText(4, pair.date_source or "")
        
        if format_to_delete == "JPG":
            jpg_item.setText(5, "✗ Eliminar")
            jpg_item.setForeground(5, QColor(DesignSystem.COLOR_ERROR))
        else:
            jpg_item.setText(5, "✓ Conservar")
            jpg_item.setForeground(5, QColor(DesignSystem.COLOR_SUCCESS))
        
        # Guardar referencia al archivo JPG
        jpg_item.setData(0, Qt.ItemDataRole.UserRole, pair.jpg_path)
        
        # Tooltip para JPG
        jpg_mtime = datetime.fromtimestamp(pair.jpg_path.stat().st_mtime)
        jpg_tooltip = (f"<b>{pair.jpg_path.name}</b><br>"
                       f"Carpeta: {pair.jpg_path.parent}<br>"
                       f"Tamaño: {format_size(pair.jpg_size)}<br>"
                       f"Fecha: {jpg_mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>")
        
        if pair.date_source:
             jpg_tooltip += f"Origen fecha: {pair.date_source}<br>"
             
        jpg_tooltip += f"{'✓ Se conservará' if format_to_delete == 'HEIC' else '✗ Se eliminará'}"
        jpg_item.setToolTip(0, jpg_tooltip)
    
    def _on_item_double_clicked(self, item, column):
        """Maneja doble click: expande grupos o abre archivos"""
        from .dialog_utils import handle_tree_item_double_click
        handle_tree_item_double_click(item, column, self)
    
    def _show_context_menu(self, position):
        """Muestra menú contextual para archivos individuales"""
        from .dialog_utils import show_file_context_menu
        show_file_context_menu(self.tree_widget, position, self)
    
    def _update_button_text(self):
        """Actualiza el texto del botón según el formato seleccionado"""
        if self.analysis.items_count > 0:
            if self.selected_format == 'jpg':
                savings = self.analysis.potential_savings_keep_jpg
            else:
                savings = self.analysis.potential_savings_keep_heic

            space_formatted = format_size(savings)
            self.ok_button.setText(
                f"Eliminar Duplicados ({self.analysis.items_count} grupos, {space_formatted})"
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
