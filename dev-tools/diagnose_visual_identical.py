#!/usr/bin/env python3
"""
Script de diagnóstico para investigar por qué visual_identical_service
no detectó ciertos duplicados visuales.

Uso:
    cd /home/ed/HACK/innerpix-lab
    source .venv/bin/activate
    python dev-tools/diagnose_visual_identical.py
"""

from pathlib import Path
from PIL import Image
import imagehash
from config import Config


def diagnose_pair(file1: Path, file2: Path):
    """Diagnostica un par de archivos que deberían ser idénticos."""
    print("=" * 80)
    print("DIAGNÓSTICO DE PAR DE ARCHIVOS")
    print("=" * 80)
    
    # 1. Verificar existencia
    print("\n1. VERIFICACIÓN DE EXISTENCIA:")
    print(f"   Archivo 1: {file1}")
    print(f"      Existe: {file1.exists()}")
    print(f"   Archivo 2: {file2}")
    print(f"      Existe: {file2.exists()}")
    
    if not file1.exists() or not file2.exists():
        print("\n   ❌ Uno o ambos archivos no existen. No se puede continuar.")
        return
    
    # 2. Verificar tamaños
    print("\n2. TAMAÑOS DE ARCHIVO:")
    size1 = file1.stat().st_size
    size2 = file2.stat().st_size
    print(f"   Archivo 1: {size1:,} bytes ({size1/1024/1024:.2f} MB)")
    print(f"   Archivo 2: {size2:,} bytes ({size2/1024/1024:.2f} MB)")
    print(f"   Diferencia: {abs(size1-size2):,} bytes")
    
    # 3. Verificar extensiones
    print("\n3. VERIFICACIÓN DE EXTENSIONES:")
    ext1 = file1.suffix.lower()
    ext2 = file2.suffix.lower()
    supported = Config.SUPPORTED_IMAGE_EXTENSIONS
    print(f"   Extensión 1: {ext1} (soportada: {ext1 in supported})")
    print(f"   Extensión 2: {ext2} (soportada: {ext2 in supported})")
    
    if ext1 not in supported or ext2 not in supported:
        print("\n   ❌ Una o ambas extensiones no están soportadas.")
        return
    
    # 4. Calcular hashes con configuración actual
    print("\n4. HASHES PERCEPTUALES (Config actual):")
    algorithm = Config.PERCEPTUAL_HASH_ALGORITHM
    hash_size = Config.PERCEPTUAL_HASH_SIZE
    print(f"   Configuración: algorithm={algorithm}, hash_size={hash_size}")
    
    try:
        img1 = Image.open(file1)
        if img1.mode != 'RGB':
            img1 = img1.convert('RGB')
        
        img2 = Image.open(file2)
        if img2.mode != 'RGB':
            img2 = img2.convert('RGB')
        
        if algorithm == "phash":
            hash1 = imagehash.phash(img1, hash_size=hash_size)
            hash2 = imagehash.phash(img2, hash_size=hash_size)
        elif algorithm == "ahash":
            hash1 = imagehash.average_hash(img1, hash_size=hash_size)
            hash2 = imagehash.average_hash(img2, hash_size=hash_size)
        else:
            hash1 = imagehash.dhash(img1, hash_size=hash_size)
            hash2 = imagehash.dhash(img2, hash_size=hash_size)
        
        hash_str1 = str(hash1)
        hash_str2 = str(hash2)
        distance = hash1 - hash2
        
        print(f"\n   Hash archivo 1: {hash_str1}")
        print(f"   Hash archivo 2: {hash_str2}")
        print(f"\n   Distancia Hamming: {distance}")
        print(f"   ¿Hash strings iguales?: {hash_str1 == hash_str2}")
        
        if hash_str1 == hash_str2:
            print("\n   ✅ Los hashes son IDÉNTICOS. Deberían estar en el mismo grupo.")
        else:
            print(f"\n   ⚠️  Los hashes son DIFERENTES (distancia={distance}).")
            print("      Esto explica por qué no fueron agrupados por visual_identical_service.")
        
    except Exception as e:
        print(f"\n   ❌ Error calculando hashes: {e}")
        return
    
    # 5. Simular agrupamiento
    print("\n5. SIMULACIÓN DE AGRUPAMIENTO:")
    hash_groups = {}
    for path, h in [(str(file1), hash_str1), (str(file2), hash_str2)]:
        if h not in hash_groups:
            hash_groups[h] = []
        hash_groups[h].append(path)
    
    if len(hash_groups) == 1:
        print(f"   ✅ Ambos archivos quedarían en el mismo grupo.")
        print(f"   Archivos en el grupo: {list(hash_groups.values())[0]}")
    else:
        print(f"   ❌ Los archivos quedarían en grupos SEPARADOS.")
        for h, files in hash_groups.items():
            print(f"      Hash '{h[:32]}...': {files}")
    
    # 6. Verificar FileInfoRepositoryCache
    print("\n6. VERIFICACIÓN DEL REPOSITORIO:")
    try:
        from services.file_metadata_repository_cache import FileInfoRepositoryCache
        repo = FileInfoRepositoryCache.get_instance()
        
        meta1 = repo.get_file_metadata(file1)
        meta2 = repo.get_file_metadata(file2)
        
        print(f"   Archivo 1 en cache: {meta1 is not None}")
        if meta1:
            print(f"      - Extension: {meta1.extension}")
            print(f"      - Size: {meta1.fs_size:,} bytes")
        
        print(f"   Archivo 2 en cache: {meta2 is not None}")
        if meta2:
            print(f"      - Extension: {meta2.extension}")
            print(f"      - Size: {meta2.fs_size:,} bytes")
        
        if meta1 is None or meta2 is None:
            print("\n   ⚠️  Uno o ambos archivos NO están en el cache.")
            print("      Esto podría explicar por qué no fueron analizados.")
            
        # Contar archivos en cache
        all_files = repo.get_all_files()
        print(f"\n   Total archivos en cache: {len(all_files)}")
        
    except Exception as e:
        print(f"   Error accediendo al repositorio: {e}")
    
    print("\n" + "=" * 80)
    print("FIN DEL DIAGNÓSTICO")
    print("=" * 80)


if __name__ == "__main__":
    # Archivos a diagnosticar
    file1 = Path("/home/ed/Pictures/RAW_1_2_3_4_5/iPhoneM_hasta_202406/3d171bb2-e181-429f-864c-22437ff6a5be.jpg")
    file2 = Path("/home/ed/Pictures/RAW_1_2_3_4_5/iPhoneC_hasta_202211/IMG_8771.JPG")
    
    diagnose_pair(file1, file2)
