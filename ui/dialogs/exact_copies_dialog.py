from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QGroupBox, QButtonGroup, QRadioButton,
    QCheckBox, QDialogButtonBox, QPushButton,
    QHBoxLayout, QVBoxLayout as QVLayout, QFrame, QTreeWidget, QTreeWidgetItem, QLineEdit,
    QComboBox, QMessageBox, QMenu, QWidget
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices
from config import Config
from services.exact_copies_detector import DuplicateGroup
from utils.format_utils import format_size
from ui import ui_styles
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
        self.setWindowTitle("Gestionar copias exactas")
        self.setModal(True)
        self.resize(1000, 700)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)  # Reducir espaciado general
        
        # Explicación contextual con métricas integradas
        explanation_frame = QFrame()
        explanation_frame.setFrameShape(QFrame.Shape.NoFrame)
        explanation_frame.setStyleSheet("""
            QFrame { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #f8f9fa, stop:1 #e9ecef);
                border: none;
                border-radius: 6px; 
                padding: 8px;
            }
        """)
        explanation_layout = QVBoxLayout(explanation_frame)
        explanation_layout.setSpacing(4)
        explanation_layout.setContentsMargins(10, 6, 10, 6)
        
        # Texto explicativo
        explanation = QLabel(
            "Los duplicados exactos son archivos idénticos (100%). <b>Eliminarlos es seguro.</b>"
        )
        explanation.setWordWrap(True)
        explanation.setTextFormat(Qt.TextFormat.RichText)
        explanation.setStyleSheet(ui_styles.STYLE_DIALOG_EXPLANATION_TEXT)
        explanation_layout.addWidget(explanation)
        
        # Métricas inline compactas (dentro del mismo frame)
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(8)
        
        metrics_data = [
            ("grupos", self.analysis.total_groups, "#2c5aa0"),
            ("archivos", self.analysis.total_duplicates, "#ff9800"),
        ]
        
        for label_text, value, color in metrics_data:
            card = self._create_inline_metric(label_text, value, color)
            metrics_layout.addWidget(card)
        
        # Ahorro potencial destacado
        savings_text = f"{format_size(self.analysis.space_wasted)}"
        savings_label = QLabel(savings_text)
        savings_label.setStyleSheet(ui_styles.STYLE_DIALOG_SAVINGS_GREEN)
        metrics_layout.addWidget(savings_label)
        
        metrics_layout.addStretch()
        explanation_layout.addLayout(metrics_layout)
        
        layout.addWidget(explanation_frame)
        
        # Estrategia de eliminación - EN LÍNEA HORIZONTAL
        strategy_group = QGroupBox("Estrategia")
        strategy_group.setStyleSheet("QGroupBox { font-weight: bold; padding-top: 12px; }")
        strategy_layout = QHBoxLayout(strategy_group)  # HORIZONTAL
        strategy_layout.setContentsMargins(10, 8, 10, 8)
        strategy_layout.setSpacing(15)
        
        self.strategy_buttons = QButtonGroup()
        
        r1 = QRadioButton("Mantener el más antiguo (Recomendado)")
        r1.setChecked(True)
        self.strategy_buttons.addButton(r1, 0)
        strategy_layout.addWidget(r1)
        
        r2 = QRadioButton("Mantener el más reciente")
        self.strategy_buttons.addButton(r2, 1)
        strategy_layout.addWidget(r2)
        
        strategy_layout.addStretch()
        
        self.strategy_buttons.buttonClicked.connect(self._on_strategy_changed)
        layout.addWidget(strategy_group)
        
        # Advertencia si hay muchos grupos
        if len(self.all_groups) > self.WARNING_THRESHOLD:
            warning_many = QLabel(
                f"Hay {len(self.all_groups)} grupos de duplicados. "
                f"Se cargarán inicialmente {self.INITIAL_LOAD} grupos. "
                f"Usa la búsqueda y filtros para encontrar grupos específicos más rápido."
            )
            warning_many.setTextFormat(Qt.TextFormat.RichText)
            warning_many.setWordWrap(True)
            warning_many.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                               stop:0 #f8f9fa, stop:1 #e9ecef);
                    border: none;
                    border-radius: 6px;
                    padding: 10px;
                    color: #495057;
                    font-size: 9pt;
                }
            """)
            layout.addWidget(warning_many)
        
        # Barra de herramientas (búsqueda, filtros y acciones)
        toolbar_layout = QHBoxLayout()
        
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
        
        toolbar_layout.addWidget(search_container)
        
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
        toolbar_layout.addWidget(self.search_input, 2)
        
        # Filtro por tamaño
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(4)
        
        filter_icon = QLabel()
        icon_manager.set_label_icon(filter_icon, 'chart-bar', size=14)
        filter_layout.addWidget(filter_icon)
        
        filter_text = QLabel("Filtrar:")
        filter_layout.addWidget(filter_text)
        
        toolbar_layout.addWidget(filter_container)
        
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
        toolbar_layout.addWidget(self.filter_combo, 1)
        
        # Separador visual
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.VLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        toolbar_layout.addWidget(separator_line)
        
        # Botón "Mostrar Todos" integrado en la barra
        show_all_btn = QPushButton("Ver Todos")
        icon_manager.set_button_icon(show_all_btn, 'eye', size=16)
        show_all_btn.setToolTip("Cargar y mostrar todos los grupos de duplicados")
        show_all_btn.clicked.connect(self._load_all_groups)
        show_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #0f6674;
            }
        """)
        toolbar_layout.addWidget(show_all_btn)
        
        # Información de grupos cargados (inline, sin fondo)
        self.groups_info_label = QLabel()
        self.groups_info_label.setStyleSheet("""
            color: #6c757d;
            font-size: 11px;
            padding: 5px;
        """)
        toolbar_layout.addWidget(self.groups_info_label)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
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
        
        # Botón de paginación (solo "Cargar Más")
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
        
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)
        
        # Cargar grupos iniciales
        self._load_initial_groups()
        
        # Opciones de seguridad
        options_group = QGroupBox("Opciones de Seguridad")
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet("QGroupBox { font-weight: bold; padding-top: 12px; }")
        options_layout = QVLayout(options_group)
        options_layout.setContentsMargins(10, 8, 10, 8)
        options_layout.setSpacing(6)
        
        # Backup checkbox (primero)
        self.add_backup_checkbox(options_layout, "Crear backup antes de eliminar (Recomendado)")
        
        # Simulación checkbox (segundo)
        self.dry_run_checkbox = QCheckBox("Modo simulación (no eliminar archivos realmente)")
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
        buttons = self.make_ok_cancel_buttons(ok_text="Eliminar Ahora")
        # apply danger style to ok button
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        icon_manager.set_button_icon(ok_btn, 'delete', size=16)
        ok_btn.setStyleSheet(ui_styles.STYLE_DANGER_BUTTON)
        layout.addWidget(buttons)
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())
    
    def _create_inline_metric(self, label_text, value, color):
        """Crea una métrica compacta inline con borde de color"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #f8f9fa;
                border-left: 3px solid {color};
                padding: 3px;
                margin: 1px;
                border-radius: 3px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)
        
        # Valor más pequeño
        value_label = QLabel(str(value))
        font = QFont()
        font.setPointSize(12)  # Reducido de 16 a 12
        font.setBold(True)
        value_label.setFont(font)
        value_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        
        # Label descriptivo más pequeño
        desc_label = QLabel(label_text)
        desc_label.setStyleSheet(ui_styles.STYLE_DIALOG_DESC_TINY)
        
        layout.addWidget(value_label)
        layout.addWidget(desc_label)
        
        return frame
    
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
            self.load_more_btn.setText("Todos los Grupos Cargados")
            icon_manager.set_button_icon(self.load_more_btn, 'check', size=16)
        else:
            remaining = len(self.filtered_groups) - self.loaded_count
            self.load_more_btn.setText(f"Cargar {min(self.LOAD_INCREMENT, remaining)} Más Grupos")
            icon_manager.set_button_icon(self.load_more_btn, 'refresh', size=16)
    
    def _add_group_to_tree(self, group: DuplicateGroup, group_number: int):
        """Añade un grupo como nodo padre expandible en el tree"""
        # Nodo padre del grupo
        group_item = QTreeWidgetItem(self.tree_widget)
        file_count = len(group.files)
        # Espacio a liberar = tamaño total - archivo más grande (que se conservará)
        largest_file_size = max(f.stat().st_size for f in group.files)
        space_to_free = group.total_size - largest_file_size
        group_item.setText(0, f"Grupo {group_number} - {file_count} archivos")
        group_item.setText(1, format_size(group.total_size))
        group_item.setText(2, "")
        group_item.setText(3, "")
        group_item.setText(4, f"Libera: {format_size(space_to_free)}")
        
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
                icon_name = "image"
            elif ext in ['.mov', '.mp4', '.avi', '.mkv']:
                icon_name = "video"
            elif ext in ['.heic', '.heif']:
                icon_name = "camera"
            else:
                icon_name = "file"
            
            file_item.setIcon(0, icon_manager.get_icon(icon_name, size=16))
            file_item.setText(0, file_path.name)
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
                file_item.setText(4, "Mantener")
                file_item.setForeground(4, Qt.GlobalColor.darkGreen)
            else:
                file_item.setText(4, "Eliminar")
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
                f"Mostrando grupos {1 if self.loaded_count > 0 else 0}-{self.loaded_count} "
                f"de {total_filtered} grupos filtrados (de {total_original} totales)"
            )
        else:
            # Sin filtros
            self.groups_info_label.setText(
                f"Mostrando grupos {1 if self.loaded_count > 0 else 0}-{self.loaded_count} de {total_original}"
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
            filtered = [g for g in filtered if len(g.files) >= 3]
        elif filter_idx == 5:  # 5+ archivos
            filtered = [g for g in filtered if len(g.files) >= 5]
        
        # Actualizar grupos filtrados y recargar
        self.filtered_groups = filtered
        self.tree_widget.clear()
        self.loaded_count = 0
        
        if len(self.filtered_groups) == 0:
            # No hay resultados
            self.groups_info_label.setText("No se encontraron grupos que coincidan con los filtros")
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
        from .dialog_utils import open_file, open_folder
        
        item = self.tree_widget.itemAt(position)
        if not item:
            return
        
        # Obtener el archivo asociado al item
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not isinstance(file_path, Path):
            return  # Es un grupo padre, no mostrar menú
        
        menu = QMenu(self)
        
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
                    keep_file = min(group.files, key=lambda f: f.stat().st_mtime)
                else:
                    keep_file = max(group.files, key=lambda f: f.stat().st_mtime)
                
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
    
    def accept(self):
        self.accepted_plan = {
            'groups': self.analysis.groups,
            'keep_strategy': self.keep_strategy,
            'create_backup': self.backup_checkbox.isChecked(),
            'dry_run': self.dry_run_checkbox.isChecked()
        }
        super().accept()
