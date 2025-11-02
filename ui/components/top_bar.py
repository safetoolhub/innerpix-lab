"""
TopBar - Barra superior expandible que combina control, resumen y progreso.
Componente profesional con expansión vertical animada para mostrar resumen tras análisis.

Diseño:
- Sección fija (52px): Control de directorio + botones de acción
- Sección expandible (0-180px): Resumen de análisis + herramientas + progreso
- Animación suave (300ms) con progressive disclosure
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QLineEdit, 
    QFrame, QMenu, QToolButton, QComboBox, QStyle, QApplication, 
    QProgressBar, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QCursor

from config import Config
from ui import styles
from utils.settings_manager import settings_manager
from utils.format_utils import format_number


class TopBar(QWidget):
    """Barra superior expandible con resumen integrado.
    
    Componente profesional que combina control (fijo) + resumen (expandible).
    
    Estados:
    - EMPTY: Sin directorio seleccionado (compacto)
    - READY: Directorio seleccionado, no analizado (compacto)
    - ANALYZING: Análisis en curso (expandido con progreso)
    - ANALYZED: Análisis completado (expandido con resumen)
    """
    
    # Señales
    select_directory_requested = pyqtSignal()
    analyze_requested = pyqtSignal()
    reanalyze_requested = pyqtSignal()
    stop_analysis_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()
    directory_changed = pyqtSignal(Path)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.current_directory = None
        self.current_state = 'empty'
        self._is_summary_expanded = False
        self._animation = None
        
        self._init_ui()
        self._update_button_visibility()
        
        # Estado inicial: SIEMPRE colapsado al arrancar la app.
        # (Se expandirá automáticamente cuando haya progreso o resultados.)
        settings_manager.set('summary_expanded', False)
    
    def _init_ui(self):
        """Inicializa la interfaz de usuario con diseño expandible"""
        # Layout principal vertical - SIN spacing extra
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Asegurar que el widget no se expanda verticalmente
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # ===== SECCIÓN FIJA: Control de directorio y acciones =====
        self.control_bar = QFrame(self)
        try:
            tooltip_dark = styles.STYLE_TOOLTIP_DARK
        except Exception:
            tooltip_dark = ""
        # No aplicar STYLE_SEARCH_CONTAINER (causaba bordes duplicados con field_widget)
        self.control_bar.setStyleSheet(
            "QFrame { background-color: white; border: none; padding: 0px; }" + tooltip_dark
        )
        self.control_bar.setFixedHeight(90)  # Altura extra para bordes redondeados en cualquier DPI
        
        layout = QHBoxLayout(self.control_bar)
        layout.setSpacing(16)
        layout.setContentsMargins(18, 22, 18, 22)  # Márgenes extra para asegurar visibilidad del borde
        
        # === TÍTULO DE LA APP ===
        title_label = QLabel(f"🎬 {Config.APP_NAME}")
        title_label.setStyleSheet(
            "font-size: 16px;"
            "font-weight: 700;"
            "color: #1a1a1a;"
            "background: transparent;"
            "border: none;"
            "padding: 0px;"
            "min-width: 140px;"
        )
        layout.addWidget(title_label)
        
        # Espaciador más generoso en lugar de separador visual
        layout.addSpacing(20)
        
        # === CAMPO DE DIRECTORIO UNIFICADO (Estilo Profesional) ===
        directory_container = QFrame()
        directory_container.setStyleSheet("background: transparent; border: none;")
        directory_container.setMinimumWidth(350)
        directory_container.setMaximumWidth(600)
        
        # Layout para el campo unificado con icono interno
        dir_outer_layout = QHBoxLayout(directory_container)
        # Sin margen para alinear con el TabView de la derecha
        dir_outer_layout.setContentsMargins(0, 0, 0, 0)
        dir_outer_layout.setSpacing(0)
        
        # Widget contenedor para el campo con icono y chevron integrados
        field_widget = QWidget()
        field_widget.setStyleSheet(
            "QWidget {"
            "  background: white;"
            "  border: 1px solid #cbd5e0;"
            "  border-radius: 8px;"
            "}"
            "QWidget:hover {"
            "  border-color: #94a3b8;"
            "}"
        )
        field_widget.setFixedHeight(44)  # Altura incrementada para evitar recorte del borde inferior
        field_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        field_widget.setToolTip(
            "Arrastra una carpeta aquí\n"
            "o usa el botón 'Seleccionar' para elegir el directorio de trabajo"
        )
        
        # Hacer que el campo completo sea clickeable.
        # Comportamiento consistente:
        # - Si hay un directorio seleccionado: abrirlo en el explorador
        # - Si no hay directorio (estado empty): abrir diálogo de selección
        def on_field_clicked(event):
            # Evitar interacción durante un análisis en curso. Aunque el botón
            # 'Cambiar' se deshabilita visualmente, añadimos una salvaguarda
            # aquí para cubrir cualquier otra vía de interacción con el campo.
            if getattr(self, 'current_state', None) == 'analyzing':
                # Informar al usuario que debe detener el análisis primero
                try:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self,
                        "Análisis en curso",
                        "Hay un análisis en curso. Pulsa 'Detener' para interrumpirlo antes de cambiar de directorio."
                    )
                except Exception:
                    # Si por alguna razón no se puede mostrar el diálogo,
                    # simplemente ignoramos el clic silenciosamente.
                    pass
                return

            # Si no hay directorio seleccionado (estado 'empty') no reaccionamos
            # al clic: el usuario debe arrastrar una carpeta o usar el botón
            # 'Seleccionar'. Esto evita que la zona izquierda actúe como atajo.
            if getattr(self, 'current_state', None) == 'empty':
                return

            # Sólo abrir el directorio en el explorador si el icono de carpeta
            # está visible (directorio analizado/activo). En caso contrario
            # emitimos la señal de selección para cambiar el directorio.
            try:
                icon_visible = hasattr(self, 'folder_icon') and self.folder_icon.isVisible()
            except Exception:
                icon_visible = False

            if icon_visible and self.current_directory is not None:
                self.open_folder_requested.emit()
            else:
                self.select_directory_requested.emit()

        field_widget.mousePressEvent = on_field_clicked
        
        # Habilitar Drag & Drop
        field_widget.setAcceptDrops(True)
        
        def on_drag_enter(event):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
        
        def on_drop(event):
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                from pathlib import Path
                path = Path(urls[0].toLocalFile())
                if path.is_dir():
                    self.directory_changed.emit(path)
                    event.acceptProposedAction()
        
        field_widget.dragEnterEvent = on_drag_enter
        field_widget.dropEvent = on_drop

        # Guardar referencia para permitir ajustes dinámicos (cursor/tooltip)
        self.field_widget = field_widget
        
        field_layout = QHBoxLayout(field_widget)
        field_layout.setContentsMargins(12, 8, 8, 8)  # Márgenes verticales para que no choque con el borde
        field_layout.setSpacing(8)
        
        # Icono de carpeta (izquierda) - usar icono estándar para evitar problemas
        # Inicialmente OCULTO - se muestra solo tras análisis completado
        self.folder_icon = QLabel()
        dir_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.folder_icon.setPixmap(dir_icon.pixmap(18, 18))
        self.folder_icon.setStyleSheet(
            "opacity: 0.9;"
            "background: transparent;"
            "border: none;"
        )
        # Tooltip inicial: indica al usuario que debe seleccionar un directorio
        self.folder_icon.setToolTip("Clica aquí para seleccionar directorio (o usa el botón 'Seleccionar')")
        self.folder_icon.setVisible(False)  # Oculto inicialmente
        field_layout.addWidget(self.folder_icon)
        
        # Campo de texto del directorio (sin bordes, integrado)
        self.directory_edit = QLineEdit()
        self.directory_edit.setPlaceholderText("Ningún directorio seleccionado")
        self.directory_edit.setReadOnly(True)
        self.directory_edit.setFrame(False)
        # El texto del directorio es solo informativo: usar cursor por defecto
        self.directory_edit.setCursor(Qt.CursorShape.ArrowCursor)
        self.directory_edit.setStyleSheet(
            "QLineEdit {"
            "  background: transparent;"
            "  border: none;"
            "  color: #334155;"
            "  font-size: 13px;"
            "  padding: 0px;"
            "}"
            "QLineEdit:focus {"
            "  outline: none;"
            "}"
        )
        
        # El click se maneja a nivel de `field_widget` para mantener
        # comportamiento consistente; no sobrescribimos mousePressEvent
        field_layout.addWidget(self.directory_edit, stretch=1)
        
        # Botón de historial (chevron integrado)
        self.history_btn = QToolButton()
        # usar icono estándar (flecha hacia abajo) en lugar de caracter unicode
        arrow_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown)
        self.history_btn.setIcon(arrow_icon)
        self.history_btn.setIconSize(QSize(12, 12))
        self.history_btn.setFixedSize(26, 24)
        self.history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_btn.setToolTip("Ver historial de directorios")
        self.history_btn.setStyleSheet(
            "QToolButton {"
            "  background: transparent;"
            "  border: none;"
            "  border-radius: 4px;"
            "  color: #64748b;"
            "  font-size: 12px;"
            "  font-weight: bold;"
            "}"
            "QToolButton:hover {"
            "  background: #f1f5f9;"
            "  color: #334155;"
            "}"
            "QToolButton:pressed {"
            "  background: #e2e8f0;"
            "}"
            "QToolButton:disabled {"
            "  color: #cbd5e0;"
            "}"
            "QToolButton::menu-indicator {"
            "  image: none;"
            "  width: 0px;"
            "}"
        )
        self.history_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        # Menú de historial
        self.history_menu = QMenu(self)
        self.history_menu.setStyleSheet(styles.STYLE_MENU)
        self.history_btn.setMenu(self.history_menu)
        # Poblar menú de historial al iniciar (si hay entradas guardadas)
        self._update_history_menu()

        field_layout.addWidget(self.history_btn)
        
        dir_outer_layout.addWidget(field_widget)
        layout.addWidget(directory_container, stretch=1)
        
        # === BOTONES DE ACCIÓN ===
        # Botón: Cambiar directorio
        self.select_btn = QPushButton("📁 Cambiar")
        self.select_btn.setFixedHeight(36)
        self.select_btn.setMinimumWidth(110)
        self.select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_btn.setStyleSheet(styles.STYLE_ANALYZE_BUTTON_PRIMARY)
        self.select_btn.clicked.connect(self._on_select_clicked)
        self.select_btn.setToolTip("Seleccionar otro directorio")
        layout.addWidget(self.select_btn)
        
        # Botón: Analizar
        self.analyze_btn = QPushButton("📊 Analizar")
        self.analyze_btn.setFixedHeight(36)
        self.analyze_btn.setMinimumWidth(110)
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.setStyleSheet(styles.STYLE_ANALYZE_BUTTON_PRIMARY)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self.analyze_btn)
        
        # Botón: Re-analizar
        self.reanalyze_btn = QPushButton("🔄 Re-analizar")
        self.reanalyze_btn.setFixedHeight(36)
        self.reanalyze_btn.setMinimumWidth(120)
        self.reanalyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reanalyze_btn.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f8f9fa);"
            "  border: 1px solid #dee2e6;"
            "  border-radius: 6px;"
            "  color: #495057;"
            "  font-weight: 600;"
            "  font-size: 13px;"
            "  padding: 6px 14px;"
            "}"
            "QPushButton:hover {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef);"
            "  border-color: #adb5bd;"
            "}"
            "QPushButton:pressed {"
            "  background: #e9ecef;"
            "}"
        )
        self.reanalyze_btn.clicked.connect(self._on_reanalyze_clicked)
        layout.addWidget(self.reanalyze_btn)
        
        # Botón: Detener análisis
        self.stop_btn = QPushButton("⏸️ Detener")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setMinimumWidth(100)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff3cd, stop:1 #ffeaa7);"
            "  border: 1px solid #ffc107;"
            "  border-radius: 6px;"
            "  color: #856404;"
            "  font-weight: 600;"
            "  font-size: 13px;"
            "  padding: 6px 14px;"
            "}"
            "QPushButton:hover {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffeaa7, stop:1 #ffd93d);"
            "}"
            "QPushButton:pressed {"
            "  background: #ffd93d;"
            "}"
        )
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_btn)
        
        # Espaciador antes de los iconos (reducido para acercar los iconos)
        layout.addSpacing(8)
        
        # === ICONO DE CONFIGURACIÓN (ACCESO DIRECTO) ===
        config_btn = QPushButton("⚙️")
        config_btn.setFixedSize(40, 40)
        config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        config_btn.setToolTip("Configuración")
        config_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent;"
            "  border: none;"
            "  border-radius: 8px;"
            "  color: #64748b;"
            "  font-size: 20px;"
            "  padding: 0px;"
            "}"
            "QPushButton:hover {"
            "  background: #f1f5f9;"
            "}"
            "QPushButton:pressed {"
            "  background: #e2e8f0;"
            "}"
        )
        if self.main_window is not None:
            config_btn.clicked.connect(self.main_window.toggle_config)
        layout.addWidget(config_btn)
        
        # === ICONO DE ACERCA DE (ACCESO DIRECTO) ===
        about_btn = QPushButton("ℹ️")
        about_btn.setFixedSize(40, 40)
        about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        about_btn.setToolTip("Acerca de Pixaro Lab")
        about_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent;"
            "  border: none;"
            "  border-radius: 8px;"
            "  color: #64748b;"
            "  font-size: 20px;"
            "  padding: 0px;"
            "}"
            "QPushButton:hover {"
            "  background: #f1f5f9;"
            "}"
            "QPushButton:pressed {"
            "  background: #e2e8f0;"
            "}"
        )
        if self.main_window is not None:
            about_btn.clicked.connect(self.main_window.show_about_dialog)
        layout.addWidget(about_btn)
        
        main_layout.addWidget(self.control_bar)
        
        # ===== BARRA DE CONTROL DE RESUMEN (siempre visible) =====
        self._create_summary_control_bar()
        main_layout.addWidget(self.summary_control_bar)
        
        # ===== SECCIÓN EXPANDIBLE: Resumen + Herramientas + Progreso =====
        self._create_summary_section()
        main_layout.addWidget(self.summary_container)
    
    def _create_summary_control_bar(self):
        """Crea la barra de control del resumen (siempre visible)"""
        self.summary_control_bar = QFrame()
        self.summary_control_bar.setStyleSheet(
            "QFrame {"
            "  background: #f8f9fa;"
            "  border-top: 1px solid #e1e8ed;"
            "  border-bottom: 1px solid #e1e8ed;"
            "}"
        )
        self.summary_control_bar.setFixedHeight(60)
        self.summary_control_bar.setVisible(False)  # Oculto hasta que haya análisis
        
        control_layout = QHBoxLayout(self.summary_control_bar)
        control_layout.setContentsMargins(18, 12, 18, 12)
        control_layout.setSpacing(12)
        
        # Badge de estado del análisis
        self.analysis_status_badge = QLabel("⏸️ Listo para analizar")
        self.analysis_status_badge.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef);"
            "border: 1px solid #dee2e6;"
            "border-radius: 6px;"
            "padding: 8px 16px;"
            "color: #495057;"
            "font-size: 12px;"
            "font-weight: 600;"
        )
        self.analysis_status_badge.setAlignment(Qt.AlignmentFlag.AlignLeft)
        control_layout.addWidget(self.analysis_status_badge)
        
        control_layout.addStretch()
        
        # Botón colapsar/expandir (siempre accesible)
        self.toggle_summary_btn = QPushButton("▼ Ocultar resumen")
        self.toggle_summary_btn.setFixedHeight(32)
        self.toggle_summary_btn.setMinimumWidth(140)
        self.toggle_summary_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_summary_btn.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 #ffffff, stop:1 #f8f9fa);"
            "  border: 1px solid #cbd5e0;"
            "  border-radius: 6px;"
            "  color: #64748b;"
            "  font-weight: 600;"
            "  font-size: 12px;"
            "  padding: 4px 14px;"
            "}"
            "QPushButton:hover {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 #f8fafc, stop:1 #f1f5f9);"
            "  border-color: #94a3b8;"
            "  color: #334155;"
            "}"
            "QPushButton:pressed {"
            "  background: #e2e8f0;"
            "}"
        )
        self.toggle_summary_btn.clicked.connect(self._toggle_summary)
        self.toggle_summary_btn.setToolTip("Colapsar o expandir el panel de resumen (Ctrl+R)")
        control_layout.addWidget(self.toggle_summary_btn)
    
    def _create_summary_section(self):
        """Crea la sección expandible con resumen, herramientas y progreso"""
        # Container con altura animable
        self.summary_container = QFrame()
        self.summary_container.setStyleSheet(
            "QFrame {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 #f8f9fa, stop:1 #ffffff);"
            "  border-top: 1px solid #e1e8ed;"
            "  border-bottom: 2px solid #cbd5e0;"
            "}"
        )
        self.summary_container.setMinimumHeight(0)
        self.summary_container.setMaximumHeight(0)  # Inicialmente colapsado
        self.summary_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        container_layout = QVBoxLayout(self.summary_container)
        container_layout.setContentsMargins(18, 12, 18, 12)
        container_layout.setSpacing(12)
        
        # ===== STATS: Imágenes, Videos, Total =====
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(
            "QFrame {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 #ffffff, stop:1 #fafbfc);"
            "  border: 1px solid #e1e8ed;"
            "  border-radius: 8px;"
            "}"
        )
        self.stats_frame.setVisible(False)  # Oculto hasta que haya stats reales
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(20, 14, 20, 14)
        stats_layout.setSpacing(24)
        
        # Guardar referencias para actualización
        self.stats_labels = {}
        
        def create_stat_widget(emoji, label_key, label_text):
            stat_widget = QFrame()
            stat_widget.setStyleSheet("background: transparent; border: none;")
            stat_layout = QHBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(12)
            
            icon_label = QLabel(emoji)
            icon_label.setStyleSheet(
                "font-size: 22px; background: transparent; padding: 2px;"
            )
            icon_label.setFixedSize(32, 32)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_layout.addWidget(icon_label)
            
            text_container = QVBoxLayout()
            text_container.setSpacing(2)
            
            title_label = QLabel(label_text.upper())
            title_label.setStyleSheet(
                "color: #94a3b8; "
                "font-size: 10px; "
                "font-weight: 700; "
                "letter-spacing: 0.5px; "
                "background: transparent;"
            )
            text_container.addWidget(title_label)
            
            value_label = QLabel("—")
            value_label.setStyleSheet(
                "color: #1e293b; "
                "font-size: 20px; "
                "font-weight: 700; "
                "background: transparent; "
                "line-height: 1.2;"
            )
            self.stats_labels[label_key] = value_label
            text_container.addWidget(value_label)
            
            stat_layout.addLayout(text_container)
            return stat_widget
        
        stats_layout.addWidget(create_stat_widget("🖼️", "images", "Imágenes"))
        
        # Separador vertical con estilo mejorado
        vsep1 = QFrame()
        vsep1.setFrameShape(QFrame.Shape.VLine)
        vsep1.setStyleSheet(
            "background: qlineargradient(y1:0, y2:1, "
            "  stop:0 transparent, stop:0.2 #e1e8ed, stop:0.8 #e1e8ed, stop:1 transparent);"
            "max-width: 1px;"
        )
        vsep1.setFixedHeight(40)
        stats_layout.addWidget(vsep1)
        
        stats_layout.addWidget(create_stat_widget("🎥", "videos", "Videos"))
        
        vsep2 = QFrame()
        vsep2.setFrameShape(QFrame.Shape.VLine)
        vsep2.setStyleSheet(
            "background: qlineargradient(y1:0, y2:1, "
            "  stop:0 transparent, stop:0.2 #e1e8ed, stop:0.8 #e1e8ed, stop:1 transparent);"
            "max-width: 1px;"
        )
        vsep2.setFixedHeight(40)
        stats_layout.addWidget(vsep2)
        
        stats_layout.addWidget(create_stat_widget("📊", "total", "Total"))
        stats_layout.addStretch()
        
        container_layout.addWidget(self.stats_frame)
        
        # ===== HERRAMIENTAS: Botones de acceso rápido =====
        tools_title = QLabel("⚙️  HERRAMIENTAS DISPONIBLES")
        tools_title.setStyleSheet(
            "color: #64748b; "
            "font-size: 11px; "
            "font-weight: 700; "
            "letter-spacing: 0.5px; "
            "padding: 8px 0px 4px 0px;"
        )
        container_layout.addWidget(tools_title)
        
        tools_grid = QHBoxLayout()
        tools_grid.setSpacing(10)
        
        self.summary_action_buttons = {}
        
        def create_tool_button(key, emoji, label_text, tooltip):
            btn = QPushButton(f"{emoji}  {label_text}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(38)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setStyleSheet(
                "QPushButton {"
                "  background: white;"
                "  border: 1px solid #e1e8ed;"
                "  border-radius: 6px;"
                "  color: #334155;"
                "  font-weight: 600;"
                "  font-size: 12px;"
                "  text-align: left;"
                "  padding: 8px 14px;"
                "}"
                "QPushButton:hover {"
                "  background: #f8fafc;"
                "  border-color: #94a3b8;"
                "  color: #1e293b;"
                "}"
                "QPushButton:pressed {"
                "  background: #f1f5f9;"
                "}"
                "QPushButton:disabled {"
                "  background: #f8f9fa;"
                "  color: #cbd5e0;"
                "  border-color: #e9ecef;"
                "}"
            )
            btn.setToolTip(tooltip)
            
            def _invoke():
                tc = getattr(self.main_window, 'tab_controller', None)
                if tc is None:
                    return
                tc.open_summary_action(label_text)
            
            btn.clicked.connect(_invoke)
            self.summary_action_buttons[key] = btn
            return btn
        
        # Todas las herramientas en una sola fila
        tools_grid.addWidget(create_tool_button(
            'live_photos', '📱', 'Live Photos', 
            'Detectar y gestionar Live Photos de iOS'
        ))
        tools_grid.addWidget(create_tool_button(
            'heic', '🖼️', 'HEIC/JPG', 
            'Eliminar duplicados HEIC con equivalente JPG'
        ))
        tools_grid.addWidget(create_tool_button(
            'duplicates', '🔍', 'Duplicados', 
            'Encontrar archivos duplicados exactos y similares'
        ))
        tools_grid.addWidget(create_tool_button(
            'organization', '📁', 'Organizador', 
            'Organizar archivos por fecha o categoría'
        ))
        tools_grid.addWidget(create_tool_button(
            'renaming', '📝', 'Renombrado', 
            'Renombrar archivos con formato estándar'
        ))
        tools_grid.addStretch()

        container_layout.addLayout(tools_grid)
        
        # ===== PROGRESO =====
        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet(
            "QFrame {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 #fffef5, stop:1 #fffbf0);"
            "  border: 1px solid #ffd93d;"
            "  border-left: 3px solid #ffc107;"
            "  border-radius: 8px;"
            "}"
        )
        self.progress_frame.setVisible(False)  # Oculto por defecto
        
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(16, 12, 16, 12)
        progress_layout.setSpacing(8)
        
        # Label de estado
        self.summary_progress_label = QLabel("⏳ Preparando análisis...")
        self.summary_progress_label.setStyleSheet(
            "color: #856404; font-weight: 600; font-size: 12px; background: transparent;"
        )
        progress_layout.addWidget(self.summary_progress_label)
        
        # Barra de progreso con diseño moderno
        self.summary_progress_bar = QProgressBar()
        self.summary_progress_bar.setStyleSheet(
            "QProgressBar {"
            "  border: none;"
            "  border-radius: 6px;"
            "  text-align: center;"
            "  background-color: #fff3cd;"
            "  height: 24px;"
            "  font-size: 12px;"
            "  font-weight: 700;"
            "  color: #6d5310;"
            "}"
            "QProgressBar::chunk {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "    stop:0 #ffa000, stop:0.5 #ffc107, stop:1 #ffcd38);"
            "  border-radius: 6px;"
            "}"
        )
        self.summary_progress_bar.setMaximum(100)
        self.summary_progress_bar.setValue(0)
        self.summary_progress_bar.setTextVisible(True)
        self.summary_progress_bar.setFixedHeight(24)
        progress_layout.addWidget(self.summary_progress_bar)
        
        # Detalle adicional
        self.summary_progress_detail = QLabel("")
        self.summary_progress_detail.setStyleSheet(
            "color: #6c757d; font-size: 11px; background: transparent;"
        )
        self.summary_progress_detail.setWordWrap(True)
        progress_layout.addWidget(self.summary_progress_detail)
        
        container_layout.addWidget(self.progress_frame)
        
        # Guardar referencia al área de progreso para compatibilidad
        self.summary_progress_area = self.progress_frame
    
    def _toggle_summary(self):
        """Toggle manual del resumen (expandir/colapsar)"""
        if self._is_summary_expanded:
            self._collapse_summary()
        else:
            self._expand_summary()
    
    def _expand_summary(self, animate=True):
        """Expande la sección de resumen con animación"""
        if self._is_summary_expanded:
            return
        
        self._is_summary_expanded = True
        self.toggle_summary_btn.setText("▼ Ocultar resumen")
        
        # Mostrar barra de control
        self.summary_control_bar.setVisible(True)
        
        # Calcular altura óptima según contenido (una sola fila de herramientas)
        target_height = 280  # Altura para 1 fila de herramientas + stats + progreso
        
        if animate:
            self._animation = QPropertyAnimation(self.summary_container, b"maximumHeight")
            self._animation.setDuration(300)
            self._animation.setStartValue(0)
            self._animation.setEndValue(target_height)
            self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animation.start()
        else:
            self.summary_container.setMaximumHeight(target_height)
        
        # Guardar preferencia
        settings_manager.set('summary_expanded', True)
    
    def _collapse_summary(self, animate=True):
        """Colapsa la sección de resumen con animación"""
        if not self._is_summary_expanded:
            return
        
        self._is_summary_expanded = False
        self.toggle_summary_btn.setText("▲ Mostrar resumen")
        
        # La barra de control permanece visible para poder expandir de nuevo
        
        if animate:
            self._animation = QPropertyAnimation(self.summary_container, b"maximumHeight")
            self._animation.setDuration(300)
            self._animation.setStartValue(self.summary_container.height())
            self._animation.setEndValue(0)
            self._animation.setEasingCurve(QEasingCurve.Type.InCubic)
            self._animation.start()
        else:
            self.summary_container.setMaximumHeight(0)
        
        # Guardar preferencia
        settings_manager.set('summary_expanded', False)
    
    def _update_button_visibility(self):
        """Actualiza visibilidad de botones según el estado actual
        
        IMPORTANTE: El botón "Cambiar" está siempre visible para poder
        cambiar de directorio en cualquier momento. La funcionalidad de abrir
        carpeta ahora está en el campo de directorio (clickeable).
        """
        # Ajustar etiqueta del botón según el estado inicial
        if self.current_state == 'empty':
            self.select_btn.setText("📁 Seleccionar")
            self.select_btn.setToolTip("Seleccionar directorio")
        else:
            self.select_btn.setText("📁 Cambiar")
            self.select_btn.setToolTip("Seleccionar otro directorio")
        
        # Botón Cambiar/Seleccionar: siempre visible (permite cambiar de directorio)
        # Pero debe quedar inhabilitado durante un análisis en curso para
        # evitar cambiar de directorio mientras los hilos del análisis
        # anterior siguen corriendo. El usuario debe usar 'Detener' primero.
        self.select_btn.setVisible(True)
        
        if self.current_state == 'empty':
            self.analyze_btn.setHidden(True)
            self.reanalyze_btn.setHidden(True)
            self.stop_btn.setHidden(True)
            # Asegurar que el botón 'Seleccionar' esté habilitado en estado empty
            # (por ejemplo si antes se pulsó 'Detener' sin haber analizado nada).
            self.select_btn.setEnabled(True)
            # Campo de directorio interactivo en estado empty (permite arrastrar o usar seleccionar)
            if hasattr(self, 'field_widget'):
                self.field_widget.setEnabled(True)
            # Permitir acceso al historial incluso en estado empty si hay historial disponible
            history = settings_manager.get_directory_history()
            self.history_btn.setEnabled(len(history) > 0)
            # Cursor no debe sugerir clic cuando está vacío
            if hasattr(self, 'field_widget'):
                self.field_widget.setCursor(Qt.CursorShape.ArrowCursor)
                # Tooltip: instrucción clara cuando NO hay directorio seleccionado
                self.field_widget.setToolTip(
                    "Arrastra una carpeta aquí\n" 
                    "o usa el botón 'Seleccionar' para elegir el directorio de trabajo"
                )
            
        elif self.current_state == 'ready':
            self.analyze_btn.setVisible(True)
            self.reanalyze_btn.setHidden(True)
            self.stop_btn.setHidden(True)
            self.history_btn.setEnabled(True)
            # En estado 'ready' el botón Cambiar debe estar habilitado y el
            # botón Analizar activo para iniciar el análisis.
            self.select_btn.setEnabled(True)
            self.analyze_btn.setEnabled(True)
            # Campo clickeable cuando hay directorio seleccionado
            if hasattr(self, 'field_widget'):
                self.field_widget.setCursor(Qt.CursorShape.PointingHandCursor)
                # Tooltip: cuando hay directorio seleccionado (lista para analizar)
                # usar el botón 'Cambiar' para cambiar el directorio
                self.field_widget.setToolTip(
                    "Arrastra un directorio aquí o pulsa el botón de 'Cambiar' para cambiar el directorio de trabajo"
                )
            
        elif self.current_state == 'analyzing':
            self.analyze_btn.setHidden(True)
            self.reanalyze_btn.setHidden(True)
            self.stop_btn.setVisible(True)
            self.history_btn.setEnabled(False)
            # Desactivar el botón de cambiar para prevenir interrupciones
            self.select_btn.setEnabled(False)
            self.select_btn.setToolTip("No puedes cambiar de directorio mientras se está analizando. Pulsa 'Detener' para interrumpir el análisis.")
            if hasattr(self, 'field_widget'):
                # Mantener campo visible pero no interactivo (salvaguarda extra)
                self.field_widget.setCursor(Qt.CursorShape.ArrowCursor)
                try:
                    self.field_widget.setEnabled(False)
                except Exception:
                    pass
            
        elif self.current_state == 'analyzed':
            self.analyze_btn.setHidden(True)
            self.reanalyze_btn.setVisible(True)
            self.stop_btn.setHidden(True)
            self.history_btn.setEnabled(True)
            # Asegurar que el botón 'Cambiar' esté habilitado después del análisis
            self.select_btn.setEnabled(True)
            self.select_btn.setToolTip("Seleccionar otro directorio")
            if hasattr(self, 'field_widget'):
                # Restaurar interactividad del campo tras finalizar análisis
                try:
                    self.field_widget.setEnabled(True)
                except Exception:
                    pass
                self.field_widget.setCursor(Qt.CursorShape.PointingHandCursor)
                # Tooltip: tras análisis completado el texto debe sugerir 'Cambiar'
                self.field_widget.setToolTip(
                    "Arrastra un directorio aquí o pulsa el botón de 'Cambiar' para cambiar el directorio de trabajo"
                )
    
    def set_state(self, state: str):
        """Cambia el estado del TopBar
        
        Args:
            state: 'empty', 'ready', 'analyzing', 'analyzed'
        """
        if state not in ['empty', 'ready', 'analyzing', 'analyzed']:
            return
        
        self.current_state = state
        self._update_button_visibility()
    
    def set_directory(self, directory_path):
        """Actualiza el directorio mostrado
        
        Args:
            directory_path: Path object del directorio
        """
        from pathlib import Path
        
        path = Path(directory_path) if not isinstance(directory_path, Path) else directory_path
        self.current_directory = path
        
        # Obtener preferencia de visualización
        show_full_path = settings_manager.get_show_full_path()
        
        if show_full_path:
            display_text = str(path)
        else:
            display_text = path.name
        
        self.directory_edit.setText(display_text)
        # Mostrar la ruta completa como tooltip en el icono de carpeta y
        # ofrecer hint para abrir en el explorador. El texto del directorio
        # permanece informativo (sin tooltip de acción).
        try:
            self.folder_icon.setToolTip(f"{str(path)}\n\nClica aquí para abrir el directorio de trabajo")
        except Exception:
            # defensivo: si no existe el icono, ignorar
            pass
        
        # Actualizar historial
        self._update_history_menu()
        
        # Agregar al historial
        settings_manager.add_to_directory_history(str(path))
    
    def _update_history_menu(self):
        """Actualiza el menú de historial de directorios con formato profesional"""
        self.history_menu.clear()
        
        history = settings_manager.get_directory_history()
        
        if not history:
            no_history_action = self.history_menu.addAction("Sin historial reciente")
            no_history_action.setEnabled(False)
            return
        
        # Título del menú
        title_action = self.history_menu.addAction("🕒 DIRECTORIOS RECIENTES")
        title_action.setEnabled(False)
        font = title_action.font()
        font.setBold(True)
        font.setPointSize(9)
        title_action.setFont(font)
        
        self.history_menu.addSeparator()
        
        # Calcular tiempo relativo (si hay timestamp)
        from datetime import datetime
        
        for idx, dir_path in enumerate(history):
            path = Path(dir_path)
            
            # Texto del item: icono + nombre + ruta parcial
            folder_name = path.name
            parent_path = str(path.parent.name) if path.parent.name else ""
            
            if parent_path:
                display_text = f"📁 {folder_name}  •  .../{parent_path}"
            else:
                display_text = f"📁 {folder_name}"
            
            action = self.history_menu.addAction(display_text)
            action.setToolTip(f"📍 {str(path)}\n\nClick para seleccionar y analizar")
            
            # Conectar a lambda con default argument para capturar el valor
            action.triggered.connect(lambda checked=False, p=path: self._on_history_selected(p))
        
        # Agregar opción para limpiar historial
        if len(history) > 0:
            self.history_menu.addSeparator()
            clear_action = self.history_menu.addAction("🗑️ Limpiar historial")
            clear_action.triggered.connect(self._clear_history)
    
    def _on_history_selected(self, path: Path):
        """Callback cuando se selecciona un directorio del historial"""
        self.directory_changed.emit(path)
    
    def _clear_history(self):
        """Limpia el historial de directorios"""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Limpiar Historial",
            "¿Estás seguro de que deseas limpiar el historial de directorios?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            settings_manager.set(settings_manager.KEY_DIRECTORY_HISTORY, [])
            self._update_history_menu()
    
    def _on_select_clicked(self):
        """Callback del botón Seleccionar"""
        # Evitar abrir el diálogo de selección mientras hay un análisis en curso
        # para evitar que el usuario intente cambiar de directorio y cuelgue
        # hilos que aún están corriendo. El botón se deshabilita visualmente
        # en ese estado, pero añadimos una salvaguarda aquí por si acaso.
        if getattr(self, 'current_state', None) == 'analyzing':
            return

        self.select_directory_requested.emit()
    
    def _on_analyze_clicked(self):
        """Callback del botón Analizar"""
        self.analyze_requested.emit()
    
    def _on_reanalyze_clicked(self):
        """Callback del botón Re-analizar"""
        self.reanalyze_requested.emit()
    
    def _on_stop_clicked(self):
        """Callback del botón Detener"""
        self.stop_analysis_requested.emit()
    
    def _on_open_folder_clicked(self):
        """Callback del botón Abrir carpeta"""
        self.open_folder_requested.emit()
    
    def get_current_directory(self):
        """Retorna el directorio actual"""
        return self.current_directory
    
    def get_current_state(self):
        """Retorna el estado actual"""
        return self.current_state

    def show_folder_icon(self):
        """Muestra el icono de carpeta (tras completarse el análisis)"""
        self.folder_icon.setVisible(True)
        self.folder_icon.setEnabled(True)
        # Restaurar eventos de mouse
        self.folder_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        # Restaurar tooltip
        if self.current_directory:
            self.folder_icon.setToolTip(f"{str(self.current_directory)}\n\nClica aquí para abrir el directorio de trabajo")

    def hide_folder_icon(self):
        """Oculta el icono de carpeta y desactiva toda interacción"""
        self.folder_icon.setVisible(False)
        self.folder_icon.setEnabled(False)
        # Eliminar tooltip para que no aparezca aunque el usuario intente hovering
        self.folder_icon.setToolTip("")
        # Bloquear eventos de mouse completamente
        self.folder_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def update_directory_display(self, directory_path):
        """Método de compatibilidad con SearchBar - actualiza el directorio"""
        self.set_directory(directory_path)
    
    # ========================================================================
    # MÉTODOS PARA ACTUALIZAR EL RESUMEN (Compatibilidad con SummaryPanel)
    # ========================================================================
    
    def update_summary(self, results):
        """Actualiza el resumen con los resultados del análisis
        
        Args:
            results: Dict con claves 'stats', 'renaming', 'live_photos', etc.
        """
        # Expandir automáticamente al recibir resultados
        self._expand_summary()
        
        # Mostrar el frame de stats ahora que hay datos reales
        self.stats_frame.setVisible(True)
        
        # Actualizar stats con formato para miles
        stats = results.get('stats', {})
        self.stats_labels['images'].setText(format_number(stats.get('images', 0)))
        self.stats_labels['videos'].setText(format_number(stats.get('videos', 0)))
        self.stats_labels['total'].setText(format_number(stats.get('total', 0)))
        
        # Actualizar tooltips con números exactos
        self.stats_labels['images'].setToolTip(f"Imágenes: {stats.get('images', 0):,}")
        self.stats_labels['videos'].setToolTip(f"Videos: {stats.get('videos', 0):,}")
        self.stats_labels['total'].setToolTip(f"Total de archivos: {stats.get('total', 0):,}")
        
        # Actualizar badge de estado del análisis
        from utils.settings_manager import settings_manager
        from datetime import datetime
        
        timestamp = settings_manager.get_analysis_timestamp()
        if timestamp:
            time_ago = self._format_time_ago(timestamp)
            self.analysis_status_badge.setText(f"✓ Analizado {time_ago}")
            self.analysis_status_badge.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d4edda, stop:1 #c3e6cb);"
                "border: 1px solid #c3e6cb;"
                "border-radius: 6px;"
                "padding: 8px 16px;"
                "color: #155724;"
                "font-size: 12px;"
                "font-weight: 600;"
            )
        else:
            self.analysis_status_badge.setText("✓ Análisis completado")
            self.analysis_status_badge.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d4edda, stop:1 #c3e6cb);"
                "border: 1px solid #c3e6cb;"
                "border-radius: 6px;"
                "padding: 8px 16px;"
                "color: #155724;"
                "font-size: 12px;"
                "font-weight: 600;"
            )
        
        # Actualizar contadores de herramientas
        ren = results.get('renaming')
        lp = results.get('live_photos', {})
        org = results.get('organization')
        heic = results.get('heic')
        dup = results.get('duplicates')
        
        if 'live_photos' in self.summary_action_buttons:
            lp_count = lp.get('live_photos_found', 0) if isinstance(lp, dict) else (lp.live_photos_found if lp else 0)
            btn = self.summary_action_buttons['live_photos']
            btn.setText(f"📱  Live Photos ({format_number(lp_count)})")
            btn.setToolTip(f"Detectar y gestionar Live Photos de iOS\n{lp_count:,} encontrados")
        
        if 'heic' in self.summary_action_buttons:
            heic_count = heic.total_duplicates if heic else 0
            btn = self.summary_action_buttons['heic']
            btn.setText(f"🖼️  HEIC/JPG ({format_number(heic_count)})")
            btn.setToolTip(f"Eliminar duplicados HEIC con equivalente JPG\n{heic_count:,} duplicados encontrados")
        
        if 'duplicates' in self.summary_action_buttons:
            btn = self.summary_action_buttons['duplicates']
            if dup is not None:
                dup_count = dup.total_duplicates if hasattr(dup, 'total_duplicates') else 0
                btn.setText(f"🔍  Duplicados ({format_number(dup_count)})")
                btn.setToolTip(f"Encontrar archivos duplicados exactos y similares\n{dup_count:,} duplicados encontrados")
            else:
                btn.setText("🔍  Duplicados")
                btn.setToolTip("Encontrar archivos duplicados exactos y similares")
        
        if 'organization' in self.summary_action_buttons:
            org_count = org.total_files_to_move if org else 0
            btn = self.summary_action_buttons['organization']
            btn.setText(f"📁  Organizador ({format_number(org_count)})")
            btn.setToolTip(f"Organizar archivos por fecha o categoría\n{org_count:,} archivos a organizar")
        
        if 'renaming' in self.summary_action_buttons:
            ren_count = ren.need_renaming if ren else 0
            btn = self.summary_action_buttons['renaming']
            btn.setText(f"📝  Renombrado ({format_number(ren_count)})")
            btn.setToolTip(f"Renombrar archivos con formato estándar\n{ren_count:,} archivos necesitan renombrado")
    
    def set_status_not_analyzed(self):
        """Establece el badge de estado a 'No analizado'"""
        self.analysis_status_badge.setText("⚠️ No analizado")
        self.analysis_status_badge.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff3cd, stop:1 #ffeaa7);"
            "border: 1px solid #ffc107;"
            "border-radius: 6px;"
            "padding: 8px 16px;"
            "color: #856404;"
            "font-size: 12px;"
            "font-weight: 600;"
        )
        # Ocultar stats hasta que haya un análisis real
        self.stats_frame.setVisible(False)
    
    def set_status_analyzing(self):
        """Establece el badge de estado a 'Analizando...'"""
        self.analysis_status_badge.setText("⏳ Analizando...")
        self.analysis_status_badge.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d1ecf1, stop:1 #bee5eb);"
            "border: 1px solid #bee5eb;"
            "border-radius: 6px;"
            "padding: 8px 16px;"
            "color: #0c5460;"
            "font-size: 12px;"
            "font-weight: 600;"
        )
        # Ocultar stats durante análisis (se mostrarán cuando haya resultados)
        self.stats_frame.setVisible(False)
        # Expandir automáticamente durante análisis para mostrar progreso
        self._expand_summary()
    
    def _format_time_ago(self, timestamp_str: str) -> str:
        """Formatea un timestamp ISO en texto 'hace X tiempo'"""
        from datetime import datetime
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            delta = now - timestamp
            
            seconds = delta.total_seconds()
            if seconds < 60:
                return "hace menos de 1 min"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                return f"hace {minutes} min"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f"hace {hours}h"
            else:
                days = int(seconds / 86400)
                return f"hace {days}d"
        except Exception:
            return "recientemente"
    
    def show_progress(self):
        """Muestra el área de progreso"""
        self.progress_frame.setVisible(True)
        self._expand_summary()
    
    def hide_progress(self):
        """Oculta el área de progreso"""
        self.progress_frame.setVisible(False)
