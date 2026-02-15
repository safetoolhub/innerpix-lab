from pathlib import Path
import logging
import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QGroupBox, QVBoxLayout as QVLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFrame, 
    QMessageBox, QCheckBox, QSpinBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from config import Config
from ui.styles.design_system import DesignSystem
from utils.logger import set_global_log_level, get_logger
from utils.settings_manager import settings_manager
from utils.platform_utils import check_ffprobe, check_exiftool, get_current_os_install_hint
import logging


class SettingsDialog(QDialog):
    """Diálogo de configuración avanzada con persistencia"""

    # Señal emitida cuando se guardan cambios importantes que requieren actualización
    settings_saved = pyqtSignal()

    def __init__(self, parent=None, initial_tab=0):
        super().__init__(parent)
        self.parent_window = parent
        self.logger = logging.getLogger('InnerpixLab.SettingsDialog')
        
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
        self.resize(850, 960)  # Aumentado verticalmente para acomodar instrucciones sin scroll
        
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
        self.tabs.addTab(self._wrap_in_scroll_area(general_tab), "General")

        # === PESTAÑA 2: ANÁLISIS INICIAL ===
        analysis_tab = self._create_analysis_tab()
        self.tabs.addTab(self._wrap_in_scroll_area(analysis_tab), "Análisis inicial")

        # === PESTAÑA 3: BACKUPS ===
        backups_tab = self._create_backups_tab()
        self.tabs.addTab(self._wrap_in_scroll_area(backups_tab), "Backup y Logs")

        # === PESTAÑA 4: AVANZADO ===
        advanced_tab = self._create_advanced_tab()
        self.tabs.addTab(self._wrap_in_scroll_area(advanced_tab), "Avanzado")

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

    def _wrap_in_scroll_area(self, widget: QWidget) -> QScrollArea:
        """Envuelve un widget en un QScrollArea para evitar cortes de contenido"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(widget)
        # Hacer el fondo del scroll area transparente para que herede el del tab widget
        scroll.setStyleSheet(f"background-color: transparent;")
        return scroll

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



        self.confirm_delete_checkbox = QCheckBox("Pedir confirmación adicional para operaciones de eliminación")
        self.confirm_delete_checkbox.setChecked(True)
        self.confirm_delete_checkbox.setToolTip("Doble confirmación para operaciones que eliminan archivos")
        self.confirm_delete_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        confirm_layout.addWidget(self.confirm_delete_checkbox)

        self.confirm_reanalyze_checkbox = QCheckBox("Confirmar antes de reanalizar tras ejecutar operaciones")
        self.confirm_reanalyze_checkbox.setChecked(True)
        self.confirm_reanalyze_checkbox.setToolTip(
            "Si está activado, se pedirá confirmación antes de actualizar las estadísticas.\n"
            "Si está desactivado, se actualizarán automáticamente tras operaciones destructivas."
        )
        self.confirm_reanalyze_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        confirm_layout.addWidget(self.confirm_reanalyze_checkbox)

        layout.addWidget(confirm_group)

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

    def _create_analysis_tab(self):
        """Pestaña de configuración de análisis inicial y herramientas"""
        widget = QWidget()
        widget.setObjectName("analysis_tab")
        widget.setStyleSheet(f"#analysis_tab {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}")
        layout = QVLayout(widget)
        layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20
        )
        layout.setSpacing(DesignSystem.SPACE_16)  # Más compacto

        # === HERRAMIENTAS DEL SISTEMA ===
        tools_group = self._create_groupbox("Herramientas del Sistema")
        tools_layout = QVLayout(tools_group)
        tools_layout.setSpacing(DesignSystem.SPACE_8)  # Más compacto

        tools_info = self._create_info_label(
            "Para extraer metadatos de videos (duración, fecha de creación) se requieren herramientas externas. "
            "Sin ellas, la fase de análisis de videos se saltará automáticamente."
        )
        tools_layout.addWidget(tools_info)

        # Contenedor horizontal para estado + botón
        tools_row = QWidget()
        tools_row_layout = QHBoxLayout(tools_row)
        tools_row_layout.setContentsMargins(0, 0, 0, 0)
        tools_row_layout.setSpacing(DesignSystem.SPACE_12)  # Más compacto

        # Frame para mostrar estado de herramientas
        self.tools_status_frame = QFrame()
        # Usamos el nuevo estilo profesional de DesignSystem
        self.tools_status_frame.setStyleSheet(DesignSystem.get_status_frame_style(DesignSystem.COLOR_BORDER))
        
        tools_status_layout = QVLayout(self.tools_status_frame)
        tools_status_layout.setSpacing(DesignSystem.SPACE_4)

        self.ffprobe_status_label = QLabel("⏳ ffprobe: Verificando...")
        self.ffprobe_status_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px;")
        tools_status_layout.addWidget(self.ffprobe_status_label)

        self.exiftool_status_label = QLabel("⏳ exiftool: Verificando...")
        self.exiftool_status_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px;")
        tools_status_layout.addWidget(self.exiftool_status_label)

        tools_row_layout.addWidget(self.tools_status_frame, 1)

        # Botón para verificar herramientas
        check_tools_btn = QPushButton("Verificar")
        check_tools_btn.setFixedWidth(120)  # Aumentado para evitar corte de texto
        check_tools_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        check_tools_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        check_tools_btn.setToolTip("Verificar si las herramientas están instaladas")
        check_tools_btn.clicked.connect(self._check_system_tools)
        tools_row_layout.addWidget(check_tools_btn, 0, Qt.AlignmentFlag.AlignTop)

        tools_layout.addWidget(tools_row)

        # Info colapsable sobre instalación
        self.install_info_btn = QPushButton("📦 ¿Cómo instalar estas herramientas?")
        self.install_info_btn.setFlat(True)
        self.install_info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_info_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_PRIMARY};
                text-align: left;
                padding: {DesignSystem.SPACE_4}px 0;
                border: none;
            }}
            QPushButton:hover {{
                color: {DesignSystem.COLOR_PRIMARY_HOVER};
                text-decoration: underline;
            }}
        """)
        self.install_info_btn.clicked.connect(self._toggle_install_info)
        tools_layout.addWidget(self.install_info_btn)

        # Panel de instalación (oculto por defecto) - instrucciones según SO
        current_os_hint = get_current_os_install_hint()
        self.install_info_panel = QLabel(
            f"<b>Tu sistema:</b> {current_os_hint}<br><br>"
            "• <b>Ubuntu/Debian:</b> sudo apt install ffmpeg libimage-exiftool-perl<br>"
            "• <b>Fedora/RHEL:</b> sudo dnf install ffmpeg perl-Image-ExifTool<br>"
            "• <b>Arch/Manjaro:</b> sudo pacman -S ffmpeg perl-image-exiftool<br>"
            "• <b>macOS:</b> brew install ffmpeg exiftool<br>"
            "• <b>Windows:</b> Descargar desde ffmpeg.org y exiftool.org"
        )
        self.install_info_panel.setWordWrap(True)
        self.install_info_panel.setOpenExternalLinks(True)
        self.install_info_panel.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                background-color: {DesignSystem.COLOR_BG_4};
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_12}px;
                margin-left: {DesignSystem.SPACE_8}px;
            }}
        """)
        self.install_info_panel.hide()  # Oculto por defecto
        tools_layout.addWidget(self.install_info_panel)

        layout.addWidget(tools_group)

        # === CONFIGURACIÓN DE ANÁLISIS INICIAL ===
        analysis_group = self._create_groupbox("Configuración de Análisis Inicial")
        analysis_layout = QVLayout(analysis_group)
        analysis_layout.setSpacing(DesignSystem.SPACE_8)  # Más compacto

        analysis_info = self._create_info_label(
            "Controla qué información se extrae durante el escaneo inicial del directorio. "
            "Desactivar opciones hace el escaneo más rápido, pero el análisis de cada herramienta tomará más tiempo al abrirla."
        )
        analysis_layout.addWidget(analysis_info)

        # Checkbox para pre-cálculo de hashes
        self.precalculate_hashes_checkbox = QCheckBox("Pre-calcular hashes SHA256 de todos los archivos")
        self.precalculate_hashes_checkbox.setChecked(False)
        self.precalculate_hashes_checkbox.setToolTip(
            "Pre-calcula hashes SHA256 de todos los archivos durante el escaneo inicial.\n"
            "\n"
            "VENTAJAS:\n"
            "  • Herramienta 'Duplicados exactos' es INSTANTÁNEA (ya tiene todos los hashes)\n"
            "  • Ideal si siempre buscas duplicados\n"
            "\n"
            "DESVENTAJAS:\n"
            "  • Hace el escaneo inicial MUY lento (calcula hash de cada archivo)\n"
            "  • Para 10,000 archivos: escaneo pasa de ~10s a ~2-5 min\n"
            "\n"
            "RECOMENDACIÓN: Dejar DESACTIVADO (el análisis bajo demanda es eficiente)."
        )
        self.precalculate_hashes_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        analysis_layout.addWidget(self.precalculate_hashes_checkbox)

        # Checkbox para EXIF de imágenes
        self.precalculate_image_exif_checkbox = QCheckBox("Extraer metadatos EXIF de imágenes")
        self.precalculate_image_exif_checkbox.setChecked(True)
        self.precalculate_image_exif_checkbox.setToolTip(
            "Extrae metadatos EXIF de todas las imágenes durante el escaneo inicial.\n"
            "\n"
            "VENTAJAS:\n"
            "  • Herramientas de organización y renombrado son más rápidas\n"
            "  • Costo moderado en el escaneo inicial (~30-60 seg para 30k fotos)\n"
            "\n"
            "DESVENTAJAS:\n"
            "  • Añade tiempo al escaneo inicial\n"
            "\n"
            "RECOMENDACIÓN: Dejar ACTIVADO (el costo es razonable y útil para la mayoría)."
        )
        self.precalculate_image_exif_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        analysis_layout.addWidget(self.precalculate_image_exif_checkbox)

        # Checkbox para EXIF de videos
        self.precalculate_video_exif_checkbox = QCheckBox("Extraer metadatos EXIF de videos (MUY LENTO)")
        self.precalculate_video_exif_checkbox.setChecked(False)
        self.precalculate_video_exif_checkbox.setToolTip(
            "Extrae metadatos de videos usando ffprobe durante el escaneo inicial.\n"
            "\n"
            "⚠️ ADVERTENCIA: Este proceso es EXTREMADAMENTE LENTO\n"
            "  • Para 5,000 videos: ~3-10 minutos adicionales\n"
            "  • Bloquea el escaneo inicial\n"
            "\n"
            "VENTAJAS:\n"
            "  • Herramienta de organización de videos tiene datos listos\n"
            "\n"
            "DESVENTAJAS:\n"
            "  • Hace el escaneo inicial MUCHO más lento\n"
            "  • La mayoría de usuarios no organizan videos por fecha\n"
            "\n"
            "RECOMENDACIÓN: Dejar DESACTIVADO (análisis bajo demanda es mucho más eficiente)."
        )
        self.precalculate_video_exif_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        analysis_layout.addWidget(self.precalculate_video_exif_checkbox)

        layout.addWidget(analysis_group)

        # Verificar herramientas al cargar
        self._check_system_tools()

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

        # Checkbox para dual logging (WARNING/ERROR adicional)
        self.dual_log_checkbox = QCheckBox(
            "Crear archivo adicional solo con WARNING y ERROR (para datasets grandes)"
        )
        self.dual_log_checkbox.setChecked(True)  # Por defecto activado
        self.dual_log_checkbox.setToolTip(
            "Cuando está activado y el nivel de log es INFO o DEBUG:\n"
            "• Se creará un archivo principal con TODOS los logs (sufijo: _INFO o _DEBUG)\n"
            "• Se creará un archivo adicional solo con WARNING y ERROR (sufijo: _WARNERROR)\n\n"
            "Útil para datasets grandes donde el log completo es muy extenso.\n"
            "Esta opción se deshabilita automáticamente si el nivel es WARNING o ERROR."
        )
        self.dual_log_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        logs_layout.addWidget(self.dual_log_checkbox)

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
        
        # Info de configuración automática
        auto_info = QLabel(
            f"🤖 Configuración automática basada en tu hardware:\n"
            f"   • CPU Cores: {Config.get_cpu_count()}\n"
            f"   • Workers I/O (recomendado): {Config.get_optimal_worker_threads()}\n"
            f"   • Workers CPU (recomendado): {Config.get_cpu_bound_workers()}"
        )
        auto_info.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_12}px;
            }}
        """)
        perf_layout.addWidget(auto_info)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        perf_layout.addWidget(separator)
        
        # Override manual (opcional)
        override_label = QLabel(
            "⚠️ Override manual (deja en 0 para usar automático):"
        )
        override_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_WARNING};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
        """)
        perf_layout.addWidget(override_label)

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

        from ui.screens.custom_spinbox import CustomSpinBox
        self.max_workers_spin = CustomSpinBox()
        self.max_workers_spin.setMinimum(0)  # 0 = automático
        self.max_workers_spin.setMaximum(Config.MAX_WORKER_THREADS)
        self.max_workers_spin.setValue(0)  # Por defecto: automático
        self.max_workers_spin.setSpecialValueText("Automático")
        self.max_workers_spin.setToolTip(
            f"Número de hilos paralelos para procesar archivos.\n"
            f"\n"
            f"• 0 (Automático): Detecta y usa el óptimo para tu hardware\n"
            f"• I/O workers: {Config.get_optimal_worker_threads()} (lectura/hashing)\n"
            f"• CPU workers: {Config.get_cpu_bound_workers()} (análisis de imágenes)\n"
            f"\n"
            f"Solo cambia esto si experimentas problemas de rendimiento.\n"
            f"Rango válido: 1-{Config.MAX_WORKER_THREADS}"
        )
        workers_layout.addWidget(self.max_workers_spin)
        workers_layout.addStretch()

        perf_layout.addLayout(workers_layout)

        # Intervalo de actualización de UI
        ui_update_layout = QHBoxLayout()
        ui_update_layout.setSpacing(DesignSystem.SPACE_12)
        
        ui_update_label = QLabel("Frecuencia de actualización en análisis:")
        ui_update_label.setMinimumWidth(180)
        ui_update_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
        """)
        ui_update_layout.addWidget(ui_update_label)

        self.ui_update_spin = CustomSpinBox()
        self.ui_update_spin.setMinimum(1)
        self.ui_update_spin.setMaximum(1000)
        self.ui_update_spin.setValue(Config.UI_UPDATE_INTERVAL)
        self.ui_update_spin.setToolTip(
            "Cada cuántos archivos se da feeback al usuario en los análisis.\n"
            "Valores más altos mejoran el rendimiento pero se recibe menos feedback.\n"
            "Valores más bajos (1) hacen pueden ralentizar el proceso.\n"
            "Recomendado: 10-50"
        )
        ui_update_layout.addWidget(self.ui_update_spin)
        ui_update_layout.addStretch()

        perf_layout.addLayout(ui_update_layout)

        perf_info = self._create_info_label(
            "Cambiar el número de hilos requiere reiniciar la aplicación para tener efecto completo."
        )
        perf_layout.addWidget(perf_info)

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

    def _load_current_settings(self):
        """Carga la configuración actual desde el gestor de settings"""
        try:
            # General tab
            self.auto_backup_checkbox.setChecked(settings_manager.get_auto_backup_enabled())

            self.confirm_delete_checkbox.setChecked(settings_manager.get_confirm_delete())
            self.confirm_reanalyze_checkbox.setChecked(settings_manager.get_confirm_reanalyze())
            self.show_full_path_checkbox.setChecked(settings_manager.get_show_full_path())

            # Configuración de análisis inicial (General tab)
            self.precalculate_hashes_checkbox.setChecked(settings_manager.get_precalculate_hashes())
            self.precalculate_image_exif_checkbox.setChecked(settings_manager.get_precalculate_image_exif())
            self.precalculate_video_exif_checkbox.setChecked(settings_manager.get_precalculate_video_exif())

            # Advanced tab
            # Workers: 0 significa automático, cualquier otro valor es override manual
            saved_workers = settings_manager.get_max_workers(0)
            self.max_workers_spin.setValue(saved_workers)
            
            self.ui_update_spin.setValue(settings_manager.get_int("ui_update_interval", Config.UI_UPDATE_INTERVAL))
            self.dry_run_default_checkbox.setChecked(settings_manager.get_bool(settings_manager.KEY_DRY_RUN_DEFAULT, False))

            # Directories tab - Log level
            current_level = settings_manager.get_log_level("INFO")
            level_index_map = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
            self.log_level_combo.setCurrentIndex(level_index_map.get(current_level, 1))
            
            # Dual log checkbox
            self.dual_log_checkbox.setChecked(settings_manager.get_dual_log_enabled())
            # Deshabilitar si el nivel es WARNING o ERROR
            self._update_dual_log_enabled_state(current_level)

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
            'dual_log': self.dual_log_checkbox.isChecked(),
            'auto_backup': self.auto_backup_checkbox.isChecked(),

            'confirm_delete': self.confirm_delete_checkbox.isChecked(),
            'confirm_reanalyze': self.confirm_reanalyze_checkbox.isChecked(),
            'show_path': self.show_full_path_checkbox.isChecked(),
            'max_workers': self.max_workers_spin.value(),
            'dry_run': self.dry_run_default_checkbox.isChecked(),
            'ui_update_interval': self.ui_update_spin.value(),
            'precalculate_hashes': self.precalculate_hashes_checkbox.isChecked(),
            'precalculate_image_exif': self.precalculate_image_exif_checkbox.isChecked(),
            'precalculate_video_exif': self.precalculate_video_exif_checkbox.isChecked(),
        }
        self.logger.debug(f"Valores originales guardados: {self.original_values}")
    
    def _connect_change_signals(self):
        """Conecta señales de cambio de todos los widgets para detectar modificaciones"""
        # Checkboxes
        self.auto_backup_checkbox.stateChanged.connect(lambda: self._on_widget_changed("auto_backup"))

        self.confirm_delete_checkbox.stateChanged.connect(lambda: self._on_widget_changed("confirm_delete"))
        self.confirm_reanalyze_checkbox.stateChanged.connect(lambda: self._on_widget_changed("confirm_reanalyze"))
        self.show_full_path_checkbox.stateChanged.connect(lambda: self._on_widget_changed("show_path"))
        self.dry_run_default_checkbox.stateChanged.connect(lambda: self._on_widget_changed("dry_run"))
        self.precalculate_hashes_checkbox.stateChanged.connect(lambda: self._on_widget_changed("precalculate_hashes"))
        self.precalculate_image_exif_checkbox.stateChanged.connect(lambda: self._on_widget_changed("precalculate_image_exif"))
        self.precalculate_video_exif_checkbox.stateChanged.connect(lambda: self._on_widget_changed("precalculate_video_exif"))
        self.dual_log_checkbox.stateChanged.connect(lambda: self._on_widget_changed("dual_log"))
        
        # Spinbox
        self.max_workers_spin.valueChanged.connect(lambda: self._on_widget_changed("max_workers"))
        self.ui_update_spin.valueChanged.connect(lambda: self._on_widget_changed("ui_update_interval"))
        
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
        

        
        current_confirm_delete = self.confirm_delete_checkbox.isChecked()
        original_confirm_delete = self.original_values['confirm_delete']
        confirm_delete_changed = current_confirm_delete != original_confirm_delete
        
        current_confirm_reanalyze = self.confirm_reanalyze_checkbox.isChecked()
        original_confirm_reanalyze = self.original_values['confirm_reanalyze']
        confirm_reanalyze_changed = current_confirm_reanalyze != original_confirm_reanalyze
        
        current_show_path = self.show_full_path_checkbox.isChecked()
        original_show_path = self.original_values['show_path']
        show_path_changed = current_show_path != original_show_path
        
        current_max_workers = self.max_workers_spin.value()
        original_max_workers = self.original_values['max_workers']
        current_max_workers = self.max_workers_spin.value()
        original_max_workers = self.original_values['max_workers']
        max_workers_changed = current_max_workers != original_max_workers

        current_ui_update = self.ui_update_spin.value()
        original_ui_update = self.original_values['ui_update_interval']
        ui_update_changed = current_ui_update != original_ui_update
        
        current_dry_run = self.dry_run_default_checkbox.isChecked()
        original_dry_run = self.original_values['dry_run']
        dry_run_changed = current_dry_run != original_dry_run
        
        current_precalculate_hashes = self.precalculate_hashes_checkbox.isChecked()
        original_precalculate_hashes = self.original_values['precalculate_hashes']
        precalculate_hashes_changed = current_precalculate_hashes != original_precalculate_hashes
        
        current_precalculate_image_exif = self.precalculate_image_exif_checkbox.isChecked()
        original_precalculate_image_exif = self.original_values['precalculate_image_exif']
        precalculate_image_exif_changed = current_precalculate_image_exif != original_precalculate_image_exif
        
        current_precalculate_video_exif = self.precalculate_video_exif_checkbox.isChecked()
        original_precalculate_video_exif = self.original_values['precalculate_video_exif']
        precalculate_video_exif_changed = current_precalculate_video_exif != original_precalculate_video_exif
        
        current_dual_log = self.dual_log_checkbox.isChecked()
        original_dual_log = self.original_values['dual_log']
        dual_log_changed = current_dual_log != original_dual_log
        
        has_changes = (
            logs_changed or backup_changed or level_changed or auto_backup_changed or
            confirm_delete_changed or confirm_reanalyze_changed or
            show_path_changed or max_workers_changed or dry_run_changed or
            ui_update_changed or precalculate_hashes_changed or
            precalculate_image_exif_changed or precalculate_video_exif_changed or
            dual_log_changed
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
        - Pestaña Avanzado: max_workers
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
            
            # Actualizar el estado del checkbox de dual log
            self._update_dual_log_enabled_state(level_name)
            
            # Actualizar también el log_level de la ventana padre si existe
            if self.parent_window and hasattr(self.parent_window, 'log_level'):
                self.parent_window.log_level = level_name
            
            self.logger.info(f"Nivel de log cambiado a: {level_name}")

        except Exception as e:
            self.logger.exception(f"Error cambiando nivel de log: {e}")

    def _update_dual_log_enabled_state(self, level_name: str):
        """
        Actualiza el estado habilitado/deshabilitado del checkbox de dual logging
        basándose en el nivel de log seleccionado.
        
        Args:
            level_name: Nombre del nivel de log (DEBUG, INFO, WARNING, ERROR)
        """
        # Deshabilitar si el nivel es WARNING o ERROR (no tiene sentido logs duplicados)
        should_enable = level_name in ('DEBUG', 'INFO')
        self.dual_log_checkbox.setEnabled(should_enable)
        
        # Si se deshabilita, mostrar tooltip explicativo
        if not should_enable:
            self.dual_log_checkbox.setToolTip(
                "Esta opción solo está disponible para niveles INFO o DEBUG.\n"
                "Con nivel WARNING o ERROR, todos los logs ya contienen solo advertencias y errores."
            )
        else:
            # Restaurar tooltip original
            self.dual_log_checkbox.setToolTip(
                "Cuando está activado y el nivel de log es INFO o DEBUG:\n"
                "• Se creará un archivo principal con TODOS los logs (sufijo: _INFO o _DEBUG)\n"
                "• Se creará un archivo adicional solo con WARNING y ERROR (sufijo: _WARNERROR)\n\n"
                "Útil para datasets grandes donde el log completo es muy extenso.\n"
                "Esta opción se deshabilita automáticamente si el nivel es WARNING o ERROR."
            )

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
            self.confirm_delete_checkbox.setChecked(True)
            self.confirm_reanalyze_checkbox.setChecked(True)
            self.show_full_path_checkbox.setChecked(True)
            self.dry_run_default_checkbox.setChecked(False)
            self.max_workers_spin.setValue(Config.MAX_WORKER_THREADS)
            
            # Restaurar opciones de análisis inicial
            self.precalculate_hashes_checkbox.setChecked(False)
            self.precalculate_image_exif_checkbox.setChecked(True)
            self.precalculate_video_exif_checkbox.setChecked(False)
            
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
            current_confirm_reanalyze = settings_manager.get_confirm_reanalyze()
            current_show_path = settings_manager.get_show_full_path()
            current_max_workers = settings_manager.get_max_workers(Config.MAX_WORKER_THREADS)
            current_dry_run = settings_manager.get_bool(settings_manager.KEY_DRY_RUN_DEFAULT, False)
            current_ui_update = settings_manager.get_int("ui_update_interval", Config.UI_UPDATE_INTERVAL)
            current_precalculate_hashes = settings_manager.get_precalculate_hashes()
            current_precalculate_image_exif = settings_manager.get_precalculate_image_exif()
            current_precalculate_video_exif = settings_manager.get_precalculate_video_exif()
            current_dual_log = settings_manager.get_dual_log_enabled()
            
            # Valores nuevos (desde UI)
            new_logs_dir = Path(self.logs_edit.text())
            new_backup_dir = Path(self.backup_edit.text())
            new_log_level = self.log_level_combo.currentText().split()[0].split(" - ")[0].upper()
            new_auto_backup = self.auto_backup_checkbox.isChecked()
            new_confirm_delete = self.confirm_delete_checkbox.isChecked()
            new_confirm_reanalyze = self.confirm_reanalyze_checkbox.isChecked()
            new_show_path = self.show_full_path_checkbox.isChecked()
            new_max_workers = self.max_workers_spin.value()
            new_ui_update = self.ui_update_spin.value()
            new_dry_run = self.dry_run_default_checkbox.isChecked()
            new_precalculate_hashes = self.precalculate_hashes_checkbox.isChecked()
            new_precalculate_image_exif = self.precalculate_image_exif_checkbox.isChecked()
            new_precalculate_video_exif = self.precalculate_video_exif_checkbox.isChecked()
            new_dual_log = self.dual_log_checkbox.isChecked()
            
            # Detectar qué cambió
            logs_dir_changed = (current_logs_dir != new_logs_dir)
            backup_dir_changed = (current_backup_dir != new_backup_dir)
            log_level_changed = (current_log_level != new_log_level)
            any_setting_changed = (
                logs_dir_changed or backup_dir_changed or log_level_changed or
                current_auto_backup != new_auto_backup or
                current_confirm_delete != new_confirm_delete or
                current_confirm_reanalyze != new_confirm_reanalyze or
                current_show_path != new_show_path or
                current_max_workers != new_max_workers or
                current_ui_update != new_ui_update or
                current_dry_run != new_dry_run or
                current_precalculate_hashes != new_precalculate_hashes or
                current_precalculate_image_exif != new_precalculate_image_exif or
                current_precalculate_video_exif != new_precalculate_video_exif or
                current_dual_log != new_dual_log
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
                    new_log_file, new_logs_dir_resolved = change_logs_directory(
                        new_logs_dir, 
                        dual_log_enabled=new_dual_log
                    )
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
            if current_confirm_delete != new_confirm_delete:
                settings_manager.set(settings_manager.KEY_CONFIRM_DELETE, new_confirm_delete)
            if current_confirm_reanalyze != new_confirm_reanalyze:
                settings_manager.set(settings_manager.KEY_CONFIRM_REANALYZE, new_confirm_reanalyze)
            if current_show_path != new_show_path:
                settings_manager.set_show_full_path(new_show_path)

            # Avanzado (solo si cambiaron)
            if current_max_workers != new_max_workers:
                settings_manager.set(settings_manager.KEY_MAX_WORKERS, new_max_workers)
            if current_ui_update != new_ui_update:
                settings_manager.set("ui_update_interval", new_ui_update)
                # Actualizar Config en tiempo real
                Config.UI_UPDATE_INTERVAL = new_ui_update
            if current_dry_run != new_dry_run:
                settings_manager.set(settings_manager.KEY_DRY_RUN_DEFAULT, new_dry_run)
            if current_precalculate_hashes != new_precalculate_hashes:
                settings_manager.set_precalculate_hashes(new_precalculate_hashes)
            if current_precalculate_image_exif != new_precalculate_image_exif:
                settings_manager.set_precalculate_image_exif(new_precalculate_image_exif)
            if current_precalculate_video_exif != new_precalculate_video_exif:
                settings_manager.set_precalculate_video_exif(new_precalculate_video_exif)
                # Actualizar Config.USE_VIDEO_METADATA para que tenga efecto inmediato
                Config.USE_VIDEO_METADATA = new_precalculate_video_exif
            
            # Dual log (solo si cambió)
            if current_dual_log != new_dual_log:
                settings_manager.set_dual_log_enabled(new_dual_log)
                # Actualizar el sistema de logging
                from utils.logger import set_dual_log_enabled
                set_dual_log_enabled(new_dual_log)

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

    def _toggle_install_info(self):
        """Muestra u oculta el panel de instrucciones de instalación."""
        if self.install_info_panel.isVisible():
            self.install_info_panel.hide()
            self.install_info_btn.setText("📦 ¿Cómo instalar estas herramientas?")
        else:
            self.install_info_panel.show()
            self.install_info_btn.setText("📦 Ocultar instrucciones de instalación")

    def _check_system_tools(self):
        """
        Verifica si las herramientas del sistema necesarias están instaladas.
        
        Usa las funciones unificadas de utils/platform_utils.py para verificación
        multiplataforma (Windows, Linux, macOS).
        """
        self.logger.debug("Iniciando verificación de herramientas del sistema (ffprobe, exiftool)...")
        
        # Verificar ffprobe usando función unificada
        ffprobe_status = check_ffprobe()
        self.logger.debug(f"Resultado ffprobe: disponible={ffprobe_status.available}, versión={ffprobe_status.version}")
        
        if ffprobe_status.available:
            display_text = f"✅ ffprobe: {ffprobe_status.version[:40]}" if ffprobe_status.version else "✅ ffprobe: Instalado"
            self.ffprobe_status_label.setText(display_text)
            self.ffprobe_status_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_SUCCESS};
            """)
        else:
            self.ffprobe_status_label.setText("❌ ffprobe: No instalado")
            self.ffprobe_status_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_ERROR};
            """)
        
        # Verificar exiftool usando función unificada
        exiftool_status = check_exiftool()
        self.logger.debug(f"Resultado exiftool: disponible={exiftool_status.available}, versión={exiftool_status.version}")
        
        if exiftool_status.available:
            display_text = f"✅ exiftool: v{exiftool_status.version}" if exiftool_status.version else "✅ exiftool: Instalado"
            self.exiftool_status_label.setText(display_text)
            self.exiftool_status_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_SUCCESS};
            """)
        else:
            self.exiftool_status_label.setText("❌ exiftool: No instalado")
            self.exiftool_status_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_ERROR};
            """)
        
        # Actualizar estilo del frame según disponibilidad
        has_ffprobe = ffprobe_status.available
        has_exiftool = exiftool_status.available
        
        if has_ffprobe and has_exiftool:
            self.tools_status_frame.setStyleSheet(DesignSystem.get_status_frame_style(DesignSystem.COLOR_SUCCESS))
        elif has_ffprobe or has_exiftool:
            self.tools_status_frame.setStyleSheet(DesignSystem.get_status_frame_style(DesignSystem.COLOR_WARNING))
        else:
            self.tools_status_frame.setStyleSheet(DesignSystem.get_status_frame_style(DesignSystem.COLOR_ERROR))

