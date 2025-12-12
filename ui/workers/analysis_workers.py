"""
Analysis Workers for Stage 2 (Scan) and Stage 3 (On-Demand Analysis).
"""
import time
from pathlib import Path
from typing import Optional, Any
from PyQt6.QtCore import pyqtSignal

from config import Config
from .base_worker import BaseWorker

class AnalysisWorker(BaseWorker):
    """
    Worker for Stage 2: Initial Directory Scan ONLY.
    """
    # Sobrescribir finished con tipo específico (FullAnalysisResult)
    finished = pyqtSignal(object)
    
    phase_update = pyqtSignal(str)  # phase_id
    phase_completed = pyqtSignal(str)  # phase_id
    phase_text_update = pyqtSignal(str, str)  # phase_id, new_text
    stats_update = pyqtSignal(object)  # Dict con estadísticas de scan
    partial_results = pyqtSignal(object)  # Dict[str, AnalysisResult]

    def __init__(self, directory: Path):
        super().__init__()
        self.directory = directory
        
        # Leer configuración UX de delays
        self.min_phase_duration: float = Config.MIN_PHASE_DURATION_SECONDS
        self.final_delay: float = Config.FINAL_DELAY_BEFORE_STAGE3_SECONDS
        
        # Tracking de fase actual para delays UX
        self._current_phase_id: Optional[str] = None
        self._current_phase_start: float = 0.0

    def _handle_phase_start(self, phase_id: str) -> None:
        if self._stop_requested:
            return
        
        # Completar fase anterior si existe
        if self._current_phase_id is not None:
            actual_duration = time.time() - self._current_phase_start
            if actual_duration < self.min_phase_duration:
                delay = self.min_phase_duration - actual_duration
                time.sleep(delay)
            
            if not self._stop_requested:
                self.phase_completed.emit(self._current_phase_id)
        
        # Iniciar nueva fase
        self._current_phase_id = phase_id
        self._current_phase_start = time.time()
        self.phase_update.emit(phase_id)
    
    def run(self) -> None:
        try:
            # Importar dependencias aquí (evita imports circulares)
            from services.analysis_orchestrator import AnalysisOrchestrator
            from utils.settings_manager import settings_manager
            from services.result_types import FullAnalysisResult
            
            orchestrator = AnalysisOrchestrator()
            
            # Leer configuración
            precalculate_hashes = settings_manager.get_precalculate_hashes()
            
            # Ejecutar SOLO escaneo (Fase 1)
            self._handle_phase_start("scan")
            
            # 1. Escanear directorio
            scan_result = orchestrator.scan_directory(
                directory=self.directory,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                create_metadata_cache=True,
                precalculate_hashes=precalculate_hashes
            )
            
            # 2. Envolver en FullAnalysisResult para compatibilidad con UI
            result = FullAnalysisResult(
                directory=self.directory,
                scan=scan_result
                # Las demás fases se quedan en None
            )
            
            # Emitir estadísticas del scan
            self.stats_update.emit({
                'total': scan_result.total_files,
                'images': scan_result.image_count,
                'videos': scan_result.video_count,
                'others': scan_result.other_count
            })
            
            # Completar última fase
            if self._current_phase_id and not self._stop_requested:
                actual_duration = time.time() - self._current_phase_start
                if actual_duration < self.min_phase_duration:
                    time.sleep(self.min_phase_duration - actual_duration)
                
                if not self._stop_requested:
                    self.phase_completed.emit(self._current_phase_id)
            
            # Fase final: Finalizando análisis
            if not self._stop_requested:
                self._handle_phase_start("finalizing")
                time.sleep(self.min_phase_duration)
                if not self._stop_requested:
                    self.phase_completed.emit("finalizing")
            
            # Delay final antes de transición
            if not self._stop_requested:
                time.sleep(self.final_delay)
            
            # Emitir resultado final
            if not self._stop_requested:
                self.finished.emit(result)
                
                import gc
                del result
                del orchestrator
                gc.collect()

        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


# ============================================================================
# ON-DEMAND ANALYSIS WORKERS (STAGE 3)
# ============================================================================

