
import pickle
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from services.live_photos_service import LivePhotoService, CleanupMode
from config import Config

def test_plan_generation():
    cache_path = Path('/home/ed/Pictures/RAW/.pixaro_analysis_cache.pkl')
    if not cache_path.exists():
        print(f"Cache file not found: {cache_path}")
        return

    print("Loading cache...")
    with open(cache_path, 'rb') as f:
        full_result = pickle.load(f)

    if not full_result.live_photos or not full_result.live_photos.groups:
        print("No live photo groups in cache.")
        return

    groups = full_result.live_photos.groups
    print(f"Loaded {len(groups)} live photo groups.")

    service = LivePhotoService()
    
    # Test KEEP_IMAGE mode (default)
    print("\nGenerating plan for KEEP_IMAGE...")
    plan = service._generate_cleanup_plan(groups, CleanupMode.KEEP_IMAGE)
    
    files_to_delete = [str(f['path']) for f in plan['files_to_delete']]
    unique_files = set(files_to_delete)
    
    print(f"Files to delete: {len(files_to_delete)}")
    print(f"Unique files: {len(unique_files)}")
    
    if len(files_to_delete) != len(unique_files):
        print(f"❌ DUPLICATES FOUND! Diff: {len(files_to_delete) - len(unique_files)}")
        from collections import Counter
        counts = Counter(files_to_delete)
        for p, c in counts.most_common(10):
            if c > 1:
                print(f"  {p}: {c} times")
    else:
        print("✅ No duplicates found in plan.")

if __name__ == "__main__":
    test_plan_generation()
