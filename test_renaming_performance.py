#!/usr/bin/env python3
"""
Script de prueba de rendimiento para la fase de renaming.
Verifica que las optimizaciones funcionen correctamente.
"""
from pathlib import Path
import time
from config import Config
from services.file_renamer_service import FileRenamer
from utils.logger import configure_logging, get_logger

def test_renaming_performance(directory: Path):
    """Prueba el rendimiento del análisis de renaming"""
    print(f"\n{'='*70}")
    print(f"TEST DE RENDIMIENTO - FASE RENAMING")
    print(f"{'='*70}")
    print(f"Directorio: {directory}")
    print(f"MAX_WORKERS configurado: {Config.MAX_WORKERS}")
    print(f"{'='*70}\n")
    
    # Inicializar servicio
    renamer = FileRenamer()
    
    # Medir tiempo de análisis
    start_time = time.time()
    
    # Callback simple para medir progreso
    def progress_callback(current, total, message):
        if current % 100 == 0 or current == total:
            elapsed = time.time() - start_time
            rate = current / elapsed if elapsed > 0 else 0
            print(f"  [{current}/{total}] {message} - {rate:.1f} archivos/seg")
        return True  # Continuar procesamiento
    
    # Ejecutar análisis
    print("Iniciando análisis...\n")
    result = renamer.analyze(directory, progress_callback=progress_callback)
    
    elapsed_time = time.time() - start_time
    
    # Mostrar resultados
    print(f"\n{'='*70}")
    print(f"RESULTADOS")
    print(f"{'='*70}")
    print(f"Tiempo total: {elapsed_time:.2f} segundos")
    print(f"Total de archivos: {result.total_files}")
    print(f"Archivos procesados: {result.total_files}")
    print(f"Tasa promedio: {result.total_files / elapsed_time:.1f} archivos/segundo")
    print(f"\nDesglose:")
    print(f"  - Ya renombrados: {result.already_renamed}")
    print(f"  - Necesitan renombrado: {result.need_renaming}")
    print(f"  - No se pueden procesar: {result.cannot_process}")
    print(f"  - Conflictos resueltos: {result.conflicts}")
    print(f"{'='*70}\n")
    
    # Verificar caché
    from utils.date_utils import _get_all_file_dates_cached
    cache_info = _get_all_file_dates_cached.cache_info()
    print(f"ESTADÍSTICAS DE CACHÉ:")
    print(f"  - Hits: {cache_info.hits}")
    print(f"  - Misses: {cache_info.misses}")
    print(f"  - Ratio de aciertos: {cache_info.hits / (cache_info.hits + cache_info.misses) * 100:.1f}%")
    print(f"  - Tamaño actual: {cache_info.currsize}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    import sys
    
    # Configurar logging
    log_file, logs_dir = configure_logging(
        logs_dir=Config.DEFAULT_LOG_DIR,
        level="WARNING"  # Solo warnings y errores para no contaminar benchmark
    )
    
    # Obtener directorio de argumentos o usar el de desarrollo
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        # Usar el último directorio usado si está en modo desarrollo
        from utils.settings_manager import settings_manager
        last_folder = settings_manager.get_last_folder()
        if last_folder:
            test_dir = Path(last_folder)
        else:
            print("❌ Error: Especifica un directorio como argumento")
            print("   Uso: python test_renaming_performance.py /ruta/al/directorio")
            sys.exit(1)
    
    if not test_dir.exists():
        print(f"❌ Error: El directorio no existe: {test_dir}")
        sys.exit(1)
    
    # Ejecutar test
    test_renaming_performance(test_dir)
