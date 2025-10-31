"""
Ventana principal de Pixaro Lab
"""
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QFileDialog, QMessageBox, QDialog, 
    QSplitter, QApplication
)
from PyQt6.QtCore import Qt, QTimer

from config import Config
from services.file_renamer import FileRenamer
from ui.components import Header
from ui.workers import AnalysisWorker
from ui.dialogs import SettingsDialog, AboutDialog
from services.live_photo_cleaner import LivePhotoCleaner
from services.live_photo_detector import LivePhotoDetector
from services.file_organizer import FileOrganizer
from services.heic_remover import HEICDuplicateRemover
from ui.helpers import (
    update_tab_details, reset_analysis_ui,
)
from ui.validators.directory_validator import (
    confirm_directory_change,
    count_files_in_directory,
    confirm_large_directory,
)
from utils.format_utils import format_size
from ui.controllers.progress_controller import ProgressController

from services.duplicate_detector import DuplicateDetector
from ui.components import SearchBar


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    def __init__(self):
        super().__init__()

        # Variables de estado
        self.current_directory = None
        self.analysis_results = None
        self.last_analyzed_directory = None

        # === CARGAR CONFIGURACIÓN PERSISTENTE ===
        from utils.settings_manager import settings_manager
        self.settings_manager = settings_manager

        # Cargar directorios personalizados si existen
        custom_log_dir = settings_manager.get_logs_directory()
        custom_backup_dir = settings_manager.get_backup_directory()
        log_level = settings_manager.get_log_level("INFO")

        # Actualizar config global con directorios personalizados
        if custom_log_dir:
            Config.DEFAULT_LOG_DIR = custom_log_dir
        if custom_backup_dir:
            Config.DEFAULT_BACKUP_DIR = custom_backup_dir
        Config.LOG_LEVEL = log_level

        # Configuración de logging delegada a un manager dedicado
        # Se importa aquí para evitar dependencias circulares en el módulo
        from ui.managers.logging_manager import LoggingManager

        self.logging_manager = LoggingManager(
            default_dir=Config.DEFAULT_LOG_DIR,
            level=log_level,
            logger_name='PixaroLab'
        )

        # Alinear atributos usados anteriormente por el resto de la app
        self.logger = self.logging_manager.logger
        # Alias compatible con otros módulos que esperan `app_logger`
        self.app_logger = self.logger
        self.logs_directory = self.logging_manager.logs_directory
        self.log_file = self.logging_manager.log_file

        self.logger.info("=" * 70)
        self.logger.info("Aplicación iniciada")
        self.logger.info(f"Archivo de log: {self.log_file}")
        self.logger.info("=" * 70)

        # Inicializar servicios
        self.renamer = FileRenamer()
        self.live_photo_detector = LivePhotoDetector()
        self.live_photo_cleaner = LivePhotoCleaner()
        self.file_organizer = FileOrganizer()
        self.heic_remover = HEICDuplicateRemover()
        self.duplicate_detector = DuplicateDetector()

        # Workers
        self.active_workers = []
        
        # Inicializar UI
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{Config.APP_NAME} v{Config.APP_VERSION}")
        self.setGeometry(100, 100, 1600, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ===== HEADER CON MENÚ DESPLEGABLE =====
        header = Header(self)
        main_layout.addWidget(header)

        # ===== SELECTOR ESTILO SEARCH BAR =====
        search_bar = SearchBar(self)

        # Exponer los controles usados por el resto de MainWindow
        self.directory_edit = search_bar.directory_edit
        self.analyze_btn = search_bar.analyze_btn

        main_layout.addWidget(search_bar)
        main_layout.addSpacing(10)


        # ===== SPLITTER: PANEL RESUMEN + PESTAÑAS =====
        splitter = QSplitter(Qt.Orientation.Horizontal)

    # Controlador de pestañas: centraliza creación, navegación y lógica
    # de disponibilidad de pestañas. Usa `window.tab_controller` como
    # fuente de verdad para la disponibilidad (ya no se inyecta
    # `tab_availability` directamente en `window`).
        from ui.controllers.tab_controller import TabController
        self.tab_controller = TabController(self)

        from ui.components import SummaryPanel
        # Guardar la instancia del componente para poder actualizarlo luego
        self.summary_component = SummaryPanel(self)
        # `create_summary_panel` retorna un widget; mantener compatibilidad
        self.summary_panel = self.summary_component.get_widget()
        splitter.addWidget(self.summary_panel)
        self.tabs_widget = self.tab_controller.create_tabs_widget()
        splitter.addWidget(self.tabs_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([300, 900])
        main_layout.addWidget(splitter, 1)

        # ===== CONTROLADOR DE PROGRESO =====
        # Instanciar después de crear el SummaryPanel para que los widgets estén disponibles
        self.progress_controller = ProgressController(self)

        # ===== CONTROLADOR DE ANÁLISIS =====
        # Centraliza la lógica de análisis del directorio
        from ui.controllers.analysis_controller import AnalysisController
        self.analysis_controller = AnalysisController(self)

        # ===== CONTROLADOR DE RESULTADOS =====
        # Centraliza la presentación de resultados HTML
        from ui.controllers.results_controller import ResultsController
        self.results_controller = ResultsController(self)

        # ===== CONTROLLERS ESPECIALIZADOS POR FUNCIONALIDAD =====
        # Cada funcionalidad tiene su propio controller especializado

        # Controlador de duplicados
        from ui.controllers.duplicates_controller import DuplicatesController
        self.duplicates_controller = DuplicatesController(
            self, self.duplicate_detector, self.results_controller
        )

        # Controlador de renombrado
        from ui.controllers.renaming_controller import RenamingController
        self.renaming_controller = RenamingController(
            self, self.renamer, self.progress_controller, self.results_controller
        )

        # Controlador de Live Photos
        from ui.controllers.live_photos_controller import LivePhotosController
        self.live_photos_controller = LivePhotosController(
            self, self.live_photo_cleaner, self.progress_controller, self.results_controller
        )

        # Controlador de organización de archivos
        from ui.controllers.organizer_controller import OrganizerController
        self.organizer_controller = OrganizerController(
            self, self.file_organizer, self.progress_controller, self.results_controller
        )

        # Controlador de HEIC
        from ui.controllers.heic_controller import HEICController
        self.heic_controller = HEICController(
            self, self.heic_remover, self.progress_controller, self.results_controller
        )

        # Crear y usar el componente de botones de acción para mantener
        # la lógica encapsulada y reducir el tamaño de MainWindow.
        from ui.components.action_buttons import ActionButtons

        # ActionButtons registrará en `self` los atributos `reanalyze_btn`
        # y `change_dir_btn` para mantener compatibilidad con el código
        # existente en esta clase.
        self.action_buttons = ActionButtons(self, search_bar)

    # ========================================================================
    # WRAPPER METHODS FOR SPECIALIZED CONTROLLERS
    # ========================================================================
    # Estos métodos delegan a los controllers especializados para mantener
    # compatibilidad con las conexiones de botones existentes en las tabs

    def preview_renaming(self):
        """Wrapper: delega a renaming_controller"""
        self.renaming_controller.preview_renaming()

    def cleanup_live_photos(self):
        """Wrapper: delega a live_photos_controller"""
        self.live_photos_controller.preview_live_photo_cleanup()

    def organize_files(self):
        """Wrapper: delega a organizer_controller"""
        self.organizer_controller.preview_organization()

    def remove_heic(self):
        """Wrapper: delega a heic_controller"""
        self.heic_controller.preview_heic_removal()

    def on_analyze_duplicates(self):
        """Wrapper: delega a duplicates_controller"""
        self.duplicates_controller.analyze_duplicates()

    def on_cancel_duplicate_analysis(self):
        """Wrapper: delega a duplicates_controller"""
        self.duplicates_controller.cancel_duplicate_analysis()

    def on_delete_exact_duplicates(self):
        """Wrapper: delega a duplicates_controller"""
        self.duplicates_controller.delete_exact_duplicates()

    def on_review_similar_duplicates(self):
        """Wrapper: delega a duplicates_controller"""
        self.duplicates_controller.review_similar_duplicates()

    # ========================================================================
    # CONFIGURACIÓN Y DIÁLOGOS
    # ========================================================================

    def toggle_config(self):
        """Abre el diálogo de configuración avanzada"""
        dialog = SettingsDialog(self)
        # Conectar señal para recargar configuración si se guardan cambios
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()

    def _on_settings_saved(self):
        """Callback cuando se guardan cambios en la configuración"""
        self.logger.info("Configuración actualizada, aplicando cambios...")
        
        # Recargar configuración en memoria
        custom_log_dir = self.settings_manager.get_logs_directory()
        custom_backup_dir = self.settings_manager.get_backup_directory()
        
        if custom_log_dir:
            Config.DEFAULT_LOG_DIR = custom_log_dir
        if custom_backup_dir:
            Config.DEFAULT_BACKUP_DIR = custom_backup_dir

    def show_about_dialog(self):
        """Muestra el diálogo Acerca de usando `AboutDialog`."""
        dialog = AboutDialog(self)
        dialog.exec()

    

    # ========================================================================
    # GESTIÓN DE CIERRE Y LIMPIEZA
    # ========================================================================
    
    def closeEvent(self, event):
        """Asegurar limpieza correcta al cerrar"""
        try:
            self.logger.info("Iniciando cierre de la aplicación...")
            
            # Limpiar el análisis controller
            if hasattr(self, 'analysis_controller'):
                self.analysis_controller.cleanup()

            # Limpiar controllers especializados
            if hasattr(self, 'duplicates_controller'):
                self.duplicates_controller.cleanup()
            if hasattr(self, 'renaming_controller'):
                self.renaming_controller.cleanup()
            if hasattr(self, 'live_photos_controller'):
                self.live_photos_controller.cleanup()
            if hasattr(self, 'organizer_controller'):
                self.organizer_controller.cleanup()
            if hasattr(self, 'heic_controller'):
                self.heic_controller.cleanup()

            # Limpiar otros workers activos con timeout mejorado
            if hasattr(self, 'active_workers'):
                active_count = sum(1 for w in self.active_workers if w and w.isRunning())
                if active_count > 0:
                    self.logger.info(f"Deteniendo {active_count} workers activos...")
                
                for worker in self.active_workers[:]:  # Copy to avoid modification during iteration
                    if worker and worker.isRunning():
                        worker_name = worker.__class__.__name__
                        self.logger.debug(f"Deteniendo worker: {worker_name}")
                        
                        # Solicitar stop gracefully
                        if hasattr(worker, 'stop'):
                            worker.stop()
                        
                        # Dar tiempo para terminar limpiamente (10 segundos)
                        if not worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS):
                            self.logger.warning(f"Worker {worker_name} no terminó en {Config.WORKER_SHUTDOWN_TIMEOUT_MS}ms, enviando quit()...")
                            worker.quit()
                            
                            # Dar 2 segundos más para quit()
                            if not worker.wait(2000):
                                self.logger.warning(f"Worker {worker_name} no respondió a quit(), terminando forzosamente...")
                                worker.terminate()
                                worker.wait()  # Esperar a que termine definitivamente
                        else:
                            self.logger.debug(f"Worker {worker_name} detenido correctamente")
                
                self.logger.info("Todos los workers detenidos")
            
            self.logger.info("Aplicación cerrada correctamente")
        except Exception as e:
            # Log pero no bloquear el cierre
            if hasattr(self, 'logger'):
                self.logger.error(f"Error durante cleanup: {e}")
        finally:
            event.accept()
    
    # ========================================================================
    # MÉTODOS DE CONFIGURACIÓN
    # ========================================================================

    def select_and_analyze_directory(self):
        """Selecciona directorio y analiza automáticamente con confirmación inteligente"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

        if not directory:
            return  # Usuario canceló

        new_directory = Path(directory)

        # Si hay un análisis previo en otro directorio, pedir confirmación
        if self.last_analyzed_directory and new_directory != self.last_analyzed_directory:
            if not confirm_directory_change(self, self.last_analyzed_directory, new_directory, logger=self.logger):
                return
            # Usuario confirmó, limpiar análisis previo
            self._reset_analysis_ui()
            self.logger.info(f"Directorio cambiado de {self.last_analyzed_directory} a {new_directory}")

        # Actualizar directorio actual y mostrar en UI
        self.current_directory = new_directory
        self.directory_edit.setText(f"{self.current_directory.name}")
        self.directory_edit.setToolTip(str(self.current_directory))

        # Contar archivos y manejar errores de acceso
        try:
            file_count = count_files_in_directory(new_directory)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo acceder al directorio:\n{str(e)}")
            return

        # Confirmación para directorios grandes
        if not confirm_large_directory(self, new_directory, file_count, Config.LARGE_DIRECTORY_THRESHOLD):
            self.logger.info(f"Análisis cancelado por el usuario para: {new_directory}")
            return

        # Ejecutar análisis automáticamente
        self.analyze_directory()

    def browse_logs_directory(self):
        """Cambia directorio de logs"""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Seleccionar Directorio de Logs",
            str(self.logs_directory)
        )
        if directory:
            self.logs_directory = Path(directory)
            self.logger.info(f"Directorio de logs cambiado a: {self.logs_directory}")
    
    

    # ========================================================================
    # ANÁLISIS
    # ========================================================================
    
    def analyze_directory(self):
        """Análisis completo del directorio - delega al AnalysisController"""
        if not self.current_directory:
            QMessageBox.warning(self, "Advertencia", "Selecciona un directorio primero")
            return

        self.analysis_controller.start_analysis(self.current_directory)

    def _reanalyze_same_directory(self):
        """Reinicia el análisis sobre el mismo directorio sin pedir confirmaciones"""
        # Delegar al componente la puesta en estado previo al re-análisis
        self.action_buttons.before_reanalyze()

        # Llamar al análisis directamente (analyze_directory maneja la ejecución)
        self.analyze_directory()

    def _regenerate_organization_plan(self):
        """
        Regenera solo el plan de organización sin re-analizar toda la estructura.
        OPTIMIZACIÓN: Evita re-escanear archivos cuando solo cambia el tipo de organización.
        """
        if not self.current_directory or not self.analysis_results:
            return
        
        # Solo proceder si ya existe un análisis de organización previo
        if 'organization' not in self.analysis_results:
            return
        
        from services.file_organizer import OrganizationType
        
        # Obtener el tipo de organización seleccionado
        if self.org_type_by_month.isChecked():
            org_type = OrganizationType.BY_MONTH
        elif self.org_type_whatsapp.isChecked():
            org_type = OrganizationType.WHATSAPP_SEPARATE
        else:
            org_type = OrganizationType.TO_ROOT
        
        # Verificar si el tipo ya es el mismo (evitar trabajo innecesario)
        current_org = self.analysis_results['organization']
        if current_org.organization_type == org_type.value:
            return  # Ya está en ese tipo, no hacer nada
        
        # Re-analizar solo la organización (rápido, no re-escanea archivos)
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QCursor
            from PyQt6.QtCore import Qt
            
            # Mostrar cursor de espera
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            
            # Re-generar plan de organización con el nuevo tipo
            new_org_analysis = self.file_organizer.analyze_directory_structure(
                self.current_directory,
                org_type
            )
            
            # Actualizar solo la parte de organización
            self.analysis_results['organization'] = new_org_analysis
            
            # Actualizar la UI de organización
            from utils.format_utils import format_size
            from ui.helpers import generate_stats_html
            
            # Actualizar el texto de detalles del tab de organización
            stats = {
                '📁 Subdirectorios': len(new_org_analysis.subdirectories),
                '📄 Archivos a mover': new_org_analysis.total_files_to_move,
                '💾 Tamaño total': format_size(new_org_analysis.total_size_to_move),
                '⚠️ Conflictos potenciales': new_org_analysis.potential_conflicts,
            }
            
            if new_org_analysis.folders_to_create:
                folders_list = new_org_analysis.folders_to_create
                stats['📂 Carpetas a crear'] = f"{len(folders_list)} ({', '.join(folders_list[:5])}{'...' if len(folders_list) > 5 else ''})"
            
            html = generate_stats_html(stats)
            self.org_details.setHtml(html)
            
            # Actualizar botón de acción en el resumen
            if 'organization' in self.summary_action_buttons:
                count = new_org_analysis.total_files_to_move
                self.summary_action_buttons['organization'].setText(f"📁 Organizador   {count:,}")
            
            # Actualizar botón de ejecución
            self.exec_org_btn.setEnabled(new_org_analysis.total_files_to_move > 0)
            
        except Exception as e:
            self.logger.error(f"Error al regenerar plan de organización: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _change_directory_after_analysis(self):
        """Permite cambiar el directorio tras un análisis, manteniendo el flujo de confirmación actual"""
        # Simular comportamiento de select_and_analyze_directory pero conservando aviso
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

        if not directory:
            return  # Usuario canceló

        new_directory = Path(directory)
        # Si el usuario selecciona el mismo directorio, simplemente re-analizar
        if self.last_analyzed_directory and new_directory == self.last_analyzed_directory:
            # Delegar la ocultación de alternativas y re-habilitar analyze
            self.action_buttons.hide_alternatives_and_enable_analyze()
            self.analyze_directory()
            return

        # Confirmar cambio de directorio (pérdida de análisis previo)
        if self.last_analyzed_directory:
            if not confirm_directory_change(self, self.last_analyzed_directory, new_directory, logger=self.logger):
                return

        # Comprobar acceso y contar archivos
        try:
            file_count = count_files_in_directory(new_directory)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo acceder al directorio:\n{str(e)}")
            return

        # Si es grande, pedir confirmación adicional
        if not confirm_large_directory(self, new_directory, file_count, Config.LARGE_DIRECTORY_THRESHOLD):
            self.logger.info(f"Cambio de directorio cancelado por el usuario para: {new_directory}")
            return

        # Usuario confirmó, aplicar cambio
        self.current_directory = new_directory
        self.directory_edit.setText(f"{self.current_directory.name}")
        self.directory_edit.setToolTip(str(self.current_directory))

        # Limpiar análisis previo pero NO reinsertar analyze_btn (delegar la
        # gestión de visibilidad al componente ActionButtons)
        self._reset_analysis_ui(reinsert_analyze=False)
        self.action_buttons.show_alternatives_disabled()

        # Iniciar nuevo análisis automáticamente
        self.analyze_directory()

    
    def _reset_analysis_ui(self, reinsert_analyze=True):
        """Reinicia la UI tras cambiar de directorio
        Args:
            reinsert_analyze (bool): si True (por defecto) se reinsertará el
                `analyze_btn` en el layout; si False no se tocará (útil cuando
                el flujo actual debe mantener los botones alternativos visibles).
        """
        return reset_analysis_ui(self, reinsert_analyze)


    # =========================================================================
    # MÉTODOS DE ANÁLISIS
    # =========================================================================

