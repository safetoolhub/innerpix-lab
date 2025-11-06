"""
Clase base para las stages de la interfaz de usuario.
Proporciona utilidades comunes como animaciones, persistencia y navegación.
"""

from typing import Optional, Callable, Any
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QMainWindow, QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, QObject

from utils.settings_manager import settings_manager
from utils.logger import get_logger


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

    def save_analysis_results(self, results: dict) -> None:
        """
        Guarda el resumen del análisis en la configuración.

        Args:
            results: Resultados del análisis a guardar
        """
        try:
            settings_manager.set('last_analysis_summary', results)
            self.logger.debug("Resultados del análisis guardados")
        except Exception as e:
            self.logger.warning(f"Error guardando resultados del análisis: {e}")

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