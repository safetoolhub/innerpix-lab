"""
Workers para la aplicación Pixaro Lab
Este módulo contiene todos los QThread workers que ejecutan operaciones
en segundo plano para no bloquear la interfaz gráfica.
"""
import time
from PyQt6.QtCore import QThread, pyqtSignal
from config import Config


class BaseWorker(QThread):
    """Base worker that provides common signals and a helper to create
    progress callbacks to avoid repeating the same small functions in
    every worker.
    """
    progress_update = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)  # Changed from dict to object to support dataclasses
    error = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_requested = False

    def stop(self):
        """Request the worker to stop gracefully"""
        self._stop_requested = True

    def is_stop_requested(self):
        """Check if stop was requested"""
        return self._stop_requested

    def _create_progress_callback(self, counts_in_message: bool = False, emit_numbers: bool = False):
        """Return a progress callback(current, total, message) with consistent
        behavior across workers.

        - By default emits (0, 0, message) so the UI shows only the text.
        - If counts_in_message is True, appends " (current/total)" to the
          message and still emits numeric placeholders (0,0) for UI.
        - If emit_numbers is True, emits (current, total, message) so the
          UI can use real progress numbers.
        
        Returns:
            Callable that returns False when stop is requested, True otherwise
        """
        def callback(current: int, total: int, message: str):
            # Check if stop was requested BEFORE emitting
            if self._stop_requested:
                return False  # Signal to stop processing immediately
            
            try:
                if emit_numbers:
                    self.progress_update.emit(current, total, message)
                elif counts_in_message:
                    self.progress_update.emit(0, 0, f"{message} ({current}/{total})")
                else:
                    self.progress_update.emit(0, 0, message)
            except Exception:
                # La señal de progreso no debe bloquear el worker
                pass
            
            # Check again after emitting in case stop was requested during emit
            return not self._stop_requested

        return callback


