"""
Controlador de renombrado (preview + ejecución)
Extrae la lógica de renombrado desde operations_controller.py
"""
from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QObject, QTimer

from ui.workers import RenamingWorker
from ui.dialogs import RenamingPreviewDialog
from utils.logger import get_logger


class RenamingController(QObject):
    """Controlador especializado para operaciones de renombrado"""

    def __init__(self, main_window, renamer, progress_controller, results_controller):
        """
        Constructor del controlador de renombrado

        Args:
            main_window: Instancia de MainWindow
            renamer: Servicio FileRenamer
            progress_controller: Controlador de progreso
            results_controller: Controlador de presentación de resultados
        """
        super().__init__()
        self.main_window = main_window
        self.renamer = renamer
        self.progress_controller = progress_controller
        self.results_controller = results_controller

        # Plan de renombrado
        self.renaming_plan = None

        # Worker de ejecución
        self.execution_worker = None

        # Logger
        self.logger = get_logger('RenamingController')

    # ========================================================================
    # PREVIEW
    # ========================================================================

    def preview_renaming(self):
        """Muestra preview de renombrado"""
        if not self.main_window.analysis_results or not self.main_window.analysis_results.get('renaming'):
            QMessageBox.warning(self.main_window, "Advertencia", "No hay análisis disponible")
            return

        dialog = RenamingPreviewDialog(self.main_window.analysis_results['renaming'], self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.accepted_plan:
            self.renaming_plan = dialog.accepted_plan
            self.execute_renaming(skip_confirmation=True)

    # ========================================================================
    # EXECUTION
    # ========================================================================

    def execute_renaming(self, skip_confirmation=False):
        """Ejecuta el renombrado"""
        if not self.renaming_plan:
            return

        if not skip_confirmation:
            reply = QMessageBox.question(
                self.main_window,
                "Confirmar",
                f"¿Renombrar {len(self.renaming_plan['plan'])} archivos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()

        self.progress_controller.show_progress(len(self.renaming_plan['plan']), "Renombrando archivos...")

        self.execution_worker = RenamingWorker(
            self.renamer,
            self.renaming_plan['plan'],
            self.renaming_plan['create_backup']
        )

        self.execution_worker.progress_update.connect(self.main_window.analysis_controller.update_progress)
        self.execution_worker.finished.connect(self.on_renaming_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)

        self.main_window.active_workers.append(self.execution_worker)
        self.execution_worker.start()

        self.main_window.preview_rename_btn.setEnabled(False)

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def on_renaming_finished(self, results):
        """Callback al terminar renombrado"""
        self.progress_controller.hide_progress()

        # Actualizar estadísticas si el diálogo está abierto
        for dialog in self.main_window.findChildren(RenamingPreviewDialog):
            dialog.update_statistics(results)

        html = self.results_controller.format_renaming_results(results)
        self.results_controller.show_results_html(html, show_generic_status=False)

        if results.get('success'):
            QMessageBox.information(
                self.main_window,
                "Completado",
                f"Se renombraron {results.get('files_renamed', 0)} archivos correctamente"
            )

        files_renamed = int(results.get('files_renamed', 0))
        if self.main_window.analysis_results and self.main_window.analysis_results.get('renaming'):
            ren = self.main_window.analysis_results['renaming']
            ren['already_renamed'] = ren.get('already_renamed', 0) + files_renamed
            ren['need_renaming'] = max(0, ren.get('need_renaming', 0) - files_renamed)

            errors_count = len(results.get('errors', [])) if results.get('errors') else 0
            if errors_count:
                ren['cannot_process'] = ren.get('cannot_process', 0) + errors_count

            conflicts_resolved = int(results.get('conflicts_resolved', 0)) if results.get('conflicts_resolved') is not None else 0
            if conflicts_resolved:
                ren['conflicts'] = max(0, ren.get('conflicts', 0) - conflicts_resolved)

            self.main_window.analysis_results['renaming'] = ren

            self.results_controller.update_ui_after_operation(
                self.main_window.analysis_results, 'renaming'
            )

            self.main_window.preview_rename_btn.setEnabled(ren.get('need_renaming', 0) > 0)
        else:
            self.main_window.preview_rename_btn.setEnabled(False)

        if self.execution_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.execution_worker)
        self.execution_worker = None

        self.schedule_reanalysis()

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

    def schedule_reanalysis(self, delay_ms: int = 500):
        """Programa un re-análisis del directorio actual tras operaciones que cambian archivos"""
        if not self.main_window.current_directory:
            self.logger.debug("No hay directorio actual: se omite re-análisis programado")
            return

        def _do_reanalyze():
            self.logger.info("Iniciando re-análisis automático tras operación que modifica archivos")
            self.main_window._reanalyze_same_directory()

        QTimer.singleShot(delay_ms, _do_reanalyze)

    def cleanup(self):
        """Limpia workers activos"""
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait(1000)
