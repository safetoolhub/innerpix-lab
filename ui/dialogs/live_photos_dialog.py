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
from utils.platform_utils import are_video_tools_available
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from services.result_types import LivePhotosAnalysisResult, LivePhotoGroup
from .base_dialog import BaseDialog


class LivePhotosDialog(BaseDialog):
    """Diálogo para limpieza de Live Photos con vista de grupos expandibles"""
    
    # Constantes para carga progresiva
    INITIAL_LOAD = 100
    LOAD_INCREMENT = 100
    WARNING_THRESHOLD = 500

    def __init__(self, analysis: LivePhotosAnalysisResult, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.accepted_plan = None
        
        # Datos de grupos
        self.all_groups = list(analysis.groups)
        self.filtered_groups = list(analysis.groups)
        self.loaded_count = 0
        
        # Referencias a widgets
        self.tree_widget = None
        self.search_input = None
        self.dir_combo = None
        self.counter_label = None
        self.pagination_bar = None
        
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
        
        # Warning sobre metadata de video no disponible
        # Prioridad: 1) Herramientas no instaladas, 2) Configuración desactivada
        video_tools_available = are_video_tools_available()
        
        if not video_tools_available or not Config.USE_VIDEO_METADATA:
            warning_container = QWidget()
            warning_container_layout = QVBoxLayout(warning_container)
            warning_container_layout.setContentsMargins(
                int(DesignSystem.SPACE_24),
                int(DesignSystem.SPACE_12),
                int(DesignSystem.SPACE_24),
                0
            )
            warning_container_layout.setSpacing(0)
            
            if not video_tools_available:
                # Herramientas no instaladas - warning más importante
                warning_banner = self._create_warning_banner(
                    title='Herramientas de video no disponibles',
                    message='No se detectaron <b>ffprobe</b> ni <b>exiftool</b> en el sistema. '
                            'Sin estas herramientas, no es posible validar la duración ni fechas de los videos. '
                            'Los Live Photos se detectan solo por coincidencia de nombres, lo que puede incluir falsos positivos.',
                    icon='alert-circle',
                    action_text='Ver cómo instalar',
                    action_callback=self._open_settings,
                    bg_color=DesignSystem.COLOR_DANGER_BG,
                    border_color=DesignSystem.COLOR_ERROR
                )
            else:
                # Herramientas disponibles pero configuración desactivada
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
            str(group.directory) for group in self.analysis.groups
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
            column_widths=[350, 100, 80, 160, 150, 120],
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
        
        self.filtered_groups = []
        
        for group in self.all_groups:
            # Filtro de búsqueda
            if search_text and search_text not in group.base_name.lower():
                continue
            
            # Filtro por directorio
            if dir_filter != "Todos los directorios" and str(group.directory) != dir_filter:
                continue
            
            # Filtro por origen de fecha
            if not self._matches_source_filter(group.date_source, source_filter):
                continue
            
            self.filtered_groups.append(group)
        
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
        end = min(start + self.LOAD_INCREMENT, len(self.filtered_groups))
        
        for i in range(start, end):
            group = self.filtered_groups[i]
            self._add_group_to_tree(group, i + 1)
        
        self.loaded_count = end
        self._update_pagination_ui()
    
    def _load_all_groups(self):
        """Carga todos los grupos restantes."""
        from PyQt6.QtWidgets import QMessageBox
        
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
    
    def _update_pagination_ui(self):
        """Actualiza la UI de la barra de carga progresiva."""
        if self.pagination_bar:
            self._update_progressive_loading_ui(
                pagination_bar=self.pagination_bar,
                loaded_count=self.loaded_count,
                filtered_count=len(self.filtered_groups),
                total_count=len(self.all_groups),
                load_increment=self.LOAD_INCREMENT
            )
            
            # Actualizar contador
            total = len(self.all_groups)
            filtered = len(self.filtered_groups)
            if filtered == total:
                self.counter_label.setText(f"Mostrando {self.loaded_count} de {filtered} grupos")
            else:
                self.counter_label.setText(f"Mostrando {self.loaded_count} de {filtered} grupos filtrados ({total} total)")
    
    def _add_group_to_tree(self, group: LivePhotoGroup, group_number: int):
        """Añade un grupo como nodo padre expandible con archivos de imagen y video"""
        from .dialog_utils import apply_group_item_style, create_group_tooltip
        
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
        
        # Aplicar estilo unificado de grupo
        apply_group_item_style(group_item, num_columns=6)
        
        # Tooltip informativo
        extra_info = f"{group.image_count} imagen(es) + 1 video MOV"
        if group.date_source:
            extra_info += f"\nFecha común: {group.date_source}"
            if group.date_difference is not None:
                extra_info += f"\nDiferencia: {group.date_difference:.3f}s"
        
        group_item.setToolTip(0, create_group_tooltip(
            group_number,
            f"Live Photo: {group.base_name}",
            extra_info
        ))
        
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
                               f"Carpeta: {img_info.path.parent}<br>"
                               f"Tamaño: {format_size(img_info.size)}<br>"
                               f"Fecha: {img_mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>")
                if img_info.date_source:
                    img_tooltip += f"Origen fecha: {img_info.date_source}<br>"
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
                             f"Carpeta: {group.video_path.parent}<br>"
                             f"Tamaño: {format_size(group.video_size)}<br>"
                             f"Fecha: {video_mtime.strftime('%d/%m/%Y %H:%M:%S')}<br>")
            if group.video_date_source:
                video_tooltip += f"Origen fecha: {group.video_date_source}<br>"
            video_tooltip += "✗ Se eliminará"
            video_item.setToolTip(0, video_tooltip)
        except Exception:
            pass
    
    def _on_item_double_clicked(self, item, column):
        """Maneja doble click: expande grupos o abre archivos"""
        from .dialog_utils import handle_tree_item_double_click
        handle_tree_item_double_click(item, column, self)
    
    def _show_context_menu(self, position):
        """Muestra menú contextual para archivos individuales"""
        from .dialog_utils import show_file_context_menu
        show_file_context_menu(self.tree_widget, position, self)
    
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
        """Abre el diálogo de configuración en la pestaña Análisis inicial"""
        from .settings_dialog import SettingsDialog
        settings_dialog = SettingsDialog(self, initial_tab=1)  # 1 = Análisis inicial tab
        settings_dialog.exec()
