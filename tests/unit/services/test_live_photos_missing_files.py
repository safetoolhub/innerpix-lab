
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from services.live_photos_service import LivePhotoService, CleanupMode, LivePhotosAnalysisResult

@pytest.mark.unit
class TestLivePhotosMissingFiles:
    """Tests specifically for handling missing files during execution."""

    def test_execute_skips_missing_files(self, temp_dir):
        """Test that if a file is missing during execution, it is skipped and not counted in stats."""
        # Setup: Create a fake analysis result
        video_path = temp_dir / 'missing.MOV'
        # We purposely do NOT create the file to simulate it being missing
        
        analysis = LivePhotosAnalysisResult(
            files_to_delete=[{
                'path': video_path,
                'size': 1000,
                'type': 'video'
            }],
            files_to_keep=[],
            space_to_free=1000,
            cleanup_mode=CleanupMode.KEEP_IMAGE.value
        )
        
        service = LivePhotoService()
        
        # Execute
        with patch.object(service.logger, 'warning') as mock_warning:
            result = service.execute(
                analysis, 
                create_backup=False, 
                dry_run=False
            )
            
            # Verify results
            assert result.success == True
            assert result.files_affected == 0  # Should NOT be counted
            assert result.bytes_processed == 0    # Should NOT be counted
            
            # Verify warning was logged
            mock_warning.assert_called_with(f"Archivo no encontrado durante eliminación: {video_path}")

    def test_execute_skips_missing_files_dry_run(self, temp_dir):
        """Test missing file handling in dry-run mode."""
        video_path = temp_dir / 'missing.MOV'
        
        analysis = LivePhotosAnalysisResult(
            files_to_delete=[{
                'path': video_path,
                'size': 1000,
                'type': 'video'
            }],
            files_to_keep=[],
            space_to_free=1000
        )
        
        service = LivePhotoService()
        
        with patch.object(service.logger, 'warning') as mock_warning:
            result = service.execute(
                analysis, 
                create_backup=False, 
                dry_run=True
            )
            
            assert result.success == True
            assert result.items_processed == 0
            assert result.bytes_processed == 0
            
            mock_warning.assert_called_with(f"[SIMULACIÓN] Archivo no encontrado durante eliminación: {video_path}")
