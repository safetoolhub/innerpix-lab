"""
Ventana principal de PhotoKit Manager
"""
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QFileDialog, QMessageBox, QDialog, 
    QSplitter, QApplication
)
from PyQt5.QtCore import Qt, QTimer

import config
from services.file_renamer import FileRenamer
from ui.components import Header
from ui.workers import AnalysisWorker
from ui.dialogs import SettingsDialog, AboutDialog
from services.live_photo_cleaner import LivePhotoCleaner
from services.live_photo_detector import LivePhotoDetector
from services.directory_unifier import DirectoryUnifier
from services.heic_remover import HEICDuplicateRemover
from ui.helpers import (
    update_tab_details, reset_analysis_ui,
)
from ui.validators.directory_validator import (
    confirm_directory_change,
    count_files_in_directory,
    confirm_large_directory,
)
from utils.format_utils import format_size, markdown_like_to_html
from ui.controllers.progress_controller import ProgressController

from services.duplicate_detector import DuplicateDetector
from ui.workers import DuplicateAnalysisWorker, DuplicateDeletionWorker
from ui.dialogs import ExactDuplicatesDialog, SimilarDuplicatesDialog
from ui.components import SearchBar


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    def __init__(self):
        super().__init__()

        # Variables de estado
        self.current_directory = None
        self.analysis_results = None
        self.last_analyzed_directory = None

        # Configuración de logging delegada a un manager dedicado
        # Se importa aquí para evitar dependencias circulares en el módulo
        from ui.managers.logging_manager import LoggingManager

        self.logging_manager = LoggingManager(
            default_dir=config.Config.DEFAULT_LOG_DIR,
            level=config.Config.LOG_LEVEL,
            logger_name='PhotokitManager'
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
        self.directory_unifier = DirectoryUnifier()
        self.heic_remover = HEICDuplicateRemover()
        self.duplicate_detector = DuplicateDetector()

        # Workers
        self.active_workers = []
        
        # Inicializar UI
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{config.config.APP_NAME} v{config.config.APP_VERSION}")
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
        splitter = QSplitter(Qt.Horizontal)

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

        # ===== BARRA DE PROGRESO =====
        # Instanciar el nuevo controlador de progreso
        self.progress_controller = ProgressController(self, main_layout)

        # ===== CONTROLADOR DE ANÁLISIS =====
        # Centraliza la lógica de análisis del directorio
        from ui.controllers.analysis_controller import AnalysisController
        self.analysis_controller = AnalysisController(self)

        # ===== CONTROLADOR DE RESULTADOS =====
        # Centraliza la presentación de resultados HTML
        from ui.controllers.results_controller import ResultsController
        self.results_controller = ResultsController(self)

        # ===== CONTROLADOR DE OPERACIONES =====
        # Centraliza la lógica de operaciones de archivos (preview + ejecución)
        from ui.controllers.operations_controller import OperationsController
        self.operations_controller = OperationsController(
            self, self.progress_controller, self.analysis_controller, self.results_controller
        )

        # Crear y usar el componente de botones de acción para mantener
        # la lógica encapsulada y reducir el tamaño de MainWindow.
        from ui.components.action_buttons import ActionButtons

        # ActionButtons registrará en `self` los atributos `reanalyze_btn`
        # y `change_dir_btn` para mantener compatibilidad con el código
        # existente en esta clase.
        self.action_buttons = ActionButtons(self, search_bar)

    # ========================================================================
    # WRAPPER METHODS FOR OPERATIONS CONTROLLER
    # ========================================================================
    # Estos métodos delegan al operations_controller para mantener compatibilidad
    # con las conexiones de botones existentes en las tabs
    
    def preview_renaming(self):
        """Wrapper: delega a operations_controller"""
        self.operations_controller.preview_renaming()
    
    def cleanup_live_photos(self):
        """Wrapper: delega a operations_controller"""
        self.operations_controller.preview_live_photo_cleanup()
    
    def unify_directories(self):
        """Wrapper: delega a operations_controller"""
        self.operations_controller.preview_unification()
    
    def remove_heic(self):
        """Wrapper: delega a operations_controller"""
        self.operations_controller.preview_heic_removal()

    # ========================================================================
    # CONFIGURACIÓN Y DIÁLOGOS
    # ========================================================================

    def toggle_config(self):
        """Abre el diálogo de configuración avanzada"""
        dialog = SettingsDialog(self)
        dialog.exec_()

    def show_about_dialog(self):
        """Muestra el diálogo Acerca de usando `AboutDialog`."""
        dialog = AboutDialog(self)
        dialog.exec_()

    

    # ========================================================================
    # GESTIÓN DE CIERRE Y LIMPIEZA
    # ========================================================================
    
    def closeEvent(self, event):
        """Asegurar limpieza correcta al cerrar"""
        # Limpiar el análisis controller
        self.analysis_controller.cleanup()

        # Limpiar otros workers activos
        for worker in self.active_workers:
            if worker and worker.isRunning():
                worker.quit()
                worker.wait(1000)
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
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
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
        if not confirm_large_directory(self, new_directory, file_count, config.config.LARGE_DIRECTORY_THRESHOLD):
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


    def _change_directory_after_analysis(self):
        """Permite cambiar el directorio tras un análisis, manteniendo el flujo de confirmación actual"""
        # Simular comportamiento de select_and_analyze_directory pero conservando aviso
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio",
            str(Path.home()),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
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
        if not confirm_large_directory(self, new_directory, file_count, config.config.LARGE_DIRECTORY_THRESHOLD):
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
    # MÉTODOS PARA DUPLICADOS
    # =========================================================================
    
    def on_analyze_duplicates(self):
        """Inicia el análisis de duplicados según el modo seleccionado"""
        if not self.current_directory:
            QMessageBox.warning(
                self,
                "Directorio no seleccionado",
                "Por favor selecciona un directorio primero."
            )
            return
        
        # Determinar modo
        is_exact_mode = self.exact_mode_radio.isChecked()
        mode = 'exact' if is_exact_mode else 'perceptual'
        sensitivity = self.sensitivity_slider.value()
        
        self.logger.info(f"Iniciando análisis de duplicados: modo={mode}, sensitivity={sensitivity}")
        
        # Deshabilitar botones
        self.analyze_duplicates_btn.setEnabled(False)
        self.delete_exact_duplicates_btn.setVisible(False)
        self.review_similar_btn.setVisible(False)
        
        # Actualizar UI
        mode_text = "exactos" if is_exact_mode else "similares"
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(
                f"🔄 Analizando duplicados {mode_text}...\n"
                f"Por favor espera, esto puede tardar varios minutos."
            ))
        except Exception:
            pass
        
        # Crear y ejecutar worker
        self.duplicate_worker = DuplicateAnalysisWorker(
            self.duplicate_detector,
            self.current_directory,
            mode=mode,
            sensitivity=sensitivity
        )
        
        self.duplicate_worker.progress_update.connect(self._update_duplicate_progress)
        self.duplicate_worker.finished.connect(self._on_duplicate_analysis_finished)
        self.duplicate_worker.error.connect(self._on_duplicate_analysis_error)
        
        self.duplicate_worker.start()
    
    def _update_duplicate_progress(self, current, total, message):
        """Actualiza el progreso del análisis de duplicados"""
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(f"🔄 {message}"))
        except Exception:
            pass
    
    def _on_duplicate_analysis_finished(self, results):
        """Maneja la finalización del análisis de duplicados"""
        self.logger.info(f"Análisis completado: {results.get('mode')}")
        
        # Guardar resultados en el servicio DuplicateDetector para centralizar estado
        self.duplicate_detector.set_last_results(results)
        self.analyze_duplicates_btn.setEnabled(True)
        
        if results.get('error'):
            QMessageBox.critical(
                self,
                "Error en Análisis",
                f"Error: {results['error']}\n\n"
                "Asegúrate de tener instalados imagehash y opencv-python para detección perceptual."
            )
            try:
                self.duplicates_details.setHtml(markdown_like_to_html(f"❌ Error: {results['error']}"))
            except Exception:
                pass
            return
        
        # Mostrar resultados según el modo
        if results['mode'] == 'exact':
            self.results_controller.show_exact_results(results)
        else:  # perceptual
            self.results_controller.show_similar_results(results)
    
    def _on_duplicate_analysis_error(self, error_msg):
        """Maneja errores en el análisis de duplicados"""
        self.logger.error(f"Error en análisis: {error_msg}")
        
        QMessageBox.critical(
            self,
            "Error en Análisis",
            f"Ocurrió un error durante el análisis:\n\n{error_msg}"
        )
        
        try:
            self.duplicates_details.setHtml(markdown_like_to_html("❌ Error en el análisis. Revisa el log para más detalles."))
        except Exception:
            pass
        
        self.analyze_duplicates_btn.setEnabled(True)
    
    def on_delete_exact_duplicates(self):
        """Muestra diálogo para eliminar duplicados exactos"""
        # Leer resultados desde el servicio DuplicateDetector
        if not self.duplicate_detector.get_last_results():
            return

        dialog = ExactDuplicatesDialog(self.duplicate_detector.get_last_results(), self)
        
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self._execute_duplicate_deletion(dialog.accepted_plan)
    
    def on_review_similar_duplicates(self):
        """Muestra diálogo para revisar duplicados similares"""
        if not self.duplicate_detector.get_last_results():
            return

        dialog = SimilarDuplicatesDialog(self.duplicate_detector.get_last_results(), self)
        
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self._execute_duplicate_deletion(dialog.accepted_plan)
    
    def _execute_duplicate_deletion(self, plan):
        """Ejecuta la eliminación de duplicados"""
        groups = plan['groups']
        keep_strategy = plan['keep_strategy']
        create_backup = plan['create_backup']
        
        # Confirmación final
        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar los archivos seleccionados?\n\n"
            f"Se eliminarán archivos de {len(groups)} grupos.\n"
            f"{'Se creará un backup de seguridad.' if create_backup else 'NO se creará backup.'}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.logger.info(f"Ejecutando eliminación de duplicados: {len(groups)} grupos")
        
        # Deshabilitar botones
        self.delete_exact_duplicates_btn.setEnabled(False)
        self.review_similar_btn.setEnabled(False)
        self.analyze_duplicates_btn.setEnabled(False)
        
        try:
            self.duplicates_details.setHtml(markdown_like_to_html("🗑️ Eliminando archivos...\nPor favor espera."))
        except Exception:
            pass
        
        # Crear y ejecutar worker
        self.deletion_worker = DuplicateDeletionWorker(
            self.duplicate_detector,
            groups,
            keep_strategy,
            create_backup
        )
        
        self.deletion_worker.progress_update.connect(self._update_deletion_progress)
        self.deletion_worker.finished.connect(self._on_deletion_finished)
        self.deletion_worker.error.connect(self._on_deletion_error)
        
        self.deletion_worker.start()
    
    def _update_deletion_progress(self, current, total, message):
        """Actualiza progreso de eliminación"""
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(f"🗑️ {message}"))
        except Exception:
            pass
    
    def _on_deletion_finished(self, results):
        """Maneja finalización de eliminación"""
        files_deleted = results['files_deleted']
        space_freed = results['space_freed']
        errors = results['errors']
        backup_path = results.get('backup_path')
        
        # Formatear tamaño usando helper central
        size_str = format_size(space_freed)
        
        self.logger.info(f"Eliminación completada: {files_deleted} archivos, {size_str} liberados")
        
        # Mostrar mensaje de éxito
        msg = (
            f"✅ **Eliminación Completada**\n\n"
            f"• Archivos eliminados: {files_deleted}\n"
            f"• Espacio liberado: {size_str}\n"
        )
        
        if backup_path:
            msg += f"\n📦 Backup guardado en:\n{backup_path}"
        
        if errors:
            msg += f"\n\n⚠️ Errores: {len(errors)}"
        
        QMessageBox.information(self, "Eliminación Completada", msg)
        
        # Actualizar UI
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(
                f"✅ **Eliminación completada exitosamente**\n\n"
                f"• {files_deleted} archivos eliminados\n"
                f"• {size_str} liberados\n\n"
                f"Ejecuta un nuevo análisis para verificar."
            ))
        except Exception:
            pass
        
        # Limpiar resultados y restaurar botones
        self.duplicate_detector.clear_last_results()
        self.analyze_duplicates_btn.setEnabled(True)
        self.delete_exact_duplicates_btn.setVisible(False)
        self.review_similar_btn.setVisible(False)
    
    def _on_deletion_error(self, error_msg):
        """Maneja errores en eliminación"""
        self.logger.error(f"Error en eliminación: {error_msg}")
        
        QMessageBox.critical(
            self,
            "Error en Eliminación",
            f"Ocurrió un error durante la eliminación:\n\n{error_msg}"
        )
        
        self.analyze_duplicates_btn.setEnabled(True)
        self.delete_exact_duplicates_btn.setEnabled(True)
        self.review_similar_btn.setEnabled(True)
