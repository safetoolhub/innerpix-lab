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
from utils.settings_manager import settings_manager
from utils.format_utils import format_number
from utils.icons import icon_manager
import os


# ===== FUNCIONES AUXILIARES DE FORMATO =====

def format_count_short(count: int) -> str:
    """Formato abreviado de conteo de archivos."""
    if count >= 1_000_000:
        return f"{count/1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count/1_000:.1f}k"
    return str(count)


def format_size_short(bytes_size: int) -> str:
    """Formato abreviado de tamaño de archivos."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{int(bytes_size)}{unit}"
        bytes_size /= 1024
    return f"{int(bytes_size)}PB"


def format_count_full(count: int) -> str:
    """Formato completo con separadores de miles."""
    return f"{count:,}"


def format_size_full(bytes_size: int) -> str:
    """Formato completo de tamaño legible."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


def apply_stat_state(widget, state: str, key: str):
    """Aplica estilos según el estado del stat (amarillo/verde/gris).
    
    Args:
        widget: El widget QFrame del stat
        state: 'detected' (amarillo), 'clean' (verde), 'not-analyzed' (gris)
        key: Clave del stat para el objectName
    """
    if state == 'detected':
        # 🟡 AMARILLO - Detectado (count > 0)
        widget.setStyleSheet(
            f"QFrame#stat_{key} {{"
            "  background: rgba(234, 179, 8, 0.12);"  # warning at 12% opacity
            "  border: 1px solid rgba(234, 179, 8, 0.25);"
            "  border-radius: 6px;"
            "  padding: 6px 8px;"
            "}"
            f"QFrame#stat_{key}:hover {{"
            "  background: rgba(234, 179, 8, 0.17);"
            "  border-color: rgba(234, 179, 8, 0.35);"
            "}"
        )
    elif state == 'clean':
        # 🟢 VERDE - Sin detección (count == 0)
        widget.setStyleSheet(
            f"QFrame#stat_{key} {{"
            "  background: rgba(16, 185, 129, 0.08);"  # success at 8% opacity
            "  border: 1px solid rgba(16, 185, 129, 0.15);"
            "  border-radius: 6px;"
            "  padding: 6px 8px;"
            "}"
            f"QFrame#stat_{key}:hover {{"
            "  background: rgba(16, 185, 129, 0.13);"
            "  border-color: rgba(16, 185, 129, 0.25);"
            "}"
        )
    else:  # 'not-analyzed'
        # ⚪ GRIS - No analizado
        widget.setStyleSheet(
            f"QFrame#stat_{key} {{"
            "  background: #f8f9fa;"
            "  border: 1px solid #dee2e6;"
            "  border-radius: 6px;"
            "  padding: 6px 8px;"
            "}"
            f"QFrame#stat_{key}:hover {{"
            "  background: #e9ecef;"
            "}"
        )


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
        try:
            tooltip_dark = styles.STYLE_TOOLTIP_DARK
        except Exception:
            tooltip_dark = ""
        # No aplicar STYLE_SEARCH_CONTAINER (causaba bordes duplicados con field_widget)
        self.control_bar.setStyleSheet(
            "QFrame { background-color: white; border: none; padding: 0px; }" + tooltip_dark
        )
        self.control_bar.setFixedHeight(60)  # Altura optimizada
        
        layout = QHBoxLayout(self.control_bar)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 12, 18, 12)  # Márgenes reducidos pero equilibrados
        
        # === TÍTULO DE LA APP (CLICKEABLE - INTEGRA ABOUT) ===
        # Container para icono + texto
        title_container = QWidget()
        title_container.setStyleSheet(
            "QWidget {"
            "  background: transparent;"
            "  border: none;"
            "  border-radius: 6px;"
            "  padding: 4px 8px;"
            "}"
            "QWidget:hover {"
            "  background: rgba(37, 99, 235, 0.06);"  # primary blue at 6% opacity
            "}"
        )
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
        title_label.setStyleSheet(
            "font-size: 15px;"
            "font-weight: 700;"
            "color: #1a1a1a;"
            "background: transparent;"
            "border: none;"
            "padding: 0px;"
        )
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
        
        # Badge de metadata (archivos y tamaño, solo visible tras análisis)
        self.metadata_badge = QLabel()
        self.metadata_badge.setVisible(False)
        self.metadata_badge.setStyleSheet(
            "QLabel {"
            "  background: rgba(120, 113, 108, 0.08);"  # brown-600 at 8% opacity
            "  color: #64748b;"  # text-secondary
            "  font-family: 'Courier New', monospace;"
            "  font-size: 10px;"
            "  font-weight: 500;"
            "  padding: 2px 6px;"
            "  border-radius: 4px;"
            "  border: 1px solid rgba(120, 113, 108, 0.12);"
            "}"
        )
        field_layout.addWidget(self.metadata_badge)
        
        # Badge de estado integrado (se muestra solo tras análisis)
        self.analysis_badge = QLabel()
        self.analysis_badge.setVisible(False)
        self.analysis_badge.setStyleSheet(
            "QLabel {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d4edda, stop:1 #c3e6cb);"
            "  border: 1px solid #c3e6cb;"
            "  border-radius: 4px;"
            "  padding: 2px 8px;"
            "  color: #155724;"
            "  font-size: 11px;"
            "  font-weight: 600;"
            "}"
        )
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
        # Botón: Selector de directorio (solo icono, compacto)
        self.select_btn = QPushButton()
        self.select_btn.setObjectName("select_btn")
        icon_manager.set_button_icon(self.select_btn, 'folder', color='#2563eb', size=18)
        self.select_btn.setFixedSize(36, 32)
        self.select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_btn.setStyleSheet(
            "QPushButton#select_btn {"
            "  background-color: transparent;"
            "  border: 1px solid #cbd5e0;"
            "  border-radius: 6px;"
            "}"
            "QPushButton#select_btn:hover:enabled {"
            "  background-color: rgba(37, 99, 235, 0.08);"
            "  border-color: #2563eb;"
            "}"
            "QPushButton#select_btn:pressed:enabled {"
            "  background-color: rgba(37, 99, 235, 0.15);"
            "}"
            "QPushButton#select_btn:disabled {"
            "  opacity: 0.5;"
            "}"
        )
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
        separator.setStyleSheet(
            "QFrame {"
            "  background: rgba(255, 255, 255, 0.3);"
            "  border: none;"
            "}"
        )
        
        # Parte 2: Botón dropdown (chevron)
        self.dropdown_btn = QPushButton()
        self.dropdown_btn.setObjectName("dropdown_btn")
        # usar icono en vez de texto para mejor rasterización
    # use existing 'down' icon from icon manager
    # chevron widget not used directly; icon will be set on the button
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
        self.analyze_menu.setStyleSheet(
            "QMenu {"
            "  background: white;"
            "  border: 1px solid #cbd5e0;"
            "  border-radius: 8px;"
            "  padding: 6px;"
            "}"
            "QMenu::item {"
            "  padding: 8px 16px;"
            "  border-radius: 4px;"
            "  color: #334155;"
            "  font-size: 13px;"
            "}"
            "QMenu::item:selected {"
            "  background: #f1f5f9;"
            "}"
            "QMenu::item:disabled {"
            "  color: #94a3b8;"
            "  opacity: 0.5;"
            "}"
            "QMenu::separator {"
            "  height: 1px;"
            "  background: #e2e8f0;"
            "  margin: 4px 0;"
            "}"
        )
        
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
        self.split_container.setStyleSheet(
            "QWidget#split_container {"
            "  background-color: #2563eb;"
            "  border: none;"
            "  border-radius: 6px;"
            "}"
            "QWidget#split_container:hover {"
            "  background-color: #1d4ed8;"
            "}"
            "QWidget#split_container:disabled {"
            "  background-color: #94a3b8;"
            "  opacity: 0.6;"
            "}"
            "QWidget#split_container QPushButton {"
            "  background-color: transparent;"
            "  color: white;"
            "  border: none;"
            "  font-size: 13px;"
            "  font-weight: 600;"
            "  padding: 0 12px;"
            "}"
            "QWidget#split_container QPushButton#analyze_btn {"
            "  padding-left: 14px;"
            "  padding-right: 10px;"
            "}"
            "QWidget#split_container QPushButton#dropdown_btn {"
            "  padding: 0 8px;"
            "  border-left: 1px solid rgba(255,255,255,0.12);"
            "  min-width: 30px;"
            "}"
            "QWidget#split_container QPushButton:hover {"
            "  background-color: rgba(255, 255, 255, 0.12);"
            "}"
            "QWidget#split_container QPushButton:disabled {"
            "  color: #e2e8f0;"
            "}"
        )
        
        layout.addWidget(self.split_container)
        
        # Alias de compatibilidad (algunos componentes pueden referenciar reanalyze_btn)
        self.reanalyze_btn = self.analyze_btn  # Mismo botón, texto cambia según estado
        
        # Botón: Detener análisis
        self.stop_btn = QPushButton(" Detener")
        icon_manager.set_button_icon(self.stop_btn, 'stop', color='#856404', size=16)
        self.stop_btn.setFixedHeight(32)
        self.stop_btn.setMinimumWidth(90)
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
        
        # Espaciador antes de los iconos
        layout.addSpacing(6)
        
        # === CHEVRON TOGGLE SUTIL (para smart stats) ===
        self.stats_toggle_btn = QPushButton("▼")
        self.stats_toggle_btn.setFixedSize(32, 32)
        self.stats_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stats_toggle_btn.setToolTip("Mostrar/ocultar resumen del análisis")
        self.stats_toggle_btn.setVisible(False)  # Oculto hasta que haya análisis
        self.stats_toggle_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent;"
            "  border: 1px solid #e1e8ed;"
            "  border-radius: 6px;"
            "  color: #64748b;"
            "  font-size: 14px;"
            "  font-weight: bold;"
            "  padding: 0px;"
            "}"
            "QPushButton:hover {"
            "  background: #f1f5f9;"
            "  border-color: #cbd5e0;"
            "  color: #334155;"
            "}"
            "QPushButton:pressed {"
            "  background: #e2e8f0;"
            "}"
        )
        self.stats_toggle_btn.clicked.connect(self._toggle_summary)
        layout.addWidget(self.stats_toggle_btn)
        
        # === ICONO DE CONFIGURACIÓN (ACCESO DIRECTO) ===
        config_btn = QPushButton()
        icon_manager.set_button_icon(config_btn, 'settings', color='#64748b', size=20)
        config_btn.setFixedSize(32, 32)
        config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        config_btn.setToolTip("Configuración")
        config_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent;"
            "  border: none;"
            "  border-radius: 6px;"
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
        
        main_layout.addWidget(self.control_bar)
        
        # ===== SMART STATS BAR (colapsable, 48px) =====
        self._create_smart_stats_bar()
        main_layout.addWidget(self.smart_stats_container)
        
        # ===== PROGRESS BAR (superpuesto, no afecta layout) =====
        self._create_progress_bar()
        
        # Aliases de compatibilidad con código existente
        self.summary_container = self.smart_stats_container
        self.summary_panel = self.smart_stats_container
        self.analysis_status_badge = self.analysis_badge  # Alias
        self.stats_labels = {}  # Ya no se usa pero mantener por compatibilidad
        self.summary_action_buttons = {}  # Ya no se usa
        self.toggle_summary_btn = self.stats_toggle_btn  # Alias
    
    def _create_smart_stats_bar(self):
        """Crea la barra de Smart Stats con grid 3×2 (Redundancias | Duplicados | Organización)"""
        # Inicializar diccionario ANTES de crear columnas
        self.smart_stats = {}
        
        # Container animable
        self.smart_stats_container = QFrame()
        self.smart_stats_container.setStyleSheet(
            "QFrame {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 #fafbfc, stop:1 #ffffff);"
            "  border-top: 1px solid #e1e8ed;"
            "  border-bottom: 1px solid #cbd5e0;"
            "}"
        )
        self.smart_stats_container.setMinimumHeight(0)
        self.smart_stats_container.setMaximumHeight(0)  # Inicialmente colapsado
        self.smart_stats_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.smart_stats_container.setVisible(False)
        
        container_layout = QHBoxLayout(self.smart_stats_container)
        container_layout.setContentsMargins(16, 8, 16, 8)
        container_layout.setSpacing(20)
        
        # === COLUMNA 1: REDUNDANCIAS ===
        self.redundancies_column = self._create_stat_column(
            title="REDUNDANCIAS",
            stats_keys=['live_photos', 'heic']
        )
        container_layout.addWidget(self.redundancies_column, 1)
        
        # Separador vertical
        vsep1 = self._create_separator()
        container_layout.addWidget(vsep1)
        
        # === COLUMNA 2: DUPLICADOS ===
        self.duplicates_column = self._create_stat_column(
            title="DUPLICADOS",
            stats_keys=['duplicates_exact', 'duplicates_similar']
        )
        container_layout.addWidget(self.duplicates_column, 1)
        
        # Separador vertical
        vsep2 = self._create_separator()
        container_layout.addWidget(vsep2)
        
        # === COLUMNA 3: ORGANIZACIÓN ===
        self.organization_column = self._create_stat_column(
            title="ORGANIZACIÓN",
            stats_keys=['renaming', 'organization']
        )
        container_layout.addWidget(self.organization_column, 1)
        
        # Inicializar stats con placeholders
        self._initialize_stats_placeholders()
    
    def _create_separator(self):
        """Crea un separador vertical con gradiente sutil"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(
            "QFrame {"
            "  border: none;"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 transparent, "
            "    stop:0.2 rgba(120, 113, 108, 0.15), "
            "    stop:0.8 rgba(120, 113, 108, 0.15), "
            "    stop:1 transparent);"
            "  width: 1px;"
            "  margin: 0px 20px;"
            "}"
        )
        return separator
    
    def _initialize_stats_placeholders(self):
        """Inicializa los stats con valores placeholder"""
        # Columna 1: REDUNDANCIAS
        if 'live_photos' in self.smart_stats:
            widget = self.smart_stats['live_photos']
            icon_manager.set_button_icon(widget.icon_label, 'live-photo', color='#64748b', size=16)
            widget.text_label.setText("Live Photos")
            widget.value_label.setText("—")
            widget.setToolTip("Detecta pares de Live Photos (foto + video MOV)")
        
        if 'heic' in self.smart_stats:
            widget = self.smart_stats['heic']
            icon_manager.set_button_icon(widget.icon_label, 'heic', color='#64748b', size=16)
            widget.text_label.setText("HEIC Duplicados")
            widget.value_label.setText("—")
            widget.setToolTip("Duplicados HEIC con equivalente JPG")
        
        # Columna 2: DUPLICADOS
        if 'duplicates_exact' in self.smart_stats:
            widget = self.smart_stats['duplicates_exact']
            icon_manager.set_button_icon(widget.icon_label, 'duplicate-exact', color='#64748b', size=16)
            widget.text_label.setText("Exactos")
            widget.value_label.setText("—")
            widget.setToolTip("Archivos duplicados por hash (contenido idéntico)")
        
        if 'duplicates_similar' in self.smart_stats:
            widget = self.smart_stats['duplicates_similar']
            icon_manager.set_button_icon(widget.icon_label, 'eye', color='#64748b', size=16)
            widget.text_label.setText("Similares")
            widget.value_label.setText("—")
            widget.setToolTip("Duplicados similares (requiere análisis manual)")
        
        # Columna 3: ORGANIZACIÓN
        if 'renaming' in self.smart_stats:
            widget = self.smart_stats['renaming']
            icon_manager.set_button_icon(widget.icon_label, 'rename', color='#64748b', size=16)
            widget.text_label.setText("Renombrar")
            widget.value_label.setText("—")
            widget.setToolTip("Archivos que necesitan renombrado normalizado")
        
        if 'organization' in self.smart_stats:
            widget = self.smart_stats['organization']
            icon_manager.set_button_icon(widget.icon_label, 'organize', color='#64748b', size=16)
            widget.text_label.setText("Organizar")
            widget.value_label.setText("—")
            widget.setToolTip("Archivos que pueden organizarse por fecha/carpeta")
    
    def _create_stat_column(self, title: str, stats_keys: list):
        """Crea una columna de stats con un título y varios items"""
        column = QFrame()
        column.setStyleSheet("background: transparent; border: none;")
        
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)  # Spacing entre título y primera fila
        
        # Título de la columna
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "color: #64748b; "
            "font-size: 10px; "
            "font-weight: 600; "
            "letter-spacing: 0.05em; "
            "background: transparent; "
            "padding: 0px; "
            "margin-bottom: 0px;"
        )
        layout.addWidget(title_label)
        
        # Container para los stats
        stats_container = QVBoxLayout()
        stats_container.setSpacing(6)  # Spacing entre filas
        
        for key in stats_keys:
            stat_widget = self._create_stat_item(key)
            self.smart_stats[key] = stat_widget
            stats_container.addWidget(stat_widget)
        
        layout.addLayout(stats_container)
        layout.addStretch()
        
        return column
    
    def _create_stat_item(self, key: str):
        """Crea un item de stat individual (clickeable) con diseño [icono] Label    Número"""
        widget = QFrame()
        widget.setObjectName(f"stat_{key}")
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setFixedHeight(36)  # Altura fija para cada item
        
        # Estilo inicial (gris neutral - no analizado)
        widget.setStyleSheet(
            "QFrame#stat_" + key + " {"
            "  background: #f8f9fa;"
            "  border: 1px solid #dee2e6;"
            "  border-radius: 6px;"
            "  padding: 6px 8px;"
            "}"
            "QFrame#stat_" + key + ":hover {"
            "  background: #e9ecef;"
            "}"
        )
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Icono (usar QToolButton con QIcon para que Qt rasterice correctamente)
        icon_btn = QToolButton()
        icon_btn.setAutoRaise(True)
        icon_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        icon_btn.setFixedSize(QSize(16, 16))
        icon_btn.setIconSize(QSize(16, 16))
        icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_btn.setStyleSheet(
            "QToolButton { background: transparent; border: none; padding: 0px; margin: 0px; }"
        )
        icon_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(icon_btn)
        
        # Label (texto descriptivo)
        text_label = QLabel()
        text_label.setStyleSheet(
            "color: #64748b; "
            "font-size: 12px; "
            "font-weight: 400; "
            "background: transparent; "
            "border: none;"
        )
        text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(text_label, 1)
        
        # Número (valor del stat)
        value_label = QLabel()
        value_label.setStyleSheet(
            "color: #64748b; "
            "font-size: 12px; "
            "font-weight: 600; "
            "background: transparent; "
            "border: none;"
        )
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(value_label)
        
        # Guardar referencias
        widget.icon_label = icon_btn
        widget.text_label = text_label
        widget.value_label = value_label
        widget.stat_key = key

        # Conectar click
        widget.mousePressEvent = lambda event: self._on_stat_clicked(key)

        return widget
    
    def _on_stat_clicked(self, key: str):
        """Navega a la pestaña correspondiente al hacer click en un stat"""
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
    
    def _create_progress_bar(self):
        """Crea la barra de progreso superpuesta (no afecta layout)"""
        # Container superpuesto sobre smart_stats
        self.progress_container = QFrame(self)
        self.progress_container.setStyleSheet(
            "QFrame {"
            "  background: rgba(255, 255, 255, 0.98);"
            "  border: none;"
            "  border-radius: 0px;"
            "}"
        )
        self.progress_container.setVisible(False)
        
        # Posicionamiento absoluto (se calculará dinámicamente)
        self.progress_container.setGeometry(0, 60, self.width(), 0)
        
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(24, 16, 24, 16)
        progress_layout.setSpacing(12)
        
        # Container interno con diseño moderno
        inner_container = QFrame()
        inner_container.setStyleSheet(
            "QFrame {"
            "  background: white;"
            "  border: 1px solid #e1e8ed;"
            "  border-radius: 12px;"
            "  padding: 20px;"
            "}"
        )
        inner_layout = QVBoxLayout(inner_container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(12)
        
        # Label de estado con diseño limpio
        self.summary_progress_label = QLabel("⏳ Preparando análisis...")
        self.summary_progress_label.setStyleSheet(
            "color: #334155;"
            "font-weight: 600;"
            "font-size: 13px;"
            "background: transparent;"
            "border: none;"
        )
        inner_layout.addWidget(self.summary_progress_label)
        
        # Barra de progreso moderna
        self.summary_progress_bar = QProgressBar()
        self.summary_progress_bar.setStyleSheet(
            "QProgressBar {"
            "  border: none;"
            "  border-radius: 8px;"
            "  text-align: center;"
            "  background-color: #f1f5f9;"
            "  height: 32px;"
            "  font-size: 12px;"
            "  font-weight: 600;"
            "  color: #475569;"
            "}"
            "QProgressBar::chunk {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "    stop:0 #3b82f6, stop:1 #60a5fa);"
            "  border-radius: 8px;"
            "}"
        )
        self.summary_progress_bar.setMaximum(100)
        self.summary_progress_bar.setValue(0)
        self.summary_progress_bar.setTextVisible(True)
        self.summary_progress_bar.setFixedHeight(32)
        inner_layout.addWidget(self.summary_progress_bar)
        
        # Detalle adicional con diseño sutil
        self.summary_progress_detail = QLabel("")
        self.summary_progress_detail.setStyleSheet(
            "color: #64748b;"
            "font-size: 11px;"
            "background: transparent;"
            "border: none;"
        )
        self.summary_progress_detail.setWordWrap(True)
        inner_layout.addWidget(self.summary_progress_detail)
        
        progress_layout.addWidget(inner_container)
        progress_layout.addStretch()
        
        # Alias para compatibilidad
        self.summary_progress_area = self.progress_container
        self.progress_frame = self.progress_container


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
        self.smart_stats_container.setVisible(True)
        
        target_height = 112  # Altura compacta: 8px top + 18px títulos + 36px + 6px + 36px + 8px bottom
        
        if animate:
            self._animation = QPropertyAnimation(self.smart_stats_container, b"maximumHeight")
            self._animation.setDuration(200)
            self._animation.setStartValue(0)
            self._animation.setEndValue(target_height)
            self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animation.start()
        else:
            self.smart_stats_container.setMaximumHeight(target_height)
        
        settings_manager.set('summary_expanded', True)
    
    def _collapse_summary(self, animate=True):
        """Colapsa Smart Stats"""
        if not self._is_summary_expanded:
            return
        
        self._is_summary_expanded = False
        self.stats_toggle_btn.setText("▼")
        
        if animate:
            self._animation = QPropertyAnimation(self.smart_stats_container, b"maximumHeight")
            self._animation.setDuration(200)
            self._animation.setStartValue(self.smart_stats_container.height())
            self._animation.setEndValue(0)
            self._animation.setEasingCurve(QEasingCurve.Type.InCubic)
            self._animation.finished.connect(lambda: self.smart_stats_container.setVisible(False))
            self._animation.start()
        else:
            self.smart_stats_container.setMaximumHeight(0)
            self.smart_stats_container.setVisible(False)
        
        settings_manager.set('summary_expanded', False)
    
    def clear_stats(self):
        """Limpia los stats y colapsa el panel (usado al cancelar o cambiar directorio)"""
        # Colapsar el panel de stats
        self._collapse_summary(animate=True)
        
        # Ocultar toggle button y metadata badge
        self.stats_toggle_btn.setVisible(False)
        self.metadata_badge.setVisible(False)
        
        # Reinicializar stats con placeholders
        self._initialize_stats_placeholders()
    
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
            self.smart_stats_container.setVisible(False)
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
            self.smart_stats_container.setVisible(False)
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
            self.smart_stats_container.setVisible(True)
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
            self.smart_stats_container.setVisible(True)
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
        """Ajusta el tamaño del progress_container cuando cambia el tamaño de la ventana"""
        super().resizeEvent(event)
        if hasattr(self, 'progress_container'):
            # Ajustar ancho del progress_container
            current_geo = self.progress_container.geometry()
            self.progress_container.setGeometry(0, current_geo.y(), self.width(), current_geo.height())

    def update_directory_display(self, directory_path):
        """Método de compatibilidad con SearchBar - actualiza el directorio"""
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
    # MÉTODOS PARA ACTUALIZAR EL RESUMEN (Compatibilidad con SummaryPanel)
    # ========================================================================
    def update_smart_stats(self, results):
        """Actualiza los Smart Stats con datos del análisis usando sistema de color amarillo/verde/gris"""
        from utils.format_utils import format_size
        
        stats = results.get('stats', {})
        ren = results.get('renaming')
        lp = results.get('live_photos', {})
        org = results.get('organization')
        heic = results.get('heic')
        dup = results.get('duplicates')
        
        # === GENERAL ===
        total_files = stats.get('total', 0)
        total_size = stats.get('total_size', 0)
        
        # Actualizar metadata badge
        self.update_metadata_badge(total_files, total_size)
        
        # === COLUMNA 1: REDUNDANCIAS ===
        
        # Live Photos
        lp_count = lp.get('live_photos_found', 0) if isinstance(lp, dict) else (lp.live_photos_found if lp else 0)
        if 'live_photos' in self.smart_stats:
            widget = self.smart_stats['live_photos']
            if lp_count > 0:
                apply_stat_state(widget, 'detected', 'live_photos')
                icon_manager.set_button_icon(widget.icon_label, 'live-photo', color='#eab308', size=16)
                widget.value_label.setText(str(lp_count))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'live_photos')
                icon_manager.set_button_icon(widget.icon_label, 'live-photo', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Live Photos detectados: {lp_count:,}")
        
        # HEIC Duplicados
        heic_count = heic.total_duplicates if heic else 0
        if 'heic' in self.smart_stats:
            widget = self.smart_stats['heic']
            if heic_count > 0:
                apply_stat_state(widget, 'detected', 'heic')
                icon_manager.set_button_icon(widget.icon_label, 'heic', color='#eab308', size=16)
                widget.value_label.setText(str(heic_count))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'heic')
                icon_manager.set_button_icon(widget.icon_label, 'heic', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Archivos HEIC con duplicado JPG: {heic_count:,}")
        
        # === COLUMNA 2: DUPLICADOS ===
        
        # Duplicados Exactos
        dup_exact = dup.total_exact_duplicates if (dup and hasattr(dup, 'total_exact_duplicates')) else 0
        if 'duplicates_exact' in self.smart_stats:
            widget = self.smart_stats['duplicates_exact']
            if dup_exact > 0:
                apply_stat_state(widget, 'detected', 'duplicates_exact')
                icon_manager.set_button_icon(widget.icon_label, 'duplicate-exact', color='#eab308', size=16)
                widget.value_label.setText(str(dup_exact))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'duplicates_exact')
                icon_manager.set_button_icon(widget.icon_label, 'duplicate-exact', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Duplicados exactos por hash: {dup_exact:,}")
        
        # Duplicados Similares (no analizado por defecto)
        if 'duplicates_similar' in self.smart_stats:
            widget = self.smart_stats['duplicates_similar']
            apply_stat_state(widget, 'not-analyzed', 'duplicates_similar')
            icon_manager.set_button_icon(widget.icon_label, 'eye', color='#64748b', size=16)
            widget.value_label.setText("—")
            widget.value_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 400;")
            widget.setToolTip("Duplicados similares (requiere análisis manual)")
        
        # === COLUMNA 3: ORGANIZACIÓN ===
        
        # Renombrar
        ren_count = ren.need_renaming if ren else 0
        if 'renaming' in self.smart_stats:
            widget = self.smart_stats['renaming']
            if ren_count > 0:
                apply_stat_state(widget, 'detected', 'renaming')
                icon_manager.set_button_icon(widget.icon_label, 'rename', color='#eab308', size=16)
                widget.value_label.setText(str(ren_count))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'renaming')
                icon_manager.set_button_icon(widget.icon_label, 'rename', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Archivos que necesitan renombrado: {ren_count:,}")
        
        # Organizar
        org_count = org.total_files_to_move if org else 0
        if 'organization' in self.smart_stats:
            widget = self.smart_stats['organization']
            if org_count > 0:
                apply_stat_state(widget, 'detected', 'organization')
                icon_manager.set_button_icon(widget.icon_label, 'organize', color='#eab308', size=16)
                widget.value_label.setText(str(org_count))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'organization')
                icon_manager.set_button_icon(widget.icon_label, 'organize', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Archivos que pueden organizarse: {org_count:,}")
        
        # Mostrar badge completado
        self.set_status_completed()
        
        # Expandir automáticamente
        self._expand_summary()
    
    
    def update_summary(self, results):
        """Actualiza el resumen - delega a update_smart_stats"""
        self.update_smart_stats(results)
        
        # Mantener compatibilidad con código antiguo
        self.stats_labels = {}  # Ya no se usa
        self.summary_action_buttons = {}  # Ya no se usa

    def set_status_not_analyzed(self):
        """Establece el badge de estado a 'No analizado' (oculto) y limpia stats"""
        self.analysis_badge.setVisible(False)
        
        # Limpiar stats y colapsar panel
        self.clear_stats()

    def set_status_analyzing(self):
        """Establece el badge de estado a 'Analizando...'"""
        self.analysis_badge.setText("⏳ Analizando")  # Unicode hourglass, no emoji
        self.analysis_badge.setStyleSheet(
            "QLabel {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #dbeafe, stop:1 #bfdbfe);"
            "  border: 1px solid #93c5fd;"
            "  border-radius: 4px;"
            "  padding: 2px 8px;"
            "  color: #1e40af;"
            "  font-size: 11px;"
            "  font-weight: 600;"
            "}"
        )
        self.analysis_badge.setVisible(True)
        # Mostrar progreso superpuesto
        self.show_progress()
    
    def set_status_canceled(self):
        """Establece el badge de estado a 'Cancelado' y limpia stats parciales"""
        self.analysis_badge.setText("⚠️ Cancelado")  # Unicode warning, no emoji
        self.analysis_badge.setStyleSheet(
            "QLabel {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff3cd, stop:1 #ffeaa7);"
            "  border: 1px solid #ffc107;"
            "  border-radius: 4px;"
            "  padding: 2px 8px;"
            "  color: #856404;"
            "  font-size: 11px;"
            "  font-weight: 600;"
            "}"
        )
        self.analysis_badge.setVisible(True)
        
        # Limpiar stats parciales (no queremos mostrar resultados incompletos)
        self.clear_stats()
    
    def set_status_completed(self):
        """Establece el badge de estado a 'Completado'"""
        self._has_completed_analysis = True  # Marcar que se completó al menos un análisis
        self.analysis_badge.setText("✓ Analizado")  # Unicode checkmark, no emoji
        self.analysis_badge.setStyleSheet(
            "QLabel {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d4edda, stop:1 #c3e6cb);"
            "  border: 1px solid #c3e6cb;"
            "  border-radius: 4px;"
            "  padding: 2px 8px;"
            "  color: #155724;"
            "  font-size: 11px;"
            "  font-weight: 600;"
            "}"
        )
        self.analysis_badge.setVisible(True)
        self.stats_toggle_btn.setVisible(True)
        # Actualizar botón a "Cambiar" después del primer análisis exitoso
        self._update_button_visibility()


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
        """Muestra el área de progreso superpuesta"""
        # Calcular altura target (200px para cubrir smart_stats cuando está expandido)
        target_height = 200
        
        # Ajustar geometría para cubrir smart_stats
        self.progress_container.setGeometry(0, 60, self.width(), 0)
        self.progress_container.setVisible(True)
        self.progress_container.raise_()  # Traer al frente
        
        # Animar altura
        self._progress_animation = QPropertyAnimation(self.progress_container, b"geometry")
        self._progress_animation.setDuration(250)
        self._progress_animation.setStartValue(self.progress_container.geometry())
        from PyQt6.QtCore import QRect
        self._progress_animation.setEndValue(QRect(0, 60, self.width(), target_height))
        self._progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._progress_animation.start()
    
    def hide_progress(self):
        """Oculta el área de progreso superpuesta"""
        if not self.progress_container.isVisible():
            return
        
        # Animar hacia 0 altura
        self._progress_animation = QPropertyAnimation(self.progress_container, b"geometry")
        self._progress_animation.setDuration(250)
        self._progress_animation.setStartValue(self.progress_container.geometry())
        from PyQt6.QtCore import QRect
        self._progress_animation.setEndValue(QRect(0, 60, self.width(), 0))
        self._progress_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._progress_animation.finished.connect(lambda: self.progress_container.setVisible(False))
        self._progress_animation.start()
