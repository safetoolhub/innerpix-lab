"""
Initial Analysis Worker - QThread worker for Stage 2.

Executes the initial multi-phase directory scan in background without blocking the UI.
"""

from PyQt6.QtCore import pyqtSignal
from pathlib import Path
import time

from config import Config
from ui.workers.base_worker import BaseWorker
from services.result_types import ScanSnapshot
from services.initial_scanner import InitialScanner, PhaseProgress


class InitialAnalysisWorker(BaseWorker):
    """
    Worker for Stage 2: Multi-phase Initial Directory Scan.
    
    Emits signals for:
    - Phase transitions (phase_started, phase_completed)
    - Progress updates within each phase
    - Scan statistics
    - Final result (ScanSnapshot)
    """
    
    # Signals
    finished = pyqtSignal(object)  # ScanSnapshot
    phase_started = pyqtSignal(str, str)  # phase_id, phase_message
    phase_completed = pyqtSignal(str)  # phase_id
    stats_update = pyqtSignal(object)  # Dict with scan statistics
    
    def __init__(self, directory: Path):
        super().__init__()
        self.directory = directory
        self.scanner = None
        
        # Delay before transitioning to Stage 3
        self.final_delay: float = Config.FINAL_DELAY_BEFORE_STAGE3_SECONDS
    
    def stop(self):
        """Stop the worker gracefully."""
        super().stop()
        if self.scanner:
            self.scanner.request_stop()
    
    def run(self) -> None:
        """Execute the initial scan in background."""
        try:
            # Lazy import to avoid circular dependencies
            from utils.settings_manager import settings_manager
            
            # Read configuration for what to extract
            precalculate_hashes = settings_manager.get_precalculate_hashes()
            
            # Create scanner
            self.scanner = InitialScanner()
            
            # Define phase callback
            def phase_callback(phase_id: str, phase_message: str):
                """Called when a new phase starts."""
                if not self._stop_requested:
                    self.phase_started.emit(phase_id, phase_message)
            
            # Define progress callback
            def progress_callback(phase_progress: PhaseProgress) -> bool:
                """Called for progress updates within a phase."""
                if self._stop_requested:
                    return False
                
                # Emit progress signal
                self.progress_update.emit(
                    phase_progress.current,
                    phase_progress.total,
                    phase_progress.message
                )
                
                return True
            
            # Execute multi-phase scan
            scan_result = self.scanner.scan(
                directory=self.directory,
                phase_callback=phase_callback,
                progress_callback=progress_callback,
                calculate_hashes=precalculate_hashes,
                extract_image_exif=True,
                extract_video_exif=True
            )
            
            if self._stop_requested:
                return
            
            # Emit phase completions (for phases that were executed)
            if precalculate_hashes:
                self.phase_completed.emit(InitialScanner.PHASE_HASH)
            
            if scan_result.image_count > 0:
                self.phase_completed.emit(InitialScanner.PHASE_EXIF_IMAGES)
            
            if scan_result.video_count > 0:
                self.phase_completed.emit(InitialScanner.PHASE_EXIF_VIDEOS)
            
            # Create snapshot with scan result
            result = ScanSnapshot(
                directory=self.directory,
                scan=scan_result
            )
            
            # Emit scan statistics
            self.stats_update.emit({
                'total': scan_result.total_files,
                'images': scan_result.image_count,
                'videos': scan_result.video_count,
                'others': scan_result.other_count
            })
            
            # Final delay before transitioning to Stage 3
            if not self._stop_requested:
                time.sleep(self.final_delay)
            
            # Emit final result
            if not self._stop_requested:
                self.finished.emit(result)
                
                # Clean up to free memory
                import gc
                del result
                gc.collect()
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)
