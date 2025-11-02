"""
TopBar - Barra superior unificada que combina Header y SearchBar.
Componente ultra-compacto (~45px) enfocado en control y navegación.
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit, 
    QFrame, QMenu, QToolButton, QComboBox, QStyle, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QCursor

from config import Config
from ui import styles
from utils.settings_manager import settings_manager


class TopBar(QWidget):
    """Barra superior unificada con título, directorio, acciones y menú.
    
    Estados:
    - EMPTY: Sin directorio seleccionado
    - READY: Directorio seleccionado, no analizado
    - ANALYZING: Análisis en curso
    - ANALYZED: Análisis completado
    """
    
    # Señales
    select_directory_requested = pyqtSignal()  # Usuario quiere seleccionar directorio
    analyze_requested = pyqtSignal()  # Usuario quiere analizar
    reanalyze_requested = pyqtSignal()  # Usuario quiere re-analizar
    stop_analysis_requested = pyqtSignal()  # Usuario quiere detener análisis
    open_folder_requested = pyqtSignal()  # Usuario quiere abrir carpeta en explorador
    directory_changed = pyqtSignal(Path)  # Usuario seleccionó un directorio del historial
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.current_directory = None
        self.current_state = 'empty'
        
        self._init_ui()
        self._update_button_visibility()
    
    def _init_ui(self):
        """Inicializa la interfaz de usuario"""
        # Container principal con estilo
        self.container = QFrame(self)
        # Aplicar estilo del contenedor y un tooltip específico oscuro para
        # que los tooltips dentro de la TopBar usen texto claro sobre fondo
        # oscuro (coherente con los diálogos que usan este estilo).
        # Usar estilo compartido de tooltip oscuro definido en ui.styles
        try:
            tooltip_dark = styles.STYLE_TOOLTIP_DARK
        except Exception:
            tooltip_dark = ""
        self.container.setStyleSheet(styles.STYLE_SEARCH_CONTAINER + tooltip_dark)
        self.container.setMinimumHeight(52)
        
        layout = QHBoxLayout(self.container)
        layout.setSpacing(16)
        layout.setContentsMargins(18, 10, 18, 10)
        
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
        field_widget.setFixedHeight(38)
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
        field_layout.setContentsMargins(12, 0, 8, 0)
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
        
        # Layout exterior
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.container)
    
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
