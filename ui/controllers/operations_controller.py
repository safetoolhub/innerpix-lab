"""
Controlador de operaciones de archivos (preview + ejecución)
Extrae toda la lógica de operaciones desde main_window.py
"""
from pathlib import Path

from PyQt5.QtWidgets import QMessageBox, QDialog
from PyQt5.QtCore import QObject, QTimer

from ui.workers import (
    RenamingWorker, LivePhotoCleanupWorker,
    DirectoryUnificationWorker, HEICRemovalWorker
)
from ui.dialogs import (
    RenamingPreviewDialog, LivePhotoCleanupDialog,
    DirectoryUnificationDialog, HEICDuplicateRemovalDialog
)
from ui.helpers import update_tab_details
from utils.format_utils import format_size
from utils.logger import get_logger


class OperationsController(QObject):
    """Controlador centralizado para operaciones de archivos (preview + ejecución)"""

    def __init__(self, main_window, progress_controller, analysis_controller, results_controller):
        """
        Constructor del controlador de operaciones
        
        Args:
            main_window: Instancia de MainWindow
            progress_controller: Controlador de progreso
            analysis_controller: Controlador de análisis
            results_controller: Controlador de presentación de resultados
        """
        super().__init__()
        self.main_window = main_window
        self.progress_controller = progress_controller
        self.analysis_controller = analysis_controller
        self.results_controller = results_controller
        
        # Planes de operaciones
        self.renaming_plan = None
        self.live_photo_plan = None
        self.unification_plan = None
        self.heic_plan = None
        
        # Worker de ejecución activo
        self.execution_worker = None
        
        # Logger
        self.logger = get_logger('OperationsController')

    # ========================================================================
    # PREVIEW METHODS
    # ========================================================================

    def preview_renaming(self):
        """Muestra preview de renombrado"""
        if not self.main_window.analysis_results or not self.main_window.analysis_results.get('renaming'):
            QMessageBox.warning(self.main_window, "Advertencia", "No hay análisis disponible")
            return

        dialog = RenamingPreviewDialog(self.main_window.analysis_results['renaming'], self.main_window)
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self.renaming_plan = dialog.accepted_plan
            self.execute_renaming(skip_confirmation=True)

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
            if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
                self.live_photo_plan = dialog.accepted_plan
                self.execute_live_photo_cleanup(dialog.accepted_plan)

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self.main_window, "Error", f"Error preparando limpieza LP:\n{error_msg}")
            self.logger.error(f"Error preparando limpieza LP: {error_msg}")

    def preview_unification(self):
        """Muestra preview de unificación de directorios"""
        if not self.main_window.analysis_results or not self.main_window.analysis_results.get('unification'):
            return

        unif_analysis = self.main_window.analysis_results['unification']

        if unif_analysis.get('total_files_to_move', 0) == 0:
            QMessageBox.information(self.main_window, "Unificación", "No hay archivos para mover")
            return

        dialog = DirectoryUnificationDialog(unif_analysis, self.main_window)
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self.unification_plan = dialog.accepted_plan
            self.execute_unification(dialog.accepted_plan)

    def preview_heic_removal(self):
        """Muestra preview de eliminación de duplicados HEIC"""
        if not self.main_window.analysis_results or not self.main_window.analysis_results.get('heic'):
            return

        heic_analysis = self.main_window.analysis_results['heic']

        if heic_analysis.get('total_duplicates', 0) == 0:
            QMessageBox.information(self.main_window, "HEIC", "No hay duplicados para eliminar")
            return

        dialog = HEICDuplicateRemovalDialog(heic_analysis, self.main_window)
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self.heic_plan = dialog.accepted_plan
            self.execute_heic_removal(dialog.accepted_plan)

    # ========================================================================
    # EXECUTION METHODS
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
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()

        self.progress_controller.show_progress(len(self.renaming_plan['plan']), "Renombrando archivos...")

        self.execution_worker = RenamingWorker(
            self.main_window.renamer,
            self.renaming_plan['plan'],
            self.renaming_plan['create_backup']
        )

        try:
            self.execution_worker.progress_update.connect(self.analysis_controller.update_progress)
        except Exception:
            pass

        self.execution_worker.finished.connect(self.on_renaming_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)

        self.main_window.active_workers.append(self.execution_worker)
        self.execution_worker.start()

        self.main_window.preview_rename_btn.setEnabled(False)

    def execute_live_photo_cleanup(self, plan):
        """Ejecuta la limpieza de Live Photos"""
        count = len(plan['files_to_delete'])
        space = sum(file_info['size'] for file_info in plan['files_to_delete'])
        space_formatted = format_size(space)

        reply = QMessageBox.question(
            self.main_window,
            "Confirmar",
            f"¿Eliminar {count} archivos ({space_formatted})?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()

        self.progress_controller.show_progress(count, "Limpiando Live Photos...")

        self.execution_worker = LivePhotoCleanupWorker(self.main_window.live_photo_cleaner, plan)

        try:
            self.execution_worker.progress_update.connect(self.analysis_controller.update_progress)
        except Exception:
            pass

        self.execution_worker.finished.connect(self.on_live_photo_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)

        self.main_window.active_workers.append(self.execution_worker)
        self.execution_worker.start()

        self.main_window.exec_lp_btn.setEnabled(False)

    def execute_unification(self, plan):
        """Ejecuta la unificación"""
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

        self.progress_controller.show_progress(count, "Unificando directorios...")

        self.execution_worker = DirectoryUnificationWorker(
            self.main_window.directory_unifier,
            plan['move_plan'],
            plan['create_backup']
        )

        try:
            self.execution_worker.progress_update.connect(self.analysis_controller.update_progress)
        except Exception:
            pass

        self.execution_worker.finished.connect(self.on_unification_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)

        self.main_window.active_workers.append(self.execution_worker)
        self.execution_worker.start()

        self.main_window.exec_unif_btn.setEnabled(False)

    def execute_heic_removal(self, plan):
        """Ejecuta la eliminación de duplicados HEIC"""
        count = len(plan['duplicate_pairs'])
        format_del = 'HEIC' if plan['keep_format'] == 'jpg' else 'JPG'

        reply = QMessageBox.question(
            self.main_window,
            "Confirmar",
            f"¿Eliminar {count} archivos {format_del}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()

        self.progress_controller.show_progress(count, f"Eliminando archivos {format_del}...")

        self.execution_worker = HEICRemovalWorker(
            self.main_window.heic_remover,
            plan['duplicate_pairs'],
            plan['keep_format'],
            plan['create_backup']
        )

        try:
            self.execution_worker.progress_update.connect(self.analysis_controller.update_progress)
        except Exception:
            pass

        self.execution_worker.finished.connect(self.on_heic_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)

        self.main_window.active_workers.append(self.execution_worker)
        self.execution_worker.start()

        self.main_window.exec_heic_btn.setEnabled(False)

    # ========================================================================
    # CALLBACK METHODS
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

    def on_live_photo_finished(self, results):
        """Callback al terminar limpieza de Live Photos"""
        self.progress_controller.hide_progress()

        dry_run = bool(results.get('dry_run'))
        simulated_count = results.get('simulated_files_deleted', 0)
        simulated_space = results.get('simulated_space_freed', 0)

        html = self.results_controller.format_live_photo_results(results)
        self.results_controller.show_results_html(html, show_generic_status=False)

        if dry_run:
            try:
                note = f"<p style='color: #0c5460;'><em>ℹ️ Simulación: se simularon {simulated_count} eliminaciones " \
                       f"(potencialmente {format_size(simulated_space)} liberados)</em></p>"
                try:
                    current = self.main_window.lp_details.toHtml()
                    if 'Simulación:' not in current:
                        self.main_window.lp_details.setHtml(current + "<hr>" + note)
                except Exception:
                    pass
            except Exception:
                pass

        if results.get('success'):
            try:
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
                        f"Se eliminaron {results.get('files_deleted', 0)} archivos"
                    )
            except Exception:
                pass

        self.main_window.exec_lp_btn.setEnabled(False)

        if self.execution_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.execution_worker)
        self.execution_worker = None

        self.schedule_reanalysis()

    def on_unification_finished(self, results):
        """Callback al terminar unificación"""
        self.progress_controller.hide_progress()

        html = self.results_controller.format_unification_results(results)
        self.results_controller.show_results_html(html, show_generic_status=False)

        if results.get('success'):
            QMessageBox.information(
                self.main_window,
                "Completado",
                f"Se movieron {results.get('files_moved', 0)} archivos"
            )

        self.main_window.exec_unif_btn.setEnabled(False)

        try:
            if self.main_window.current_directory and self.main_window.directory_unifier:
                updated_unif = self.main_window.directory_unifier.analyze_directory_structure(
                    self.main_window.current_directory
                )

                if not self.main_window.analysis_results:
                    self.main_window.analysis_results = {}

                self.main_window.analysis_results['unification'] = updated_unif

                self.results_controller.update_ui_after_operation(
                    self.main_window.analysis_results, 'unification'
                )

                if updated_unif.get('total_files_to_move', 0) > 0:
                    self.main_window.exec_unif_btn.setEnabled(True)
                else:
                    self.main_window.exec_unif_btn.setEnabled(False)

        except Exception as e:
            self.logger.error(f"Error re-analizando después de unificación: {e}")

        if self.execution_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.execution_worker)
        self.execution_worker = None

        self.schedule_reanalysis()

    def on_heic_finished(self, results):
        """Callback al terminar eliminación HEIC"""
        self.progress_controller.hide_progress()

        html = self.results_controller.format_heic_results(results)
        self.results_controller.show_results_html(html, show_generic_status=False)

        if results.get('success'):
            QMessageBox.information(
                self.main_window,
                "Completado",
                f"Se eliminaron {results.get('files_removed', 0)} duplicados"
            )

        self.main_window.exec_heic_btn.setEnabled(False)

        if self.execution_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.execution_worker)
        self.execution_worker = None

        self.schedule_reanalysis()

    # ========================================================================
    # AUXILIARY METHODS
    # ========================================================================

    def on_operation_error(self, error):
        """Callback genérico para errores"""
        self.progress_controller.hide_progress()
        QMessageBox.critical(self.main_window, "Error", f"Error durante la operación:\n{error}")
        self.logger.error(f"Error: {error}")

        if self.execution_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.execution_worker)
        self.execution_worker = None

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

    def _update_button_states(self, results):
        """Habilita/deshabilita botones según disponibilidad (no usado actualmente)"""
        pass
