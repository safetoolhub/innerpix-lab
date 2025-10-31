"""
Diálogo de eliminación de duplicados HEIC/JPG - Rediseñado
Incluye explicaciones claras, vista de archivos con TreeWidget y optimización para miles de fotos
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QVBoxLayout as QVLayout, QRadioButton,
    QButtonGroup, QTableWidget, QTableWidgetItem, QCheckBox, QDialogButtonBox, 
    QLabel, QTreeWidget, QTreeWidgetItem, QLineEdit, QComboBox, QPushButton,
    QFrame, QApplication
)
from PyQt6.QtGui import QColor, QFont, QCursor
from PyQt6.QtCore import Qt, QTimer
from config import Config
from utils.format_utils import format_size
from ui import styles as ui_styles
from .base_dialog import BaseDialog


class HEICDuplicateRemovalDialog(BaseDialog):
    """Diálogo para eliminación de duplicados HEIC con vista mejorada"""
    
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
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Limpieza de Duplicados HEIC/JPG")
        self.setModal(True)
        self.resize(1200, 750)
        main_layout = QVBoxLayout(self)
        
        # Explicación clara del problema
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
        
        # Formato a mantener (más prominente)
        format_group = self._create_format_selection()
        main_layout.addWidget(format_group)
        
        # Barra de herramientas (filtros y búsqueda)
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)
        
        # TreeWidget de archivos duplicados
        self.files_tree = self._create_files_tree()
        main_layout.addWidget(self.files_tree)
        
        # Controles de paginación
        self.pagination_widget = self._create_pagination_controls()
        main_layout.addWidget(self.pagination_widget)
        
        # Opciones de seguridad
        options_group = self._create_options_group()
        main_layout.addWidget(options_group)
        
        # Botones
        ok_enabled = self.analysis.total_duplicates > 0
        self.buttons = self.make_ok_cancel_buttons(ok_enabled=ok_enabled)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_enabled:
            self._update_button_text()
        main_layout.addWidget(self.buttons)
        
        # Actualizar vista inicial
        self._update_tree()

    def _create_explanation_section(self):
        """Crea sección de explicación clara"""
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
        
        explanation = QLabel(
            "ℹ️ iOS crea versiones HEIC y JPG de la misma foto. Puedes eliminar una versión para liberar espacio. "
            "<b>Mantener JPG</b>: compatibilidad universal | <b>Mantener HEIC</b>: menor tamaño"
        )
        explanation.setWordWrap(True)
        explanation.setTextFormat(Qt.TextFormat.RichText)
        explanation.setStyleSheet("font-size: 9pt; color: #495057; background: transparent;")
        layout.addWidget(explanation)
        
        return frame
    
    def _create_metrics_section(self):
        """Crea panel de métricas compacto"""
        layout = QHBoxLayout()
        
        metrics_data = [
            ("Total pares", self.analysis.total_pairs, "#2c5aa0"),
            ("Archivos HEIC", self.analysis.heic_files, "#9c27b0"),
            ("Archivos JPG", self.analysis.jpg_files, "#ff9800"),
        ]
        
        for label_text, value, color in metrics_data:
            card = self._create_inline_metric(label_text, value, color)
            layout.addWidget(card)
        
        # Info de ahorro
        savings_text = f"💾 Ahorro potencial: {format_size(self.analysis.potential_savings_keep_jpg)}"
        savings_label = QLabel(savings_text)
        savings_label.setStyleSheet("font-weight: bold; color: #27ae60; font-size: 12px; padding: 5px;")
        layout.addWidget(savings_label)
        
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
    
    def _create_format_selection(self):
        """Crea sección de selección de formato mejorada"""
        format_group = QGroupBox("🎯 Formato a Mantener (Elige cuál conservar)")
        format_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        format_layout = QVLayout(format_group)
        
        self.format_buttons = QButtonGroup()
        
        # JPG opción
        r1 = QRadioButton("📸 Mantener JPG, eliminar HEIC (Recomendado)")
        r1.setChecked(True)
        r1.setToolTip("Máxima compatibilidad. Los JPG funcionan en todos los dispositivos y aplicaciones.")
        self.format_buttons.addButton(r1, 0)
        format_layout.addWidget(r1)
        
        jpg_info = QLabel(f"   → Liberarás: {format_size(self.analysis.potential_savings_keep_jpg)}")
        jpg_info.setStyleSheet("color: #666; font-size: 10px; margin-left: 20px;")
        format_layout.addWidget(jpg_info)
        self.jpg_savings_label = jpg_info
        
        # HEIC opción
        r2 = QRadioButton("🖼️ Mantener HEIC, eliminar JPG (Menor tamaño)")
        r2.setToolTip("Archivos más pequeños pero requiere soporte HEIC en el visor/editor.")
        self.format_buttons.addButton(r2, 1)
        format_layout.addWidget(r2)
        
        heic_info = QLabel(f"   → Liberarás: {format_size(self.analysis.potential_savings_keep_heic)}")
        heic_info.setStyleSheet("color: #666; font-size: 10px; margin-left: 20px;")
        format_layout.addWidget(heic_info)
        self.heic_savings_label = heic_info
        
        self.format_buttons.buttonClicked.connect(self._on_format_changed)
        return format_group
    
    def _create_toolbar(self):
        """Crea barra de herramientas con filtros"""
        toolbar = QHBoxLayout()
        
        # Búsqueda
        search_label = QLabel("🔍")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setMaximumWidth(200)
        toolbar.addWidget(search_label)
        toolbar.addWidget(self.search_input)
        
        toolbar.addWidget(QLabel("|"))
        
        # Filtro por directorio
        dir_label = QLabel("Directorio:")
        self.dir_combo = QComboBox()
        directories = ["Todos"] + sorted(list(set(
            str(pair.directory) for pair in self.analysis.duplicate_pairs
        )))
        self.dir_combo.addItems(directories)
        self.dir_combo.currentTextChanged.connect(self._apply_filters)
        self.dir_combo.setMaximumWidth(250)
        toolbar.addWidget(dir_label)
        toolbar.addWidget(self.dir_combo)
        
        # Botón limpiar
        clear_btn = QPushButton("✕ Limpiar")
        clear_btn.clicked.connect(self._clear_filters)
        clear_btn.setMaximumWidth(80)
        toolbar.addWidget(clear_btn)
        
        # Contador
        self.counter_label = QLabel()
        self.counter_label.setStyleSheet("font-weight: bold; color: #2c5aa0; margin-left: 10px;")
        toolbar.addWidget(self.counter_label)
        
        toolbar.addStretch()
        return toolbar
    
    def _create_files_tree(self):
        """Crea TreeWidget para mostrar archivos duplicados"""
        tree = QTreeWidget()
        tree.setHeaderLabels(["Archivos", "HEIC 📷", "JPG 📷", "A Eliminar"])
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
            "💡 Doble clic en 'HEIC 📷' para abrir archivo HEIC\n"
            "💡 Doble clic en 'JPG 📷' para abrir archivo JPG\n"
            "💡 Clic derecho para más opciones"
        )
        
        # Ajustar columnas
        header = tree.header()
        header.setStretchLastSection(False)
        tree.setColumnWidth(0, 400)
        tree.setColumnWidth(1, 100)
        tree.setColumnWidth(2, 100)
        tree.setColumnWidth(3, 120)
        
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
        options_group = QGroupBox("⚙️ Opciones de Ejecución")
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        options_layout = QVLayout()
        
        # Checkbox de simulación
        self.dry_run_checkbox = QCheckBox("🔍 Modo simulación (no eliminar realmente)")
        from utils.settings_manager import settings_manager
        dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, False)
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() in ('true', '1', 'yes')
        self.dry_run_checkbox.setChecked(bool(dry_run_default))
        options_layout.addWidget(self.dry_run_checkbox)
        
        # Checkbox de backup
        self.add_backup_checkbox(options_layout, "💾 Crear backup antes de eliminar (Recomendado)")
        
        options_group.setLayout(options_layout)
        return options_group
    
    def _apply_filters(self):
        """Aplica filtros a la lista de pares"""
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
        """Actualiza el TreeWidget con los pares filtrados"""
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
            self.files_tree.clear()
            
            # Determinar qué se eliminará según formato seleccionado
            format_to_delete = "HEIC" if self.selected_format == 'jpg' else "JPG"
            
            # Añadir items
            for pair in items_to_show:
                item = QTreeWidgetItem()
                item.setText(0, pair.base_name)
                item.setText(1, format_size(pair.heic_size))
                item.setText(2, format_size(pair.jpg_size))
                item.setText(3, format_to_delete)
                
                # Color en la columna "A Eliminar"
                if format_to_delete == "HEIC":
                    item.setForeground(3, QColor("#9c27b0"))
                else:
                    item.setForeground(3, QColor("#ff9800"))
                
                # Guardar datos del par en el item
                item.setData(0, Qt.ItemDataRole.UserRole, pair)
                
                self.files_tree.addTopLevelItem(item)
                
                # Procesar eventos cada 50 items
                if self.files_tree.topLevelItemCount() % 50 == 0:
                    QApplication.processEvents()
            
            # Actualizar contador
            total = len(self.analysis.duplicate_pairs)
            if use_pagination:
                self.counter_label.setText(
                    f"Mostrando {len(items_to_show)} de {total_filtered} pares filtrados ({total} total)"
                )
            else:
                if total_filtered == total:
                    self.counter_label.setText(f"Mostrando {total_filtered} pares")
                else:
                    self.counter_label.setText(f"Mostrando {total_filtered} de {total} pares")
        
        finally:
            QApplication.restoreOverrideCursor()
    
    def _on_file_double_clicked(self, item, column):
        """Abre el archivo con doble clic según la columna"""
        import subprocess
        import platform
        
        pair = item.data(0, Qt.ItemDataRole.UserRole)
        if not pair:
            return
        
        # Determinar qué archivo abrir según la columna
        if column == 1:  # Columna HEIC
            file_path = pair.heic_path
            file_type = "HEIC"
            emoji = "🖼️"
        elif column == 2:  # Columna JPG
            file_path = pair.jpg_path
            file_type = "JPG"
            emoji = "📸"
        else:
            # Si hace clic en otra columna, abrir JPG por defecto
            file_path = pair.jpg_path
            file_type = "JPG (por defecto)"
            emoji = "📸"
        
        if not file_path.exists():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Archivo no encontrado", 
                f"El archivo {file_type} no existe:\n{file_path}"
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
            
            # Mostrar feedback temporal en la barra de estado del diálogo
            self.setWindowTitle(f"Limpieza de Duplicados HEIC/JPG - Abriendo {emoji} {file_type}...")
            QTimer.singleShot(2000, lambda: self.setWindowTitle("Limpieza de Duplicados HEIC/JPG"))
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"No se pudo abrir el archivo:\n{str(e)}")
    
    def _show_context_menu(self, position):
        """Muestra menú contextual para abrir archivos"""
        from PyQt6.QtWidgets import QMenu
        
        item = self.files_tree.itemAt(position)
        if not item:
            return
        
        pair = item.data(0, Qt.ItemDataRole.UserRole)
        if not pair:
            return
        
        menu = QMenu(self)
        
        # Opción para abrir HEIC
        open_heic_action = menu.addAction("🖼️ Abrir archivo HEIC")
        open_heic_action.triggered.connect(lambda: self._open_specific_file(pair.heic_path, "HEIC"))
        
        # Opción para abrir JPG
        open_jpg_action = menu.addAction("📸 Abrir archivo JPG")
        open_jpg_action.triggered.connect(lambda: self._open_specific_file(pair.jpg_path, "JPG"))
        
        menu.addSeparator()
        
        # Opción para abrir ambos
        open_both_action = menu.addAction("📂 Abrir ambos archivos")
        open_both_action.triggered.connect(lambda: self._open_both_files(pair))
        
        # Opción para abrir carpeta
        open_folder_action = menu.addAction("📁 Abrir carpeta")
        open_folder_action.triggered.connect(lambda: self._open_folder(pair.heic_path.parent))
        
        menu.addSeparator()
        
        # Opción para ver detalles de HEIC
        details_heic_action = menu.addAction("ℹ️ Ver detalles HEIC")
        details_heic_action.triggered.connect(lambda: self._show_file_details(pair, "heic"))
        
        # Opción para ver detalles de JPG
        details_jpg_action = menu.addAction("ℹ️ Ver detalles JPG")
        details_jpg_action.triggered.connect(lambda: self._show_file_details(pair, "jpg"))
        
        menu.exec(self.files_tree.viewport().mapToGlobal(position))
    
    def _open_specific_file(self, file_path, file_type):
        """Abre un archivo específico"""
        import subprocess
        import platform
        
        if not file_path.exists():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Archivo no encontrado", 
                f"El archivo {file_type} no existe:\n{file_path}"
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
            
            emoji = "🖼️" if file_type == "HEIC" else "📸"
            self.setWindowTitle(f"Limpieza de Duplicados HEIC/JPG - Abriendo {emoji} {file_type}...")
            QTimer.singleShot(2000, lambda: self.setWindowTitle("Limpieza de Duplicados HEIC/JPG"))
            
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"No se pudo abrir el archivo:\n{str(e)}")
    
    def _open_both_files(self, pair):
        """Abre ambos archivos (HEIC y JPG)"""
        import subprocess
        import platform
        
        files_to_open = [
            (pair.heic_path, "HEIC"),
            (pair.jpg_path, "JPG")
        ]
        
        opened_count = 0
        for file_path, file_type in files_to_open:
            if not file_path.exists():
                continue
            
            try:
                system = platform.system()
                if system == 'Linux':
                    subprocess.Popen(['xdg-open', str(file_path)])
                elif system == 'Darwin':
                    subprocess.Popen(['open', str(file_path)])
                elif system == 'Windows':
                    subprocess.Popen(['start', str(file_path)], shell=True)
                opened_count += 1
            except Exception:
                pass
        
        if opened_count > 0:
            self.setWindowTitle(f"Limpieza de Duplicados HEIC/JPG - Abriendo {opened_count} archivos...")
            QTimer.singleShot(2000, lambda: self.setWindowTitle("Limpieza de Duplicados HEIC/JPG"))
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "No se pudo abrir ningún archivo")
    
    def _open_folder(self, folder_path):
        """Abre una carpeta en el explorador de archivos"""
        from .dialog_utils import open_folder
        open_folder(folder_path, self)
    
    def _show_file_details(self, pair, file_type):
        """Muestra un diálogo con detalles completos del archivo"""
        from .dialog_utils import show_file_details_dialog
        
        # Seleccionar archivo según tipo
        if file_type == "heic":
            file_path = pair.heic_path
            file_size = pair.heic_size
            other_format = "JPG"
            other_size = pair.jpg_size
        else:
            file_path = pair.jpg_path
            file_size = pair.jpg_size
            other_format = "HEIC"
            other_size = pair.heic_size
        
        additional_info = {
            'original_name': pair.base_name,
            'new_name': pair.base_name,
            'file_type': file_type.upper(),
            'metadata': {
                'Nombre base': pair.base_name,
                f'Tamaño {file_type.upper()}': format_size(file_size),
                f'Tamaño {other_format}': format_size(other_size),
                'Directorio': str(pair.directory),
                'Par duplicado': f'Sí (con {other_format})',
            }
        }
        
        show_file_details_dialog(file_path, self, additional_info)
    
    def _update_button_text(self):
        """Actualiza el texto del botón según el formato seleccionado"""
        if self.analysis.total_duplicates > 0:
            if self.selected_format == 'jpg':
                savings = self.analysis.potential_savings_keep_jpg
            else:
                savings = self.analysis.potential_savings_keep_heic

            space_formatted = format_size(savings)
            self.ok_button.setText(
                f"Eliminar Duplicados ({self.analysis.total_duplicates} pares, {space_formatted})"
            )

    def _on_format_changed(self, button):
        self.selected_format = 'jpg' if self.format_buttons.id(button) == 0 else 'heic'
        self._update_button_text()
        self._update_tree()  # Actualizar para mostrar qué se eliminará

    def accept(self):
        self.accepted_plan = self.build_accepted_plan({
            'duplicate_pairs': self.analysis.duplicate_pairs,
            'keep_format': self.selected_format,
            'dry_run': self.dry_run_checkbox.isChecked(),
        })
        super().accept()
