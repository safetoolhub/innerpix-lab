"""
Execution Workers for performing destructive/modification actions.
"""
from typing import TYPE_CHECKING, List, Optional
from pathlib import Path
from PyQt6.QtCore import pyqtSignal

from .base_worker import BaseWorker

if TYPE_CHECKING:
    from services.result_types import (
        RenameDeletionResult,
        RenameAnalysisResult,
        OrganizationDeletionResult,
        OrganizationAnalysisResult,
        LivePhotoCleanupDeletionResult,
        LivePhotoCleanupAnalysisResult,
        HeicDeletionResult,
        HeicAnalysisResult,
        DuplicateDeletionResult,
        ZeroByteDeletionResult
    )
    from services.file_renamer_service import FileRenamer
    from services.live_photos_service import LivePhotoService
    from services.file_organizer_service import FileOrganizer
    from services.heic_service import HeicService
    from services.duplicates_exact_service import DuplicatesExactService
    from services.duplicates_similar_service import DuplicatesSimilarService
    from services.zero_byte_service import ZeroByteService


class FileRenamerExecutionWorker(BaseWorker):
    """
    Worker para ejecutar renombrado de nombres de archivos
    """
    finished = pyqtSignal(object)  # RenameDeletionResult

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
            
            # Importar aquí para evitar circularidad real
            from services.result_types import RenameDeletionResult
            
            results = self.renamer.execute(
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


class LivePhotosExecutionWorker(BaseWorker):
    """
    Worker para ejecutar limpieza de Live Photos
    """
    finished = pyqtSignal(object)  # LivePhotoCleanupDeletionResult

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
            
            results = self.service.execute(
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


class FileOrganizerExecutionWorker(BaseWorker):
    """
    Worker para ejecutar organización de archivos
    """
    finished = pyqtSignal(object)  # OrganizationDeletionResult

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
            
            results = self.organizer.execute(
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


class HeicExecutionWorker(BaseWorker):
    """
    Worker para ejecutar eliminación de duplicados HEIC
    """
    finished = pyqtSignal(object)  # HeicDeletionResult

    def __init__(
        self,
        service: 'HeicService',
        analysis: 'HeicAnalysisResult',
        keep_format: str,
        create_backup: bool = True,
        dry_run: bool = False
    ):
        super().__init__()
        self.service = service  # Fixed assignment (was self.remover = remover)
        self.analysis = analysis
        self.keep_format = keep_format
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results = self.service.execute(
                self.analysis.duplicate_pairs,
                keep_format=self.keep_format,
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


class DuplicatesExecutionWorker(BaseWorker):
    """
    Worker para eliminación de duplicados
    """
    finished = pyqtSignal(object)  # DuplicateDeletionResult
    
    def __init__(
        self,
        detector: 'DuplicatesExactService | DuplicatesSimilarService',
        groups: List,
        keep_strategy: str,
        create_backup: bool = True,
        dry_run: bool = False,
        metadata_cache = None
    ):
        super().__init__()
        self.detector = detector
        self.groups = groups
        self.keep_strategy = keep_strategy
        self.create_backup = create_backup
        self.dry_run = dry_run
        self.metadata_cache = metadata_cache
    
    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results = self.detector.execute(
                self.groups,
                keep_strategy=self.keep_strategy,
                create_backup=self.create_backup,
                dry_run=self.dry_run,
                progress_callback=self._create_progress_callback(emit_numbers=True),
                metadata_cache=self.metadata_cache
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class ZeroByteExecutionWorker(BaseWorker):
    """
    Worker para eliminación de archivos de 0 bytes
    """
    finished = pyqtSignal(object)  # ZeroByteDeletionResult

    def __init__(
        self,
        service: 'ZeroByteService',
        files: List[Path],
        create_backup: bool = True,
        dry_run: bool = False
    ):
        super().__init__()
        self.service = service
        self.files = files
        self.create_backup = create_backup
        self.dry_run = dry_run

    def run(self) -> None:
        try:
            if self._stop_requested:
                return
            
            results = self.service.execute(
                self.files,
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
