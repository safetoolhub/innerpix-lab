"""
Diálogo de Organización de Archivos - Rediseñado
Incluye explicaciones claras, vista de archivos con TreeWidget y optimización para miles de fotos
"""
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QVBoxLayout as QVLayout,
    QDialogButtonBox, QCheckBox, QLabel, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QComboBox, QPushButton, QFrame, QApplication, QMenu, QWidget
)
from PyQt6.QtGui import QColor, QFont, QCursor
from PyQt6.QtCore import Qt, QTimer

from config import Config
from utils.format_utils import format_size
from utils.date_utils import get_file_date
from ui import ui_styles
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from .base_dialog import BaseDialog


class FileOrganizationDialog(BaseDialog):
    """Diálogo profesional para organización de archivos con UX mejorado"""
    
    # Configuración de paginación
    ITEMS_PER_PAGE = 200
    MAX_ITEMS_WITHOUT_PAGINATION = 500

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.accepted_plan = None
        
        # Datos filtrados
        self.filtered_moves = list(analysis.move_plan)
        
        # Paginación
        self.current_page = 0
        self.total_pages = 0
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Organización de Archivos")
        self.setModal(True)
        self.resize(1200, 750)
        main_layout = QVBoxLayout(self)
        
        # Explicación clara según tipo de organización
        explanation = self._create_explanation_section()
        main_layout.addWidget(explanation)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        
        # Resumen compacto con métricas
        metrics = self._create_metrics_section()
        main_layout.addLayout(metrics)
        
        # Información de carpetas a crear (si aplica)
        folders_info = self._create_folders_info()
        if folders_info:
            main_layout.addWidget(folders_info)
        
        # Barra de herramientas (filtros y búsqueda)
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)
        
        # TreeWidget de archivos a mover
        self.files_tree = self._create_tree_widget()
        main_layout.addWidget(self.files_tree)
        
        # Controles de paginación
        self.pagination_widget = self._create_pagination_controls()
        main_layout.addWidget(self.pagination_widget)
        
        # Opciones de seguridad
        options_group = self._create_options_group()
        main_layout.addWidget(options_group)
        
        # Botones
        ok_enabled = self.analysis.total_files_to_move > 0
        if ok_enabled:
            size_formatted = format_size(self.analysis.total_size_to_move)
            ok_text = f"Organizar Archivos ({self.analysis.total_files_to_move} archivos, {size_formatted})"
        else:
            ok_text = None
        self.buttons = self.make_ok_cancel_buttons(ok_text=ok_text, ok_enabled=ok_enabled)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        main_layout.addWidget(self.buttons)
        
        # Actualizar vista inicial
        self._update_tree()
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())

    def _create_explanation_section(self):
        """Crea sección de explicación clara según tipo de organización"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.NoFrame)
        frame.setStyleSheet("""
            QFrame { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #f8f9fa, stop:1 #e9ecef);
                border: none;
                border-radius: 6px; 
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(2)
        layout.setContentsMargins(12, 8, 12, 8)
        
        org_type = self.analysis.organization_type
        
        # Explicación según tipo
        if org_type == 'by_month':
            icon_name = "calendar_month"
            title = "Organización por Mes"
            description = (
                "Organizará los archivos en <b>carpetas mensuales (YYYY_MM)</b> basándose en la fecha más antigua de cada archivo. "
                "Archivos sin fecha se colocarán en una carpeta especial. "
                "Ejemplo: <code>IMG_2023_01_15_001.jpg</code> → <code>2023_01/</code>"
            )
        elif org_type == 'whatsapp_separate':
            icon_name = "mobile"
            title = "Separación de WhatsApp"
            description = (
                "Separará los <b>archivos de WhatsApp</b> en una carpeta dedicada y moverá el resto al directorio raíz. "
                "Identifica archivos con patrones: <code>IMG-YYYYMMDD-WA####</code>, <code>VID-YYYYMMDD-WA####</code>, "
                "o desde carpetas <code>WhatsApp/</code>."
            )
        else:  # to_root
            icon_name = "folder"
            title = "Mover Todo a Raíz"
            description = (
                "Moverá <b>todos los archivos al directorio raíz</b> eliminando la estructura de subdirectorios. "
                "Los conflictos de nombres se resolverán automáticamente añadiendo sufijos <code>_001</code>, <code>_002</code>, etc. "
                "Los subdirectorios vacíos se pueden eliminar opcionalmente."
            )
        
        # Crear contenedor con icono y texto
        explanation_container = QWidget()
        explanation_layout = QHBoxLayout(explanation_container)
        explanation_layout.setContentsMargins(0, 0, 0, 0)
        explanation_layout.setSpacing(8)
        
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, size=20)
        explanation_layout.addWidget(icon_label)
        
        text_label = QLabel(f"<b>{title}</b><br>{description}")
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.TextFormat.RichText)
        text_label.setStyleSheet(ui_styles.STYLE_HEIC_EXPLANATION)
        explanation_layout.addWidget(text_label, 1)
        
        layout.addWidget(explanation_container)
        
        return frame
    
    def _create_metrics_section(self):
        """Crea panel de métricas compacto"""
        layout = QHBoxLayout()
        
        # Métricas principales
        metrics_data = [
            ("Total archivos", self.analysis.total_files_to_move, "#2c5aa0"),
            ("Subdirectorios", len(self.analysis.subdirectories), "#9c27b0"),
            ("Tamaño total", format_size(self.analysis.total_size_to_move), "#ff9800"),
        ]
        
        for label_text, value, color in metrics_data:
            card = self._create_inline_metric(label_text, value, color)
            layout.addWidget(card)
        
        # Métricas por tipo de archivo
        if self.analysis.files_by_type:
            types_text = " | ".join([
                f"{file_type}: {count}" 
                for file_type, count in sorted(self.analysis.files_by_type.items())
            ])
            types_label = QLabel(f"{types_text}")
            types_label.setStyleSheet(ui_styles.STYLE_ORG_TYPES_LABEL)
            layout.addWidget(types_label)
        
        # Advertencia de conflictos
        if self.analysis.potential_conflicts > 0:
            conflicts_label = QLabel(f"{self.analysis.potential_conflicts} conflictos de nombres")
            conflicts_label.setStyleSheet(ui_styles.STYLE_ORG_CONFLICTS_LABEL)
            layout.addWidget(conflicts_label)
        
        layout.addStretch()
        return layout
    
    def _create_inline_metric(self, label_text, value, color):
        """Crea una métrica compacta inline"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #f8f9fa;
                border-left: 3px solid {color};
                padding: 5px;
                margin: 2px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 5, 8, 5)
        
        # Valor
        value_label = QLabel(str(value))
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        value_label.setFont(font)
        value_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        
        # Label descriptivo
        desc_label = QLabel(label_text)
        desc_label.setStyleSheet("font-size: 10px; color: #666; background: transparent; border: none;")
        
        layout.addWidget(value_label)
        layout.addWidget(desc_label)
        
        return frame
    
    def _create_folders_info(self):
        """Crea sección de información de carpetas a crear"""
        if not self.analysis.folders_to_create:
            return None
        
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { 
                background-color: #e3f2fd; 
                border-left: 3px solid #2196f3;
                border-radius: 3px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        
        folders = sorted(self.analysis.folders_to_create)
        count = len(folders)
        
        if count <= 10:
            folders_text = ", ".join(folders)
        else:
            folders_text = ", ".join(folders[:10]) + f"... (+{count - 10} más)"
        
        label = QLabel(f"Se crearán {count} carpetas: <b>{folders_text}</b>")
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setStyleSheet("font-size: 10px; color: #1976d2; background: transparent;")
        layout.addWidget(label)
        
        return frame
    
    def _create_toolbar(self):
        """Crea barra de herramientas con filtros"""
        toolbar = QHBoxLayout()
        
        # Búsqueda
        search_icon = QLabel()
        icon_manager.set_label_icon(search_icon, 'search', size=16)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setMaximumWidth(200)
        toolbar.addWidget(search_icon)
        toolbar.addWidget(self.search_input)
        
        toolbar.addWidget(QLabel("|"))
        
        # Filtro por tipo
        type_label = QLabel("Tipo:")
        self.type_combo = QComboBox()
        types = ["Todos"] + sorted(list(self.analysis.files_by_type.keys()))
        self.type_combo.addItems(types)
        self.type_combo.currentTextChanged.connect(self._apply_filters)
        self.type_combo.setMaximumWidth(120)
        toolbar.addWidget(type_label)
        toolbar.addWidget(self.type_combo)
        
        # Filtro por subdirectorio origen (solo para to_root y whatsapp_separate)
        if self.analysis.organization_type in ['to_root', 'whatsapp_separate']:
            subdir_label = QLabel("Origen:")
            self.subdir_combo = QComboBox()
            subdirs = ["Todos"] + sorted(list(self.analysis.subdirectories.keys()))
            self.subdir_combo.addItems(subdirs)
            self.subdir_combo.currentTextChanged.connect(self._apply_filters)
            self.subdir_combo.setMaximumWidth(250)
            toolbar.addWidget(subdir_label)
            toolbar.addWidget(self.subdir_combo)
        else:
            self.subdir_combo = None
        
        # Filtro solo conflictos
        self.conflicts_checkbox = QCheckBox("Solo conflictos")
        self.conflicts_checkbox.stateChanged.connect(self._apply_filters)
        toolbar.addWidget(self.conflicts_checkbox)
        
        # Botón limpiar
        clear_btn = QPushButton("Limpiar")
        icon_manager.set_button_icon(clear_btn, 'close', size=16)
        clear_btn.clicked.connect(self._clear_filters)
        clear_btn.setMaximumWidth(80)
        toolbar.addWidget(clear_btn)
        
        # Contador
        self.counter_label = QLabel()
        self.counter_label.setStyleSheet("font-weight: bold; color: #2c5aa0; margin-left: 10px;")
        toolbar.addWidget(self.counter_label)
        
        toolbar.addStretch()
        return toolbar
    
    def _create_tree_widget(self):
        """Crea TreeWidget con agrupación según tipo de organización"""
        tree = QTreeWidget()
        
        # Configurar columnas según tipo de organización
        if self.analysis.organization_type == 'to_root':
            tree.setHeaderLabels(["Archivo", "Origen", "Tamaño", "Estado"])
        elif self.analysis.organization_type == 'by_month':
            tree.setHeaderLabels(["Archivo", "Fecha", "Origen", "Tamaño"])
        else:  # whatsapp_separate
            tree.setHeaderLabels(["Archivo", "Origen", "Destino", "Tamaño"])
        
        tree.setAlternatingRowColors(True)
        tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tree.itemDoubleClicked.connect(self._on_file_double_clicked)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._show_context_menu)
        tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                outline: none;
            }
            QTreeWidget::item {
                border: none;
                outline: none;
                padding: 2px;
            }
            QTreeWidget::item:hover {
                background-color: #f0f7ff;
            }
            QToolTip {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                padding: 8px;
                font-size: 10pt;
                border-radius: 4px;
            }
        """)
        tree.setToolTip(
            "Doble clic en archivo para abrirlo\n"
            "Clic derecho para ver detalles y opciones\n"
            "Los archivos con conflictos de nombre se marcan especialmente"
        )
        
        # Ajustar columnas según tipo de organización
        header = tree.header()
        header.setStretchLastSection(False)
        
        # Anchos optimizados por tipo
        if self.analysis.organization_type == 'to_root':
            # TO_ROOT: ["Archivo", "Origen", "Tamaño", "Estado"]
            tree.setColumnWidth(0, 380)  # Archivo
            tree.setColumnWidth(1, 180)  # Origen
            tree.setColumnWidth(2, 100)  # Tamaño
            tree.setColumnWidth(3, 250)  # Estado (más ancho para conflictos)
        elif self.analysis.organization_type == 'by_month':
            # BY_MONTH: ["Archivo", "Fecha", "Origen", "Tamaño"]
            tree.setColumnWidth(0, 400)  # Archivo
            tree.setColumnWidth(1, 120)  # Fecha
            tree.setColumnWidth(2, 200)  # Origen
            tree.setColumnWidth(3, 100)  # Tamaño
        else:  # whatsapp_separate
            # WHATSAPP: ["Archivo", "Origen", "Destino", "Tamaño"]
            tree.setColumnWidth(0, 400)  # Archivo
            tree.setColumnWidth(1, 200)  # Origen
            tree.setColumnWidth(2, 150)  # Destino
            tree.setColumnWidth(3, 100)  # Tamaño
        
        return tree
    
    def _create_pagination_controls(self):
        """Crea controles de paginación"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.StyledPanel)
        widget.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 3px; }")
        layout = QHBoxLayout(widget)
        
        self.first_page_btn = QPushButton("⏮ Primera")
        self.first_page_btn.clicked.connect(self._go_first_page)
        self.first_page_btn.setMaximumWidth(100)
        layout.addWidget(self.first_page_btn)
        
        self.prev_page_btn = QPushButton("◀ Anterior")
        self.prev_page_btn.clicked.connect(self._go_prev_page)
        self.prev_page_btn.setMaximumWidth(100)
        layout.addWidget(self.prev_page_btn)
        
        self.page_label = QLabel()
        self.page_label.setStyleSheet("font-weight: bold; padding: 0 20px;")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)
        
        self.next_page_btn = QPushButton("Siguiente ▶")
        self.next_page_btn.clicked.connect(self._go_next_page)
        self.next_page_btn.setMaximumWidth(100)
        layout.addWidget(self.next_page_btn)
        
        self.last_page_btn = QPushButton("Última ⏭")
        self.last_page_btn.clicked.connect(self._go_last_page)
        self.last_page_btn.setMaximumWidth(100)
        layout.addWidget(self.last_page_btn)
        
        layout.addStretch()
        
        layout.addWidget(QLabel("Items por página:"))
        self.items_per_page_combo = QComboBox()
        self.items_per_page_combo.addItems(["100", "200", "500", "Todos"])
        self.items_per_page_combo.setCurrentText("200")
        self.items_per_page_combo.currentTextChanged.connect(self._change_items_per_page)
        self.items_per_page_combo.setMaximumWidth(100)
        layout.addWidget(self.items_per_page_combo)
        
        widget.setVisible(False)
        return widget
    
    def _create_options_group(self):
        """Crea grupo de opciones de seguridad"""
        options_group = QGroupBox("Opciones de Seguridad")
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        options_layout = QVLayout()
        
        # Backup checkbox (primero)
        self.add_backup_checkbox(options_layout, "Crear backup antes de mover (Recomendado)")
        
        # Simulación checkbox (segundo)
        self.dry_run_checkbox = QCheckBox("Modo simulación (no mover archivos realmente)")
        # Leer configuración para establecer estado por defecto
        from utils.settings_manager import settings_manager
        dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, False)
        # Asegurar que es un booleano
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() in ('true', '1', 'yes')
        self.dry_run_checkbox.setChecked(bool(dry_run_default))
        options_layout.addWidget(self.dry_run_checkbox)
        
        # Cleanup checkbox (tercero)
        self.cleanup_checkbox = QCheckBox("Eliminar directorios vacíos al finalizar")
        self.cleanup_checkbox.setChecked(True)  # Por defecto activado
        options_layout.addWidget(self.cleanup_checkbox)
    
    def _apply_filters(self):
        """Aplica filtros a la lista de movimientos"""
        search_text = self.search_input.text().lower()
        type_filter = self.type_combo.currentText()
        subdir_filter = self.subdir_combo.currentText() if self.subdir_combo else "Todos"
        show_only_conflicts = self.conflicts_checkbox.isChecked()
        
        self.filtered_moves = []
        
        for move in self.analysis.move_plan:
            # Filtro de búsqueda
            if search_text and search_text not in move.original_name.lower():
                continue
            
            # Filtro por tipo
            if type_filter != "Todos" and move.file_type != type_filter:
                continue
            
            # Filtro por subdirectorio origen
            if subdir_filter != "Todos" and move.subdirectory != subdir_filter:
                continue
            
            # Filtro solo conflictos
            if show_only_conflicts and not move.has_conflict:
                continue
            
            self.filtered_moves.append(move)
        
        self.current_page = 0
        self._update_tree()
    
    def _clear_filters(self):
        """Limpia todos los filtros"""
        self.search_input.clear()
        self.type_combo.setCurrentIndex(0)
        if self.subdir_combo:
            self.subdir_combo.setCurrentIndex(0)
        self.conflicts_checkbox.setChecked(False)
    
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
            self.ITEMS_PER_PAGE = len(self.filtered_moves)
        else:
            self.ITEMS_PER_PAGE = int(text)
        self.current_page = 0
        QTimer.singleShot(0, self._update_tree)
    
    def _update_tree(self):
        """Actualiza el TreeWidget con agrupación según tipo de organización"""
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        
        try:
            total_filtered = len(self.filtered_moves)
            use_pagination = total_filtered > self.MAX_ITEMS_WITHOUT_PAGINATION
            
            if use_pagination:
                self.total_pages = (total_filtered + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
                start_idx = self.current_page * self.ITEMS_PER_PAGE
                end_idx = min(start_idx + self.ITEMS_PER_PAGE, total_filtered)
                items_to_show = self.filtered_moves[start_idx:end_idx]
                
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
                items_to_show = self.filtered_moves
                self.pagination_widget.setVisible(False)
            
            # Limpiar tree
            self.files_tree.clear()
            
            # Agrupar según tipo de organización
            if self.analysis.organization_type == 'to_root':
                self._populate_tree_to_root(items_to_show)
            elif self.analysis.organization_type == 'by_month':
                self._populate_tree_by_month(items_to_show)
            else:  # whatsapp_separate
                self._populate_tree_whatsapp(items_to_show)
            
            # Actualizar contador
            total = len(self.analysis.move_plan)
            if use_pagination:
                self.counter_label.setText(
                    f"Mostrando {len(items_to_show)} de {total_filtered} archivos filtrados ({total} total)"
                )
            else:
                if total_filtered == total:
                    self.counter_label.setText(f"Mostrando {total_filtered} archivos")
                else:
                    self.counter_label.setText(f"Mostrando {total_filtered} de {total} archivos")
        
        finally:
            QApplication.restoreOverrideCursor()
    
    def _populate_tree_to_root(self, moves):
        """Poblar tree agrupado mostrando destino (Raíz) con archivos desde subdirectorios"""
        from collections import defaultdict
        
        # Todos los archivos van a la raíz, agruparlos por subdirectorio de origen
        by_subdir = defaultdict(list)
        for move in moves:
            by_subdir[move.subdirectory].append(move)
        
        # Crear nodo principal para Raíz (destino de todos)
        total_moves = len(moves)
        total_size_all = sum(m.size for m in moves)
        total_conflicts = sum(1 for m in moves if m.has_conflict)
        
        root_parent = QTreeWidgetItem()
        root_parent.setText(0, "📂 Raíz del directorio")
        root_parent.setText(1, "")  # Vacío
        root_parent.setText(2, f"{total_moves} archivos")
        if total_conflicts > 0:
            root_parent.setText(3, f"⚠️ {total_conflicts} conflictos | {format_size(total_size_all)}")
            root_parent.setForeground(3, QColor("#e74c3c"))
        else:
            root_parent.setText(3, format_size(total_size_all))
        
        root_font = QFont()
        root_font.setBold(True)
        root_font.setPointSize(11)
        root_parent.setFont(0, root_font)
        root_parent.setForeground(0, QColor("#2c5aa0"))
        
        self.files_tree.addTopLevelItem(root_parent)
        
        # Crear subnodos por subdirectorio origen
        for subdir in sorted(by_subdir.keys()):
            moves_in_subdir = by_subdir[subdir]
            total_size = sum(m.size for m in moves_in_subdir)
            conflicts = sum(1 for m in moves_in_subdir if m.has_conflict)
            
            # Nodo de subdirectorio origen
            subdir_node = QTreeWidgetItem()
            subdir_node.setText(0, f"  Desde: {subdir}")
            subdir_node.setText(1, f"{len(moves_in_subdir)} archivos")
            subdir_node.setText(2, format_size(total_size))
            if conflicts > 0:
                subdir_node.setText(3, f"⚠️ {conflicts} conflictos")
                subdir_node.setForeground(3, QColor("#e74c3c"))
            
            subdir_font = QFont()
            subdir_font.setBold(True)
            subdir_node.setFont(0, subdir_font)
            subdir_node.setForeground(0, QColor("#666"))
            
            root_parent.addChild(subdir_node)
            
            # Archivos individuales
            for move in sorted(moves_in_subdir, key=lambda m: m.original_name):
                child = QTreeWidgetItem()
                child.setText(0, f"    {move.original_name}")
                child.setText(1, subdir)
                child.setText(2, format_size(move.size))
                
                if move.has_conflict:
                    conflict_text = f"⚠️ → {move.new_name}"
                    child.setText(3, conflict_text)
                    child.setForeground(3, QColor("#e74c3c"))
                else:
                    child.setText(3, "✓ OK")
                    child.setForeground(3, QColor("#27ae60"))
                
                # Guardar datos del movimiento
                child.setData(0, Qt.ItemDataRole.UserRole, move)
                
                subdir_node.addChild(child)
            
            # Expandir si tiene pocos items
            if len(moves_in_subdir) <= 20:
                subdir_node.setExpanded(True)
            
            # Procesar eventos cada 10 items
            if root_parent.childCount() % 10 == 0:
                QApplication.processEvents()
        
        # Expandir el nodo raíz
        root_parent.setExpanded(True)
    
    def _populate_tree_by_month(self, moves):
        """Poblar tree agrupado por carpeta destino (mes)"""
        from collections import defaultdict
        
        # Agrupar por carpeta destino
        by_folder = defaultdict(list)
        for move in moves:
            folder = move.target_folder or "Sin fecha"
            by_folder[folder].append(move)
        
        # Crear nodos por carpeta destino
        for folder in sorted(by_folder.keys(), reverse=True):
            moves_in_folder = by_folder[folder]
            total_size = sum(m.size for m in moves_in_folder)
            
            # Nodo padre (carpeta destino)
            parent = QTreeWidgetItem()
            if folder == "Sin fecha":
                parent.setText(0, f"📅 {folder}")
            else:
                parent.setText(0, f"📅 {folder}/")
            parent.setText(1, "")  # Vacío en fecha para el nodo padre
            parent.setText(2, f"{len(moves_in_folder)} archivos")
            parent.setText(3, format_size(total_size))
            
            parent_font = QFont()
            parent_font.setBold(True)
            parent.setFont(0, parent_font)
            
            self.files_tree.addTopLevelItem(parent)
            
            # Archivos individuales
            for move in sorted(moves_in_folder, key=lambda m: m.original_name):
                child = QTreeWidgetItem()
                child.setText(0, f"  {move.original_name}")
                
                # Obtener fecha del archivo
                try:
                    file_date = get_file_date(move.source_path)
                    if file_date:
                        child.setText(1, file_date.strftime("%Y-%m-%d"))
                    else:
                        child.setText(1, "Sin fecha")
                except Exception:
                    child.setText(1, "Error")
                
                child.setText(2, move.subdirectory)
                child.setText(3, format_size(move.size))
                
                # Guardar datos del movimiento
                child.setData(0, Qt.ItemDataRole.UserRole, move)
                
                parent.addChild(child)
            
            # Expandir si tiene pocos items
            if len(moves_in_folder) <= 20:
                parent.setExpanded(True)
            
            # Procesar eventos cada 10 items
            if self.files_tree.topLevelItemCount() % 10 == 0:
                QApplication.processEvents()
    
    def _populate_tree_whatsapp(self, moves):
        """Poblar tree agrupado por categoría (WhatsApp vs Resto)"""
        from collections import defaultdict
        
        # Agrupar por categoría
        whatsapp_moves = []
        other_moves = []
        
        for move in moves:
            # Determinar si es WhatsApp
            is_whatsapp = (
                'whatsapp' in move.subdirectory.lower() or
                'WhatsApp' in str(move.source_path) or
                move.original_name.startswith(('IMG-', 'VID-')) and '-WA' in move.original_name
            )
            
            if is_whatsapp:
                whatsapp_moves.append(move)
            else:
                other_moves.append(move)
        
        # Crear nodo para WhatsApp (destino: carpeta WhatsApp/)
        if whatsapp_moves:
            self._create_whatsapp_category_node("📱 WhatsApp/", whatsapp_moves, "WhatsApp/")
        
        # Crear nodo para Resto (destino: raíz)
        if other_moves:
            self._create_whatsapp_category_node("📂 Raíz del directorio", other_moves, "Raíz")
    
    def _create_whatsapp_category_node(self, title, moves, destination):
        """Crea un nodo de categoría con sus archivos para WhatsApp"""
        total_size = sum(m.size for m in moves)
        
        # Nodo padre - muestra el destino donde irán los archivos
        parent = QTreeWidgetItem()
        parent.setText(0, title)
        parent.setText(1, "")  # Vacío en origen para el nodo padre
        parent.setText(2, f"{len(moves)} archivos → {destination}")
        parent.setText(3, format_size(total_size))
        
        parent_font = QFont()
        parent_font.setBold(True)
        parent.setFont(0, parent_font)
        
        # Color según destino
        if "WhatsApp" in destination:
            parent.setForeground(0, QColor("#25d366"))  # Verde WhatsApp
        else:
            parent.setForeground(0, QColor("#2c5aa0"))  # Azul para raíz
        
        self.files_tree.addTopLevelItem(parent)
        
        # Archivos individuales
        for move in sorted(moves, key=lambda m: m.original_name):
            child = QTreeWidgetItem()
            child.setText(0, f"  {move.original_name}")
            child.setText(1, move.subdirectory if move.subdirectory != "." else "Raíz")
            child.setText(2, destination)
            child.setText(3, format_size(move.size))
            
            # Guardar datos del movimiento
            child.setData(0, Qt.ItemDataRole.UserRole, move)
            
            parent.addChild(child)
        
        # Expandir si tiene pocos items
        if len(moves) <= 20:
            parent.setExpanded(True)
    
    def _on_file_double_clicked(self, item, column):
        """Abre el archivo con doble clic"""
        import subprocess
        import platform
        
        move = item.data(0, Qt.ItemDataRole.UserRole)
        if not move:
            return
        
        file_path = move.source_path
        
        if not file_path.exists():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Archivo no encontrado", 
                f"El archivo no existe:\n{file_path}"
            )
            return
        
        try:
            system = platform.system()
            if system == 'Linux':
                subprocess.Popen(['xdg-open', str(file_path)])
            elif system == 'Darwin':
                subprocess.Popen(['open', str(file_path)])
            elif system == 'Windows':
                subprocess.Popen(['start', str(file_path)], shell=True)
            
            # Feedback temporal
            self.setWindowTitle(f"Organización de Archivos - Abriendo {move.original_name}...")
            QTimer.singleShot(2000, lambda: self.setWindowTitle("Organización de Archivos"))
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"No se pudo abrir el archivo:\n{str(e)}")
    
    def _show_context_menu(self, position):
        """Muestra menú contextual con opciones y detalles del archivo"""
        item = self.files_tree.itemAt(position)
        if not item:
            return
        
        move = item.data(0, Qt.ItemDataRole.UserRole)
        if not move:
            return
        
        menu = QMenu(self)
        
        # Opción para abrir archivo
        open_file_action = menu.addAction("📂 Abrir archivo")
        open_file_action.triggered.connect(lambda: self._open_file(move.source_path))
        
        # Opción para abrir carpeta origen
        open_source_action = menu.addAction("📁 Abrir carpeta origen")
        open_source_action.triggered.connect(lambda: self._open_folder(move.source_path.parent))
        
        # Opción para abrir carpeta destino
        if move.target_path.parent.exists():
            open_target_action = menu.addAction("📂 Abrir carpeta destino")
            open_target_action.triggered.connect(lambda: self._open_folder(move.target_path.parent))
        
        menu.addSeparator()
        
        # Opción para ver detalles completos
        details_action = menu.addAction("ℹ️ Ver detalles completos")
        details_action.triggered.connect(lambda: self._show_file_details(move))
        
        menu.exec(self.files_tree.viewport().mapToGlobal(position))
    
    def _open_file(self, file_path):
        """Abre un archivo específico"""
        from .dialog_utils import open_file
        open_file(file_path, self)
    
    def _open_folder(self, folder_path):
        """Abre una carpeta en el explorador de archivos"""
        from .dialog_utils import open_folder
        open_folder(folder_path, self)
    
    def _show_file_details(self, move):
        """Muestra un diálogo con detalles completos del archivo"""
        from .dialog_utils import show_file_details_dialog
        
        additional_info = {
            'original_name': move.original_name,
            'new_name': move.new_name,
            'file_type': move.file_type,
            'target_path': move.target_path,
            'conflict': move.has_conflict,
            'sequence': move.sequence if move.has_conflict else None,
            'metadata': {
                'Subdirectorio origen': move.subdirectory,
            }
        }
        
        if move.target_folder:
            additional_info['metadata']['Carpeta destino'] = move.target_folder
        
        show_file_details_dialog(move.source_path, self, additional_info)

    def accept(self):
        self.accepted_plan = self.build_accepted_plan({
            'move_plan': self.analysis.move_plan,
            'cleanup_empty_dirs': self.cleanup_checkbox.isChecked(),
            'organization_type': self.analysis.organization_type,
            'folders_to_create': self.analysis.folders_to_create,
            'dry_run': self.dry_run_checkbox.isChecked()
        })
        super().accept()

