"""
TopBar - Barra superior compacta con Smart Stats integrados.
Componente profesional optimizado para maximizar espacio vertical.

Diseño (Opción A - Smart Stats):
- Control Bar (60px): Título + directorio + badge integrado + acciones
- Smart Stats Bar (48px): General | Acciones Requeridas | Detectados [Colapsable]
- Total: 108px (vs 430px anterior = 75% reducción)

Smart Stats muestra información útil para decidir qué acciones tomar:
- General: Total archivos + tamaño
- Acciones Requeridas: Renombrado, HEIC, con warnings si > 0
- Detectados: Live Photos, Duplicados (exactos + similares), Organización
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
from ui.components.smart_stats_bar import SmartStatsBar
from ui.components.progress_overlay import ProgressOverlay
from utils.settings_manager import settings_manager
from utils.format_utils import (
    format_number, format_count_short, format_size_short,
    format_count_full, format_size_full
)
from utils.icons import icon_manager


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
    analyze_requested = pyqtSignal(str)  # Emite 'quick' o 'deep'
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
        self._has_completed_analysis = False  # Track if any analysis completed successfully
        self._last_analysis_type = 'quick'  # Recordar último tipo de análisis
        
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
        self.control_bar.setStyleSheet(styles.STYLE_TOPBAR_CONTROL)
        self.control_bar.setFixedHeight(60)  # Altura optimizada
        
        layout = QHBoxLayout(self.control_bar)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 12, 18, 12)  # Márgenes reducidos pero equilibrados
        
        # === TÍTULO DE LA APP (CLICKEABLE - INTEGRA ABOUT) ===
        # Container para icono + texto
        title_container = QWidget()
        title_container.setStyleSheet(styles.STYLE_TOPBAR_TITLE_CONTAINER)
        title_container.setCursor(Qt.CursorShape.PointingHandCursor)
        title_container.setToolTip("Acerca de")
        
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        
        # Icono de la app
        app_icon_label = icon_manager.create_icon_label('app', color='#2563eb', size=20)
        title_layout.addWidget(app_icon_label)
        
        # Texto del título
        title_label = QLabel(Config.APP_NAME)
        title_label.setStyleSheet(styles.STYLE_TOPBAR_TITLE_LABEL)
        title_layout.addWidget(title_label)
        
        # Hacer clickeable para mostrar About
        def on_logo_clicked(event):
            if self.main_window is not None:
                self.main_window.show_about_dialog()
            event.accept()
        
        title_container.mousePressEvent = on_logo_clicked
        
        layout.addWidget(title_container)
        
        # Espaciador reducido
        layout.addSpacing(12)
        
        # === CAMPO DE DIRECTORIO UNIFICADO (Estilo Profesional) ===
        directory_container = QFrame()
        directory_container.setStyleSheet(styles.STYLE_TOPBAR_DIR_CONTAINER)
        directory_container.setMinimumWidth(350)
        directory_container.setMaximumWidth(600)
        
        # Layout para el campo unificado con icono interno
        dir_outer_layout = QHBoxLayout(directory_container)
        # Sin margen para alinear con el TabView de la derecha
        dir_outer_layout.setContentsMargins(0, 0, 0, 0)
        dir_outer_layout.setSpacing(0)
        
        # Widget contenedor para el campo con icono y chevron integrados
        field_widget = QWidget()
        field_widget.setStyleSheet(styles.STYLE_TOPBAR_FIELD_WIDGET)
        field_widget.setFixedHeight(36)  # Altura compacta
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
        field_layout.setContentsMargins(10, 6, 6, 6)  # Márgenes compactos
        field_layout.setSpacing(6)
        
        # Icono de carpeta (izquierda) - usar QToolButton para que Qt rasterice correctamente
        # Inicialmente OCULTO - se muestra solo tras análisis completado
        from PyQt6.QtWidgets import QToolButton
        self.folder_icon = QToolButton()
        dir_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self.folder_icon.setIcon(dir_icon)
        self.folder_icon.setIconSize(QSize(18, 18))
        self.folder_icon.setFixedSize(QSize(24, 24))
        self.folder_icon.setAutoRaise(True)
        self.folder_icon.setStyleSheet(styles.STYLE_TOPBAR_FOLDER_ICON)
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
        self.directory_edit.setStyleSheet(styles.STYLE_TOPBAR_DIR_EDIT)
        
        # El click se maneja a nivel de `field_widget` para mantener
        # comportamiento consistente; no sobrescribimos mousePressEvent
        field_layout.addWidget(self.directory_edit, stretch=1)
        
        # Badge de metadata (archivos y tamaño, solo visible tras análisis)
        self.metadata_badge = QLabel()
        self.metadata_badge.setVisible(False)
        self.metadata_badge.setStyleSheet(styles.STYLE_TOPBAR_METADATA_BADGE)
        field_layout.addWidget(self.metadata_badge)
        
        # Badge de estado integrado (se muestra solo tras análisis)
        self.analysis_badge = QLabel()
        self.analysis_badge.setVisible(False)
        self.analysis_badge.setStyleSheet(styles.STYLE_TOPBAR_ANALYSIS_BADGE_SUCCESS)
        field_layout.addWidget(self.analysis_badge)
        
        # Botón de historial (chevron integrado)
        self.history_btn = QToolButton()
        # usar icono estándar (flecha hacia abajo) en lugar de caracter unicode
        arrow_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown)
        self.history_btn.setIcon(arrow_icon)
        self.history_btn.setIconSize(QSize(12, 12))
        self.history_btn.setFixedSize(26, 24)
        self.history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_btn.setToolTip("Ver historial de directorios")
        self.history_btn.setStyleSheet(styles.STYLE_TOPBAR_HISTORY_BTN)
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
        # Espacio entre el campo de directorio y los botones de acción
        layout.addSpacing(12)
        
        # === BOTONES DE ACCIÓN ===
        # Botón: Selector de directorio (solo icono, compacto)
        self.select_btn = QPushButton()
        self.select_btn.setObjectName("select_btn")
        icon_manager.set_button_icon(self.select_btn, 'folder', color='#2563eb', size=18)
        self.select_btn.setFixedSize(36, 32)
        self.select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_btn.setStyleSheet(styles.STYLE_TOPBAR_SELECT_BTN)
        self.select_btn.clicked.connect(self._on_select_clicked)
        self.select_btn.setToolTip("Seleccionar directorio")
        layout.addWidget(self.select_btn)
        
        # === SPLIT BUTTON: Analizar (con dropdown para rápido/profundo/re-analizar) ===
        # Widget contenedor del split button
        self.split_container = QWidget()
        self.split_container.setObjectName("split_container")  # Para estilos específicos
        self.split_container.setFixedHeight(32)
        split_layout = QHBoxLayout(self.split_container)
        split_layout.setSpacing(0)
        split_layout.setContentsMargins(0, 0, 0, 0)
        
        # Parte 1: Botón principal "Analizar"
        self.analyze_btn = QPushButton("Analizar")
        self.analyze_btn.setObjectName("analyze_btn")
        self.analyze_btn.setFixedHeight(32)
        self.analyze_btn.setMinimumWidth(90)
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.clicked.connect(self._on_analyze_quick)
        self.analyze_btn.setToolTip(
            "Análisis rápido: Live Photos, HEIC, renombrado, "
            "organización, duplicados exactos (~1-5 min)"
        )
        
        # Separador visual (línea vertical)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFixedSize(1, 20)
        separator.setStyleSheet(styles.STYLE_TOPBAR_SPLIT_SEPARATOR)
        
        # Parte 2: Botón dropdown (chevron)
        self.dropdown_btn = QPushButton()
        self.dropdown_btn.setObjectName("dropdown_btn")

        # Insertar icono en el QPushButton como widget: usar stylesheet fallback
        self.dropdown_btn.setFixedSize(30, 32)
        self.dropdown_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Si icon_manager soporta setIcon, intentar usarlo; si no, caer a texto
        try:
            from PyQt6.QtGui import QIcon
            self.dropdown_btn.setIcon(icon_manager.get_icon('down', color='#ffffff'))
            self.dropdown_btn.setIconSize(QSize(12, 12))
            self.dropdown_btn.setText("")
        except Exception:
            self.dropdown_btn.setText("▼")
        
        # Crear menú de opciones
        self.analyze_menu = QMenu(self.dropdown_btn)
        self.analyze_menu.setStyleSheet(styles.STYLE_TOPBAR_ANALYZE_MENU)
        
        # Opciones del menú
        self.action_quick = self.analyze_menu.addAction("⚡ Análisis rápido")
        self.action_quick.triggered.connect(self._on_analyze_quick)
        self.action_quick.setToolTip(
            "Análisis rápido: Live Photos, HEIC, renombrado, "
            "organización, duplicados exactos (~1-5 min)"
        )
        
        self.action_deep = self.analyze_menu.addAction("🔍 Análisis profundo")
        self.action_deep.triggered.connect(self._on_analyze_deep)
        self.action_deep.setToolTip(
            "Análisis profundo: Todo lo anterior + duplicados "
            "similares (~10-30 min según tamaño del directorio)"
        )
        
        self.analyze_menu.addSeparator()
        
        self.action_reanalyze = self.analyze_menu.addAction("🔄 Re-analizar")
        self.action_reanalyze.triggered.connect(self._on_reanalyze)
        self.action_reanalyze.setEnabled(False)  # Disabled por defecto
        self.action_reanalyze.setVisible(False)  # Hidden por defecto
        self.action_reanalyze.setToolTip("Re-ejecutar el último tipo de análisis realizado")
        
        # Asociar menú al botón dropdown
        self.dropdown_btn.setMenu(self.analyze_menu)
        
        # Añadir todo al layout del split button
        split_layout.addWidget(self.analyze_btn)
        split_layout.addWidget(separator)
        split_layout.addWidget(self.dropdown_btn)

        # Forzar tamaño compacto del contenedor (evitar que expanda)
        # Use module-level QSizePolicy imported at top of file
        self.split_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # Calcular un width razonable (botón principal + dropdown + margen)
        self.split_container.setMinimumWidth(140)
        self.split_container.setMaximumWidth(220)
        
        # Estilo del split button container
        self.split_container.setStyleSheet(styles.STYLE_TOPBAR_SPLIT_CONTAINER)
        
        layout.addWidget(self.split_container)
        
        # Referencia usada por ActionButtons y controllers
        self.reanalyze_btn = self.analyze_btn
        
        # Botón: Detener análisis
        self.stop_btn = QPushButton(" Detener")
        icon_manager.set_button_icon(self.stop_btn, 'stop', color='#856404', size=16)
        self.stop_btn.setFixedHeight(32)
        self.stop_btn.setMinimumWidth(90)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet(styles.STYLE_TOPBAR_STOP_BTN)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_btn)
        
        # Espaciador antes de los iconos
        layout.addSpacing(6)
        
        # === CHEVRON TOGGLE SUTIL (para smart stats) ===
        self.stats_toggle_btn = QPushButton("▼")
        self.stats_toggle_btn.setFixedSize(32, 32)
        self.stats_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stats_toggle_btn.setToolTip("Mostrar/ocultar resumen del análisis")
        self.stats_toggle_btn.setVisible(False)  # Oculto hasta que haya análisis
        self.stats_toggle_btn.setStyleSheet(styles.STYLE_TOPBAR_STATS_TOGGLE)
        self.stats_toggle_btn.clicked.connect(self._toggle_summary)
        layout.addWidget(self.stats_toggle_btn)
        
        # === ICONO DE CONFIGURACIÓN (ACCESO DIRECTO) ===
        config_btn = QPushButton()
        icon_manager.set_button_icon(config_btn, 'settings', color='#64748b', size=20)
        config_btn.setFixedSize(32, 32)
        config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        config_btn.setToolTip("Configuración")
        config_btn.setStyleSheet(styles.STYLE_TOPBAR_CONFIG_BTN)
        if self.main_window is not None:
            config_btn.clicked.connect(self.main_window.toggle_config)
        layout.addWidget(config_btn)
        
        main_layout.addWidget(self.control_bar)
        
        # ===== SMART STATS BAR =====
        self.smart_stats_bar = SmartStatsBar(self)
        self.smart_stats_bar.stat_clicked.connect(self._on_stat_clicked)
        main_layout.addWidget(self.smart_stats_bar)
        
        # ===== PROGRESS OVERLAY =====
        self.progress_overlay = ProgressOverlay(self)
    
    def _on_stat_clicked(self, key: str):
        """Navega a la pestaña correspondiente"""
        if not self.main_window or not hasattr(self.main_window, 'tab_index_map'):
            return
        
        tab_map = {
            'renaming': 'renaming',
            'heic': 'heic',
            'live_photos': 'live_photos',
            'duplicates_exact': 'duplicates',
            'duplicates_similar': 'duplicates',
            'organization': 'organization'
        }
        
        if key in tab_map:
            tab_key = tab_map[key]
            if tab_key in self.main_window.tab_index_map:
                idx = self.main_window.tab_index_map[tab_key]
                self.main_window.tabs_widget.setCurrentIndex(idx)
    
    def _toggle_summary(self):
        """Toggle de Smart Stats"""
        if self._is_summary_expanded:
            self._collapse_summary()
        else:
            self._expand_summary()
    
    def _expand_summary(self, animate=True):
        """Expande Smart Stats"""
        if self._is_summary_expanded:
            return
        
        self._is_summary_expanded = True
        self.stats_toggle_btn.setText("▲")
        self.smart_stats_bar.setVisible(True)
        
        target_height = 112
        
        if animate:
            self._animation = QPropertyAnimation(self.smart_stats_bar, b"maximumHeight")
            self._animation.setDuration(200)
            self._animation.setStartValue(0)
            self._animation.setEndValue(target_height)
            self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animation.start()
        else:
            self.smart_stats_bar.setMaximumHeight(target_height)
        
        settings_manager.set('summary_expanded', True)
    
    def _collapse_summary(self, animate=True):
        """Colapsa Smart Stats"""
        if not self._is_summary_expanded:
            return
        
        self._is_summary_expanded = False
        self.stats_toggle_btn.setText("▼")
        
        if animate:
            self._animation = QPropertyAnimation(self.smart_stats_bar, b"maximumHeight")
            self._animation.setDuration(200)
            self._animation.setStartValue(self.smart_stats_bar.height())
            self._animation.setEndValue(0)
            self._animation.setEasingCurve(QEasingCurve.Type.InCubic)
            self._animation.finished.connect(lambda: self.smart_stats_bar.setVisible(False))
            self._animation.start()
        else:
            self.smart_stats_bar.setMaximumHeight(0)
            self.smart_stats_bar.setVisible(False)
        
        settings_manager.set('summary_expanded', False)
    
    def clear_stats(self):
        """Limpia los stats y colapsa el panel"""
        self._collapse_summary(animate=True)
        self.stats_toggle_btn.setVisible(False)
        self.metadata_badge.setVisible(False)
        self.smart_stats_bar.clear_stats()
    
    def _update_button_visibility(self):
        """Actualiza visibilidad de botones según el estado actual
        
        Estados soportados: empty, ready, analyzing, analyzed
        """
        # Actualizar tooltip del botón selector según estado
        if self.current_state == 'empty':
            self.select_btn.setToolTip("Seleccionar directorio")
        elif self.current_state == 'ready':
            self.select_btn.setToolTip("Cambiar directorio")
        elif self.current_state == 'analyzing':
            self.select_btn.setToolTip("No puedes cambiar durante el análisis")
        elif self.current_state == 'analyzed':
            self.select_btn.setToolTip("Cambiar directorio")
        
        # === ESTADO: EMPTY ===
        if self.current_state == 'empty':
            # Selector: enabled
            self.select_btn.setEnabled(True)
            self.select_btn.setVisible(True)
            
            # Split button: disabled
            self.split_container.setEnabled(False)
            self.split_container.setVisible(True)
            self.analyze_btn.setText("Analizar")
            self.action_reanalyze.setVisible(False)
            
            # Stop button: hidden
            self.stop_btn.setHidden(True)
            
            # Campo de directorio
            self.directory_edit.setText("Ningún directorio seleccionado")
            self.metadata_badge.setVisible(False)
            self.analysis_badge.setVisible(False)
            self.folder_icon.setVisible(False)
            
            # Smart stats y toggle
            self.smart_stats_bar.setVisible(False)
            self.stats_toggle_btn.setVisible(False)
            
            # Historial
            history = settings_manager.get_directory_history()
            self.history_btn.setEnabled(len(history) > 0)
            
            # Campo interactivo
            if hasattr(self, 'field_widget'):
                self.field_widget.setEnabled(True)
                self.field_widget.setCursor(Qt.CursorShape.ArrowCursor)
                self.field_widget.setToolTip(
                    "Arrastra una carpeta aquí\n" 
                    "o usa el botón 'Seleccionar' para elegir el directorio de trabajo"
                )
        
        # === ESTADO: READY ===
        elif self.current_state == 'ready':
            # Selector: enabled
            self.select_btn.setEnabled(True)
            self.select_btn.setVisible(True)
            
            # Split button: enabled
            self.split_container.setEnabled(True)
            self.split_container.setVisible(True)
            self.analyze_btn.setText("Analizar")
            self.action_reanalyze.setVisible(False)
            
            # Stop button: hidden
            self.stop_btn.setHidden(True)
            
            # Campo de directorio: path visible, badges ocultos
            self.metadata_badge.setVisible(False)
            self.analysis_badge.setVisible(False)
            self.folder_icon.setVisible(True)
            
            # Smart stats: ocultos
            self.smart_stats_bar.setVisible(False)
            self.stats_toggle_btn.setVisible(False)
            
            # Historial: enabled
            self.history_btn.setEnabled(True)
            
            # Campo clickeable
            if hasattr(self, 'field_widget'):
                self.field_widget.setEnabled(True)
                self.field_widget.setCursor(Qt.CursorShape.PointingHandCursor)
                self.field_widget.setToolTip(
                    "Arrastra un directorio aquí o pulsa el botón de 'Cambiar' para cambiar el directorio de trabajo"
                )
        
        # === ESTADO: ANALYZING ===
        elif self.current_state == 'analyzing':
            # Selector: disabled
            self.select_btn.setEnabled(False)
            self.select_btn.setVisible(True)
            
            # Split button: hidden
            self.split_container.setVisible(False)
            
            # Stop button: visible
            self.stop_btn.setVisible(True)
            
            # Badges ocultos durante análisis
            self.metadata_badge.setVisible(False)
            self.analysis_badge.setVisible(False)
            
            # Smart stats: visible con progreso
            self.smart_stats_bar.setVisible(True)
            self.stats_toggle_btn.setVisible(True)
            
            # Historial: disabled
            self.history_btn.setEnabled(False)
            
            # Campo no interactivo
            if hasattr(self, 'field_widget'):
                self.field_widget.setCursor(Qt.CursorShape.ArrowCursor)
                try:
                    self.field_widget.setEnabled(False)
                except Exception:
                    pass
        
        # === ESTADO: ANALYZED ===
        elif self.current_state == 'analyzed':
            # Selector: enabled
            self.select_btn.setEnabled(True)
            self.select_btn.setVisible(True)
            
            # Split button: enabled, texto "Re-analizar"
            self.split_container.setEnabled(True)
            self.split_container.setVisible(True)
            self.analyze_btn.setText("Re-analizar")
            self.action_reanalyze.setVisible(True)
            self.action_reanalyze.setEnabled(True)
            
            # Stop button: hidden
            self.stop_btn.setHidden(True)
            
            # Mostrar badges
            self.metadata_badge.setVisible(True)
            self.analysis_badge.setVisible(True)
            
            # Smart stats: visible con resultados
            self.smart_stats_bar.setVisible(True)
            self.stats_toggle_btn.setVisible(True)
            
            # Historial: enabled
            self.history_btn.setEnabled(True)
            
            # Campo clickeable
            if hasattr(self, 'field_widget'):
                try:
                    self.field_widget.setEnabled(True)
                except Exception:
                    pass
                self.field_widget.setCursor(Qt.CursorShape.PointingHandCursor)
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
        
        old_state = self.current_state
        self.current_state = state
        
        # Si cambiamos de 'analyzed' a 'ready' o 'empty', limpiar stats
        if old_state == 'analyzed' and state in ['ready', 'empty']:
            self.clear_stats()
            self.set_status_not_analyzed()
        
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
    
    def _on_analyze_quick(self):
        """Lanza análisis rápido (sin duplicados similares)"""
        self._last_analysis_type = 'quick'
        self.analyze_requested.emit('quick')
        self.set_state('analyzing')
    
    def _on_analyze_deep(self):
        """Lanza análisis profundo (con duplicados similares)"""
        self._last_analysis_type = 'deep'
        self.analyze_requested.emit('deep')
        self.set_state('analyzing')
    
    def _on_reanalyze(self):
        """Re-ejecuta el último análisis realizado"""
        if self._last_analysis_type == 'quick':
            self._on_analyze_quick()
        else:
            self._on_analyze_deep()
    
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

    def resizeEvent(self, event):
        """Ajusta el tamaño del progress_overlay cuando cambia el tamaño de la ventana"""
        super().resizeEvent(event)
        if hasattr(self, 'progress_overlay'):
            self.progress_overlay.adjust_width(self.width())

    def update_directory_display(self, directory_path):
        """Actualiza el directorio mostrado (usado por main_window)"""
        self.set_directory(directory_path)
    
    def update_metadata_badge(self, file_count: int, total_size: int):
        """Actualiza el badge de metadata con valores abreviados.
        
        Args:
            file_count: Número total de archivos
            total_size: Tamaño total en bytes
        """
        short_count = format_count_short(file_count)
        short_size = format_size_short(total_size)
        
        self.metadata_badge.setText(f"{short_count} │ {short_size}")
        
        # Tooltip con valores completos
        full_count = format_count_full(file_count)
        full_size = format_size_full(total_size)
        self.metadata_badge.setToolTip(f"{full_count} archivos · {full_size}")
        
        self.metadata_badge.setVisible(True)
    
    # ========================================================================
    # MÉTODOS PARA ACTUALIZAR EL RESUMEN
    # ========================================================================
    def update_smart_stats(self, results):
        """Actualiza los Smart Stats con datos del análisis - delega al componente SmartStatsBar"""
        stats = results.get('stats', {})
        total_files = stats.get('total', 0)
        total_size = stats.get('total_size', 0)
        
        # Actualizar metadata badge
        self.update_metadata_badge(total_files, total_size)
        
        # Delegar actualización de stats al componente
        self.smart_stats_bar.update_stats(results)
        
        # Mostrar badge completado
        self.set_status_completed()
        
        # Expandir automáticamente
        self._expand_summary()
    
    
    def update_summary(self, results):
        """Actualiza el resumen - delega a update_smart_stats"""
        self.update_smart_stats(results)

    def set_status_not_analyzed(self):
        """Establece el badge de estado a 'No analizado' (oculto) y limpia stats"""
        self.analysis_badge.setVisible(False)
        
        # Limpiar stats y colapsar panel
        self.clear_stats()

    def set_status_analyzing(self):
        """Establece el badge de estado a 'Analizando...'"""
        self.analysis_badge.setText("⏳ Analizando")  # Unicode hourglass, no emoji
        self.analysis_badge.setStyleSheet(styles.STYLE_TOPBAR_ANALYSIS_BADGE_ANALYZING)
        self.analysis_badge.setVisible(True)
        # Mostrar progreso superpuesto
        self.show_progress()
    
    def set_status_canceled(self):
        """Establece el badge de estado a 'Cancelado' y limpia stats parciales"""
        self.analysis_badge.setText("⚠️ Cancelado")  # Unicode warning, no emoji
        self.analysis_badge.setStyleSheet(styles.STYLE_TOPBAR_ANALYSIS_BADGE_CANCELED)
        self.analysis_badge.setVisible(True)
        
        # Limpiar stats parciales (no queremos mostrar resultados incompletos)
        self.clear_stats()
    
    def set_status_completed(self):
        """Establece el badge de estado a 'Completado'"""
        self._has_completed_analysis = True  # Marcar que se completó al menos un análisis
        self.analysis_badge.setText("✓ Analizado")  # Unicode checkmark, no emoji
        self.analysis_badge.setStyleSheet(styles.STYLE_TOPBAR_ANALYSIS_BADGE_SUCCESS)
        self.analysis_badge.setVisible(True)
        self.stats_toggle_btn.setVisible(True)
        # Actualizar botón a "Cambiar" después del primer análisis exitoso
        self._update_button_visibility()


    def show_progress(self):
        """Muestra el área de progreso superpuesta"""
        self.progress_overlay.show_animated(self.width())
    
    def hide_progress(self):
        """Oculta el área de progreso superpuesta"""
        self.progress_overlay.hide_animated()
    
    # Properties para acceso directo desde ProgressController
    @property
    def summary_progress_label(self):
        return self.progress_overlay.progress_label
    
    @property
    def summary_progress_bar(self):
        return self.progress_overlay.progress_bar
    
    @property
    def summary_progress_detail(self):
        return self.progress_overlay.progress_detail
