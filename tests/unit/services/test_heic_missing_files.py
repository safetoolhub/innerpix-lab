
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from services.heic_service import HeicService, DuplicatePair
from services.result_types import HeicAnalysisResult

@pytest.mark.unit
class TestHeicServiceMissingFiles:
    """Tests specifically for handling missing files during execution."""

    def test_execute_skips_missing_files(self, temp_dir):
        """Test that if a file is missing during execution, it is skipped and not counted in stats."""
        # Setup: Create a duplicate pair but delete the file that should be deleted
        heic_path = temp_dir / 'missing.heic'
        jpg_path = temp_dir / 'missing.jpg'
        
        # Create ONLY the keep file
        jpg_path.write_text("keep")
        # heic_path (to delete) is missing
        
        # Construct DuplicatePair manually (bypassing validation which checks existence)
        # We simulate the file disappearing between analysis and execution
        pair = MagicMock(spec=DuplicatePair)
        pair.heic_path = heic_path
        pair.jpg_path = jpg_path
        pair.heic_size = 1000
        pair.jpg_size = 1000
        
        service = HeicService()
        
        # Create analysis result
        analysis = HeicAnalysisResult(
            success=True,
            errors=[],
            message="",
            items_count=1,
            bytes_total=2000,
            data={'duplicate_pairs': [pair], 'heic_files': [heic_path], 'jpg_files': [jpg_path], 'potential_savings_heic': 1000, 'potential_savings_jpg': 1000, 'potential_savings_total': 1000}
        )
        
        # Execute
        with patch.object(service.logger, 'warning') as mock_warning:
            result = service.execute(
                analysis,
                keep_format='jpg',
                create_backup=False, 
                dry_run=False
            )
            
            # Verify results
            assert result.success == True
            assert result.files_affected == 0  # Should NOT be counted
            assert result.bytes_processed == 0    # Should NOT be counted
            
            # Verify warning was logged
            mock_warning.assert_called_with(f"Archivo no encontrado durante eliminación: {heic_path}")

    def test_execute_skips_missing_files_dry_run(self, temp_dir):
        """Test missing file handling in dry-run mode."""
        heic_path = temp_dir / 'missing.heic'
        jpg_path = temp_dir / 'missing.jpg'
        jpg_path.write_text("keep")
        
        pair = MagicMock(spec=DuplicatePair)
        pair.heic_path = heic_path
        pair.jpg_path = jpg_path
        pair.heic_size = 1000
        pair.jpg_size = 1000
        
        service = HeicService()
        
        # Create analysis result
        analysis = HeicAnalysisResult(
            success=True,
            errors=[],
            message="",
            items_count=1,
            bytes_total=2000,
            data={'duplicate_pairs': [pair], 'heic_files': [heic_path], 'jpg_files': [jpg_path], 'potential_savings_heic': 1000, 'potential_savings_jpg': 1000, 'potential_savings_total': 1000}
        )
        
        with patch.object(service.logger, 'warning') as mock_warning:
            result = service.execute(
                analysis, 
                keep_format='jpg',
                create_backup=False, 
                dry_run=True
            )
            
            assert result.success == True
            assert result.items_processed == 0
            assert result.bytes_processed == 0
            
            mock_warning.assert_called_with(f"Archivo no encontrado durante eliminación: {heic_path}")
