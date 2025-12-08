#!/usr/bin/env python3
"""
Script para generar caché de análisis para desarrollo.
Uso: python scripts/generate_analysis_cache.py /ruta/al/directorio

Este script ejecuta un análisis completo usando AnalysisOrchestrator y guarda
el resultado en un archivo pickle (.pixaro_analysis_cache.pkl) en el directorio destino.
Esto permite saltar la fase de análisis en Stage 2 activando DEV_USE_CACHED_ANALYSIS en config.py.

La caché incluye:
- metadata_cache con hashes SHA256 para duplicados exactos
- metadata_cache con todas las fechas extraídas (EXIF, video, filename, filesystem)
- metadata_cache con fechas seleccionadas finales (selected_date, date_source)
- Resultados de análisis de todos los servicios (renaming, live_photos, etc.)

NOTA: Si cambias la estructura de FileMetadataCache o result_types, 
      regenera las cachés existentes para evitar errores de deserialización.
"""
import sys
import os
import pickle
import time
from pathlib import Path

# Añadir directorio raíz al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from services.analysis_orchestrator import AnalysisOrchestrator
from services.file_renamer_service import FileRenamer
from services.live_photos_service import LivePhotoService
from services.file_organizer_service import FileOrganizer
from services.heic_remover_service import HEICRemover
from services.exact_copies_detector import ExactCopiesDetector
from services.zero_byte_service import ZeroByteService
from utils.logger import configure_logging

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/generate_analysis_cache.py <directorio>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: {target_dir} no es un directorio válido")
        sys.exit(1)
        
    # Configurar logger básico
    configure_logging()
    
    print(f"🚀 Iniciando generación de caché para: {target_dir}")
    print("Esto puede tardar unos minutos dependiendo del tamaño del dataset...")
    
    # Instanciar servicios
    orchestrator = AnalysisOrchestrator()
    renamer = FileRenamer()
    live_photos_service = LivePhotoService()
    organizer = FileOrganizer()
    heic_remover = HEICRemover()
    duplicate_exact_detector = ExactCopiesDetector()
    zero_byte_service = ZeroByteService()
    
    # Callbacks simples para feedback
    def progress_callback(current, total, message):
        sys.stdout.write(f"\rProgress: {current}/{total} - {message[:50]:<50}")
        sys.stdout.flush()
        return True
        
    def phase_callback(phase_name):
        print(f"\n\n--- Fase: {phase_name} ---")
        
    start_time = time.time()
    
    # Ejecutar análisis
    try:
        result = orchestrator.run_full_analysis(
            directory=target_dir,
            renamer=renamer,
            live_photos_service=live_photos_service,
            organizer=organizer,
            heic_remover=heic_remover,
            duplicate_exact_detector=duplicate_exact_detector,
            zero_byte_service=zero_byte_service,
            progress_callback=progress_callback,
            phase_callback=phase_callback,
            precalculate_hashes=True  # Importante: pre-calcular hashes para que sea completo
        )
        
        print(f"\n\n✅ Análisis completado en {time.time() - start_time:.2f}s")
        
        # Guardar caché
        cache_path = target_dir / Config.DEV_CACHE_FILENAME
        print(f"💾 Guardando caché en: {cache_path}")
        
        with open(cache_path, 'wb') as f:
            pickle.dump(result, f)
            
        print(f"✨ Caché generada exitosamente")
        print(f"📂 Archivo: {cache_path.name}")
        print(f"📍 Ruta completa: {cache_path.absolute()}")
        print(f"📦 Tamaño: {cache_path.stat().st_size / 1024 / 1024:.2f} MB")
        print("\nPara usar esta caché:")
        print("1. Edita config.py y pon DEV_USE_CACHED_ANALYSIS = True")
        print("2. Ejecuta la aplicación y selecciona este directorio")
        
    except Exception as e:
        print(f"\n\n❌ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
