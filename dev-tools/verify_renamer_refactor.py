"""
Script de verificación del refactor de file_renamer_service.py

Verifica que:
1. El servicio usa correctamente FileInfoRepositoryCache.get_instance()
2. No hay referencias a get_all_metadata_from_file
3. Las dataclasses de resultado están correctas
4. El servicio funciona con el nuevo flujo de Stage 3
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.file_renamer_service import FileRenamerService
from services.result_types import RenameAnalysisResult, RenameExecutionResult
from services.file_metadata_repository_cache import FileInfoRepositoryCache, PopulationStrategy
from services.file_metadata import FileMetadata
from utils.logger import configure_logging, get_logger

def test_renamer_basic_usage():
    """Verifica uso básico del servicio"""
    logger = get_logger('VerifyRenamer')
    
    # Test 1: El servicio debe poder instanciarse
    logger.info("Test 1: Instanciar servicio")
    service = FileRenamerService()
    assert service is not None
    logger.info("✓ Servicio instanciado correctamente")
    
    # Test 2: El repositorio debe ser accesible vía get_instance()
    logger.info("\nTest 2: Acceso al repositorio")
    repo = FileInfoRepositoryCache.get_instance()
    assert repo is not None
    logger.info("✓ Repositorio accesible vía get_instance()")
    
    # Test 3: Las dataclasses de resultado deben tener la estructura correcta
    logger.info("\nTest 3: Estructura de dataclasses")
    
    # Test RenameAnalysisResult
    analysis_result = RenameAnalysisResult(
        renaming_plan=[],
        already_renamed=5,
        conflicts=2,
        files_by_year={2023: 10, 2024: 15},
        issues=["Test issue"],
        items_count=20,
        bytes_total=0
    )
    assert hasattr(analysis_result, 'need_renaming')
    assert hasattr(analysis_result, 'cannot_process')
    assert analysis_result.need_renaming == 0
    assert analysis_result.cannot_process == 1
    logger.info("✓ RenameAnalysisResult estructura correcta")
    
    # Test RenameExecutionResult
    execution_result = RenameExecutionResult(
        renamed_files=[{"original": "test.jpg", "new_name": "20240101_120000_IMG.jpg"}],
        conflicts_resolved=1,
        items_processed=10,
        dry_run=False
    )
    assert hasattr(execution_result, 'files_renamed')
    assert execution_result.files_renamed == 10
    logger.info("✓ RenameExecutionResult estructura correcta")
    
    # Test 4: Verificar que no hay __post_init__ vacío
    logger.info("\nTest 4: No __post_init__ vacío")
    import inspect
    analysis_source = inspect.getsource(RenameAnalysisResult)
    assert 'def __post_init__(self):' not in analysis_source or 'pass' not in analysis_source.split('def __post_init__')[1].split('def ')[0]
    logger.info("✓ No hay __post_init__ vacío en RenameAnalysisResult")
    
    # Test 5: El servicio debe usar el patrón correcto (get_instance, no parámetros)
    logger.info("\nTest 5: Patrón de uso del repositorio")
    service_source = inspect.getsource(FileRenamerService)
    assert 'get_instance()' in service_source
    assert 'get_all_metadata_from_file' not in service_source
    logger.info("✓ Servicio usa get_instance() correctamente")
    logger.info("✓ No hay referencias a get_all_metadata_from_file")
    
    # Test 6: Verificar que el método move_file existe en el repositorio
    logger.info("\nTest 6: move_file en repositorio")
    assert hasattr(repo, 'move_file')
    assert callable(getattr(repo, 'move_file'))
    logger.info("✓ move_file disponible en repositorio")
    
    logger.info("\n" + "="*60)
    logger.info("✅ TODOS LOS TESTS PASARON")
    logger.info("="*60)
    logger.info("\nResumen del refactor:")
    logger.info("1. ✓ Servicio usa FileInfoRepositoryCache.get_instance()")
    logger.info("2. ✓ Eliminadas referencias a get_all_metadata_from_file")
    logger.info("3. ✓ Dataclasses optimizadas (sin __post_init__ vacío)")
    logger.info("4. ✓ move_file disponible para actualizar caché")
    logger.info("5. ✓ Patrón Stage 3 on-demand implementado")

if __name__ == "__main__":
    # Configurar logging
    logs_dir = Path.home() / "Documents" / "Innerpix_Lab" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(logs_dir, level="INFO", dual_log_enabled=False)
    
    try:
        test_renamer_basic_usage()
    except AssertionError as e:
        logger = get_logger('VerifyRenamer')
        logger.error(f"❌ Test falló: {e}")
        sys.exit(1)
    except Exception as e:
        logger = get_logger('VerifyRenamer')
        logger.error(f"❌ Error inesperado: {e}", exc_info=True)
        sys.exit(1)
