"""
Worker threads para análisis y operaciones de larga duración.
Permite ejecutar tareas en background sin bloquear la UI.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from pathlib import Path
import time
from typing import Optional, Any

from config import Config
from .base_worker import BaseWorker
from services.result_types import ScanSnapshot


class AnalysisWorker(BaseWorker):
    """
    Worker for Stage 2: Initial Directory Scan ONLY.
    Emits simple object with scan result and directory.
    """
    finished = pyqtSignal(object)
    
    phase_update = pyqtSignal(str)  # phase_id
    phase_completed = pyqtSignal(str)  # phase_id
    phase_text_update = pyqtSignal(str, str)  # phase_id, new_text
    stats_update = pyqtSignal(object)  # Dict con estadísticas de scan
    partial_results = pyqtSignal(object)  # Dict[str, AnalysisResult]

    def __init__(self, directory: Path):
        super().__init__()
        self.directory = directory
        
        # Delay final antes de transición a Stage 3
        self.final_delay: float = Config.FINAL_DELAY_BEFORE_STAGE3_SECONDS
    
    def _create_scan_progress_callback(self):
        """
        Crea un callback personalizado para el escaneo que detecta
        las fases del DirectoryScanner y actualiza el texto de la fase.
        """
        def callback(current: int, total: int, message: str) -> bool:
            if self._stop_requested:
                return False
            
            try:
                # Actualizar el texto de la fase 'scan' según el mensaje
                self.phase_text_update.emit("scan", message)
                
                # Emitir progreso numérico
                self.progress_update.emit(current, total, message)
            except Exception:
                pass
            
            return not self._stop_requested
        
        return callback

    def run(self) -> None:
        try:
            # Importar dependencias aquí (evita imports circulares)
            from utils.settings_manager import settings_manager
            from services.directory_scanner import DirectoryScanner
            
            # Leer configuración
            precalculate_hashes = settings_manager.get_precalculate_hashes()
            
            # Ejecutar SOLO escaneo (Fase 1)
            self.phase_update.emit("scan")
            
            # 1. Escanear directorio directamente
            scanner = DirectoryScanner()
            scan_result = scanner.scan(
                directory=self.directory,
                progress_callback=self._create_scan_progress_callback(),
                use_file_info_repository=True,
                precalculate_hashes=precalculate_hashes
            )
            
            # 2. Crear snapshot simple con scan result y directory
            result = ScanSnapshot(
                directory=self.directory,
                scan=scan_result
            )
            
            # Emitir estadísticas del scan
            self.stats_update.emit({
                'total': scan_result.total_files,
                'images': scan_result.image_count,
                'videos': scan_result.video_count,
                'others': scan_result.other_count
            })
            
            # Completar fase de scan
            if not self._stop_requested:
                self.phase_completed.emit("scan")
            
            # Delay final antes de transición a Stage 3
            if not self._stop_requested:
                time.sleep(self.final_delay)
            
            # Emitir resultado final
            if not self._stop_requested:
                self.finished.emit(result)
                
                import gc
                del result
                gc.collect()

        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


# ============================================================================
# ON-DEMAND ANALYSIS WORKERS (STAGE 3)
# ============================================================================

class LivePhotosAnalysisWorker(BaseWorker):
    finished = pyqtSignal(object)
    
    def __init__(self, directory: Path, metadata_cache=None):
        super().__init__()
        self.directory = directory
        self.metadata_cache = metadata_cache
        
    def run(self):
        try:
            if self._stop_requested: return
            from services.live_photos_service import LivePhotoService, CleanupMode
            
            service = LivePhotoService()
            result = service.analyze(
                cleanup_mode=CleanupMode.KEEP_IMAGE,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                directory=self.directory
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
                progress_callback=self._create_progress_callback(emit_numbers=True),
                directory=self.directory
            )
            if not self._stop_requested:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DuplicatesExactAnalysisWorker(BaseWorker):
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


class FileRenamerAnalysisWorker(BaseWorker):
    finished = pyqtSignal(object)
    
    def __init__(self, directory: Path):
        super().__init__()
        self.directory = directory
        
    def run(self):
        try:
            if self._stop_requested: return
            from services.file_renamer_service import FileRenamer
            service = FileRenamer()
            result = service.analyze(
                directory=self.directory,
                progress_callback=self._create_progress_callback(emit_numbers=True)
            )
            if not self._stop_requested:
                self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class FileOrganizerAnalysisWorker(BaseWorker):
    """Worker para análisis de organización de archivos con opciones de agrupación"""
    finished = pyqtSignal(object)
    
    def __init__(
        self,
        directory: Path,
        organization_type=None,
        group_by_source: bool = False,
        group_by_type: bool = False,
        date_grouping_type: Optional[str] = None
    ):
        super().__init__()
        self.directory = directory
        self.organization_type = organization_type
        self.group_by_source = group_by_source
        self.group_by_type = group_by_type
        self.date_grouping_type = date_grouping_type
        
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
                group_by_source=self.group_by_source,
                group_by_type=self.group_by_type,
                date_grouping_type=self.date_grouping_type
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
        detector # Type hint omitted to avoid circular import here
    ):
        super().__init__()
        self.detector = detector
    
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
                progress_callback=progress_callback
            )
            
            if not self._stop_requested:
                self.finished.emit(analysis)
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)
