
import sys
import os
from pathlib import Path
import logging
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.file_metadata_repository_cache import FileInfoRepositoryCache
from services.duplicates_exact_service import DuplicatesExactService
from config import Config

def progress_callback(current, total, message):
    if current % 10000 == 0 or total == current:
        print(f"UI PROGRESS: [{current}/{total}] {message}")
    return True

def main():
    cache_path = Path("/home/ed/Documents/Innerpix_Lab/cache_saved/RAW.json")
    if not cache_path.exists():
        print(f"Error: Cache file {cache_path} not found")
        sys.exit(1)

    # Configure logging to console
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print(f"Loading cache from {cache_path}...")
    start_load = time.time()
    repo = FileInfoRepositoryCache.get_instance()
    loaded = repo.load_from_disk(cache_path, validate=False)
    print(f"Loaded {loaded} files from cache in {time.time() - start_load:.2f}s")
    
    print("\n--- Testing DuplicatesExactService (Performance Check) ---")
    dup_service = DuplicatesExactService()
    
    start_analyze = time.time()
    try:
        dup_service.analyze(progress_callback=progress_callback)
    except Exception as e:
        print(f"Dup Service Error: {e}")
        
    print(f"Analysis completed in {time.time() - start_analyze:.2f}s")

if __name__ == "__main__":
    main()
