"""
Workers para la aplicación Pixaro Lab
Este módulo contiene todos los QThread workers que ejecutan operaciones
en segundo plano para no bloquear la interfaz gráfica.

Todos los workers heredan de BaseWorker y proporcionan señales tipadas
con los dataclasses correspondientes de services.result_types
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, List, Dict, Optional, Callable
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from config import Config

# Imports condicionales para type checking (evita imports circulares en runtime)
if TYPE_CHECKING:
    from services.result_types import (
        FullAnalysisResult,
        RenameResult,
        OrganizationResult,
        LivePhotoCleanupResult,
        HeicDeletionResult,
        DuplicateAnalysisResult,
        DuplicateDeletionResult,
        ScanResult
    )
    from services.file_renamer import FileRenamer
    from services.live_photo_detector import LivePhotoDetector
    from services.live_photo_cleaner import LivePhotoCleaner
    from services.file_organizer import FileOrganizer
    from services.heic_remover import HEICDuplicateRemover
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
    
    Signals:
        finished(FullAnalysisResult): Emite resultado completo del análisis
        phase_update(str): Emite phase_id cuando inicia una fase
        phase_completed(str): Emite phase_id cuando completa una fase
        stats_update(ScanResult): Emite estadísticas de escaneo
        partial_results(dict): Emite resultados parciales por fase
        progress_update(int, int, str): Heredado de BaseWorker
        error(str): Heredado de BaseWorker
    """
    # Sobrescribir finished con tipo específico (FullAnalysisResult)
    finished = pyqtSignal(object)  # En runtime es object, pero tipo semántico es FullAnalysisResult
    
    phase_update = pyqtSignal(str)
    phase_completed = pyqtSignal(str)
    stats_update = pyqtSignal(object)  # ScanResult
    partial_results = pyqtSignal(object)  # Dict[str, AnalysisResult]

    def __init__(
        self, 
        directory: Path,
        renamer: 'FileRenamer',
        live_photo_detector: 'LivePhotoDetector',
        unifier: 'FileOrganizer',
        heic_remover: 'HEICDuplicateRemover',
        duplicate_exact_detector: Optional['ExactCopiesDetector'] = None,
        organization_type: Optional[str] = None
    ):
        super().__init__()
        self.directory = directory
        self.renamer = renamer
        self.live_photo_detector = live_photo_detector
        self.unifier = unifier
        self.heic_remover = heic_remover
        self.duplicate_exact_detector = duplicate_exact_detector
        self.organization_type = organization_type
        self.phase_timings: Dict[str, Dict] = {}  # Almacena timing de cada fase
        
        # Leer duración mínima desde config
        self.min_phase_duration: float = Config.MIN_PHASE_DURATION_SECONDS
        self.final_delay: float = Config.FINAL_DELAY_BEFORE_STAGE3_SECONDS

    def _ensure_min_phase_duration(self, phase_id: str, actual_duration: float) -> None:
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

    def run(self) -> None:
        try:
            # Importar orchestrator aquí para evitar dependencias circulares
            from services.analysis_orchestrator import AnalysisOrchestrator
            from utils.logger import get_logger
            
            self.logger = get_logger('AnalysisWorker')
            orchestrator = AnalysisOrchestrator()
            
            # Callbacks para conectar orchestrator con señales Qt
            def phase_callback(phase_id: str) -> None:
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
            
            def partial_callback(phase_name: str, data) -> None:
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
            result: 'FullAnalysisResult' = orchestrator.run_full_analysis(
                directory=self.directory,
                renamer=self.renamer,
                live_photo_detector=self.live_photo_detector,
                organizer=self.unifier,
                heic_remover=self.heic_remover,
                duplicate_exact_detector=self.duplicate_exact_detector,
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
            
            # Emitir resultado final (dataclass directamente, no dict)
            if not self._stop_requested:
                self.finished.emit(result)

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
        plan: List[Dict],
        create_backup: bool = True,
        dry_run: bool = False
    ):
        super().__init__()
        self.renamer = renamer
        self.plan = plan
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results: 'RenameResult' = self.renamer.execute_renaming(
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
    """
    Worker para ejecutar limpieza de Live Photos
    
    Signals:
        finished(LivePhotoCleanupResult): Emite resultado de la limpieza
        progress_update(int, int, str): Heredado de BaseWorker
        error(str): Heredado de BaseWorker
    """
    # Sobrescribir finished con tipo específico
    finished = pyqtSignal(object)  # En runtime es object, tipo semántico es LivePhotoCleanupResult

    def __init__(self, cleaner: 'LivePhotoCleaner', plan: Dict):
        super().__init__()
        self.cleaner = cleaner
        self.plan = plan

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            # El plan es un diccionario que incluye create_backup y dry_run
            # Extraer estos parámetros del plan antes de pasarlo a execute_cleanup
            create_backup = self.plan.get('create_backup', True)
            dry_run = self.plan.get('dry_run', False)
            
            # Pasar el plan completo - execute_cleanup lo convertirá a dataclass si es necesario
            results: 'LivePhotoCleanupResult' = self.cleaner.execute_cleanup(
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
        plan: List[Dict],
        create_backup: bool = True,
        dry_run: bool = False
    ):
        super().__init__()
        self.organizer = organizer
        self.plan = plan
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results: 'OrganizationResult' = self.organizer.execute_organization(
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
        remover: 'HEICDuplicateRemover',
        pairs: List[Dict],
        keep_format: str,
        create_backup: bool = True,
        dry_run: bool = False
    ):
        super().__init__()
        self.remover = remover
        self.pairs = pairs
        self.keep_format = keep_format
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            progress_cb_local = self._create_progress_callback()

            # Attach callback to remover so create_backup (which may not accept
            # progress_callback explicitly) can use it via attribute
            setattr(self.remover, '_progress_callback', progress_cb_local)

            results: 'HeicDeletionResult' = self.remover.execute_removal(
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
            
            results: 'DuplicateDeletionResult' = self.detector.execute_deletion(
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


class SimilarFilesAnalysisWorker(BaseWorker):
    """
    Worker para análisis de archivos similares (perceptual hash).
    
    Detecta fotos y vídeos visualmente similares: recortes, rotaciones,
    ediciones o diferentes resoluciones.
    
    Este análisis puede tardar varios minutos dependiendo del número de archivos.
    
    Signals:
        progress_update(int, int, str): (current, total, message)
        finished(DuplicateAnalysisResult): Resultado del análisis con grupos de similares
        error(str): Mensaje de error
    """
    finished = pyqtSignal(object)  # DuplicateAnalysisResult
    
    def __init__(
        self,
        detector: 'SimilarFilesDetector',
        workspace_path: Path,
        sensitivity: int
    ):
        """
        Args:
            detector: Instancia de SimilarFilesDetector
            workspace_path: Path del directorio a analizar
            sensitivity: Sensibilidad del análisis (0-20)
        """
        super().__init__()
        self.detector = detector
        self.workspace_path = workspace_path
        self.sensitivity = sensitivity
    
    def run(self) -> None:
        """Ejecuta el análisis de archivos similares"""
        try:
            if self._stop_requested:
                return
            
            # Callback de progreso que verifica cancelación
            def progress_callback(current: int, total: int, message: str) -> bool:
                if self._stop_requested:
                    return False
                self.progress_update.emit(current, total, message)
                return True
            
            results: 'DuplicateAnalysisResult' = self.detector.analyze_similar_duplicates(
                directory=self.workspace_path,
                sensitivity=self.sensitivity,
                progress_callback=progress_callback
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class WorkspaceReanalysisWorker(BaseWorker):
    """
    Worker para re-análisis automático del workspace.
    Solo ejecuta análisis rápidos (< 5 segundos cada uno).
    
    Este worker se ejecuta en background cuando se modifican archivos
    para mantener actualizadas las 5 herramientas de análisis rápido:
    - Live Photos
    - HEIC/JPG
    - Duplicados Exactos
    - Organizar
    - Renombrar
    
    Signals:
        progress_update(int, int, str): (current, total, message)
        tool_completed(str, object): (tool_name, results) cuando termina cada herramienta
        finished(dict): Todos los resultados {tool_name: results}
        tool_error(str, str): (tool_name, error_message)
    """
    tool_completed = pyqtSignal(str, object)  # (tool_name, results)
    tool_error = pyqtSignal(str, str)  # (tool_name, error_message) - señal específica
    finished = pyqtSignal(dict)  # {tool_name: results}
    
    def __init__(self, workspace_path: Path):
        """
        Args:
            workspace_path: Path del directorio a re-analizar
        """
        super().__init__()
        self.workspace_path = workspace_path
        
    def run(self) -> None:
        """Ejecuta re-análisis de todas las herramientas rápidas"""
        from services.live_photo_detector import LivePhotoDetector
        from services.heic_remover import HEICDuplicateRemover
        from services.exact_copies_detector import ExactCopiesDetector
        from services.file_organizer import FileOrganizer
        from services.file_renamer import FileRenamer
        from config import Config
        
        results = {}
        
        # Lista de análisis a ejecutar (solo rápidos)
        tools_to_analyze = [
            ("live_photos", LivePhotoDetector, "Live Photos"),
            ("heic", HEICDuplicateRemover, "HEIC/JPG"),
            ("exact_duplicates", ExactCopiesDetector, "Duplicados Exactos"),
            ("organize", FileOrganizer, "Organizar"),
            ("rename", FileRenamer, "Renombrar")
        ]
        
        total = len(tools_to_analyze)
        
        for idx, (tool_name, detector_class, display_name) in enumerate(tools_to_analyze, 1):
            if self._stop_requested:
                break
            
            # Emitir progreso (0, 0 para que solo se muestre el mensaje)
            self.progress_update.emit(0, 0, f"Analizando: {display_name} ({idx}/{total})")
            
            try:
                detector = detector_class()
                
                # Ejecutar análisis según el tipo de detector
                if tool_name == "live_photos":
                    result = detector.detect_live_photos(self.workspace_path)
                elif tool_name == "heic":
                    result = detector.analyze_heic_jpg_pairs(self.workspace_path)
                elif tool_name == "exact_duplicates":
                    result = detector.analyze_exact_duplicates(
                        directory=self.workspace_path,
                        progress_callback=None  # Re-análisis rápido sin progreso detallado
                    )
                elif tool_name == "organize":
                    result = detector.analyze_organization(
                        directory=self.workspace_path,
                        organization_type='BY_MONTH'  # Tipo por defecto
                    )
                elif tool_name == "rename":
                    result = detector.analyze_directory(
                        directory=self.workspace_path,
                        pattern='{date}_{time}_{original}'  # Patrón por defecto
                    )
                
                # Guardar resultado y notificar
                results[tool_name] = result
                self.tool_completed.emit(tool_name, result)
                
            except Exception as e:
                if not self._stop_requested:
                    import traceback
                    error_msg = f"{str(e)}\n{traceback.format_exc()}"
                    self.tool_error.emit(tool_name, error_msg)
                    results[tool_name] = None  # Marcar como fallido
        
        # Emitir resultados completos
        if not self._stop_requested:
            self.finished.emit(results)
