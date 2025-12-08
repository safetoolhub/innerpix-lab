"""
Test to find if there are duplicates in the deletion plan
"""
import pytest
from pathlib import Path
from services.live_photos_service import LivePhotoService, CleanupMode
from collections import Counter


@pytest.mark.unit  
def test_massive_scenario_for_duplicates(temp_dir, create_test_image, create_test_video):
    """
    Try to reproduce a scenario where files are added multiple times to deletion list
    """
    # Create a complex scenario with many files
    for i in range(100):
        dir_path = temp_dir / f"dir{i}"
        dir_path.mkdir()
        
        # Some files with same name across directories
        if i % 3 == 0:
            mov = dir_path / "IMG_0037.MOV"
            heic = dir_path / "IMG_0037.HEIC"
            jpg = dir_path / "IMG_0037.jpg"
            
            create_test_video(mov, size_bytes=2048)
            create_test_image(heic, size=(100, 100), format='PNG')
            create_test_image(jpg, size=(100, 100), format='JPEG')
    
    # Analyze
    service = LivePhotoService()
    analysis = service.analyze(
        temp_dir,
        cleanup_mode=CleanupMode.KEEP_IMAGE,
        recursive=True
    )
    
    # Check for duplicates in deletion list
    paths_to_delete = [str(item['path']) for item in analysis.files_to_delete]
    path_counts = Counter(paths_to_delete)
    duplicates = {p: count for p, count in path_counts.items() if count > 1}
    
    print(f"\n=== STATISTICS ===")
    print(f"Total groups: {analysis.live_photos_found}")
    print(f"Files to delete: {len(analysis.files_to_delete)}")
    print(f"Unique paths: {len(set(paths_to_delete))}")
    print(f"Duplicates found: {len(duplicates)}")
    
    if duplicates:
        print(f"\n=== DUPLICATES ===")
        for path, count in list(duplicates.items())[:10]:  # Show first 10
            print(f"{path}: appears {count} times")
        
        assert False, f"Found {len(duplicates)} duplicate paths in deletion list!"
    
    assert len(paths_to_delete) == len(set(paths_to_delete)), "No duplicates should exist"
