"""
Ventana Principal de Innerpix Lab - Arquitectura basada en Stages
Stage 1: Selector de carpeta y bienvenida
Stage 2: Análisis con progreso
Stage 3: Grid de herramientas
"""

from pathlib import Path
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QScrollArea
from PyQt6.QtCore import Qt

from ui.styles.design_system import DesignSystem
from ui.screens.stage_1_window import Stage1Window
from utils.logger import get_logger
from config import Config


class MainWindow(QMainWindow):
    """
    Ventana principal de Innerpix Lab
    Maneja los tres stages principales de la aplicación usando el patrón State:
    - Stage 1: Selector de carpeta y bienvenida
    - Stage 2: Análisis con progreso
    - Stage 3: Grid de herramientas
    """

    def __init__(self):
        super().__init__()
        self.logger = get_logger('MainWindow')

        # Sistema de estados
        self.current_state = None

        # Layout principal (necesario para cambiar widgets)
        self.main_layout = None

        self._setup_window()
        self._setup_ui()
        self._apply_stylesheet()

        # Modo desarrollo: Intentar cargar caché y saltar directamente a Stage 3
        # Modo desarrollo: Intentar cargar caché y saltar directamente a Stage 3
        if Config.DEVELOPMENT_MODE and Config.SAVED_CACHE_DEV_MODE_PATH:
            cache_file = Path(Config.SAVED_CACHE_DEV_MODE_PATH)
            
            if cache_file.exists():
                self.logger.info(f"🔧 Modo desarrollo: Cargando caché específica {cache_file}")
                # En este caso, no conocemos el folder_path aún, lo inferiremos dentro de _load_cache_and_transition
                if self._load_cache_and_transition(None, cache_file):
                    return
            else:
                msg = f"🔧 ERROR CRÍTICO Modo desarrollo: No se encontró archivo de caché en {cache_file}"
                self.logger.error(msg)
                print(msg)
                print("Abortando ejecución debido a configuración de desarrollo inválida.")
                import sys
                sys.exit(1)

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
        # Lazy import para evitar cargar servicios hasta que se necesiten
        from ui.screens.stage_2_window import Stage2Window
        self._change_state(Stage2Window, selected_folder)

    def _transition_to_state_3(self, analysis_results: dict):
        """Transición al Stage 3 (Herramientas)"""
        self.logger.info("Transición a Stage 3")
        # Lazy import para evitar cargar diálogos hasta que se necesiten
        from ui.screens.stage_3_window import Stage3Window
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

        # Configurar UI del nuevo estado de forma asíncrona para evitar congelar la UI
        # Dar tiempo al event loop para procesar eventos pendientes
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.current_state.setup_ui)

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
        # Widget central con scroll
        central_widget = QWidget()
        central_widget.setContentsMargins(0, 0, 0, 0)  # Eliminar márgenes del central widget
        self.setCentralWidget(central_widget)

        # Layout principal del central widget
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area para contenido
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setMinimumWidth(800)  # Asegurar ancho mínimo
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea QWidget {
                background: transparent;
            }
        """)
        central_layout.addWidget(self.scroll_area)

        # Widget contenedor dentro del scroll area
        scroll_widget = QWidget()
        scroll_widget.setMinimumWidth(800)  # Asegurar ancho mínimo
        scroll_widget.setContentsMargins(0, 0, 0, 0)  # Eliminar márgenes del widget contenedor
        self.scroll_area.setWidget(scroll_widget)
        
        # Configurar viewport del scroll area para eliminar márgenes
        self.scroll_area.viewport().setContentsMargins(0, 0, 0, 0)

        # Layout principal dentro del scroll area
        self.main_layout = QVBoxLayout(scroll_widget)
        self.main_layout.setSpacing(0)  # Sin spacing para evitar espacio antes del primer elemento
        self.main_layout.setContentsMargins(
            DesignSystem.SPACE_20,  # left
            0,                      # top - sin margen superior
            DesignSystem.SPACE_20,  # right
            DesignSystem.SPACE_20   # bottom
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

    def _load_cache_and_transition(self, folder_path, cache_file):
        """
        Carga la caché desde disco y transiciona a Stage 3.
        Reconstruye la estructura de resultados esperada por Stage 3.
        
        IMPORTANTE: En modo desarrollo, también actualiza la última carpeta
        usada en settings_manager para mantener consistencia con los datos
        del caché cargado.
        """
        try:
            from services.file_metadata_repository_cache import FileInfoRepositoryCache
            from services.result_types import ScanSnapshot, DirectoryScanResult
            from utils.settings_manager import settings_manager
            
            repo = FileInfoRepositoryCache.get_instance()
            repo.clear()
            
            # Cargar caché
            loaded_count = repo.load_from_disk(cache_file, validate=True)
            self.logger.info(f"Caché cargada: {loaded_count} archivos")
            
            if loaded_count == 0:
                self.logger.warning("Caché vacía o inválida")
                return False
                
            # Reconstruir resultados del escaneo iterando el repositorio
            # Esto es necesario porque load_from_disk solo llena el repo, no devuelve estadísticas
            images = []
            videos = []
            others = []
            total_size = 0
            
            # Extensiones
            image_extensions = {}
            video_extensions = {}
            unsupported_extensions = {}
            
            all_files = repo.get_all_files()
            
            if not all_files:
                self.logger.warning("Cache loaded but empty repository")
                return False

            # Inferir directorio raíz desde los archivos (si no se proporciona)
            if folder_path is None:
                try:
                    import os
                    # Usar commonpath para encontrar la raíz común
                    common_root = os.path.commonpath([str(f.path) for f in all_files])
                    folder_path = Path(common_root)
                    self.logger.info(f"Directorio inferido desde caché: {folder_path}")
                except Exception as e:
                    self.logger.warning(f"No se pudo inferir directorio raíz: {e}")
                    # Fallback al directorio del primer archivo
                    folder_path = all_files[0].path.parent
            
            # CRÍTICO: En modo desarrollo, actualizar la última carpeta usada
            # para mantener consistencia entre los datos del caché y la carpeta
            # que el sistema considera activa. Sin esto, los servicios pueden
            # operar sobre una carpeta diferente a la de los datos cargados.
            if Config.DEVELOPMENT_MODE:
                settings_manager.set('last_analyzed_folder', str(folder_path))
                self.logger.info(f"🔧 Modo desarrollo: Carpeta activa actualizada a: {folder_path}")
            
            for metadata in all_files:
                path = metadata.path
                total_size += metadata.fs_size
                ext = metadata.extension
                
                if metadata.is_image:
                    images.append(path)
                    image_extensions[ext] = image_extensions.get(ext, 0) + 1
                elif metadata.is_video:
                    videos.append(path)
                    video_extensions[ext] = video_extensions.get(ext, 0) + 1
                else:
                    others.append(path)
                    unsupported_extensions[ext] = unsupported_extensions.get(ext, 0) + 1
            
            # Crear objetos de resultado
            scan_result = DirectoryScanResult(
                total_files=len(all_files),
                images=images,
                videos=videos,
                others=others,
                total_size=total_size,
                image_extensions=image_extensions,
                video_extensions=video_extensions,
                unsupported_extensions=unsupported_extensions,
                unsupported_files=others
            )
            
            snapshot = ScanSnapshot(
                directory=folder_path,
                scan=scan_result
            )
            
            # Configurar estado dummy para que Stage 3 funcione
            class DummyState:
                def __init__(self, folder):
                    self.selected_folder = str(folder)
                def cleanup(self): pass
            
            self.current_state = DummyState(folder_path)
            
            # Transición directa
            self.logger.info("Transicionando a Stage 3 con datos de caché")
            self._transition_to_state_3(snapshot)
            return True
            
        except Exception as e:
            self.logger.error(f"Error cargando caché en modo desarrollo: {e}", exc_info=True)
            return False
