"""
Stage 2: Análisis con progreso.
Maneja la ejecución del análisis de archivos con indicadores visuales de progreso.
"""

from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer, pyqtSignal

from .base_stage import BaseStage
from ui.styles.design_system import DesignSystem
from ui.widgets.progress_card import ProgressCard
from ui.workers import AnalysisWorker
from services.file_renamer_service import FileRenamer
from services.live_photo_service import LivePhotoService
from services.file_organizer_service import FileOrganizer
from services.heic_remover_service import HEICRemover
from services.exact_copies_detector import ExactCopiesDetector


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

        # Estado del análisis
        self.analysis_worker = None
        self.analysis_results = None

        # Gestión de fases
        self.current_phase = None  # Fase actualmente en ejecución
        
        # Estado de cancelación
        self.cancel_dialog_open = False  # Si el diálogo de cancelación está abierto
        self.analysis_completed_while_cancel_dialog_open = False  # Si terminó mientras el diálogo estaba abierto

    def setup_ui(self) -> None:
        """Configura la interfaz de usuario del Stage 2."""
        self.logger.debug("Configurando UI del Stage 2")

        # Limpiar el layout principal para evitar espacios residuales de otras stages
        if self.main_layout:
            while self.main_layout.count():
                item = self.main_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.hide()
                    widget.setParent(None)

        # Crear y mostrar header con pequeño margen superior
        self.header = self.create_header(
            subtitle_text="Análisis de tu carpeta",
            show_settings_button=False,
            show_about_button=False
        )
        self.main_layout.addSpacing(DesignSystem.SPACE_8)
        self.main_layout.addWidget(self.header)
        self.main_layout.addSpacing(DesignSystem.SPACE_16)

        # Crear y mostrar card de progreso (ahora incluye las fases)
        self.progress_card = ProgressCard(self.selected_folder)
        self.progress_card.cancel_requested.connect(self._on_cancel_requested)
        self.main_layout.addWidget(self.progress_card)

        # Añadir espacio y stretch en la parte inferior para que el margen vaya al final
        self.main_layout.addSpacing(DesignSystem.SPACE_20)
        self.main_layout.addStretch()
        self.fade_in_widget(self.progress_card, duration=350)

        # Iniciar análisis con delay para mostrar animaciones
        QTimer.singleShot(200, self._start_analysis)

        self.logger.debug("UI del Estado 2 configurada")

    def cleanup(self) -> None:
        """Limpia los recursos del Estado 2."""
        self.logger.debug("Limpiando Estado 2")

        # Detener worker si está ejecutándose
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.logger.info("Deteniendo worker durante cleanup...")
            self.analysis_worker.stop()
            
            # Esperar con timeout para evitar bloqueos indefinidos
            if not self.analysis_worker.wait(5000):  # 5 segundos de timeout
                self.logger.warning("Worker no respondió durante cleanup, terminando forzosamente")
                self.analysis_worker.terminate()
                self.analysis_worker.wait(1000)
            else:
                self.logger.info("Worker detenido correctamente durante cleanup")

        # Limpiar referencias
        if self.header:
            self.header.hide()
            self.header.setParent(None)
            self.header = None

        if self.progress_card:
            self.progress_card.hide()
            self.progress_card.setParent(None)
            self.progress_card = None

        self.current_phase = None

    def _start_analysis(self):
        """Inicia el análisis del directorio seleccionado"""
        # Marcar la fase de duplicados similares como "skipped" desde el inicio
        # ya que no se ejecutará por ser costosa en tiempo
        if self.progress_card:
            self.progress_card.set_phase_status('duplicates_similar', 'skipped')
        
        # Crear instancias de servicios
        renamer = FileRenamer()
        live_photo_service = LivePhotoService()
        organizer = FileOrganizer()
        heic_remover = HEICRemover()
        duplicate_exact_detector = ExactCopiesDetector()

        # Crear worker de análisis
        self.analysis_worker = AnalysisWorker(
            directory=Path(self.selected_folder),
            renamer=renamer,
            live_photo_service=live_photo_service,
            organizer=organizer,
            heic_remover=heic_remover,
            duplicate_exact_detector=duplicate_exact_detector,
            organization_type=None  # Se usará el default
        )

        # Conectar señales del worker
        self.analysis_worker.progress_update.connect(self._on_analysis_progress)
        self.analysis_worker.phase_update.connect(self._on_phase_started)
        self.analysis_worker.phase_completed.connect(self._on_phase_completed)
        self.analysis_worker.stats_update.connect(self._on_analysis_stats)
        self.analysis_worker.partial_results.connect(self._on_partial_results)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.error.connect(self._on_analysis_error)

        # Iniciar análisis
        self.logger.debug("Iniciando worker de análisis")
        self.analysis_worker.start()

    def _on_analysis_progress(self, current: int, total: int, message: str):
        """
        Callback de progreso del análisis
        
        Args:
            current: Archivos procesados
            total: Total de archivos
            message: Mensaje descriptivo (ignorado)
        """
        # Actualizar contador de la fase actual si hay números válidos
        if self.current_phase and self.progress_card and total > 0:
            self.progress_card.update_phase_progress(self.current_phase, current, total)

    def _on_phase_started(self, phase_id: str):
        """
        Callback cuando inicia una nueva fase del análisis.
        
        Args:
            phase_id: ID de la fase que inicia
        """
        # Log ya se hace en el worker (mismo thread del análisis, más preciso)
        if not self.progress_card:
            return

        # Establecer la fase como running
        self.progress_card.set_phase_status(phase_id, 'running')
        self.current_phase = phase_id
        
    def _on_phase_completed(self, phase_id: str):
        """
        Callback cuando una fase se completa (ya con delay mínimo aplicado).
        
        Args:
            phase_id: ID de la fase que se completó
        """
        # Log ya se hace en el worker (mismo thread del análisis, más preciso)
        if not self.progress_card:
            return

        # Marcar la fase como completada
        self.progress_card.set_phase_status(phase_id, 'completed')



    def _on_analysis_stats(self, stats):
        """
        Callback con estadísticas del análisis (ignorado - barra indeterminada)
        
        Args:
            stats: Objeto con estadísticas (ignorado)
        """
        # Con barra indeterminada, no necesitamos mostrar estadísticas detalladas
        pass

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
        Callback cuando el análisis termina exitosamente.
        El worker ya aplicó el delay de 2s, así que podemos transicionar inmediatamente.

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

        # Limpiar estado
        self.current_phase = None

        # Verificar si el diálogo de cancelación está abierto
        if self.cancel_dialog_open:
            self.logger.info("Análisis terminó mientras diálogo de cancelación estaba abierto, esperando...")
            self.analysis_completed_while_cancel_dialog_open = True
            return

        # Emitir señal de análisis completado y transicionar
        self.analysis_completed.emit(results)
        self._perform_stage_3_transition()
    
    def _perform_stage_3_transition(self):
        """Realiza la transición a Fase 3"""
        self.logger.debug("Realizando transición a Stage 3")
        self.main_window._transition_to_state_3(self.analysis_results)

    def _on_analysis_error(self, error_msg: str):
        """
        Callback cuando ocurre un error en el análisis

        Args:
            error_msg: Mensaje de error
        """
        self.logger.error(f"Error en análisis: {error_msg}")

        # Detener el worker si está corriendo
        if hasattr(self, 'analysis_worker') and self.analysis_worker:
            self.analysis_worker.stop()

        # Marcar fase actual como error si existe
        if self.progress_card and self.current_phase:
            self.progress_card.set_phase_status(self.current_phase, 'error')
        
        self.current_phase = None

        # Detener la barra de progreso
        if self.progress_card:
            self.progress_card.stop_progress()

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
        exit_btn = msg.addButton("Salir", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(retry_btn)

        msg.exec()

        # Manejar la respuesta del usuario
        if msg.clickedButton() == retry_btn:
            self.logger.info("Usuario eligió reintentar el análisis")
            self._restart_analysis()
        elif msg.clickedButton() == change_btn:
            self.logger.info("Usuario eligió cambiar de carpeta")
            self._return_to_state_1()
        else:  # exit_btn o cerrar diálogo
            self.logger.info("Usuario eligió salir - volviendo a Stage 1")
            self._return_to_state_1()

    def _restart_analysis(self):
        """Reinicia el análisis de la carpeta actual"""
        self.logger.info("Reiniciando análisis...")

        # Limpiar estado de análisis previo
        if self.progress_card:
            self.progress_card.reset()

        if self.progress_card:
            self.progress_card.reset_phases()

        # Reiniciar análisis
        self._start_analysis()

    def _return_to_state_1(self):
        """Vuelve al Estado 1 para seleccionar otra carpeta"""
        self.logger.info("Volviendo a Estado 1")

        # Limpiar datos del análisis
        self.analysis_results = None

        # Transición al Estado 1 a través de MainWindow
        self.main_window._transition_to_state_1()
    
    def _on_cancel_requested(self):
        """Usuario solicitó cancelar el análisis"""
        self.logger.info("Usuario solicitó cancelar el análisis")
        
        # Marcar que el diálogo está abierto
        self.cancel_dialog_open = True
        
        msg = QMessageBox(self.main_window)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Cancelar análisis")
        msg.setText("¿Estás seguro de que quieres cancelar el análisis?")
        msg.setInformativeText("Se perderá el progreso actual.")
        
        # Botones con roles claros
        continue_btn = msg.addButton("Continuar análisis", QMessageBox.ButtonRole.RejectRole)
        change_btn = msg.addButton("Seleccionar otra carpeta", QMessageBox.ButtonRole.ActionRole)
        msg.setDefaultButton(continue_btn)
        
        msg.exec()
        
        # Marcar que el diálogo se cerró
        self.cancel_dialog_open = False
        
        # Manejar respuesta
        if msg.clickedButton() == change_btn:
            self.logger.info("Usuario eligió seleccionar otra carpeta")
            self._cancel_and_return_to_stage_1()
        else:
            self.logger.info("Usuario eligió continuar el análisis")
            # Si el análisis terminó mientras el diálogo estaba abierto, hacer la transición ahora
            if self.analysis_completed_while_cancel_dialog_open:
                self.logger.info("Análisis terminó mientras diálogo estaba abierto, haciendo transición ahora")
                self._perform_stage_3_transition()
        
        # Resetear la bandera
        self.analysis_completed_while_cancel_dialog_open = False
    
    def _cancel_and_return_to_stage_1(self):
        """Cancela el análisis y vuelve a Fase 1"""
        self.logger.info("Cancelando análisis y volviendo a Fase 1")
        
        # Detener worker si está ejecutándose
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.logger.debug("Deteniendo worker de análisis...")
            self.analysis_worker.stop()
            
            # Esperar con timeout para evitar bloqueos indefinidos
            # Con 50000 archivos, el worker debería responder en menos de 5 segundos
            if not self.analysis_worker.wait(5000):  # 5 segundos de timeout
                self.logger.warning("Worker no respondió en 5 segundos, terminando forzosamente")
                self.analysis_worker.terminate()
                # Esperar un poco más después de terminate
                self.analysis_worker.wait(1000)
            else:
                self.logger.info("Worker detenido correctamente")
        
        # Volver a Estado 1
        self._return_to_state_1()
