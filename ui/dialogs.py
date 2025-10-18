"""
Diálogos para la aplicación PhotoKit Manager
Este módulo contiene todos los diálogos de la interfaz gráfica.
"""
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QDialogButtonBox,
    QGroupBox, QRadioButton, QButtonGroup, QWidget, QTabWidget, QLineEdit,
    QMessageBox, QPushButton, QFileDialog, QComboBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import logging

from services.live_photo_cleaner import CleanupMode
import config

class RenamingPreviewDialog(QDialog):
    """Diálogo de preview para renombrado"""

    def __init__(self, analysis_results, parent=None):
        super().__init__(parent)
        self.analysis_results = analysis_results
        self.accepted_plan = None
        self.init_ui()

    def update_statistics(self, results):
        """Actualiza las estadísticas después del renombrado"""
        if hasattr(self, 'stats_table'):
            self.stats_table.item(0, 1).setText(str(results['files_renamed']))
            if 'conflicts_resolved' in results:
                self.stats_table.item(1, 1).setText(str(results['conflicts_resolved']))
            if len(results['errors']) > 0:
                self.stats_table.item(2, 1).setText(str(len(results['errors'])))
            self.stats_table.viewport().update()

    def init_ui(self):
        self.setWindowTitle("Preview de Renombrado")
        self.setModal(True)
        self.resize(900, 600)
        layout = QVBoxLayout(self)

        # Estadísticas
        stats_group = QGroupBox("Estadísticas")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setRowCount(3)
        self.stats_table.setHorizontalHeaderLabels(["Concepto", "Cantidad"])
        header = self.stats_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # Filas de estadísticas
        stats_rows = [
            ("Archivos renombrados", "0"),
            ("Conflictos resueltos", "0"),
            ("Errores", "0")
        ]

        for row, (label, value) in enumerate(stats_rows):
            self.stats_table.setItem(row, 0, QTableWidgetItem(label))
            self.stats_table.setItem(row, 1, QTableWidgetItem(value))

        stats_layout.addWidget(self.stats_table)
        layout.addWidget(stats_group)

        # Tabla de cambios propuestos
        if self.analysis_results.get('renaming_plan'):
            layout.addWidget(QLabel("Cambios propuestos (primeros 50):"))
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Original", "Nuevo", "Fecha", "Conflicto"])
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

            plan = self.analysis_results['renaming_plan'][:50]
            table.setRowCount(len(plan))
            for row, item in enumerate(plan):
                table.setItem(row, 0, QTableWidgetItem(item['original_path'].name))
                table.setItem(row, 1, QTableWidgetItem(item['new_name']))
                table.setItem(row, 2, QTableWidgetItem(item['date'].strftime('%Y-%m-%d %H:%M:%S')))
                conflict_item = QTableWidgetItem("Sí" if item['has_conflict'] else "No")
                if item['has_conflict']:
                    conflict_item.setBackground(QColor(255, 255, 0))
                table.setItem(row, 3, conflict_item)

            table.setMaximumHeight(400)
            layout.addWidget(table)

            if len(self.analysis_results['renaming_plan']) > 50:
                more_label = QLabel(f"... y {len(self.analysis_results['renaming_plan']) - 50} más")
                more_label.setStyleSheet("font-style: italic; color: gray;")
                layout.addWidget(more_label)

        # Opciones
        self.backup_checkbox = QCheckBox("Crear backup (Recomendado)")
        self.backup_checkbox.setChecked(True)
        layout.addWidget(self.backup_checkbox)

        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        if self.analysis_results.get('need_renaming', 0) > 0:
            buttons.button(QDialogButtonBox.Ok).setText(
                f"Proceder ({self.analysis_results['need_renaming']})"
            )
        else:
            buttons.button(QDialogButtonBox.Ok).setEnabled(False)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self.accepted_plan = {
            'plan': self.analysis_results['renaming_plan'],
            'create_backup': self.backup_checkbox.isChecked()
        }
        super().accept()


