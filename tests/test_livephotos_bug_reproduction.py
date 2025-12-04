"""
Test to reproduce the ACTUAL bug reported by user.
User is certain files were NOT deleted externally.

Scenario: IMG_0037.MOV, IMG_0037.HEIC, IMG_0037.jpg in SAME directory
with recursive analysis and potentially subdirectories.
"""
import pytest
from pathlib import Path
from services.live_photos_service import LivePhotoService, CleanupMode


@pytest.mark.unit
class TestLivePhotosBugReproduction:
    """Reproduce exact user scenario with recursive analysis"""
    
    def test_exact_user_scenario_single_dir(self, temp_dir, create_test_image, create_test_video):
        """
        EXACT scenario from user: 3 files in same directory
        - IMG_0037.MOV
        - IMG_0037.HEIC  
        - IMG_0037.jpg (lowercase extension)
        
        User says this fails with "archivo no encontrado" error
        """
        # Create the EXACT scenario
        mov = temp_dir / "IMG_0037.MOV"
        heic = temp_dir / "IMG_0037.HEIC"
        jpg = temp_dir / "IMG_0037.jpg"  # lowercase
        
        create_test_video(mov, size_bytes=2048)
        create_test_image(heic, size=(100, 100), format='PNG')
        create_test_image(jpg, size=(100, 100), format='JPEG')
        
        # Analyze with RECURSIVE=False (single directory)
        service = LivePhotoService()
        analysis = service.analyze(
            temp_dir,
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            recursive=False
        )
        
        print(f"\n=== ANALYSIS RESULTS ===")
        print(f"Groups found: {analysis.live_photos_found}")
        print(f"Files to delete: {len(analysis.files_to_delete)}")
        print(f"Files to keep: {len(analysis.files_to_keep)}")
        
        # Print detailed plan
        print(f"\n=== DELETION PLAN ===")
        for i, item in enumerate(analysis.files_to_delete):
            print(f"{i+1}. DELETE: {item['path']} ({item['type']})")
        
        print(f"\n=== KEEP PLAN ===")
        for i, item in enumerate(analysis.files_to_keep):
            print(f"{i+1}. KEEP: {item['path']} ({item['type']})")
        
        # Execute and capture any errors
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        print(f"\n=== EXECUTION RESULTS ===")
        print(f"Success: {result.success}")
        print(f"Files deleted: {result.files_deleted}")
        print(f"Errors: {len(result.errors)}")
        if result.errors:
            for error in result.errors:
                print(f"  ERROR: {error}")
        
        # The bug would show up as errors
        assert result.success, f"Operation failed with errors: {result.errors}"
        assert len(result.errors) == 0, f"Got {len(result.errors)} errors: {result.errors}"
        assert result.files_deleted == 1, f"Expected 1 file deleted, got {result.files_deleted}"
        
        # Verify final state
        assert not mov.exists(), "MOV should be deleted"
        assert heic.exists(), "HEIC should exist"
        assert jpg.exists(), "jpg should exist"
    
    def test_user_scenario_with_subdirectories_recursive(self, temp_dir, create_test_image, create_test_video):
        """
        Test with RECURSIVE analysis and subdirectories
        Maybe the bug only appears with recursive analysis?
        """
        # Directory structure
        dir1 = temp_dir / "iPhoneC_hasta_202311"
        dir2 = temp_dir / "iPhoneC_hasta_202311" / "subdir"
        dir1.mkdir(parents=True)
        dir2.mkdir(parents=True)
        
        # Scenario 1: dir1 has IMG_0037.MOV + IMG_0037.HEIC + IMG_0037.jpg
        mov1 = dir1 / "IMG_0037.MOV"
        heic1 = dir1 / "IMG_0037.HEIC"
        jpg1 = dir1 / "IMG_0037.jpg"
        
        create_test_video(mov1, size_bytes=2048)
        create_test_image(heic1, size=(100, 100), format='PNG')
        create_test_image(jpg1, size=(100, 100), format='JPEG')
        
        # Scenario 2: subdir also has files with same name
        mov2 = dir2 / "IMG_0037.MOV"
        heic2 = dir2 / "IMG_0037.HEIC"
        
        create_test_video(mov2, size_bytes=2048)
        create_test_image(heic2, size=(100, 100), format='PNG')
        
        # Analyze with RECURSIVE=True
        service = LivePhotoService()
        analysis = service.analyze(
            temp_dir,
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            recursive=True
        )
        
        print(f"\n=== RECURSIVE ANALYSIS ===")
        print(f"Groups found: {analysis.live_photos_found}")
        print(f"Files to delete: {len(analysis.files_to_delete)}")
        
        # Print ALL deletion targets
        print(f"\n=== ALL FILES TO DELETE ===")
        for i, item in enumerate(analysis.files_to_delete):
            print(f"{i+1}. {item['path']} (type={item['type']}, base_name={item['base_name']})")
        
        # Check for duplicates
        paths = [str(item['path']) for item in analysis.files_to_delete]
        duplicates = [p for p in paths if paths.count(p) > 1]
        if duplicates:
            print(f"\n!!! DUPLICATE PATHS FOUND: {set(duplicates)}")
            assert False, f"Found duplicate paths in deletion list: {duplicates}"
        
        # Execute
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        print(f"\n=== EXECUTION ===")
        print(f"Success: {result.success}")
        print(f"Deleted: {result.files_deleted}")
        print(f"Errors: {len(result.errors)}")
        if result.errors:
            for error in result.errors:
                print(f"  ERROR: {error}")
        
        assert result.success, f"Failed: {result.errors}"
        assert len(result.errors) == 0, f"Errors: {result.errors}"
        
        # Both MOVs should be deleted, all images kept
        assert not mov1.exists()
        assert not mov2.exists()
        assert heic1.exists()
        assert jpg1.exists()
        assert heic2.exists()
    
    def test_log_all_groups_details(self, temp_dir, create_test_image, create_test_video):
        """
        Detailed logging of ALL groups to understand the internal state
        """
        # Create scenario
        mov = temp_dir / "IMG_0037.MOV"
        heic = temp_dir / "IMG_0037.HEIC"
        jpg = temp_dir / "IMG_0037.jpg"
        
        create_test_video(mov, size_bytes=2048)
        create_test_image(heic, size=(100, 100), format='PNG')
        create_test_image(jpg, size=(100, 100), format='JPEG')
        
        # Analyze
        service = LivePhotoService()
        analysis = service.analyze(
            temp_dir,
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            recursive=False
        )
        
        # Access internal groups
        print(f"\n=== INTERNAL GROUPS ===")
        for i, group in enumerate(analysis.groups):
            print(f"\nGroup {i+1}:")
            print(f"  image_path: {group.image_path}")
            print(f"  video_path: {group.video_path}")
            print(f"  base_name: {group.base_name}")
            print(f"  directory: {group.directory}")
            print(f"  Same video? {group.video_path}")
        
        # Check if video paths are same object
        video_paths = [str(g.video_path) for g in analysis.groups]
        print(f"\nAll video paths: {video_paths}")
        print(f"Unique video paths: {set(video_paths)}")
        print(f"Count of each: {[(p, video_paths.count(p)) for p in set(video_paths)]}")
