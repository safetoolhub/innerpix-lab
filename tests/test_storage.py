"""
Tests para verificar la abstracción de storage (backends de persistencia).
"""
import tempfile
from pathlib import Path

from utils.storage import StorageBackend, JsonStorageBackend, QSettingsBackend
from utils.settings_manager import SettingsManager


def test_json_storage_backend():
    """Verifica que JsonStorageBackend funciona correctamente"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test_settings.json"
        backend = JsonStorageBackend(file_path)
        
        # Test básico set/get
        backend.set("test/key", "value")
        assert backend.get("test/key") == "value"
        
        # Test con default
        assert backend.get("nonexistent", "default") == "default"
        
        # Test contains
        assert backend.contains("test/key")
        assert not backend.contains("nonexistent")
        
        # Test nested keys
        backend.set("app/config/theme", "dark")
        assert backend.get("app/config/theme") == "dark"
        
        # Test remove
        backend.remove("test/key")
        assert not backend.contains("test/key")
        
        # Test persistencia (cerrar y reabrir)
        backend2 = JsonStorageBackend(file_path)
        assert backend2.get("app/config/theme") == "dark"
        
        # Test clear
        backend2.clear()
        assert not backend2.contains("app/config/theme")


def test_qsettings_backend():
    """Verifica que QSettingsBackend funciona correctamente (requiere PyQt6)"""
    try:
        from PyQt6.QtCore import QCoreApplication
        import sys
        
        # QSettings requiere QCoreApplication
        if not QCoreApplication.instance():
            app = QCoreApplication(sys.argv)
        
        backend = QSettingsBackend("TestOrg", "TestApp")
        
        # Limpiar antes de test
        backend.clear()
        
        # Test básico set/get
        backend.set("test/key", "value")
        assert backend.get("test/key") == "value"
        
        # Test con default
        assert backend.get("nonexistent", "default") == "default"
        
        # Test contains
        assert backend.contains("test/key")
        assert not backend.contains("nonexistent")
        
        # Test nested keys
        backend.set("app/config/theme", "dark")
        assert backend.get("app/config/theme") == "dark"
        
        # Test remove
        backend.remove("test/key")
        assert not backend.contains("test/key")
        
        # Test clear
        backend.clear()
        assert not backend.contains("app/config/theme")
        
    except ImportError:
        print("⚠️  PyQt6 no disponible, saltando test de QSettingsBackend")
        return


def test_settings_manager_with_json_backend():
    """Verifica que SettingsManager funciona con JsonStorageBackend"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test_settings.json"
        backend = JsonStorageBackend(file_path)
        manager = SettingsManager(backend=backend)
        
        # Test métodos básicos
        manager.set("test_key", "test_value")
        assert manager.get("test_key") == "test_value"
        
        # Test get_bool
        manager.set("bool_key", True)
        assert manager.get_bool("bool_key") is True
        
        # Test get_int
        manager.set("int_key", 42)
        assert manager.get_int("int_key") == 42
        
        # Test get_path
        test_path = Path("/test/path")
        manager.set("path_key", str(test_path))
        assert manager.get_path("path_key") == test_path
        
        # Test métodos de conveniencia
        manager.set_auto_backup_enabled(False)
        assert manager.get_auto_backup_enabled() is False
        
        manager.set_log_level("DEBUG")
        assert manager.get_log_level() == "DEBUG"


def test_settings_manager_default_backend():
    """Verifica que SettingsManager usa backend automático correctamente"""
    manager = SettingsManager()
    
    # Debería usar QSettingsBackend si PyQt6 está disponible, sino JsonStorageBackend
    backend_type = type(manager.backend).__name__
    assert backend_type in ["QSettingsBackend", "JsonStorageBackend"]
    
    # Test que funciona independiente del backend
    test_key = "test/default_backend/key"
    manager.set(test_key, "value")
    assert manager.get(test_key) == "value"
    
    # Limpiar
    manager.remove(test_key)


if __name__ == "__main__":
    print("Ejecutando tests de storage...")
    test_json_storage_backend()
    print("✓ JsonStorageBackend funciona correctamente")
    
    test_qsettings_backend()
    print("✓ QSettingsBackend funciona correctamente")
    
    test_settings_manager_with_json_backend()
    print("✓ SettingsManager con JsonStorageBackend funciona correctamente")
    
    test_settings_manager_default_backend()
    print("✓ SettingsManager con backend automático funciona correctamente")
    
    print("\n✅ Todos los tests pasaron!")
