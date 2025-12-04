#!/usr/bin/env python3
"""
Script de prueba para verificar el sistema de dual logging.
"""
import logging
from pathlib import Path
from utils.logger import configure_logging, get_logger

def test_dual_logging():
    """Prueba el sistema de dual logging"""
    
    # Crear directorio temporal para logs de prueba
    test_logs_dir = Path("./test_logs")
    test_logs_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("TEST: Sistema de Dual Logging")
    print("=" * 80)
    
    # Test 1: Nivel INFO con dual logging habilitado
    print("\n📝 Test 1: INFO con dual logging habilitado")
    print("-" * 80)
    log_file, logs_dir = configure_logging(
        logs_dir=test_logs_dir,
        level="INFO",
        dual_log_enabled=True
    )
    
    logger = get_logger("TestDualLog")
    
    # Generar diferentes tipos de logs
    logger.debug("Este mensaje DEBUG no debería aparecer (nivel INFO)")
    logger.info("Este mensaje INFO aparece en el log principal")
    logger.warning("Este mensaje WARNING aparece en AMBOS logs")
    logger.error("Este mensaje ERROR aparece en AMBOS logs")
    logger.info("Otro mensaje INFO solo en el log principal")
    
    print(f"✓ Log principal creado: {log_file}")
    
    # Verificar que se creó el archivo de warnings
    warnerror_files = list(test_logs_dir.glob("*_WARNERROR.log"))
    if warnerror_files:
        print(f"✓ Log de warnings/errors creado: {warnerror_files[0]}")
        print("\n📄 Contenido del log principal:")
        with open(log_file, 'r', encoding='utf-8') as f:
            print(f.read())
        
        print("\n📄 Contenido del log de warnings/errors:")
        with open(warnerror_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
            
        # Verificar que solo tiene WARNING y ERROR
        lines = content.strip().split('\n')
        log_lines = [l for l in lines if ' - ' in l]
        has_only_warnings_errors = all(
            ' - WARNING - ' in l or ' - ERROR - ' in l 
            for l in log_lines
        )
        
        if has_only_warnings_errors:
            print("✓ El log de warnings/errors contiene SOLO WARNING y ERROR")
        else:
            print("✗ ERROR: El log de warnings/errors contiene otros niveles")
    else:
        print("✗ ERROR: No se creó el archivo de warnings/errors")
    
    # Test 2: Nivel WARNING (dual logging no debería crear archivo adicional)
    print("\n" + "=" * 80)
    print("📝 Test 2: WARNING (dual logging no crea archivo adicional)")
    print("-" * 80)
    
    # Limpiar archivos anteriores
    for f in test_logs_dir.glob("*.log"):
        f.unlink()
    
    log_file2, _ = configure_logging(
        logs_dir=test_logs_dir,
        level="WARNING",
        dual_log_enabled=True
    )
    
    logger2 = get_logger("TestWarningLevel")
    logger2.info("Este INFO no debería aparecer")
    logger2.warning("Este WARNING sí aparece")
    logger2.error("Este ERROR sí aparece")
    
    print(f"✓ Log principal creado: {log_file2}")
    
    warnerror_files2 = list(test_logs_dir.glob("*_WARNERROR.log"))
    if not warnerror_files2:
        print("✓ Correcto: No se creó log adicional con nivel WARNING")
    else:
        print("✗ ERROR: Se creó log adicional con nivel WARNING (no debería)")
    
    # Test 3: Nivel DEBUG con dual logging habilitado
    print("\n" + "=" * 80)
    print("📝 Test 3: DEBUG con dual logging habilitado")
    print("-" * 80)
    
    # Limpiar archivos anteriores
    for f in test_logs_dir.glob("*.log"):
        f.unlink()
    
    log_file3, _ = configure_logging(
        logs_dir=test_logs_dir,
        level="DEBUG",
        dual_log_enabled=True
    )
    
    logger3 = get_logger("TestDebugLevel")
    logger3.debug("Este DEBUG aparece en log principal")
    logger3.info("Este INFO aparece en log principal")
    logger3.warning("Este WARNING aparece en AMBOS logs")
    logger3.error("Este ERROR aparece en AMBOS logs")
    
    print(f"✓ Log principal creado: {log_file3}")
    
    warnerror_files3 = list(test_logs_dir.glob("*_WARNERROR.log"))
    if warnerror_files3:
        print(f"✓ Log de warnings/errors creado: {warnerror_files3[0]}")
        
        # Verificar contenido
        with open(warnerror_files3[0], 'r', encoding='utf-8') as f:
            content = f.read()
            if 'WARNING' in content and 'ERROR' in content:
                print("✓ El log de warnings/errors contiene WARNING y ERROR")
            if 'DEBUG' not in content and 'INFO' not in content:
                print("✓ El log de warnings/errors NO contiene DEBUG ni INFO")
    else:
        print("✗ ERROR: No se creó el archivo de warnings/errors")
    
    print("\n" + "=" * 80)
    print("✅ Tests completados")
    print("=" * 80)
    print(f"\n📁 Archivos de log creados en: {test_logs_dir.absolute()}")
    print("   Puedes revisar los archivos manualmente para verificar.")


if __name__ == "__main__":
    test_dual_logging()
