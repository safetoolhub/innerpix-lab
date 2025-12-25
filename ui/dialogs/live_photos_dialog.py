"""
Diálogo de limpieza de Live Photos
Grupos expandibles con archivos de imagen y video, diseño Material Design
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
from services.result_types import LivePhotosAnalysisResult, LivePhotoGroup
from .base_dialog import BaseDialog


class LivePhotosDialog(BaseDialog):
    """Diálogo para limpieza de Live Photos con vista de grupos expandibles"""
    
    # Configuración de paginación
    ITEMS_PER_PAGE = 200
    MAX_ITEMS_WITHOUT_PAGINATION = 500

    def __init__(self, analysis: LivePhotosAnalysisResult, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.accepted_plan = None
        
        # Datos filtrados
        self.filtered_groups = list(analysis.groups)
        
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
        self.setWindowTitle("Limpieza de Live Photos")
        self.setModal(True)
        self.resize(1200, 800)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(int(DesignSystem.SPACE_12))
        main_layout.setContentsMargins(0, 0, 0, int(DesignSystem.SPACE_20))
        
        # Calcular espacio recuperable (videos a eliminar)
        potential_savings = self.analysis.potential_savings
        
        # Header compacto integrado con métricas inline
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='camera',
            title='Live Photos detectadas',
            description='Live Photos de iPhone (Imagen + MOV). Los videos MOV serán eliminados para liberar espacio.',
            metrics=[
                {
                    'value': str(self.analysis.items_count),
                    'label': 'Grupos',
                    'color': DesignSystem.COLOR_PRIMARY
                },
                {
                    'value': str(self.analysis.total_images),
                    'label': 'Imágenes',
                    'color': DesignSystem.COLOR_TEXT_SECONDARY
                },
                {
                    'value': format_size(potential_savings),
                    'label': 'Recuperable',
                    'color': DesignSystem.COLOR_SUCCESS
                }
            ]
        )
        main_layout.addWidget(self.header_frame)
        
        # Warning sobre metadata de video desactivado
        if not Config.USE_VIDEO_METADATA:
            warning_container = QWidget()
            warning_container_layout = QVBoxLayout(warning_container)
            warning_container_layout.setContentsMargins(
                int(DesignSystem.SPACE_24),
                int(DesignSystem.SPACE_12),
                int(DesignSystem.SPACE_24),
                0
            )
            warning_container_layout.setSpacing(0)
            
            warning_banner = self._create_warning_banner(
                title='Detección sin validación temporal',
                message='La extracción de metadata de video está desactivada. Los Live Photos se detectan '
                        'solo por coincidencia de nombres, validando únicamente las fechas provenientes del sistema. '
                        'Esto puede incluir falsos positivos.',
                action_text='Activar en Configuración',
                action_callback=self._open_settings
            )
            warning_container_layout.addWidget(warning_banner)
            main_layout.addWidget(warning_container)
        
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
        ok_enabled = self.analysis.items_count > 0
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
            str(group.directory) for group in self.analysis.groups
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
        tree.setHeaderLabels(["Grupos / Archivos", "Tamaño", "Tipo", "Fecha", "Origen Fecha", "Estado"])
        tree.setColumnWidth(0, 350)
        tree.setColumnWidth(1, 100)
        tree.setColumnWidth(2, 80)
        tree.setColumnWidth(3, 160)
        tree.setColumnWidth(4, 150)
        tree.setColumnWidth(5, 120)
        tree.setAlternatingRowColors(True)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
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
        
        self.filtered_groups = []
        
        for group in self.analysis.groups:
            # Filtro de búsqueda
            if search_text and search_text not in group.base_name.lower():
                continue
            
            # Filtro por directorio
            if dir_filter != "Todos" and str(group.directory) != dir_filter:
                continue
            
            self.filtered_groups.append(group)
        
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
            self.ITEMS_PER_PAGE = len(self.filtered_groups)
        else:
            self.ITEMS_PER_PAGE = int(text)
        self.current_page = 0
        QTimer.singleShot(0, self._update_tree)
    
    def _update_tree(self):
        """Actualiza el TreeWidget con grupos expandibles"""
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        
        try:
            total_filtered = len(self.filtered_groups)
            use_pagination = total_filtered > self.MAX_ITEMS_WITHOUT_PAGINATION
            
            if use_pagination:
                self.total_pages = (total_filtered + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
                start_idx = self.current_page * self.ITEMS_PER_PAGE
                end_idx = min(start_idx + self.ITEMS_PER_PAGE, total_filtered)
                items_to_show = self.filtered_groups[start_idx:end_idx]
                
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
                items_to_show = self.filtered_groups
                self.pagination_widget.setVisible(False)
            
            # Limpiar tree
            self.tree_widget.clear()
            
            # Añadir grupos
            for group_number, group in enumerate(items_to_show, start=1):
                self._add_group_to_tree(group, group_number)
                
                # Procesar eventos cada 20 grupos
                if group_number % 20 == 0:
                    QApplication.processEvents()
            
            # Actualizar contador
            total = len(self.analysis.groups)
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
    
    def _add_group_to_tree(self, group: LivePhotoGroup, group_number: int):
        """Añade un grupo como nodo padre expandible con archivos de imagen y video"""
        # Nodo padre del grupo
        group_item = QTreeWidgetItem(self.tree_widget)
        
        # Texto del grupo - Solo columna 0
        images_info = f"{group.image_count} imagen{'es' if group.image_count > 1 else ''}"
        group_item.setText(0, f"Grupo #{group_number} • {group.base_name} ({images_info})")
        
        # Fecha y origen en el grupo
        group_date = group.best_date
        if group_date:
            group_item.setText(3, group_date.strftime('%d/%m/%Y %H:%M:%S'))
        group_item.setText(4, group.date_source or "")
        
        # Estilo del grupo padre estándar (Bold + Blue + BASE size)
        font = group_item.font(0)
        font.setBold(True)
        font.setPointSize(int(DesignSystem.FONT_SIZE_XS))
        group_item.setFont(0, font)
        group_item.setForeground(0, QColor(DesignSystem.COLOR_PRIMARY))
        
        # Tooltip informativo
        tooltip_msg = (f"Grupo #{group_number}: {group.base_name}\n"
                       f"▶ Doble clic para expandir y ver archivos\n"
                       f"📷 {group.image_count} imagen(es) + 1 video MOV\n")
        
        if group.date_source:
            tooltip_msg += f"📅 Fecha común: {group.date_source}\n"
            if group.date_difference is not None:
                tooltip_msg += f"⏱️ Diferencia: {group.date_difference:.3f}s\n"
        
        group_item.setToolTip(0, tooltip_msg)
        
        # Añadir imágenes como hijos
        for idx, img_info in enumerate(group.images):
            img_item = QTreeWidgetItem(group_item)
            img_item.setIcon(0, icon_manager.get_icon('image', size=16))
            img_item.setText(0, img_info.path.name)
            img_item.setText(1, format_size(img_info.size))
            img_item.setText(2, img_info.path.suffix.upper().lstrip('.'))
            if img_info.date:
                img_item.setText(3, img_info.date.strftime('%d/%m/%Y %H:%M:%S'))
            img_item.setText(4, img_info.date_source or "")
            img_item.setText(5, "✓ Conservar")
            img_item.setForeground(5, QColor(DesignSystem.COLOR_SUCCESS))
            
            # Guardar referencia al archivo
            img_item.setData(0, Qt.ItemDataRole.UserRole, img_info.path)
            
            # Tooltip para imagen
            try:
                img_mtime = datetime.fromtimestamp(img_info.path.stat().st_mtime)
                img_tooltip = (f"<b>{img_info.path.name}</b><br>"
                               f"📂 {img_info.path.parent}<br>"
                               f"📊 {format_size(img_info.size)}<br>"
                               f"📅 {img_mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>")
                if img_info.date_source:
                    img_tooltip += f"🔍 Origen fecha: {img_info.date_source}<br>"
                img_tooltip += "✓ Se conservará"
                img_item.setToolTip(0, img_tooltip)
            except Exception:
                pass
        
        # Añadir video como hijo
        video_item = QTreeWidgetItem(group_item)
        video_item.setIcon(0, icon_manager.get_icon('video', size=16))
        video_item.setText(0, group.video_path.name)
        video_item.setText(1, format_size(group.video_size))
        video_item.setText(2, "MOV")
        if group.video_date:
            video_item.setText(3, group.video_date.strftime('%d/%m/%Y %H:%M:%S'))
        video_item.setText(4, group.video_date_source or "")
        video_item.setText(5, "✗ Eliminar")
        video_item.setForeground(5, QColor(DesignSystem.COLOR_ERROR))
        
        # Guardar referencia al video
        video_item.setData(0, Qt.ItemDataRole.UserRole, group.video_path)
        
        # Tooltip para video
        try:
            video_mtime = datetime.fromtimestamp(group.video_path.stat().st_mtime)
            video_tooltip = (f"<b>{group.video_path.name}</b><br>"
                             f"📂 {group.video_path.parent}<br>"
                             f"📊 {format_size(group.video_size)}<br>"
                             f"📅 {video_mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>")
            if group.video_date_source:
                video_tooltip += f"🔍 Origen fecha: {group.video_date_source}<br>"
            video_tooltip += "✗ Se eliminará"
            video_item.setToolTip(0, video_tooltip)
        except Exception:
            pass
    
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
        open_action = menu.addAction(icon_manager.get_icon('open-in-new'), "Abrir archivo")
        open_action.triggered.connect(lambda: open_file(file_path, self))
        
        # Opción para abrir carpeta
        open_folder_action = menu.addAction(icon_manager.get_icon('folder-open'), "Abrir carpeta contenedora")
        open_folder_action.triggered.connect(lambda: open_folder(file_path.parent, self))
        
        menu.addSeparator()
        
        # Opción para ver detalles
        details_action = menu.addAction(icon_manager.get_icon('information'), "Ver detalles del archivo")
        details_action.triggered.connect(lambda: show_file_details_dialog(file_path, self))
        
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))
    
    def _update_button_text(self):
        """Actualiza el texto del botón según los grupos"""
        if self.analysis.items_count > 0:
            savings = self.analysis.potential_savings
            space_formatted = format_size(savings)
            self.ok_button.setText(
                f"Eliminar Videos ({self.analysis.items_count} grupos, {space_formatted})"
            )

    def accept(self):
        """Acepta el diálogo y prepara los datos para la ejecución"""
        # Pasar el analysis completo + parámetros por separado
        self.accepted_plan = {
            'analysis': self.analysis,  # Ya es un LivePhotosAnalysisResult dataclass
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled(),
        }
        super().accept()
    
    def _open_settings(self):
        """Abre el diálogo de configuración en la pestaña General"""
        from .settings_dialog import SettingsDialog
        settings_dialog = SettingsDialog(self, initial_tab=0)  # 0 = General tab
        settings_dialog.exec()
