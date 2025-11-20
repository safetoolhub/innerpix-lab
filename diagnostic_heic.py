#!/usr/bin/env python3
"""
Script de diagnóstico para entender por qué no aparecen duplicados HEIC/JPG
"""
import sys
from pathlib import Path
from services.heic_remover_service import HEICRemover

def main():
    if len(sys.argv) != 2:
        print("Uso: python diagnostic_heic.py <directorio>")
        sys.exit(1)

    test_dir = Path(sys.argv[1])
    if not test_dir.exists():
        print(f"Directorio {test_dir} no existe")
        sys.exit(1)

    print(f"Analizando directorio: {test_dir}")

    # Crear servicio
    service = HEICRemover()

    # Analizar sin validación de fechas
    result = service.analyze(test_dir, recursive=True, validate_dates=False)

    print(f"\nEstadísticas del análisis:")
    print(f"Archivos HEIC encontrados: {result.total_heic_files}")
    print(f"Archivos JPG encontrados: {result.total_jpg_files}")
    print(f"Pares duplicados encontrados: {result.total_duplicates}")

    # Buscar específicamente archivos con nombre IMG_1115
    heic_files = list(test_dir.rglob('IMG_1115.HEIC'))
    jpg_files = list(test_dir.rglob('IMG_1115.JPG'))
    jpg_files.extend(list(test_dir.rglob('IMG_1115.JPEG')))

    print(f"\nArchivos encontrados con nombre IMG_1115:")
    for f in heic_files:
        size = f.stat().st_size
        mtime = f.stat().st_mtime
        print(f"HEIC: {f} - {size} bytes - mtime: {mtime}")

    for f in jpg_files:
        size = f.stat().st_size
        mtime = f.stat().st_mtime
        print(f"JPG: {f} - {size} bytes - mtime: {mtime}")

    if heic_files and jpg_files:
        heic_file = heic_files[0]
        jpg_file = jpg_files[0]
        print(f"\nComparación detallada:")
        print(f"HEIC: {heic_file} ({heic_file.stat().st_size} bytes)")
        print(f"JPG: {jpg_file} ({jpg_file.stat().st_size} bytes)")
        print(f"Mismo directorio: {heic_file.parent == jpg_file.parent}")
        print(f"Nombre base HEIC: '{heic_file.stem}'")
        print(f"Nombre base JPG: '{jpg_file.stem}'")
        print(f"Nombres base iguales: {heic_file.stem == jpg_file.stem}")

        # Verificar si están en el mismo directorio en el análisis
        heic_dir = str(heic_file.parent)
        jpg_dir = str(jpg_file.parent)
        print(f"Directorio HEIC: {heic_dir}")
        print(f"Directorio JPG: {jpg_dir}")

        # Verificar si aparecen en los resultados del análisis
        found_in_results = False
        for pair in result.duplicate_pairs:
            if pair.heic_path == heic_file and pair.jpg_path == jpg_file:
                found_in_results = True
                print("✓ Encontrado en resultados del análisis")
                break

        if not found_in_results:
            print("✗ NO encontrado en resultados del análisis")

            # Verificar posibles razones
            if heic_file.stat().st_size == 0:
                print("⚠ Razón posible: Archivo HEIC tiene 0 bytes")
            if jpg_file.stat().st_size == 0:
                print("⚠ Razón posible: Archivo JPG tiene 0 bytes")
            if heic_file.parent != jpg_file.parent:
                print("⚠ Razón posible: Archivos están en directorios diferentes")
    else:
        print("No se encontraron ambos archivos HEIC y JPG con nombre IMG_1115")

if __name__ == "__main__":
    main()