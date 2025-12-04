"""
Workers para la aplicación Pixaro Lab

Este módulo contiene todos los QThread workers que ejecutan operaciones
en segundo plano para no bloquear la interfaz gráfica.

ARQUITECTURA:
- BaseWorker: Clase base con señales comunes y helpers
- AnalysisWorker: Worker completo que delega a AnalysisOrchestrator
- Execution Workers: RenamingWorker, LivePhotoCleanupWorker, etc.

PRINCIPIOS DE DISEÑO:
1. Zero duplicación: El orchestrator maneja timing y lógica, workers solo Qt
2. Type safety: Todos los workers usan dataclasses de services.result_types
3. Cancelación uniforme: _stop_requested verificado en puntos clave
4. UX suave: Delays mínimos configurables para feedback visual

OPTIMIZACIONES APLICADAS:
- Callbacks simplificados (_handle_phase_start, _handle_partial_result)
- Timing centralizado en orchestrator (zero duplicación)
- Progress callback con verificación única de stop
- Señales Qt emitidas en tiempo real sin procesamiento extra

SINERGIAS POTENCIALES (Futuro):
Para directorios muy grandes (10k+ archivos), podría optimizarse scan_directory
para pre-cachear datos compartidos entre fases:
- Hashes SHA256: Usados por exact_copies y heic_remover
- Fechas EXIF: Usadas por file_renamer y file_organizer
- Metadata básico: Tamaño, tipo, usado por todas las fases

Implementación sugerida: DirectoryScanResult extendido con cache opcional
que se pasa entre fases. Requiere refactor del orchestrator para soportar
context sharing entre servicios.

SINCRONIZACIÓN UI-WORKER:
- phase_update: UI muestra nueva fase activa
- phase_completed: UI marca fase como completada (con delay UX)
- stats_update: UI actualiza estadísticas de escaneo
- partial_results: UI puede mostrar preview de resultados
- progress_update: UI actualiza barra de progreso
- finished: UI recibe FullAnalysisResult con todos los datos
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, List, Dict, Optional, Callable, Any
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from config import Config

# Imports condicionales para type checking (evita imports circulares en runtime)
if TYPE_CHECKING:
    from services.result_types import (
        FullAnalysisResult,
        RenameResult,
        RenameAnalysisResult,
        OrganizationResult,
        OrganizationAnalysisResult,
        LivePhotoCleanupResult,
        LivePhotoCleanupAnalysisResult,
        HeicDeletionResult,
        HeicAnalysisResult,
        DuplicateAnalysisResult,
        DuplicateDeletionResult,
        ScanResult
    )
    from services.file_renamer_service import FileRenamer
    from services.live_photos_service import LivePhotoService
    from services.file_organizer_service import FileOrganizer
    from services.heic_remover_service import HEICRemover
    from services.exact_copies_detector import ExactCopiesDetector
    from services.similar_files_detector import SimilarFilesDetector



class BaseWorker(QThread):
    """
    Base worker that provides common signals and helper for progress callbacks.
    
    Subclasses should override the 'finished' signal with a typed version
    matching their result dataclass type.
    
    Signals:
        progress_update(int, int, str): Emite (current, total, message) para actualizar progreso
        finished(object): Emite resultado de operación (subclases deben sobrescribir con tipo específico)
        error(str): Emite mensaje de error con traceback
    """
    progress_update = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)  # Genérico - subclases deben sobrescribir con tipo específico
    error = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_requested: bool = False

    def stop(self) -> None:
        """Request the worker to stop gracefully"""
        self._stop_requested = True

    def is_stop_requested(self) -> bool:
        """Check if stop was requested"""
        return self._stop_requested

    def _create_progress_callback(
        self, 
        counts_in_message: bool = False, 
        emit_numbers: bool = False
    ) -> Callable[[int, int, str], bool]:
        """
        Return a progress callback(current, total, message) with consistent
        behavior across workers.

        - By default emits (0, 0, message) so the UI shows only the text.
        - If counts_in_message is True, appends " (current/total)" to the
          message and still emits numeric placeholders (0,0) for UI.
        - If emit_numbers is True, emits (current, total, message) so the
          UI can use real progress numbers.
        
        Returns:
            Callable that returns False when stop is requested, True otherwise
        """
        def callback(current: int, total: int, message: str) -> bool:
            # Single check for stop request (optimized)
            if self._stop_requested:
                return False
            
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
            
            # Return stop status
            return not self._stop_requested

        return callback



class AnalysisWorker(BaseWorker):
    """
    Worker unificado para análisis completo.
    
    Responsabilidades:
    - Threading: Ejecuta análisis en background sin bloquear UI
    - Señales Qt: Convierte callbacks del orchestrator en señales PyQt6
    - UX timing: Asegura duración mínima de fases para feedback visual
    
    El orchestrator maneja toda la lógica de análisis y timing interno.
    Este worker solo agrega la capa de presentación (delays UX, señales Qt).
    
    Signals:
        finished(FullAnalysisResult): Resultado completo con todos los timings
        phase_update(str): Notifica inicio de fase (para UI)
        phase_completed(str): Notifica fin de fase (para UI)
        stats_update(dict): Estadísticas de escaneo inicial
        partial_results(dict): Resultados parciales por fase
        progress_update(int, int, str): Progreso de operación actual
        error(str): Error con traceback
    """
    # Sobrescribir finished con tipo específico (FullAnalysisResult)
    finished = pyqtSignal(object)  # En runtime es object, pero tipo semántico es FullAnalysisResult
    
    phase_update = pyqtSignal(str)  # phase_id
    phase_completed = pyqtSignal(str)  # phase_id
    stats_update = pyqtSignal(object)  # Dict con estadísticas de scan
    partial_results = pyqtSignal(object)  # Dict[str, AnalysisResult]

    def __init__(
        self, 
        directory: Path,
        renamer: 'FileRenamer',
        live_photos_service: 'LivePhotoService',
        organizer: 'FileOrganizer',
        heic_remover: 'HEICRemover',
        duplicate_exact_detector: Optional['ExactCopiesDetector'] = None,
        organization_type: Optional[str] = None
    ):
        super().__init__()
        self.directory = directory
        self.renamer = renamer
        self.live_photo_service = live_photos_service
        self.organizer = organizer
        self.heic_remover = heic_remover
        self.duplicate_exact_detector = duplicate_exact_detector
        self.organization_type = organization_type
        
        # Leer configuración UX de delays
        self.min_phase_duration: float = Config.MIN_PHASE_DURATION_SECONDS
        self.final_delay: float = Config.FINAL_DELAY_BEFORE_STAGE3_SECONDS
        
        # Tracking de fase actual para delays UX
        self._current_phase_id: Optional[str] = None
        self._current_phase_start: float = 0.0

    def _handle_phase_start(self, phase_id: str) -> None:
        """
        Maneja el inicio de una nueva fase.
        Completa la fase anterior con delay UX si es necesario.
        
        Args:
            phase_id: ID de la nueva fase que está iniciando
        """
        if self._stop_requested:
            return
        
        # Completar fase anterior si existe
        if self._current_phase_id is not None:
            actual_duration = time.time() - self._current_phase_start
            
            # Aplicar delay UX si la fase fue muy rápida
            if actual_duration < self.min_phase_duration:
                delay = self.min_phase_duration - actual_duration
                self.logger.debug(
                    f"Fase '{self._current_phase_id}' duró {actual_duration:.2f}s, "
                    f"aplicando delay UX de {delay:.2f}s (mínimo: {self.min_phase_duration:.1f}s)"
                )
                time.sleep(delay)
            
            # Emitir señal de fase completada
            if not self._stop_requested:
                self.phase_completed.emit(self._current_phase_id)
        
        # Iniciar nueva fase
        self._current_phase_id = phase_id
        self._current_phase_start = time.time()
        self.phase_update.emit(phase_id)
    
    def _handle_partial_result(self, phase_id: str, result: Any) -> None:
        """
        Maneja resultados parciales de cada fase.
        
        Args:
            phase_id: ID de la fase
            result: Resultado parcial (puede ser dict o dataclass)
        """
        if self._stop_requested:
            return
        
        # El escaneo emite estadísticas en formato especial
        if phase_id == 'scan':
            self.stats_update.emit(result)
        else:
            # Otras fases emiten resultados en dict
            self.partial_results.emit({phase_id: result})

    def run(self) -> None:
        """
        Ejecuta el análisis completo en background.
        
        Flujo optimizado:
        1. Orchestrator ejecuta todo el análisis (sin delays)
        2. Worker aplica delays UX solo para presentación
        3. Señales Qt emitidas en tiempo real
        4. Zero duplicación de lógica de timing
        """
        try:
            # Importar dependencias aquí (evita imports circulares)
            from services.analysis_orchestrator import AnalysisOrchestrator
            from utils.logger import get_logger
            from utils.settings_manager import settings_manager
            
            self.logger = get_logger('AnalysisWorker')
            orchestrator = AnalysisOrchestrator()
            
            # Leer configuración de precalculate_hashes
            precalculate_hashes = settings_manager.get_precalculate_hashes()
            if precalculate_hashes:
                self.logger.info("🔐 Pre-cálculo de hashes ACTIVADO (configuración del usuario)")
            
            # Ejecutar análisis completo
            # El orchestrator maneja toda la lógica, este worker solo convierte a señales Qt
            result: 'FullAnalysisResult' = orchestrator.run_full_analysis(
                directory=self.directory,
                renamer=self.renamer,
                live_photos_service=self.live_photo_service,
                organizer=self.organizer,
                heic_remover=self.heic_remover,
                duplicate_exact_detector=self.duplicate_exact_detector,
                organization_type=self.organization_type,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                phase_callback=self._handle_phase_start,
                partial_callback=self._handle_partial_result,
                precalculate_hashes=precalculate_hashes
            )
            
            # Completar última fase con delay UX
            if self._current_phase_id and not self._stop_requested:
                actual_duration = time.time() - self._current_phase_start
                if actual_duration < self.min_phase_duration:
                    delay = self.min_phase_duration - actual_duration
                    self.logger.debug(
                        f"Fase final '{self._current_phase_id}' duró {actual_duration:.2f}s, "
                        f"aplicando delay UX de {delay:.2f}s"
                    )
                    time.sleep(delay)
                
                if not self._stop_requested:
                    self.phase_completed.emit(self._current_phase_id)
            
            # Delay final antes de transición a Stage 3 (UX suave)
            if not self._stop_requested:
                self.logger.debug(
                    f"Análisis completado en {result.total_duration:.2f}s, "
                    f"esperando {self.final_delay:.1f}s antes de transicionar a Stage 3"
                )
                time.sleep(self.final_delay)
            
            # Emitir resultado final
            if not self._stop_requested:
                self.finished.emit(result)
                
                # Liberar memoria explícitamente después de emitir
                # Esto ayuda con datasets grandes (>5000 archivos)
                import gc
                del result
                del orchestrator
                gc.collect()
                self.logger.debug("Memoria del worker liberada")

        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class RenamingWorker(BaseWorker):
    """
    Worker para ejecutar renombrado de nombres de archivos
    
    Signals:
        finished(RenameResult): Emite resultado del renombrado
        progress_update(int, int, str): Heredado de BaseWorker
        error(str): Heredado de BaseWorker
    """
    # Sobrescribir finished con tipo específico
    finished = pyqtSignal(object)  # En runtime es object, tipo semántico es RenameResult

    def __init__(
        self, 
        renamer: 'FileRenamer',
        analysis: 'RenameAnalysisResult',
        create_backup: bool = True,
        dry_run: bool = False
    ):
        super().__init__()
        self.renamer = renamer
        self.analysis = analysis
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results: 'RenameResult' = self.renamer.execute(
                self.analysis.renaming_plan,
                create_backup=self.create_backup,
                dry_run=self.dry_run,
                progress_callback=self._create_progress_callback(emit_numbers=True)
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class LivePhotoCleanupWorker(BaseWorker):
    """
    Worker para ejecutar limpieza de Live Photos
    
    Signals:
        finished(LivePhotoCleanupResult): Emite resultado de la limpieza
        progress_update(int, int, str): Heredado de BaseWorker
        error(str): Heredado de BaseWorker
    """
    # Sobrescribir finished con tipo específico
    finished = pyqtSignal(object)  # En runtime es object, tipo semántico es LivePhotoCleanupResult

    def __init__(self, service: 'LivePhotoService', analysis: 'LivePhotoCleanupAnalysisResult', 
                 create_backup: bool = True, dry_run: bool = False):
        super().__init__()
        self.service = service
        self.analysis = analysis
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results: 'LivePhotoCleanupResult' = self.service.execute(
                self.analysis,
                create_backup=self.create_backup,
                dry_run=self.dry_run,
                progress_callback=self._create_progress_callback(emit_numbers=True)
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class FileOrganizerWorker(BaseWorker):
    """
    Worker para ejecutar organización de archivos
    
    Signals:
        finished(OrganizationResult): Emite resultado de la organización
        progress_update(int, int, str): Heredado de BaseWorker
        error(str): Heredado de BaseWorker
    """
    # Sobrescribir finished con tipo específico
    finished = pyqtSignal(object)  # En runtime es object, tipo semántico es OrganizationResult

    def __init__(
        self,
        organizer: 'FileOrganizer',
        analysis: 'OrganizationAnalysisResult',
        cleanup_empty_dirs: bool = True,
        create_backup: bool = True,
        dry_run: bool = False
    ):
        super().__init__()
        self.organizer = organizer
        self.analysis = analysis
        self.cleanup_empty_dirs = cleanup_empty_dirs
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results: 'OrganizationResult' = self.organizer.execute(
                self.analysis.move_plan,
                create_backup=self.create_backup,
                cleanup_empty_dirs=self.cleanup_empty_dirs,
                dry_run=self.dry_run,
                progress_callback=self._create_progress_callback(emit_numbers=True)
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class HEICRemovalWorker(BaseWorker):
    """
    Worker para ejecutar eliminación de duplicados HEIC
    
    Signals:
        finished(HeicDeletionResult): Emite resultado de la eliminación
        progress_update(int, int, str): Heredado de BaseWorker
        error(str): Heredado de BaseWorker
    """
    # Sobrescribir finished con tipo específico
    finished = pyqtSignal(object)  # En runtime es object, tipo semántico es HeicDeletionResult

    def __init__(
        self,
        remover: 'HEICRemover',
        analysis: 'HeicAnalysisResult',
        keep_format: str,
        create_backup: bool = True,
        dry_run: bool = False
    ):
        super().__init__()
        self.remover = remover
        self.analysis = analysis
        self.keep_format = keep_format
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            progress_cb_local = self._create_progress_callback(emit_numbers=True)

            # Attach callback to remover so create_backup (which may not accept
            # progress_callback explicitly) can use it via attribute
            setattr(self.remover, '_progress_callback', progress_cb_local)

            results: 'HeicDeletionResult' = self.remover.execute(
                self.analysis.duplicate_pairs,
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
    """
    Worker para análisis de duplicados (exactos o similares)
    
    Signals:
        finished(DuplicateAnalysisResult): Emite resultado del análisis
        progress_update(int, int, str): Heredado de BaseWorker
        error(str): Heredado de BaseWorker
    """
    # Sobrescribir finished con tipo específico
    finished = pyqtSignal(object)  # En runtime es object, tipo semántico es DuplicateAnalysisResult
    
    def __init__(
        self,
        detector: 'ExactCopiesDetector | SimilarFilesDetector',
        directory: Path,
        mode: str = 'exact',
        sensitivity: int = 10
    ):
        super().__init__()
        self.detector = detector
        self.directory = directory
        self.mode = mode
        self.sensitivity = sensitivity
    
    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results: 'DuplicateAnalysisResult'
            if self.mode == 'exact':
                results = self.detector.analyze(
                    self.directory,
                    progress_callback=self._create_progress_callback(emit_numbers=True)
                )
            else:  # perceptual
                results = self.detector.analyze(
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
    """
    Worker para eliminación de duplicados
    
    Signals:
        finished(DuplicateDeletionResult): Emite resultado de la operación
        progress_update(int, int, str): Heredado de BaseWorker
        error(str): Heredado de BaseWorker
    """
    # Sobrescribir finished con tipo específico
    finished = pyqtSignal(object)  # En runtime es object, tipo semántico es DuplicateDeletionResult
    
    def __init__(
        self,
        detector: 'ExactCopiesDetector | SimilarFilesDetector',
        groups: List,
        keep_strategy: str,
        create_backup: bool = True,
        dry_run: bool = False
    ):
        super().__init__()
        self.detector = detector
        self.groups = groups
        self.keep_strategy = keep_strategy
        self.create_backup = create_backup
        self.dry_run = dry_run
    
    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results: 'DuplicateDeletionResult' = self.detector.execute(
                self.groups,
                keep_strategy=self.keep_strategy,
                create_backup=self.create_backup,
                dry_run=self.dry_run,
                progress_callback=self._create_progress_callback(emit_numbers=True)
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class SimilarFilesAnalysisWorker(BaseWorker):
    """
    Worker para análisis inicial de archivos similares (perceptual hash).
    
    Solo calcula hashes perceptuales (operación costosa ~5 min).
    El clustering con diferentes sensibilidades se hace on-demand
    en el diálogo de gestión (<1 segundo).
    
    Signals:
        progress_update(int, int, str): (current, total, message)
        finished(SimilarFilesAnalysis): Análisis con hashes calculados
        error(str): Mensaje de error
    """
    finished = pyqtSignal(object)  # SimilarFilesAnalysis
    
    def __init__(
        self,
        detector: 'SimilarFilesDetector',
        workspace_path: Path
    ):
        """
        Args:
            detector: Instancia de SimilarFilesDetector
            workspace_path: Path del directorio a analizar
        """
        super().__init__()
        self.detector = detector
        self.workspace_path = workspace_path
    
    def run(self) -> None:
        """Ejecuta el análisis inicial de archivos similares"""
        try:
            if self._stop_requested:
                return
            
            # Callback de progreso que verifica cancelación
            def progress_callback(current: int, total: int, message: str) -> bool:
                if self._stop_requested:
                    return False
                self.progress_update.emit(current, total, message)
                return True
            
            # Importar tipo para type hint
            from services.similar_files_detector import SimilarFilesAnalysis
            
            # Ejecutar análisis inicial (solo hashes)
            analysis: SimilarFilesAnalysis = self.detector.analyze_initial(
                workspace_path=self.workspace_path,
                progress_callback=progress_callback
            )
            
            if not self._stop_requested:
                self.finished.emit(analysis)
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)
