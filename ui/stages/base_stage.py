"""
Clase base para las stages de la interfaz de usuario.
Proporciona utilidades comunes como animaciones, persistencia y navegación.
"""

from typing import Optional, Callable, Any
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QMainWindow, QGraphicsOpacityEffect, QFrame, QHBoxLayout, QLabel, QToolButton
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, QObject, QSize

from utils.settings_manager import settings_manager
from utils.logger import get_logger
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from config import Config


class BaseStage(QObject):
    """
    Clase base abstracta para todas las stages de la UI.
    Define la interfaz común y proporciona utilidades compartidas.
    """

    def __init__(self, main_window: QMainWindow):
        """
        Inicializa la stage base.

        Args:
            main_window: Referencia a la ventana principal
        """
        super().__init__()
        self.main_window = main_window
        # Extraer el número del stage del nombre de la clase (Stage1Window -> 1)
        stage_num = ''.join(filter(str.isdigit, self.__class__.__name__))
        self.logger = get_logger(f'UI.Stage.{stage_num}')

        # Referencias a componentes compartidos
        self.main_layout = getattr(main_window, 'main_layout', None)

    def setup_ui(self) -> None:
        """
        Configura la interfaz de usuario para esta fase.
        Debe ser implementado por cada fase específica.
        """
        pass

    def cleanup(self) -> None:
        """
        Limpia los recursos y widgets de la fase actual.
        Debe ser implementado por cada fase específica.
        """
        pass

    def fade_out_widget(self, widget: QWidget, duration: int = 300,
                       on_finished: Optional[Callable] = None) -> None:
        """
        Aplica una animación de fade out a un widget.

        Args:
            widget: Widget a animar
            duration: Duración de la animación en ms
            on_finished: Callback opcional al terminar la animación
        """
        if not widget:
            return

        # Crear efecto de opacidad si no existe
        effect = widget.graphicsEffect()
        if not effect:
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

        # Configurar animación
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Guardar referencia para evitar GC
        widget._fade_animation = animation

        # Conectar callback si se proporciona
        if on_finished:
            animation.finished.connect(on_finished)

        animation.start()

    def fade_in_widget(self, widget: QWidget, duration: int = 300) -> None:
        """
        Aplica una animación de fade in a un widget.

        Args:
            widget: Widget a animar
            duration: Duración de la animación en ms
        """
        if not widget:
            return

        # Crear efecto de opacidad si no existe
        effect = widget.graphicsEffect()
        if not effect:
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

        # Configurar animación
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)

        # Guardar referencia para evitar GC
        widget._fade_animation = animation

        animation.start()

    def load_last_folder(self) -> Optional[str]:
        """
        Carga la última carpeta analizada desde la configuración.

        Returns:
            Ruta de la última carpeta si existe y es válida, None en caso contrario
        """
        try:
            last_folder = settings_manager.get('last_analyzed_folder')
            if last_folder and Path(last_folder).exists():
                self.logger.debug(f"Última carpeta cargada: {last_folder}")
                return last_folder
            else:
                if last_folder:
                    self.logger.debug(f"Última carpeta inválida: {last_folder}")
                return None
        except Exception as e:
            self.logger.warning(f"Error cargando última carpeta: {e}")
            return None

    def save_last_folder(self, folder_path: str) -> None:
        """
        Guarda la carpeta analizada en la configuración.

        Args:
            folder_path: Ruta de la carpeta a guardar
        """
        try:
            settings_manager.set('last_analyzed_folder', folder_path)
            self.logger.debug(f"Última carpeta guardada: {folder_path}")
        except Exception as e:
            self.logger.warning(f"Error guardando última carpeta: {e}")

    def save_analysis_results(self, results) -> None:
        """
        Guarda el resumen del análisis en la configuración.
        
        Automáticamente invalida la caché anterior si existe, ya que un nuevo
        análisis significa que puede haber cambios en los archivos.

        Args:
            results: Resultados del análisis a guardar (FullAnalysisResult o dict)
        """
        try:
            # Invalidar caché anterior antes de guardar nuevos resultados
            self._invalidate_metadata_cache()
            
            # Si es un dataclass, convertir a dict para persistencia
            from dataclasses import is_dataclass, asdict
            if is_dataclass(results):
                results_dict = asdict(results)
            else:
                results_dict = results
                
            settings_manager.set('last_analysis_summary', results_dict)
            self.logger.debug("Resultados del análisis guardados")
        except Exception as e:
            self.logger.warning(f"Error guardando resultados del análisis: {e}")
    
    def _invalidate_metadata_cache(self) -> None:
        """
        Invalida la caché de metadatos de archivos.
        
        Debe llamarse después de operaciones destructivas:
        - Eliminación de archivos (duplicados, HEIC, Live Photos)
        - Movimiento de archivos (organización)
        - Renombrado de archivos
        
        La caché se invalida automáticamente al guardar nuevos resultados
        de análisis (save_analysis_results).
        """
        try:
            # Obtener resultados actuales
            current_results = self.get_analysis_summary()
            
            # Si hay resultados y contienen caché
            if current_results and isinstance(current_results, dict):
                # Verificar si hay metadata_cache en scan
                scan_data = current_results.get('scan', {})
                if scan_data and isinstance(scan_data, dict):
                    # La caché no se serializa (es un objeto), pero logueamos la acción
                    self.logger.debug("Invalidando caché de metadatos por nuevo análisis")
            
            # La próxima vez que se ejecute el análisis, se creará una nueva caché
            self.logger.debug("Caché de metadatos marcada para regeneración")
            
        except Exception as e:
            self.logger.warning(f"Error invalidando caché de metadatos: {e}")

    def get_analysis_summary(self) -> Optional[dict]:
        """
        Obtiene el resumen del último análisis desde la configuración.

        Returns:
            Diccionario con el resumen del análisis o None si no existe
        """
        try:
            return settings_manager.get('last_analysis_summary')
        except Exception as e:
            self.logger.warning(f"Error obteniendo resumen del análisis: {e}")
            return None

    def transition_to_state(self, state_class: type, *args, **kwargs) -> None:
        """
        Transición genérica a otro estado.

        Args:
            state_class: Clase del estado al que transicionar
            *args, **kwargs: Argumentos para pasar al nuevo estado
        """
        # Limpiar estado actual
        self.cleanup()

        # Crear nuevo estado
        new_state = state_class(self.main_window, *args, **kwargs)

        # Configurar nuevo estado
        new_state.setup_ui()

        # Actualizar referencia en main_window
        self.main_window.current_state = new_state

        self.logger.info(f"Transición completada a {state_class.__name__}")

    def create_header(self, 
                           title_text: Optional[str] = None,
                           subtitle_text: Optional[str] = None,
                           show_settings_button: bool = True,
                           show_about_button: bool = True,
                           on_settings_clicked: Optional[Callable] = None, 
                           on_about_clicked: Optional[Callable] = None) -> QFrame:
        """
        Crea la card de header profesional compartida entre stages.

        Args:
            title_text: Texto opcional para el título (por defecto usa "{APP_NAME}")
            subtitle_text: Texto opcional para el subtítulo (por defecto vacío)
            show_settings_button: Si mostrar el botón de configuración
            show_about_button: Si mostrar el botón "Acerca de"
            on_settings_clicked: Callback opcional para el botón de configuración
            on_about_clicked: Callback opcional para el botón "Acerca de"

        Returns:
            QFrame: La card de header
        """
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_20}px;
            }}
        """)

        # Layout horizontal compacto
        layout = QHBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_16)
        layout.setContentsMargins(0, 0, 0, 0)

        # Logo/Icono de la aplicación
        app_icon = QLabel()
        icon_manager.set_label_icon(app_icon, 'app', color=DesignSystem.COLOR_PRIMARY, size=DesignSystem.ICON_SIZE_LG)
        layout.addWidget(app_icon)

        # Título principal
        title = title_text if title_text is not None else Config.APP_NAME
        welcome_title = QLabel(title)
        welcome_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(welcome_title)

        # Separador visual sutil
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER}; margin: 0 {DesignSystem.SPACE_8}px;")
        separator.setFixedWidth(1)
        layout.addWidget(separator)

        # Subtítulo compacto
        subtitle = subtitle_text if subtitle_text is not None else ""
        welcome_subtitle = QLabel(subtitle)
        welcome_subtitle.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
            }}
        """)
        layout.addWidget(welcome_subtitle)

        # Espaciador para empujar botones a la derecha
        layout.addStretch()

        # Botones de acción (solo si se proporcionan callbacks y están habilitados)
        if show_settings_button and on_settings_clicked:
            btn_settings = QToolButton()
            btn_settings.setAutoRaise(True)
            btn_settings.setToolTip("Configuración")
            icon_manager.set_button_icon(btn_settings, 'settings', color=DesignSystem.COLOR_TEXT_SECONDARY, size=16)
            btn_settings.setIconSize(QSize(16, 16))
            btn_settings.clicked.connect(on_settings_clicked)
            btn_settings.setStyleSheet(f"""
                QToolButton {{
                    background: transparent;
                    border: none;
                    padding: 4px;
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                }}
                QToolButton:hover {{
                    background-color: {DesignSystem.COLOR_SECONDARY};
                }}
            """)
            layout.addWidget(btn_settings)

        if show_about_button and on_about_clicked:
            btn_about = QToolButton()
            btn_about.setAutoRaise(True)
            btn_about.setToolTip("Acerca de")
            icon_manager.set_button_icon(btn_about, 'about', color=DesignSystem.COLOR_TEXT_SECONDARY, size=16)
            btn_about.setIconSize(QSize(16, 16))
            btn_about.clicked.connect(on_about_clicked)
            btn_about.setStyleSheet(f"""
                QToolButton {{
                    background: transparent;
                    border: none;
                    padding: 4px;
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                }}
                QToolButton:hover {{
                    background-color: {DesignSystem.COLOR_SECONDARY};
                }}
            """)
            layout.addWidget(btn_about)

        return card