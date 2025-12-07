#!/usr/bin/env python3
"""
Script de prueba manual para rotación de logs por tamaño.

Prueba dos escenarios:
1. Backups ilimitados (backupCount=0)
2. Backups limitados (backupCount=5)
"""
from pathlib import Path
import sys
import tempfile
import shutil

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import logger
from config import Config


def test_unlimited_backups():
    """Prueba rotación con backups ilimitados"""
    print("\n" + "=" * 80)
    print("TEST 1: Backups ilimitados (backupCount=0)")
    print("=" * 80)
    
    # Crear directorio temporal
    test_dir = Path(tempfile.mkdtemp(prefix="pixaro_log_test_unlimited_"))
    print(f"📁 Directorio de prueba: {test_dir}")
    
    # Configuración: 10 KB por archivo, backups ilimitados
    original_size = Config.MAX_LOG_FILE_SIZE_MB
    original_count = Config.MAX_LOG_BACKUP_COUNT
    
    Config.MAX_LOG_FILE_SIZE_MB = 0.01  # 10 KB para testing rápido
    Config.MAX_LOG_BACKUP_COUNT = 0  # Ilimitado
    
    try:
        # Configurar logging
        log_file, _ = logger.configure_logging(
            logs_dir=test_dir,
            level="INFO",
            dual_log_enabled=False
        )
        
        print(f"📝 Archivo principal: {log_file.name}")
        print(f"⚙️  Configuración: {Config.MAX_LOG_FILE_SIZE_MB} MB max, backups ilimitados")
        
        # Crear logger de prueba
        test_logger = logger.get_logger("UnlimitedTest")
        
        # Escribir suficientes mensajes para crear múltiples rotaciones
        print("\n✍️  Escribiendo mensajes...")
        long_message = "X" * 100  # ~100 bytes por mensaje
        for i in range(500):  # Forzar ~10+ rotaciones
            test_logger.info(f"Test message {i}: {long_message}")
            if i % 100 == 0 and i > 0:
                print(f"   {i} mensajes escritos...")
        
        print(f"✅ {500} mensajes escritos")
        
        # Listar archivos creados
        log_files = sorted(test_dir.glob("*.log*"))
        backup_files = sorted(test_dir.glob("*.log.*"))
        
        print(f"\n📊 Resultados:")
        print(f"   Total de archivos: {len(log_files)}")
        print(f"   Archivos de backup: {len(backup_files)}")
        print(f"\n📄 Archivos creados:")
        for f in log_files:
            size_kb = f.stat().st_size / 1024
            print(f"   - {f.name} ({size_kb:.2f} KB)")
        
        # Verificación
        if len(backup_files) >= 10:
            print(f"\n✅ ÉXITO: Se crearon {len(backup_files)} backups (ilimitados)")
            return True
        else:
            print(f"\n⚠️  ADVERTENCIA: Solo se crearon {len(backup_files)} backups (esperados 10+)")
            return False
            
    finally:
        # Restaurar configuración
        Config.MAX_LOG_FILE_SIZE_MB = original_size
        Config.MAX_LOG_BACKUP_COUNT = original_count
        
        # Limpiar
        print(f"\n🧹 Limpiando directorio temporal...")
        shutil.rmtree(test_dir, ignore_errors=True)


def test_limited_backups():
    """Prueba rotación con backups limitados a 5"""
    print("\n" + "=" * 80)
    print("TEST 2: Backups limitados (backupCount=5)")
    print("=" * 80)
    
    # Crear directorio temporal
    test_dir = Path(tempfile.mkdtemp(prefix="pixaro_log_test_limited_"))
    print(f"📁 Directorio de prueba: {test_dir}")
    
    # Configuración: 10 KB por archivo, máximo 5 backups
    original_size = Config.MAX_LOG_FILE_SIZE_MB
    original_count = Config.MAX_LOG_BACKUP_COUNT
    
    Config.MAX_LOG_FILE_SIZE_MB = 0.01  # 10 KB
    Config.MAX_LOG_BACKUP_COUNT = 5  # Límite de 5
    
    try:
        # Configurar logging
        log_file, _ = logger.configure_logging(
            logs_dir=test_dir,
            level="INFO",
            dual_log_enabled=False
        )
        
        print(f"📝 Archivo principal: {log_file.name}")
        print(f"⚙️  Configuración: {Config.MAX_LOG_FILE_SIZE_MB} MB max, máximo {Config.MAX_LOG_BACKUP_COUNT} backups")
        
        # Crear logger de prueba
        test_logger = logger.get_logger("LimitedTest")
        
        # Escribir suficientes mensajes para crear más de 5 rotaciones
        print("\n✍️  Escribiendo mensajes...")
        long_message = "X" * 100
        for i in range(500):  # Forzar ~10 rotaciones
            test_logger.info(f"Test message {i}: {long_message}")
            if i % 100 == 0 and i > 0:
                print(f"   {i} mensajes escritos...")
        
        print(f"✅ {500} mensajes escritos")
        
        # Listar archivos creados
        log_files = sorted(test_dir.glob("*.log*"))
        backup_files = sorted(test_dir.glob("*.log.*"))
        
        print(f"\n📊 Resultados:")
        print(f"   Total de archivos: {len(log_files)}")
        print(f"   Archivos de backup: {len(backup_files)}")
        print(f"\n📄 Archivos creados:")
        for f in log_files:
            size_kb = f.stat().st_size / 1024
            print(f"   - {f.name} ({size_kb:.2f} KB)")
        
        # Verificación
        if len(backup_files) <= 5:
            print(f"\n✅ ÉXITO: Se mantuvieron {len(backup_files)} backups (máximo 5)")
            return True
        else:
            print(f"\n❌ ERROR: Se encontraron {len(backup_files)} backups (máximo esperado: 5)")
            return False
            
    finally:
        # Restaurar configuración
        Config.MAX_LOG_FILE_SIZE_MB = original_size
        Config.MAX_LOG_BACKUP_COUNT = original_count
        
        # Limpiar
        print(f"\n🧹 Limpiando directorio temporal...")
        shutil.rmtree(test_dir, ignore_errors=True)


def main():
    """Ejecutar ambos tests"""
    print("\n🧪 PRUEBA DE ROTACIÓN DE LOGS POR TAMAÑO")
    print("=" * 80)
    
    results = []
    
    # Test 1: Ilimitados
    results.append(("Backups ilimitados", test_unlimited_backups()))
    
    # Test 2: Limitados
    results.append(("Backups limitados", test_limited_backups()))
    
    # Resumen
    print("\n" + "=" * 80)
    print("📋 RESUMEN DE RESULTADOS")
    print("=" * 80)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 ¡Todos los tests pasaron exitosamente!")
        return 0
    else:
        print("\n⚠️  Algunos tests fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
