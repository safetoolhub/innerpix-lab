"""
Controlador de HEIC (preview + ejecución)
Extrae la lógica de eliminación de duplicados HEIC desde operations_controller.py
"""
from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QObject, QTimer

from config import Config
from ui.workers import HEICRemovalWorker
from ui.dialogs import HEICDuplicateRemovalDialog
from utils.logger import get_logger


class HEICController(QObject):
    """Controlador especializado para operaciones de HEIC"""

    def __init__(self, main_window, heic_remover, progress_controller, results_controller):
        """
        Constructor del controlador de HEIC

        Args:
            main_window: Instancia de MainWindow
            heic_remover: Servicio HEICDuplicateRemover
            progress_controller: Controlador de progreso
            results_controller: Controlador de presentación de resultados
        """
        super().__init__()
        self.main_window = main_window
        self.heic_remover = heic_remover
        self.progress_controller = progress_controller
        self.results_controller = results_controller

        # Plan de eliminación HEIC
        self.heic_plan = None

        # Worker de ejecución
        self.execution_worker = None

        # Logger
        self.logger = get_logger('HEICController')

    # ========================================================================
    # PREVIEW
    # ========================================================================

    def preview_heic_removal(self):
        """Muestra preview de eliminación de duplicados HEIC"""
        if not self.main_window.analysis_results or not self.main_window.analysis_results.get('heic'):
            return

        heic_analysis = self.main_window.analysis_results['heic']

        if heic_analysis.total_duplicates == 0:
            QMessageBox.information(self.main_window, "HEIC", "No hay duplicados para eliminar")
            return

        dialog = HEICDuplicateRemovalDialog(heic_analysis, self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.accepted_plan:
            self.heic_plan = dialog.accepted_plan
            self.execute_heic_removal(dialog.accepted_plan)

    # ========================================================================
    # EXECUTION
    # ========================================================================

    def execute_heic_removal(self, plan):
        """Ejecuta la eliminación de duplicados HEIC"""
        count = len(plan['duplicate_pairs'])
        format_del = 'HEIC' if plan['keep_format'] == 'jpg' else 'JPG'
        dry_run = plan.get('dry_run', False)

        # Mensaje de confirmación diferente según sea simulación o no
        if dry_run:
            confirm_msg = f"¿Simular la eliminación de {count} archivos {format_del}?\n\n" \
                          "No se eliminarán archivos realmente."
        else:
            confirm_msg = f"¿Eliminar {count} archivos {format_del}?"

        reply = QMessageBox.question(
            self.main_window,
            "Confirmar",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()

        # Mensaje de progreso según sea simulación o no
        progress_msg = f"Simulando eliminación de archivos {format_del}..." if dry_run else f"Eliminando archivos {format_del}..."
        self.progress_controller.show_progress(count, progress_msg)

        self.execution_worker = HEICRemovalWorker(
            self.heic_remover,
            plan['duplicate_pairs'],
            plan['keep_format'],
            plan['create_backup'],
            dry_run
        )

        self.execution_worker.progress_update.connect(self.main_window.analysis_controller.update_progress)
        self.execution_worker.finished.connect(self.on_heic_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        worker_ref = self.execution_worker
        self.execution_worker.finished.connect(lambda: worker_ref.setParent(None) if worker_ref else None)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(lambda: worker_ref.setParent(None) if worker_ref else None)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)

        self.main_window.active_workers.append(self.execution_worker)
        self.execution_worker.start()

        self.main_window.exec_heic_btn.setEnabled(False)

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def on_heic_finished(self, results):
        """Callback al terminar eliminación HEIC
        
        Args:
            results: HeicDeletionResult (dataclass)
        """
        self.progress_controller.hide_progress()

        html = self.results_controller.format_heic_results(results)
        self.results_controller.show_results_html(html, show_generic_status=False)

        if results.success:
            # Mensaje diferente según sea simulación o no
            if results.dry_run:
                files_count = results.simulated_files_deleted
                QMessageBox.information(
                    self.main_window,
                    "Simulación Completada",
                    f"Simulación completada: {files_count} archivos se eliminarían\n\n"
                    "No se eliminó ningún archivo realmente."
                )
            else:
                QMessageBox.information(
                    self.main_window,
                    "Completado",
                    f"Se eliminaron {results.files_deleted} duplicados"
                )
            
            # Actualizar display inmediatamente antes del re-análisis (solo si no es simulación)
            if not results.dry_run:
                self._update_heic_display_after_deletion()

        # Gestionar estado del botón según si fue simulación o eliminación real
        if results.dry_run:
            # Fue simulación: re-habilitar el botón (los archivos siguen ahí)
            self.main_window.exec_heic_btn.setEnabled(True)
        else:
            # Fue eliminación real: deshabilitar el botón (los archivos ya no existen)
            self.main_window.exec_heic_btn.setEnabled(False)

        if self.execution_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.execution_worker)
        self.execution_worker = None

        # Solo re-analizar si no fue simulación
        if not results.dry_run:
            self.schedule_reanalysis()

    def _update_heic_display_after_deletion(self):
        """Actualiza el display de HEIC para indicar que ya no hay archivos pendientes"""
        # Actualizar summary panel
        if hasattr(self.main_window, 'summary_action_buttons') and 'heic' in self.main_window.summary_action_buttons:
            self.main_window.summary_action_buttons['heic'].setText("🖼️ Duplicados HEIC   0")
        
        # Actualizar detail panel con mensaje temporal
        if hasattr(self.main_window, 'heic_details'):
            temp_html = """
            <div style='padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; color: #155724;'>
                <p style='margin: 0; font-weight: 600;'>✅ Eliminación completada</p>
                <p style='margin: 5px 0 0 0;'>Re-analizando directorio...</p>
            </div>
            """
            self.main_window.heic_details.setHtml(temp_html)

    def on_operation_error(self, error):
        """Callback genérico para errores"""
        self.progress_controller.hide_progress()
        QMessageBox.critical(self.main_window, "Error", f"Error durante la operación:\n{error}")
        self.logger.error(f"Error: {error}")

        if self.execution_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.execution_worker)
        self.execution_worker = None

    # ========================================================================
    # AUXILIARY METHODS
    # ========================================================================

    def schedule_reanalysis(self, delay_ms: int = 2000):
        """Programa un re-análisis del directorio actual tras operaciones que cambian archivos"""
        if not self.main_window.current_directory:
            self.logger.debug("No hay directorio actual: se omite re-análisis programado")
            return

        def _do_reanalyze():
            # Forzar sincronización del filesystem antes del re-análisis
            import os
            try:
                os.sync()
            except (AttributeError, OSError):
                pass  # sync() no disponible en todos los sistemas
            
            self.logger.info("Iniciando re-análisis automático tras operación que modifica archivos")
            self.main_window._reanalyze_same_directory()

        QTimer.singleShot(delay_ms, _do_reanalyze)

    def cleanup(self):
        """Limpia workers activos"""
        if self.execution_worker:
            if self.execution_worker.isRunning():
                self.execution_worker.stop()
                self.execution_worker.quit()
                self.execution_worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS)
            if self.execution_worker in self.main_window.active_workers:
                self.main_window.active_workers.remove(self.execution_worker)
            self.execution_worker = None
