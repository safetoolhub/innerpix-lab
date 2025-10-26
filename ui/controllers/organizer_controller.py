"""
Controlador de organización de archivos (preview + ejecución)
"""
from PyQt5.QtWidgets import QMessageBox, QDialog
from PyQt5.QtCore import QObject, QTimer

from ui.workers import FileOrganizerWorker
from ui.dialogs import FileOrganizationDialog
from utils.logger import get_logger


class OrganizerController(QObject):
    """Controlador especializado para operaciones de organización de archivos"""

    def __init__(self, main_window, file_organizer, progress_controller, results_controller):
        """
        Constructor del controlador de organización

        Args:
            main_window: Instancia de MainWindow
            file_organizer: Servicio FileOrganizer
            progress_controller: Controlador de progreso
            results_controller: Controlador de presentación de resultados
        """
        super().__init__()
        self.main_window = main_window
        self.file_organizer = file_organizer
        self.progress_controller = progress_controller
        self.results_controller = results_controller

        # Plan de organización
        self.organization_plan = None

        # Worker de ejecución
        self.execution_worker = None

        # Logger
        self.logger = get_logger('OrganizerController')

    # ========================================================================
    # PREVIEW
    # ========================================================================

    def preview_organization(self):
        """Muestra preview de organización de archivos"""
        if not self.main_window.analysis_results or not self.main_window.analysis_results.get('organization'):
            return

        org_analysis = self.main_window.analysis_results['organization']

        if org_analysis.get('total_files_to_move', 0) == 0:
            QMessageBox.information(self.main_window, "Organización", "No hay archivos para mover")
            return

        dialog = FileOrganizationDialog(org_analysis, self.main_window)
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self.organization_plan = dialog.accepted_plan
            self.execute_organization(dialog.accepted_plan)

    # ========================================================================
    # EXECUTION
    # ========================================================================

    def execute_organization(self, plan):
        """Ejecuta la organización"""
        count = len(plan['move_plan'])

        reply = QMessageBox.question(
            self.main_window,
            "Confirmar",
            f"¿Mover {count} archivos al directorio raíz?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()

        self.progress_controller.show_progress(count, "Organizando archivos...")

        self.execution_worker = FileOrganizerWorker(
            self.file_organizer,
            plan['move_plan'],
            plan['create_backup']
        )

        try:
            self.execution_worker.progress_update.connect(self.main_window.analysis_controller.update_progress)
        except Exception:
            pass

        self.execution_worker.finished.connect(self.on_organization_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)

        self.main_window.active_workers.append(self.execution_worker)
        self.execution_worker.start()

        self.main_window.exec_org_btn.setEnabled(False)

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def on_organization_finished(self, results):
        """Callback al terminar organización"""
        self.progress_controller.hide_progress()

        html = self.results_controller.format_organization_results(results)
        self.results_controller.show_results_html(html, show_generic_status=False)

        if results.get('success'):
            QMessageBox.information(
                self.main_window,
                "Completado",
                f"Se movieron {results.get('files_moved', 0)} archivos"
            )

        self.main_window.exec_org_btn.setEnabled(False)

        try:
            if self.main_window.current_directory and self.file_organizer:
                updated_org = self.file_organizer.analyze_directory_structure(
                    self.main_window.current_directory
                )

                if not self.main_window.analysis_results:
                    self.main_window.analysis_results = {}

                self.main_window.analysis_results['organization'] = updated_org

                self.results_controller.update_ui_after_operation(
                    self.main_window.analysis_results, 'organization'
                )

                if updated_org.get('total_files_to_move', 0) > 0:
                    self.main_window.exec_org_btn.setEnabled(True)
                else:
                    self.main_window.exec_org_btn.setEnabled(False)

        except Exception as e:
            self.logger.error(f"Error re-analizando después de organización: {e}")

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
            try:
                self.logger.info("Iniciando re-análisis automático tras operación que modifica archivos")
                self.main_window._reanalyze_same_directory()
            except Exception:
                self.logger.exception("Fallo durante re-análisis automático")

        QTimer.singleShot(delay_ms, _do_reanalyze)

    def cleanup(self):
        """Limpia workers activos"""
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait(1000)
