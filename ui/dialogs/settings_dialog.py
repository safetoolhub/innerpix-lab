from pathlib import Path
import logging
import os
import platform
import subprocess
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QGroupBox, QVBoxLayout as QVLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFrame, 
    QMessageBox, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from config import Config
from ui.styles.design_system import DesignSystem
from utils.logger import set_global_log_level, get_logger
from utils.settings_manager import settings_manager
import logging


class SettingsDialog(QDialog):
    """Diálogo de configuración avanzada con persistencia"""

    # Señal emitida cuando se guardan cambios importantes que requieren actualización
    settings_saved = pyqtSignal()

    def __init__(self, parent=None, initial_tab=0):
        super().__init__(parent)
        self.parent_window = parent
        self.logger = logging.getLogger('PixaroLab.SettingsDialog')
        
        # Referencia al botón de guardar (se asignará en init_ui)
        self.save_button = None
        
        # Referencia al tab widget
        self.tabs = None
        
        # Valores originales para detectar cambios
        self.original_values = {}
        
        # Flag para evitar validaciones durante la carga inicial
        self._loading = True
        
        self.init_ui()
        self._load_current_settings()
        
        # Cambiar a la pestaña inicial si se especificó
        if initial_tab > 0 and self.tabs:
            self.tabs.setCurrentIndex(initial_tab)
        
        # Conectar señales para detectar cambios
        self._connect_change_signals()
        
        # Marcar que la carga inicial terminó
        self._loading = False
        
        # Validar estado inicial (debe estar deshabilitado sin cambios)
        self._validate_changes()

    def init_ui(self):
        self.setWindowTitle("Configuración")
        self.setModal(True)
        self.resize(800, 650)
        
        # Aplicar estilo base del DesignSystem
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
            }}
            {DesignSystem.get_tooltip_style()}
        """)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Crear pestañas usando estilo del DesignSystem
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(DesignSystem.get_tab_widget_style())

        # === PESTAÑA 1: GENERAL ===
        general_tab = self._create_general_tab()
        self.tabs.addTab(general_tab, "General")

        # === PESTAÑA 2: BACKUPS ===
        backups_tab = self._create_backups_tab()
        self.tabs.addTab(backups_tab, "Backup y Logs")

        # === PESTAÑA 3: AVANZADO ===
        advanced_tab = self._create_advanced_tab()
        self.tabs.addTab(advanced_tab, "Avanzado")

        main_layout.addWidget(self.tabs)

        # Footer con botones - Material Design
        footer = self._create_footer()
        main_layout.addWidget(footer)

    def _create_footer(self):
        """Crea el footer del diálogo con botones estilizados"""
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border-top: 1px solid {DesignSystem.COLOR_BORDER};
                padding: {DesignSystem.SPACE_16}px;
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_16
        )
        footer_layout.setSpacing(DesignSystem.SPACE_12)

        # Botón restaurar valores por defecto
        restore_btn = QPushButton("Restaurar valores por defecto")
        restore_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        restore_btn.clicked.connect(self.restore_defaults)
        restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(restore_btn)

        footer_layout.addStretch()

        # Botón Cancelar - estilo secundario
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(cancel_btn)

        # Botón Guardar - estilo success (primary)
        self.save_button = QPushButton("Guardar Cambios")
        self.save_button.setEnabled(False)
        # Usamos primary button style pero podríamos personalizar si queremos verde específico
        # Por consistencia con el resto de la app, usamos primary (azul) o success (verde)
        # DesignSystem no tiene get_success_button_style explícito, pero podemos usar primary
        # o construir uno similar si es crítico. Por ahora usaremos primary para consistencia.
        self.save_button.setStyleSheet(DesignSystem.get_primary_button_style())
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(self.save_button)

        return footer

    def _create_groupbox(self, title: str) -> QGroupBox:
        """Crea un QGroupBox con estilo consistente del DesignSystem"""
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: {DesignSystem.SPACE_8}px;
                padding-top: {DesignSystem.SPACE_24}px;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {DesignSystem.SPACE_16}px;
                padding: 0 {DesignSystem.SPACE_4}px;
                background-color: {DesignSystem.COLOR_SURFACE}; /* Ensure title background matches */
            }}
        """)
        return group

    def _create_info_label(self, text: str, warning: bool = False) -> QLabel:
        """Crea un QLabel informativo con estilo consistente"""
        label = QLabel(text)
        label.setWordWrap(True)
        
        if warning:
            label.setStyleSheet(f"""
                QLabel {{
                    color: {DesignSystem.COLOR_WARNING};
                    font-size: {DesignSystem.FONT_SIZE_BASE}px;
                    padding: {DesignSystem.SPACE_12}px;
                    background-color: {DesignSystem.COLOR_BG_4};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    border: 1px solid {DesignSystem.COLOR_WARNING};
                }}
            """)
        else:
            label.setStyleSheet(f"""
                QLabel {{
                    color: {DesignSystem.COLOR_TEXT_SECONDARY};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-style: italic;
                    padding: {DesignSystem.SPACE_4}px 0;
                }}
            """)
        return label

    def _create_directory_input(self, text: str = "") -> QLineEdit:
        """Crea un QLineEdit para mostrar directorios con estilo consistente"""
        edit = QLineEdit(text)
        edit.setReadOnly(True)
        edit.setStyleSheet(DesignSystem.get_lineedit_style())
        return edit

    def _create_browse_button(self, tooltip: str = "") -> QPushButton:
        """Crea un botón 'Cambiar...' con estilo consistente"""
        btn = QPushButton("Cambiar...")
        btn.setMinimumWidth(120)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        return btn

    def _create_general_tab(self):
        """Pestaña de configuración general"""
        widget = QWidget()
        widget.setObjectName("general_tab")
        widget.setStyleSheet(f"#general_tab {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}")
        layout = QVLayout(widget)
        layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20
        )
        layout.setSpacing(DesignSystem.SPACE_20)

        # === CONFIRMACIONES ===
        confirm_group = self._create_groupbox("Confirmaciones")
        confirm_layout = QVLayout(confirm_group)
        confirm_layout.setSpacing(DesignSystem.SPACE_12)

        self.confirm_operations_checkbox = QCheckBox("Mostrar diálogo de confirmación antes de ejecutar operaciones")
        self.confirm_operations_checkbox.setChecked(True)
        self.confirm_operations_checkbox.setToolTip("Muestra un resumen antes de aplicar cambios")
        self.confirm_operations_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        confirm_layout.addWidget(self.confirm_operations_checkbox)

        self.confirm_delete_checkbox = QCheckBox("Pedir confirmación adicional para operaciones de eliminación")
        self.confirm_delete_checkbox.setChecked(True)
        self.confirm_delete_checkbox.setToolTip("Doble confirmación para operaciones que eliminan archivos")
        self.confirm_delete_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        confirm_layout.addWidget(self.confirm_delete_checkbox)

        layout.addWidget(confirm_group)

        # === NOTIFICACIONES ===
        notif_group = self._create_groupbox("Notificaciones")
        notif_layout = QVLayout(notif_group)
        notif_layout.setSpacing(DesignSystem.SPACE_12)

        self.show_notifications_checkbox = QCheckBox("Mostrar notificación al completar operaciones")
        self.show_notifications_checkbox.setChecked(True)
        self.show_notifications_checkbox.setToolTip("Muestra una notificación cuando se completan las operaciones")
        self.show_notifications_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        notif_layout.addWidget(self.show_notifications_checkbox)

        layout.addWidget(notif_group)

        # === INTERFAZ ===
        interface_group = self._create_groupbox("Interfaz")
        interface_layout = QVLayout(interface_group)
        interface_layout.setSpacing(DesignSystem.SPACE_12)

        self.show_full_path_checkbox = QCheckBox("Mostrar ruta completa del directorio en la barra de búsqueda")
        self.show_full_path_checkbox.setChecked(True)
        self.show_full_path_checkbox.setToolTip(
            "Si está activado, muestra la ruta completa del directorio (ej: /home/usuario/Fotos).\n"
            "Si está desactivado, solo muestra el nombre de la carpeta (ej: Fotos)."
        )
        self.show_full_path_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        interface_layout.addWidget(self.show_full_path_checkbox)

        layout.addWidget(interface_group)

        # === MODO SIMULACIÓN ===
        dryrun_group = self._create_groupbox("Modo Simulación (Dry Run)")
        dryrun_layout = QVLayout(dryrun_group)
        dryrun_layout.setSpacing(DesignSystem.SPACE_12)

        dryrun_info = self._create_info_label(
            "En modo simulación, las operaciones se analizan y muestran pero <b>no se ejecutan</b> realmente. "
            "Útil para verificar qué hará la aplicación antes de aplicar cambios."
        )
        dryrun_layout.addWidget(dryrun_info)

        self.dry_run_default_checkbox = QCheckBox("Activar modo simulación por defecto en todas las operaciones")
        self.dry_run_default_checkbox.setChecked(False)
        self.dry_run_default_checkbox.setToolTip(
            "Si se activa, todos los diálogos de eliminación (HEIC, Live Photos, Duplicados)\n"
            "mostrarán el checkbox de 'Modo simulación' marcado por defecto.\n"
            "Esto añade una capa extra de seguridad para evitar eliminaciones accidentales."
        )
        self.dry_run_default_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        dryrun_layout.addWidget(self.dry_run_default_checkbox)

        layout.addWidget(dryrun_group)

        layout.addStretch()
        return widget



    def _create_backups_tab(self):
        """Pestaña de configuración de backups"""
        widget = QWidget()
        widget.setObjectName("backups_tab")
        widget.setStyleSheet(f"#backups_tab {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}")
        layout = QVLayout(widget)
        layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20
        )
        layout.setSpacing(DesignSystem.SPACE_20)

        # === BACKUPS AUTOMÁTICOS ===
        auto_backup_group = self._create_groupbox("Backups Automáticos")
        auto_backup_layout = QVLayout(auto_backup_group)
        auto_backup_layout.setSpacing(DesignSystem.SPACE_12)

        backup_info = self._create_info_label(
            "<b>Muy Recomendado:</b> Los backups te permiten recuperar archivos en caso de error.",
            warning=True
        )
        auto_backup_layout.addWidget(backup_info)

        self.auto_backup_checkbox = QCheckBox("Crear backup automáticamente antes de cada operación destructiva")
        self.auto_backup_checkbox.setChecked(True)
        self.auto_backup_checkbox.setToolTip(
            "Si está activado, se creará una copia de seguridad de los archivos antes de:\n"
            "• Renombrar archivos\n"
            "• Eliminar Live Photos\n"
            "• Eliminar duplicados HEIC\n"
            "• Organizar carpetas"
        )
        self.auto_backup_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        auto_backup_layout.addWidget(self.auto_backup_checkbox)

        layout.addWidget(auto_backup_group)

        # === DIRECTORIO DE BACKUPS ===
        backup_dir_group = self._create_groupbox("Directorio de Backups")
        backup_dir_layout = QVLayout(backup_dir_group)
        backup_dir_layout.setSpacing(DesignSystem.SPACE_12)

        backup_dir_info = self._create_info_label("Ubicación donde se guardan las copias de seguridad automáticas.")
        backup_dir_layout.addWidget(backup_dir_info)

        backup_row = QHBoxLayout()
        backup_row.setSpacing(DesignSystem.SPACE_12)
        
        backup_label = QLabel("Carpeta:")
        backup_label.setMinimumWidth(80)
        backup_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
        """)
        backup_row.addWidget(backup_label)

        self.backup_edit = self._create_directory_input(str(Config.DEFAULT_BACKUP_DIR))
        backup_row.addWidget(self.backup_edit)

        browse_backup_btn = self._create_browse_button("Cambiar ubicación de backups")
        browse_backup_btn.clicked.connect(self.browse_backup_directory)
        backup_row.addWidget(browse_backup_btn)

        backup_dir_layout.addLayout(backup_row)
        layout.addWidget(backup_dir_group)

        # === BACKUP Y LOGS ===
        logs_group = self._create_groupbox("Logs y diagnóstico")
        logs_layout = QVLayout(logs_group)
        logs_layout.setSpacing(DesignSystem.SPACE_12)

        logs_info = self._create_info_label(
            "Los archivos de log registran todas las operaciones para diagnóstico y auditoría."
        )
        logs_layout.addWidget(logs_info)

        # Directorio de logs
        logs_dir_layout = QHBoxLayout()
        logs_dir_layout.setSpacing(DesignSystem.SPACE_12)
        
        logs_label = QLabel("Carpeta:")
        logs_label.setMinimumWidth(120)
        logs_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
        """)
        logs_dir_layout.addWidget(logs_label)

        self.logs_edit = self._create_directory_input(
            str(settings_manager.get_logs_directory() or Config.DEFAULT_LOG_DIR)
        )
        logs_dir_layout.addWidget(self.logs_edit)

        browse_logs_btn = self._create_browse_button("Cambiar ubicación de logs")
        browse_logs_btn.clicked.connect(self.browse_logs_directory)
        logs_dir_layout.addWidget(browse_logs_btn)

        logs_layout.addLayout(logs_dir_layout)

        # Nivel de log
        log_level_layout = QHBoxLayout()
        log_level_layout.setSpacing(DesignSystem.SPACE_12)
        
        log_level_label = QLabel("Nivel de detalle:")
        log_level_label.setMinimumWidth(120)
        log_level_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
        """)
        log_level_layout.addWidget(log_level_label)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems([
            "DEBUG - Máximo detalle (para desarrollo)",
            "INFO - Normal (recomendado)",
            "WARNING - Solo advertencias",
            "ERROR - Solo errores críticos"
        ])
        self.log_level_combo.setStyleSheet(DesignSystem.get_combobox_style())
        self.log_level_combo.setToolTip(
            "DEBUG: Toda la información técnica\n"
            "INFO: Operaciones normales\n"
            "WARNING: Situaciones inusuales\n"
            "ERROR: Solo errores graves"
        )
        self.log_level_combo.currentTextChanged.connect(self.change_log_level)
        log_level_layout.addWidget(self.log_level_combo)
        log_level_layout.addStretch()

        logs_layout.addLayout(log_level_layout)

        # Botón abrir carpeta de logs
        open_logs_btn = QPushButton("Abrir carpeta de logs")
        open_logs_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        open_logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_logs_btn.clicked.connect(self.open_logs_folder)
        logs_layout.addWidget(open_logs_btn)

        layout.addWidget(logs_group)

        layout.addStretch()
        return widget

    def _create_advanced_tab(self):
        """Pestaña de configuración avanzada"""
        widget = QWidget()
        widget.setObjectName("advanced_tab")
        widget.setStyleSheet(f"#advanced_tab {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}")
        layout = QVLayout(widget)
        layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20
        )
        layout.setSpacing(DesignSystem.SPACE_20)

        # === RENDIMIENTO ===
        perf_group = self._create_groupbox("Rendimiento")
        perf_layout = QVLayout(perf_group)
        perf_layout.setSpacing(DesignSystem.SPACE_12)

        workers_layout = QHBoxLayout()
        workers_layout.setSpacing(DesignSystem.SPACE_12)
        
        workers_label = QLabel("Hilos de procesamiento:")
        workers_label.setMinimumWidth(180)
        workers_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
        """)
        workers_layout.addWidget(workers_label)

        from ui.widgets.custom_spinbox import CustomSpinBox
        self.max_workers_spin = CustomSpinBox()
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

        perf_info = self._create_info_label(
            "Cambiar el número de hilos requiere reiniciar la aplicación para tener efecto completo."
        )
        perf_layout.addWidget(perf_info)
        
        # Checkbox para metadatos de video
        self.use_video_metadata_checkbox = QCheckBox("Extraer metadatos de archivos de video (lento)")
        self.use_video_metadata_checkbox.setChecked(Config.USE_VIDEO_METADATA)
        self.use_video_metadata_checkbox.setToolTip(
            "Habilitar extracción de metadatos de videos usando ffprobe.\n"
            "ADVERTENCIA: Este proceso es muy lento y puede afectar el rendimiento.\n"
            "La aplicación está optimizada para imágenes, por lo que esta opción\n"
            "está deshabilitada por defecto."
        )
        self.use_video_metadata_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        perf_layout.addWidget(self.use_video_metadata_checkbox)

        layout.addWidget(perf_group)

        # === DEPURACIÓN ===
        debug_group = self._create_groupbox("Depuración")
        debug_layout = QVLayout(debug_group)
        debug_layout.setSpacing(DesignSystem.SPACE_12)

        clear_settings_btn = QPushButton("Restablecer TODA la configuración guardada")
        clear_settings_btn.setStyleSheet(DesignSystem.get_danger_button_style())
        clear_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_settings_btn.clicked.connect(self.clear_all_settings)
        debug_layout.addWidget(clear_settings_btn)

        debug_info = self._create_info_label(
            "Esto eliminará todas las preferencias guardadas y volverá a los valores por defecto."
        )
        debug_info.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_WARNING};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-style: italic;
                padding: {DesignSystem.SPACE_4}px 0;
            }}
        """)
        debug_layout.addWidget(debug_info)

        layout.addWidget(debug_group)

        layout.addStretch()
        return widget


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
            self.show_full_path_checkbox.setChecked(settings_manager.get_show_full_path())

            # Advanced tab
            self.max_workers_spin.setValue(settings_manager.get_max_workers(Config.MAX_WORKERS))
            self.dry_run_default_checkbox.setChecked(settings_manager.get_bool(settings_manager.KEY_DRY_RUN_DEFAULT, False))
            self.use_video_metadata_checkbox.setChecked(settings_manager.get_bool(settings_manager.KEY_USE_VIDEO_METADATA, False))

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

            # Guardar valores originales para detectar cambios
            self._save_original_values()

            self.logger.debug("Configuración cargada desde settings_manager")

        except Exception as e:
            self.logger.exception(f"Error cargando configuración: {e}")
    
    def _save_original_values(self):
        """Guarda los valores actuales como originales para detectar cambios"""
        self.original_values = {
            'logs_dir': self.logs_edit.text(),
            'backup_dir': self.backup_edit.text(),
            'log_level': self.log_level_combo.currentIndex(),
            'auto_backup': self.auto_backup_checkbox.isChecked(),
            'confirm_ops': self.confirm_operations_checkbox.isChecked(),
            'confirm_delete': self.confirm_delete_checkbox.isChecked(),
            'show_notif': self.show_notifications_checkbox.isChecked(),
            'show_path': self.show_full_path_checkbox.isChecked(),
            'max_workers': self.max_workers_spin.value(),
            'dry_run': self.dry_run_default_checkbox.isChecked(),
            'use_video_metadata': self.use_video_metadata_checkbox.isChecked(),
        }
        self.logger.debug(f"Valores originales guardados: {self.original_values}")
    
    def _connect_change_signals(self):
        """Conecta señales de cambio de todos los widgets para detectar modificaciones"""
        # Checkboxes
        self.auto_backup_checkbox.stateChanged.connect(lambda: self._on_widget_changed("auto_backup"))
        self.confirm_operations_checkbox.stateChanged.connect(lambda: self._on_widget_changed("confirm_ops"))
        self.confirm_delete_checkbox.stateChanged.connect(lambda: self._on_widget_changed("confirm_delete"))
        self.show_notifications_checkbox.stateChanged.connect(lambda: self._on_widget_changed("show_notif"))
        self.show_full_path_checkbox.stateChanged.connect(lambda: self._on_widget_changed("show_path"))
        self.dry_run_default_checkbox.stateChanged.connect(lambda: self._on_widget_changed("dry_run"))
        self.use_video_metadata_checkbox.stateChanged.connect(lambda: self._on_widget_changed("use_video_metadata"))
        
        # Spinbox
        self.max_workers_spin.valueChanged.connect(lambda: self._on_widget_changed("max_workers"))
        
        # Combobox
        self.log_level_combo.currentIndexChanged.connect(lambda: self._on_widget_changed("log_level"))
        
        # Line edits (directorios)
        self.logs_edit.textChanged.connect(lambda: self._on_widget_changed("logs_dir"))
        self.backup_edit.textChanged.connect(lambda: self._on_widget_changed("backup_dir"))
    
    def _on_widget_changed(self, widget_name):
        """Manejador común para cambios en widgets"""
        self.logger.debug(f"Widget changed: {widget_name}")
        self._validate_changes()
    
    def _validate_changes(self):
        """
        Valida si hay cambios reales comparando valores actuales con originales.
        Habilita/deshabilita el botón Guardar según corresponda.
        """
        # Ignorar validaciones durante la carga inicial
        if getattr(self, '_loading', True):
            return
        
        if not self.original_values or not self.save_button:
            return
        
        # Comparar cada valor
        current_logs = self.logs_edit.text()
        original_logs = self.original_values['logs_dir']
        logs_changed = current_logs != original_logs
        
        current_backup = self.backup_edit.text()
        original_backup = self.original_values['backup_dir']
        backup_changed = current_backup != original_backup
        
        current_level = self.log_level_combo.currentIndex()
        original_level = self.original_values['log_level']
        level_changed = current_level != original_level
        
        current_auto_backup = self.auto_backup_checkbox.isChecked()
        original_auto_backup = self.original_values['auto_backup']
        auto_backup_changed = current_auto_backup != original_auto_backup
        
        current_confirm_ops = self.confirm_operations_checkbox.isChecked()
        original_confirm_ops = self.original_values['confirm_ops']
        confirm_ops_changed = current_confirm_ops != original_confirm_ops
        
        current_confirm_delete = self.confirm_delete_checkbox.isChecked()
        original_confirm_delete = self.original_values['confirm_delete']
        confirm_delete_changed = current_confirm_delete != original_confirm_delete
        
        current_show_notif = self.show_notifications_checkbox.isChecked()
        original_show_notif = self.original_values['show_notif']
        show_notif_changed = current_show_notif != original_show_notif
        
        current_show_path = self.show_full_path_checkbox.isChecked()
        original_show_path = self.original_values['show_path']
        show_path_changed = current_show_path != original_show_path
        
        current_max_workers = self.max_workers_spin.value()
        original_max_workers = self.original_values['max_workers']
        max_workers_changed = current_max_workers != original_max_workers
        
        current_dry_run = self.dry_run_default_checkbox.isChecked()
        original_dry_run = self.original_values['dry_run']
        dry_run_changed = current_dry_run != original_dry_run
        
        current_use_video_metadata = self.use_video_metadata_checkbox.isChecked()
        original_use_video_metadata = self.original_values['use_video_metadata']
        use_video_metadata_changed = current_use_video_metadata != original_use_video_metadata
        
        has_changes = (
            logs_changed or backup_changed or level_changed or auto_backup_changed or
            confirm_ops_changed or confirm_delete_changed or show_notif_changed or
            show_path_changed or max_workers_changed or dry_run_changed or
            use_video_metadata_changed
        )
        
        # Habilitar/deshabilitar botón según haya cambios
        self.save_button.setEnabled(has_changes)
        
        # Log para debugging (solo si cambia el estado)
        if has_changes != getattr(self, '_last_has_changes', None):
            self.logger.debug(f"Cambios detectados: {has_changes}")
            self._last_has_changes = has_changes
    
    def _requires_restart_changed(self):
        """
        Detecta si algún cambio requiere reiniciar la aplicación.
        
        Settings que requieren reinicio:
        - Pestaña Avanzado: max_workers, use_video_metadata
        - Pestaña Backup y Logs: logs_dir, backup_dir, log_level
        
        Returns:
            bool: True si hay cambios que requieren reinicio
        """
        if not self.original_values:
            return False
        
        # Verificar cambios en settings que requieren reinicio
        restart_required_changes = [
            # Avanzado tab
            self.max_workers_spin.value() != self.original_values['max_workers'],
            self.use_video_metadata_checkbox.isChecked() != self.original_values['use_video_metadata'],
            # Backup y Logs tab
            self.logs_edit.text() != self.original_values['logs_dir'],
            self.backup_edit.text() != self.original_values['backup_dir'],
            self.log_level_combo.currentIndex() != self.original_values['log_level'],
        ]
        
        return any(restart_required_changes)
    
    def _restart_application(self):
        """
        Reinicia la aplicación.
        Usa sys.executable para obtener el intérprete de Python y os.execv para reiniciar.
        """
        try:
            self.logger.info("Reiniciando aplicación...")
            python = sys.executable
            # os.execv reemplaza el proceso actual con uno nuevo
            os.execv(python, [python] + sys.argv)
        except Exception as e:
            self.logger.exception(f"Error al reiniciar la aplicación: {e}")
            QMessageBox.critical(
                self,
                "Error al Reiniciar",
                f"No se pudo reiniciar la aplicación:\n{str(e)}\n\n"
                "Por favor, reinicia manualmente la aplicación."
            )

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
            # La señal textChanged se dispara automáticamente

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
            # La señal textChanged se dispara automáticamente
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
            "Confirmar Eliminacion",
            "¿Estas seguro de que deseas eliminar TODA la configuracion guardada?\n\n"
            "Esto incluye:\n"
            "• Preferencias de backup\n"
            "• Carpetas personalizadas\n"
            "• Nivel de logging\n"
            "• Todas las demas configuraciones\n\n"
            "La aplicacion volvera a los valores por defecto.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                settings_manager.clear_all()
                self.logger.info("Toda la configuración ha sido eliminada")
                QMessageBox.information(
                    self,
                    "Configuracion Eliminada",
                    "Se ha eliminado toda la configuracion.\n"
                    "Se recomienda reiniciar la aplicacion."
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
        """Cambia el nivel de logging en caliente y actualiza config y logger del padre."""
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
            
            # Actualizar TODOS los loggers globalmente (cambio en caliente)
            set_global_log_level(level)
            
            # Registrar el cambio
            self.logger.info("=" * 80)
            self.logger.info(f"Nivel de log cambiado a: {level_name}")
            self.logger.info("=" * 80)
            
            # Guardar en settings manager
            settings_manager.set_log_level(level_name)
            
            # Actualizar también el log_level de la ventana padre si existe
            if self.parent_window and hasattr(self.parent_window, 'log_level'):
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
            self.show_notifications_checkbox.setChecked(True)
            self.show_full_path_checkbox.setChecked(True)
            self.dry_run_default_checkbox.setChecked(False)
            self.max_workers_spin.setValue(Config.MAX_WORKERS)
            
            # Revalidar cambios (las señales ya se dispararán automáticamente)

            QMessageBox.information(self, "Restaurado", "Configuracion restaurada a valores por defecto.\n\n"
                                   "Presiona 'Guardar Cambios' para aplicar.")

    def save_settings(self):
        """Guarda la configuración en el settings_manager"""
        try:
            # === DETECTAR CAMBIOS REALES PRIMERO ===
            # Evita operaciones costosas si no hay cambios
            
            # Valores actuales (desde settings_manager)
            current_logs_dir = settings_manager.get_logs_directory()
            current_backup_dir = settings_manager.get_backup_directory()
            current_log_level = settings_manager.get_log_level("INFO")
            current_auto_backup = settings_manager.get_auto_backup_enabled()
            current_confirm_ops = settings_manager.get_confirm_operations()
            current_confirm_delete = settings_manager.get_confirm_delete()
            current_show_notif = settings_manager.get_show_notifications()
            current_show_path = settings_manager.get_show_full_path()
            current_max_workers = settings_manager.get_max_workers(Config.MAX_WORKERS)
            current_dry_run = settings_manager.get_bool(settings_manager.KEY_DRY_RUN_DEFAULT, False)
            current_use_video_metadata = settings_manager.get_bool(settings_manager.KEY_USE_VIDEO_METADATA, False)
            
            # Valores nuevos (desde UI)
            new_logs_dir = Path(self.logs_edit.text())
            new_backup_dir = Path(self.backup_edit.text())
            new_log_level = self.log_level_combo.currentText().split()[0].split(" - ")[0].upper()
            new_auto_backup = self.auto_backup_checkbox.isChecked()
            new_confirm_ops = self.confirm_operations_checkbox.isChecked()
            new_confirm_delete = self.confirm_delete_checkbox.isChecked()
            new_show_notif = self.show_notifications_checkbox.isChecked()
            new_show_path = self.show_full_path_checkbox.isChecked()
            new_max_workers = self.max_workers_spin.value()
            new_dry_run = self.dry_run_default_checkbox.isChecked()
            new_use_video_metadata = self.use_video_metadata_checkbox.isChecked()
            
            # Detectar qué cambió
            logs_dir_changed = (current_logs_dir != new_logs_dir)
            backup_dir_changed = (current_backup_dir != new_backup_dir)
            log_level_changed = (current_log_level != new_log_level)
            any_setting_changed = (
                logs_dir_changed or backup_dir_changed or log_level_changed or
                current_auto_backup != new_auto_backup or
                current_confirm_ops != new_confirm_ops or
                current_confirm_delete != new_confirm_delete or
                current_show_notif != new_show_notif or
                current_show_path != new_show_path or
                current_max_workers != new_max_workers or
                current_dry_run != new_dry_run or
                current_use_video_metadata != new_use_video_metadata
            )
            
            # Si NO hay cambios, cerrar inmediatamente sin operaciones costosas
            if not any_setting_changed:
                self.logger.debug("No hay cambios en la configuración, cerrando diálogo")
                self.accept()
                return
            
            # === APLICAR SOLO LOS CAMBIOS NECESARIOS ===
            
            # Directorios (solo si cambiaron)
            if logs_dir_changed:
                settings_manager.set_logs_directory(new_logs_dir)
                
                # Cambiar directorio de logs usando la nueva API
                from utils.logger import change_logs_directory
                try:
                    new_log_file, new_logs_dir_resolved = change_logs_directory(new_logs_dir)
                    self.logger.info(f"Directorio de logs cambiado a: {new_logs_dir_resolved}")
                    self.logger.info(f"Nuevo archivo de log: {new_log_file}")
                except Exception as e:
                    self.logger.warning(f"No se pudo cambiar directorio de logs: {e}")
            
            if backup_dir_changed:
                settings_manager.set_backup_directory(new_backup_dir)

            # Nivel de log (solo si cambió)
            if log_level_changed:
                self.change_log_level(self.log_level_combo.currentText())

            # General (solo si cambiaron)
            if current_auto_backup != new_auto_backup:
                settings_manager.set_auto_backup_enabled(new_auto_backup)
            if current_confirm_ops != new_confirm_ops:
                settings_manager.set(settings_manager.KEY_CONFIRM_OPERATIONS, new_confirm_ops)
            if current_confirm_delete != new_confirm_delete:
                settings_manager.set(settings_manager.KEY_CONFIRM_DELETE, new_confirm_delete)
            if current_show_notif != new_show_notif:
                settings_manager.set(settings_manager.KEY_SHOW_NOTIFICATIONS, new_show_notif)
            if current_show_path != new_show_path:
                settings_manager.set_show_full_path(new_show_path)

            # Avanzado (solo si cambiaron)
            if current_max_workers != new_max_workers:
                settings_manager.set(settings_manager.KEY_MAX_WORKERS, new_max_workers)
            if current_dry_run != new_dry_run:
                settings_manager.set(settings_manager.KEY_DRY_RUN_DEFAULT, new_dry_run)
            if current_use_video_metadata != new_use_video_metadata:
                settings_manager.set(settings_manager.KEY_USE_VIDEO_METADATA, new_use_video_metadata)
                # Actualizar Config.USE_VIDEO_METADATA para que tenga efecto inmediato
                Config.USE_VIDEO_METADATA = new_use_video_metadata

            self.logger.info("Configuración guardada exitosamente")

            # Emitir señal de cambios guardados
            self.settings_saved.emit()

            # ✅ IMPORTANTE: Cerrar el diálogo ANTES de mostrar el mensaje
            # Esto evita problemas con la pila modal
            self.accept()

            # Verificar si se requiere reiniciar la aplicación
            needs_restart = self._requires_restart_changed()
            
            if needs_restart:
                # Mostrar diálogo de confirmación para reiniciar
                restart_msg = (
                    "Se han guardado cambios que requieren reiniciar la aplicación para tomar efecto:\n\n"
                )
                
                # Listar qué cambió
                changes_list = []
                if self.max_workers_spin.value() != self.original_values['max_workers']:
                    changes_list.append("• Número de hilos de procesamiento")
                if self.use_video_metadata_checkbox.isChecked() != self.original_values['use_video_metadata']:
                    changes_list.append("• Extracción de metadatos de video")
                if self.logs_edit.text() != self.original_values['logs_dir']:
                    changes_list.append("• Directorio de logs")
                if self.backup_edit.text() != self.original_values['backup_dir']:
                    changes_list.append("• Directorio de backups")
                if self.log_level_combo.currentIndex() != self.original_values['log_level']:
                    changes_list.append("• Nivel de detalle de logs")
                
                restart_msg += "\n".join(changes_list)
                restart_msg += "\n\n¿Desea reiniciar la aplicación ahora?"
                
                reply = QMessageBox.question(
                    self.parent_window if self.parent_window else self,
                    "Reiniciar Aplicación",
                    restart_msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Reiniciar la aplicación
                    self._restart_application()
                else:
                    # Usuario rechazó reiniciar - mostrar advertencia
                    QMessageBox.warning(
                        self.parent_window if self.parent_window else self,
                        "Reinicio Requerido",
                        "Los cambios se han guardado correctamente, pero NO tomarán efecto "
                        "hasta que reinicie la aplicación.\n\n"
                        "La aplicación puede no comportarse como espera hasta que se reinicie."
                    )
            else:
                # No se requiere reinicio - mensaje informativo normal
                msg_text = "La configuracion se ha guardado correctamente."
                if logs_dir_changed:
                    msg_text += "\n\nEl directorio de logs ha cambiado. Los nuevos logs se escribirán en la nueva ubicación."
                
                QMessageBox.information(
                    self.parent_window if self.parent_window else self,
                    "Configuracion Guardada",
                    msg_text
                )

        except Exception as e:
            self.logger.exception(f"Error guardando configuración: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo guardar la configuración:\n{str(e)}"
            )
