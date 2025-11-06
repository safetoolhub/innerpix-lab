"""
Ventana Principal de Pixaro Lab - Arquitectura basada en Stages
Stage 1: Selector de carpeta y bienvenida
Stage 2: Análisis con progreso
Stage 3: Grid de herramientas
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

from ui.styles.design_system import DesignSystem
from ui.stages import Stage1Window, Stage2Window, Stage3Window
from utils.logger import get_logger
from config import Config


class MainWindow(QMainWindow):
    """
    Ventana principal de Pixaro Lab
    Maneja los tres stages principales de la aplicación usando el patrón State:
    - Stage 1: Selector de carpeta y bienvenida
    - Stage 2: Análisis con progreso
    - Stage 3: Grid de herramientas
    """

    def __init__(self):
        super().__init__()
        self.logger = get_logger('PixaroLab.MainWindow')

        # Sistema de estados
        self.current_state = None

        # Layout principal (necesario para cambiar widgets)
        self.main_layout = None

        self._setup_window()
        self._setup_ui()
        self._apply_stylesheet()

        # Inicializar con Estado 1
        self._transition_to_state_1()

        self.logger.info("MainWindow inicializada en Estado 1")

    # ==================== SISTEMA DE ESTADOS ====================

    def _transition_to_state_1(self):
        """Transición al Stage 1 (Selector de carpeta)"""
        self.logger.info("Transición a Stage 1")
        self._change_state(Stage1Window)

    def _transition_to_state_2(self, selected_folder: str):
        """Transición al Stage 2 (Análisis)"""
        self.logger.info(f"Transición a Stage 2 con carpeta: {selected_folder}")
        self._change_state(Stage2Window, selected_folder)

    def _transition_to_state_3(self, analysis_results: dict):
        """Transición al Stage 3 (Herramientas)"""
        self.logger.info("Transición a Stage 3")
        selected_folder = self.current_state.selected_folder if self.current_state else None
        self._change_state(Stage3Window, selected_folder, analysis_results)

    def _change_state(self, state_class, *args, **kwargs):
        """
        Cambia al estado especificado

        Args:
            state_class: Clase del estado a crear
            *args, **kwargs: Argumentos para el constructor del estado
        """
        # Limpiar estado actual si existe
        if self.current_state:
            self.current_state.cleanup()

        # Crear nuevo estado
        self.current_state = state_class(self, *args, **kwargs)

        # Configurar UI del nuevo estado
        self.current_state.setup_ui()

    # ==================== CONFIGURACIÓN DE VENTANA ====================

    def _setup_window(self):
        """Configura las propiedades básicas de la ventana"""
        self.setWindowTitle(f"{Config.APP_NAME}")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        # Centrar ventana
        self.center_window()

    def _setup_ui(self):
        """Configura la interfaz de usuario principal"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(DesignSystem.SPACE_20)
        self.main_layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20
        )

    def _apply_stylesheet(self):
        """Aplica el stylesheet global incluyendo tooltips"""
        stylesheet = (
            DesignSystem.get_stylesheet() +
            DesignSystem.get_tooltip_style() +
            DesignSystem.get_progressbar_style()
        )
        self.setStyleSheet(stylesheet)

    def center_window(self):
        """Centra la ventana en la pantalla"""
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
