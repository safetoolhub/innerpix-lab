#!/usr/bin/env python3
"""Script de debugging para Live Photos"""

import sys
import logging
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar logging a nivel DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

from services.live_photos_service import LivePhotoService, CleanupMode

def debug_live_photos(directory: str):
    """Debug Live Photos detection"""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"❌ Directorio no existe: {directory}")
        return
    
    print(f"🔍 Debugging Live Photos en: {directory}\n")
    
    # Crear servicio
    service = LivePhotoService()
    
    # Buscar archivos
    print("📁 Buscando archivos...")
    photos = []
    videos = []
    
    for file in dir_path.rglob("*"):
        if file.is_file():
            ext_upper = file.suffix.upper()
            if ext_upper in service.photo_extensions:
                photos.append(file)
                print(f"  📷 Foto: {file.name} (ext: {file.suffix})")
            elif ext_upper in service.video_extensions:
                videos.append(file)
                print(f"  🎬 Video: {file.name} (ext: {file.suffix})")
    
    print(f"\n✅ Encontrados: {len(photos)} fotos, {len(videos)} videos\n")
    
    # Buscar IMG_0017_HAYLIVE específicamente
    haylive_files = [f for f in dir_path.rglob("*HAYLIVE*")]
    if haylive_files:
        print("🎯 Archivos HAYLIVE encontrados:")
        for f in haylive_files:
            ext_upper = f.suffix.upper()
            in_photos = ext_upper in service.photo_extensions
            in_videos = ext_upper in service.video_extensions
            print(f"  - {f.name}")
            print(f"    Extensión: {f.suffix} (upper: {ext_upper})")
            print(f"    Es foto: {in_photos}")
            print(f"    Es video: {in_videos}")
            print(f"    Stem: {f.stem}")
            print(f"    Normalizado: {service._normalize_name(f.stem)}")
        print()
    
    # Ejecutar análisis
    print("🔬 Ejecutando análisis...")
    result = service.analyze(dir_path, CleanupMode.KEEP_IMAGE)
    
    print(f"\n📊 Resultados:")
    print(f"  Live Photos encontrados: {len(result.live_photo_groups)}")
    print(f"  Archivos a eliminar: {len(result.cleanup_plan['files_to_delete'])}")
    
    if result.live_photo_groups:
        print(f"\n✅ Live Photos detectados:")
        for lp in result.live_photo_groups:
            print(f"  - {lp.base_name}")
            print(f"    Imagen: {lp.image_path.name}")
            print(f"    Video: {lp.video_path.name}")
            print(f"    Diferencia tiempo: {lp.time_difference:.2f}s")
    else:
        print(f"\n❌ No se encontraron Live Photos")
        print(f"\n💡 Posibles causas:")
        print(f"  1. Las extensiones no están en mayúsculas (.JPG vs .jpg)")
        print(f"  2. Los archivos no están en la misma carpeta")
        print(f"  3. La diferencia de tiempo entre archivos es > 5 segundos")
        print(f"  4. Los nombres normalizados no coinciden")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <directorio>")
        print(f"Ejemplo: {sys.argv[0]} /home/ed/Pictures/TEST_BASE5")
        sys.exit(1)
    
    debug_live_photos(sys.argv[1])