class AnalysisWorker(BaseWorker):
    """
    Worker unificado para análisis completo.
    Delega la lógica de análisis a AnalysisOrchestrator y solo maneja
    threading + señales Qt + timing mínimo configurable por fase.
    """
    phase_update = pyqtSignal(str)  # Emite phase_id cuando inicia
    phase_completed = pyqtSignal(str)  # Emite phase_id cuando completa (con delay si necesario)
    stats_update = pyqtSignal(object)
    partial_results = pyqtSignal(object)

    def __init__(self, directory, renamer, lp_detector, unifier, heic_remover, duplicate_detector=None, organization_type=None):
        super().__init__()
        self.directory = directory
        self.renamer = renamer
        self.lp_detector = lp_detector
        self.unifier = unifier
        self.heic_remover = heic_remover
        self.duplicate_detector = duplicate_detector
        self.organization_type = organization_type
        self.phase_timings = {}  # Almacena timing de cada fase
        
        # Leer duración mínima desde config
        self.min_phase_duration = Config.MIN_PHASE_DURATION_SECONDS
        self.final_delay = Config.FINAL_DELAY_BEFORE_STAGE3_SECONDS

    def _ensure_min_phase_duration(self, phase_id: str, actual_duration: float):
        """
        Asegura que una fase tenga al menos min_phase_duration de visualización.
        Si la duración real es menor, hace sleep del tiempo restante.
        Antes del delay, asegura que el progreso muestre 100% (current == total).
        
        Args:
            phase_id: ID de la fase
            actual_duration: Duración real de la fase en segundos
        """
        if actual_duration < self.min_phase_duration:
            delay_needed = self.min_phase_duration - actual_duration
            self.logger.debug(
                f"Fase '{phase_id}' completada en {actual_duration:.2f}s, "
                f"agregando delay de {delay_needed:.2f}s (mínimo: {self.min_phase_duration:.1f}s)"
            )
            time.sleep(delay_needed)

    def run(self):
        try:
            # Importar orchestrator aquí para evitar dependencias circulares
            from services.analysis_orchestrator import AnalysisOrchestrator
            from utils.logger import get_logger
            
            self.logger = get_logger('AnalysisWorker')
            orchestrator = AnalysisOrchestrator()
            
            # Callbacks para conectar orchestrator con señales Qt
            def phase_callback(phase_id: str):
                """
                Emite cuando inicia una fase.
                Completa la fase anterior si existe (aplicando delay mínimo).
                """
                if self._stop_requested:
                    return
                
                # Si hay una fase anterior, completarla con delay mínimo
                if self.phase_timings:
                    last_phase_id = list(self.phase_timings.keys())[-1]
                    last_timing = self.phase_timings[last_phase_id]
                    
                    # Emitir progreso final (100%) antes del delay si tenemos el total
                    if 'total_files' in last_timing and last_timing['total_files'] > 0:
                        total = last_timing['total_files']
                        self.progress_update.emit(total, total, f"Completando {last_phase_id}...")
                    
                    self._ensure_min_phase_duration(last_phase_id, last_timing['duration'])
                    
                    if not self._stop_requested:
                        self.phase_completed.emit(last_phase_id)
                
                # Registrar inicio de nueva fase
                self.phase_timings[phase_id] = {
                    'start_time': time.time(),
                    'duration': 0.0
                }
                
                # Emitir inicio de fase
                self.phase_update.emit(phase_id)
            
            def partial_callback(phase_name: str, data):
                """Emite resultados parciales y registra duración de fase"""
                if self._stop_requested:
                    return
                
                # Registrar duración real de la fase
                if phase_name in self.phase_timings:
                    self.phase_timings[phase_name]['duration'] = (
                        time.time() - self.phase_timings[phase_name]['start_time']
                    )
                    # Guardar el total de archivos para esta fase
                    if hasattr(data, 'total_files'):
                        self.phase_timings[phase_name]['total_files'] = data.total_files
                
                # Emitir resultado parcial
                if phase_name == 'scan':
                    self.stats_update.emit(data)
                else:
                    self.partial_results.emit({phase_name: data})
            
            # Ejecutar análisis completo usando orchestrator
            # Usar emit_numbers=True para que las fases con números reales (scan, duplicates)
            # emitan (current, total, mensaje) y el UI pueda mostrar progreso real
            result = orchestrator.run_full_analysis(
                directory=self.directory,
                renamer=self.renamer,
                lp_detector=self.lp_detector,
                organizer=self.unifier,
                heic_remover=self.heic_remover,
                duplicate_detector=self.duplicate_detector,
                organization_type=self.organization_type,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                phase_callback=phase_callback,
                partial_callback=partial_callback
            )
            
            # Completar la última fase (finalizing) con delay mínimo
            if self.phase_timings and not self._stop_requested:
                last_phase_id = list(self.phase_timings.keys())[-1]
                last_timing = self.phase_timings[last_phase_id]
                
                # Emitir progreso final (100%) antes del delay si tenemos el total
                if 'total_files' in last_timing and last_timing['total_files'] > 0:
                    total = last_timing['total_files']
                    self.progress_update.emit(total, total, f"Completando {last_phase_id}...")
                
                self._ensure_min_phase_duration(last_phase_id, last_timing['duration'])
                
                if not self._stop_requested:
                    self.phase_completed.emit(last_phase_id)
            
            # Delay adicional configurable antes de transicionar a Stage 3
            if not self._stop_requested:
                self.logger.info(f"Análisis completado, esperando {self.final_delay:.1f}s antes de transicionar...")
                time.sleep(self.final_delay)
            
            # Emitir resultado final
            if not self._stop_requested:
                self.finished.emit(result.to_dict())

        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class RenamingWorker(BaseWorker):
    """Worker para ejecutar renombrado de nombres de archivos"""

    def __init__(self, renamer, plan, create_backup=True, dry_run=False):
        super().__init__()
        self.renamer = renamer
        self.plan = plan
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self):
        try:
            if self._stop_requested:
                return
            
            results = self.renamer.execute_renaming(
                self.plan,
                create_backup=self.create_backup,
                dry_run=self.dry_run,
                progress_callback=self._create_progress_callback()
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class LivePhotoCleanupWorker(BaseWorker):
    """Worker para ejecutar limpieza de Live Photos"""

    def __init__(self, cleaner, plan):
        super().__init__()
        self.cleaner = cleaner
        self.plan = plan

    def run(self):
        try:
            if self._stop_requested:
                return
            
            # El plan es un diccionario que incluye create_backup y dry_run
            # Extraer estos parámetros del plan antes de pasarlo a execute_cleanup
            create_backup = self.plan.get('create_backup', True)
            dry_run = self.plan.get('dry_run', False)
            
            # Pasar el plan completo - execute_cleanup lo convertirá a dataclass si es necesario
            results = self.cleaner.execute_cleanup(
                self.plan,
                create_backup=create_backup,
                dry_run=dry_run,
                progress_callback=self._create_progress_callback()
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class FileOrganizerWorker(BaseWorker):
    """Worker para ejecutar organización de archivos"""

    def __init__(self, organizer, plan, create_backup=True, dry_run=False):
        super().__init__()
        self.organizer = organizer
        self.plan = plan
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self):
        try:
            if self._stop_requested:
                return
            
            results = self.organizer.execute_organization(
                self.plan,
                create_backup=self.create_backup,
                dry_run=self.dry_run,
                progress_callback=self._create_progress_callback()
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class HEICRemovalWorker(BaseWorker):
    """Worker para ejecutar eliminación de duplicados HEIC"""

    def __init__(self, remover, pairs, keep_format, create_backup=True, dry_run=False):
        super().__init__()
        self.remover = remover
        self.pairs = pairs
        self.keep_format = keep_format
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self):
        try:
            if self._stop_requested:
                return
            
            progress_cb_local = self._create_progress_callback()

            # Attach callback to remover so create_backup (which may not accept
            # progress_callback explicitly) can use it via attribute
            setattr(self.remover, '_progress_callback', progress_cb_local)

            results = self.remover.execute_removal(
                self.pairs,
                keep_format=self.keep_format,
                create_backup=self.create_backup,
                dry_run=self.dry_run
            )
            # Clean up attribute
            if hasattr(self.remover, '_progress_callback'):
                delattr(self.remover, '_progress_callback')
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)

