#!/usr/bin/env python3
"""
Script CLI de demostración: usar funciones de platform sin PyQt6

Este script demuestra cómo las funciones de utils/platform_utils.py
pueden usarse en scripts CLI sin ninguna dependencia de UI.
"""
import sys
from pathlib import Path

# Asegurar que podemos importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar SOLO módulos de lógica - NO PyQt6
from utils.platform_utils import (
    open_file_with_default_app,
    open_folder_in_explorer,
    get_platform_info,
    is_linux,
    is_macos,
    is_windows,
    get_default_file_manager
)


def main():
    """Función principal del script CLI"""
    print("=" * 70)
    print("🚀 Demo: Funciones de Platform en CLI (SIN PyQt6)")
    print("=" * 70)
    print()
    
    # 1. Información de plataforma
    print("1️⃣  Información del Sistema")
    print("-" * 70)
    info = get_platform_info()
    print(f"   Sistema:        {info['system']}")
    print(f"   Versión:        {info['release']}")
    print(f"   Arquitectura:   {info['machine']}")
    print(f"   Procesador:     {info['processor']}")
    print()
    
    print(f"   Es Linux:       {is_linux()}")
    print(f"   Es macOS:       {is_macos()}")
    print(f"   Es Windows:     {is_windows()}")
    print()
    
    print(f"   Gestor archivos: {get_default_file_manager()}")
    print()
    
    # 2. Manejo de errores en CLI
    print("2️⃣  Manejo de Errores")
    print("-" * 70)
    
    def cli_error_handler(msg):
        """Handler de errores simple para CLI"""
        print(f"   ❌ Error: {msg}")
    
    # Intentar abrir archivo inexistente
    print("   Intentando abrir archivo inexistente...")
    result = open_file_with_default_app(
        Path("/tmp/nonexistent_file.txt"),
        error_callback=cli_error_handler
    )
    print(f"   Resultado: {result}")
    print()
    
    # 3. Abrir carpeta temporal
    print("3️⃣  Abrir Carpeta Temporal")
    print("-" * 70)
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        print(f"   Carpeta temporal: {temp_path}")
        
        # Crear algunos archivos de ejemplo
        (temp_path / "ejemplo1.txt").write_text("Contenido 1")
        (temp_path / "ejemplo2.txt").write_text("Contenido 2")
        (temp_path / "ejemplo3.txt").write_text("Contenido 3")
        
        print(f"   Archivos creados: 3")
        print()
        
        # Preguntar al usuario
        response = input("   ¿Abrir carpeta temporal en explorador? (s/n): ")
        
        if response.lower() == 's':
            result = open_folder_in_explorer(
                temp_path,
                error_callback=cli_error_handler
            )
            if result:
                print("   ✅ Carpeta abierta en explorador")
                input("   Presiona Enter para continuar (y limpiar la carpeta temporal)...")
            else:
                print("   ❌ No se pudo abrir la carpeta")
        else:
            print("   ⏭️  Saltado")
        print()
    
    # 4. Uso con callbacks personalizados
    print("4️⃣  Callbacks Personalizados")
    print("-" * 70)
    
    errors = []
    def custom_callback(msg):
        """Callback que acumula errores"""
        errors.append(msg)
    
    # Intentar varias operaciones
    operations = [
        Path("/tmp/fake1.txt"),
        Path("/tmp/fake2.txt"),
        Path("/tmp/fake3.txt"),
    ]
    
    for op in operations:
        open_file_with_default_app(op, error_callback=custom_callback)
    
    print(f"   Operaciones intentadas: {len(operations)}")
    print(f"   Errores capturados: {len(errors)}")
    print()
    
    # 5. Comparación con necesidades de PyQt6
    print("5️⃣  Comparación: CLI vs UI")
    print("-" * 70)
    print("   CLI (este script):")
    print("   ✅ NO requiere PyQt6")
    print("   ✅ NO requiere QApplication")
    print("   ✅ NO requiere QMessageBox")
    print("   ✅ Callbacks simples con print()")
    print("   ✅ Puede correr en servidores sin X11")
    print()
    print("   UI (dialog_utils.py):")
    print("   ✅ Usa las MISMAS funciones de platform_utils")
    print("   ✅ Solo añade wrappers con QMessageBox")
    print("   ✅ Separación limpia UI/lógica")
    print()
    
    # Resumen
    print("=" * 70)
    print("✅ DEMOSTRACIÓN COMPLETADA")
    print("=" * 70)
    print()
    print("💡 Conclusiones:")
    print("   • platform_utils.py es 100% independiente de UI")
    print("   • Funciones reutilizables en CLI y GUI")
    print("   • Callbacks flexibles para cualquier contexto")
    print("   • Logging integrado para debugging")
    print("   • Soporte multiplataforma robusto")
    print()
    print("🎯 Casos de uso:")
    print("   • Scripts CLI de automatización")
    print("   • Herramientas de línea de comandos")
    print("   • Tests sin entorno gráfico")
    print("   • Servidores y servicios backend")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
