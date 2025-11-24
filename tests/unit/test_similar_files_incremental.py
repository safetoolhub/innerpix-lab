import unittest
import unittest.mock
import sys
import os
from pathlib import Path
import imagehash
import numpy as np
from PIL import Image

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.similar_files_detector import SimilarFilesAnalysis

class TestSimilarFilesIncremental(unittest.TestCase):
    def setUp(self):
        self.analysis = SimilarFilesAnalysis()
        
    def _create_hash(self, seed=0):
        # Create a deterministic hash
        arr = np.full((8, 8), seed % 2, dtype=bool)
        return imagehash.ImageHash(arr)

    @unittest.mock.patch('pathlib.Path.stat')
    def test_find_new_groups_cross_batch(self, mock_stat):
        """Test finding duplicates where one file is in existing and one in new batch"""
        # Mock stat to return dummy size
        mock_stat_result = unittest.mock.MagicMock()
        mock_stat_result.st_size = 100
        mock_stat.return_value = mock_stat_result
        
        # Hash A (seed 0)
        hash_a = self._create_hash(0)
        
        # Existing hashes: File 1 has Hash A
        existing_hashes = {
            '/tmp/file1.jpg': {'hash': hash_a, 'size': 100, 'modified': 0}
        }
        
        # New hashes: File 2 has Hash A (duplicate of File 1)
        new_hashes = {
            '/tmp/file2.jpg': {'hash': hash_a, 'size': 100, 'modified': 0}
        }
        
        result = self.analysis.find_new_groups(new_hashes, existing_hashes, sensitivity=100)
        
        self.assertEqual(len(result.groups), 1)
        group = result.groups[0]
        self.assertEqual(len(group.files), 2)
        
        # Verify both files are in the group
        filenames = [f.name for f in group.files]
        self.assertIn('file1.jpg', filenames)
        self.assertIn('file2.jpg', filenames)

    @unittest.mock.patch('pathlib.Path.stat')
    def test_find_new_groups_within_batch(self, mock_stat):
        """Test finding duplicates where both files are in the new batch"""
        # Mock stat to return dummy size
        mock_stat_result = unittest.mock.MagicMock()
        mock_stat_result.st_size = 100
        mock_stat.return_value = mock_stat_result
        
        hash_b = self._create_hash(1)
        
        existing_hashes = {}
        
        new_hashes = {
            '/tmp/file3.jpg': {'hash': hash_b, 'size': 100, 'modified': 0},
            '/tmp/file4.jpg': {'hash': hash_b, 'size': 100, 'modified': 0}
        }
        
        result = self.analysis.find_new_groups(new_hashes, existing_hashes, sensitivity=100)
        
        self.assertEqual(len(result.groups), 1)
        group = result.groups[0]
        self.assertEqual(len(group.files), 2)
        filenames = [f.name for f in group.files]
        self.assertIn('file3.jpg', filenames)
        self.assertIn('file4.jpg', filenames)

if __name__ == '__main__':
    unittest.main()
