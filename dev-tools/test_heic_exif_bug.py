#!/usr/bin/env python3
"""
Test script para reproducir el bug de EXIF en archivos HEIC.

Verifica que los datos EXIF extraídos de HEIC se almacenan correctamente en FileMetadata.
"""
from pathlib import Path
import sys

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.file_metadata import FileMetadata
from utils.file_utils import get_exif_from_image, get_file_stat_info


def test_heic_exif():
    """Test completo del flujo EXIF para HEIC"""
    heic_file = Path("/home/ed/Pictures/TEST_BASE2/IMG_0013_HAYHEIC.HEIC")
    
    if not heic_file.exists():
        print(f"❌ Archivo no encontrado: {heic_file}")
        return
    
    print(f"🔍 Probando con: {heic_file.name}")
    print("=" * 80)
    
    # Paso 1: Extraer EXIF usando get_exif_from_image
    print("\n1️⃣ Extrayendo EXIF con get_exif_from_image()...")
    exif_dates = get_exif_from_image(heic_file)
    
    print(f"   Campos extraídos: {len(exif_dates)}")
    for key, value in exif_dates.items():
        if value is not None:
            print(f"   ✓ {key}: {value}")
        else:
            print(f"   ✗ {key}: None")
    
    # Paso 2: Crear FileMetadata básico
    print("\n2️⃣ Creando FileMetadata básico...")
    stat_info = get_file_stat_info(heic_file, resolve_path=False)
    metadata = FileMetadata(
        path=heic_file.resolve(),
        fs_size=stat_info['size'],
        fs_ctime=stat_info['ctime'],
        fs_mtime=stat_info['mtime'],
        fs_atime=stat_info['atime']
    )
    print(f"   ✓ FileMetadata creado: {metadata.path.name}")
    
    # Paso 3: Intentar asignar campos EXIF (simulando _process_file_exif_images)
    print("\n3️⃣ Asignando campos EXIF a FileMetadata...")
    
    # Verificar qué campos tiene FileMetadata
    available_fields = [attr for attr in dir(metadata) if attr.startswith('exif_')]
    print(f"   Campos EXIF disponibles en FileMetadata: {len(available_fields)}")
    for field in available_fields:
        print(f"   - {field}")
    
    print("\n4️⃣ Mapeando campos extraídos a FileMetadata...")
    
    # Mapeo actual en _process_file_exif_images
    mappings = {
        'DateTimeOriginal': 'exif_DateTimeOriginal',
        'CreateDate': 'exif_DateTime',
        'DateTimeDigitized': 'exif_DateTimeDigitized',
        'SubSecTimeOriginal': 'exif_SubSecTimeOriginal',
        'OffsetTimeOriginal': 'exif_OffsetTimeOriginal',
        'GPSDateStamp': 'exif_GPSDateStamp',
        'Software': 'exif_Software',
        'ExifVersion': 'exif_ExifVersion'
    }
    
    errors = []
    for exif_key, metadata_attr in mappings.items():
        exif_value = exif_dates.get(exif_key)
        if exif_value is not None:
            # Intentar asignar
            if hasattr(metadata, metadata_attr):
                setattr(metadata, metadata_attr, exif_value)
                print(f"   ✓ {exif_key} → {metadata_attr}: OK")
            else:
                print(f"   ❌ {exif_key} → {metadata_attr}: CAMPO NO EXISTE EN FileMetadata!")
                errors.append(metadata_attr)
    
    # Paso 5: Verificar has_exif
    print(f"\n5️⃣ Verificando has_exif...")
    print(f"   metadata.has_exif = {metadata.has_exif}")
    print(f"   metadata.get_exif_dates() = {metadata.get_exif_dates()}")
    
    # Resumen
    print("\n" + "=" * 80)
    if errors:
        print(f"❌ BUG CONFIRMADO - Faltan {len(errors)} campos en FileMetadata:")
        for field in errors:
            print(f"   - {field}")
        print("\nSolución: Agregar estos campos al dataclass FileMetadata")
    else:
        print("✅ Todos los campos EXIF se mapearon correctamente")
    
    print("=" * 80)


if __name__ == '__main__':
    test_heic_exif()
