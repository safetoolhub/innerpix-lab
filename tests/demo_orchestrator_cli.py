#!/usr/bin/env python3
"""
Script CLI de análisis de directorios usando AnalysisOrchestrator

Demuestra cómo usar el orchestrator en scripts CLI sin PyQt6
"""
import sys
from pathlib import Path
import argparse

# Asegurar imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar SOLO servicios - NO PyQt6
from services.analysis_orchestrator import AnalysisOrchestrator
from services.file_renamer import FileRenamer
from services.live_photo_detector import LivePhotoDetector
from services.file_organizer import FileOrganizer
from services.heic_remover import HEICDuplicateRemover
from services.duplicate_detector import DuplicateDetector
from utils.format_utils import format_size


def cli_progress_callback(current, total, message):
    """Callback de progreso para CLI"""
    if current > 0 and current % 100 == 0:
        print(f"   [{current}/{total}] {message}")
    return True  # Continuar


def cli_phase_callback(phase):
    """Callback de fase para CLI"""
    print(f"\n{phase}")


def cli_partial_callback(phase_name, data):
    """Callback de resultados parciales para CLI"""
    if phase_name == 'stats':
        print(f"   Total: {data['total']} archivos")
        print(f"   Imágenes: {data['images']}")
        print(f"   Videos: {data['videos']}")
        print(f"   Otros: {data['others']}")
    elif phase_name == 'renaming':
        if data and hasattr(data, 'files_to_rename'):
            print(f"   Archivos a renombrar: {len(data.files_to_rename)}")
    elif phase_name == 'live_photos':
        if data:
            print(f"   Live Photos encontrados: {data['live_photos_found']}")
            print(f"   Espacio a liberar: {format_size(data['space_to_free'])}")
    elif phase_name == 'organization':
        if data and hasattr(data, 'total_files'):
            print(f"   Archivos para organizar: {data.total_files}")
    elif phase_name == 'heic':
        if data and hasattr(data, 'pairs'):
            print(f"   Pares HEIC/JPG: {len(data.pairs)}")
    elif phase_name == 'duplicates':
        if data and hasattr(data, 'groups'):
            print(f"   Grupos de duplicados: {len(data.groups)}")


def analyze_directory(directory: Path, 
                     analyze_renaming: bool = True,
                     analyze_live_photos: bool = True,
                     analyze_organization: bool = True,
                     analyze_heic: bool = True,
                     analyze_duplicates: bool = False):
    """
    Analiza un directorio sin UI
    
    Args:
        directory: Directorio a analizar
        analyze_*: Flags para habilitar/deshabilitar análisis específicos
    """
    print("=" * 80)
    print(f"🔍 Análisis de Directorio: {directory}")
    print("=" * 80)
    
    if not directory.exists():
        print(f"❌ Error: El directorio no existe: {directory}")
        return 1
    
    if not directory.is_dir():
        print(f"❌ Error: La ruta no es un directorio: {directory}")
        return 1
    
    # Crear servicios según flags
    renamer = FileRenamer() if analyze_renaming else None
    lp_detector = LivePhotoDetector() if analyze_live_photos else None
    organizer = FileOrganizer() if analyze_organization else None
    heic_remover = HEICDuplicateRemover() if analyze_heic else None
    dup_detector = DuplicateDetector() if analyze_duplicates else None
    
    # Crear orchestrator
    orchestrator = AnalysisOrchestrator()
    
    # Ejecutar análisis
    try:
        result = orchestrator.run_full_analysis(
            directory=directory,
            renamer=renamer,
            lp_detector=lp_detector,
            organizer=organizer,
            heic_remover=heic_remover,
            duplicate_detector=dup_detector,
            progress_callback=cli_progress_callback,
            phase_callback=cli_phase_callback,
            partial_callback=cli_partial_callback
        )
        
        # Mostrar resumen final
        print("\n" + "=" * 80)
        print("📊 RESUMEN DEL ANÁLISIS")
        print("=" * 80)
        print(f"Directorio: {result.directory}")
        print(f"Total archivos: {result.scan.total_files}")
        print(f"  • Imágenes: {result.scan.image_count}")
        print(f"  • Videos: {result.scan.video_count}")
        print(f"  • Otros: {result.scan.other_count}")
        
        if result.renaming and hasattr(result.renaming, 'files_to_rename'):
            print(f"\n📝 Renombrado:")
            print(f"  • Archivos a renombrar: {len(result.renaming.files_to_rename)}")
        
        if result.live_photos:
            print(f"\n📱 Live Photos:")
            print(f"  • Grupos encontrados: {result.live_photos['live_photos_found']}")
            print(f"  • Espacio a liberar: {format_size(result.live_photos['space_to_free'])}")
        
        if result.organization and hasattr(result.organization, 'total_files'):
            print(f"\n📁 Organización:")
            print(f"  • Archivos para organizar: {result.organization.total_files}")
        
        if result.heic and hasattr(result.heic, 'pairs'):
            print(f"\n🖼️  Duplicados HEIC:")
            print(f"  • Pares HEIC/JPG: {len(result.heic.pairs)}")
        
        if result.duplicates and hasattr(result.duplicates, 'groups'):
            print(f"\n🔍 Duplicados exactos:")
            print(f"  • Grupos: {len(result.duplicates.groups)}")
            total_dup = sum(len(g.files) - 1 for g in result.duplicates.groups)
            print(f"  • Archivos duplicados: {total_dup}")
        
        print("\n" + "=" * 80)
        print("✅ Análisis completado exitosamente")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Analiza un directorio de fotos/videos sin UI',
        epilog='Ejemplo: python demo_orchestrator_cli.py ~/Photos --all'
    )
    
    parser.add_argument(
        'directory',
        type=Path,
        help='Directorio a analizar'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Ejecutar todos los análisis (incluyendo duplicados)'
    )
    
    parser.add_argument(
        '--no-rename',
        action='store_true',
        help='Desactivar análisis de renombrado'
    )
    
    parser.add_argument(
        '--no-live-photos',
        action='store_true',
        help='Desactivar detección de Live Photos'
    )
    
    parser.add_argument(
        '--no-organization',
        action='store_true',
        help='Desactivar análisis de organización'
    )
    
    parser.add_argument(
        '--no-heic',
        action='store_true',
        help='Desactivar búsqueda de duplicados HEIC'
    )
    
    parser.add_argument(
        '--duplicates',
        action='store_true',
        help='Activar detección de duplicados exactos (puede ser lento)'
    )
    
    args = parser.parse_args()
    
    # Configurar análisis
    analyze_renaming = not args.no_rename
    analyze_live_photos = not args.no_live_photos
    analyze_organization = not args.no_organization
    analyze_heic = not args.no_heic
    analyze_duplicates = args.duplicates or args.all
    
    # Ejecutar
    return analyze_directory(
        directory=args.directory,
        analyze_renaming=analyze_renaming,
        analyze_live_photos=analyze_live_photos,
        analyze_organization=analyze_organization,
        analyze_heic=analyze_heic,
        analyze_duplicates=analyze_duplicates
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