class LivePhotoAnalysisWorker(BaseWorker):
    finished = pyqtSignal(object)
    
    def __init__(self, directory: Path, metadata_cache=None):
        super().__init__()
        self.directory = directory
        self.metadata_cache = metadata_cache
        
    def run(self):
        try:
            if self._stop_requested: return
            from services.live_photos_service import LivePhotoService, CleanupMode
            from services.result_types import LivePhotoDetectionResult
            
            service = LivePhotoService()
            cleanup_analysis = service.analyze(
                self.metadata_cache,
                cleanup_mode=CleanupMode.KEEP_IMAGE,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                directory=self.directory
            )
            
            result = LivePhotoDetectionResult(
                items_count=cleanup_analysis.items_count,
                groups=cleanup_analysis.groups,
                space_to_free=cleanup_analysis.space_to_free,
                bytes_total=cleanup_analysis.bytes_total
            )
            
            if not self._stop_requested:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class HeicAnalysisWorker(BaseWorker):
    finished = pyqtSignal(object)
    
    def __init__(self, directory: Path, metadata_cache=None):
        super().__init__()
        self.directory = directory
        self.metadata_cache = metadata_cache
        
    def run(self):
        try:
            if self._stop_requested: return
            from services.heic_service import HeicService
            service = HeicService()
            result = service.analyze(
                self.metadata_cache,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                directory=self.directory
            )
            if not self._stop_requested:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ExactDuplicatesAnalysisWorker(BaseWorker):
    finished = pyqtSignal(object)
    
    def __init__(self, directory: Path, metadata_cache=None):
        super().__init__()
        self.directory = directory
        self.metadata_cache = metadata_cache
        
    def run(self):
        try:
            if self._stop_requested: return
            from services.duplicates_exact_service import DuplicatesExactService
            service = DuplicatesExactService()
            result = service.analyze(
                self.metadata_cache,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                directory=self.directory
            )
            if not self._stop_requested:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ZeroByteAnalysisWorker(BaseWorker):
    finished = pyqtSignal(object)
    
    def __init__(self, directory: Path, metadata_cache=None):
        super().__init__()
        self.directory = directory
        self.metadata_cache = metadata_cache
        
    def run(self):
        try:
            if self._stop_requested: return
            from services.zero_byte_service import ZeroByteService
            service = ZeroByteService()
            result = service.analyze(
                directory=self.directory,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                metadata_cache=self.metadata_cache
            )
            if not self._stop_requested:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class RenamingAnalysisWorker(BaseWorker):
    finished = pyqtSignal(object)
    
    def __init__(self, directory: Path, metadata_cache=None):
        super().__init__()
        self.directory = directory
        self.metadata_cache = metadata_cache
        
    def run(self):
        try:
            if self._stop_requested: return
            from services.file_renamer_service import FileRenamer
            service = FileRenamer()
            result = service.analyze(
                directory=self.directory,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                metadata_cache=self.metadata_cache
            )
            if not self._stop_requested:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class OrganizationAnalysisWorker(BaseWorker):
    finished = pyqtSignal(object)
    
    def __init__(self, directory: Path, organization_type=None, metadata_cache=None):
        super().__init__()
        self.directory = directory
        self.organization_type = organization_type
        self.metadata_cache = metadata_cache
        
    def run(self):
        try:
            if self._stop_requested: return
            from services.file_organizer_service import FileOrganizer
            from services.file_organizer_service import OrganizationType
            
            service = FileOrganizer()
            
            org_type = self.organization_type
            if org_type is None:
                org_type = OrganizationType.TO_ROOT
            elif isinstance(org_type, str):
                org_type = OrganizationType(org_type)
                
            result = service.analyze(
                directory=self.directory,
                organization_type=org_type,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                metadata_cache=self.metadata_cache
            )
            if not self._stop_requested:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class DuplicatesSimilarAnalysisWorker(BaseWorker):
    """
    Worker para análisis inicial de archivos similares (perceptual hash).
    """
    finished = pyqtSignal(object)  # DuplicatesSimilarAnalysis
    
    def __init__(
        self,
        detector, # Type hint omitted to avoid circular import here
        workspace_path: Path
    ):
        super().__init__()
        self.detector = detector
        self.workspace_path = workspace_path
    
    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            def progress_callback(current: int, total: int, message: str) -> bool:
                if self._stop_requested:
                    return False
                self.progress_update.emit(current, total, message)
                return True
            
            # Importar tipo para type hint
            from services.duplicates_similar_service import DuplicatesSimilarAnalysis
            
            # Ejecutar análisis inicial (solo hashes)
            analysis = self.detector.analyze_initial(
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
