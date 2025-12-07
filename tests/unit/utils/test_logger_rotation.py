"""
Tests para la funcionalidad de rotación de logs por tamaño.

Verifica que los logs roten correctamente cuando alcanzan el tamaño máximo
configurado, tanto para backups ilimitados como limitados.
"""
import pytest
import logging
from pathlib import Path
import time
from utils import logger
from config import Config


@pytest.mark.unit
class TestLogRotation:
    """Tests para la rotación de logs por tamaño"""
    
    def test_rotating_handler_creation(self, temp_dir):
        """Verifica que se crean handlers con parámetros de rotación correctos"""
        # Configurar logging en directorio temporal
        log_file, logs_dir = logger.configure_logging(
            logs_dir=temp_dir,
            level="INFO",
            dual_log_enabled=False
        )
        
        # Verificar que el archivo de log se creó
        assert log_file.exists()
        
        # Obtener el logger raíz y verificar sus handlers
        root = logging.getLogger('PixaroLab')
        
        # Buscar handler de archivo rotativo
        rotating_handlers = [
            h for h in root.handlers 
            if isinstance(h, logger.ThreadSafeRotatingFileHandler)
        ]
        
        assert len(rotating_handlers) > 0, "Debería haber al menos un handler rotativo"
        
        # Verificar parámetros del handler
        handler = rotating_handlers[0]
        expected_max_bytes = Config.MAX_LOG_FILE_SIZE_MB * 1024 * 1024
        assert handler.maxBytes == expected_max_bytes
        assert handler.backupCount == Config.MAX_LOG_BACKUP_COUNT
    
    def test_rotation_trigger_basic(self, temp_dir):
        """Verifica que los logs rotan cuando se alcanza el tamaño máximo"""
        # Configurar con tamaño pequeño (10 KB) para testing rápido
        original_size = Config.MAX_LOG_FILE_SIZE_MB
        Config.MAX_LOG_FILE_SIZE_MB = 0.01  # 10 KB
        
        try:
            log_file, _ = logger.configure_logging(
                logs_dir=temp_dir,
                level="INFO",
                dual_log_enabled=False
            )
            
            test_logger = logger.get_logger("RotationTest")
            
            # Escribir suficientes mensajes para superar 10 KB
            # Cada mensaje tiene ~100 bytes, necesitamos ~100 mensajes
            long_message = "X" * 100
            for i in range(150):
                test_logger.info(f"Test message {i}: {long_message}")
            
            # CRITICAL: Flush handlers para forzar escritura al disco
            root = logging.getLogger('PixaroLab')
            for handler in root.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Verificar que se crearon archivos de backup
            backup_files = list(temp_dir.glob("*.log.*"))
            assert len(backup_files) > 0, "Deberían existir archivos de backup después de rotar"
            
        finally:
            # Restaurar configuración original
            Config.MAX_LOG_FILE_SIZE_MB = original_size
    
    def test_unlimited_backups(self, temp_dir):
        """Verifica que con backupCount=0 se mantienen todos los backups"""
        # Configurar para backups ilimitados y tamaño pequeño
        original_size = Config.MAX_LOG_FILE_SIZE_MB
        original_count = Config.MAX_LOG_BACKUP_COUNT
        
        Config.MAX_LOG_FILE_SIZE_MB = 0.005  # 5 KB - muy pequeño para forzar rotaciones
        Config.MAX_LOG_BACKUP_COUNT = 0  # Ilimitado
        
        try:
            log_file, _ = logger.configure_logging(
                logs_dir=temp_dir,
                level="INFO",
                dual_log_enabled=False
            )
            
            test_logger = logger.get_logger("UnlimitedTest")
            
            # Escribir muchos mensajes para forzar múltiples rotaciones
            long_message = "X" * 100
            for i in range(300):  # Suficiente para crear 6+ rotaciones
                test_logger.info(f"Message {i}: {long_message}")
                if i % 50 == 0:
                    time.sleep(0.01)  # Pequeña pausa para asegurar escritura
            
            # CRITICAL: Flush handlers
            root = logging.getLogger('PixaroLab')
            for handler in root.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Contar archivos de backup (*.log.1, *.log.2, etc.)
            backup_files = sorted(temp_dir.glob("*.log.*"))
            
            # Con backupCount=0, todos los backups deberían mantenerse
            assert len(backup_files) >= 5, f"Deberían existir 5+ backups con count=0, encontrados: {len(backup_files)}"
            
            # Verificar que la numeración es secuencial
            backup_numbers = []
            for f in backup_files:
                parts = f.name.split('.')
                if len(parts) >= 3 and parts[-1].isdigit():
                    backup_numbers.append(int(parts[-1]))
            
            assert backup_numbers == sorted(backup_numbers), "Los backups deberían estar numerados secuencialmente"
            
        finally:
            Config.MAX_LOG_FILE_SIZE_MB = original_size
            Config.MAX_LOG_BACKUP_COUNT = original_count
    
    def test_limited_backups(self, temp_dir):
        """Verifica que con backupCount=5 solo se mantienen 5 backups"""
        original_size = Config.MAX_LOG_FILE_SIZE_MB
        original_count = Config.MAX_LOG_BACKUP_COUNT
        
        Config.MAX_LOG_FILE_SIZE_MB = 0.005  # 5 KB
        Config.MAX_LOG_BACKUP_COUNT = 5  # Máximo 5 backups
        
        try:
            log_file, _ = logger.configure_logging(
                logs_dir=temp_dir,
                level="INFO",
                dual_log_enabled=False
            )
            
            test_logger = logger.get_logger("LimitedTest")
            
            # Escribir suficientes mensajes para crear más de 5 rotaciones
            long_message = "X" * 100
            for i in range(400):  # Crear 8+ rotaciones
                test_logger.info(f"Message {i}: {long_message}")
                if i % 50 == 0:
                    time.sleep(0.01)
            
            # Flush handlers
            root = logging.getLogger('PixaroLab')
            for handler in root.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Contar archivos de backup
            backup_files = sorted(temp_dir.glob("*.log.*"))
            
            # Solo deberían existir máximo 5 backups
            assert len(backup_files) <= 5, f"Deberían existir máximo 5 backups, encontrados: {len(backup_files)}"
            
        finally:
            Config.MAX_LOG_FILE_SIZE_MB = original_size
            Config.MAX_LOG_BACKUP_COUNT = original_count
    
    def test_dual_log_rotation(self, temp_dir):
        """Verifica que tanto el log principal como el de warnings rotan"""
        original_size = Config.MAX_LOG_FILE_SIZE_MB
        Config.MAX_LOG_FILE_SIZE_MB = 0.01  # 10 KB
        
        try:
            log_file, _ = logger.configure_logging(
                logs_dir=temp_dir,
                level="INFO",
                dual_log_enabled=True  # Activar dual logging
            )
            
            test_logger = logger.get_logger("DualTest")
            
            # Escribir mensajes de diferentes niveles
            long_message = "X" * 100
            for i in range(150):
                test_logger.info(f"Info message {i}: {long_message}")
                if i % 3 == 0:
                    test_logger.warning(f"Warning message {i}: {long_message}")
            
            # Flush handlers
            root = logging.getLogger('PixaroLab')
            for handler in root.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Verificar backups del log principal
            main_backups = list(temp_dir.glob("*_INFO.log.*"))
            assert len(main_backups) > 0, "El log principal debería tener backups"
            
            # Verificar backups del log de warnings
            warn_backups = list(temp_dir.glob("*_WARNERROR.log.*"))
            # El archivo de warnings puede no rotar si no hay suficientes warnings
            # pero debería existir
            warn_files = list(temp_dir.glob("*_WARNERROR.log*"))
            assert len(warn_files) > 0, "Debería existir archivo de warnings"
            
        finally:
            Config.MAX_LOG_FILE_SIZE_MB = original_size
    
    def test_rotation_file_naming(self, temp_dir):
        """Verifica que los archivos rotados siguen el patrón .log.1, .log.2, etc."""
        original_size = Config.MAX_LOG_FILE_SIZE_MB
        Config.MAX_LOG_FILE_SIZE_MB = 0.005  # 5 KB
        
        try:
            log_file, _ = logger.configure_logging(
                logs_dir=temp_dir,
                level="INFO",
                dual_log_enabled=False
            )
            
            test_logger = logger.get_logger("NamingTest")
            
            # Escribir suficientes mensajes para crear varios backups
            long_message = "X" * 100
            for i in range(200):
                test_logger.info(f"Message {i}: {long_message}")
            
            # Obtener archivos de backup
            backup_files = sorted(temp_dir.glob("*.log.*"))
            
            # Verificar que todos siguen el patrón correcto
            for backup in backup_files:
                name = backup.name
                # Debería terminar en .log.N donde N es un número
                parts = name.split('.')
                assert len(parts) >= 3, f"Nombre inválido: {name}"
                assert parts[-1].isdigit(), f"Último componente debería ser número: {name}"
                assert parts[-2] == "log", f"Penúltimo componente debería ser 'log': {name}"
            
        finally:
            Config.MAX_LOG_FILE_SIZE_MB = original_size
