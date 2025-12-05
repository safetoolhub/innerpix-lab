#!/usr/bin/env python3
"""
Script para inspeccionar la caché de análisis generada.
Uso: python scripts/inspect_analysis_cache.py /ruta/al/directorio [--read-records N]
"""
import sys
import os
import pickle
import argparse
from pathlib import Path

# Añadir directorio raíz al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from utils.logger import configure_logging

def inspect_cache(cache_path: Path, num_records: int):
    """
    Lee y muestra los primeros N registros de cada sección de la caché.
    """
    print(f"\n🔍 Inspeccionando caché: {cache_path}")
    
    if not cache_path.exists():
        print(f"❌ Error: No existe el archivo de caché en {cache_path}")
        return

    try:
        with open(cache_path, 'rb') as f:
            result = pickle.load(f)
            
        print(f"✅ Caché cargada exitosamente. Tipo: {type(result).__name__}")
        
        # 1. Scan Result
        print(f"\n--- 📊 Scan Results ---")
        if hasattr(result, 'scan'):
            print(f"Total Files: {result.scan.total_files}")
            print(f"Images: {result.scan.image_count}")
            print(f"Videos: {result.scan.video_count}")
            print(f"Others: {result.scan.other_count}")
            
            if num_records > 0:
                print(f"\n[First {num_records} Images]")
                for i, img in enumerate(result.scan.images[:num_records]):
                    print(f"  {i+1}. {img.name}")
                    
                print(f"\n[First {num_records} Videos]")
                for i, vid in enumerate(result.scan.videos[:num_records]):
                    print(f"  {i+1}. {vid.name}")
        else:
             print("No scan data found.")

        # 2. Renaming
        print(f"\n--- 🏷️  Renaming ---")
        if result.renaming:
            print(f"Need renaming: {result.renaming.need_renaming}")
            print(f"Already renamed: {result.renaming.already_renamed}")
            if num_records > 0 and hasattr(result.renaming, 'renaming_plan') and result.renaming.renaming_plan:
                 print(f"\n[First {num_records} Renaming Items]")
                 for i, item in enumerate(result.renaming.renaming_plan[:num_records]):
                     print(f"  {i+1}. {item}")
        else:
            print("No renaming analysis performed.")
            
        # 3. Live Photos
        print(f"\n--- 📸 Live Photos ---")
        if result.live_photos:
            print(f"Groups found: {result.live_photos.live_photos_found}")
            
            # Extract Live Photos paths
            lp_files = set()
            if hasattr(result.live_photos, 'groups'):
                 for g in result.live_photos.groups:
                     lp_files.add(str(g.video_path))
            
            # Check Exact Duplicates for overlaps
            if result.duplicates and hasattr(result.duplicates, 'groups'):
                dup_files = set()
                for g in result.duplicates.groups:
                    for f in g.files:
                        dup_files.add(str(f.path))
                
                overlaps = lp_files.intersection(dup_files)
                print(f"Overlaps between Live Photos (Video) and Exact Duplicates: {len(overlaps)}")
                if overlaps:
                    print("Example overlaps:")
                    for p in list(overlaps)[:5]:
                        print(f"  - {p}")
            if hasattr(result.live_photos, 'files_to_delete'):
                paths = [str(f['path']) for f in result.live_photos.files_to_delete]
                unique_paths = set(paths)
                print(f"Files to delete: {len(paths)}")
                print(f"Unique paths: {len(unique_paths)}")
                if len(paths) != len(unique_paths):
                    print(f"⚠️  DUPLICATES FOUND IN PLAN: {len(paths) - len(unique_paths)}")
                    from collections import Counter
                    counts = Counter(paths)
                    for p, c in counts.most_common(5):
                        if c > 1:
                            print(f"  - {p} (x{c})")
            
            if num_records > 0 and hasattr(result.live_photos, 'groups') and result.live_photos.groups:
                 print(f"\n[First {num_records} Live Photo Groups]")
                 for i, group in enumerate(result.live_photos.groups[:num_records]):
                     print(f"  {i+1}. {group}")
        else:
            print("No Live Photos analysis performed.")

        # 4. HEIC/JPG
        print(f"\n--- 👯 HEIC/JPG Duplicates ---")
        if result.heic:
            print(f"Total pairs: {result.heic.total_pairs}")
            if num_records > 0 and hasattr(result.heic, 'duplicate_pairs') and result.heic.duplicate_pairs:
                 print(f"\n[First {num_records} HEIC Pairs]")
                 for i, pair in enumerate(result.heic.duplicate_pairs[:num_records]):
                     print(f"  {i+1}. {pair}")
        else:
            print("No HEIC analysis performed.")

        # 5. Exact Duplicates
        print(f"\n--- 📑 Exact Duplicates ---")
        if result.duplicates:
            print(f"Total groups: {result.duplicates.total_groups}")
            if num_records > 0 and hasattr(result.duplicates, 'groups') and result.duplicates.groups:
                 print(f"\n[First {num_records} Duplicate Groups]")
                 for i, group in enumerate(result.duplicates.groups[:num_records]):
                     print(f"  {i+1}. {group}")
        else:
            print("No duplicates analysis performed.")

        # 6. Zero Byte
        print(f"\n--- 🗑️  Zero Byte Files ---")
        if result.zero_byte:
            print(f"Files found: {result.zero_byte.zero_byte_files_found}")
            if num_records > 0 and hasattr(result.zero_byte, 'files') and result.zero_byte.files:
                 print(f"\n[First {num_records} Empty Files]")
                 for i, fpath in enumerate(result.zero_byte.files[:num_records]):
                     print(f"  {i+1}. {fpath}")
        else:
            print("No zero-byte analysis performed.")
            
        # 7. Organization
        print(f"\n--- 📂 Organization ---")
        if result.organization:
             print(f"Total files to move: {result.organization.total_files_to_move}")
             if num_records > 0 and hasattr(result.organization, 'move_plan') and result.organization.move_plan:
                  print(f"\n[First {num_records} Move Plan Items]")
                  for i, move in enumerate(result.organization.move_plan[:num_records]):
                      print(f"  {i+1}. {move}")
        else:
             print("No organization analysis performed.")

    except Exception as e:
        print(f"\n❌ Error leyendo caché: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Inspeccionar caché de análisis generada.")
    parser.add_argument("directory", help="Directorio donde se encuentra la caché")
    parser.add_argument("--read-records", "-n", type=int, default=0, help="Leer los primeros N registros de la caché y mostrarlos")
    
    args = parser.parse_args()
    
    target_dir = Path(args.directory)
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: {target_dir} no es un directorio válido")
        sys.exit(1)
        
    # Configurar logger básico
    configure_logging()
    
    cache_path = target_dir / Config.DEV_CACHE_FILENAME
    
    inspect_cache(cache_path, args.read_records)

if __name__ == "__main__":
    main()
