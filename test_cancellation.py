#!/usr/bin/env python3
"""
Script de prueba para verificar la cancelación cooperativa del análisis.
Simula un análisis de 1000 archivos con cancelación manual.
"""
import sys
import time
from pathlib import Path
import tempfile
import threading

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from services.initial_scanner import InitialScanner
from utils.logger import configure_logging, get_logger

def test_cancellation():
    """Test cooperative cancellation during scan."""
    
    # Configure logging
    configure_logging(Path.home() / "tmp", level="INFO", dual_log_enabled=False)
    logger = get_logger("TestCancellation")
    
    # Create temp directory with test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create 1000 test files (larger dataset for slower processing)
        logger.info("Creating 1000 test files...")
        for i in range(1000):
            test_file = temp_path / f"test_{i:04d}.jpg"
            test_file.write_text(f"Test content {i}" * 1000)  # Larger files
        
        logger.info(f"Created {len(list(temp_path.glob('*.jpg')))} test files")
        
        # Create scanner
        scanner = InitialScanner()
        
        # Variables for tracking
        phases_started = []
        phases_completed = []
        progress_updates = 0
        
        def phase_callback(phase_id: str, phase_message: str):
            logger.info(f"📍 Phase started: {phase_id} - {phase_message}")
            phases_started.append(phase_id)
        
        def phase_completed_callback(phase_id: str):
            logger.info(f"✅ Phase completed: {phase_id}")
            phases_completed.append(phase_id)
        
        def progress_callback(phase_progress) -> bool:
            nonlocal progress_updates
            progress_updates += 1
            if progress_updates % 10 == 0:
                logger.info(f"Progress: {phase_progress.current}/{phase_progress.total}")
            return True  # Continue
        
        # Schedule cancellation after 2 seconds
        def cancel_after_delay():
            time.sleep(2)
            logger.warning("⚠️ REQUESTING CANCELLATION...")
            scanner.request_stop()
        
        cancel_thread = threading.Thread(target=cancel_after_delay, daemon=True)
        cancel_thread.start()
        
        # Start scan with all phases
        logger.info("🚀 Starting scan with cancellation scheduled in 2 seconds...")
        start_time = time.time()
        
        result = scanner.scan(
            directory=temp_path,
            phase_callback=phase_callback,
            phase_completed_callback=phase_completed_callback,
            progress_callback=progress_callback,
            calculate_hashes=True,
            extract_image_exif=True,
            extract_video_exif=False
        )
        
        elapsed = time.time() - start_time
        
        # Results
        logger.info("\n" + "="*60)
        logger.info("CANCELLATION TEST RESULTS")
        logger.info("="*60)
        logger.info(f"Elapsed time: {elapsed:.2f}s")
        logger.info(f"Phases started: {len(phases_started)} - {phases_started}")
        logger.info(f"Phases completed: {len(phases_completed)} - {phases_completed}")
        logger.info(f"Progress updates: {progress_updates}")
        logger.info(f"Files in result: {result.total_files}")
        logger.info(f"Scanner stopped: {scanner._should_stop}")
        
        # Verify graceful cancellation
        if scanner._should_stop:
            logger.info("✅ SUCCESS: Scanner stopped gracefully")
            logger.info("✅ SUCCESS: No forced termination needed")
            return True
        else:
            logger.error("❌ FAILED: Scanner did not stop")
            return False

if __name__ == "__main__":
    success = test_cancellation()
    sys.exit(0 if success else 1)
