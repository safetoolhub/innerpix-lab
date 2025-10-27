from pathlib import Path
import logging
import os
import platform
import subprocess
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QGroupBox, QVBoxLayout as QVLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFrame, QDialogButtonBox, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt
import config
from ui import styles as ui_styles


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
        tabs.setStyleSheet(ui_styles.STYLE_TABS)

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
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Save).setText("Guardar Cambios")
        buttons.button(QDialogButtonBox.Save).setStyleSheet(ui_styles.STYLE_SAVE_BUTTON)
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        buttons.button(QDialogButtonBox.Cancel).setStyleSheet(ui_styles.STYLE_CANCEL_BUTTON)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        footer_layout.addWidget(buttons)

        main_layout.addWidget(footer)

    def _create_directories_tab(self):
        """Pestaña de configuración de directorios y logs"""
        widget = QWidget()
        layout = QVLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # === LOGS - TODO JUNTO ===
        logs_group = QGroupBox("📄 Logs y Diagnóstico")
        logs_layout = QVLayout(logs_group)
        logs_layout.setSpacing(12)

        # Descripción general
        logs_info = QLabel(
            "Los archivos de log se guardan aquí para diagnóstico, auditoría y seguimiento de operaciones."
        )
        logs_info.setStyleSheet(ui_styles.STYLE_SMALL_INFO_LABEL)
        logs_info.setWordWrap(True)
        logs_layout.addWidget(logs_info)

        # Directorio de logs
        logs_dir_layout = QHBoxLayout()
        logs_dir_layout.addWidget(QLabel("Carpeta:"))

        self.logs_edit = QLineEdit()
        self.logs_edit.setText(str(self.parent_window.logs_directory))
        self.logs_edit.setReadOnly(True)
        self.logs_edit.setStyleSheet(ui_styles.STYLE_DIRECTORY_EDIT)
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

        # Combo de nivel de log
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems([
            "DEBUG (Máximo detalle)",
            "INFO (Normal - Recomendado)",
            "WARNING (Solo advertencias)",
            "ERROR (Solo errores)"
        ])
        self.log_level_combo.setStyleSheet(ui_styles.STYLE_LOG_LEVEL_COMBO)
        log_level_layout.addWidget(self.log_level_combo)
        log_level_layout.addStretch()

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
        open_logs_btn.setStyleSheet(ui_styles.STYLE_OPEN_LOGS_BUTTON)
        open_logs_btn.clicked.connect(self.open_logs_folder)
        logs_layout.addWidget(open_logs_btn)

        layout.addWidget(logs_group)

        # === BACKUPS ===
        backup_group = QGroupBox("💾 Directorio de Backups")
        backup_layout = QVLayout(backup_group)

        backup_info = QLabel("Los backups automáticos se guardan aquí antes de cada operación.")
        backup_info.setStyleSheet(ui_styles.STYLE_SMALL_INFO_LABEL)
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
        layout = QVLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Confirmaciones
        confirm_group = QGroupBox("❓ Confirmaciones")
        confirm_layout = QVLayout(confirm_group)

        self.confirm_operations_checkbox = QCheckBox("Pedir confirmación antes de ejecutar operaciones")
        self.confirm_operations_checkbox.setChecked(True)
        confirm_layout.addWidget(self.confirm_operations_checkbox)

        self.confirm_delete_checkbox = QCheckBox("Confirmación adicional para eliminaciones permanentes")
        self.confirm_delete_checkbox.setChecked(True)
        confirm_layout.addWidget(self.confirm_delete_checkbox)

        layout.addWidget(confirm_group)

        # Notificaciones
        notif_group = QGroupBox("🔔 Notificaciones")
        notif_layout = QVLayout(notif_group)

        self.show_notifications_checkbox = QCheckBox("Mostrar notificación al completar operaciones")
        self.show_notifications_checkbox.setChecked(True)
        notif_layout.addWidget(self.show_notifications_checkbox)

        self.sound_notifications_checkbox = QCheckBox("Reproducir sonido con notificaciones")
        self.sound_notifications_checkbox.setChecked(False)
        notif_layout.addWidget(self.sound_notifications_checkbox)

        layout.addWidget(notif_group)

        # Inicio
        startup_group = QGroupBox("🚀 Al Iniciar")
        startup_layout = QVLayout(startup_group)

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
        layout = QVLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # === BACKUPS AUTOMÁTICOS ===
        backup_group = QGroupBox("💾 Backups Automáticos")
        backup_layout = QVLayout(backup_group)
        backup_layout.setSpacing(12)

        backup_info = QLabel(
            "⚠️ Recomendado: Los backups te permiten recuperar archivos en caso de error o problema."
        )
        backup_info.setStyleSheet(ui_styles.STYLE_WARNING_LABEL)
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)

        self.auto_backup_checkbox = QCheckBox("Crear backup automáticamente antes de cada operación")
        self.auto_backup_checkbox.setChecked(True)
        backup_layout.addWidget(self.auto_backup_checkbox)

        layout.addWidget(backup_group)

        # === MODO SIMULACIÓN ===
        dryrun_group = QGroupBox("🧪 Modo Simulación")
        dryrun_layout = QVLayout(dryrun_group)
        dryrun_layout.setSpacing(12)

        dryrun_info = QLabel(
            "En modo simulación, las operaciones se analizan y muestran pero no se ejecutan realmente. "
            "Útil para verificar qué hará la aplicación antes de aplicar cambios."
        )
        dryrun_info.setStyleSheet(ui_styles.STYLE_SMALL_INFO_LABEL)
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
        from PyQt5.QtWidgets import QFileDialog
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
        from PyQt5.QtWidgets import QFileDialog
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
            logs_dir = None
            if hasattr(self, 'parent_window') and getattr(self.parent_window, 'logs_directory', None):
                logs_dir = str(self.parent_window.logs_directory)
            else:
                logs_dir = str(config.config.DEFAULT_LOG_DIR)

            if platform.system() == 'Windows':
                os.startfile(logs_dir)
            elif platform.system() == 'Darwin':
                subprocess.Popen(['open', logs_dir])
            else:
                subprocess.Popen(['xdg-open', logs_dir])

            try:
                if hasattr(self.parent_window, 'logger'):
                    self.parent_window.logger.info(f"Carpeta de logs abierta: {logs_dir}")
                else:
                    logging.getLogger('PhotokitManager').info(f"Carpeta de logs abierta: {logs_dir}")
            except Exception:
                logging.getLogger('PhotokitManager').info(f"Carpeta de logs abierta: {logs_dir}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo abrir la carpeta:\n{str(e)}"
            )

    def change_log_level(self, level_str):
        """Cambia el nivel de logging y actualiza config y logger del padre."""
        try:
            level_name = str(level_str).split()[0].upper()
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR
            }
            level = level_map.get(level_name, logging.INFO)

            config.Config.LOG_LEVEL = level_name

            if hasattr(self, 'parent_window') and getattr(self.parent_window, 'logging_manager', None):
                try:
                    self.parent_window.logging_manager.set_level(level_name)
                    if getattr(self.parent_window, 'app_logger', None):
                        self.parent_window.app_logger.setLevel(level)
                    if getattr(self.parent_window, 'logger', None):
                        self.parent_window.logger.setLevel(level)
                    self.parent_window.log_level = level_name
                    try:
                        self.parent_window.app_logger.info(f"Nivel de log cambiado a: {level_name}")
                    except Exception:
                        if getattr(self.parent_window, 'logger', None):
                            self.parent_window.logger.info(f"Nivel de log cambiado a: {level_name}")
                except Exception:
                    logging.getLogger('PhotokitManager').info(f"Nivel de log cambiado a: {level_name}")
            else:
                logging.getLogger('PhotokitManager').setLevel(level)
                logging.getLogger('PhotokitManager').info(f"Nivel de log cambiado a: {level_name}")

        except Exception:
            logging.getLogger('PhotokitManager').exception("Error cambiando nivel de log")

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
        new_logs_dir = Path(self.logs_edit.text())
        try:
            if getattr(self, 'parent_window', None) and getattr(self.parent_window, 'logging_manager', None):
                try:
                    self.parent_window.logging_manager.change_logs_directory(new_logs_dir)
                    self.parent_window.logs_directory = self.parent_window.logging_manager.logs_directory
                    self.parent_window.log_file = self.parent_window.logging_manager.log_file
                    try:
                        self.parent_window.app_logger.info(f"Directorio de logs cambiado a: {new_logs_dir}")
                    except Exception:
                        if getattr(self.parent_window, 'logger', None):
                            self.parent_window.logger.info(f"Directorio de logs cambiado a: {new_logs_dir}")
                except Exception:
                    self.parent_window.logs_directory = new_logs_dir
                    try:
                        self.parent_window.app_logger.info(f"Directorio de logs cambiado a: {new_logs_dir}")
                    except Exception:
                        if getattr(self.parent_window, 'logger', None):
                            self.parent_window.logger.info(f"Directorio de logs cambiado a: {new_logs_dir}")
            else:
                if new_logs_dir != getattr(self.parent_window, 'logs_directory', None):
                    self.parent_window.logs_directory = new_logs_dir
                    try:
                        self.parent_window.app_logger.info(f"Directorio de logs cambiado a: {new_logs_dir}")
                    except Exception:
                        if getattr(self.parent_window, 'logger', None):
                            self.parent_window.logger.info(f"Directorio de logs cambiado a: {new_logs_dir}")

        except Exception:
            logging.getLogger('PhotokitManager').info(f"Directorio de logs cambiado a: {new_logs_dir}")

        level_text = self.log_level_combo.currentText()
        level = level_text.split(" ")[0]
        self.change_log_level(level)

        try:
            lvl = self.parent_window.app_logger.getEffectiveLevel()
            self.parent_window.app_logger.log(lvl, "Configuración guardada exitosamente")
        except Exception:
            try:
                self.parent_window.app_logger.info("Configuración guardada exitosamente")
            except Exception:
                if getattr(self.parent_window, 'logger', None):
                    self.parent_window.logger.info("Configuración guardada exitosamente")
                else:
                    logging.getLogger('PhotokitManager').info("Configuración guardada exitosamente")

        QMessageBox.information(
            self,
            "Guardado",
            "✅ Configuración guardada correctamente"
        )

        self.accept()
