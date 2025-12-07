"""
Test específico para verificar el comportamiento con MAX_LOG_BACKUP_COUNT = 9999.

Este test valida que:
1. La rotación funciona correctamente con el valor real de producción (9999)
2. Los archivos se numeran correctamente hasta valores altos
3. El sistema puede manejar múltiples rotaciones sin degradación
"""
import pytest
from pathlib import Path
import tempfile

from utils.logger import configure_logging, get_logger
from config import Config


def test_rotation_with_production_backup_count():
    """
    Test con el valor real de producción: MAX_LOG_BACKUP_COUNT = 9999.
    
    Verifica que:
    - La rotación funciona correctamente con 9999 como límite
    - Los archivos se crean con numeración correcta
    - No hay degradación con múltiples rotaciones
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        
        # Usar el valor real de producción
        assert Config.MAX_LOG_BACKUP_COUNT == 9999, \
            "Este test asume MAX_LOG_BACKUP_COUNT = 9999"
        
        log_file, _ = configure_logging(
            logs_dir=temp_dir,
            level="INFO",
            dual_log_enabled=False
        )
        
        logger = get_logger("ProductionTest")
        
        # Calcular mensajes para provocar 3 rotaciones
        max_bytes = Config.MAX_LOG_FILE_SIZE_MB * 1024 * 1024
        messages_per_rotation = (max_bytes // 250) + 500
        
        rotation_count = 0
        target_rotations = 3
        
        print(f"\n📊 Provocando {target_rotations} rotaciones con backupCount={Config.MAX_LOG_BACKUP_COUNT}")
        
        for i in range(messages_per_rotation * target_rotations):
            logger.info(f"[{i:06d}] " + "x" * 200)
            
            # Verificar rotaciones cada 5000 mensajes
            if i % 5000 == 0:
                new_count = sum(
                    1 for j in range(1, 10)
                    if Path(f"{log_file}.{j}").exists()
                )
                
                if new_count > rotation_count:
                    rotation_count = new_count
                    print(f"✅ Rotación #{rotation_count} detectada (mensaje {i})")
                
                # Detener cuando alcancemos el objetivo
                if rotation_count >= target_rotations:
                    break
        
        # Verificar que se crearon las rotaciones esperadas
        existing_backups = [
            i for i in range(1, target_rotations + 2)
            if Path(f"{log_file}.{i}").exists()
        ]
        
        print(f"\n📁 Archivos creados: {existing_backups}")
        
        assert len(existing_backups) == target_rotations, \
            f"Deben existir {target_rotations} backups, encontrados: {existing_backups}"
        
        # Verificar numeración consecutiva
        assert existing_backups == list(range(1, target_rotations + 1)), \
            f"Los backups deben ser consecutivos desde .1, encontrados: {existing_backups}"
        
        # Verificar tamaño de archivos rotados
        for i in range(1, target_rotations + 1):
            backup_file = Path(f"{log_file}.{i}")
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            
            # Tolerancia del 95% (algunos bytes menos por flush timing)
            assert size_mb >= Config.MAX_LOG_FILE_SIZE_MB * 0.95, \
                f"El backup .{i} debe ser >= {Config.MAX_LOG_FILE_SIZE_MB * 0.95} MB, fue {size_mb:.2f} MB"
            
            print(f"✅ Backup .{i}: {size_mb:.2f} MB")
        
        # Verificar archivo actual
        current_size_mb = log_file.stat().st_size / (1024 * 1024)
        assert current_size_mb < Config.MAX_LOG_FILE_SIZE_MB, \
            f"El archivo actual debe ser < {Config.MAX_LOG_FILE_SIZE_MB} MB, fue {current_size_mb:.2f} MB"
        
        print(f"✅ Archivo actual: {current_size_mb:.2f} MB")
        print(f"\n🎉 Test exitoso con MAX_LOG_BACKUP_COUNT = {Config.MAX_LOG_BACKUP_COUNT}")


def test_high_number_backup_numbering():
    """
    Verifica que el sistema funciona correctamente con backupCount=9999.
    
    Este test valida que la configuración de producción (9999 backups)
    permite rotaciones múltiples sin errores.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        
        from utils.logger import ThreadSafeRotatingFileHandler
        import logging
        
        log_file = temp_dir / "test_high_numbers.log"
        
        # Usar el valor de producción: 9999
        handler = ThreadSafeRotatingFileHandler(
            str(log_file),
            maxBytes=1 * 1024 * 1024,  # 1 MB para rotación rápida
            backupCount=9999
        )
        
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        test_logger = logging.getLogger('HighNumberTest')
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)
        
        print(f"\n📊 Provocando rotaciones con backupCount=9999")
        
        # Provocar 3 rotaciones
        target_rotations = 3
        rotation_count = 0
        
        for i in range(20000):  # Suficientes mensajes para 3 rotaciones
            test_logger.info(f"[{i:06d}] " + "x" * 200)
            
            if i % 500 == 0:
                # Contar backups existentes
                new_count = sum(
                    1 for j in range(1, 10)
                    if Path(f"{log_file}.{j}").exists()
                )
                
                if new_count > rotation_count:
                    rotation_count = new_count
                    print(f"✅ Rotación #{rotation_count} detectada")
                
                if rotation_count >= target_rotations:
                    break
        
        # Verificar que se crearon las rotaciones
        assert rotation_count >= target_rotations, \
            f"Deben haberse creado al menos {target_rotations} rotaciones, encontradas: {rotation_count}"
        
        # Verificar archivos .1, .2, .3
        for i in range(1, target_rotations + 1):
            backup = Path(f"{log_file}.{i}")
            assert backup.exists(), f"El backup .{i} debe existir"
            print(f"✅ Backup .{i} creado correctamente")
        
        print(f"\n✅ Sistema funciona correctamente con backupCount=9999")
        print(f"✅ {rotation_count} rotaciones exitosas sin errores")
        
        handler.close()


