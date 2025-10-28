"""
Controlador de duplicados (análisis + eliminación)
Extrae toda la lógica de duplicados desde main_window.py
"""
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QObject

from ui.workers import DuplicateAnalysisWorker, DuplicateDeletionWorker
from ui.dialogs import ExactDuplicatesDialog, SimilarDuplicatesDialog
from utils.format_utils import format_size, markdown_like_to_html
from utils.logger import get_logger


class DuplicatesController(QObject):
    """Controlador centralizado para operaciones de duplicados (análisis + eliminación)"""

    def __init__(self, main_window, duplicate_detector, results_controller):
        """
        Constructor del controlador de duplicados

        Args:
            main_window: Instancia de MainWindow
            duplicate_detector: Servicio DuplicateDetector
            results_controller: Controlador de presentación de resultados
        """
        super().__init__()
        self.main_window = main_window
        self.duplicate_detector = duplicate_detector
        self.results_controller = results_controller

        # Workers
        self.duplicate_worker = None
        self.deletion_worker = None

        # Logger
        self.logger = get_logger('DuplicatesController')

    # ========================================================================
    # ANÁLISIS DE DUPLICADOS
    # ========================================================================

    def analyze_duplicates(self):
        """Inicia el análisis de duplicados según el modo seleccionado"""
        if not self.main_window.current_directory:
            QMessageBox.warning(
                self.main_window,
                "Directorio no seleccionado",
                "Por favor selecciona un directorio primero."
            )
            return

        # Determinar modo
        is_exact_mode = self.main_window.exact_mode_radio.isChecked()
        mode = 'exact' if is_exact_mode else 'perceptual'
        sensitivity = self.main_window.sensitivity_slider.value()

        self.logger.info(f"Iniciando análisis de duplicados: modo={mode}, sensitivity={sensitivity}")

        # Deshabilitar controles durante análisis
        self._set_analysis_controls_enabled(False)

        # Actualizar UI
        mode_text = "exactos" if is_exact_mode else "similares"
        self.main_window.duplicates_details.setHtml(markdown_like_to_html(
            f"🔄 Analizando duplicados {mode_text}...\n"
            f"Por favor espera, esto puede tardar varios minutos."
        ))

        # Crear y ejecutar worker
        self.duplicate_worker = DuplicateAnalysisWorker(
            self.duplicate_detector,
            self.main_window.current_directory,
            mode=mode,
            sensitivity=sensitivity
        )

        self.duplicate_worker.progress_update.connect(self._update_duplicate_progress)
        self.duplicate_worker.finished.connect(self._on_duplicate_analysis_finished)
        self.duplicate_worker.error.connect(self._on_duplicate_analysis_error)

        self.duplicate_worker.start()

    def cancel_duplicate_analysis(self):
        """Cancela el análisis de duplicados en curso"""
        if self.duplicate_worker and self.duplicate_worker.isRunning():
            self.logger.info("Cancelando análisis de duplicados...")
            self.duplicate_worker.stop()
            self.duplicate_worker.wait(2000)  # Esperar hasta 2 segundos
            
            self.main_window.duplicates_details.setHtml(markdown_like_to_html(
                "⏹ **Análisis cancelado**\n\nEl análisis fue detenido por el usuario."
            ))
            
            self._set_analysis_controls_enabled(True)

    def _set_analysis_controls_enabled(self, enabled: bool):
        """Habilita/deshabilita controles durante el análisis"""
        # Botones de análisis en la pestaña de duplicados
        self.main_window.analyze_duplicates_btn.setVisible(enabled)
        self.main_window.cancel_duplicates_btn.setVisible(not enabled)
        
        # Controles de modo y sensibilidad en la pestaña de duplicados
        self.main_window.exact_mode_radio.setEnabled(enabled)
        self.main_window.similar_mode_radio.setEnabled(enabled)
        self.main_window.sensitivity_slider.setEnabled(enabled)
        
        # Deshabilitar cambio de pestañas (pero no el contenido)
        # Esto evita que el usuario cambie de pestaña durante el análisis
        for i in range(self.main_window.tabs_widget.count()):
            if i != self.main_window.tabs_widget.currentIndex() or enabled:
                self.main_window.tabs_widget.setTabEnabled(i, enabled)
        
        # Deshabilitar barra de búsqueda y botones de acción
        self.main_window.directory_edit.setEnabled(enabled)
        self.main_window.analyze_btn.setEnabled(enabled)
        self.main_window.reanalyze_btn.setEnabled(enabled)
        self.main_window.change_dir_btn.setEnabled(enabled)
        
        # Ocultar botones de acción si se está iniciando análisis
        if not enabled:
            self.main_window.delete_exact_duplicates_btn.setVisible(False)
            self.main_window.review_similar_btn.setVisible(False)

    def _update_duplicate_progress(self, current, total, message):
        """Actualiza el progreso del análisis de duplicados"""
        if total > 0:
            progress_text = f"🔄 {message} ({current}/{total})"
        else:
            progress_text = f"🔄 {message}"
        self.main_window.duplicates_details.setHtml(markdown_like_to_html(progress_text))

    def _on_duplicate_analysis_finished(self, results):
        """Maneja la finalización del análisis de duplicados"""
        self.logger.info(f"Análisis completado: {results.get('mode')}")

        # Guardar resultados en el servicio DuplicateDetector para centralizar estado
        self.duplicate_detector.set_last_results(results)
        
        # Rehabilitar controles
        self._set_analysis_controls_enabled(True)

        if results.get('error'):
            QMessageBox.critical(
                self.main_window,
                "Error en Análisis",
                f"Error: {results['error']}\n\n"
                "Asegúrate de tener instalados imagehash y opencv-python para detección perceptual."
            )
            self.main_window.duplicates_details.setHtml(markdown_like_to_html(f"❌ Error: {results['error']}"))
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
            self.main_window,
            "Error en Análisis",
            f"Ocurrió un error durante el análisis:\n\n{error_msg}"
        )

        self.main_window.duplicates_details.setHtml(markdown_like_to_html("❌ Error en el análisis. Revisa el log para más detalles."))

        # Rehabilitar controles
        self._set_analysis_controls_enabled(True)

    # ========================================================================
    # ELIMINACIÓN DE DUPLICADOS
    # ========================================================================

    def delete_exact_duplicates(self):
        """Muestra diálogo para eliminar duplicados exactos"""
        # Leer resultados desde el servicio DuplicateDetector
        if not self.duplicate_detector.get_last_results():
            return

        dialog = ExactDuplicatesDialog(self.duplicate_detector.get_last_results(), self.main_window)

        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.accepted_plan:
            self._execute_duplicate_deletion(dialog.accepted_plan)

    def review_similar_duplicates(self):
        """Muestra diálogo para revisar duplicados similares"""
        if not self.duplicate_detector.get_last_results():
            return

        dialog = SimilarDuplicatesDialog(self.duplicate_detector.get_last_results(), self.main_window)

        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.accepted_plan:
            self._execute_duplicate_deletion(dialog.accepted_plan)

    def _execute_duplicate_deletion(self, plan):
        """Ejecuta la eliminación de duplicados"""
        groups = plan['groups']
        keep_strategy = plan['keep_strategy']
        create_backup = plan['create_backup']

        # Confirmación final
        reply = QMessageBox.question(
            self.main_window,
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar los archivos seleccionados?\n\n"
            f"Se eliminarán archivos de {len(groups)} grupos.\n"
            f"{'Se creará un backup de seguridad.' if create_backup else 'NO se creará backup.'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.logger.info(f"Ejecutando eliminación de duplicados: {len(groups)} grupos")

        # Deshabilitar botones
        self.main_window.delete_exact_duplicates_btn.setEnabled(False)
        self.main_window.review_similar_btn.setEnabled(False)
        self.main_window.analyze_duplicates_btn.setEnabled(False)

        self.main_window.duplicates_details.setHtml(markdown_like_to_html("🗑️ Eliminando archivos...\nPor favor espera."))

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
        self.main_window.duplicates_details.setHtml(markdown_like_to_html(f"🗑️ {message}"))

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

        QMessageBox.information(self.main_window, "Eliminación Completada", msg)

        # Actualizar UI
        self.main_window.duplicates_details.setHtml(markdown_like_to_html(
            f"✅ **Eliminación completada exitosamente**\n\n"
            f"• {files_deleted} archivos eliminados\n"
            f"• {size_str} liberados\n\n"
            f"Ejecuta un nuevo análisis para verificar."
        ))

        # Limpiar resultados y restaurar botones
        self.duplicate_detector.clear_last_results()
        self.main_window.analyze_duplicates_btn.setEnabled(True)
        self.main_window.delete_exact_duplicates_btn.setVisible(False)
        self.main_window.review_similar_btn.setVisible(False)

    def _on_deletion_error(self, error_msg):
        """Maneja errores en eliminación"""
        self.logger.error(f"Error en eliminación: {error_msg}")

        QMessageBox.critical(
            self.main_window,
            "Error en Eliminación",
            f"Ocurrió un error durante la eliminación:\n\n{error_msg}"
        )

        self.main_window.analyze_duplicates_btn.setEnabled(True)
        self.main_window.delete_exact_duplicates_btn.setEnabled(True)
        self.main_window.review_similar_btn.setEnabled(True)

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup(self):
        """Limpia workers activos"""
        if self.duplicate_worker and self.duplicate_worker.isRunning():
            self.duplicate_worker.quit()
            self.duplicate_worker.wait(1000)

        if self.deletion_worker and self.deletion_worker.isRunning():
            self.deletion_worker.quit()
            self.deletion_worker.wait(1000)
