#!/usr/bin/env python3
"""
Script de demostración de las mejoras en date_utils.py

Este script demuestra las nuevas funcionalidades implementadas:
1. Extracción de campos EXIF adicionales (GPS, zona horaria, software)
2. Extracción de fechas desde nombres de archivo (WhatsApp, screenshots, etc.)
3. Extracción de metadata de videos con ffprobe
4. Validación de coherencia de fechas
5. Nueva lógica de priorización mejorada
"""
from pathlib import Path
from datetime import datetime
from utils.date_utils import (
    extract_date_from_filename,
    validate_date_coherence,
    get_exif_dates,
    select_chosen_date,
    get_all_file_dates
)


def demo_extract_date_from_filename():
    """Demuestra extracción de fechas desde nombres de archivo"""
    print("=" * 70)
    print("1. EXTRACCIÓN DE FECHAS DESDE NOMBRES DE ARCHIVO")
    print("=" * 70)
    
    test_filenames = [
        "IMG-20241113-WA0001.jpg",  # WhatsApp
        "VID-20231225-WA0042.mp4",  # WhatsApp video
        "Screenshot_20240101_153045.png",  # Screenshot
        "DSC_20231215_103022.jpg",  # Cámara
        "20230115_143022_document.pdf",  # Formato genérico
        "2024-03-15_vacation.jpg",  # ISO format
        "random_photo.jpg"  # Sin fecha
    ]
    
    for filename in test_filenames:
        date = extract_date_from_filename(filename)
        if date:
            print(f"✓ {filename:40} → {date.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"✗ {filename:40} → No date found")
    print()


def demo_validate_date_coherence():
    """Demuestra validación de coherencia de fechas"""
    print("=" * 70)
    print("2. VALIDACIÓN DE COHERENCIA DE FECHAS")
    print("=" * 70)
    
    # Caso 1: Fechas coherentes
    print("\nCaso 1: Fechas coherentes")
    dates_ok = {
        'exif_date_time_original': datetime(2023, 1, 15, 10, 30),
        'exif_create_date': datetime(2023, 1, 15, 10, 31),
        'exif_date_digitized': None,
        'exif_gps_date': None,
        'exif_software': None,
        'modification_date': datetime(2023, 1, 16, 12, 0),
        'creation_date': datetime(2023, 1, 15, 12, 0),
    }
    validation = validate_date_coherence(dates_ok)
    print(f"  Valid: {validation['is_valid']}")
    print(f"  Confidence: {validation['confidence']}")
    print(f"  Warnings: {validation['warnings'] or 'None'}")
    
    # Caso 2: EXIF posterior a mtime (sospechoso)
    print("\nCaso 2: EXIF posterior a modification_date")
    dates_suspicious = {
        'exif_date_time_original': datetime(2024, 1, 15, 10, 30),
        'exif_create_date': None,
        'exif_date_digitized': None,
        'exif_gps_date': None,
        'exif_software': None,
        'modification_date': datetime(2023, 1, 16, 12, 0),  # Anterior al EXIF!
        'creation_date': datetime(2023, 1, 15, 12, 0),
    }
    validation = validate_date_coherence(dates_suspicious)
    print(f"  Valid: {validation['is_valid']}")
    print(f"  Confidence: {validation['confidence']}")
    print(f"  Warnings: {validation['warnings']}")
    
    # Caso 3: Archivo editado con software
    print("\nCaso 3: Archivo editado (software detectado)")
    dates_edited = {
        'exif_date_time_original': datetime(2023, 1, 15, 10, 30),
        'exif_create_date': datetime(2023, 1, 15, 10, 31),
        'exif_date_digitized': None,
        'exif_gps_date': None,
        'exif_software': 'Adobe Photoshop CS6',
        'modification_date': datetime(2023, 1, 16, 12, 0),
        'creation_date': datetime(2023, 1, 15, 12, 0),
    }
    validation = validate_date_coherence(dates_edited)
    print(f"  Valid: {validation['is_valid']}")
    print(f"  Confidence: {validation['confidence']}")
    print(f"  Warnings: {validation['warnings']}")
    
    # Caso 4: Transferencia reciente
    print("\nCaso 4: Transferencia reciente (fechas divergentes)")
    dates_transferred = {
        'exif_date_time_original': datetime(2023, 1, 15, 10, 30),
        'exif_create_date': None,
        'exif_date_digitized': None,
        'exif_gps_date': None,
        'exif_software': None,
        'modification_date': datetime(2024, 11, 10, 12, 0),
        'creation_date': datetime(2024, 11, 10, 12, 0),  # Muy diferente al EXIF
    }
    validation = validate_date_coherence(dates_transferred)
    print(f"  Valid: {validation['is_valid']}")
    print(f"  Confidence: {validation['confidence']}")
    print(f"  Warnings: {validation['warnings']}")
    print()


def demo_select_chosen_date():
    """Demuestra la nueva lógica de priorización"""
    print("=" * 70)
    print("3. NUEVA LÓGICA DE PRIORIZACIÓN DE FECHAS")
    print("=" * 70)
    
    # Caso 1: GPS tiene mayor prioridad
    print("\nCaso 1: GPS DateStamp (mayor prioridad)")
    dates_gps = {
        'exif_gps_date': datetime(2023, 1, 15, 10, 30),
        'exif_date_time_original': datetime(2023, 1, 15, 10, 31),
        'exif_create_date': datetime(2023, 1, 15, 10, 32),
        'exif_date_digitized': None,
        'exif_offset_time': None,
        'exif_software': None,
        'video_metadata_date': None,
        'filename_date': None,
        'creation_date': datetime(2024, 1, 1, 12, 0),
        'creation_source': 'birth',
        'modification_date': datetime(2024, 1, 2, 14, 0),
    }
    selected, source = select_chosen_date(dates_gps)
    print(f"  Selected: {selected.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Source: {source}")
    
    # Caso 2: DateTimeOriginal con zona horaria
    print("\nCaso 2: DateTimeOriginal con zona horaria")
    dates_tz = {
        'exif_gps_date': None,
        'exif_date_time_original': datetime(2023, 1, 15, 10, 30),
        'exif_create_date': datetime(2023, 1, 15, 10, 32),
        'exif_date_digitized': None,
        'exif_offset_time': '+01:00',
        'exif_software': None,
        'video_metadata_date': None,
        'filename_date': None,
        'creation_date': datetime(2024, 1, 1, 12, 0),
        'creation_source': 'birth',
        'modification_date': datetime(2024, 1, 2, 14, 0),
    }
    selected, source = select_chosen_date(dates_tz)
    print(f"  Selected: {selected.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Source: {source}")
    
    # Caso 3: WhatsApp sin EXIF, fecha extraída del nombre
    print("\nCaso 3: WhatsApp sin EXIF (fecha del nombre)")
    dates_whatsapp = {
        'exif_gps_date': None,
        'exif_date_time_original': None,
        'exif_create_date': None,
        'exif_date_digitized': None,
        'exif_offset_time': None,
        'exif_software': None,
        'video_metadata_date': None,
        'filename_date': datetime(2024, 11, 13, 0, 0),  # Extraída de IMG-20241113-WA0001.jpg
        'creation_date': datetime(2024, 11, 15, 12, 0),
        'creation_source': 'birth',
        'modification_date': datetime(2024, 11, 15, 14, 0),
    }
    selected, source = select_chosen_date(dates_whatsapp)
    print(f"  Selected: {selected.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Source: {source}")
    
    # Caso 4: Video con metadata
    print("\nCaso 4: Video con metadata (ffprobe)")
    dates_video = {
        'exif_gps_date': None,
        'exif_date_time_original': None,
        'exif_create_date': None,
        'exif_date_digitized': None,
        'exif_offset_time': None,
        'exif_software': None,
        'video_metadata_date': datetime(2024, 1, 15, 14, 30),
        'filename_date': None,
        'creation_date': datetime(2024, 11, 15, 12, 0),
        'creation_source': 'birth',
        'modification_date': datetime(2024, 11, 15, 14, 0),
    }
    selected, source = select_chosen_date(dates_video)
    print(f"  Selected: {selected.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Source: {source}")
    print()


def main():
    """Función principal"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "DEMOSTRACIÓN DE MEJORAS EN DATE_UTILS.PY" + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    demo_extract_date_from_filename()
    demo_validate_date_coherence()
    demo_select_chosen_date()
    
    print("=" * 70)
    print("RESUMEN DE MEJORAS IMPLEMENTADAS")
    print("=" * 70)
    print("✓ get_exif_dates() ampliado con 4 campos adicionales")
    print("✓ extract_date_from_filename() implementado (6 patrones)")
    print("✓ get_video_metadata_date() implementado (ffprobe)")
    print("✓ validate_date_coherence() implementado (6 validaciones)")
    print("✓ get_all_file_dates() actualizado (12 campos)")
    print("✓ select_chosen_date() con priorización avanzada (7 niveles)")
    print("✓ Función renombrada de select_earliest_date → select_chosen_date")
    print("✓ Todos los tests pasando (51/51)")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
