import sys
import os
from pathlib import Path
import random
import string
import imagehash
import numpy as np
from PIL import Image
from PyQt6.QtWidgets import QApplication
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from config import Config
from services.similar_files_detector import SimilarFilesAnalysis
from ui.dialogs.similar_files_dialog import SimilarFilesDialog
from ui.styles.design_system import DesignSystem

def create_dummy_hashes(count=16000):
    print(f"Generating {count} dummy hashes...")
    hashes = {}
    
    # Base hash
    base_hash = imagehash.phash(Image.new('RGB', (100, 100), color='red'))
    
    for i in range(count):
        # Create a fake path
        path = f"/tmp/dummy_file_{i}.jpg"
        
        # Create a hash that is slightly different or same
        # 80% unique, 20% similar
        if i % 5 == 0:
            # Similar to base
            h = base_hash
        else:
            # Random hash
            # imagehash objects are wrapped numpy arrays
            # We can just generate random bits
            arr = np.random.randint(0, 2, (8, 8), dtype=bool)
            h = imagehash.ImageHash(arr)
            
        hashes[path] = {
            'hash': h,
            'size': 1024 * 1024, # 1MB
            'modified': datetime.now().timestamp()
        }
        
    return hashes

def main():
    app = QApplication(sys.argv)
    # DesignSystem.initialize()
    
    print("Creating analysis object...")
    analysis = SimilarFilesAnalysis()
    analysis.perceptual_hashes = create_dummy_hashes(16172)
    analysis.workspace_path = "/tmp"
    analysis.total_files = len(analysis.perceptual_hashes)
    analysis.analysis_timestamp = datetime.now()
    
    print(f"Analysis created with {analysis.total_files} files.")
    
    print("Opening dialog...")
    dialog = SimilarFilesDialog(analysis)
    dialog.show()
    
    print("Dialog shown. Waiting for crash...")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
