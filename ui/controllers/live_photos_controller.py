"""
Controlador de Live Photos (preview + ejecución)
Extrae la lógica de Live Photos desde operations_controller.py
"""
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QObject, QTimer

from config import Config
from ui.workers import LivePhotoCleanupWorker
from ui.dialogs import LivePhotoCleanupDialog
from utils.format_utils import format_size
from utils.logger import get_logger


class LivePhotosController(QObject):
    """Controlador especializado para operaciones de Live Photos"""

    def __init__(self, main_window, live_photo_cleaner, progress_controller, results_controller):
        """
        Constructor del controlador de Live Photos

        Args:
            main_window: Instancia de MainWindow
            live_photo_cleaner: Servicio LivePhotoCleaner
            progress_controller: Controlador de progreso
            results_controller: Controlador de presentación de resultados
        """
        super().__init__()
        self.main_window = main_window
        self.live_photo_cleaner = live_photo_cleaner
        self.progress_controller = progress_controller
        self.results_controller = results_controller

        # Plan de limpieza
        self.live_photo_plan = None

        # Worker de ejecución
        self.execution_worker = None

        # Logger
        self.logger = get_logger('LivePhotosController')

    # ========================================================================
    # PREVIEW
    # ========================================================================

    def preview_live_photo_cleanup(self):
        """Muestra preview de limpieza de Live Photos"""
        if not self.main_window.analysis_results or not self.main_window.analysis_results.get('live_photos'):
            return

        lp_results = self.main_window.analysis_results['live_photos']
        lp_groups = lp_results.get('groups', [])

        if not lp_groups:
            QMessageBox.information(self.main_window, "Live Photos", "No hay Live Photos para limpiar")
            return

        try:
            cleanup_analysis = {
                'live_photos_found': len(lp_groups),
                'total_space': lp_results.get('total_space', 0),
                'space_to_free': lp_results.get('space_to_free', 0),
                'cleanup_mode': 'keep_image',
                'files_to_delete': [
                    {
                        'path': Path(group['video_path']),
                        'size': group['video_size'],
                        'type': 'video',
                        'base_name': group['base_name']
                    }
                    for group in lp_groups
                ],
                'files_to_keep': [
                    {
                        'path': Path(group['image_path']),
                        'size': group['image_size'],
                        'type': 'image',
                        'base_name': group['base_name']
                    }
                    for group in lp_groups
                ],
                'groups': lp_groups
            }

            dialog = LivePhotoCleanupDialog(cleanup_analysis, self.main_window)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.accepted_plan:
                self.live_photo_plan = dialog.accepted_plan
                self.execute_live_photo_cleanup(dialog.accepted_plan)

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self.main_window, "Error", f"Error preparando limpieza LP:\n{error_msg}")
            self.logger.error(f"Error preparando limpieza LP: {error_msg}")

    # ========================================================================
    # EXECUTION
    # ========================================================================

    def execute_live_photo_cleanup(self, plan):
        """Ejecuta la limpieza de Live Photos"""
        count = len(plan['files_to_delete'])
        space = sum(file_info['size'] for file_info in plan['files_to_delete'])
        space_formatted = format_size(space)

        reply = QMessageBox.question(
            self.main_window,
            "Confirmar",
            f"¿Eliminar {count} archivos ({space_formatted})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()

        self.progress_controller.show_progress(count, "Limpiando Live Photos...")

        self.execution_worker = LivePhotoCleanupWorker(self.live_photo_cleaner, plan)

        self.execution_worker.progress_update.connect(self.main_window.analysis_controller.update_progress)
        self.execution_worker.finished.connect(self.on_live_photo_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        worker_ref = self.execution_worker
        self.execution_worker.finished.connect(lambda: worker_ref.setParent(None) if worker_ref else None)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(lambda: worker_ref.setParent(None) if worker_ref else None)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)

        self.main_window.active_workers.append(self.execution_worker)
        self.execution_worker.start()

        self.main_window.exec_lp_btn.setEnabled(False)

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def on_live_photo_finished(self, results):
        """Callback al terminar limpieza de Live Photos
        
        Args:
            results: LivePhotoCleanupResult (dataclass)
        """
        self.progress_controller.hide_progress()

        dry_run = results.dry_run
        simulated_count = results.simulated_files_deleted
        simulated_space = results.simulated_space_freed

        html = self.results_controller.format_live_photo_results(results)
        self.results_controller.show_results_html(html, show_generic_status=False)

        if dry_run:
            note = f"<p style='color: #0c5460;'><em>ℹ️ Simulación: se simularon {simulated_count} eliminaciones " \
                   f"(potencialmente {format_size(simulated_space)} liberados)</em></p>"
            current = self.main_window.lp_details.toHtml()
            if 'Simulación:' not in current:
                self.main_window.lp_details.setHtml(current + "<hr>" + note)

        if results.success:
            if dry_run:
                QMessageBox.information(
                    self.main_window,
                    "Simulación completada",
                    f"Se simularon {simulated_count} eliminaciones (0 reales)"
                )
            else:
                QMessageBox.information(
                    self.main_window,
                    "Completado",
                    f"Se eliminaron {results.files_deleted} archivos"
                )

        self.main_window.exec_lp_btn.setEnabled(False)
        
        if self.execution_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.execution_worker)
        self.execution_worker = None

        # Actualizar inmediatamente el display para mostrar que ya no hay Live Photos
        # antes del re-análisis (para evitar confusión durante el delay)
        if not dry_run and results.success:
            self._update_lp_display_after_deletion()

        self.schedule_reanalysis()

    def _update_lp_display_after_deletion(self):
        """Actualiza el display de Live Photos para indicar que ya no hay archivos pendientes"""
        # Actualizar el summary panel
        if hasattr(self.main_window, 'summary_action_buttons') and 'live_photos' in self.main_window.summary_action_buttons:
            self.main_window.summary_action_buttons['live_photos'].setText("📱 Live Photos   0")
        
        # Actualizar el detail panel con un mensaje temporal
        if hasattr(self.main_window, 'lp_details'):
            temp_html = """
            <div style='padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; color: #155724;'>
                <p style='margin: 0; font-weight: 600;'>✅ Limpieza completada</p>
                <p style='margin: 5px 0 0 0;'>Re-analizando directorio...</p>
            </div>
            """
            self.main_window.lp_details.setHtml(temp_html)

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
        if self.execution_worker:
            if self.execution_worker.isRunning():
                self.execution_worker.stop()
                self.execution_worker.quit()
                self.execution_worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS)
            if self.execution_worker in self.main_window.active_workers:
                self.main_window.active_workers.remove(self.execution_worker)
            self.execution_worker = None
