"""
Tests para utils/callback_utils.py
"""
import pytest
from utils.callback_utils import safe_progress_callback, create_safe_callback


@pytest.mark.unit
class TestSafeProgressCallback:
    """Tests para safe_progress_callback()"""
    
    def test_callback_executed(self):
        """Test que el callback se ejecuta correctamente"""
        results = []
        
        def callback(current, total, message):
            results.append((current, total, message))
        
        result = safe_progress_callback(callback, 50, 100, "Processing")
        
        assert result is True
        assert len(results) == 1
        assert results[0] == (50, 100, "Processing")
    
    def test_callback_returns_false(self):
        """Test que si callback retorna False, se propaga"""
        def callback(current, total, message):
            return False
        
        result = safe_progress_callback(callback, 50, 100, "Processing")
        
        assert result is False
    
    def test_callback_none(self):
        """Test que None callback no causa error"""
        result = safe_progress_callback(None, 50, 100, "Processing")
        
        assert result is True
    
    def test_callback_raises_exception(self):
        """Test que excepciones en callback no se propagan"""
        def callback(current, total, message):
            raise ValueError("Test error")
        
        # No debe lanzar excepción
        result = safe_progress_callback(callback, 50, 100, "Processing")
        
        assert result is True  # Continúa el proceso


@pytest.mark.unit
class TestCreateSafeCallback:
    """Tests para create_safe_callback()"""
    
    def test_creates_safe_wrapper(self):
        """Test que crea un wrapper seguro"""
        results = []
        
        def callback(current, total, message):
            results.append((current, total, message))
        
        safe_cb = create_safe_callback(callback)
        result = safe_cb(75, 100, "Done")
        
        assert result is True
        assert len(results) == 1
        assert results[0] == (75, 100, "Done")
    
    def test_wrapper_with_none(self):
        """Test que wrapper con None callback funciona"""
        safe_cb = create_safe_callback(None)
        result = safe_cb(50, 100, "Processing")
        
        assert result is True
    
    def test_wrapper_propagates_false(self):
        """Test que wrapper propaga False correctamente"""
        def callback(current, total, message):
            return False
        
        safe_cb = create_safe_callback(callback)
        result = safe_cb(50, 100, "Processing")
        
        assert result is False
    
    def test_wrapper_handles_exceptions(self):
        """Test que wrapper maneja excepciones"""
        def callback(current, total, message):
            raise RuntimeError("Test error")
        
        safe_cb = create_safe_callback(callback)
        # No debe lanzar excepción
        result = safe_cb(50, 100, "Processing")
        
        assert result is True
