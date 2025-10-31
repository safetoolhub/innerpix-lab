"""
Script de demostración: usar SettingsManager sin PyQt6
Este script prueba que la lógica de configuración es completamente
independiente de la UI, permitiendo uso en CLI, tests, y scripts.
"""
import sys
from pathlib import Path
import tempfile

# Asegurar que podemos importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

# NO importar nada de PyQt6 - solo la capa de lógica
from utils.settings_manager import SettingsManager
from utils.storage import JsonStorageBackend

def simulate_cli_application():
    """Simula una aplicación CLI que usa configuración persistente"""
    print("=" * 60)
    print("🚀 DEMO: SettingsManager sin PyQt6")
    print("=" * 60)
    print()
    
    # Crear directorio temporal para settings
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "cli_app_settings.json"
        
        print(f"📁 Archivo de configuración: {settings_file}\n")
        
        # Crear SettingsManager con backend JSON (sin PyQt6)
        json_backend = JsonStorageBackend(settings_file)
        manager = SettingsManager(backend=json_backend)
        
        print("1️⃣  Guardando configuración...")
        manager.set_logs_directory(Path.home() / "logs")
        manager.set_backup_directory(Path.home() / "backups")
        manager.set_auto_backup_enabled(True)
        manager.set_log_level("DEBUG")
        
        # Configuración personalizada
        manager.set("cli/theme", "dark")
        manager.set("cli/verbose", True)
        manager.set("cli/max_threads", 8)
        
        print("   ✅ Configuración guardada\n")
        
        print("2️⃣  Leyendo configuración...")
        logs_dir = manager.get_logs_directory()
        backup_dir = manager.get_backup_directory()
        auto_backup = manager.get_auto_backup_enabled()
        log_level = manager.get_log_level()
        
        print(f"   📂 Logs:        {logs_dir}")
        print(f"   📂 Backups:     {backup_dir}")
        print(f"   💾 Auto backup: {auto_backup}")
        print(f"   📝 Log level:   {log_level}")
        print()
        
        print("3️⃣  Leyendo configuración personalizada...")
        theme = manager.get("cli/theme")
        verbose = manager.get_bool("cli/verbose")
        threads = manager.get_int("cli/max_threads")
        
        print(f"   🎨 Theme:    {theme}")
        print(f"   🔊 Verbose:  {verbose}")
        print(f"   ⚡ Threads:  {threads}")
        print()
        
        print("4️⃣  Verificando persistencia...")
        # Crear nueva instancia usando el mismo archivo
        manager2 = SettingsManager(backend=JsonStorageBackend(settings_file))
        
        assert manager2.get_log_level() == "DEBUG"
        assert manager2.get("cli/theme") == "dark"
        assert manager2.get_int("cli/max_threads") == 8
        
        print("   ✅ Persistencia verificada\n")
        
        print("5️⃣  Verificando contenido del archivo JSON...")
        with open(settings_file, 'r') as f:
            content = f.read()
        print(f"   {content}\n")
        
    print("=" * 60)
    print("✅ DEMOSTRACIÓN COMPLETA")
    print("=" * 60)
    print()
    print("💡 Conclusiones:")
    print("   • SettingsManager NO depende de PyQt6")
    print("   • Puede usarse en scripts CLI sin UI")
    print("   • Tests pueden correr sin entorno gráfico")
    print("   • Lógica de negocio completamente desacoplada")
    print()
    print("🎯 Beneficios:")
    print("   ✓ Tests más rápidos (sin inicializar Qt)")
    print("   ✓ Scripts CLI pueden usar configuración")
    print("   ✓ Fácil migrar a otros frameworks UI")
    print("   ✓ Mejor separación de responsabilidades")

if __name__ == "__main__":
    simulate_cli_application()
