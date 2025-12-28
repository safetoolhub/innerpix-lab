#!/usr/bin/env python3
"""
Script de verificación del fix del bug HEIC/JPG con strings EXIF.

Este script reproduce el bug reportado por el usuario donde archivos con
EXIF como strings "2023:08:10 15:41:34" estaban siendo procesados con
fs_mtime en lugar de exif_date_time_original.

Caso de prueba:
- IMG_0022.HEIC: exif_DateTimeOriginal = "2023:08:10 15:41:34"
- IMG_0022.jpg:  exif_DateTimeOriginal = "2023:08:10 15:41:34"

Resultado esperado DESPUÉS del fix:
- Source: exif_date_time_original (NO fs_mtime)
- Fechas: 2023-08-10 15:41:34 para ambos
"""

from types import SimpleNamespace
from datetime import datetime
from utils.date_utils import select_best_date_from_common_date_to_2_files


def main():
    print("=" * 80)
    print("VERIFICACIÓN DEL FIX: Bug HEIC/JPG con EXIF como strings")
    print("=" * 80)
    print()
    
    # Simular exactamente los datos del caché del usuario
    heic_file = SimpleNamespace(
        path="/home/ed/Pictures/RAW/iPhoneC_hasta_202311/IMG_0022.HEIC",
        exif_DateTimeOriginal="2023:08:10 15:41:34",  # String, NO datetime
        exif_DateTime="2023:08:10 15:41:34",
        fs_mtime=1691703949.0,  # 2023-08-10 pero hora diferente en UTC
        fs_ctime=1766818401.512191,
        fs_atime=1766832805.0878773
    )
    
    jpg_file = SimpleNamespace(
        path="/home/ed/Pictures/RAW/iPhoneC_hasta_202311/IMG_0022.jpg",
        exif_DateTimeOriginal="2023:08:10 15:41:34",  # String, NO datetime
        exif_DateTime="2023:08:10 15:41:34",
        fs_mtime=1691703949.0,
        fs_ctime=1766818401.5821912,
        fs_atime=1766832805.0838773
    )
    
    print("Archivo HEIC:")
    print(f"  Path: {heic_file.path}")
    print(f"  exif_DateTimeOriginal: {heic_file.exif_DateTimeOriginal} (type: {type(heic_file.exif_DateTimeOriginal).__name__})")
    print(f"  fs_mtime: {heic_file.fs_mtime} → {datetime.fromtimestamp(heic_file.fs_mtime)}")
    print()
    
    print("Archivo JPG:")
    print(f"  Path: {jpg_file.path}")
    print(f"  exif_DateTimeOriginal: {jpg_file.exif_DateTimeOriginal} (type: {type(jpg_file.exif_DateTimeOriginal).__name__})")
    print(f"  fs_mtime: {jpg_file.fs_mtime} → {datetime.fromtimestamp(jpg_file.fs_mtime)}")
    print()
    
    print("-" * 80)
    print("Llamando a select_best_date_from_common_date_to_2_files()...")
    print("-" * 80)
    print()
    
    result = select_best_date_from_common_date_to_2_files(heic_file, jpg_file, verbose=True)
    
    if result is None:
        print("❌ ERROR: No se pudo determinar fecha común")
        return False
    
    date1, date2, source = result
    
    print()
    print("=" * 80)
    print("RESULTADO:")
    print("=" * 80)
    print(f"  Fecha HEIC: {date1}")
    print(f"  Fecha JPG:  {date2}")
    print(f"  Fuente:     {source}")
    print()
    
    # Verificación
    success = True
    
    if source != 'exif_date_time_original':
        print(f"❌ FALLO: Se esperaba 'exif_date_time_original' pero se obtuvo '{source}'")
        success = False
    else:
        print(f"✓ CORRECTO: Source es 'exif_date_time_original'")
    
    expected_date = datetime(2023, 8, 10, 15, 41, 34)
    if date1 != expected_date or date2 != expected_date:
        print(f"❌ FALLO: Fechas incorrectas. Se esperaba {expected_date}")
        success = False
    else:
        print(f"✓ CORRECTO: Fechas coinciden con EXIF DateTimeOriginal")
    
    print()
    
    if success:
        print("✓✓✓ FIX VERIFICADO CORRECTAMENTE ✓✓✓")
        print()
        print("El bug ha sido corregido. Ahora select_best_date_from_common_date_to_2_files()")
        print("parsea correctamente strings EXIF como '2023:08:10 15:41:34' y los prioriza")
        print("sobre filesystem timestamps (mtime/ctime/atime).")
    else:
        print("❌❌❌ FIX NO FUNCIONA CORRECTAMENTE ❌❌❌")
    
    print()
    print("=" * 80)
    
    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
