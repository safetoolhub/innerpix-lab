"""
Controlador de duplicados (análisis + eliminación)
Extrae toda la lógica de duplicados desde main_window.py
"""
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import QObject

from config import Config
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
        
        # Autoeliminación cuando termine - capturar referencia al worker
        worker_ref = self.duplicate_worker
        self.duplicate_worker.finished.connect(lambda: worker_ref.setParent(None) if worker_ref else None)
        self.duplicate_worker.finished.connect(self.duplicate_worker.deleteLater)
        self.duplicate_worker.error.connect(lambda: worker_ref.setParent(None) if worker_ref else None)
        self.duplicate_worker.error.connect(self.duplicate_worker.deleteLater)

        # Añadir a lista de workers activos
        self.main_window.active_workers.append(self.duplicate_worker)

        self.duplicate_worker.start()

    def show_initial_results_if_available(self):
        """Muestra los resultados del análisis inicial si están disponibles.
        
        Este método se llama cuando el usuario entra a la pestaña de duplicados
        y ya hay resultados del análisis inicial de duplicados exactos.
        """
        # Verificar si hay resultados en analysis_results
        if not self.main_window.analysis_results:
            self.logger.debug("No hay analysis_results disponibles")
            return
        
        dup_results = self.main_window.analysis_results.get('duplicates')
        if not dup_results:
            self.logger.debug("No hay resultados de duplicados en analysis_results")
            return
        
        # dup_results es un DuplicateAnalysisResult (dataclass)
        # Solo mostrar si es modo exacto (del análisis inicial)
        if dup_results.mode != 'exact':
            self.logger.debug(f"Modo de duplicados es '{dup_results.mode}', no 'exact'")
            return
        
        self.logger.info(f"Mostrando resultados iniciales de duplicados exactos: {dup_results.total_groups} grupos")
        
        # Guardar en el detector para mantener consistencia
        self.duplicate_detector.set_last_results(dup_results)
        
        # Asegurar que el radio button de exactos esté seleccionado ANTES de mostrar
        # Esto es crítico porque show_exact_results verifica este estado
        self.main_window.exact_mode_radio.setChecked(True)
        
        # Procesar eventos de Qt para asegurar que el radio button se actualice
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Mostrar los resultados con el formato rico
        self.results_controller.show_exact_results(dup_results)
        
        # Habilitar el botón de análisis para permitir re-analizar
        self.main_window.analyze_duplicates_btn.setEnabled(True)
        
        self.logger.debug("Resultados iniciales de duplicados mostrados correctamente")

    def cancel_duplicate_analysis(self):
        """Cancela el análisis de duplicados en curso"""
        if self.duplicate_worker and self.duplicate_worker.isRunning():
            self.logger.info("Cancelando análisis de duplicados...")
            self.duplicate_worker.stop()
            self.duplicate_worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS)
            
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
        self.logger.info(f"Análisis completado: {results.mode}")

        # Guardar resultados en el servicio DuplicateDetector para centralizar estado
        self.duplicate_detector.set_last_results(results)
        
        # Limpiar worker
        if self.duplicate_worker:
            if self.duplicate_worker in self.main_window.active_workers:
                self.main_window.active_workers.remove(self.duplicate_worker)
            self.duplicate_worker = None
        
        # Rehabilitar controles
        self._set_analysis_controls_enabled(True)

        if results.error:
            QMessageBox.critical(
                self.main_window,
                "Error en Análisis",
                f"Error: {results.error}\n\n"
                "Asegúrate de tener instalados imagehash y opencv-python para detección perceptual."
            )
            self.main_window.duplicates_details.setHtml(markdown_like_to_html(f"❌ Error: {results.error}"))
            return

        # Mostrar resultados según el modo
        if results.mode == 'exact':
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

        # Limpiar worker
        if self.duplicate_worker:
            if self.duplicate_worker in self.main_window.active_workers:
                self.main_window.active_workers.remove(self.duplicate_worker)
            self.duplicate_worker = None

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
        dry_run = plan.get('dry_run', False)

        # Confirmación final con mensaje diferente según sea simulación
        if dry_run:
            confirm_msg = (
                f"¿Simular la eliminación de archivos seleccionados?\n\n"
                f"Se simularán eliminaciones de {len(groups)} grupos.\n\n"
                f"No se eliminarán archivos realmente."
            )
        else:
            confirm_msg = (
                f"¿Estás seguro de que deseas eliminar los archivos seleccionados?\n\n"
                f"Se eliminarán archivos de {len(groups)} grupos.\n"
                f"{'Se creará un backup de seguridad.' if create_backup else 'NO se creará backup.'}"
            )

        reply = QMessageBox.question(
            self.main_window,
            "Confirmar",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.logger.info(f"{'Simulando' if dry_run else 'Ejecutando'} eliminación de duplicados: {len(groups)} grupos")

        # Deshabilitar botones
        self.main_window.delete_exact_duplicates_btn.setEnabled(False)
        self.main_window.review_similar_btn.setEnabled(False)
        self.main_window.analyze_duplicates_btn.setEnabled(False)

        progress_msg = "🔍 Simulando eliminación..." if dry_run else "🗑️ Eliminando archivos..."
        self.main_window.duplicates_details.setHtml(markdown_like_to_html(f"{progress_msg}\nPor favor espera."))

        # Crear y ejecutar worker
        self.deletion_worker = DuplicateDeletionWorker(
            self.duplicate_detector,
            groups,
            keep_strategy,
            create_backup,
            dry_run
        )

        self.deletion_worker.progress_update.connect(self._update_deletion_progress)
        self.deletion_worker.finished.connect(self._on_deletion_finished)
        self.deletion_worker.error.connect(self._on_deletion_error)
        
        # Autoeliminación cuando termine - capturar referencia al worker
        worker_ref = self.deletion_worker
        self.deletion_worker.finished.connect(lambda: worker_ref.setParent(None) if worker_ref else None)
        self.deletion_worker.finished.connect(self.deletion_worker.deleteLater)
        self.deletion_worker.error.connect(lambda: worker_ref.setParent(None) if worker_ref else None)
        self.deletion_worker.error.connect(self.deletion_worker.deleteLater)

        # Añadir a lista de workers activos
        self.main_window.active_workers.append(self.deletion_worker)

        self.deletion_worker.start()

    def _update_deletion_progress(self, current, total, message):
        """Actualiza progreso de eliminación"""
        self.main_window.duplicates_details.setHtml(markdown_like_to_html(f"🗑️ {message}"))

    def _on_deletion_finished(self, results):
        """Maneja la finalización de eliminación de duplicados
        
        Args:
            results: DuplicateDeletionResult (dataclass)
        """
        dry_run = results.dry_run
        
        if dry_run:
            files_count = results.simulated_files_deleted
            space_freed = results.simulated_space_freed
        else:
            files_count = results.files_deleted
            space_freed = results.space_freed
        
        errors = results.errors
        backup_path = results.backup_path

        # Formatear tamaño usando helper central
        size_str = format_size(space_freed)

        if dry_run:
            self.logger.info(f"Simulación completada: {files_count} archivos se eliminarían, {size_str} se liberarían")
        else:
            self.logger.info(f"Eliminación completada: {files_count} archivos, {size_str} liberados")

        # Mostrar mensaje de éxito diferenciado
        if dry_run:
            msg = (
                f"🔍 **Simulación Completada**\n\n"
                f"• Archivos que se eliminarían: {files_count}\n"
                f"• Espacio que se liberaría: {size_str}\n\n"
                f"⚠️ No se eliminó ningún archivo realmente."
            )
            title = "Simulación Completada"
        else:
            msg = (
                f"✅ **Eliminación Completada**\n\n"
                f"• Archivos eliminados: {files_count}\n"
                f"• Espacio liberado: {size_str}\n"
            )
            title = "Eliminación Completada"
            
            if backup_path:
                msg += f"\n📦 Backup guardado en:\n{backup_path}"

        if errors:
            msg += f"\n\n⚠️ Errores: {len(errors)}"

        QMessageBox.information(self.main_window, title, msg)

        # Actualizar área de detalles con resumen
        if dry_run:
            # Mostrar resumen de simulación en el área de detalles
            summary_html = markdown_like_to_html(
                f"🔍 **Simulación Completada**\n\n"
                f"• Archivos que se eliminarían: **{files_count}**\n"
                f"• Espacio que se liberaría: **{size_str}**\n\n"
                f"⚠️ No se eliminó ningún archivo realmente.\n\n"
                f"Los archivos siguen disponibles. Puedes ejecutar la eliminación real si lo deseas."
            )
            self.main_window.duplicates_details.setHtml(summary_html)

        # Gestionar estado de botones según si fue simulación o eliminación real
        if dry_run:
            # Fue simulación: re-habilitar botones (los archivos siguen ahí)
            self.main_window.delete_exact_duplicates_btn.setEnabled(True)
            self.main_window.review_similar_btn.setEnabled(True)
            self.main_window.analyze_duplicates_btn.setEnabled(True)
        else:
            # Fue eliminación real: actualizar display y limpiar
            self._update_display_after_deletion(files_count, size_str)
            # Limpiar resultados temporalmente
            self.duplicate_detector.clear_last_results()
            self.main_window.analyze_duplicates_btn.setEnabled(False)
            self.main_window.delete_exact_duplicates_btn.setVisible(False)
            self.main_window.review_similar_btn.setVisible(False)

        # Limpiar worker
        if self.deletion_worker:
            if self.deletion_worker in self.main_window.active_workers:
                self.main_window.active_workers.remove(self.deletion_worker)
            self.deletion_worker = None

        # Limpiar el deletion_worker de la lista de workers activos (código duplicado, se mantiene por si acaso)
        if self.deletion_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.deletion_worker)
        
        self.logger.debug("Deletion worker limpiado de active_workers")

        # Programar re-análisis completo solo si no fue simulación
        if not dry_run:
            self.schedule_reanalysis()

    def _update_display_after_deletion(self, files_deleted, size_str):
        """Actualiza el display inmediatamente después de la eliminación"""
        # Actualizar summary panel
        if hasattr(self.main_window, 'summary_action_buttons') and 'duplicates' in self.main_window.summary_action_buttons:
            self.main_window.summary_action_buttons['duplicates'].setText("🔍 Duplicados   0")
        
        # Actualizar detail panel con mensaje temporal
        self.main_window.duplicates_details.setHtml(markdown_like_to_html(
            f"✅ **Eliminación completada exitosamente**\n\n"
            f"• {files_deleted} archivos eliminados\n"
            f"• {size_str} liberados\n\n"
            f"🔄 Re-analizando directorio..."
        ))

    def schedule_reanalysis(self, delay_ms: int = 500):
        """Programa un re-análisis del directorio actual tras eliminación de duplicados.
        
        Esto mantiene consistencia con otras funcionalidades (Live Photos, HEIC, etc.)
        que también hacen re-análisis completo tras modificar archivos.
        
        Args:
            delay_ms: Milisegundos de delay antes del re-análisis
        """
        from PyQt6.QtCore import QTimer
        
        if not self.main_window.current_directory:
            self.logger.debug("No hay directorio actual: se omite re-análisis programado")
            return

        def _do_reanalyze():
            self.logger.info("Iniciando re-análisis automático tras eliminación de duplicados")
            
            # Asegurar que el deletion_worker está completamente limpio
            if self.deletion_worker:
                self.logger.debug("Limpiando deletion_worker antes de re-análisis")
                if self.deletion_worker.isRunning():
                    self.deletion_worker.quit()
                    self.deletion_worker.wait(1000)
                self.deletion_worker = None
            
            # Guardar el modo actual y la pestaña antes del re-análisis
            current_tab_index = self.main_window.tabs_widget.currentIndex()
            is_exact_mode = self.main_window.exact_mode_radio.isChecked()
            
            # Almacenar en el main_window para restaurar después
            self.main_window._restore_duplicates_tab_state = {
                'tab_index': current_tab_index,
                'is_exact_mode': is_exact_mode
            }
            
            # Verificar que el directorio todavía existe antes de re-analizar
            if not self.main_window.current_directory.exists():
                self.logger.error(f"El directorio {self.main_window.current_directory} ya no existe")
                QMessageBox.warning(
                    self.main_window,
                    "Directorio no encontrado",
                    f"El directorio {self.main_window.current_directory} ya no existe."
                )
                return
            
            self.logger.debug("Ejecutando re-análisis del mismo directorio")
            self.main_window._reanalyze_same_directory()

        QTimer.singleShot(delay_ms, _do_reanalyze)

    def _on_deletion_error(self, error_msg):
        """Maneja errores en eliminación"""
        self.logger.error(f"Error en eliminación: {error_msg}")

        QMessageBox.critical(
            self.main_window,
            "Error en Eliminación",
            f"Ocurrió un error durante la eliminación:\n\n{error_msg}"
        )

        # Limpiar worker
        if self.deletion_worker:
            if self.deletion_worker in self.main_window.active_workers:
                self.main_window.active_workers.remove(self.deletion_worker)
            self.deletion_worker = None

        self.main_window.analyze_duplicates_btn.setEnabled(True)
        self.main_window.delete_exact_duplicates_btn.setEnabled(True)
        self.main_window.review_similar_btn.setEnabled(True)

    # ========================================================================
    # CLEANUP
    # ========================================================================

    def cleanup(self):
        """Limpia workers activos"""
        if self.duplicate_worker:
            if self.duplicate_worker.isRunning():
                self.duplicate_worker.stop()
                self.duplicate_worker.quit()
                self.duplicate_worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS)
            if self.duplicate_worker in self.main_window.active_workers:
                self.main_window.active_workers.remove(self.duplicate_worker)
            self.duplicate_worker = None

        if self.deletion_worker:
            if self.deletion_worker.isRunning():
                self.deletion_worker.stop()
                self.deletion_worker.quit()
                self.deletion_worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS)
            if self.deletion_worker in self.main_window.active_workers:
                self.main_window.active_workers.remove(self.deletion_worker)
            self.deletion_worker = None
