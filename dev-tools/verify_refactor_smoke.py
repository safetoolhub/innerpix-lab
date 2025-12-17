
import sys
import os
from pathlib import Path
import logging
import shutil
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.analysis_orchestrator import AnalysisOrchestrator
from services.file_metadata_repository_cache import FileInfoRepositoryCache
from services.duplicates_exact_service import DuplicatesExactService
from services.zero_byte_service import ZeroByteService
from config import Config

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmokeTest")

def create_test_environment(base_dir: Path):
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True)
    
    # Create some test files
    (base_dir / "file1.jpg").write_text("content1")
    (base_dir / "file2.jpg").write_text("content1") # Duplicate content (exact)
    (base_dir / "file3.png").write_text("content2")
    (base_dir / "empty.txt").write_text("") # Zero byte
    
    # Create subfolder
    sub = base_dir / "subdir"
    sub.mkdir()
    (sub / "file4.jpg").write_text("content3")

def run_smoke_test():
    test_dir = Path("./smoke_test_data").absolute()
    create_test_environment(test_dir)
    
    logger.info(f"Created test environment at {test_dir}")
    
    orchestrator = AnalysisOrchestrator()
    
    # Callbacks
    def on_progress(current, total, message):
        print(f"PROGRESS: [{current}/{total}] {message}")
        return True
        
    def on_phase(phase_name):
        print(f"PHASE: {phase_name}")
        
    try:
        logger.info("Starting Orchestrator Full Analysis...")
        
        # Instantiate services to test integration
        duplicates_service = DuplicatesExactService()
        zero_byte_service = ZeroByteService()
        
        result = orchestrator.run_full_analysis(
            directory=test_dir,
            duplicate_exact_detector=duplicates_service,
            zero_byte_service=zero_byte_service,
            progress_callback=on_progress,
            phase_callback=on_phase
        )
        
        logger.info("Analysis finished successfully.")

        print("COMPLETED!")
        print(f"Files found: {result.scan.total_files}")
        print(f"Zero byte files: {len(result.zero_byte.files)}")
        
        # Validation
        # if result.success:
        #     logger.info("✅ Result success is True")
        # else:
        #     logger.error(f"❌ Result success is False: {result.errors}")
            
        if result.scan.total_files == 5:
             logger.info("✅ Total files count correct (5)")
        else:
             logger.error(f"❌ Total files count incorrect: {result.scan.total_files}")

        if result.zero_byte and len(result.zero_byte.files) == 1:
             logger.info("✅ Zero byte files detection correct (1)")
        else:
             logger.error(f"❌ Zero byte files detection incorrect: {len(result.zero_byte.files) if result.zero_byte else 'None'}")
             
    except Exception as e:
        logger.exception("❌ Smoke test failed with exception")
        sys.exit(1)
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    run_smoke_test()
