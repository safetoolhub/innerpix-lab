#!/usr/bin/env python3
"""Debug script para ver qué pasa con EXIF en HEIC"""
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import pillow_heif

# Registrar opener HEIC
pillow_heif.register_heif_opener()

heic_file = Path("/home/ed/Pictures/TEST_BASE2/IMG_0013_HAYHEIC.HEIC")

print(f"🔍 Analizando: {heic_file.name}")
print("=" * 80)

with Image.open(heic_file) as image:
    print(f"Formato: {image.format}")
    print(f"Tamaño: {image.size}")
    print(f"Modo: {image.mode}")
    
    # Verificar image.info
    print(f"\nKeys en image.info: {list(image.info.keys())}")
    
    # Método 1: image.info['exif']
    print("\n📋 Método 1: image.info['exif']")
    exif_bytes = image.info.get('exif')
    if exif_bytes:
        print(f"   ✓ Tiene exif bytes: {len(exif_bytes)} bytes")
        try:
            exif_obj = Image.Exif()
            exif_obj.load(exif_bytes)
            exif_data = exif_obj._getexif()
            if exif_data:
                print(f"   ✓ _getexif() retornó {len(exif_data)} tags")
                for tag_id, value in list(exif_data.items())[:10]:
                    tag_name = TAGS.get(tag_id, tag_id)
                    print(f"      - {tag_name} ({tag_id}): {value}")
            else:
                print(f"   ❌ _getexif() retornó None")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print(f"   ❌ No hay exif bytes")
    
    # Método 2: image._getexif()
    print("\n📋 Método 2: image._getexif() directo")
    try:
        exif_data = image._getexif()
        if exif_data:
            print(f"   ✓ _getexif() retornó {len(exif_data)} tags")
            for tag_id, value in list(exif_data.items())[:10]:
                tag_name = TAGS.get(tag_id, tag_id)
                print(f"      - {tag_name} ({tag_id}): {value}")
        else:
            print(f"   ❌ _getexif() retornó None")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Método 3: image.getexif()
    print("\n📋 Método 3: image.getexif() (moderno)")
    try:
        exif = image.getexif()
        if exif:
            print(f"   ✓ getexif() retornó {len(exif)} tags")
            for tag_id in list(exif.keys())[:15]:
                tag_name = TAGS.get(tag_id, tag_id)
                value = exif.get(tag_id)
                print(f"      - {tag_name} ({tag_id}): {value}")
        else:
            print(f"   ❌ getexif() retornó vacío")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "=" * 80)
