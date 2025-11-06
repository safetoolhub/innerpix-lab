"""
Stage 2: Análisis con progreso.
Maneja la ejecución del análisis de archivos con indicadores visuales de progreso.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer, pyqtSignal

from .base_stage import BaseStage
from ui.styles.design_system import DesignSystem
from ui.widgets.progress_card import ProgressCard
from ui.widgets.analysis_phase_widget import AnalysisPhaseWidget
from ui.workers import AnalysisWorker
from services.file_renamer import FileRenamer
from services.live_photo_detector import LivePhotoDetector
from services.file_organizer import FileOrganizer
from services.heic_remover import HEICRemover
from services.duplicate_detector import DuplicateDetector


class Stage2Window(BaseStage):
    """
    Stage 2: Análisis con progreso.
    Coordina la ejecución del análisis mostrando progreso y fases.
    """

    # Señales
    analysis_completed = pyqtSignal(object)  # Emite cuando el análisis termina

    def __init__(self, main_window, selected_folder: str):
        super().__init__(main_window)

        # Parámetros del estado
        self.selected_folder = selected_folder

        # Referencias a widgets de la fase
        self.header = None
        self.progress_card = None
        self.phase_widget = None

        # Estado del análisis
        self.analysis_worker = None
        self.analysis_results = None

        # Gestión de fases
        self.phase_timers = {}  # Dict de phase_id -> QTimer
        self.current_phase = None  # Fase actualmente en ejecución

    def setup_ui(self) -> None:
        """Configura la interfaz de usuario del Stage 2."""
        self.logger.info("Configurando UI del Stage 2")

        # Crear y mostrar header
        self.header = self.create_header(
            subtitle_text="Análisis de tu carpeta",
            show_settings_button=False,
            show_about_button=False
        )
        self.main_layout.addWidget(self.header)
        self.main_layout.addSpacing(DesignSystem.SPACE_20)

        # Crear y mostrar card de progreso
        self.progress_card = ProgressCard(self.selected_folder)
        self.main_layout.addWidget(self.progress_card)
        self.fade_in_widget(self.progress_card, duration=350)

        # Crear y mostrar widget de fases con delay
        self.phase_widget = AnalysisPhaseWidget()
        self.main_layout.addWidget(self.phase_widget)
        self.main_layout.addStretch()
        QTimer.singleShot(150, lambda: self.fade_in_widget(self.phase_widget, duration=350))

        # Iniciar análisis con delay para mostrar animaciones
        QTimer.singleShot(200, self._start_analysis)

        self.logger.info("UI del Estado 2 configurada")

    def cleanup(self) -> None:
        """Limpia los recursos del Estado 2."""
        self.logger.debug("Limpiando Estado 2")

        # Detener worker si está ejecutándose
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.analysis_worker.stop()
            self.analysis_worker.wait()

        # Limpiar timers pendientes
        for timer in self.phase_timers.values():
            timer.stop()
        self.phase_timers.clear()

        # Limpiar referencias
        if self.header:
            self.header.hide()
            self.header.setParent(None)
            self.header = None

        if self.progress_card:
            self.progress_card.hide()
            self.progress_card.setParent(None)
            self.progress_card = None

        if self.phase_widget:
            self.phase_widget.hide()
            self.phase_widget.setParent(None)
            self.phase_widget = None

        self.current_phase = None

    def _start_analysis(self):
        """Inicia el análisis del directorio seleccionado"""
        # Crear instancias de servicios
        renamer = FileRenamer()
        lp_detector = LivePhotoDetector()
        organizer = FileOrganizer()
        heic_remover = HEICRemover()
        duplicate_detector = DuplicateDetector()

        # Crear worker de análisis
        self.analysis_worker = AnalysisWorker(
            directory=Path(self.selected_folder),
            renamer=renamer,
            lp_detector=lp_detector,
            unifier=organizer,
            heic_remover=heic_remover,
            duplicate_detector=duplicate_detector,
            organization_type=None  # Se usará el default
        )

        # Conectar señales del worker
        self.analysis_worker.progress_update.connect(self._on_analysis_progress)
        self.analysis_worker.phase_update.connect(self._on_analysis_phase)
        self.analysis_worker.stats_update.connect(self._on_analysis_stats)
        self.analysis_worker.partial_results.connect(self._on_partial_results)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.error.connect(self._on_analysis_error)

        # Iniciar análisis
        self.logger.info("Iniciando worker de análisis")
        self.analysis_worker.start()

    def _on_analysis_progress(self, current: int, total: int, message: str):
        """
        Callback de progreso del análisis

        Args:
            current: Archivos procesados (puede ser 0 si no aplica)
            total: Total de archivos (puede ser 0 si no aplica)
            message: Mensaje descriptivo
        """
        if not self.progress_card:
            return

        # Actualizar mensaje de estado
        self.progress_card.update_status(message)

        # Si tenemos números reales, calcular porcentaje
        if total > 0 and current >= 0:
            percentage = int((current / total) * 100)
            self.progress_card.update_progress(current, total, percentage)

    def _on_analysis_phase(self, phase: str):
        """
        Callback cuando cambia la fase del análisis

        Args:
            phase: Nombre de la fase
        """
        self.logger.info(f"Fase de análisis: {phase}")

        if not self.phase_widget:
            return

        # Mapear nombres de fase a IDs del widget
        phase_map = {
            'live_photos': 'live_photos',
            'heic': 'heic',
            'duplicates': 'duplicates',
            'similar': 'similar'
        }

        # Si hay una fase anterior en ejecución, marcarla como completada con delay
        if self.current_phase and self.current_phase != phase:
            self._schedule_phase_completion(self.current_phase)

        # Establecer la nueva fase como running
        if phase in phase_map.values():
            self.phase_widget.set_phase_status(phase, 'running')
            self.current_phase = phase

    def _schedule_phase_completion(self, phase_id: str):
        """
        Programa la marcación de una fase como completada con delay mínimo de 1 segundo

        Args:
            phase_id: ID de la fase a marcar como completada
        """
        if phase_id in self.phase_timers:
            self.phase_timers[phase_id].stop()

        timer = QTimer(self.main_window)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._on_phase_timer_timeout(phase_id))
        timer.start(1000)  # 1 segundo mínimo

        self.phase_timers[phase_id] = timer

    def _on_phase_timer_timeout(self, phase_id: str):
        """
        Callback cuando expira el timer de una fase

        Args:
            phase_id: ID de la fase que se marca como completada
        """
        if self.phase_widget:
            self.phase_widget.set_phase_status(phase_id, 'completed')

        # Limpiar el timer
        if phase_id in self.phase_timers:
            del self.phase_timers[phase_id]

    def _on_analysis_stats(self, stats):
        """
        Callback con estadísticas del análisis

        Args:
            stats: Objeto con estadísticas
        """
        if not self.progress_card:
            return

        # Formatear estadísticas
        if hasattr(stats, 'total_files'):
            total = stats.total_files
            # TODO: Agregar tamaño total si está disponible
            stats_text = f"{total:,} archivos encontrados"
            self.progress_card.update_stats(stats_text)

    def _on_partial_results(self, results):
        """
        Callback con resultados parciales de cada fase

        Args:
            results: Diccionario con resultados parciales
        """
        self.logger.debug(f"Resultados parciales: {results.keys()}")
        # TODO: Podríamos mostrar más info en el UI si es necesario

    def _on_analysis_finished(self, results):
        """
        Callback cuando el análisis termina exitosamente

        Args:
            results: Diccionario con todos los resultados
        """
        self.logger.info("Análisis completado exitosamente")
        self.analysis_results = results

        # Guardar resultados del análisis para uso futuro
        self.save_analysis_results(results)

        # Marcar progreso como completo
        if self.progress_card:
            self.progress_card.mark_completed()

        # Marcar todas las fases como completadas inmediatamente al terminar
        if self.phase_widget:
            for phase_id in ['live_photos', 'heic', 'duplicates']:
                self.phase_widget.set_phase_status(phase_id, 'completed')

        # Limpiar timers pendientes
        for timer in self.phase_timers.values():
            timer.stop()
        self.phase_timers.clear()
        self.current_phase = None

        # Emitir señal de análisis completado
        self.analysis_completed.emit(results)

        # Transición a ESTADO 3 con delay para que el usuario vea "completado"
        QTimer.singleShot(1500, lambda: self.main_window._transition_to_state_3(results))

    def _on_analysis_error(self, error_msg: str):
        """
        Callback cuando ocurre un error en el análisis

        Args:
            error_msg: Mensaje de error
        """
        self.logger.error(f"Error en análisis: {error_msg}")

        # Limpiar timers pendientes
        for timer in self.phase_timers.values():
            timer.stop()
        self.phase_timers.clear()
        self.current_phase = None

        # Marcar fase actual como error si existe
        if self.phase_widget and self.current_phase:
            self.phase_widget.set_phase_status(self.current_phase, 'error')

        # Mostrar diálogo de error con opciones
        msg = QMessageBox(self.main_window)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error en el análisis")
        msg.setText("Ocurrió un error durante el análisis de la carpeta.")
        msg.setInformativeText(f"Detalles del error:\n{error_msg}")
        msg.setDetailedText(f"Carpeta: {self.selected_folder}\n\nError: {error_msg}")

        # Botones de acción
        retry_btn = msg.addButton("Reintentar", QMessageBox.ButtonRole.ActionRole)
        change_btn = msg.addButton("Cambiar carpeta", QMessageBox.ButtonRole.ActionRole)
        close_btn = msg.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(retry_btn)

        msg.exec()

        # Manejar la respuesta del usuario
        if msg.clickedButton() == retry_btn:
            self.logger.info("Usuario eligió reintentar el análisis")
            self._restart_analysis()
        elif msg.clickedButton() == change_btn:
            self.logger.info("Usuario eligió cambiar de carpeta")
            self._return_to_state_1()
        else:
            self.logger.info("Usuario cerró el diálogo de error")

    def _restart_analysis(self):
        """Reinicia el análisis de la carpeta actual"""
        self.logger.info("Reiniciando análisis...")

        # Limpiar estado de análisis previo
        if self.progress_card:
            self.progress_card.reset()

        if self.phase_widget:
            self.phase_widget.reset_all_phases()

        # Reiniciar análisis
        self._start_analysis()

    def _return_to_state_1(self):
        """Vuelve al Estado 1 para seleccionar otra carpeta"""
        self.logger.info("Volviendo a Estado 1")

        # Limpiar datos del análisis
        self.analysis_results = None

        # Transición al Estado 1 a través de MainWindow
        self.main_window._transition_to_state_1()

        # Transición al Estado 1 (delegar al sistema de estados)
        # TODO: Implementar transición a través del sistema de estados