"""Controlador de análisis: centraliza la lógica de análisis del directorio.

Este módulo encapsula:
- Creación y gestión del ciclo de vida de AnalysisWorker
- Conexión de señales del worker
- Actualización de progreso y fases
- Manejo de resultados y errores
- Actualización de la UI tras el análisis
"""
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QMessageBox, QApplication

from config import Config
from ui.workers import AnalysisWorker


class AnalysisController:
    """Controlador independiente para operaciones de análisis.

    Provee una API clara para iniciar análisis, gestionar progreso y
    manejar resultados sin exponer detalles internos del worker.

    Métodos públicos:
    - start_analysis(directory)
    - update_progress(current, total, message)
    - update_phase(phase_text)
    - on_finished(results)
    - on_error(error)
    """

    def __init__(self, window):
        """Inicializa el controlador con referencia a la ventana principal.

        Args:
            window: MainWindow instance que contiene progress_controller,
                   tab_controller, action_buttons, summary_component, etc.
        """
        self.window = window
        self.worker: Optional[AnalysisWorker] = None

    def start_analysis(self, directory: Path) -> bool:
        """Inicia el análisis completo del directorio.

        Args:
            directory: Path del directorio a analizar

        Returns:
            True si el análisis se inició correctamente, False si hubo error
        """
        if not directory:
            QMessageBox.warning(
                self.window,
                "Advertencia",
                "Selecciona un directorio primero"
            )
            return False

        if not directory.exists():
            QMessageBox.critical(
                self.window,
                "Error",
                "El directorio no existe"
            )
            return False

        # Advertir si hay análisis previo de otro directorio
        if (self.window.last_analyzed_directory and
            self.window.last_analyzed_directory != directory):

            reply = QMessageBox.warning(
                self.window,
                "Directorio Diferente",
                f"El directorio actual es diferente al último analizado.\n\n"
                f"Último analizado: {self.window.last_analyzed_directory.name}\n"
                f"Actual: {directory.name}\n\n"
                "Se realizará un nuevo análisis y se descartará el anterior.\n\n"
                "¿Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.No:
                return False

            # Limpiar análisis previo
            self.window._reset_analysis_ui()

        # Limpiar worker anterior si existe
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

        # Mostrar panel de resumen pero ocultar pestañas hasta que termine
        self.window.summary_panel.setVisible(True)
        self.window.tabs_widget.setVisible(False)

        # Mostrar progreso (modo indeterminado)
        self.window.progress_controller.show_progress(0, "Iniciando análisis...")

        # Deshabilitar botones de ejecución
        self.window.preview_rename_btn.setEnabled(False)
        self.window.exec_lp_btn.setEnabled(False)
        self.window.exec_org_btn.setEnabled(False)
        self.window.exec_heic_btn.setEnabled(False)

        # Deshabilitar botones de la search bar durante el análisis
        self.window.analyze_btn.setEnabled(False)
        if hasattr(self.window, 'reanalyze_btn'):
            self.window.reanalyze_btn.setEnabled(False)
        if hasattr(self.window, 'change_dir_btn'):
            self.window.change_dir_btn.setEnabled(False)

        # Obtener tipo de organización seleccionado desde la UI
        organization_type = None
        if hasattr(self.window, 'org_type_button_group'):
            from services.file_organizer import OrganizationType
            selected_id = self.window.org_type_button_group.checkedId()
            if selected_id == 0:
                organization_type = OrganizationType.TO_ROOT
            elif selected_id == 1:
                organization_type = OrganizationType.BY_MONTH
            elif selected_id == 2:
                organization_type = OrganizationType.WHATSAPP_SEPARATE

        # Crear y configurar worker
        self.worker = AnalysisWorker(
            directory,
            self.window.renamer,
            self.window.live_photo_detector,
            self.window.file_organizer,
            self.window.heic_remover,
            organization_type=organization_type
        )

        # Conectar señales
        self.worker.phase_update.connect(self.update_phase)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.stats_update.connect(self.update_stats)  # Nueva conexión
        self.worker.partial_results.connect(self.update_partial_results)  # Resultados parciales
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)

        # Autoeliminación cuando termine
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)

        # Mantener referencia en la lista de workers activos
        self.window.active_workers.append(self.worker)

        # Iniciar
        self.worker.start()

        self.window.logger.info(f"Iniciando análisis de: {directory}")
        return True

    def update_progress(self, current: int, total: int, message: str):
        """Actualiza el progreso del análisis.

        Delega a progress_controller que decide el modo (determinate/indeterminate).

        Args:
            current: Progreso actual
            total: Total de elementos a procesar
            message: Mensaje descriptivo del progreso
        """
        self.window.progress_controller.update_progress(current, total, message)

    def update_phase(self, phase_text: str):
        """Actualiza la fase actual del análisis.

        Args:
            phase_text: Texto descriptivo de la fase actual
        """
        self.window.progress_controller.update_progress(0, 0, phase_text)
        QApplication.processEvents()

    def update_stats(self, stats: dict):
        """Actualiza las estadísticas del summary panel durante el análisis.

        Args:
            stats: Diccionario con estadísticas parciales (images, videos, total)
        """
        if hasattr(self.window, 'stats_labels'):
            images_txt = f"🖼️ Imágenes: {stats.get('images', 0):,}"
            videos_txt = f"🎥 Videos: {stats.get('videos', 0):,}"
            total_txt = f"📊 Total: {stats.get('total', 0):,}"
            
            if 'images' in self.window.stats_labels:
                self.window.stats_labels['images'].setText(images_txt)
            if 'videos' in self.window.stats_labels:
                self.window.stats_labels['videos'].setText(videos_txt)
            if 'total' in self.window.stats_labels:
                self.window.stats_labels['total'].setText(total_txt)

    def update_partial_results(self, partial: dict):
        """Actualiza los contadores de funcionalidades durante el análisis.

        Args:
            partial: Diccionario con resultados parciales de una funcionalidad
        """
        if not hasattr(self.window, 'summary_action_buttons'):
            return

        # Actualizar cada funcionalidad según los datos recibidos
        if 'renaming' in partial and 'renaming' in self.window.summary_action_buttons:
            ren = partial['renaming']
            count = ren.get('need_renaming', 0)
            self.window.summary_action_buttons['renaming'].setText(f"📝 Renombrado   {count:,}")

        if 'live_photos' in partial and 'live_photos' in self.window.summary_action_buttons:
            lp = partial['live_photos']
            count = lp.get('live_photos_found', 0)
            self.window.summary_action_buttons['live_photos'].setText(f"📱 Live Photos   {count:,}")

            if 'organization' in partial and 'organization' in self.window.summary_action_buttons:
                org = partial['organization']
                count = org.get('total_files_to_move', 0)
                self.window.summary_action_buttons['organization'].setText(f"📁 Organizador   {count:,}")

            if 'heic' in partial and 'heic' in self.window.summary_action_buttons:
                heic = partial['heic']
                count = heic.get('total_duplicates', 0)
                self.window.summary_action_buttons['heic'].setText(f"🖼️ Duplicados HEIC   {count:,}")

    def on_finished(self, results: dict):
        """Callback cuando termina el análisis exitosamente.

        Actualiza el estado de la ventana, notifica a los componentes y
        actualiza la UI.

        Args:
            results: Diccionario con los resultados del análisis
        """
        # Limpiar worker
        if self.worker:
            self.worker.quit()
            self.worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS)
            if self.worker in self.window.active_workers:
                self.window.active_workers.remove(self.worker)
            self.worker = None

        # Ocultar progreso
        self.window.progress_controller.hide_progress()

        # Actualizar estado de la ventana
        self.window.analysis_results = results
        self.window.last_analyzed_directory = self.window.current_directory

        # Actualizar panel de resumen
        self.window.summary_component.update(results)

        # Actualizar detalles de cada pestaña
        from ui.helpers import update_tab_details
        update_tab_details(self.window, results)

        # Actualizar disponibilidad de pestañas
        self.window.tab_controller.update_tabs_availability(results)

        # Mostrar paneles
        self.window.summary_panel.setVisible(True)
        self.window.tabs_widget.setVisible(True)

        # Rehabilitar botones de la search bar
        self.window.analyze_btn.setEnabled(True)
        if hasattr(self.window, 'reanalyze_btn'):
            self.window.reanalyze_btn.setEnabled(True)
        if hasattr(self.window, 'change_dir_btn'):
            self.window.change_dir_btn.setEnabled(True)

        # Delegar habilitación/deshabilitación de botones
        self.window.action_buttons.update_after_analysis(results)

        self.window.results_controller.show_results_html(
            """
            <div style='color: #28a745; font-weight: bold;'>
                ✅ Análisis completado con éxito
            </div>
            """,
            show_generic_status=True
        )

        self.window.logger.info(
            f"Análisis completado para: {self.window.last_analyzed_directory}"
        )

        if self.worker in self.window.active_workers:
            self.window.active_workers.remove(self.worker)
        self.worker = None

    def on_error(self, error: str):
        """Callback cuando hay error en el análisis.

        Args:
            error: Mensaje de error
        """
        # Ocultar progreso
        self.window.progress_controller.hide_progress()

        # Rehabilitar botones de la search bar
        self.window.analyze_btn.setEnabled(True)
        if hasattr(self.window, 'reanalyze_btn'):
            self.window.reanalyze_btn.setEnabled(True)
        if hasattr(self.window, 'change_dir_btn'):
            self.window.change_dir_btn.setEnabled(True)

        # Mostrar mensaje de error
        QMessageBox.critical(
            self.window,
            "Error",
            f"Error durante el análisis:\n{error}"
        )

        self.window.logger.error(f"Error en análisis: {error}")

        # Limpiar worker
        if self.worker:
            self.worker.quit()
            self.worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS)
            if self.worker in self.window.active_workers:
                self.window.active_workers.remove(self.worker)
            self.worker = None

    def cleanup(self):
        """Limpia el worker si está ejecutándose."""
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1000)
            if self.worker in self.window.active_workers:
                self.window.active_workers.remove(self.worker)
            self.worker = None
