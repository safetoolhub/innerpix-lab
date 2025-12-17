
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from services.duplicates_base_service import DuplicateGroup
from services.duplicates_exact_service import DuplicatesExactService
from services.result_types import DuplicateAnalysisResult

@pytest.mark.unit
class TestBaseDetectorMissingFiles:
    """Tests specifically for handling missing files during execution in DuplicatesBaseService."""

    def test_execute_skips_missing_files(self, temp_dir):
        """Test that if a file is missing during execution, it is skipped and not counted in stats."""
        # Setup: Create a duplicate group with one missing file and one kept file
        missing_file = temp_dir / 'missing.jpg'
        keep_file = temp_dir / 'keep.jpg'
        keep_file.write_text("keep")
        
        # Create group
        group = DuplicateGroup(
            hash_value="abc",
            files=[missing_file, keep_file],
            total_size=2000
        )
        
        service = DuplicatesExactService()
        
        # Create analysis result
        analysis = DuplicateAnalysisResult(
            success=True,
            errors=[],
            message="",
            items_count=1,
            bytes_total=2000,
            data={'groups': [group], 'mode': 'exact', 'total_duplicates': 1, 'total_groups': 1, 'space_wasted': 2000}
        )
        
        # Execute
        with patch.object(service.logger, 'warning') as mock_warning:
            # We must enable strategy 'manual' or ensure select_file_to_keep picks the existing file
            # Let's use 'manual' and explicitly try to delete the missing file by ONLY passing the missing file in group?
            # Actually better: Use 'newest' strategy. "keep" file has mtime. missing file stat() will fail if we call it.
            # DuplicatesBaseService.execute calls _process_group_deletion.
            # _process_group_deletion calls select_file_to_keep.
            # select_file_to_keep CALLS stat() on files. If file is missing, IT WILL FAIL THERE before deletion logic.
            
            # WAIT. If keys are missing during selection, that IS an error.
            # The scenario "file disappears" usually happens AFTER selection, or if we use manual strategy.
            # Let's trigger the "deletion loop" logic by using 'manual' which deletes ALL files in group.
            
            result = service.execute(
                analysis,
                keep_strategy='manual', 
                create_backup=False, 
                dry_run=False
            )
            
            # Verify results
            assert result.success == True
            assert result.files_affected == 1 # The keep_file WAS deleted (manual mode deletes all)
            # wait, I wanted to keep one. 
            # In manual mode, it iterates all.
            # missing_file -> triggers warning, continue
            # keep_file -> deleted, count += 1
            
            # So total deleted should be 1 (the existing one), not 2.
            assert result.files_deleted == 1
            
            # Verify warning was logged for missing file
            mock_warning.assert_called_with(f"Archivo no encontrado durante eliminación: {missing_file}")

    def test_execute_skips_missing_files_dry_run(self, temp_dir):
        """Test missing file handling in dry-run mode."""
        missing_file = temp_dir / 'missing.jpg'
        
        group = DuplicateGroup(
            hash_value="abc",
            files=[missing_file],
            total_size=1000
        )
        
        service = DuplicatesExactService()
        
        # Create analysis result
        analysis = DuplicateAnalysisResult(
            success=True,
            errors=[],
            message="",
            items_count=1,
            bytes_total=1000,
            data={'groups': [group], 'mode': 'exact', 'total_duplicates': 1, 'total_groups': 1, 'space_wasted': 1000}
        )
        
        with patch.object(service.logger, 'warning') as mock_warning:
            result = service.execute(
                analysis,
                keep_strategy='manual',
                create_backup=False, 
                dry_run=True
            )
            
            assert result.success == True
            assert result.items_processed == 0
            
            mock_warning.assert_called_with(f"Archivo no encontrado durante eliminación: {missing_file}")