class LivePhotoCleanupDialog(QDialog):
    """Diálogo para limpieza de Live Photos"""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.selected_mode = CleanupMode.KEEP_IMAGE
        self.accepted_plan = None
        self.init_ui()

    def _format_size(self, bytes_size):
        """Formatea tamaño en bytes a MB o GB"""
        mb_size = bytes_size / (1024 * 1024)
        if mb_size >= 1024:
            gb_size = mb_size / 1024
            return f"{gb_size:.2f} GB"
        else:
            return f"{mb_size:.1f} MB"

    def _calculate_space_for_mode(self, mode):
        """Calcula el espacio a liberar según el modo seleccionado"""
        groups = self.analysis.get('groups', [])
        if not groups:
            return 0

        total_space = 0
        if mode == CleanupMode.KEEP_IMAGE:
            for group in groups:
                total_space += group['video_size']
        elif mode == CleanupMode.KEEP_VIDEO:
            for group in groups:
                total_space += group['image_size']
        return total_space

    def _update_button_text(self):
        """Actualiza el texto del botón según el modo seleccionado"""
        groups = self.analysis.get('groups', [])
        lp_found = len(groups)
        if lp_found > 0:
            space = self._calculate_space_for_mode(self.selected_mode)
            space_formatted = self._format_size(space)
            files_type = "videos" if self.selected_mode == CleanupMode.KEEP_IMAGE else "imágenes"
            self.ok_button.setText(f"Eliminar {lp_found} {files_type} ({space_formatted})")

    def init_ui(self):
        self.setWindowTitle("Limpieza de Live Photos")
        self.setModal(True)
        self.resize(650, 450)
        layout = QVBoxLayout(self)

        # Información introductoria
        info_label = QLabel(
            "Los Live Photos de iPhone contienen una imagen JPG y un video MOV.\n"
            "Selecciona qué componente deseas conservar:"
        )
        info_label.setStyleSheet("color: #495057; padding: 10px; background-color: #e7f3ff; "
                                 "border-radius: 5px; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Modo de limpieza
        mode_group = QGroupBox("¿Qué deseas conservar?")
        mode_layout = QVBoxLayout(mode_group)
        self.mode_buttons = QButtonGroup()

        r1 = QRadioButton("🖼️ Conservar imágenes (JPG)")
        r1.setChecked(True)
        self.mode_buttons.addButton(r1, 0)
        mode_layout.addWidget(r1)

        desc1 = QLabel(" → Se eliminarán los videos MOV asociados\n"
                       " → Recomendado para ahorrar espacio manteniendo las fotos")
        desc1.setStyleSheet("color: #6c757d; font-size: 11px; margin-left: 20px;")
        mode_layout.addWidget(desc1)
        mode_layout.addSpacing(10)

        r2 = QRadioButton("🎥 Conservar videos (MOV)")
        self.mode_buttons.addButton(r2, 1)
        mode_layout.addWidget(r2)

        desc2 = QLabel(" → Se eliminarán las imágenes JPG asociadas\n"
                       " → Útil si prefieres mantener el movimiento/audio de Live Photos")
        desc2.setStyleSheet("color: #6c757d; font-size: 11px; margin-left: 20px;")
        mode_layout.addWidget(desc2)

        self.mode_buttons.buttonClicked.connect(self._on_mode_changed)
        layout.addWidget(mode_group)

        # Estadísticas
        stats_group = QGroupBox("Información")
        stats_layout = QVBoxLayout(stats_group)
        lp_found = self.analysis.get('live_photos_found', 0)
        total_space = self.analysis.get('total_space', 0)
        stats_label = QLabel(
            f"📱 Live Photos detectados: <b>{lp_found}</b><br>"
            f"💾 Espacio total ocupado: <b>{self._format_size(total_space)}</b>"
        )
        stats_label.setTextFormat(Qt.RichText)
        stats_layout.addWidget(stats_label)
        layout.addWidget(stats_group)

        # Opciones
        options_group = QGroupBox("Opciones de seguridad")
        options_layout = QVBoxLayout(options_group)

        self.backup_checkbox = QCheckBox("Crear backup antes de eliminar (Recomendado)")
        self.backup_checkbox.setChecked(True)
        options_layout.addWidget(self.backup_checkbox)

        self.dry_run_checkbox = QCheckBox("Modo simulación (no eliminar archivos realmente)")
        options_layout.addWidget(self.dry_run_checkbox)
        layout.addWidget(options_group)

        # Botones
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = self.buttons.button(QDialogButtonBox.Ok)
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")

        if lp_found > 0:
            self._update_button_text()
        else:
            self.ok_button.setEnabled(False)
            self.ok_button.setText("No hay Live Photos para limpiar")

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _on_mode_changed(self, button):
        modes = {0: CleanupMode.KEEP_IMAGE, 1: CleanupMode.KEEP_VIDEO}
        self.selected_mode = modes[self.mode_buttons.id(button)]
        self._update_button_text()

    def accept(self):
        # Preparamos el plan de limpieza asegurándonos de que las rutas son objetos Path
        self.accepted_plan = {
            'mode': self.selected_mode,
            'create_backup': self.backup_checkbox.isChecked(),
            'dry_run': self.dry_run_checkbox.isChecked(),
            'files_to_delete': (
                self.analysis['files_to_delete'] if self.selected_mode == CleanupMode.KEEP_IMAGE
                else self.analysis['files_to_keep']
            )
        }
        super().accept()


class DirectoryUnificationDialog(QDialog):
    """Diálogo para unificación de directorios"""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.accepted_plan = None
        self.init_ui()

    def _format_size(self, bytes_size):
        """Formatea tamaño en bytes a MB o GB"""
        mb_size = bytes_size / (1024 * 1024)
        if mb_size >= 1024:
            gb_size = mb_size / 1024
            return f"{gb_size:.2f} GB"
        else:
            return f"{mb_size:.1f} MB"

    def init_ui(self):
        self.setWindowTitle("Unificación de Directorios")
        self.setModal(True)
        self.resize(800, 500)
        layout = QVBoxLayout(self)

        # Información
        info = QLabel("Esta operación moverá todos los archivos al directorio raíz "
                      "y eliminará los subdirectorios vacíos.")
        info.setWordWrap(True)
        info.setStyleSheet("padding: 10px; background-color: #fff3cd; border-radius: 5px;")
        layout.addWidget(info)

        # Lista de subdirectorios
        if self.analysis.get('subdirectories'):
            layout.addWidget(QLabel("Subdirectorios a unificar:"))
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Subdirectorio", "Archivos", "Tamaño"])

            subdirs = list(self.analysis['subdirectories'].items())
            table.setRowCount(len(subdirs))
            for row, (name, info) in enumerate(subdirs):
                table.setItem(row, 0, QTableWidgetItem(name))
                table.setItem(row, 1, QTableWidgetItem(str(info['file_count'])))
                size_formatted = self._format_size(info['total_size'])
                table.setItem(row, 2, QTableWidgetItem(size_formatted))

            table.setMaximumHeight(300)
            layout.addWidget(table)

        # Opciones
        options_group = QGroupBox("Opciones")
        options_layout = QVBoxLayout(options_group)

        self.backup_checkbox = QCheckBox("Crear backup")
        self.backup_checkbox.setChecked(True)
        options_layout.addWidget(self.backup_checkbox)

        self.cleanup_checkbox = QCheckBox("Eliminar directorios vacíos")
        self.cleanup_checkbox.setChecked(True)
        options_layout.addWidget(self.cleanup_checkbox)
        layout.addWidget(options_group)

        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        if self.analysis.get('total_files_to_move', 0) > 0:
            size = self.analysis.get('total_size_to_move', 0)
            size_formatted = self._format_size(size)
            buttons.button(QDialogButtonBox.Ok).setText(
                f"Proceder ({self.analysis['total_files_to_move']}, {size_formatted})"
            )
        else:
            buttons.button(QDialogButtonBox.Ok).setEnabled(False)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self.accepted_plan = {
            'move_plan': self.analysis['move_plan'],
            'create_backup': self.backup_checkbox.isChecked(),
            'cleanup_empty_dirs': self.cleanup_checkbox.isChecked()
        }
        super().accept()


class HEICDuplicateRemovalDialog(QDialog):
    """Diálogo para eliminación de duplicados HEIC"""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.selected_format = 'jpg'
        self.accepted_plan = None
        self.init_ui()

    def _format_size(self, bytes_size):
        """Formatea tamaño en bytes a MB o GB"""
        mb_size = bytes_size / (1024 * 1024)
        if mb_size >= 1024:
            gb_size = mb_size / 1024
            return f"{gb_size:.2f} GB"
        else:
            return f"{mb_size:.1f} MB"

    def _update_button_text(self):
        """Actualiza el texto del botón según el formato seleccionado"""
        if self.analysis.get('total_duplicates', 0) > 0:
            if self.selected_format == 'jpg':
                savings = self.analysis.get('potential_savings_keep_jpg', 0)
            else:
                savings = self.analysis.get('potential_savings_keep_heic', 0)

            space_formatted = self._format_size(savings)
            self.ok_button.setText(
                f"Proceder ({self.analysis['total_duplicates']}, {space_formatted})"
            )

    def init_ui(self):
        self.setWindowTitle("Duplicados HEIC/JPG")
        self.setModal(True)
        self.resize(900, 600)
        layout = QVBoxLayout(self)

        # Formato a mantener
        format_group = QGroupBox("Formato a Mantener")
        format_layout = QVBoxLayout(format_group)
        self.format_buttons = QButtonGroup()

        r1 = QRadioButton("📸 Mantener JPG (Recomendado)")
        r1.setChecked(True)
        self.format_buttons.addButton(r1, 0)
        format_layout.addWidget(r1)

        r2 = QRadioButton("🖼️ Mantener HEIC")
        self.format_buttons.addButton(r2, 1)
        format_layout.addWidget(r2)

        self.format_buttons.buttonClicked.connect(self._on_format_changed)
        layout.addWidget(format_group)

        # Tabla de duplicados
        if self.analysis.get('duplicate_pairs'):
            layout.addWidget(QLabel("Pares detectados (primeros 20):"))
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Nombre", "HEIC (KB)", "JPG (KB)", "Ratio"])

            pairs = self.analysis['duplicate_pairs'][:20]
            table.setRowCount(len(pairs))
            for row, pair in enumerate(pairs):
                table.setItem(row, 0, QTableWidgetItem(pair.base_name))
                table.setItem(row, 1, QTableWidgetItem(f"{pair.heic_size / 1024:.1f}"))
                table.setItem(row, 2, QTableWidgetItem(f"{pair.jpg_size / 1024:.1f}"))
                table.setItem(row, 3, QTableWidgetItem(f"{pair.compression_ratio:.2f}x"))

            table.setMaximumHeight(300)
            layout.addWidget(table)

        # Opciones
        self.backup_checkbox = QCheckBox("Crear backup")
        self.backup_checkbox.setChecked(True)
        layout.addWidget(self.backup_checkbox)

        # Botones
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = self.buttons.button(QDialogButtonBox.Ok)

        if self.analysis.get('total_duplicates', 0) > 0:
            self._update_button_text()
        else:
            self.ok_button.setEnabled(False)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _on_format_changed(self, button):
        self.selected_format = 'jpg' if self.format_buttons.id(button) == 0 else 'heic'
        self._update_button_text()

    def accept(self):
        self.accepted_plan = {
            'duplicate_pairs': self.analysis['duplicate_pairs'],
            'keep_format': self.selected_format,
            'create_backup': self.backup_checkbox.isChecked()
        }
        super().accept()

class SettingsDialog(QDialog):
    """Diálogo de configuración avanzada"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.settings_changed = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("⚙️ Configuración Avanzada")
        self.setModal(True)
        self.resize(700, 550)

        # Layout principal con pestañas
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Crear pestañas para mejor organización
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 10px;
                background-color: white;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #007bff;
                color: white;
            }
        """)

        # === PESTAÑA 1: DIRECTORIOS Y LOGS ===
        dirs_tab = self._create_directories_tab()
        tabs.addTab(dirs_tab, "📁 Directorios")

        # === PESTAÑA 2: COMPORTAMIENTO ===
        behavior_tab = self._create_behavior_tab()
        tabs.addTab(behavior_tab, "⚡ Comportamiento")

        # === PESTAÑA 3: SEGURIDAD ===
        security_tab = self._create_security_tab()
        tabs.addTab(security_tab, "🔒 Seguridad")

        main_layout.addWidget(tabs)

        # Footer con botones
        footer = QFrame()
        footer.setStyleSheet("background-color: #f8f9fa; border-top: 1px solid #dee2e6;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(15, 10, 15, 10)

        # Botón restaurar valores por defecto
        restore_btn = QPushButton("🔄 Restaurar valores por defecto")
        restore_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6c757d;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        restore_btn.clicked.connect(self.restore_defaults)
        footer_layout.addWidget(restore_btn)

        footer_layout.addStretch()

        # Botones estándar
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Save).setText("Guardar Cambios")
        buttons.button(QDialogButtonBox.Save).setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        buttons.button(QDialogButtonBox.Cancel).setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6c757d;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        footer_layout.addWidget(buttons)

        main_layout.addWidget(footer)

    def _create_directories_tab(self):
        """Pestaña de configuración de directorios y logs"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # === LOGS - TODO JUNTO ===
        logs_group = QGroupBox("📄 Logs y Diagnóstico")
        logs_layout = QVBoxLayout(logs_group)
        logs_layout.setSpacing(12)

        # Descripción general
        logs_info = QLabel(
            "Los archivos de log se guardan aquí para diagnóstico, auditoría y seguimiento de operaciones."
        )
        logs_info.setStyleSheet("color: #6c757d; font-size: 11px;")
        logs_info.setWordWrap(True)
        logs_layout.addWidget(logs_info)

        # Directorio de logs
        logs_dir_layout = QHBoxLayout()
        logs_dir_layout.addWidget(QLabel("Carpeta:"))

        self.logs_edit = QLineEdit()
        self.logs_edit.setText(str(self.parent_window.logs_directory))
        self.logs_edit.setReadOnly(True)
        self.logs_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
        """)
        logs_dir_layout.addWidget(self.logs_edit)

        browse_logs_btn = QPushButton("📂 Cambiar")
        browse_logs_btn.setMinimumWidth(100)
        browse_logs_btn.setCursor(Qt.PointingHandCursor)
        browse_logs_btn.clicked.connect(self.browse_logs_directory)
        logs_dir_layout.addWidget(browse_logs_btn)

        logs_layout.addLayout(logs_dir_layout)

        # Nivel de log
        log_level_layout = QHBoxLayout()
        log_level_layout.addWidget(QLabel("Nivel de detalle:"))

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems([
            "DEBUG (Máximo detalle)",
            "INFO (Normal - Recomendado)",
            "WARNING (Solo advertencias)",
            "ERROR (Solo errores)"
        ])
    # No seleccionar por defecto aquí; la sincronización posterior ajustará la selección
        self.log_level_combo.setStyleSheet("""
            QComboBox {
                padding: 5px 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
            }
        """)
        log_level_layout.addWidget(self.log_level_combo)
        log_level_layout.addStretch()

        # Sincronizar con el valor actual (usar el nivel efectivo del logger de la ventana padre si existe)
        try:
            if hasattr(self, 'parent_window') and getattr(self.parent_window, 'app_logger', None):
                level_num = self.parent_window.app_logger.getEffectiveLevel()
                current_level = logging.getLevelName(level_num).upper()
            else:
                current_level = config.Config.LOG_LEVEL.upper()
        except Exception:
            current_level = config.Config.LOG_LEVEL.upper()

        found_idx = -1
        for i in range(self.log_level_combo.count()):
            text = self.log_level_combo.itemText(i).upper()
            if text.startswith(current_level):
                found_idx = i
                break
        if found_idx >= 0:
            self.log_level_combo.setCurrentIndex(found_idx)
        logs_layout.addLayout(log_level_layout)

        # Botón abrir carpeta de logs
        open_logs_btn = QPushButton("📂 Abrir carpeta de logs")
        open_logs_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #007bff;
                border: 1px solid #007bff;
                border-radius: 4px;
                padding: 6px 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #007bff;
                color: white;
            }
        """)
        open_logs_btn.clicked.connect(self.open_logs_folder)
        logs_layout.addWidget(open_logs_btn)

        layout.addWidget(logs_group)

        # === BACKUPS ===
        backup_group = QGroupBox("💾 Directorio de Backups")
        backup_layout = QVBoxLayout(backup_group)

        backup_info = QLabel("Los backups automáticos se guardan aquí antes de cada operación.")
        backup_info.setStyleSheet("color: #6c757d; font-size: 11px;")
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)

        backup_row = QHBoxLayout()
        backup_row.addWidget(QLabel("Carpeta:"))

        self.backup_edit = QLineEdit()
        self.backup_edit.setText(str(config.config.DEFAULT_BACKUP_DIR))
        self.backup_edit.setReadOnly(True)
        self.backup_edit.setStyleSheet(self.logs_edit.styleSheet())
        backup_row.addWidget(self.backup_edit)

        browse_backup_btn = QPushButton("📂 Cambiar")
        browse_backup_btn.setMinimumWidth(100)
        browse_backup_btn.setCursor(Qt.PointingHandCursor)
        browse_backup_btn.clicked.connect(self.browse_backup_directory)
        backup_row.addWidget(browse_backup_btn)

        backup_layout.addLayout(backup_row)
        layout.addWidget(backup_group)

        layout.addStretch()
        return widget

    def _create_behavior_tab(self):
        """Pestaña de comportamiento"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Confirmaciones
        confirm_group = QGroupBox("❓ Confirmaciones")
        confirm_layout = QVBoxLayout(confirm_group)

        self.confirm_operations_checkbox = QCheckBox("Pedir confirmación antes de ejecutar operaciones")
        self.confirm_operations_checkbox.setChecked(True)
        confirm_layout.addWidget(self.confirm_operations_checkbox)

        self.confirm_delete_checkbox = QCheckBox("Confirmación adicional para eliminaciones permanentes")
        self.confirm_delete_checkbox.setChecked(True)
        confirm_layout.addWidget(self.confirm_delete_checkbox)

        layout.addWidget(confirm_group)

        # Notificaciones
        notif_group = QGroupBox("🔔 Notificaciones")
        notif_layout = QVBoxLayout(notif_group)

        self.show_notifications_checkbox = QCheckBox("Mostrar notificación al completar operaciones")
        self.show_notifications_checkbox.setChecked(True)
        notif_layout.addWidget(self.show_notifications_checkbox)

        self.sound_notifications_checkbox = QCheckBox("Reproducir sonido con notificaciones")
        self.sound_notifications_checkbox.setChecked(False)
        notif_layout.addWidget(self.sound_notifications_checkbox)

        layout.addWidget(notif_group)

        # Inicio
        startup_group = QGroupBox("🚀 Al Iniciar")
        startup_layout = QVBoxLayout(startup_group)

        self.remember_dir_checkbox = QCheckBox("Recordar último directorio utilizado")
        self.remember_dir_checkbox.setChecked(True)
        startup_layout.addWidget(self.remember_dir_checkbox)

        self.auto_analyze_checkbox = QCheckBox("Analizar automáticamente al abrir directorio")
        self.auto_analyze_checkbox.setChecked(False)
        startup_layout.addWidget(self.auto_analyze_checkbox)

        layout.addWidget(startup_group)

        layout.addStretch()
        return widget

    def _create_security_tab(self):
        """Pestaña de seguridad"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # === BACKUPS AUTOMÁTICOS ===
        backup_group = QGroupBox("💾 Backups Automáticos")
        backup_layout = QVBoxLayout(backup_group)
        backup_layout.setSpacing(12)

        backup_info = QLabel(
            "⚠️ Recomendado: Los backups te permiten recuperar archivos en caso de error o problema."
        )
        backup_info.setStyleSheet("color: #856404; background-color: #fff3cd; padding: 8px; "
                                  "border-radius: 4px; font-size: 11px;")
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)

        self.auto_backup_checkbox = QCheckBox("Crear backup automáticamente antes de cada operación")
        self.auto_backup_checkbox.setChecked(True)
        backup_layout.addWidget(self.auto_backup_checkbox)

        layout.addWidget(backup_group)

        # === MODO SIMULACIÓN ===
        dryrun_group = QGroupBox("🧪 Modo Simulación")
        dryrun_layout = QVBoxLayout(dryrun_group)
        dryrun_layout.setSpacing(12)

        dryrun_info = QLabel(
            "En modo simulación, las operaciones se analizan y muestran pero no se ejecutan realmente. "
            "Útil para verificar qué hará la aplicación antes de aplicar cambios."
        )
        dryrun_info.setStyleSheet("color: #6c757d; font-size: 11px;")
        dryrun_info.setWordWrap(True)
        dryrun_layout.addWidget(dryrun_info)

        self.dry_run_default_checkbox = QCheckBox("Activar modo simulación por defecto en todas las operaciones")
        self.dry_run_default_checkbox.setChecked(False)
        dryrun_layout.addWidget(self.dry_run_default_checkbox)

        layout.addWidget(dryrun_group)

        layout.addStretch()
        return widget

    # === MÉTODOS AUXILIARES ===

    def browse_logs_directory(self):
        """Cambia directorio de logs"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio de Logs",
            str(self.parent_window.logs_directory)
        )
        if directory:
            self.logs_edit.setText(directory)
            self.settings_changed = True

    def browse_backup_directory(self):
        """Cambia directorio de backups"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio de Backups",
            self.backup_edit.text()
        )
        if directory:
            self.backup_edit.setText(directory)
            self.settings_changed = True

    def open_logs_folder(self):
        """Abre la carpeta de logs"""
        self.parent_window.open_logs_folder()

    def restore_defaults(self):
        """Restaura valores por defecto"""
        reply = QMessageBox.question(
            self,
            "Restaurar Valores",
            "¿Restaurar toda la configuración a los valores por defecto?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Restaurar valores
            self.logs_edit.setText(str(config.config.DEFAULT_LOG_DIR))
            self.backup_edit.setText(str(config.config.DEFAULT_BACKUP_DIR))
            self.log_level_combo.setCurrentIndex(1)  # INFO
            self.auto_backup_checkbox.setChecked(True)
            self.confirm_operations_checkbox.setChecked(True)
            self.confirm_delete_checkbox.setChecked(True)
            self.remember_dir_checkbox.setChecked(True)
            self.auto_analyze_checkbox.setChecked(False)
            self.show_notifications_checkbox.setChecked(True)
            self.sound_notifications_checkbox.setChecked(False)
            self.dry_run_default_checkbox.setChecked(False)

            QMessageBox.information(self, "Restaurado", "Configuración restaurada a valores por defecto")

    def save_settings(self):
        """Guarda la configuración"""
        # Actualizar directorio de logs
        new_logs_dir = Path(self.logs_edit.text())
        if new_logs_dir != self.parent_window.logs_directory:
            self.parent_window.logs_directory = new_logs_dir
            self.parent_window.app_logger.info(f"Directorio de logs cambiado a: {new_logs_dir}")

        # Actualizar nivel de log
        level_text = self.log_level_combo.currentText()
        level = level_text.split(" ")[0]  # Extraer DEBUG, INFO, etc.
        self.parent_window.change_log_level(level)

        # Aquí guardarías el resto de configuraciones en un archivo o variables

        # Registrar usando el nivel efectivo actual del logger (para que WARNING/ERROR sean visibles)
        try:
            lvl = self.parent_window.app_logger.getEffectiveLevel()
            self.parent_window.app_logger.log(lvl, "Configuración guardada exitosamente")
        except Exception:
            self.parent_window.app_logger.info("Configuración guardada exitosamente")

        QMessageBox.information(
            self,
            "Guardado",
            "✅ Configuración guardada correctamente"
        )

        self.accept()