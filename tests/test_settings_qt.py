"""
Script de prueba para verificar que SettingsManager funciona con PyQt6
"""
import sys
from pathlib import Path

# Asegurar que podemos importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication
from utils.settings_manager import SettingsManager
from utils.storage import QSettingsBackend

def main():
    # Crear aplicación Qt (necesaria para QSettings)
    app = QApplication(sys.argv)
    
    print("🔍 Probando SettingsManager con PyQt6...\n")
    
    # Test 1: Backend automático (debería usar QSettings)
    print("Test 1: Backend automático")
    manager = SettingsManager()
    backend_type = type(manager.backend).__name__
    print(f"  Backend detectado: {backend_type}")
    assert backend_type == "QSettingsBackend", f"Esperaba QSettingsBackend, obtuve {backend_type}"
    print("  ✅ Backend correcto\n")
    
    # Test 2: Escribir y leer configuración
    print("Test 2: Escribir y leer configuración")
    test_key = "test/pixaro_lab/verification"
    test_value = "Storage abstraction works!"
    
    manager.set(test_key, test_value)
    read_value = manager.get(test_key)
    print(f"  Escrito: {test_value}")
    print(f"  Leído:   {read_value}")
    assert read_value == test_value, "Los valores no coinciden"
    print("  ✅ Lectura/escritura correcta\n")
    
    # Test 3: Métodos de conveniencia
    print("Test 3: Métodos de conveniencia")
    manager.set_auto_backup_enabled(True)
    auto_backup = manager.get_auto_backup_enabled()
    print(f"  Auto backup: {auto_backup}")
    assert auto_backup is True
    print("  ✅ Métodos de conveniencia funcionan\n")
    
    # Test 4: get_bool con strings (compatibilidad QSettings)
    print("Test 4: Compatibilidad con strings de QSettings")
    manager.set("bool_test", "true")
    bool_value = manager.get_bool("bool_test")
    print(f"  String 'true' interpretado como: {bool_value}")
    assert bool_value is True
    print("  ✅ Conversión de strings correcta\n")
    
    # Limpiar
    manager.remove(test_key)
    manager.remove("bool_test")
    
    print("=" * 60)
    print("✅ TODOS LOS TESTS PASARON")
    print("=" * 60)
    print("\n💡 SettingsManager está completamente desacoplado de PyQt6")
    print("   pero funciona perfectamente con QSettingsBackend")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
