"""
Tests para utils/platform_utils.py
"""
import pytest
from pathlib import Path
from utils.platform_utils import (
    is_linux,
    is_macos,
    is_windows,
    open_file_with_default_app,
    open_folder_in_explorer
)


@pytest.mark.unit
class TestPlatformDetection:
    """Tests para detección de plataforma"""
    
    def test_is_linux(self):
        """Test detección de Linux"""
        result = is_linux()
        assert isinstance(result, bool)
    
    def test_is_macos(self):
        """Test detección de macOS"""
        result = is_macos()
        assert isinstance(result, bool)
    
    def test_is_windows(self):
        """Test detección de Windows"""
        result = is_windows()
        assert isinstance(result, bool)
    
    def test_only_one_platform_true(self):
        """Test que solo una plataforma es verdadera"""
        platforms = [is_linux(), is_macos(), is_windows()]
        assert sum(platforms) == 1, "Exactamente una plataforma debe ser detectada"


@pytest.mark.unit
class TestOpenFile:
    """Tests para open_file_with_default_app"""
    
    def test_open_nonexistent_file_calls_error_callback(self):
        """Test que archivo inexistente llama error callback"""
        errors = []
        
        def error_callback(msg):
            errors.append(msg)
        
        nonexistent = Path("/nonexistent/file.txt")
        open_file_with_default_app(nonexistent, error_callback=error_callback)
        
        assert len(errors) > 0
    





@pytest.mark.unit
class TestOpenFolder:
    """Tests para open_folder_in_explorer"""
    
    def test_open_nonexistent_folder_calls_error_callback(self):
        """Test que carpeta inexistente llama error callback"""
        errors = []
        
        def error_callback(msg):
            errors.append(msg)
        
        nonexistent = Path("/nonexistent/folder")
        open_folder_in_explorer(nonexistent, error_callback=error_callback)
        
        assert len(errors) > 0
    