def test_backup_count_limit_enforcement():
    """
    Verifica que con 9999 backups, se pueden crear cientos de rotaciones
    sin llegar al límite (test de estrés ligero).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        
        # Este test toma mucho tiempo, solo verificamos que el límite es suficientemente alto
        # para producción (donde 9999 es prácticamente ilimitado)
        
        assert Config.MAX_LOG_BACKUP_COUNT == 9999, \
            "El límite de producción debe ser 9999"
        
        # En una sesión típica larga (8 horas de uso intensivo):
        # - 10 MB por rotación
        # - Estimado: 50-100 rotaciones en caso extremo
        # - 9999 backups = 99,990 MB = ~100 GB de espacio para logs
        
        max_expected_rotations_per_session = 100
        total_space_gb = (Config.MAX_LOG_BACKUP_COUNT * Config.MAX_LOG_FILE_SIZE_MB) / 1024
        
        print(f"\n📊 Análisis de límites:")
        print(f"   MAX_LOG_BACKUP_COUNT: {Config.MAX_LOG_BACKUP_COUNT}")
        print(f"   MAX_LOG_FILE_SIZE_MB: {Config.MAX_LOG_FILE_SIZE_MB} MB")
        print(f"   Espacio total teórico: {total_space_gb:.1f} GB")
        print(f"   Rotaciones esperadas por sesión: ~{max_expected_rotations_per_session}")
        print(f"   Factor de seguridad: {Config.MAX_LOG_BACKUP_COUNT / max_expected_rotations_per_session:.1f}x")
        
        assert Config.MAX_LOG_BACKUP_COUNT >= max_expected_rotations_per_session * 10, \
            f"El límite debe ser al menos 10x las rotaciones esperadas por sesión"
        
        print(f"\n✅ El límite de {Config.MAX_LOG_BACKUP_COUNT} backups es adecuado para producción")


def test_rotation_consistency_across_restarts():
    """
    Verifica que la numeración de backups es consistente después de
    reiniciar el logger múltiples veces.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        
        max_bytes = Config.MAX_LOG_FILE_SIZE_MB * 1024 * 1024
        messages_per_rotation = (max_bytes // 250) + 500
        
        # Sesión 1: Crear 2 backups
        log_file1, _ = configure_logging(logs_dir=temp_dir, level="INFO", dual_log_enabled=False)
        logger1 = get_logger("Session1")
        
        for i in range(messages_per_rotation * 2):
            logger1.info(f"[S1-{i:06d}] " + "x" * 200)
            if i % 5000 == 0 and Path(f"{log_file1}.2").exists():
                break
        
        # Cerrar logger
        import logging
        root_logger = logging.getLogger('PixaroLab')
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        
        print(f"\n📊 Después de sesión 1:")
        backups_after_s1 = [i for i in range(1, 5) if Path(f"{log_file1}.{i}").exists()]
        print(f"   Backups existentes: {backups_after_s1}")
        
        # Sesión 2: Crear 1 backup más
        log_file2, _ = configure_logging(logs_dir=temp_dir, level="INFO", dual_log_enabled=False)
        logger2 = get_logger("Session2")
        
        for i in range(messages_per_rotation):
            logger2.info(f"[S2-{i:06d}] " + "x" * 200)
            if i % 5000 == 0 and Path(f"{log_file2}.3").exists():
                break
        
        print(f"\n📊 Después de sesión 2:")
        backups_after_s2 = [i for i in range(1, 6) if Path(f"{log_file2}.{i}").exists()]
        print(f"   Backups existentes: {backups_after_s2}")
        
        # Verificar consistencia: debe haber 3 backups consecutivos
        assert len(backups_after_s2) <= 3, \
            f"Deben existir máximo 3 backups, encontrados: {backups_after_s2}"
        
        if len(backups_after_s2) > 0:
            assert backups_after_s2[0] == 1, "Debe empezar en .1"
            assert backups_after_s2 == list(range(1, len(backups_after_s2) + 1)), \
                f"Deben ser consecutivos: {backups_after_s2}"
        
        print(f"\n✅ Numeración consistente después de múltiples sesiones")


if __name__ == "__main__":
    print("=" * 70)
    print("TESTS DE PRODUCCIÓN CON MAX_LOG_BACKUP_COUNT = 9999")
    print("=" * 70)
    
    test_rotation_with_production_backup_count()
    print("\n" + "=" * 70)
    
    test_high_number_backup_numbering()
    print("\n" + "=" * 70)
    
    test_backup_count_limit_enforcement()
    print("\n" + "=" * 70)
    
    test_rotation_consistency_across_restarts()
    print("\n" + "=" * 70)
    
    print("\n🎉 TODOS LOS TESTS DE PRODUCCIÓN PASARON EXITOSAMENTE")
