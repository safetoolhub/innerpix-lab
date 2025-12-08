"""
Test to reproduce the issue where multiple images share the same video
"""
import pytest
from pathlib import Path
from services.live_photos_service import LivePhotoService, CleanupMode


@pytest.mark.unit
class TestMultipleImagesShareVideo:
    """Test scenario: IMG_0037.MOV, IMG_0037.HEIC, IMG_0037.jpg"""
    
    def test_two_images_one_video_keep_image(self, temp_dir, create_test_image, create_test_video):
        """
        Reproduce reported issue: 
        - 3 files: IMG_0037.MOV, IMG_0037.HEIC, IMG_0037.jpg
        - KEEP_IMAGE mode should preserve BOTH images, delete video ONCE
        """
        # Create the scenario files
        heic = temp_dir / "IMG_0037.HEIC"
        jpg = temp_dir / "IMG_0037.jpg"  # Note: lowercase extension
        mov = temp_dir / "IMG_0037.MOV"
        
        create_test_image(heic, size=(100, 100), format='PNG')  # Mock HEIC
        create_test_image(jpg, size=(100, 100), format='JPEG')
        create_test_video(mov, size_bytes=2048)
        
        # Analyze with KEEP_IMAGE mode
        service = LivePhotoService()
        analysis = service.analyze(
            temp_dir,
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            recursive=False
        )
        
        # Should detect 2 groups (one for each image)
        assert analysis.live_photos_found == 2, f"Expected 2 groups, got {analysis.live_photos_found}"
        
        # Files to delete should contain the MOV only ONCE
        paths_to_delete = [str(item['path']) for item in analysis.files_to_delete]
        mov_count = paths_to_delete.count(str(mov))
        assert mov_count == 1, f"MOV should appear once in deletion list, found {mov_count} times"
        
        # Files to keep should contain BOTH images
        paths_to_keep = [str(item['path']) for item in analysis.files_to_keep]
        assert str(heic) in paths_to_keep, "HEIC should be kept"
        assert str(jpg) in paths_to_keep, "JPG should be kept"
        
        # Execute deletion (dry run first to test)
        result = service.execute(analysis, create_backup=False, dry_run=True)
        assert result.success
        assert result.simulated_files_deleted == 1, "Should delete exactly 1 file (the MOV)"
        
        # Execute for real (no backup to speed up test)
        result = service.execute(analysis, create_backup=False, dry_run=False)
        assert result.success
        assert result.files_deleted == 1, "Should delete exactly 1 file (the MOV)"
        assert len(result.errors) == 0, f"Should have no errors, got: {result.errors}"
        
        # Verify files still exist
        assert heic.exists(), "HEIC should still exist"
        assert jpg.exists(), "JPG should still exist" 
        assert not mov.exists(), "MOV should be deleted"
    
    def test_three_images_one_video_keep_image(self, temp_dir, create_test_image, create_test_video):
        """
        Even more extreme: 3 images sharing 1 video
        """
        # Create the scenario files
        heic = temp_dir / "IMG_0037.HEIC"
        jpg = temp_dir / "IMG_0037.JPG"
        jpeg = temp_dir / "IMG_0037.jpeg"
        mov = temp_dir / "IMG_0037.MOV"
        
        create_test_image(heic, size=(100, 100), format='PNG')
        create_test_image(jpg, size=(100, 100), format='JPEG')
        create_test_image(jpeg, size=(100, 100), format='JPEG')
        create_test_video(mov, size_bytes=2048)
        
        # Analyze
        service = LivePhotoService()
        analysis = service.analyze(
            temp_dir,
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            recursive=False
        )
        
        # Should detect 3 groups
        assert analysis.live_photos_found == 3
        
        # Files to delete should contain the MOV only ONCE
        paths_to_delete = [str(item['path']) for item in analysis.files_to_delete]
        mov_count = paths_to_delete.count(str(mov))
        assert mov_count == 1, f"MOV should appear once, found {mov_count} times"
        
        # Execute
        result = service.execute(analysis, create_backup=False, dry_run=False)
        assert result.success
        assert result.files_deleted == 1, "Should delete exactly 1 file"
        assert len(result.errors) == 0, f"Should have no errors, got: {result.errors}"
        
        # Verify
        assert heic.exists()
        assert jpg.exists()
        assert jpeg.exists()
        assert not mov.exists()
