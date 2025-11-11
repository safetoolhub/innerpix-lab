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
from ui.styles.design_system import DesignSystem
from utils.logger import set_global_log_level, get_logger
from utils.settings_manager import settings_manager
import logging


class SettingsDialog(QDialog):
    """Diálogo de configuración avanzada con persistencia"""

    # Señal emitida cuando se guardan cambios importantes que requieren actualización
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.logger = logging.getLogger('PixaroLab.SettingsDialog')
        
        # Referencia al botón de guardar (se asignará en init_ui)
        self.save_button = None
        
        # Valores originales para detectar cambios
        self.original_values = {}
        
        # Flag para evitar validaciones durante la carga inicial
        self._loading = True
        
        self.init_ui()
        self._load_current_settings()
        
        # Conectar señales para detectar cambios
        self._connect_change_signals()
        
        # Marcar que la carga inicial terminó
        self._loading = False
        
        # Validar estado inicial (debe estar deshabilitado sin cambios)
        self._validate_changes()

    def init_ui(self):
        self.setWindowTitle("Configuracion")
        self.setModal(True)
        self.resize(750, 600)
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())

        # Layout principal con pestañas
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Crear pestañas para mejor organización
        tabs = QTabWidget()
        tabs.setStyleSheet(DesignSystem.get_tab_widget_style())

        # === PESTAÑA 1: GENERAL ===
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "General")

        # === PESTAÑA 2: DIRECTORIOS ===
        dirs_tab = self._create_directories_tab()
        tabs.addTab(dirs_tab, "Directorios")

        # === PESTAÑA 3: AVANZADO ===
        advanced_tab = self._create_advanced_tab()
        tabs.addTab(advanced_tab, "Avanzado")

        main_layout.addWidget(tabs)

        # Footer con botones
        footer = QFrame()
        footer.setObjectName("dialog-footer")
        footer.setStyleSheet(f"""
            QFrame#dialog-footer {{
                background-color: {DesignSystem.COLOR_BG_1};
                border-top: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(15, 10, 15, 10)

        # Botón restaurar valores por defecto
        restore_btn = QPushButton("Restaurar valores por defecto")
        restore_btn.setObjectName("restore-button")
        restore_btn.setStyleSheet(f"""
            QPushButton#restore-button {{
                background-color: {DesignSystem.COLOR_WARNING};
                color: {DesignSystem.COLOR_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 8px 16px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
            QPushButton#restore-button:hover {{
                background-color: {DesignSystem.COLOR_WARNING_HOVER};
            }}
        """)
        restore_btn.clicked.connect(self.restore_defaults)
        footer_layout.addWidget(restore_btn)

        footer_layout.addStretch()

        # Botones estándar con estilo Material Design
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        
        # Guardar referencia al botón Save
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("Guardar Cambios")
        self.save_button.setEnabled(False)  # Iniciar deshabilitado
        # Estilo personalizado para botón de guardar (verde) similar a primary pero con color success
        self.save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SUCCESS};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: #059669;
            }}
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """)
        
        # Aplicar estilo secondary al botón Cancel
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("Cancelar")
        cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        
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
        backup_group = QGroupBox("Backups Automaticos")
        backup_group.setObjectName("settings-groupbox")
        backup_group.setStyleSheet(f"""
            QGroupBox#settings-groupbox {{
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox#settings-groupbox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
        backup_layout = QVLayout(backup_group)
        backup_layout.setSpacing(12)

        backup_info = QLabel(
            "<b>Muy Recomendado:</b> Los backups te permiten recuperar archivos en caso de error."
        )
        backup_info.setObjectName("warning-label")
        backup_info.setStyleSheet(f"""
            QLabel#warning-label {{
                color: {DesignSystem.COLOR_WARNING};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                padding: 8px;
                background-color: {DesignSystem.COLOR_BG_4};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                border: 1px solid {DesignSystem.COLOR_WARNING};
            }}
        """)
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)

        self.auto_backup_checkbox = QCheckBox("Crear backup automáticamente antes de cada operación destructiva")
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
        confirm_group = QGroupBox("Confirmaciones")
        confirm_group.setObjectName("settings-groupbox")
        confirm_group.setStyleSheet(f"""
            QGroupBox#settings-groupbox {{
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox#settings-groupbox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
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
        notif_group = QGroupBox("Notificaciones")
        notif_group.setObjectName("settings-groupbox")
        notif_group.setStyleSheet(f"""
            QGroupBox#settings-groupbox {{
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox#settings-groupbox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
        notif_layout = QVLayout(notif_group)
        notif_layout.setSpacing(10)

        self.show_notifications_checkbox = QCheckBox("Mostrar notificación al completar operaciones")
        self.show_notifications_checkbox.setChecked(True)
        self.show_notifications_checkbox.setToolTip("Muestra una notificación cuando se completan las operaciones")
        notif_layout.addWidget(self.show_notifications_checkbox)

        layout.addWidget(notif_group)

        # === INTERFAZ ===
        interface_group = QGroupBox("Interfaz")
        interface_group.setObjectName("settings-groupbox")
        interface_group.setStyleSheet(f"""
            QGroupBox#settings-groupbox {{
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox#settings-groupbox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
        interface_layout = QVLayout(interface_group)
        interface_layout.setSpacing(10)

        self.show_full_path_checkbox = QCheckBox("Mostrar ruta completa del directorio en la barra de búsqueda")
        self.show_full_path_checkbox.setChecked(True)
        self.show_full_path_checkbox.setToolTip(
            "Si está activado, muestra la ruta completa del directorio (ej: /home/usuario/Fotos).\n"
            "Si está desactivado, solo muestra el nombre de la carpeta (ej: Fotos)."
        )
        interface_layout.addWidget(self.show_full_path_checkbox)

        layout.addWidget(interface_group)

        layout.addStretch()
        return widget

    def _create_directories_tab(self):
        """Pestaña de configuración de directorios y logs"""
        widget = QWidget()
        layout = QVLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # === LOGS ===
        logs_group = QGroupBox("Logs y Diagnostico")
        logs_group.setObjectName("settings-groupbox")
        logs_group.setStyleSheet(f"""
            QGroupBox#settings-groupbox {{
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox#settings-groupbox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
        logs_layout = QVLayout(logs_group)
        logs_layout.setSpacing(12)

        logs_info = QLabel(
            "Los archivos de log registran todas las operaciones para diagnostico y auditoria."
        )
        logs_info.setObjectName("small-info-label")
        logs_info.setStyleSheet(f"""
            QLabel#small-info-label {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-style: italic;
            }}
        """)
        logs_info.setWordWrap(True)
        logs_layout.addWidget(logs_info)

        # Directorio de logs
        logs_dir_layout = QHBoxLayout()
        logs_label = QLabel("Carpeta:")
        logs_label.setMinimumWidth(100)
        logs_dir_layout.addWidget(logs_label)

        self.logs_edit = QLineEdit()
        self.logs_edit.setText(str(settings_manager.get_logs_directory() or Config.DEFAULT_LOG_DIR))
        self.logs_edit.setReadOnly(True)
        self.logs_edit.setObjectName("directory-edit")
        self.logs_edit.setStyleSheet(f"""
            QLineEdit#directory-edit {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 6px 12px;
                background-color: {DesignSystem.COLOR_BG_1};
                color: {DesignSystem.COLOR_TEXT};
                font-family: {DesignSystem.FONT_FAMILY_MONO};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
            QLineEdit#directory-edit:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        logs_dir_layout.addWidget(self.logs_edit)

        browse_logs_btn = QPushButton("Cambiar...")
        browse_logs_btn.setMaximumWidth(80)
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
            "DEBUG - Maximo detalle (para desarrollo)",
            "INFO - Normal (recomendado)",
            "WARNING - Solo advertencias",
            "ERROR - Solo errores criticos"
        ])
        self.log_level_combo.setObjectName("log-level-combo")
        self.log_level_combo.setStyleSheet(f"""
            QComboBox#log-level-combo {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 6px 12px;
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
            QComboBox#log-level-combo::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox#log-level-combo::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {DesignSystem.COLOR_TEXT};
                margin-right: 8px;
            }}
            QComboBox#log-level-combo:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        self.log_level_combo.setToolTip(
            "DEBUG: Toda la informacion tecnica\n"
            "INFO: Operaciones normales\n"
            "WARNING: Situaciones inusuales\n"
            "ERROR: Solo errores graves"
        )
        # Conectar cambio en caliente
        self.log_level_combo.currentTextChanged.connect(self.change_log_level)
        log_level_layout.addWidget(self.log_level_combo)
        log_level_layout.addStretch()

        logs_layout.addLayout(log_level_layout)

        # Botón abrir carpeta de logs
        open_logs_btn = QPushButton("Abrir carpeta de logs")
        open_logs_btn.setObjectName("open-folder-button")
        open_logs_btn.setStyleSheet(f"""
            QPushButton#open-folder-button {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 8px 16px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
            QPushButton#open-folder-button:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
        """)
        open_logs_btn.clicked.connect(self.open_logs_folder)
        logs_layout.addWidget(open_logs_btn)

        layout.addWidget(logs_group)

        # === BACKUPS ===
        backup_group = QGroupBox("Directorio de Backups")
        backup_group.setObjectName("settings-groupbox")
        backup_group.setStyleSheet(f"""
            QGroupBox#settings-groupbox {{
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox#settings-groupbox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
        backup_layout = QVLayout(backup_group)

        backup_info = QLabel("Ubicacion donde se guardan las copias de seguridad automaticas.")
        backup_info.setObjectName("small-info-label")
        backup_info.setStyleSheet(f"""
            QLabel#small-info-label {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-style: italic;
            }}
        """)
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)

        backup_row = QHBoxLayout()
        backup_label = QLabel("Carpeta:")
        backup_label.setMinimumWidth(100)
        backup_row.addWidget(backup_label)

        self.backup_edit = QLineEdit()
        self.backup_edit.setText(str(Config.DEFAULT_BACKUP_DIR))
        self.backup_edit.setReadOnly(True)
        self.backup_edit.setObjectName("directory-edit")
        self.backup_edit.setStyleSheet(f"""
            QLineEdit#directory-edit {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 6px 12px;
                background-color: {DesignSystem.COLOR_BG_1};
                color: {DesignSystem.COLOR_TEXT};
                font-family: {DesignSystem.FONT_FAMILY_MONO};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
            QLineEdit#directory-edit:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        backup_row.addWidget(self.backup_edit)

        browse_backup_btn = QPushButton("Cambiar...")
        browse_backup_btn.setMaximumWidth(80)
        browse_backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_backup_btn.setToolTip("Cambiar ubicación de backups")
        browse_backup_btn.clicked.connect(self.browse_backup_directory)
        backup_row.addWidget(browse_backup_btn)

        backup_layout.addLayout(backup_row)
        layout.addWidget(backup_group)

        layout.addStretch()
        return widget

    def _create_advanced_tab(self):
        """Pestaña de configuración avanzada"""
        widget = QWidget()
        layout = QVLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # === RENDIMIENTO ===
        perf_group = QGroupBox("Rendimiento")
        perf_group.setObjectName("settings-groupbox")
        perf_group.setStyleSheet(f"""
            QGroupBox#settings-groupbox {{
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox#settings-groupbox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
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
            "Cambiar el numero de hilos requiere reiniciar la aplicacion para tener efecto completo."
        )
        perf_info.setObjectName("small-info-label")
        perf_info.setStyleSheet(f"""
            QLabel#small-info-label {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-style: italic;
            }}
        """)
        perf_info.setWordWrap(True)
        perf_layout.addWidget(perf_info)

        layout.addWidget(perf_group)

        # === MODO SIMULACIÓN ===
        dryrun_group = QGroupBox("Modo Simulacion (Dry Run)")
        dryrun_group.setObjectName("settings-groupbox")
        dryrun_group.setStyleSheet(f"""
            QGroupBox#settings-groupbox {{
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox#settings-groupbox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
        dryrun_layout = QVLayout(dryrun_group)
        dryrun_layout.setSpacing(12)

        dryrun_info = QLabel(
            "En modo simulacion, las operaciones se analizan y muestran pero <b>no se ejecutan</b> realmente. "
            "Util para verificar que hara la aplicacion antes de aplicar cambios."
        )
        dryrun_info.setObjectName("small-info-label")
        dryrun_info.setStyleSheet(f"""
            QLabel#small-info-label {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-style: italic;
            }}
        """)
        dryrun_info.setWordWrap(True)
        dryrun_layout.addWidget(dryrun_info)

        self.dry_run_default_checkbox = QCheckBox("Activar modo simulación por defecto en todas las operaciones")
        self.dry_run_default_checkbox.setChecked(False)
        self.dry_run_default_checkbox.setToolTip(
            "Si se activa, todos los diálogos de eliminación (HEIC, Live Photos, Duplicados)\n"
            "mostrarán el checkbox de 'Modo simulación' marcado por defecto.\n"
            "Esto añade una capa extra de seguridad para evitar eliminaciones accidentales."
        )
        dryrun_layout.addWidget(self.dry_run_default_checkbox)

        layout.addWidget(dryrun_group)

        # === DEPURACIÓN ===
        debug_group = QGroupBox("Depuracion")
        debug_group.setObjectName("settings-groupbox")
        debug_group.setStyleSheet(f"""
            QGroupBox#settings-groupbox {{
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: 1ex;
                padding-top: 10px;
            }}
            QGroupBox#settings-groupbox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
        debug_layout = QVLayout(debug_group)

        clear_settings_btn = QPushButton("Restablecer TODA la configuracion guardada")
        clear_settings_btn.setObjectName("danger-button")
        clear_settings_btn.setStyleSheet(f"""
            QPushButton#danger-button {{
                background-color: {DesignSystem.COLOR_ERROR};
                color: {DesignSystem.COLOR_SURFACE};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 8px 16px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton#danger-button:hover {{
                background-color: #dc2626;
            }}
        """)
        clear_settings_btn.clicked.connect(self.clear_all_settings)
        debug_layout.addWidget(clear_settings_btn)

        debug_info = QLabel("Esto eliminara todas las preferencias guardadas y volvera a los valores por defecto.")
        debug_info.setObjectName("debug-info-label")
        debug_info.setStyleSheet(f"""
            QLabel#debug-info-label {{
                color: {DesignSystem.COLOR_WARNING};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-style: italic;
                padding: 4px 0;
            }}
        """)
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
        
        has_changes = (
            logs_changed or backup_changed or level_changed or auto_backup_changed or
            confirm_ops_changed or confirm_delete_changed or show_notif_changed or
            show_path_changed or max_workers_changed or dry_run_changed
        )
        
        # Habilitar/deshabilitar botón según haya cambios
        self.save_button.setEnabled(has_changes)
        
        # Log para debugging (solo si cambia el estado)
        if has_changes != getattr(self, '_last_has_changes', None):
            self.logger.debug(f"Cambios detectados: {has_changes}")
            self._last_has_changes = has_changes

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
            "• Directorios personalizados\n"
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
                current_dry_run != new_dry_run
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
                
                # Actualizar logging_manager solo si cambió
                if self.parent_window and hasattr(self.parent_window, 'logging_manager'):
                    try:
                        self.parent_window.logging_manager.change_logs_directory(new_logs_dir)
                        self.parent_window.logs_directory = self.parent_window.logging_manager.logs_directory
                        self.parent_window.log_file = self.parent_window.logging_manager.log_file
                    except Exception as e:
                        self.logger.warning(f"No se pudo cambiar directorio de logs: {e}")
                        self.parent_window.logs_directory = new_logs_dir
            
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

            self.logger.info("Configuración guardada exitosamente")

            # Emitir señal de cambios guardados
            self.settings_saved.emit()

            # ✅ IMPORTANTE: Cerrar el diálogo ANTES de mostrar el mensaje
            # Esto evita problemas con la pila modal
            self.accept()

            # Mensaje informativo después de cerrar el diálogo
            msg_text = "La configuracion se ha guardado correctamente."
            if logs_dir_changed:
                msg_text += "\n\nEl directorio de logs ha cambiado. Los nuevos logs se escribirán en la nueva ubicación."
            elif any_setting_changed:
                msg_text += "\n\nAlgunos cambios pueden requerir reiniciar la aplicacion."
            
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
