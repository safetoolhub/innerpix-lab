#!/usr/bin/env python3
"""Examina metadatos EXIF completos de archivos Live Photo"""
import subprocess
import sys
from pathlib import Path

def show_exif_times(jpg_path, mov_path):
    """Muestra todos los campos de tiempo EXIF"""
    
    print("=" * 70)
    print(f"📷 METADATOS JPG: {jpg_path.name}")
    print("=" * 70)
    try:
        result = subprocess.run(
            ["exiftool", "-time:all", "-G1", str(jpg_path)],
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 70)
    print(f"🎬 METADATOS MOV: {mov_path.name}")
    print("=" * 70)
    try:
        result = subprocess.run(
            ["exiftool", "-time:all", "-G1", str(mov_path)],
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except Exception as e:
        print(f"Error: {e}")
    
    # También mostrar ContentIdentifier si existe (Live Photo metadata)
    print("\n" + "=" * 70)
    print("🔍 BUSCANDO MARCADORES DE LIVE PHOTO")
    print("=" * 70)
    
    print(f"\n📷 JPG - Content Identifier:")
    try:
        result = subprocess.run(
            ["exiftool", "-ContentIdentifier", str(jpg_path)],
            capture_output=True,
            text=True
        )
        print(result.stdout.strip() or "  No encontrado")
    except Exception as e:
        print(f"  Error: {e}")
    
    print(f"\n🎬 MOV - Content Identifier:")
    try:
        result = subprocess.run(
            ["exiftool", "-ContentIdentifier", str(mov_path)],
            capture_output=True,
            text=True
        )
        print(result.stdout.strip() or "  No encontrado")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    jpg = Path("/home/ed/Pictures/TEST_BASE5/IMG_0017_HAYLIVE.JPG")
    mov = Path("/home/ed/Pictures/TEST_BASE5/IMG_0017_HAYLIVE.MOV")
    
    if not jpg.exists():
        print(f"❌ No existe: {jpg}")
        sys.exit(1)
    if not mov.exists():
        print(f"❌ No existe: {mov}")
        sys.exit(1)
    
    show_exif_times(jpg, mov)
