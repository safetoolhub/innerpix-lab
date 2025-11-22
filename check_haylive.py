#!/usr/bin/env python3
"""Verifica timestamp de archivos HAYLIVE"""
from pathlib import Path
from datetime import datetime
import sys

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.date_utils import get_date_from_file

def check_haylive_times(directory):
    dir_path = Path(directory)
    
    jpg = dir_path / "IMG_0017_HAYLIVE.JPG"
    mov = dir_path / "IMG_0017_HAYLIVE.MOV"
    
    if not jpg.exists():
        print(f"❌ No existe: {jpg}")
        return
    if not mov.exists():
        print(f"❌ No existe: {mov}")
        return
    
    print(f"📷 JPG: {jpg}")
    jpg_mtime = datetime.fromtimestamp(jpg.stat().st_mtime)
    jpg_exif = get_date_from_file(jpg)
    print(f"   mtime: {jpg_mtime}")
    print(f"   EXIF:  {jpg_exif}")
    
    print(f"\n🎬 MOV: {mov}")
    mov_mtime = datetime.fromtimestamp(mov.stat().st_mtime)
    mov_exif = get_date_from_file(mov)
    print(f"   mtime: {mov_mtime}")
    print(f"   EXIF:  {mov_exif}")
    
    # Calculate differences
    print(f"\n⏱️  Diferencias de tiempo:")
    
    if jpg_exif and mov_exif:
        diff = abs((jpg_exif - mov_exif).total_seconds())
        print(f"   EXIF vs EXIF: {diff:.2f} segundos")
        if diff > 5:
            print(f"   ❌ RECHAZADO: diferencia > 5 segundos")
        else:
            print(f"   ✅ VÁLIDO: diferencia <= 5 segundos")
    else:
        print(f"   ⚠️  No hay fechas EXIF para comparar")
    
    diff_mtime = abs((jpg_mtime - mov_mtime).total_seconds())
    print(f"   mtime vs mtime: {diff_mtime:.2f} segundos")

if __name__ == "__main__":
    check_haylive_times("/home/ed/Pictures/TEST_BASE5")
