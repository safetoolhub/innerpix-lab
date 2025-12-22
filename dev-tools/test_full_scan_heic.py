#!/usr/bin/env python3
"""Test del flujo completo de análisis inicial con archivos HEIC"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.file_metadata_repository_cache import FileInfoRepositoryCache, PopulationStrategy
from services.initial_scanner import InitialScanner


def test_full_scan():
    """Test completo del flujo de análisis"""
    test_dir = Path("/home/ed/Pictures/TEST_BASE2")
    
    if not test_dir.exists():
        print(f"❌ Directorio no encontrado: {test_dir}")
        return
    
    print(f"🔍 Escaneando directorio: {test_dir}")
    print("=" * 80)
    
    # Reset repositorio
    FileInfoRepositoryCache.reset_instance()
    repo = FileInfoRepositoryCache.get_instance()
    
    # Scanner
    scanner = InitialScanner()
    
    # Fase 1: BASIC scan
    print("\n1️⃣ FASE BASIC (filesystem metadata)...")
    result = scanner.scan(test_dir)
    
    print(f"   ✓ Total archivos: {result.total_files}")
    print(f"   ✓ Imágenes: {len(result.images)}")
    print(f"   ✓ Videos: {len(result.videos)}")
    
    # Verificar que el archivo HEIC está en la caché
    heic_file = test_dir / "IMG_0013_HAYHEIC.HEIC"
    if heic_file.exists():
        metadata = repo.get_file_metadata(heic_file)
        if metadata:
            print(f"\n2️⃣ Archivo HEIC en caché:")
            print(f"   Path: {metadata.path.name}")
            print(f"   Size: {metadata.fs_size} bytes")
            print(f"   Has EXIF: {metadata.has_exif}")
            print(f"   EXIF dates: {len(metadata.get_exif_dates())} campos")
            
            if metadata.has_exif:
                print(f"\n   Campos EXIF presentes:")
                if metadata.exif_DateTimeOriginal:
                    print(f"      ✓ DateTimeOriginal: {metadata.exif_DateTimeOriginal}")
                if metadata.exif_DateTime:
                    print(f"      ✓ DateTime: {metadata.exif_DateTime}")
                if metadata.exif_DateTimeDigitized:
                    print(f"      ✓ DateTimeDigitized: {metadata.exif_DateTimeDigitized}")
                if metadata.exif_SubSecTimeOriginal:
                    print(f"      ✓ SubSecTimeOriginal: {metadata.exif_SubSecTimeOriginal}")
                if metadata.exif_OffsetTimeOriginal:
                    print(f"      ✓ OffsetTimeOriginal: {metadata.exif_OffsetTimeOriginal}")
                if metadata.exif_Software:
                    print(f"      ✓ Software: {metadata.exif_Software}")
                if metadata.exif_ExifVersion:
                    print(f"      ✓ ExifVersion: {metadata.exif_ExifVersion}")
            else:
                print("      ❌ NO HAY DATOS EXIF - BUG!")
        else:
            print(f"\n❌ Archivo HEIC NO está en la caché!")
    else:
        print(f"\n❌ Archivo HEIC no existe: {heic_file}")
    
    print("\n" + "=" * 80)
    print("✅ Test completado")
    print("=" * 80)


if __name__ == '__main__':
    test_full_scan()