class DuplicateAnalysisWorker(BaseWorker):
    """Worker para análisis de duplicados (exactos o similares)"""
    
    def __init__(self, detector, directory, mode='exact', sensitivity=10):
        super().__init__()
        self.detector = detector
        self.directory = directory
        self.mode = mode
        self.sensitivity = sensitivity
    
    def run(self):
        try:
            if self._stop_requested:
                return
            
            if self.mode == 'exact':
                results = self.detector.analyze_exact_duplicates(
                    self.directory,
                    progress_callback=self._create_progress_callback(emit_numbers=True)
                )
            else:  # perceptual
                results = self.detector.analyze_similar_duplicates(
                    self.directory,
                    sensitivity=self.sensitivity,
                    progress_callback=self._create_progress_callback(emit_numbers=True)
                )
            
            if not self._stop_requested:
                self.finished.emit(results)
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class DuplicateDeletionWorker(BaseWorker):
    """Worker para eliminación de duplicados"""
    
    def __init__(self, detector, groups, keep_strategy, create_backup=True, dry_run=False):
        super().__init__()
        self.detector = detector
        self.groups = groups
        self.keep_strategy = keep_strategy
        self.create_backup = create_backup
        self.dry_run = dry_run
    
    def run(self):
        try:
            if self._stop_requested:
                return
            
            results = self.detector.execute_deletion(
                self.groups,
                keep_strategy=self.keep_strategy,
                create_backup=self.create_backup,
                dry_run=self.dry_run,
                progress_callback=self._create_progress_callback()
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)
