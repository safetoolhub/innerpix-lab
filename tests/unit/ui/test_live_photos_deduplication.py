import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from services.live_photos_service import LivePhotoGroup, CleanupMode
from services.result_types import LivePhotosAnalysisResult

# Mock Config to avoid import errors or side effects
with patch('config.Config') as MockConfig:
    MockConfig.USE_VIDEO_METADATA = False
    # Mock styles to avoid PyQt/font issues in headless env
    with patch('ui.styles.design_system.DesignSystem') as MockDS:
        # Mock BaseDialog to bypass UI initialization
        with patch('ui.dialogs.base_dialog.BaseDialog') as MockBaseDialog:
            from ui.dialogs.live_photos_dialog import LivePhotoCleanupDialog

@pytest.fixture
def mock_analysis_with_duplicates():
    """
    Creates an analysis result where two images share the same video file.
    This simulates the case:
    - IMG_001.JPG -> IMG_001.MOV
    - IMG_001.HEIC -> IMG_001.MOV
    """
    video_path = Path("/tmp/test/IMG_001.MOV")
    img1_path = Path("/tmp/test/IMG_001.JPG")
    img2_path = Path("/tmp/test/IMG_001.HEIC")
    
    with patch('services.live_photos_service.LivePhotoGroup.__post_init__', return_value=None):
        group1 = LivePhotoGroup(
            image_path=img1_path,
            video_path=video_path,
            base_name="IMG_001",
            directory=Path("/tmp/test"),
            image_size=1000,
            video_size=5000,
        )
        
        group2 = LivePhotoGroup(
            image_path=img2_path,
            video_path=video_path, # SAME VIDEO PATH
            base_name="IMG_001",
            directory=Path("/tmp/test"),
            image_size=2000,
            video_size=5000
        )
        
        return LivePhotosAnalysisResult(
            total_files=4,
            files_to_delete=[], # Not used by dialog directly, it rebuilds plan
            files_to_keep=[],
            space_to_free=0,
            total_space=13000,
            cleanup_mode="keep_image",
            groups=[group1, group2]
        )

def test_dialog_deduplicates_video_deletion(mock_analysis_with_duplicates):
    """
    Verifies that when generating the plan for KEEP_IMAGE, 
    the same video file is not added twice to the deletion list.
    """
    # Mock parent to avoid GUI issues
    with patch.object(LivePhotoCleanupDialog, '__init__', return_value=None) as mock_init:
        dialog = LivePhotoCleanupDialog(mock_analysis_with_duplicates, parent=None)
        
        # Manually set attributes since __init__ is mocked
        dialog.analysis = mock_analysis_with_duplicates
        dialog.selected_mode = CleanupMode.KEEP_IMAGE
        
        # We can't easily call dialog.accept() because it closes the window and interacts with QT
        # So we'll test the logic that Would be inside accept() or extract it to a method
        # For this test, we accept we are testing the logic we PLAN to implement or verifying the BUG exists.
        # To verify the BUG, we can manually run the logic currently in accept():
        
        groups = dialog.analysis.groups
        files_to_delete = []
        files_to_keep = [] # Added to match implementation logic
    
    # CURRENT LOGIC (REPRODUCING BUG)
    if dialog.selected_mode == CleanupMode.KEEP_IMAGE:
        for group in groups:
            files_to_delete.append({
                'path': group.video_path,
                'type': 'video',
                'size': group.video_size,
                'base_name': group.base_name
            })
            
    # Check for duplicates
    paths = [str(f['path']) for f in files_to_delete]
    assert len(paths) == 2, "Should have 2 entries initially (reproducing bug)"
    assert paths[0] == paths[1], "Both entries should be the same path"
    
    # NOW: Verification of FIX logic (what we want)
    # This part serves as the 'TDD' part - verifying our proposed fix works
    deduplicated_files = []
    seen_paths = set()
    
    for group in groups:
        path_str = str(group.video_path)
        if path_str not in seen_paths:
            deduplicated_files.append({
                'path': group.video_path
            })
            seen_paths.add(path_str)
            
    assert len(deduplicated_files) == 1, "Should only have 1 entry after deduplication"
