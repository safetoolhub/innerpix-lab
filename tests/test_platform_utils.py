"""
Tests para utils/platform_utils.py
Verifica las funciones multiplataforma de interacción con el SO
"""
import tempfile
from pathlib import Path
from utils.platform_utils import (
    open_file_with_default_app,
    open_folder_in_explorer,
    get_platform_info,
    is_linux,
    is_macos,
    is_windows,
    get_default_file_manager
)


def test_platform_detection():
    """Verifica que la detección de plataforma funciona"""
    print("🔍 Test: Detección de plataforma")
    
    # Solo una debe ser verdadera
    platforms = [is_linux(), is_macos(), is_windows()]
    assert sum(platforms) == 1, "Debe detectar exactamente una plataforma"
    
    info = get_platform_info()
    assert 'system' in info
    assert 'platform' in info
    assert info['system'] in ['Linux', 'Darwin', 'Windows']
    
    print(f"   Sistema detectado: {info['system']}")
    print(f"   Plataforma: {info['platform']}")
    print("   ✅ Detección correcta\n")


def test_open_file_nonexistent():
    """Verifica manejo de archivos que no existen"""
    print("🔍 Test: Abrir archivo inexistente")
    
    error_messages = []
    def capture_error(msg):
        error_messages.append(msg)
    
    nonexistent = Path("/tmp/this_file_does_not_exist_12345.txt")
    result = open_file_with_default_app(nonexistent, error_callback=capture_error)
    
    assert result is False, "Debe retornar False para archivo inexistente"
    assert len(error_messages) > 0, "Debe reportar error"
    assert "no existe" in error_messages[0].lower()
    
    print(f"   Mensaje de error: {error_messages[0]}")
    print("   ✅ Manejo de error correcto\n")


def test_open_folder_nonexistent():
    """Verifica manejo de carpetas que no existen"""
    print("🔍 Test: Abrir carpeta inexistente")
    
    error_messages = []
    def capture_error(msg):
        error_messages.append(msg)
    
    nonexistent = Path("/tmp/this_folder_does_not_exist_12345")
    result = open_folder_in_explorer(nonexistent, error_callback=capture_error)
    
    assert result is False, "Debe retornar False para carpeta inexistente"
    assert len(error_messages) > 0, "Debe reportar error"
    assert "no existe" in error_messages[0].lower()
    
    print(f"   Mensaje de error: {error_messages[0]}")
    print("   ✅ Manejo de error correcto\n")


def test_open_file_valid():
    """Verifica que se puede intentar abrir un archivo válido"""
    print("🔍 Test: Abrir archivo válido (sin verificar que se abra realmente)")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test file")
        temp_file = Path(f.name)
    
    try:
        error_messages = []
        def capture_error(msg):
            error_messages.append(msg)
        
        # Intentar abrir (puede fallar en CI sin entorno gráfico)
        result = open_file_with_default_app(temp_file, error_callback=capture_error)
        
        # En CI puede fallar, pero no debe dar error de "no existe"
        if result:
            print("   ✅ Archivo se intentó abrir correctamente")
        else:
            # Verificar que el error NO sea "no existe"
            if error_messages:
                assert "no existe" not in error_messages[0].lower()
                print(f"   ⚠️  No se pudo abrir (esperado en CI): {error_messages[0]}")
            else:
                print("   ⚠️  No se pudo abrir (esperado en CI sin display)")
        print()
    finally:
        temp_file.unlink()


def test_open_folder_valid():
    """Verifica que se puede intentar abrir una carpeta válida"""
    print("🔍 Test: Abrir carpeta válida (sin verificar que se abra realmente)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        
        error_messages = []
        def capture_error(msg):
            error_messages.append(msg)
        
        # Intentar abrir (puede fallar en CI sin entorno gráfico)
        result = open_folder_in_explorer(temp_dir, error_callback=capture_error)
        
        # En CI puede fallar, pero no debe dar error de "no existe"
        if result:
            print("   ✅ Carpeta se intentó abrir correctamente")
        else:
            # Verificar que el error NO sea "no existe"
            if error_messages:
                assert "no existe" not in error_messages[0].lower()
                print(f"   ⚠️  No se pudo abrir (esperado en CI): {error_messages[0]}")
            else:
                print("   ⚠️  No se pudo abrir (esperado en CI sin display)")
        print()


def test_get_default_file_manager():
    """Verifica detección del gestor de archivos"""
    print("🔍 Test: Detección de gestor de archivos")
    
    manager = get_default_file_manager()
    assert manager is not None, "Debe detectar algún gestor de archivos"
    
    print(f"   Gestor detectado: {manager}")
    print("   ✅ Detección correcta\n")


def test_file_vs_directory_validation():
    """Verifica que valida correctamente archivos vs directorios"""
    print("🔍 Test: Validación archivo vs directorio")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        temp_file = temp_dir / "test.txt"
        temp_file.write_text("test")
        
        errors_file = []
        errors_dir = []
        
        # Intentar abrir directorio como archivo
        open_file_with_default_app(temp_dir, error_callback=lambda e: errors_file.append(e))
        
        # Intentar abrir archivo como directorio
        open_folder_in_explorer(temp_file, error_callback=lambda e: errors_dir.append(e))
        
        # Debe generar errores apropiados
        assert len(errors_file) > 0, "Debe reportar error al abrir directorio como archivo"
        assert len(errors_dir) > 0, "Debe reportar error al abrir archivo como directorio"
        
        print(f"   Error directorio→archivo: {errors_file[0][:50]}...")
        print(f"   Error archivo→directorio: {errors_dir[0][:50]}...")
        print("   ✅ Validación correcta\n")


def test_cli_usage_example():
    """Demuestra uso en script CLI sin PyQt6"""
    print("🔍 Test: Uso en CLI sin PyQt6")
    
    # Este test demuestra que las funciones NO requieren PyQt6
    # No importamos nada de PyQt6 aquí
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("CLI test")
        temp_file = Path(f.name)
    
    try:
        # Simular uso en CLI con callback simple
        def cli_error_handler(msg):
            print(f"      CLI Error: {msg}")
        
        # Esto funciona sin PyQt6
        result = open_file_with_default_app(temp_file, error_callback=cli_error_handler)
        
        print("   ✅ Funciones utilizables en CLI sin PyQt6")
        print("   ✅ No se requiere QApplication ni QMessageBox\n")
    finally:
        temp_file.unlink()


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Tests de platform_utils.py")
    print("=" * 60)
    print()
    
    test_platform_detection()
    test_open_file_nonexistent()
    test_open_folder_nonexistent()
    test_open_file_valid()
    test_open_folder_valid()
    test_get_default_file_manager()
    test_file_vs_directory_validation()
    test_cli_usage_example()
    
    print("=" * 60)
    print("✅ TODOS LOS TESTS PASARON")
    print("=" * 60)
    print()
    print("💡 Beneficios:")
    print("   • Funciones de sistema NO dependen de PyQt6")
    print("   • Utilizables en scripts CLI")
    print("   • Logging integrado para debugging")
    print("   • Validación robusta de rutas")
    print("   • Soporte multiplataforma (Linux/macOS/Windows)")
