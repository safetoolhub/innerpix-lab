"""
Script de prueba para verificar la implementación de MAX_WORKERS
"""
from pathlib import Path
from config import Config
from utils.settings_manager import settings_manager
from utils.logger import get_logger

logger = get_logger("TestMaxWorkers")

def test_config():
    """Verifica que la configuración esté accesible"""
    logger.info(f"Config.MAX_WORKERS (default): {Config.MAX_WORKERS}")
    logger.info(f"Config.WORKER_SHUTDOWN_TIMEOUT_MS: {Config.WORKER_SHUTDOWN_TIMEOUT_MS}")

    
def test_settings_manager():
    """Verifica el settings_manager"""
    current_max_workers = settings_manager.get_max_workers(Config.MAX_WORKERS)
    logger.info(f"Settings Manager - get_max_workers(): {current_max_workers}")
    
    # Probar cambio de valor
    logger.info("Probando cambio de MAX_WORKERS a 8...")
    settings_manager.set(settings_manager.KEY_MAX_WORKERS, 8)
    new_value = settings_manager.get_max_workers(Config.MAX_WORKERS)
    logger.info(f"Nuevo valor: {new_value}")
    
    # Restaurar al valor por defecto
    settings_manager.set(settings_manager.KEY_MAX_WORKERS, Config.MAX_WORKERS)
    logger.info(f"Restaurado al default: {settings_manager.get_max_workers(Config.MAX_WORKERS)}")

def test_service_imports():
    """Verifica que los servicios importen correctamente"""
    try:
        from services.duplicate_detector import DuplicateDetector
        logger.info("✓ DuplicateDetector importado correctamente")
        
        from services.file_renamer import FileRenamer
        logger.info("✓ FileRenamer importado correctamente")
        
        from services.file_organizer import FileOrganizer
        logger.info("✓ FileOrganizer importado correctamente")
        
        # Verificar que tengan los imports necesarios
        import services.duplicate_detector as dd_module
        assert hasattr(dd_module, 'ThreadPoolExecutor'), "DuplicateDetector no tiene ThreadPoolExecutor"
        assert hasattr(dd_module, 'settings_manager'), "DuplicateDetector no tiene settings_manager"
        logger.info("✓ DuplicateDetector tiene ThreadPoolExecutor y settings_manager")
        
        import services.file_renamer as fr_module
        assert hasattr(fr_module, 'ThreadPoolExecutor'), "FileRenamer no tiene ThreadPoolExecutor"
        assert hasattr(fr_module, 'settings_manager'), "FileRenamer no tiene settings_manager"
        logger.info("✓ FileRenamer tiene ThreadPoolExecutor y settings_manager")
        
        import services.file_organizer as fo_module
        assert hasattr(fo_module, 'ThreadPoolExecutor'), "FileOrganizer no tiene ThreadPoolExecutor"
        assert hasattr(fo_module, 'settings_manager'), "FileOrganizer no tiene settings_manager"
        logger.info("✓ FileOrganizer tiene ThreadPoolExecutor y settings_manager")
        
    except Exception as e:
        logger.error(f"Error al importar servicios: {e}")
        raise

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("TEST: Verificación de implementación de MAX_WORKERS")
    logger.info("="*60)
    
    try:
        logger.info("\n1. Probando Config...")
        test_config()
        
        logger.info("\n2. Probando SettingsManager...")
        test_settings_manager()
        
        logger.info("\n3. Probando imports de servicios...")
        test_service_imports()
        
        logger.info("\n" + "="*60)
        logger.info("✅ TODOS LOS TESTS PASARON CORRECTAMENTE")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"\n❌ ERROR EN TEST: {e}")
        raise
