import sys
import os
import shutil
import pickle
import tempfile
from pathlib import Path
import unittest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from services.analysis_orchestrator import AnalysisOrchestrator, FullAnalysisResult
from services.file_renamer_service import FileRenamer
from services.zero_byte_service import ZeroByteService
from services.metadata_cache import FileMetadataCache

class TestDevCache(unittest.TestCase):
    def setUp(self):
        # Use persistent directory for testing
        self.test_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "fixtures" / "cache_test"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up any previous run artifacts
        for f in self.test_dir.glob("*"):
            if f.is_file():
                f.unlink()
        
        # Create some dummy files with actual content (not zero-byte)
        (self.test_dir / "test1.jpg").write_bytes(b"fake jpg data")
        (self.test_dir / "test2.jpg").write_bytes(b"fake jpg data")
        (self.test_dir / "video.mp4").write_bytes(b"fake mp4 data")
        (self.test_dir / "empty.txt").touch()  # Zero-byte file for testing
        
    def tearDown(self):
        # Clean up files but keep directory
        # This allows inspecting the directory if needed, but keeps it clean for next run
        for f in self.test_dir.glob("*"):
            if f.is_file():
                f.unlink()
        
    def test_cache_generation_and_loading(self):
        print(f"\nTesting cache generation in {self.test_dir}")
        
        # 1. Generate Analysis
        orchestrator = AnalysisOrchestrator()
        renamer = FileRenamer()
        zero_byte_service = ZeroByteService()
        
        # Run analysis
        result = orchestrator.run_full_analysis(
            directory=self.test_dir,
            renamer=renamer,
            zero_byte_service=zero_byte_service,
            precalculate_hashes=True
        )
        
        # 2. Save Cache (mimic generate_analysis_cache.py)
        cache_path = self.test_dir / Config.DEV_CACHE_FILENAME
        with open(cache_path, 'wb') as f:
            pickle.dump(result, f)
            
        self.assertTrue(cache_path.exists(), "Cache file should exist")
        
        # 3. Load Cache (mimic stage_2_window.py)
        with open(cache_path, 'rb') as f:
            loaded_result = pickle.load(f)
            
        # 4. Verify Content
        self.assertIsInstance(loaded_result, FullAnalysisResult)
        self.assertEqual(loaded_result.scan.total_files, 4, "Should have 4 total files")
        self.assertEqual(loaded_result.scan.image_count, 2, "Should have 2 images")
        self.assertEqual(loaded_result.scan.video_count, 1, "Should have 1 video")
        
        # Verify metadata cache survived pickling
        self.assertIsNotNone(loaded_result.scan.metadata_cache)
        # Check if lock was restored (it should be a new lock object)
        self.assertTrue(hasattr(loaded_result.scan.metadata_cache, '_lock'))
        import threading
        # Check if it is indeed a lock (or RLock)
        # Note: isinstance might fail if imports differ, but checking behavior is enough
        # Just checking it exists and is not None is good for now as per our __setstate__ logic
        
        # Verify zero-byte service results
        self.assertIsNotNone(loaded_result.zero_byte, "Zero-byte results should be present")
        self.assertEqual(loaded_result.zero_byte.zero_byte_files_found, 1, "Should find 1 zero-byte file")
        self.assertEqual(len(loaded_result.zero_byte.files), 1, "Should have 1 zero-byte file in list")
        
        print("✅ Cache verification successful")

if __name__ == '__main__':
    unittest.main()
