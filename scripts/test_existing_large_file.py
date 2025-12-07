#!/usr/bin/env python3
"""
Test manual para verificar que la rotación funciona con archivos grandes existentes.
"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import ThreadSafeRotatingFileHandler
import logging

def test_existing_large_file():
    """Verifica que un archivo grande existente se rota al inicializar el handler"""
    print("\n" + "=" * 80)
    print("TEST: Rotación de archivo grande existente")
    print("=" * 80)
    
    # Crear directorio temporal
    test_dir = Path(tempfile.mkdtemp(prefix="pixaro_log_test_"))
    print(f"📁 Directorio de prueba: {test_dir}")
    
    log_file = test_dir / "test.log"
    
    # Paso 1: Crear un archivo de 15 MB (excede el límite de 10 MB)
    print("\n1️⃣  Creando archivo de log de 15 MB...")
    with open(log_file, 'w') as f:
        # Escribir 15 MB de datos
        for i in range(15000):
            f.write("X" * 1000 + "\n")
    
    size_before = log_file.stat().st_size / (1024 * 1024)
    print(f"   ✅ Archivo creado: {size_before:.2f} MB")
    
    # Paso 2: Crear handler con límite de 10 MB
    print("\n2️⃣  Creando ThreadSafeRotatingFileHandler con límite de 10 MB...")
    max_bytes = 10 * 1024 * 1024  # 10 MB
    handler = ThreadSafeRotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=5,
        encoding='utf-8'
    )
    
    # Verificar resultados
    print("\n3️⃣  Verificando resultados...")
    
    # Debería haberse creado un backup
    backup_files = list(test_dir.glob("*.log.*"))
    print(f"   Archivos de backup encontrados: {len(backup_files)}")
    
    # El archivo actual debería ser nuevo y pequeño
    if log_file.exists():
        size_after = log_file.stat().st_size / (1024 * 1024)
        print(f"   Tamaño del archivo actual: {size_after:.2f} MB")
    
    # Listar todos los archivos
    print("\n📄 Archivos en el directorio:")
    for f in sorted(test_dir.glob("*")):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"   - {f.name} ({size_mb:.2f} MB)")
    
    # Verificación
    success = False
    if len(backup_files) > 0:
        backup_size = backup_files[0].stat().st_size / (1024 * 1024)
        if backup_size >= 14 and backup_size <= 16:  # Debería ser ~15 MB
            if log_file.exists() and log_file.stat().st_size < 1000:  # Archivo nuevo debería estar casi vacío
                success = True
                print("\n✅ SUCCESS: El archivo grande se rotó correctamente al inicializar el handler")
            else:
                print(f"\n❌ FAIL: El archivo actual no es nuevo (tamaño: {size_after:.2f} MB)")
        else:
            print(f"\n❌ FAIL: El backup tiene tamaño incorrecto ({backup_size:.2f} MB, esperado ~15 MB)")
    else:
        print("\n❌ FAIL: No se creó ningún archivo de backup")
    
    # Limpiar
    import shutil
    shutil.rmtree(test_dir)
    
    return success

if __name__ == "__main__":
    success = test_existing_large_file()
    sys.exit(0 if success else 1)
