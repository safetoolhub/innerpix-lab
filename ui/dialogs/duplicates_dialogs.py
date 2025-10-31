from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QGroupBox, QButtonGroup, QRadioButton,
    QTableWidget, QTableWidgetItem, QCheckBox, QDialogButtonBox, QPushButton,
    QHBoxLayout, QVBoxLayout as QVLayout, QScrollArea, QWidget, QGridLayout,
    QFrame, QSizePolicy, QProgressBar, QTreeWidget, QTreeWidgetItem, QLineEdit,
    QComboBox, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QPixmap, QDesktopServices, QIcon, QCursor
from config import Config
from services.duplicate_detector import DuplicateGroup
from utils.format_utils import format_size
from ui import styles as ui_styles
from .base_dialog import BaseDialog
from .dialog_utils import show_file_details_dialog
from datetime import datetime


class ExactDuplicatesDialog(BaseDialog):
    """Diálogo para eliminación de duplicados exactos con vista expandible"""
    
    # Constantes para paginación
    INITIAL_LOAD = 50
    LOAD_INCREMENT = 50
    WARNING_THRESHOLD = 200
    
    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.keep_strategy = 'oldest'
        self.accepted_plan = None
        
        # Estado de grupos
        self.all_groups = analysis.groups  # Todos los grupos originales
        self.filtered_groups = analysis.groups  # Grupos después de filtrar
        self.loaded_count = 0  # Cuántos grupos se han cargado en el tree
        
        # Referencias a widgets
        self.tree_widget = None
        self.search_input = None
        self.filter_combo = None
        self.groups_info_label = None
        self.load_more_btn = None
        
        self.init_ui()
    def init_ui(self):
        self.setWindowTitle("Eliminar Duplicados Exactos")
        self.setModal(True)
        self.resize(1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Información general - formato mejorado sin asteriscos
        info_text = (
            f"<div style='padding: 10px;'>"
            f"<p style='margin: 5px 0; font-size: 14px;'>"
            f"📊 <b>Archivos duplicados encontrados:</b> {self.analysis.total_duplicates} archivos en {self.analysis.total_groups} grupos"
            f"</p>"
            f"<p style='margin: 5px 0; font-size: 14px;'>"
            f"💾 <b>Espacio total a liberar:</b> {format_size(self.analysis.space_wasted)}"
            f"</p>"
            f"</div>"
        )
        info = QLabel(info_text)
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        info.setStyleSheet("""
            QLabel {
                background-color: #e7f3ff;
                border: 1px solid #b3d9ff;
                border-radius: 6px;
                padding: 8px;
                color: #212529;
            }
        """)
        layout.addWidget(info)
        
        # Estrategia de eliminación - título completo visible
        strategy_group = QGroupBox("🎯 Estrategia de Eliminación de Duplicados")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_buttons = QButtonGroup()
        
        r1 = QRadioButton("🕐 Mantener el más antiguo (Recomendado)")
        r1.setChecked(True)
        self.strategy_buttons.addButton(r1, 0)
        strategy_layout.addWidget(r1)
        
        r2 = QRadioButton("🕓 Mantener el más reciente")
        self.strategy_buttons.addButton(r2, 1)
        strategy_layout.addWidget(r2)
        
        self.strategy_buttons.buttonClicked.connect(self._on_strategy_changed)
        layout.addWidget(strategy_group)
        
        # Advertencia si hay muchos grupos
        if len(self.all_groups) > self.WARNING_THRESHOLD:
            warning_many = QLabel(
                f"⚠️ <b>Hay {len(self.all_groups)} grupos de duplicados.</b> "
                f"Se cargarán inicialmente {self.INITIAL_LOAD} grupos. "
                f"Usa la búsqueda y filtros para encontrar grupos específicos más rápido."
            )
            warning_many.setTextFormat(Qt.TextFormat.RichText)
            warning_many.setWordWrap(True)
            warning_many.setStyleSheet("""
                background-color: #fff3cd;
                border: 1px solid #ffeeba;
                border-radius: 4px;
                padding: 10px;
                color: #856404;
                font-size: 12px;
            """)
            layout.addWidget(warning_many)
        
        # Barra de búsqueda y filtros
        search_filter_layout = QHBoxLayout()
        
        # Búsqueda
        search_label = QLabel("🔍 Buscar:")
        search_filter_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nombre de archivo o ruta...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        search_filter_layout.addWidget(self.search_input, 2)
        
        # Filtro por tamaño
        filter_label = QLabel("📊 Filtrar:")
        search_filter_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Todos los grupos",
            "Solo grupos >10 MB",
            "Solo grupos >50 MB",
            "Solo grupos >100 MB",
            "Solo grupos con 3+ archivos",
            "Solo grupos con 5+ archivos"
        ])
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.filter_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 13px;
            }
        """)
        search_filter_layout.addWidget(self.filter_combo, 1)
        
        layout.addLayout(search_filter_layout)
        
        # Información de grupos cargados/filtrados
        self.groups_info_label = QLabel()
        self.groups_info_label.setStyleSheet("""
            color: #6c757d;
            font-size: 12px;
            padding: 5px;
            background-color: #f8f9fa;
            border-radius: 3px;
        """)
        layout.addWidget(self.groups_info_label)
        
        # Tree widget para mostrar grupos expandibles
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Archivo/Grupo", "Tamaño", "Fecha Modificación", "Ruta", "Estado"])
        self.tree_widget.setColumnWidth(0, 250)
        self.tree_widget.setColumnWidth(1, 100)
        self.tree_widget.setColumnWidth(2, 150)
        self.tree_widget.setColumnWidth(3, 300)
        self.tree_widget.setColumnWidth(4, 100)
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
            QTreeWidget::item:hover {
                background-color: #e9ecef;
            }
            QTreeWidget::item:selected {
                background-color: #d1e3f5;
            }
        """)
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree_widget)
        
        # Botones de paginación
        pagination_layout = QHBoxLayout()
        
        self.load_more_btn = QPushButton(f"⏬ Cargar {self.LOAD_INCREMENT} Más Grupos")
        self.load_more_btn.clicked.connect(self._load_more_groups)
        self.load_more_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:disabled {
                background-color: #dee2e6;
                color: #6c757d;
            }
        """)
        pagination_layout.addWidget(self.load_more_btn)
        
        load_all_btn = QPushButton("📥 Cargar Todos los Grupos")
        load_all_btn.clicked.connect(self._load_all_groups)
        load_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #0f6674;
            }
        """)
        pagination_layout.addWidget(load_all_btn)
        
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)
        
        # Cargar grupos iniciales
        self._load_initial_groups()
        
        # Opciones de seguridad
        options_group = QGroupBox("⚙️ Opciones de Seguridad")
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        options_layout = QVLayout(options_group)
        
        # Backup checkbox (primero)
        self.add_backup_checkbox(options_layout, "💾 Crear backup antes de eliminar (Recomendado)")
        
        # Simulación checkbox (segundo)
        self.dry_run_checkbox = QCheckBox("🔍 Modo simulación (no eliminar archivos realmente)")
        # Leer configuración para establecer estado por defecto
        from utils.settings_manager import settings_manager
        dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, False)
        # Asegurar que es un booleano
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() in ('true', '1', 'yes')
        self.dry_run_checkbox.setChecked(bool(dry_run_default))
        options_layout.addWidget(self.dry_run_checkbox)
        layout.addWidget(options_group)

        # Advertencia
        warning = QLabel(
            "⚠️ Estos son duplicados exactos (100%). Eliminarlos es seguro."
        )
        warning.setStyleSheet(ui_styles.STYLE_WARNING_LABEL)
        layout.addWidget(warning)

        # Botones
        buttons = self.make_ok_cancel_buttons(ok_text="🗑️ Eliminar Ahora")
        # apply danger style to ok button
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setStyleSheet(ui_styles.STYLE_DANGER_BUTTON)
        layout.addWidget(buttons)
    
    def _on_strategy_changed(self, button):
        """Handle strategy change: only 'oldest' and 'newest' are supported."""
        strategies = {0: 'oldest', 1: 'newest'}
        self.keep_strategy = strategies[self.strategy_buttons.id(button)]
        # Actualizar visualización de estado en el tree
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
        """Carga un lote de grupos en el tree widget"""
        start_idx = self.loaded_count
        end_idx = min(start_idx + count, len(self.filtered_groups))
        
        for i in range(start_idx, end_idx):
            group = self.filtered_groups[i]
            self._add_group_to_tree(group, i + 1)
        
        self.loaded_count = end_idx
        self._update_info_label()
        
        # Deshabilitar botón si ya no hay más grupos
        if self.loaded_count >= len(self.filtered_groups):
            self.load_more_btn.setEnabled(False)
            self.load_more_btn.setText("✓ Todos los Grupos Cargados")
        else:
            remaining = len(self.filtered_groups) - self.loaded_count
            self.load_more_btn.setText(f"⏬ Cargar {min(self.LOAD_INCREMENT, remaining)} Más Grupos")
    
    def _add_group_to_tree(self, group: DuplicateGroup, group_number: int):
        """Añade un grupo como nodo padre expandible en el tree"""
        # Nodo padre del grupo
        group_item = QTreeWidgetItem(self.tree_widget)
        group_item.setText(0, f"📁 Grupo {group_number} - {group.file_count} archivos")
        group_item.setText(1, format_size(group.total_size))
        group_item.setText(2, "")
        group_item.setText(3, "")
        group_item.setText(4, f"Libera: {format_size(group.space_wasted)}")
        
        # Estilo del grupo padre
        font = group_item.font(0)
        font.setBold(True)
        group_item.setFont(0, font)
        group_item.setBackground(0, Qt.GlobalColor.lightGray)
        
        # Determinar qué archivo mantener según estrategia
        if self.keep_strategy == 'oldest':
            keep_file = min(group.files, key=lambda f: f.stat().st_mtime)
        else:  # newest
            keep_file = max(group.files, key=lambda f: f.stat().st_mtime)
        
        # Añadir archivos como hijos
        for file_path in group.files:
            file_item = QTreeWidgetItem(group_item)
            
            # Icono según tipo de archivo
            ext = file_path.suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                icon = "🖼️"
            elif ext in ['.mov', '.mp4', '.avi', '.mkv']:
                icon = "🎬"
            elif ext in ['.heic', '.heif']:
                icon = "📷"
            else:
                icon = "📄"
            
            file_item.setText(0, f"{icon} {file_path.name}")
            file_item.setText(1, format_size(file_path.stat().st_size))
            
            # Fecha de modificación
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            file_item.setText(2, mtime.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Ruta (truncada si es muy larga)
            path_str = str(file_path.parent)
            if len(path_str) > 50:
                path_str = "..." + path_str[-47:]
            file_item.setText(3, path_str)
            
            # Estado: mantener o eliminar
            is_keep = file_path == keep_file
            if is_keep:
                file_item.setText(4, "🔒 Mantener")
                file_item.setForeground(4, Qt.GlobalColor.darkGreen)
            else:
                file_item.setText(4, "🗑️ Eliminar")
                file_item.setForeground(4, Qt.GlobalColor.red)
            
            # Guardar referencia al archivo en el item
            file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            
            # Tooltip con ruta completa
            file_item.setToolTip(0, str(file_path))
            file_item.setToolTip(3, str(file_path))
    
    def _update_status_labels(self):
        """Actualiza las etiquetas de estado según la estrategia seleccionada"""
        # Recorrer todos los grupos y actualizar el estado
        self.tree_widget.clear()
        self.loaded_count = 0
        self._load_initial_groups()
    
    def _update_info_label(self):
        """Actualiza el label de información de grupos"""
        total_filtered = len(self.filtered_groups)
        total_original = len(self.all_groups)
        
        if total_filtered < total_original:
            # Hay filtros aplicados
            self.groups_info_label.setText(
                f"📑 Mostrando grupos {1 if self.loaded_count > 0 else 0}-{self.loaded_count} "
                f"de {total_filtered} grupos filtrados (de {total_original} totales)"
            )
        else:
            # Sin filtros
            self.groups_info_label.setText(
                f"📑 Mostrando grupos {1 if self.loaded_count > 0 else 0}-{self.loaded_count} de {total_original}"
            )
    
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
            filtered = [g for g in filtered if g.file_count >= 3]
        elif filter_idx == 5:  # 5+ archivos
            filtered = [g for g in filtered if g.file_count >= 5]
        
        # Actualizar grupos filtrados y recargar
        self.filtered_groups = filtered
        self.tree_widget.clear()
        self.loaded_count = 0
        
        if len(self.filtered_groups) == 0:
            # No hay resultados
            self.groups_info_label.setText("❌ No se encontraron grupos que coincidan con los filtros")
            self.load_more_btn.setEnabled(False)
        else:
            # Cargar primeros grupos
            self._load_initial_groups()
            self.load_more_btn.setEnabled(self.loaded_count < len(self.filtered_groups))
    
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
        """Muestra el menú contextual para un archivo"""
        from PyQt6.QtWidgets import QMenu
        from .dialog_utils import open_file, open_folder, show_file_details_dialog
        
        item = self.tree_widget.itemAt(position)
        if not item:
            return
        
        # Obtener el archivo asociado al item
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not isinstance(file_path, Path):
            return  # Es un grupo padre, no mostrar menú
        
        menu = QMenu(self)
        
        # Acción: Abrir archivo
        open_action = menu.addAction("📂 Abrir archivo")
        open_action.triggered.connect(lambda: open_file(file_path, self))
        
        # Acción: Abrir carpeta
        open_folder_action = menu.addAction("📁 Abrir carpeta contenedora")
        open_folder_action.triggered.connect(lambda: open_folder(file_path.parent, self))
        
        menu.addSeparator()
        
        # Acción: Ver detalles
        details_action = menu.addAction("ℹ️ Ver detalles del archivo")
        details_action.triggered.connect(lambda: self._show_file_details(file_path))
        
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))
    
    def _show_file_details(self, file_path: Path):
        """Muestra diálogo con detalles del archivo"""
        from .dialog_utils import show_file_details_dialog
        
        # Determinar el estado del archivo (mantener/eliminar)
        # Buscar en qué grupo está este archivo
        status_info = None
        for group in self.filtered_groups:
            if file_path in group.files:
                # Determinar qué archivo se mantiene
                if self.keep_strategy == 'oldest':
                    keep_file = min(group.files, key=lambda f: f.stat().st_mtime)
                else:
                    keep_file = max(group.files, key=lambda f: f.stat().st_mtime)
                
                is_keep = file_path == keep_file
                status_info = {
                    'metadata': {
                        'Estado': '🔒 Se mantendrá' if is_keep else '🗑️ Se eliminará',
                        'Grupo': f'{group.file_count} archivos duplicados',
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
    
    def accept(self):
        self.accepted_plan = {
            'groups': self.analysis.groups,
            'keep_strategy': self.keep_strategy,
            'create_backup': self.backup_checkbox.isChecked(),
            'dry_run': self.dry_run_checkbox.isChecked()
        }
        super().accept()


class SimilarDuplicatesDialog(BaseDialog):
    """Diálogo para revisión de duplicados similares"""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.current_group_index = 0
        self.selections = {}  # {group_index: [files_to_delete]}
        self.accepted_plan = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Revisar Duplicados Similares")
        self.setModal(True)
        self.resize(900, 700)
        layout = QVBoxLayout(self)

        # Advertencia con estilo sutil similar a heic_dialog
        warning_frame = QFrame()
        warning_frame.setFrameShape(QFrame.Shape.NoFrame)
        warning_frame.setStyleSheet("""
            QFrame { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #fff3cd, stop:1 #ffeaa7);
                border-left: 4px solid #f39c12;
                border-radius: 6px; 
                padding: 10px;
            }
        """)
        warning_layout = QVLayout(warning_frame)
        warning_layout.setSpacing(2)
        warning_layout.setContentsMargins(12, 8, 12, 8)
        
        warning = QLabel(
            "⚠️ <b>Estos archivos son similares pero NO idénticos.</b> "
            "Revisa cada grupo cuidadosamente antes de eliminar."
        )
        warning.setTextFormat(Qt.TextFormat.RichText)
        warning.setWordWrap(True)
        warning.setStyleSheet("font-size: 10pt; color: #856404; background: transparent;")
        warning_layout.addWidget(warning)
        
        layout.addWidget(warning_frame)

        # Navegación de grupos
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Anterior")
        self.prev_btn.clicked.connect(self._previous_group)
        nav_layout.addWidget(self.prev_btn)
        self.group_label = QLabel()
        self.group_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_label.setStyleSheet(ui_styles.STYLE_GROUP_LABEL)
        nav_layout.addWidget(self.group_label, 1)
        self.next_btn = QPushButton("Siguiente ▶")
        self.next_btn.clicked.connect(self._next_group)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)

        # Contenedor de grupo actual
        self.group_container = QGroupBox()
        self.group_layout = QVLayout(self.group_container)
        layout.addWidget(self.group_container)

        # Resumen
        summary_group = QGroupBox("📊 Resumen")
        summary_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        summary_group.setMinimumHeight(80)
        # Estilo para que el título quede dentro del cuadro
        summary_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 10pt;
                padding-top: 20px;
                margin-top: 10px;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 8px;
                left: 10px;
                top: 5px;
                color: #2c5aa0;
                font-size: 9pt;
            }
        """)
        summary_layout = QVLayout(summary_group)
        summary_layout.setContentsMargins(15, 15, 15, 15)
        summary_layout.setSpacing(5)
        self.summary_label = QLabel()
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        self.summary_label.setWordWrap(True)
        self.summary_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        summary_layout.addWidget(self.summary_label)
        layout.addWidget(summary_group)

        # Opciones de seguridad
        options_group = QGroupBox("⚙️ Opciones de Seguridad")
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        options_layout = QVLayout(options_group)
        
        # Backup checkbox (primero)
        self.add_backup_checkbox(options_layout, "💾 Crear backup antes de eliminar (Recomendado)")
        
        # Simulación checkbox (segundo)
        self.dry_run_checkbox = QCheckBox("🔍 Modo simulación (no eliminar archivos realmente)")
        # Leer configuración para establecer estado por defecto
        from utils.settings_manager import settings_manager
        dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, False)
        # Asegurar que es un booleano
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() in ('true', '1', 'yes')
        self.dry_run_checkbox.setChecked(bool(dry_run_default))
        options_layout.addWidget(self.dry_run_checkbox)
        layout.addWidget(options_group)

        # Botones
        buttons = self.make_ok_cancel_buttons(ok_text="🗑️ Eliminar Seleccionados", ok_enabled=False)
        self.ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        layout.addWidget(buttons)

        # Cargar primer grupo
        self._load_group(0)

    def _load_group(self, index):
        """Carga y muestra un grupo específico con miniaturas"""
        if not 0 <= index < len(self.analysis.groups):
            return
        self.current_group_index = index
        group = self.analysis.groups[index]

        # Actualizar navegación
        total_groups = len(self.analysis.groups)
        self.group_label.setText(f"Grupo {index + 1} de {total_groups}")
        # Con navegación circular, los botones siempre están habilitados
        self.prev_btn.setEnabled(True)
        self.next_btn.setEnabled(True)

        # Limpiar layout anterior
        for i in reversed(range(self.group_layout.count())):
            widget = self.group_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Métrica de similitud visual
        similarity_widget = self._create_similarity_widget(group)
        self.group_layout.addWidget(similarity_widget)

        # Info del grupo
        info_label = QLabel(
            f"<b>Archivos:</b> {group.file_count} | "
            f"<b>Tamaño total:</b> {format_size(group.total_size)}"
        )
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setStyleSheet(ui_styles.STYLE_PANEL_LABEL)
        self.group_layout.addWidget(info_label)

        # Advertencia si hay demasiadas imágenes
        max_thumbnails = 20
        if len(group.files) > max_thumbnails:
            warning_label = QLabel(
                f"⚠️ Este grupo tiene {len(group.files)} imágenes. "
                f"Para mejor rendimiento, usa el scroll para navegar."
            )
            warning_label.setStyleSheet(ui_styles.STYLE_DIALOG_WARNING_ORANGE)
            warning_label.setWordWrap(True)
            self.group_layout.addWidget(warning_label)

        # Crear área con scroll para las miniaturas
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Widget contenedor de miniaturas
        thumbnails_widget = QWidget()
        thumbnails_layout = QGridLayout(thumbnails_widget)
        thumbnails_layout.setSpacing(10)

        previous_selection = self.selections.get(index, [])

        # Configurar grid (máximo 5 columnas)
        max_columns = 5
        for row_idx, file_path in enumerate(group.files):
            row = row_idx // max_columns
            col = row_idx % max_columns

            # Frame contenedor para cada imagen
            frame = QFrame()
            frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            frame.setLineWidth(1)
            frame_layout = QVLayout(frame)
            frame_layout.setSpacing(0)
            frame_layout.setContentsMargins(0, 0, 0, 0)

            # === SECCIÓN 1: CHECKBOX DE ELIMINACIÓN ===
            delete_section = QWidget()
            delete_section_layout = QVLayout(delete_section)
            delete_section_layout.setContentsMargins(10, 10, 10, 10)
            delete_section_layout.setSpacing(0)
            
            checkbox = QCheckBox("Eliminar este archivo")
            checkbox.setChecked(file_path in previous_selection)
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-weight: 600;
                    font-size: 11px;
                    padding: 5px;
                    color: #DC3545;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #DC3545;
                    border-radius: 4px;
                    background-color: white;
                }
                QCheckBox::indicator:checked {
                    background-color: #DC3545;
                    border-color: #DC3545;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTMuNSA0TDYgMTEuNSAyLjUgOCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
                }
                QCheckBox::indicator:hover {
                    border-color: #BB2D3B;
                }
            """)
            checkbox.stateChanged.connect(lambda state, f=file_path: self._on_selection_changed(f, state))
            delete_section_layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
            
            # Diseño más limpio: borde rojo sutil en lugar de fondo amarillo
            delete_section.setStyleSheet("""
                QWidget {
                    background-color: #FFFFFF;
                    padding: 10px;
                    border-bottom: 2px solid #F8D7DA;
                }
            """)
            frame_layout.addWidget(delete_section)

            # === SECCIÓN 2: MINIATURA (PREVIEW) ===
            preview_section = QWidget()
            preview_section_layout = QVLayout(preview_section)
            preview_section_layout.setContentsMargins(5, 5, 5, 5)
            preview_section_layout.setSpacing(3)
            
            thumbnail_label, is_video = self._create_thumbnail(file_path)
            
            # Si es video, añadir indicador visual
            if is_video:
                video_indicator = QLabel("🎬 VIDEO - Frame de comparación")
                video_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
                video_indicator.setStyleSheet("""
                    background-color: #6F42C1;
                    color: white;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 3px;
                    border-radius: 3px;
                    margin-bottom: 3px;
                """)
                preview_section_layout.addWidget(video_indicator)
            
            if thumbnail_label:
                thumbnail_label.mousePressEvent = lambda event, f=file_path: self._open_file(f)
                thumbnail_label.setCursor(Qt.CursorShape.PointingHandCursor)
                thumbnail_label.setToolTip(f"Clic para abrir: {file_path.name}")
                preview_section_layout.addWidget(thumbnail_label, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                # Si no se puede cargar la imagen, mostrar placeholder
                no_preview = QLabel("❌ Sin vista previa")
                no_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_preview.setStyleSheet("color: #6C757D; font-size: 10px; font-style: italic;")
                preview_section_layout.addWidget(no_preview)
            
            preview_section.setStyleSheet("""
                QWidget {
                    background-color: #E9ECEF;
                    padding: 10px;
                }
            """)
            frame_layout.addWidget(preview_section)

            # === SECCIÓN 3: INFORMACIÓN COMPACTA DEL ARCHIVO (con menú contextual) ===
            info_section = QWidget()
            info_section.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            info_section.customContextMenuRequested.connect(
                lambda pos, f=file_path: self._show_file_context_menu(pos, f, info_section)
            )
            info_section.setCursor(Qt.CursorShape.PointingHandCursor)
            info_section.setToolTip("Clic derecho para más opciones")
            
            info_section_layout = QVLayout(info_section)
            info_section_layout.setContentsMargins(10, 8, 10, 8)
            info_section_layout.setSpacing(3)
            
            from datetime import datetime
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # Nombre del archivo (con icono)
            name_label = QLabel(f"📄 <b>{file_path.name[:25]}{'...' if len(file_path.name) > 25 else ''}</b>")
            name_label.setTextFormat(Qt.TextFormat.RichText)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setStyleSheet("font-size: 11px; color: #212529; background: transparent;")
            info_section_layout.addWidget(name_label)
            
            # Tamaño y fecha en una línea compacta
            details_label = QLabel(
                f"💾 {format_size(file_path.stat().st_size)} • "
                f"📅 {mtime.strftime('%Y-%m-%d %H:%M')}"
            )
            details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            details_label.setStyleSheet("font-size: 9px; color: #6C757D; background: transparent;")
            info_section_layout.addWidget(details_label)
            
            # Estilo con hover para indicar que es clickeable
            info_section.setStyleSheet("""
                QWidget {
                    background-color: #F8F9FA;
                    padding: 8px;
                    border-radius: 4px;
                }
                QWidget:hover {
                    background-color: #E9ECEF;
                }
            """)
            frame_layout.addWidget(info_section)

            # Destacar el frame si está seleccionado
            if file_path in previous_selection:
                frame.setStyleSheet("""
                    QFrame {
                        border: 2px solid #DC3545;
                        background-color: #FFFFFF;
                        border-radius: 6px;
                    }
                """)
            else:
                frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #CED4DA;
                        background-color: #FFFFFF;
                        border-radius: 6px;
                    }
                """)

            # Conectar cambios de selección para actualizar el estilo del frame
            checkbox.stateChanged.connect(
                lambda state, fr=frame, f=file_path: self._update_frame_style(fr, f, state)
            )

            thumbnails_layout.addWidget(frame, row, col)

        scroll_area.setWidget(thumbnails_widget)
        scroll_area.setMinimumHeight(400)
        self.group_layout.addWidget(scroll_area)

        self._update_summary()

    def _create_similarity_widget(self, group) -> QWidget:
        """Crea un widget visual para mostrar el grado de similitud"""
        container = QWidget()
        layout = QVLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Título
        title_label = QLabel("🔍 Grado de Similitud")
        title_label.setStyleSheet(ui_styles.STYLE_DIALOG_TITLE_BOLD)
        layout.addWidget(title_label)

        # Barra de progreso visual
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(int(group.similarity_score))
        progress_bar.setTextVisible(True)
        progress_bar.setFormat(f"{group.similarity_score:.1f}%")
        progress_bar.setMinimumHeight(30)

        # Estilo de la barra según el nivel de similitud
        similarity_color, similarity_text, similarity_icon = self._get_similarity_level(group.similarity_score)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #BDC3C7;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 13px;
                background-color: #ECF0F1;
            }}
            QProgressBar::chunk {{
                background-color: {similarity_color};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(progress_bar)

        # Interpretación del nivel
        interpretation_label = QLabel(
            f"{similarity_icon} <b>Nivel:</b> {similarity_text}"
        )
        interpretation_label.setTextFormat(Qt.TextFormat.RichText)
        interpretation_label.setStyleSheet(f"""
            color: {similarity_color};
            font-size: 13px;
            padding: 5px;
            background-color: {similarity_color}20;
            border-radius: 5px;
            border: 1px solid {similarity_color};
        """)
        layout.addWidget(interpretation_label)

        # Descripción explicativa
        description = self._get_similarity_description(group.similarity_score)
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(ui_styles.STYLE_DIALOG_DESC_MUTED)
        layout.addWidget(desc_label)

        container.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
            }
        """)

        return container

    def _get_similarity_level(self, score: float) -> tuple:
        """Retorna (color, texto, icono) según el nivel de similitud"""
        if score >= 95:
            return ("#27AE60", "Casi Idénticas", "🟢")
        elif score >= 85:
            return ("#3498DB", "Muy Similares", "🔵")
        elif score >= 75:
            return ("#F39C12", "Similares", "🟡")
        elif score >= 65:
            return ("#E67E22", "Moderadamente Similares", "🟠")
        else:
            return ("#E74C3C", "Poco Similares", "🔴")

    def _get_similarity_description(self, score: float) -> str:
        """Retorna una descripción explicativa del nivel de similitud"""
        if score >= 95:
            return "Las imágenes son prácticamente idénticas. Diferencias mínimas o imperceptibles."
        elif score >= 85:
            return "Las imágenes son muy parecidas. Pueden tener pequeñas diferencias en calidad, resolución o edición."
        elif score >= 75:
            return "Las imágenes comparten características significativas pero tienen diferencias notables."
        elif score >= 65:
            return "Las imágenes tienen similitudes pero también diferencias considerables. Revisa cuidadosamente."
        else:
            return "Las imágenes tienen pocas similitudes. Verifica que realmente sean duplicados antes de eliminar."

    def _create_thumbnail(self, file_path: Path) -> tuple:
        """Crea una miniatura para un archivo de imagen o video.
        
        Returns:
            tuple: (QLabel con la miniatura, bool indicando si es video)
        """
        try:
            # Extensiones soportadas
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.heic', '.heif'}
            video_extensions = {'.mov', '.mp4', '.avi', '.mkv', '.m4v', '.webm'}
            
            file_ext = file_path.suffix.lower()
            is_video = file_ext in video_extensions
            
            # Si no es imagen ni video, retornar None
            if file_ext not in image_extensions and file_ext not in video_extensions:
                return None, False
            
            pixmap = None
            
            # Para videos, extraer un frame fijo (frame 1 segundo)
            if is_video:
                try:
                    import cv2
                    import numpy as np
                    from PyQt6.QtGui import QImage
                    
                    # Abrir video
                    cap = cv2.VideoCapture(str(file_path))
                    
                    # Ir al frame del segundo 1 (frame 30 aprox si es 30fps)
                    # Usamos frame fijo para que sea consistente entre comparaciones
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
                    
                    # Leer frame
                    ret, frame = cap.read()
                    cap.release()
                    
                    if ret:
                        # Convertir de BGR (OpenCV) a RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # Convertir a QImage
                        h, w, ch = frame_rgb.shape
                        bytes_per_line = ch * w
                        qimage = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                        
                        # Convertir a QPixmap
                        pixmap = QPixmap.fromImage(qimage)
                    
                except ImportError:
                    # OpenCV no disponible, intentar con otro método
                    pass
                except Exception:
                    pass
            else:
                # Para imágenes, intentar cargar con QPixmap
                pixmap = QPixmap(str(file_path))
                
                # Si QPixmap falla (puede pasar con HEIC), intentar con pillow
                if pixmap.isNull():
                    try:
                        from PIL import Image
                        from PyQt6.QtGui import QImage
                        import io
                        
                        # Cargar con Pillow y convertir a QPixmap
                        img = Image.open(str(file_path))
                        img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                        
                        # Convertir PIL Image a QPixmap
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        
                        qimage = QImage()
                        qimage.loadFromData(img_byte_arr.read())
                        pixmap = QPixmap.fromImage(qimage)
                    except ImportError:
                        pass
                    except Exception:
                        pass

            if pixmap is None or pixmap.isNull():
                return None, is_video

            # Redimensionar manteniendo aspecto (150x150 máximo)
            scaled_pixmap = pixmap.scaled(
                Config.THUMBNAIL_SIZE, Config.THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            label = QLabel()
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedSize(Config.THUMBNAIL_SIZE, Config.THUMBNAIL_SIZE)
            label.setStyleSheet(ui_styles.STYLE_DIALOG_LABEL_DISABLED)
            return label, is_video
        except Exception:
            return None, False

    def _update_frame_style(self, frame: QFrame, file_path: Path, state):
        """Actualiza el estilo visual del frame según el estado de selección"""
        if state == Qt.CheckState.Checked:
            frame.setStyleSheet("""
                QFrame {
                    border: 2px solid #DC3545;
                    background-color: #FFFFFF;
                    border-radius: 6px;
                }
            """)
        else:
            frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #CED4DA;
                    background-color: #FFFFFF;
                    border-radius: 6px;
                }
            """)

    def _on_selection_changed(self, file_path, state):
        """Maneja cambios en la selección"""
        if self.current_group_index not in self.selections:
            self.selections[self.current_group_index] = []
        # Qt6 emite state como int: 0 (Unchecked), 2 (Checked)
        if state == Qt.CheckState.Checked.value or state == Qt.CheckState.Checked:
            if file_path not in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].append(file_path)
        else:
            if file_path in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].remove(file_path)
        self._update_summary()

    def _previous_group(self):
        """Navega al grupo anterior (circular: desde el primero va al último)"""
        total_groups = len(self.analysis.groups)
        if self.current_group_index == 0:
            # Estamos en el primero, ir al último
            self._load_group(total_groups - 1)
        else:
            self._load_group(self.current_group_index - 1)

    def _next_group(self):
        """Navega al grupo siguiente (circular: desde el último va al primero)"""
        total_groups = len(self.analysis.groups)
        if self.current_group_index >= total_groups - 1:
            # Estamos en el último, ir al primero
            self._load_group(0)
        else:
            self._load_group(self.current_group_index + 1)

    def _update_summary(self):
        """Actualiza el resumen de archivos seleccionados"""
        total_selected = sum(len(files) for files in self.selections.values())
        total_size = 0
        for files in self.selections.values():
            total_size += sum(f.stat().st_size for f in files)
        self.summary_label.setText(
            f"<b>Archivos seleccionados:</b> {total_selected} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Espacio a liberar:</b> {format_size(total_size)}"
        )
        self.ok_btn.setEnabled(total_selected > 0)

    def accept(self):
        # Crear grupos filtrados solo con archivos a eliminar
        groups_to_process = []
        for group_idx, files_to_delete in self.selections.items():
            if files_to_delete:
                original_group = self.analysis.groups[group_idx]
                groups_to_process.append(DuplicateGroup(
                    hash_value=original_group.hash_value,
                    files=files_to_delete,
                    total_size=sum(f.stat().st_size for f in files_to_delete),
                    similarity_score=original_group.similarity_score
                ))
        self.accepted_plan = {
            'groups': groups_to_process,
            'keep_strategy': 'manual',
            'create_backup': self.backup_checkbox.isChecked(),
            'dry_run': self.dry_run_checkbox.isChecked()
        }
        super().accept()

    def _open_file(self, file_path: Path):
        """Abre un archivo con la aplicación predeterminada del sistema operativo"""
        if file_path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Archivo no encontrado", f"No se encontró el archivo:\n{file_path}")
    
    def _show_file_context_menu(self, position, file_path: Path, widget: QWidget):
        """Muestra menú contextual para un archivo con opciones de ver detalles"""
        menu = QMenu(self)
        
        # Opción para ver detalles del archivo
        details_action = menu.addAction("ℹ️ Ver detalles del archivo")
        details_action.triggered.connect(lambda: self._show_file_details(file_path))
        
        menu.addSeparator()
        
        # Opción para abrir el archivo
        open_action = menu.addAction("🔍 Abrir archivo")
        open_action.triggered.connect(lambda: self._open_file(file_path))
        
        # Opción para abrir la carpeta
        from .dialog_utils import open_folder
        open_folder_action = menu.addAction("📁 Abrir carpeta")
        open_folder_action.triggered.connect(lambda: open_folder(file_path.parent, self))
        
        # Mostrar el menú en la posición exacta del cursor
        menu.exec(QCursor.pos())
    
    def _show_file_details(self, file_path: Path):
        """Muestra diálogo con detalles del archivo"""
        # Obtener el grupo actual para incluir contexto
        current_group = self.analysis.groups[self.current_group_index]
        
        # Preparar información adicional
        additional_info = {
            'file_type': Config.get_file_type(file_path),
            'metadata': {
                'Grupo': f'{self.current_group_index + 1} de {len(self.analysis.groups)}',
                'Similitud del grupo': f'{current_group.similarity_score:.1f}%',
                'Archivos en grupo': str(current_group.file_count),
                'Tamaño total del grupo': format_size(current_group.total_size),
            }
        }
        
        # Mostrar diálogo de detalles usando la utilidad
        show_file_details_dialog(file_path, self, additional_info)
