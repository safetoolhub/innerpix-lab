from pathlib import Path
import logging
import os
import platform
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QGroupBox, QVBoxLayout as QVLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFrame, QDialogButtonBox, 
    QMessageBox, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from config import Config
from ui import styles as ui_styles
from utils.logger import set_global_log_level, get_logger
from utils.settings_manager import settings_manager


class SettingsDialog(QDialog):
    """Diálogo de configuración avanzada con persistencia"""

    # Señal emitida cuando se guardan cambios importantes que requieren actualización
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.logger = get_logger('SettingsDialog')
        self.settings_changed = False
        self.init_ui()
        self._load_current_settings()

    def init_ui(self):
        self.setWindowTitle("⚙️ Configuración")
        self.setModal(True)
        self.resize(750, 600)

        # Layout principal con pestañas
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Crear pestañas para mejor organización
        tabs = QTabWidget()
        tabs.setStyleSheet(ui_styles.STYLE_TABS)

        # === PESTAÑA 1: GENERAL ===
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "🎯 General")

        # === PESTAÑA 2: DIRECTORIOS ===
        dirs_tab = self._create_directories_tab()
        tabs.addTab(dirs_tab, "📁 Directorios")

        # === PESTAÑA 3: COMPORTAMIENTO ===
        behavior_tab = self._create_behavior_tab()
        tabs.addTab(behavior_tab, "⚡ Comportamiento")

        # === PESTAÑA 4: AVANZADO ===
        advanced_tab = self._create_advanced_tab()
        tabs.addTab(advanced_tab, "� Avanzado")

        main_layout.addWidget(tabs)

        # Footer con botones
        footer = QFrame()
        footer.setStyleSheet(ui_styles.STYLE_FOOTER)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(15, 10, 15, 10)

        # Botón restaurar valores por defecto
        restore_btn = QPushButton("🔄 Restaurar valores por defecto")
        restore_btn.setStyleSheet(ui_styles.STYLE_RESTORE_BUTTON)
        restore_btn.clicked.connect(self.restore_defaults)
        footer_layout.addWidget(restore_btn)

        footer_layout.addStretch()

        # Botones estándar
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar Cambios")
        buttons.button(QDialogButtonBox.StandardButton.Save).setStyleSheet(ui_styles.STYLE_SAVE_BUTTON)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet(ui_styles.STYLE_CANCEL_BUTTON)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        footer_layout.addWidget(buttons)

        main_layout.addWidget(footer)

    def _create_general_tab(self):
        """Pestaña de configuración general"""
        widget = QWidget()
        layout = QVLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # === BACKUPS AUTOMÁTICOS ===
        backup_group = QGroupBox("💾 Backups Automáticos")
        backup_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        backup_layout = QVLayout(backup_group)
        backup_layout.setSpacing(12)

        backup_info = QLabel(
            "⚠️ <b>Muy Recomendado:</b> Los backups te permiten recuperar archivos en caso de error."
        )
        backup_info.setStyleSheet(ui_styles.STYLE_WARNING_LABEL)
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)

        self.auto_backup_checkbox = QCheckBox("✓ Crear backup automáticamente antes de cada operación destructiva")
        self.auto_backup_checkbox.setChecked(True)
        self.auto_backup_checkbox.setToolTip(
            "Si está activado, se creará una copia de seguridad de los archivos antes de:\n"
            "• Renombrar archivos\n"
            "• Eliminar Live Photos\n"
            "• Eliminar duplicados HEIC\n"
            "• Organizar directorios"
        )
        backup_layout.addWidget(self.auto_backup_checkbox)

        layout.addWidget(backup_group)

        # === CONFIRMACIONES ===
        confirm_group = QGroupBox("❓ Confirmaciones")
        confirm_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        confirm_layout = QVLayout(confirm_group)
        confirm_layout.setSpacing(10)

        self.confirm_operations_checkbox = QCheckBox("Mostrar diálogo de confirmación antes de ejecutar operaciones")
        self.confirm_operations_checkbox.setChecked(True)
        self.confirm_operations_checkbox.setToolTip("Muestra un resumen antes de aplicar cambios")
        confirm_layout.addWidget(self.confirm_operations_checkbox)

        self.confirm_delete_checkbox = QCheckBox("Pedir confirmación adicional para operaciones de eliminación")
        self.confirm_delete_checkbox.setChecked(True)
        self.confirm_delete_checkbox.setToolTip("Doble confirmación para operaciones que eliminan archivos")
        confirm_layout.addWidget(self.confirm_delete_checkbox)

        layout.addWidget(confirm_group)

        # === NOTIFICACIONES ===
        notif_group = QGroupBox("🔔 Notificaciones")
        notif_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        notif_layout = QVLayout(notif_group)
        notif_layout.setSpacing(10)

        self.show_notifications_checkbox = QCheckBox("Mostrar notificación al completar operaciones")
        self.show_notifications_checkbox.setChecked(True)
        notif_layout.addWidget(self.show_notifications_checkbox)

        self.sound_notifications_checkbox = QCheckBox("Reproducir sonido con notificaciones")
        self.sound_notifications_checkbox.setChecked(False)
        self.sound_notifications_checkbox.setEnabled(False)  # Feature no implementada aún
        self.sound_notifications_checkbox.setToolTip("Funcionalidad no implementada actualmente")
        notif_layout.addWidget(self.sound_notifications_checkbox)

        layout.addWidget(notif_group)

        layout.addStretch()
        return widget

    def _create_directories_tab(self):
        """Pestaña de configuración de directorios y logs"""
        widget = QWidget()
        layout = QVLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # === LOGS ===
        logs_group = QGroupBox("📄 Logs y Diagnóstico")
        logs_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        logs_layout = QVLayout(logs_group)
        logs_layout.setSpacing(12)

        logs_info = QLabel(
            "Los archivos de log registran todas las operaciones para diagnóstico y auditoría."
        )
        logs_info.setStyleSheet(ui_styles.STYLE_SMALL_INFO_LABEL)
        logs_info.setWordWrap(True)
        logs_layout.addWidget(logs_info)

        # Directorio de logs
        logs_dir_layout = QHBoxLayout()
        logs_label = QLabel("Carpeta:")
        logs_label.setMinimumWidth(100)
        logs_dir_layout.addWidget(logs_label)

        self.logs_edit = QLineEdit()
        self.logs_edit.setText(str(self.parent_window.logs_directory if self.parent_window else Config.DEFAULT_LOG_DIR))
        self.logs_edit.setReadOnly(True)
        self.logs_edit.setStyleSheet(ui_styles.STYLE_DIRECTORY_EDIT)
        logs_dir_layout.addWidget(self.logs_edit)

        browse_logs_btn = QPushButton("📂")
        browse_logs_btn.setMaximumWidth(50)
        browse_logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_logs_btn.setToolTip("Cambiar ubicación de logs")
        browse_logs_btn.clicked.connect(self.browse_logs_directory)
        logs_dir_layout.addWidget(browse_logs_btn)

        logs_layout.addLayout(logs_dir_layout)

        # Nivel de log
        log_level_layout = QHBoxLayout()
        log_level_label = QLabel("Nivel de detalle:")
        log_level_label.setMinimumWidth(100)
        log_level_layout.addWidget(log_level_label)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems([
            "DEBUG - Máximo detalle (para desarrollo)",
            "INFO - Normal (recomendado)",
            "WARNING - Solo advertencias",
            "ERROR - Solo errores críticos"
        ])
        self.log_level_combo.setStyleSheet(ui_styles.STYLE_LOG_LEVEL_COMBO)
        self.log_level_combo.setToolTip(
            "DEBUG: Toda la información técnica\n"
            "INFO: Operaciones normales\n"
            "WARNING: Situaciones inusuales\n"
            "ERROR: Solo errores graves"
        )
        log_level_layout.addWidget(self.log_level_combo)
        log_level_layout.addStretch()

        logs_layout.addLayout(log_level_layout)

        # Botón abrir carpeta de logs
        open_logs_btn = QPushButton("📂 Abrir carpeta de logs")
        open_logs_btn.setStyleSheet(ui_styles.STYLE_OPEN_LOGS_BUTTON)
        open_logs_btn.clicked.connect(self.open_logs_folder)
        logs_layout.addWidget(open_logs_btn)

        layout.addWidget(logs_group)

        # === BACKUPS ===
        backup_group = QGroupBox("💾 Directorio de Backups")
        backup_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        backup_layout = QVLayout(backup_group)

        backup_info = QLabel("Ubicación donde se guardan las copias de seguridad automáticas.")
        backup_info.setStyleSheet(ui_styles.STYLE_SMALL_INFO_LABEL)
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)

        backup_row = QHBoxLayout()
        backup_label = QLabel("Carpeta:")
        backup_label.setMinimumWidth(100)
        backup_row.addWidget(backup_label)

        self.backup_edit = QLineEdit()
        self.backup_edit.setText(str(Config.DEFAULT_BACKUP_DIR))
        self.backup_edit.setReadOnly(True)
        self.backup_edit.setStyleSheet(ui_styles.STYLE_DIRECTORY_EDIT)
        backup_row.addWidget(self.backup_edit)

        browse_backup_btn = QPushButton("📂")
        browse_backup_btn.setMaximumWidth(50)
        browse_backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_backup_btn.setToolTip("Cambiar ubicación de backups")
        browse_backup_btn.clicked.connect(self.browse_backup_directory)
        backup_row.addWidget(browse_backup_btn)

        backup_layout.addLayout(backup_row)
        layout.addWidget(backup_group)

        layout.addStretch()
        return widget

    def _create_behavior_tab(self):
        """Pestaña de comportamiento"""
        widget = QWidget()
        layout = QVLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # === INICIO ===
        startup_group = QGroupBox("🚀 Al Iniciar la Aplicación")
        startup_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        startup_layout = QVLayout(startup_group)

        self.remember_dir_checkbox = QCheckBox("Recordar último directorio utilizado")
        self.remember_dir_checkbox.setChecked(True)
        self.remember_dir_checkbox.setToolTip("Al abrir la app, se pre-carga el último directorio usado")
        startup_layout.addWidget(self.remember_dir_checkbox)

        self.auto_analyze_checkbox = QCheckBox("Analizar automáticamente al abrir un directorio")
        self.auto_analyze_checkbox.setChecked(False)
        self.auto_analyze_checkbox.setToolTip(
            "Inicia el análisis automáticamente sin pulsar 'Analizar Directorio'.\n"
            "¡Cuidado! Puede ser lento en directorios grandes."
        )
        startup_layout.addWidget(self.auto_analyze_checkbox)

        layout.addWidget(startup_group)

        # === INTERFAZ ===
        ui_group = QGroupBox("🎨 Interfaz")
        ui_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        ui_layout = QVLayout(ui_group)

        theme_layout = QHBoxLayout()
        theme_label = QLabel("Tema:")
        theme_label.setMinimumWidth(100)
        theme_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Oscuro (por defecto)", "Claro", "Sistema"])
        self.theme_combo.setCurrentIndex(0)
        self.theme_combo.setEnabled(False)  # Feature no implementada
        self.theme_combo.setToolTip("Funcionalidad no implementada actualmente")
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()

        ui_layout.addLayout(theme_layout)
        layout.addWidget(ui_group)

        layout.addStretch()
        return widget

    def _create_advanced_tab(self):
        """Pestaña de configuración avanzada"""
        widget = QWidget()
        layout = QVLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # === RENDIMIENTO ===
        perf_group = QGroupBox("⚡ Rendimiento")
        perf_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        perf_layout = QVLayout(perf_group)
        perf_layout.setSpacing(12)

        workers_layout = QHBoxLayout()
        workers_label = QLabel("Hilos de procesamiento:")
        workers_label.setMinimumWidth(180)
        workers_layout.addWidget(workers_label)

        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setMinimum(1)
        self.max_workers_spin.setMaximum(Config.MAX_WORKER_THREADS)
        self.max_workers_spin.setValue(Config.MAX_WORKERS)
        self.max_workers_spin.setToolTip(
            f"Número de hilos paralelos para procesar archivos.\n"
            f"Más hilos = más rápido, pero mayor uso de CPU.\n"
            f"Recomendado: {Config.MAX_WORKERS}"
        )
        workers_layout.addWidget(self.max_workers_spin)
        workers_layout.addStretch()

        perf_layout.addLayout(workers_layout)

        perf_info = QLabel(
            "ℹ️ Cambiar el número de hilos requiere reiniciar la aplicación para tener efecto completo."
        )
        perf_info.setStyleSheet(ui_styles.STYLE_SMALL_INFO_LABEL)
        perf_info.setWordWrap(True)
        perf_layout.addWidget(perf_info)

        layout.addWidget(perf_group)

        # === MODO SIMULACIÓN ===
        dryrun_group = QGroupBox("🧪 Modo Simulación (Dry Run)")
        dryrun_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        dryrun_layout = QVLayout(dryrun_group)
        dryrun_layout.setSpacing(12)

        dryrun_info = QLabel(
            "En modo simulación, las operaciones se analizan y muestran pero <b>no se ejecutan</b> realmente. "
            "Útil para verificar qué hará la aplicación antes de aplicar cambios."
        )
        dryrun_info.setStyleSheet(ui_styles.STYLE_SMALL_INFO_LABEL)
        dryrun_info.setWordWrap(True)
        dryrun_layout.addWidget(dryrun_info)

        self.dry_run_default_checkbox = QCheckBox("Activar modo simulación por defecto")
        self.dry_run_default_checkbox.setChecked(False)
        self.dry_run_default_checkbox.setEnabled(False)  # Feature no implementada
        self.dry_run_default_checkbox.setToolTip("Funcionalidad no implementada actualmente")
        dryrun_layout.addWidget(self.dry_run_default_checkbox)

        layout.addWidget(dryrun_group)

        # === DEPURACIÓN ===
        debug_group = QGroupBox("🐛 Depuración")
        debug_group.setStyleSheet(ui_styles.STYLE_GROUPBOX_SETTINGS)
        debug_layout = QVLayout(debug_group)

        clear_settings_btn = QPushButton("🗑️ Restablecer TODA la configuración guardada")
        clear_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        clear_settings_btn.clicked.connect(self.clear_all_settings)
        debug_layout.addWidget(clear_settings_btn)

        debug_info = QLabel("⚠️ Esto eliminará todas las preferencias guardadas y volverá a los valores por defecto.")
        debug_info.setStyleSheet("color: #ff5252; font-size: 11px;")
        debug_info.setWordWrap(True)
        debug_layout.addWidget(debug_info)

        layout.addWidget(debug_group)

        layout.addStretch()
        return widget

    def _load_current_settings(self):
        """Carga la configuración actual desde el gestor de settings"""
        try:
            # General tab
            self.auto_backup_checkbox.setChecked(settings_manager.get_auto_backup_enabled())
            self.confirm_operations_checkbox.setChecked(settings_manager.get_confirm_operations())
            self.confirm_delete_checkbox.setChecked(settings_manager.get_confirm_delete())
            self.show_notifications_checkbox.setChecked(settings_manager.get_show_notifications())

            # Behavior tab
            self.remember_dir_checkbox.setChecked(settings_manager.get_bool(
                settings_manager.KEY_REMEMBER_DIR, True
            ))
            self.auto_analyze_checkbox.setChecked(settings_manager.get_auto_analyze())

            # Advanced tab
            self.max_workers_spin.setValue(settings_manager.get_max_workers(Config.MAX_WORKERS))

            # Directories tab - Log level
            current_level = settings_manager.get_log_level("INFO")
            level_index_map = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
            self.log_level_combo.setCurrentIndex(level_index_map.get(current_level, 1))

            # Directories
            logs_dir = settings_manager.get_logs_directory()
            if logs_dir:
                self.logs_edit.setText(str(logs_dir))

            backup_dir = settings_manager.get_backup_directory()
            if backup_dir:
                self.backup_edit.setText(str(backup_dir))

            self.logger.debug("Configuración cargada desde settings_manager")

        except Exception as e:
            self.logger.exception(f"Error cargando configuración: {e}")

    # === MÉTODOS AUXILIARES ===

    def browse_logs_directory(self):
        """Cambia directorio de logs"""
        from PyQt6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio de Logs",
            self.logs_edit.text()
        )
        if directory:
            self.logs_edit.setText(directory)
            self.settings_changed = True

    def browse_backup_directory(self):
        """Cambia directorio de backups"""
        from PyQt6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio de Backups",
            self.backup_edit.text()
        )
        if directory:
            self.backup_edit.setText(directory)
            self.settings_changed = True

    def open_logs_folder(self):
        """Abre la carpeta de logs usando el método apropiado según el sistema operativo."""
        try:
            logs_dir = self.logs_edit.text()

            if platform.system() == 'Windows':
                os.startfile(logs_dir)
            elif platform.system() == 'Darwin':
                subprocess.Popen(['open', logs_dir])
            else:
                subprocess.Popen(['xdg-open', logs_dir])

            self.logger.info(f"Carpeta de logs abierta: {logs_dir}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo abrir la carpeta:\n{str(e)}"
            )

    def clear_all_settings(self):
        """Limpia toda la configuración guardada"""
        reply = QMessageBox.warning(
            self,
            "⚠️ Confirmar Eliminación",
            "¿Estás seguro de que deseas eliminar TODA la configuración guardada?\n\n"
            "Esto incluye:\n"
            "• Preferencias de backup\n"
            "• Directorios personalizados\n"
            "• Nivel de logging\n"
            "• Último directorio usado\n"
            "• Todas las demás configuraciones\n\n"
            "La aplicación volverá a los valores por defecto.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                settings_manager.clear_all()
                self.logger.info("Toda la configuración ha sido eliminada")
                QMessageBox.information(
                    self,
                    "✓ Configuración Eliminada",
                    "Se ha eliminado toda la configuración.\n"
                    "Se recomienda reiniciar la aplicación."
                )
                # Recargar valores por defecto
                self._load_current_settings()
            except Exception as e:
                self.logger.exception(f"Error limpiando configuración: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo limpiar la configuración:\n{str(e)}"
                )

    def change_log_level(self, level_str):
        """Cambia el nivel de logging y actualiza config y logger del padre."""
        try:
            level_name = str(level_str).split()[0].split(" - ")[0].upper()
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR
            }
            level = level_map.get(level_name, logging.INFO)

            # Actualizar config
            Config.LOG_LEVEL = level_name
            
            # Actualizar TODOS los loggers globalmente
            set_global_log_level(level)
            
            # Guardar en settings manager
            settings_manager.set_log_level(level_name)
            
            # Actualizar también el logger de la ventana padre si existe
            if self.parent_window:
                if hasattr(self.parent_window, 'logging_manager'):
                    try:
                        self.parent_window.logging_manager.set_level(level_name)
                    except Exception:
                        pass
                
                if hasattr(self.parent_window, 'log_level'):
                    self.parent_window.log_level = level_name
            
            self.logger.info(f"Nivel de log cambiado a: {level_name}")

        except Exception as e:
            self.logger.exception(f"Error cambiando nivel de log: {e}")

    def restore_defaults(self):
        """Restaura valores por defecto"""
        reply = QMessageBox.question(
            self,
            "Restaurar Valores",
            "¿Restaurar toda la configuración a los valores por defecto?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Restaurar valores
            self.logs_edit.setText(str(Config.DEFAULT_LOG_DIR))
            self.backup_edit.setText(str(Config.DEFAULT_BACKUP_DIR))
            self.log_level_combo.setCurrentIndex(1)  # INFO
            self.auto_backup_checkbox.setChecked(True)
            self.confirm_operations_checkbox.setChecked(True)
            self.confirm_delete_checkbox.setChecked(True)
            self.remember_dir_checkbox.setChecked(True)
            self.auto_analyze_checkbox.setChecked(False)
            self.show_notifications_checkbox.setChecked(True)
            self.sound_notifications_checkbox.setChecked(False)
            self.dry_run_default_checkbox.setChecked(False)
            self.max_workers_spin.setValue(Config.MAX_WORKERS)

            QMessageBox.information(self, "✓ Restaurado", "Configuración restaurada a valores por defecto.\n\n"
                                   "Presiona 'Guardar Cambios' para aplicar.")

    def save_settings(self):
        """Guarda la configuración en el settings_manager"""
        try:
            # === DIRECTORIOS ===
            new_logs_dir = Path(self.logs_edit.text())
            new_backup_dir = Path(self.backup_edit.text())

            settings_manager.set_logs_directory(new_logs_dir)
            settings_manager.set_backup_directory(new_backup_dir)

            # Actualizar en la ventana padre
            if self.parent_window:
                if hasattr(self.parent_window, 'logging_manager'):
                    try:
                        self.parent_window.logging_manager.change_logs_directory(new_logs_dir)
                        self.parent_window.logs_directory = self.parent_window.logging_manager.logs_directory
                        self.parent_window.log_file = self.parent_window.logging_manager.log_file
                    except Exception as e:
                        self.logger.warning(f"No se pudo cambiar directorio de logs en logging_manager: {e}")
                        self.parent_window.logs_directory = new_logs_dir

            # === NIVEL DE LOG ===
            level_text = self.log_level_combo.currentText()
            self.change_log_level(level_text)

            # === GENERAL ===
            settings_manager.set_auto_backup_enabled(self.auto_backup_checkbox.isChecked())
            settings_manager.set(settings_manager.KEY_CONFIRM_OPERATIONS, self.confirm_operations_checkbox.isChecked())
            settings_manager.set(settings_manager.KEY_CONFIRM_DELETE, self.confirm_delete_checkbox.isChecked())
            settings_manager.set(settings_manager.KEY_SHOW_NOTIFICATIONS, self.show_notifications_checkbox.isChecked())
            settings_manager.set(settings_manager.KEY_SOUND_NOTIFICATIONS, self.sound_notifications_checkbox.isChecked())

            # === COMPORTAMIENTO ===
            settings_manager.set(settings_manager.KEY_REMEMBER_DIR, self.remember_dir_checkbox.isChecked())
            settings_manager.set(settings_manager.KEY_AUTO_ANALYZE, self.auto_analyze_checkbox.isChecked())

            # === AVANZADO ===
            settings_manager.set(settings_manager.KEY_MAX_WORKERS, self.max_workers_spin.value())
            settings_manager.set(settings_manager.KEY_DRY_RUN_DEFAULT, self.dry_run_default_checkbox.isChecked())

            self.logger.info("Configuración guardada exitosamente")

            # Emitir señal de cambios guardados
            self.settings_saved.emit()

            QMessageBox.information(
                self,
                "✓ Configuración Guardada",
                "La configuración se ha guardado correctamente.\n\n"
                "Algunos cambios pueden requerir reiniciar la aplicación."
            )

            self.accept()

        except Exception as e:
            self.logger.exception(f"Error guardando configuración: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo guardar la configuración:\n{str(e)}"
            )
